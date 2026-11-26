"""M4 – reply draft and human approval in Slack (approve / edit / reject / timeout, reminder)."""

from __future__ import annotations

import json
import time
from collections.abc import Callable

import httpx
import pytest

from tests.e2e.conftest import (
    PostLead,
    await_approval,
    decision_of,
    post_company_lead,
    slack_for,
    sql,
    submit_decision,
    wait_for,
)

pytestmark = pytest.mark.e2e


def test_hot_lead_reaches_slack_with_score_reasons_sources_and_draft(
    post_lead: PostLead, mock: httpx.Client
) -> None:
    started = time.monotonic()
    lead_id = post_company_lead(post_lead, "harbor", name="Daniel Reyes")
    url = await_approval(lead_id)
    assert time.monotonic() - started < 60  # spec: in Slack within about a minute

    [post] = slack_for(mock, lead_id)["requests"]
    assert post["channel"] == "C0APPROVALS"
    text = json.dumps(post["blocks"], ensure_ascii=False)
    assert "New lead: Daniel Reyes – Harbor Logistics" in text
    assert "87/100 · HOT" in text
    assert "Industry fit* 3/3 (25 of 25)" in text  # per-criterion score and reason
    assert "harborlogistics.example/about" in text  # sources
    assert "Your shipment-tracking portal" in text  # draft subject
    assert "https://northwind.example/book" in text  # draft body with booking link
    button = next(b for b in post["blocks"] if b["type"] == "actions")["elements"][0]
    assert button["url"] == url
    assert "form-waiting" in url


def test_draft_is_stored_with_its_sources_and_no_flags(
    post_lead: PostLead, mock: httpx.Client
) -> None:
    lead_id = post_company_lead(post_lead, "harbor")
    await_approval(lead_id)
    draft = json.loads(sql(f"SELECT draft FROM leads WHERE lead_id = '{lead_id}'")[0][0])
    assert draft["flags"] == []
    assert {f["source"] for f in draft["facts_used"]} == {
        "form: message", "https://news.example/harbor-cold-chain"}  # fmt: skip


def test_risky_draft_is_flagged_for_the_reviewer(post_lead: PostLead, mock: httpx.Client) -> None:
    lead_id = post_company_lead(post_lead, "coastline")
    await_approval(lead_id)
    flags = json.loads(sql(f"SELECT draft->'flags' FROM leads WHERE lead_id = '{lead_id}'")[0][0])
    assert flags == [
        'forbidden phrase: "we have helped companies like yours"',
        'figure not found in the message or research: "30%"',
        "cites a page that was not researched: https://invented.example/case-study",
        "booking link was missing and has been added",
    ]
    text = json.dumps(slack_for(mock, lead_id)["requests"][0]["blocks"])
    assert "Check before approving" in text and "30%" in text


def test_approve(post_lead: PostLead, mock: httpx.Client) -> None:
    lead_id = post_company_lead(post_lead, "harbor")
    assert submit_decision(await_approval(lead_id), "Approve").status_code == 200
    decision = decision_of(lead_id)
    assert (decision["outcome"], decision["approver"]) == ("approved", "Sara Chen")
    assert decision["subject"] == "Your shipment-tracking portal"


def test_approve_with_edits_keeps_the_edited_email(post_lead: PostLead, mock: httpx.Client) -> None:
    lead_id = post_company_lead(post_lead, "harbor")
    edited = "Hi Daniel,\n\nShort edited reply. https://northwind.example/book\n\nBest regards"
    submit_decision(await_approval(lead_id), "Approve with edits", subject="Portal", body=edited)
    decision = decision_of(lead_id)
    assert decision["outcome"] == "approved_edited"
    assert (decision["subject"], decision["body"]) == ("Portal", edited)


def test_reject_keeps_the_reason(post_lead: PostLead, mock: httpx.Client) -> None:
    lead_id = post_company_lead(post_lead, "harbor")
    submit_decision(await_approval(lead_id), "Reject", reason="Existing customer")
    decision = decision_of(lead_id)
    assert (decision["outcome"], decision["reject_reason"]) == ("rejected", "Existing customer")


def test_no_decision_times_out_to_manual_follow_up(post_lead: PostLead, mock: httpx.Client) -> None:
    # The test stack sets APPROVAL_TIMEOUT_HOURS=0.02 (72 s) instead of 24 h.
    lead_id = post_company_lead(post_lead, "harbor")
    await_approval(lead_id)
    decision = decision_of(lead_id, timeout=150)
    assert (decision["outcome"], decision["approver"]) == ("timeout", "")


def test_reminder_is_posted_once_in_the_thread(
    post_lead: PostLead, mock: httpx.Client, ops: Callable[..., httpx.Response]
) -> None:
    # The test stack sets APPROVAL_REMINDER_HOURS=0.004 (about 15 s).
    lead_id = post_company_lead(post_lead, "harbor")
    await_approval(lead_id)
    time.sleep(16)
    # Other tests' leads may be overdue too, so count only this lead's reminders.
    assert ops("run_reminders").json()["processed"] >= 1
    slack = slack_for(mock, lead_id)
    [request] = slack["requests"]
    [reminder] = slack["reminders"]
    assert reminder["text"].startswith(":alarm_clock: Reminder: still waiting for a decision")
    assert request["text"].split("Review: ")[1] in reminder["text"]  # same form link
    ops("run_reminders")
    assert len(slack_for(mock, lead_id)["reminders"]) == 1  # reminded once


def test_cold_lead_gets_no_draft_and_no_approval_request(
    post_lead: PostLead, mock: httpx.Client
) -> None:
    lead_id = post_company_lead(post_lead, "unknown")

    def scored() -> list[list[str]]:
        return sql(
            f"SELECT tier, draft FROM leads WHERE lead_id = '{lead_id}' AND tier IS NOT NULL"
        )

    time.sleep(3)  # let the pipeline finish after scoring
    assert wait_for(scored)[0] == ["cold", ""]
    assert slack_for(mock, lead_id)["requests"] == []
    assert sql(f"SELECT coalesce(slack_ts, 'none') FROM leads WHERE lead_id = '{lead_id}'") == [
        ["none"]
    ]


def test_eval_lead_is_auto_approved_without_slack(post_lead: PostLead, mock: httpx.Client) -> None:
    lead_id = post_company_lead(post_lead, "harbor", _eval=True)
    decision = decision_of(lead_id)
    assert (decision["outcome"], decision["approver"]) == ("approved", "eval auto-approve")
    assert sql(f"SELECT coalesce(slack_ts, 'none') FROM leads WHERE lead_id = '{lead_id}'") == [
        ["none"]
    ]


def test_ops_webhook_needs_the_token_and_a_known_action(
    ops: Callable[..., httpx.Response],
) -> None:
    assert ops("run_reminders", token="wrong").status_code == 403
    res = ops("explode")
    assert res.status_code == 400
    assert res.json()["error"] == "unknown action"
