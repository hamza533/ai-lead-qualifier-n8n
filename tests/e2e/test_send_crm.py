"""M5 – send the approved email, update HubSpot and Slack; cold leads and the daily digest."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from tests.e2e.conftest import (
    PostLead,
    await_approval,
    emails_to,
    final_row,
    hubspot,
    post_company_lead,
    slack_posts,
    sql,
    submit_decision,
)

pytestmark = pytest.mark.e2e
DANIEL = "daniel.reyes@harborlogistics.example"


def approve_harbor(post_lead: PostLead, decision: str, **form: Any) -> dict[str, Any]:
    lead_id = post_company_lead(post_lead, "harbor", name="Daniel Reyes")
    submit_decision(await_approval(lead_id), decision, **form)
    return final_row(lead_id)


def test_approved_email_is_sent_and_everything_is_recorded(
    post_lead: PostLead, mock: httpx.Client, mailpit: httpx.Client, env: dict[str, str]
) -> None:
    row = approve_harbor(post_lead, "Approve")
    assert row["status"] == "approved_sent"
    assert row["email"] == DANIEL  # the lead's address is untouched
    assert row["email_sent_at"]

    [message] = emails_to(mailpit, DANIEL)
    assert message["Subject"] == "Your shipment-tracking portal"
    assert "https://northwind.example/book" in message["Text"]
    assert message["From"]["Address"] in env["EMAIL_FROM"]
    assert row["sent_email"]["subject"] == message["Subject"]

    state = hubspot(mock)
    contact = state["contacts"][DANIEL]["properties"]
    assert (contact["ai_lead_score"], contact["ai_lead_tier"]) == ("87", "hot")
    assert contact["ai_score_reasons"].startswith("87/100 (hot)\nIndustry fit: 3/3")
    assert (contact["firstname"], contact["lastname"]) == ("Daniel", "Reyes")
    [(company_id, company)] = state["companies"].items()
    assert company == {"name": "Harbor Logistics", "domain": "harborlogistics.example"}
    assert state["associations"] == [[row["crm"]["contact_id"], company_id]]

    [note] = state["notes"]
    body = note["properties"]["hs_note_body"]
    assert "Email sent, approved by Sara Chen" in body
    assert "https://news.example/harbor-cold-chain" in body  # sources
    assert "Subject: Your shipment-tracking portal" in body  # the sent email
    assert {a["to"]["id"] for a in note["associations"]} == {row["crm"]["contact_id"], company_id}

    [task] = state["tasks"]
    days = (int(task["properties"]["hs_timestamp"]) / 1000 - time.time()) / 86400
    assert 2.9 < days < 3.1  # FOLLOW_UP_DAYS=3
    assert task["properties"]["hs_task_subject"] == "Follow up with Daniel Reyes (Harbor Logistics)"
    assert task["properties"]["hs_task_priority"] == "HIGH"

    [request] = slack_posts(mock)
    [update] = slack_posts(mock, "chat.update")
    assert update["ts"] == row["slack_ts"] and update["channel"] == request["channel"]
    assert ":white_check_mark: Approved by Sara Chen" in update["text"]


def test_approve_with_edits_sends_the_edited_email(
    post_lead: PostLead, mock: httpx.Client, mailpit: httpx.Client
) -> None:
    edited = "Hi Daniel,\n\nEdited by Sara. https://northwind.example/book\n\nBest regards"
    row = approve_harbor(post_lead, "Approve with edits", subject="Your portal", body=edited)
    [message] = emails_to(mailpit, DANIEL)
    assert message["Subject"] == "Your portal"
    assert "Edited by Sara." in message["Text"]
    assert (
        ":pencil2: Approved with edits by Sara Chen" in slack_posts(mock, "chat.update")[0]["text"]
    )
    assert row["decision"]["outcome"] == "approved_edited"


def test_rejected_reply_is_not_sent_but_recorded(
    post_lead: PostLead, mock: httpx.Client, mailpit: httpx.Client
) -> None:
    row = approve_harbor(post_lead, "Reject", reason="Existing customer")
    assert row["status"] == "rejected_by_reviewer"
    assert row["sent_email"] is None and row["email_sent_at"] is None
    assert emails_to(mailpit, DANIEL) == []
    state = hubspot(mock)
    assert state["tasks"] == []
    assert (
        "Reply rejected by Sara Chen: Existing customer"
        in state["notes"][0]["properties"]["hs_note_body"]
    )
    assert (
        ":x: Rejected by Sara Chen: Existing customer"
        in slack_posts(mock, "chat.update")[0]["text"]
    )


def test_timeout_creates_a_manual_follow_up_task_due_now(
    post_lead: PostLead, mock: httpx.Client, mailpit: httpx.Client
) -> None:
    lead_id = post_company_lead(post_lead, "harbor")
    await_approval(lead_id)
    row = final_row(lead_id, timeout=150)  # 72 s window in the test stack
    assert row["status"] == "needs_manual_follow_up"
    assert emails_to(mailpit, DANIEL) == []
    [task] = hubspot(mock)["tasks"]
    assert task["properties"]["hs_task_subject"].startswith("Manual follow-up: Test Person")
    assert abs(int(task["properties"]["hs_timestamp"]) / 1000 - time.time()) < 300
    assert ":hourglass: No decision in time" in slack_posts(mock, "chat.update")[0]["text"]


def test_existing_contact_is_updated_not_duplicated(
    post_lead: PostLead, mock: httpx.Client
) -> None:
    first = final_row(post_company_lead(post_lead, "harbor", _eval=True))
    again = "A second project: a supplier portal."
    second = final_row(post_company_lead(post_lead, "harbor", _eval=True, message=again))
    state = hubspot(mock)
    assert list(state["contacts"]) == [DANIEL]
    assert len(state["companies"]) == 1
    assert first["crm"]["contact_created"] is True and second["crm"]["contact_created"] is False
    assert first["crm"]["contact_id"] == second["crm"]["contact_id"]
    assert second["crm"]["company_created"] is False
    assert len(state["notes"]) == 2


def test_cold_lead_is_recorded_in_hubspot_without_email_or_slack(
    post_lead: PostLead, mock: httpx.Client, mailpit: httpx.Client
) -> None:
    row = final_row(post_company_lead(post_lead, "unknown"))
    assert row["status"] == "cold_recorded"
    contact = hubspot(mock)["contacts"]["a@nobody-knows.example"]["properties"]
    assert (contact["ai_lead_tier"], contact["ai_lead_score"]) == ("cold", "33")
    assert hubspot(mock)["tasks"] == []
    assert "Cold lead: no email drafted." in hubspot(mock)["notes"][0]["properties"]["hs_note_body"]
    assert slack_posts(mock) == []
    assert mailpit.get("/api/v1/messages").json()["messages_count"] == 0


def test_demo_mode_redirects_mail_for_addresses_outside_the_allow_list(
    post_lead: PostLead, mock: httpx.Client, mailpit: httpx.Client
) -> None:
    row = final_row(post_company_lead(post_lead, "coastline", _eval=True))
    assert emails_to(mailpit, "priya.natarajan@gmail.com") == []
    [message] = emails_to(mailpit, "demo-inbox@example.test")
    assert message["Subject"].startswith("[demo for priya.natarajan@gmail.com] ")
    assert row["sent_email"]["redirected_from"] == "priya.natarajan@gmail.com"
    # No company domain for a personal email: the company is matched by name.
    assert list(hubspot(mock)["companies"].values()) == [{"name": "Coastline Clinics"}]


def test_daily_digest_lists_cold_leads_and_purges_expired_rows(
    post_lead: PostLead, mock: httpx.Client, ops: Callable[..., httpx.Response]
) -> None:
    cold = final_row(post_company_lead(post_lead, "unknown", company="Frosty Ltd"))
    sql("INSERT INTO leads (lead_id, lead_hash, source, status, name, email, received_at) VALUES "
        "('ld_expired_test', 'x', 'webhook', 'cold_recorded', 'Old Lead', 'old@example.test', "
        "now() - interval '45 days')")  # fmt: skip
    result = ops("run_digest").json()
    assert result["ok"] is True and result["posted"] is True
    assert result["cold_leads"] >= 1
    assert "Frosty Ltd · 33/100" in result["text"]
    assert result["leads_purged"] >= 1
    assert sql("SELECT count(*) FROM leads WHERE lead_id = 'ld_expired_test'") == [["0"]]
    assert sql(f"SELECT count(*) FROM leads WHERE lead_id = '{cold['lead_id']}'") == [["1"]]
    digest = slack_posts(mock)[-1]
    assert digest["channel"] == "C0APPROVALS" and digest["text"].startswith(":snowflake:")


def test_slack_error_reply_stops_the_lead(post_lead: PostLead, mock: httpx.Client) -> None:
    """Slack answers HTTP 200 with ok=false on errors; that must not count as posted."""
    mock.post("/_control/fail", json={"service": "slack", "times": 10, "status": 500})
    lead_id = post_company_lead(post_lead, "harbor")
    time.sleep(25)  # 3 tries, 3 s apart
    assert sql(f"SELECT status, slack_ts FROM leads WHERE lead_id = '{lead_id}'")[0][1] == ""
    calls = [c for c in mock.get("/_control/calls").json() if c["service"] == "slack"]
    assert len(calls) == 3
    assert json.loads(calls[0]["body"])["channel"] == "C0APPROVALS"
