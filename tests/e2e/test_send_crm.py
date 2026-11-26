"""M5 – send the approved email, update HubSpot and Slack; cold leads and the daily digest.

Every test looks only at the records of its own lead (unique email, its Slack ts): pipelines
from earlier tests may still be finishing in the background.
"""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from tests.e2e.conftest import (
    PostLead,
    await_approval,
    crm_for,
    emails_to,
    final_row,
    post_company_lead,
    slack_for,
    slack_posts,
    sql,
    submit_decision,
    wait_for,
)

pytestmark = pytest.mark.e2e


def approve_harbor(post_lead: PostLead, decision: str, **form: Any) -> dict[str, Any]:
    lead_id = post_company_lead(post_lead, "harbor", name="Daniel Reyes")
    submit_decision(await_approval(lead_id), decision, **form)
    return final_row(lead_id)


def test_approved_email_is_sent_and_everything_is_recorded(
    post_lead: PostLead, mock: httpx.Client, mailpit: httpx.Client, env: dict[str, str]
) -> None:
    row = approve_harbor(post_lead, "Approve")
    email = row["email"]
    assert row["status"] == "approved_sent"
    assert email.startswith("daniel.reyes+") and email.endswith("@harborlogistics.example")
    assert row["email_sent_at"]

    [message] = emails_to(mailpit, email)
    assert message["Subject"] == "Your shipment-tracking portal"
    assert "https://northwind.example/book" in message["Text"]
    assert message["From"]["Address"] in env["EMAIL_FROM"]
    assert row["sent_email"]["subject"] == message["Subject"]

    crm = crm_for(mock, email)
    contact = crm["contact"]["properties"]
    assert (contact["ai_lead_score"], contact["ai_lead_tier"]) == ("87", "hot")
    assert contact["ai_score_reasons"].startswith("87/100 (hot)\nIndustry fit: 3/3")
    assert (contact["firstname"], contact["lastname"]) == ("Daniel", "Reyes")
    [(company_id, company)] = crm["companies"].items()
    assert company == {"name": "Harbor Logistics", "domain": "harborlogistics.example"}
    assert company_id == row["crm"]["company_id"]

    [note] = crm["notes"]
    body = note["properties"]["hs_note_body"]
    assert "Email sent, approved by Sara Chen" in body
    assert "https://news.example/harbor-cold-chain" in body  # sources
    assert "Subject: Your shipment-tracking portal" in body  # the sent email
    assert {a["to"]["id"] for a in note["associations"]} == {row["crm"]["contact_id"], company_id}

    [task] = crm["tasks"]
    days = (int(task["properties"]["hs_timestamp"]) / 1000 - time.time()) / 86400
    assert 2.9 < days < 3.1  # FOLLOW_UP_DAYS=3
    assert task["properties"]["hs_task_subject"] == "Follow up with Daniel Reyes (Harbor Logistics)"
    assert task["properties"]["hs_task_priority"] == "HIGH"

    slack = slack_for(mock, row["lead_id"])
    [request] = slack["requests"]
    [update] = slack["updates"]
    assert update["channel"] == request["channel"] == "C0APPROVALS"
    assert ":white_check_mark: Approved by Sara Chen" in update["text"]


def test_approve_with_edits_sends_the_edited_email(
    post_lead: PostLead, mock: httpx.Client, mailpit: httpx.Client
) -> None:
    edited = "Hi Daniel,\n\nEdited by Sara. https://northwind.example/book\n\nBest regards"
    row = approve_harbor(post_lead, "Approve with edits", subject="Your portal", body=edited)
    [message] = emails_to(mailpit, row["email"])
    assert message["Subject"] == "Your portal"
    assert "Edited by Sara." in message["Text"]
    [update] = slack_for(mock, row["lead_id"])["updates"]
    assert ":pencil2: Approved with edits by Sara Chen" in update["text"]
    assert row["decision"]["outcome"] == "approved_edited"


def test_rejected_reply_is_not_sent_but_recorded(
    post_lead: PostLead, mock: httpx.Client, mailpit: httpx.Client
) -> None:
    row = approve_harbor(post_lead, "Reject", reason="Existing customer")
    assert row["status"] == "rejected_by_reviewer"
    assert row["sent_email"] is None and row["email_sent_at"] is None
    assert emails_to(mailpit, row["email"]) == []
    crm = crm_for(mock, row["email"])
    assert crm["tasks"] == []
    [note] = crm["notes"]
    assert "Reply rejected by Sara Chen: Existing customer" in note["properties"]["hs_note_body"]
    [update] = slack_for(mock, row["lead_id"])["updates"]
    assert ":x: Rejected by Sara Chen: Existing customer" in update["text"]


def test_timeout_creates_a_manual_follow_up_task_due_now(
    post_lead: PostLead, mock: httpx.Client, mailpit: httpx.Client
) -> None:
    lead_id = post_company_lead(post_lead, "harbor")
    await_approval(lead_id)
    row = final_row(lead_id, timeout=150)  # 72 s window in the test stack
    assert row["status"] == "needs_manual_follow_up"
    assert emails_to(mailpit, row["email"]) == []
    [task] = crm_for(mock, row["email"])["tasks"]
    assert task["properties"]["hs_task_subject"].startswith("Manual follow-up: Test Person")
    assert abs(int(task["properties"]["hs_timestamp"]) / 1000 - time.time()) < 300
    [update] = slack_for(mock, lead_id)["updates"]
    assert ":hourglass: No decision in time" in update["text"]


