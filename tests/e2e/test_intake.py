"""M1 – intake + validation: HMAC webhook, hosted form, spam, free-mail, idempotency."""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

import httpx
import pytest

from tests.e2e.conftest import BROWSER_UA, PostLead, lead_row, sign, sql, wait_for

pytestmark = pytest.mark.e2e


# --- signature ------------------------------------------------------------------
def test_unsigned_request_is_rejected_with_401(post_lead: PostLead, lead: dict[str, str]) -> None:
    res = post_lead(lead, signature=None)
    assert res.status_code == 401
    assert res.json() == {"error": "invalid signature"}


def test_wrong_signature_is_rejected_with_401(post_lead: PostLead, lead: dict[str, str]) -> None:
    assert post_lead(lead, signature="sha256=" + "0" * 64).status_code == 401


def test_signature_for_a_different_body_is_rejected(
    post_lead: PostLead, lead: dict[str, str], env: dict[str, str]
) -> None:
    signed_body = json.dumps(lead).encode()
    tampered = json.dumps({**lead, "budget_range": "Over $150k"}).encode()
    res = post_lead({}, raw=tampered, signature=sign(signed_body, env["WEBHOOK_HMAC_SECRET"]))
    assert res.status_code == 401


def test_rejected_request_stores_nothing(post_lead: PostLead, lead: dict[str, str]) -> None:
    post_lead(lead, signature=None)
    lead_hash = hashlib.sha256(f"{lead['email']}\n{lead['message']}".encode()).hexdigest()
    assert sql(f"SELECT count(*) FROM leads WHERE lead_hash = '{lead_hash}'") == [["0"]]  # noqa: S608


# --- accepted lead + normalisation ---------------------------------------------------
def test_valid_lead_is_accepted_stored_and_starts_the_pipeline(
    post_lead: PostLead, lead: dict[str, str], api: httpx.Client
) -> None:
    res = post_lead(lead)
    assert res.status_code == 202
    body = res.json()
    assert body["status"] == "accepted"
    lead_id = body["lead_id"]
    source, status, name, email, domain = lead_row(lead_id)
    assert [source, name, email, domain] == [
        "webhook", "Daniel Reyes",
        "daniel.reyes@harborlogistics.example", "harborlogistics.example",
    ]  # fmt: skip
    # The pipeline runs in the background and may already have moved the lead on.
    assert status not in {"rejected_spam", "duplicate_ignored"}

    def pipeline_started() -> bool:
        runs = api.get(
            "/executions",
            params={"workflowId": "lpMainIntake0001", "includeData": "true", "limit": 10},
        ).json()["data"]
        return any(lead_id in json.dumps(r.get("data", {})) for r in runs)

    wait_for(pipeline_started)


def test_email_and_whitespace_are_normalised(post_lead: PostLead, lead: dict[str, str]) -> None:
    messy = {**lead, "email": "  Daniel.Reyes@HarborLogistics.example ", "name": " Daniel   Reyes "}
    lead_id = post_lead(messy).json()["lead_id"]
    assert lead_row(lead_id, "name, email") == [
        "Daniel Reyes",
        "daniel.reyes@harborlogistics.example",
    ]


@pytest.mark.parametrize(
    ("website", "domain"),
    [
        ("https://www.Harbor-Group.example/about?x=1", "harbor-group.example"),
        ("harbor-group.example", "harbor-group.example"),
        ("http://harbor-group.example:8080", "harbor-group.example"),
    ],
)
def test_website_domain_is_parsed_from_the_url(
    post_lead: PostLead, lead: dict[str, str], website: str, domain: str
) -> None:
    lead_id = post_lead({**lead, "website": website}).json()["lead_id"]
    assert lead_row(lead_id, "website_domain") == [domain]


def test_domain_falls_back_to_email_domain_when_website_is_empty(
    post_lead: PostLead, lead: dict[str, str]
) -> None:
    lead_id = post_lead({**lead, "website": ""}).json()["lead_id"]
    assert lead_row(lead_id, "website_domain, personal_email") == ["harborlogistics.example", "f"]


def test_free_mail_is_flagged_and_not_used_as_website(
    post_lead: PostLead, lead: dict[str, str]
) -> None:
    lead_id = post_lead({**lead, "email": "dreyes@gmail.com", "website": ""}).json()["lead_id"]
    assert lead_row(lead_id, "website_domain, personal_email") == ["", "t"]


# --- invalid + spam --------------------------------------------------------------------
@pytest.mark.parametrize(
    ("change", "error"),
    [
        ({"email": "not-an-email"}, "email is not valid"),
        ({"name": "   "}, "name is required"),
        ({"message": ""}, "message is required"),
    ],
)
def test_invalid_lead_gets_422(
    post_lead: PostLead, lead: dict[str, str], change: dict[str, str], error: str
) -> None:
    res = post_lead({**lead, **change})
    assert res.status_code == 422
    assert error in res.json()["errors"]


