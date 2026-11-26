"""Helpers for end-to-end tests against the running n8n test stack (make test-e2e)."""

from __future__ import annotations

import hashlib
import hmac
import json
import subprocess
import time
import uuid
from collections.abc import Callable
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