def test_existing_contact_is_updated_not_duplicated(
    post_lead: PostLead, mock: httpx.Client
) -> None:
    email = f"repeat+{uuid.uuid4().hex[:8]}@harborlogistics.example"
    first = final_row(post_company_lead(post_lead, "harbor", _eval=True, email=email))
    again = "A second project: a supplier portal."
    second = final_row(
        post_company_lead(post_lead, "harbor", _eval=True, email=email, message=again)
    )
    assert first["crm"]["contact_created"] is True and second["crm"]["contact_created"] is False
    assert first["crm"]["contact_id"] == second["crm"]["contact_id"]
    assert first["crm"]["company_id"] == second["crm"]["company_id"]
    assert second["crm"]["company_created"] is False
    crm = crm_for(mock, email)
    assert len(crm["notes"]) == 2
    assert crm["contact"]["properties"]["ai_lead_tier"] == "hot"
    contacts = [e for e in mock.get("/_control/hubspot").json()["contacts"] if e == email]
    assert contacts == [email]


def test_cold_lead_is_recorded_in_hubspot_without_email_or_slack(
    post_lead: PostLead, mock: httpx.Client, mailpit: httpx.Client
) -> None:
    row = final_row(post_company_lead(post_lead, "unknown"))
    assert row["status"] == "cold_recorded"
    crm = crm_for(mock, row["email"])
    contact = crm["contact"]["properties"]
    assert (contact["ai_lead_tier"], contact["ai_lead_score"]) == ("cold", "33")
    assert crm["tasks"] == []
    assert "Cold lead: no email drafted." in crm["notes"][0]["properties"]["hs_note_body"]
    assert row["slack_ts"] is None
    assert slack_for(mock, row["lead_id"]) == {
        "requests": [], "reminders": [], "updates": [], "alerts": []}  # fmt: skip
    assert emails_to(mailpit, row["email"]) == []


def test_demo_mode_redirects_mail_for_addresses_outside_the_allow_list(
    post_lead: PostLead, mock: httpx.Client, mailpit: httpx.Client
) -> None:
    row = final_row(post_company_lead(post_lead, "coastline", _eval=True))
    email = row["email"]
    assert email.endswith("@gmail.com")
    assert emails_to(mailpit, email) == []
    [message] = [m for m in emails_to(mailpit, "demo-inbox@example.test")
                 if m["Subject"].startswith(f"[demo for {email}] ")]  # fmt: skip
    assert row["sent_email"]["redirected_from"] == email
    # No company domain for a personal email: the company is matched by name.
    assert list(crm_for(mock, email)["companies"].values()) == [{"name": "Coastline Clinics"}]
    assert message["Subject"].endswith("Booking portal for Coastline Clinics")


def test_daily_digest_lists_cold_leads_and_purges_expired_rows(
    post_lead: PostLead, mock: httpx.Client, ops: Callable[..., httpx.Response]
) -> None:
    name = f"Frosty {uuid.uuid4().hex[:6]} Ltd"
    cold = final_row(post_company_lead(post_lead, "unknown", company=name))
    sql("INSERT INTO leads (lead_id, lead_hash, source, status, name, email, received_at) VALUES "
        "('ld_expired_test', 'x', 'webhook', 'cold_recorded', 'Old Lead', 'old@example.test', "
        "now() - interval '45 days')")  # fmt: skip
    result = ops("run_digest").json()
    assert result["ok"] is True and result["posted"] is True
    assert result["cold_leads"] >= 1
    assert f"{name} · 33/100" in result["text"]
    assert result["leads_purged"] >= 1
    assert sql("SELECT count(*) FROM leads WHERE lead_id = 'ld_expired_test'") == [["0"]]
    assert sql(f"SELECT count(*) FROM leads WHERE lead_id = '{cold['lead_id']}'") == [["1"]]
    [digest] = [p for p in slack_posts(mock) if name in p.get("text", "")]
    assert digest["channel"] == "C0APPROVALS" and digest["text"].startswith(":snowflake:")


def test_slack_outage_leaves_the_lead_recoverable(post_lead: PostLead, mock: httpx.Client) -> None:
    """A failed approval post (after 3 tries) must not count as posted: the lead stops and
    the error workflow marks it error_recoverable."""
    mock.post("/_control/fail", json={"service": "slack", "times": 20, "status": 500})
    lead_id = post_company_lead(post_lead, "harbor")

    def recoverable() -> list[list[str]]:
        return sql(
            "SELECT status, coalesce(slack_ts, 'none') FROM leads "
            f"WHERE lead_id = '{lead_id}' AND status = 'error_recoverable'"
        )

    assert wait_for(recoverable, 60) == [["error_recoverable", "none"]]
    # This lead's approval request links to its own form: form-waiting/<pipeline execution id>.
    execution = sql(f"SELECT pipeline_execution_id FROM leads WHERE lead_id = '{lead_id}'")[0][0]
    approvals = [
        c for c in mock.get("/_control/calls").json()
        if c["service"] == "slack" and f"form-waiting/{execution}?" in json.loads(c["body"])["text"]
    ]  # fmt: skip
    assert len(approvals) == 3  # three tries, then the lead stops
