"""Failure paths found in review: resume without re-sending, nothing lost after a decision,
non-fatal Slack outcome update, no research without a company, escaping, retention."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable

import httpx
import pytest

from tests.e2e.conftest import (
    PostLead,
    await_approval,
    calls,
    crm_for,
    emails_to,
    fail,
    final_row,
    lead_email,
    post_company_lead,
    slack_for,
    sql,
    submit_decision,
    wait_for,
)

pytestmark = pytest.mark.e2e


def recoverable(lead_id: str, timeout: float = 90) -> dict[str, object]:
    def row() -> list[list[str]]:
        return sql(
            "SELECT row_to_json(l) FROM leads l "
            f"WHERE lead_id = '{lead_id}' AND status = 'error_recoverable'"
        )

    result: dict[str, object] = json.loads(wait_for(row, timeout)[0][0])
    return result


def test_replay_after_a_crm_outage_resumes_without_sending_the_email_again(
    post_lead: PostLead, mock: httpx.Client, mailpit: httpx.Client,
    ops: Callable[..., httpx.Response],
) -> None:  # fmt: skip
    lead_id = post_company_lead(post_lead, "harbor")
    url = await_approval(lead_id)
    # The CRM step fails (only for this lead) after the email has gone out.
    fail(mock, "hubspot", 3, match=lead_email(lead_id))
    submit_decision(url, "Approve")
    stuck = recoverable(lead_id)
    assert stuck["email_sent_at"] and stuck["completed_at"] is None
    email = str(stuck["email"])
    assert len(emails_to(mailpit, email)) == 1

    res = ops("replay", lead_id=lead_id)
    assert res.status_code == 202 and res.json()["mode"] == "resume"
    row = final_row(lead_id)
    assert row["status"] == "approved_sent"
    assert len(emails_to(mailpit, email)) == 1  # not sent again
    assert crm_for(mock, email)["contact"] is not None
    assert len(slack_for(mock, lead_id)["requests"]) == 1  # no second approval request


def test_timed_out_lead_with_a_crm_outage_is_not_lost(
    post_lead: PostLead, mock: httpx.Client, ops: Callable[..., httpx.Response]
) -> None:
    lead_id = post_company_lead(post_lead, "harbor")
    await_approval(lead_id)
    fail(mock, "hubspot", 3, match=lead_email(lead_id))
    stuck = recoverable(lead_id, timeout=150)  # 72 s approval window, then the CRM fails
    assert stuck["decision"]["outcome"] == "timeout"  # type: ignore[index]
    assert ops("replay", lead_id=lead_id).json()["mode"] == "resume"
    row = final_row(lead_id)
    assert row["status"] == "needs_manual_follow_up"
    [task] = crm_for(mock, row["email"])["tasks"]
    assert task["properties"]["hs_task_subject"].startswith("Manual follow-up:")


def test_failed_slack_outcome_update_does_not_stop_the_lead(
    post_lead: PostLead, mock: httpx.Client, mailpit: httpx.Client
) -> None:
    lead_id = post_company_lead(post_lead, "harbor")
    url = await_approval(lead_id)
    ts = sql(f"SELECT slack_ts FROM leads WHERE lead_id = '{lead_id}'")[0][0]
    fail(mock, "slack", 3, match=ts)  # this lead's chat.update fails all three tries
    submit_decision(url, "Approve")
    row = final_row(lead_id)
    assert row["status"] == "approved_sent"
    assert "Slack outcome update failed" in row["error"]
    assert len(emails_to(mailpit, row["email"])) == 1


def test_lead_without_company_or_website_is_not_researched(
    post_lead: PostLead, mock: httpx.Client
) -> None:
    email = f"someone+{uuid.uuid4().hex[:8]}@gmail.com"
    lead_id = post_company_lead(post_lead, "unknown", company="", website="", email=email)
    row = final_row(lead_id)
    assert row["enrichment_status"] == "failed"
    assert row["enrichment"]["note"] == "no company or website given – scored on form data only"
    searches = [c for c in mock.get("/_control/calls").json() if c["service"] == "tavily_search"]
    assert not any('\\"\\" company' in c["body"] for c in searches)


def test_digest_escapes_lead_supplied_text(
    post_lead: PostLead, mock: httpx.Client, ops: Callable[..., httpx.Response]
) -> None:
    tag = uuid.uuid4().hex[:6]
    final_row(post_company_lead(post_lead, "unknown", name=f"<!channel> {tag}",
                                company=f"<https://phish.example|Open {tag}>"))  # fmt: skip
    text = ops("run_digest").json()["text"]
    assert f"&lt;!channel&gt; {tag}" in text
    assert f"&lt;https://phish.example|Open {tag}&gt;" in text
    assert "<!channel>" not in text


def test_retention_purge_runs_even_when_the_digest_post_fails(
    post_lead: PostLead, mock: httpx.Client, ops: Callable[..., httpx.Response]
) -> None:
    final_row(post_company_lead(post_lead, "unknown"))  # something to post
    expired = "('ld_expired_purge', 'x', 'webhook', 'cold_recorded', now() - interval '45 days')"
    sql(f"INSERT INTO leads (lead_id, lead_hash, source, status, received_at) VALUES {expired}")
    fail(mock, "slack", 10)
    assert ops("run_digest").status_code >= 500  # the post failed...
    assert sql("SELECT count(*) FROM leads WHERE lead_id = 'ld_expired_purge'") == [
        ["0"]
    ]  # ...the purge ran
    assert calls(mock, "slack") >= 1