@pytest.mark.parametrize(
    "change",
    [
        {"website_url_confirm": "https://spam.example"},
        {"message": "Visit http://a.example http://b.example http://c.example www.d.example now"},
        {"message": "We offer SEO services and backlinks for your site"},
    ],
    ids=["honeypot", "link-stuffed", "blocked-phrase"],
)
def test_spam_is_rejected_and_stored_without_personal_data(
    post_lead: PostLead, lead: dict[str, str], change: dict[str, str]
) -> None:
    payload: dict[str, Any] = {**lead, **change}
    if "message" in change:
        payload["message"] += f" {uuid.uuid4()}"
    res = post_lead(payload)
    assert res.status_code == 200
    assert res.json() == {"status": "rejected_spam"}
    lead_hash = hashlib.sha256(f"{lead['email']}\n{payload['message']}".encode()).hexdigest()
    rows = sql(f"SELECT status, name, email, payload FROM leads WHERE lead_hash = '{lead_hash}'")  # noqa: S608
    assert rows == [["rejected_spam", "", "", ""]]


# --- idempotency -----------------------------------------------------------------------
def test_duplicate_within_24h_is_ignored(post_lead: PostLead, lead: dict[str, str]) -> None:
    first = post_lead(lead)
    second = post_lead(lead)
    assert first.status_code == 202
    assert second.status_code == 200
    assert second.json() == {"status": "duplicate_ignored"}
    lead_hash = hashlib.sha256(f"{lead['email']}\n{lead['message']}".encode()).hexdigest()
    assert sql(f"SELECT count(*) FROM leads WHERE lead_hash = '{lead_hash}'") == [["1"]]  # noqa: S608


def test_same_email_with_a_new_message_is_a_new_lead(
    post_lead: PostLead, lead: dict[str, str]
) -> None:
    assert post_lead(lead).status_code == 202
    again = post_lead({**lead, "message": lead["message"] + " Also need a mobile app."})
    assert again.status_code == 202


def test_duplicate_older_than_24h_is_processed_again(
    post_lead: PostLead, lead: dict[str, str]
) -> None:
    lead_id = post_lead(lead).json()["lead_id"]
    sql(f"UPDATE leads SET received_at = now() - interval '25 hours' WHERE lead_id = '{lead_id}'")
    sql(
        "UPDATE lead_claims SET claimed_at = now() - interval '25 hours' "
        f"WHERE lead_id = '{lead_id}'"
    )
    assert post_lead(lead).status_code == 202


def test_simultaneous_identical_submissions_create_one_lead(
    post_lead: PostLead, lead: dict[str, str]
) -> None:
    """Double-click or a sender retrying in parallel: only one lead is accepted."""
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=4) as pool:
        codes = sorted(r.status_code for r in pool.map(lambda _: post_lead(lead), range(4)))
    assert codes == [200, 200, 200, 202]
    lead_hash = hashlib.sha256(f"{lead['email']}\n{lead['message']}".encode()).hexdigest()
    assert sql(f"SELECT count(*) FROM leads WHERE lead_hash = '{lead_hash}'") == [["1"]]


# --- hosted form -------------------------------------------------------------------------
def test_hosted_form_submission_is_stored(n8n_url: str) -> None:
    marker = str(uuid.uuid4())
    fields = {
        "field-0": "Priya Natarajan",
        "field-1": "priya.natarajan@gmail.com",
        "field-2": "Coastline Clinics",
        "field-3": "coastlineclinics.example",
        "field-4": "COO",
        "field-5": "$50k-$150k",
        "field-6": f"We want a patient booking portal by spring. {marker}",
        "field-7": "",
    }
    res = httpx.post(
        f"{n8n_url}/form/lead-form",
        files={k: (None, v) for k, v in fields.items()},
        headers={"User-Agent": BROWSER_UA},
        timeout=60,
    )
    assert res.status_code == 200

    def stored() -> list[list[str]]:
        return sql(
            "SELECT source, website_domain, personal_email FROM leads "
            f"WHERE payload->>'message' LIKE '%{marker}'"  # noqa: S608
        )

    # Status is not asserted: the background pipeline may already have moved the lead on.
    assert wait_for(stored) == [["form", "coastlineclinics.example", "t"]]


def test_hosted_form_ignores_bots(n8n_url: str) -> None:
    res = httpx.get(f"{n8n_url}/form/lead-form", headers={"User-Agent": "curl/8.0"}, timeout=30)
    assert res.status_code == 401
