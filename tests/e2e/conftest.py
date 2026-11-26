"""Helpers for end-to-end tests against the running n8n test stack (make test-e2e)."""

from __future__ import annotations

import hashlib
import hmac
import json
import subprocess
import time
import uuid
from collections.abc import Callable, Iterator
from typing import Any

import httpx
import pytest

from scripts.envfile import ROOT, read_env

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0 Safari/537.36"
)


@pytest.fixture(scope="session")
def env() -> dict[str, str]:
    return read_env()


@pytest.fixture(scope="session")
def n8n_url(env: dict[str, str]) -> str:
    return env.get("N8N_URL", "http://localhost:5678")


def sign(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


PostLead = Callable[..., httpx.Response]


@pytest.fixture()
def post_lead(n8n_url: str, env: dict[str, str]) -> PostLead:
    def _post(
        payload: dict[str, Any], *, signature: str | None = "valid", raw: bytes | None = None
    ) -> httpx.Response:
        body = raw if raw is not None else json.dumps(payload).encode()
        headers = {"content-type": "application/json"}
        if signature == "valid":
            headers["X-Signature-256"] = sign(body, env["WEBHOOK_HMAC_SECRET"])
        elif signature is not None:
            headers["X-Signature-256"] = signature
        return httpx.post(f"{n8n_url}/webhook/lead", content=body, headers=headers, timeout=60)

    return _post


@pytest.fixture()
def lead() -> dict[str, str]:
    """A fresh, valid lead; the unique message keeps it clear of the 24 h duplicate check."""
    return {
        "name": "Daniel Reyes",
        "email": "daniel.reyes@harborlogistics.example",
        "company": "Harbor Logistics",
        "website": "https://www.harborlogistics.example/",
        "role": "Head of Operations",
        "budget_range": "$20k-$50k",
        "message": f"We need a customer portal for shipment tracking by Q2. ref {uuid.uuid4()}",
    }


def sql(query: str) -> list[list[str]]:
    """Run a query in the leads database (Postgres is not exposed to the host)."""
    env = read_env()
    result = subprocess.run(  # noqa: S603
        ["docker", "compose", "exec", "-T", "postgres", "psql", "-qAt", "-F", "\t",  # noqa: S607
         "-U", env.get("DB_POSTGRESDB_USER", "n8n"),
         "-d", env.get("LEADPILOT_DB_NAME", "leadpilot"),
         "-c", query],
        cwd=ROOT, capture_output=True, text=True, check=True, encoding="utf-8",
    )  # fmt: skip
    return [line.split("\t") for line in result.stdout.splitlines() if line]


def lead_row(
    lead_id: str, columns: str = "source, status, name, email, website_domain"
) -> list[str]:
    rows = sql(f"SELECT {columns} FROM leads WHERE lead_id = '{lead_id}'")  # noqa: S608
    assert len(rows) == 1, f"expected one row for {lead_id}, got {rows}"
    return rows[0]


def wait_for(predicate: Callable[[], Any], timeout: float = 30.0, interval: float = 1.0) -> Any:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(interval)
    raise AssertionError("condition not met within timeout")


@pytest.fixture()
def api(n8n_url: str, env: dict[str, str]) -> httpx.Client:
    return httpx.Client(
        base_url=f"{n8n_url}/api/v1", headers={"X-N8N-API-KEY": env["N8N_API_KEY"]}, timeout=30
    )


# --- mock server (Tavily + Gemini) ----------------------------------------------------
# Fixture companies in tests/mock_server/fixtures/companies.json: (company, website, email)
COMPANIES = {
    "harbor": (
        "Harbor Logistics",
        "harborlogistics.example",
        "daniel.reyes@harborlogistics.example",
    ),
    "unreachable": ("Unreachable Corp", "unreachable.example", "jo@unreachable.example"),
    "coastline": ("Coastline Clinics", "", "priya.natarajan@gmail.com"),
    "unknown": ("Nobody Knows Ltd", "nobody-knows.example", "a@nobody-knows.example"),
}


@pytest.fixture()
def mock(env: dict[str, str]) -> Iterator[httpx.Client]:
    client = httpx.Client(base_url=env.get("MOCK_URL", "http://localhost:8099"), timeout=10)
    client.post("/_control/reset")
    yield client
    client.post("/_control/reset")


def fail(mock: httpx.Client, service: str, times: int, match: str = "") -> None:
    """Make the next `times` calls fail; service is tavily_search, tavily_extract, gemini,
    gemini:<task> (profile, score, draft, judge), slack or hubspot. With `match`, only calls
    whose body contains that text fail (pipelines from other tests can't use them up)."""
    body = {"service": service, "times": times, "match": match}
    mock.post("/_control/fail", json=body).raise_for_status()


def calls(mock: httpx.Client, service: str) -> int:
    return sum(1 for c in mock.get("/_control/calls").json() if c["service"] == service)


def gemini_calls(mock: httpx.Client, task: str) -> int:
    return sum(1 for c in mock.get("/_control/calls").json()
               if c["service"] == "gemini" and c["path"].endswith(f"#{task}"))  # fmt: skip


def gemini_request(mock: httpx.Client, task: str) -> str:
    """The JSON body (first 50 kB) of the first Gemini request for a task."""
    return str(next(c["body"] for c in mock.get("/_control/calls").json()
                    if c["service"] == "gemini" and c["path"].endswith(f"#{task}")))  # fmt: skip


def unique_email(email: str) -> str:
    """name+tag@domain: same domain (fixtures, allow-list), but no two tests share a contact."""
    local, domain = email.split("@")
    return f"{local}+{uuid.uuid4().hex[:8]}@{domain}"


def post_company_lead(post_lead: PostLead, key: str, **overrides: Any) -> str:
    """Post a lead for one fixture company; returns its lead_id.

    Pipelines from earlier tests keep running in the background (approvals time out,
    emails and CRM writes follow decisions), so every lead gets its own email address and
    tests look only at records that belong to their lead."""
    company, website, email = COMPANIES[key]
    email = unique_email(email)
    payload = {
        "name": "Test Person", "email": email, "company": company, "website": website,
        "role": "Head of Operations", "budget_range": "$20k-$50k",
        "message": f"We need a customer portal for our team. {uuid.uuid4()}",
        **overrides,
    }  # fmt: skip
    res = post_lead(payload)
    assert res.status_code == 202, res.text
    return str(res.json()["lead_id"])


# --- approval (M4) ----------------------------------------------------------------------
def await_approval(lead_id: str, timeout: float = 60) -> str:
    """Wait until the lead is waiting for a decision; returns the approval form URL."""

    def ready() -> list[list[str]]:
        return sql(
            "SELECT approval_url FROM leads "
            f"WHERE lead_id = '{lead_id}' AND status = 'awaiting_approval'"
        )

    return str(wait_for(ready, timeout)[0][0])


def submit_decision(url: str, decision: str, *, reviewer: str = "Sara Chen",
                    subject: str | None = None, body: str | None = None,
                    reason: str = "") -> httpx.Response:  # fmt: skip
    """Fill in the approval form the way a reviewer's browser does (fields in form order).

    subject/body None keeps the pre-filled draft."""
    page = httpx.get(url, headers={"User-Agent": BROWSER_UA}, timeout=30)
    page.raise_for_status()
    # One JSON value per row: psql output is line-based and the body has several lines.
    stored = sql(
        "SELECT json_build_array(draft->>'subject', draft->>'body') FROM leads "
        f"WHERE approval_url = '{url.replace(chr(39), chr(39) * 2)}'"
    )[0][0]
    draft = json.loads(stored)
    fields = {
        "field-0": reviewer,
        "field-1": decision,
        "field-2": draft[0] if subject is None else subject,
        "field-3": draft[1] if body is None else body,
        "field-4": reason,
    }
    return httpx.post(url, files={k: (None, v) for k, v in fields.items()},
                      headers={"User-Agent": BROWSER_UA}, timeout=30)  # fmt: skip


def decision_of(lead_id: str, timeout: float = 60) -> dict[str, Any]:
    def decided() -> list[list[str]]:
        return sql(
            f"SELECT decision FROM leads WHERE lead_id = '{lead_id}' AND decision IS NOT NULL"
        )

    result: dict[str, Any] = json.loads(wait_for(decided, timeout)[0][0])
    return result


def slack_posts(mock: httpx.Client, method: str = "chat.postMessage") -> list[dict[str, Any]]:
    return [json.loads(c["body"]) for c in mock.get("/_control/calls").json()
            if c["service"] == "slack" and c["path"] == method]  # fmt: skip


@pytest.fixture()
def ops(n8n_url: str, env: dict[str, str]) -> Callable[..., httpx.Response]:
    def _ops(action: str, token: str | None = None, **extra: Any) -> httpx.Response:
        return httpx.post(
            f"{n8n_url}/webhook/ops", json={"action": action, **extra},
            headers={"X-LeadPilot-Ops-Token": token or env["OPS_WEBHOOK_TOKEN"]}, timeout=120,
        )  # fmt: skip

    return _ops


# --- send + CRM (M5) --------------------------------------------------------------------
FINAL_STATUSES = ("approved_sent", "rejected_by_reviewer", "needs_manual_follow_up",
                  "cold_recorded", "error_recoverable")  # fmt: skip


def final_row(lead_id: str, timeout: float = 90) -> dict[str, Any]:
    """Wait until the pipeline has finished with the lead; returns the row as a dict."""
    statuses = ", ".join(f"'{s}'" for s in FINAL_STATUSES)

    def done() -> list[list[str]]:
        return sql(
            "SELECT row_to_json(l) FROM leads l "
            f"WHERE lead_id = '{lead_id}' AND status IN ({statuses}) AND completed_at IS NOT NULL"
        )

    row: dict[str, Any] = json.loads(wait_for(done, timeout)[0][0])
    return row


@pytest.fixture()
def mailpit(env: dict[str, str]) -> Iterator[httpx.Client]:
    client = httpx.Client(base_url=env.get("MAILPIT_URL", "http://localhost:8025"), timeout=10)
    client.delete("/api/v1/messages")
    yield client


def emails_to(mailpit: httpx.Client, address: str) -> list[dict[str, Any]]:
    """Full messages (with Text) sent to an address."""
    listing = mailpit.get("/api/v1/messages").json().get("messages", [])
    ids = [m["ID"] for m in listing if any(t["Address"] == address for t in m["To"])]
    return [mailpit.get(f"/api/v1/message/{mid}").json() for mid in ids]


def hubspot(mock: httpx.Client) -> dict[str, Any]:
    state: dict[str, Any] = mock.get("/_control/hubspot").json()
    return state


def lead_email(lead_id: str) -> str:
    return sql(f"SELECT email FROM leads WHERE lead_id = '{lead_id}'")[0][0]


def crm_for(mock: httpx.Client, email: str) -> dict[str, Any]:
    """The HubSpot mock records that belong to one contact."""
    state = hubspot(mock)
    contact = state["contacts"].get(email)
    if contact is None:
        return {"contact": None, "companies": {}, "notes": [], "tasks": []}
    cid = contact["id"]

    def linked(obj: dict[str, Any]) -> bool:
        return any(a["to"]["id"] == cid for a in obj.get("associations", []))

    company_ids = [co for c, co in state["associations"] if c == cid]
    return {
        "contact": contact,
        "companies": {i: state["companies"][i] for i in company_ids},
        "associations": [pair for pair in state["associations"] if pair[0] == cid],
        "notes": [n for n in state["notes"] if linked(n)],
        "tasks": [t for t in state["tasks"] if linked(t)],
    }


def slack_for(mock: httpx.Client, lead_id: str) -> dict[str, list[dict[str, Any]]]:
    """Slack calls that belong to one lead: matched by its message ts and approval URL."""
    row = sql(
        "SELECT coalesce(slack_ts, '-'), coalesce(approval_url, '-') FROM leads "
        f"WHERE lead_id = '{lead_id}'"
    )[0]
    ts, url = row
    posts = slack_posts(mock)
    return {
        "requests": [
            p for p in posts if url in p.get("text", "") and not p.get("thread_ts")
        ],  # fmt: skip
        "reminders": [p for p in posts if p.get("thread_ts") == ts],
        "updates": [p for p in slack_posts(mock, "chat.update") if p.get("ts") == ts],
        "alerts": [
            p for p in posts if p.get("channel") == "C0ALERTS" and lead_id in p.get("text", "")
        ],
    }
