"""DRY_RUN=true: the pipeline runs fully, but nothing is posted, sent or written to HubSpot.

Runs on the dry-run stack only: make test-e2e-dryrun.
"""

from __future__ import annotations

import httpx
import pytest

from tests.e2e.conftest import (
    PostLead,
    await_approval,
    final_row,
    hubspot,
    post_company_lead,
    submit_decision,
)

pytestmark = pytest.mark.dryrun


def _no_external_writes(mock: httpx.Client, mailpit: httpx.Client) -> None:
    services = {c["service"] for c in mock.get("/_control/calls").json()}
    assert "slack" not in services and "hubspot" not in services
    assert hubspot(mock)["contacts"] == {}
    assert mailpit.get("/api/v1/messages").json()["messages_count"] == 0


def test_approved_lead_writes_nothing_and_records_every_skipped_call(
    post_lead: PostLead, mock: httpx.Client, mailpit: httpx.Client
) -> None:
    lead_id = post_company_lead(post_lead, "harbor")
    submit_decision(await_approval(lead_id), "Approve")
    row = final_row(lead_id)
    assert row["status"] == "approved_sent"
    assert row["email_sent_at"] is None
    assert row["crm"] == {"dry_run": True}
    assert [a["type"] for a in row["dry_run_actions"]] == [
        "slack.chat.postMessage",
        "smtp.send",
        "hubspot.contacts.upsert",
        "hubspot.companies.find_or_create",
        "hubspot.notes.create",
        "hubspot.tasks.create",
        "slack.chat.update",
    ]
    email = next(a for a in row["dry_run_actions"] if a["type"] == "smtp.send")["body"]
    assert email["to"] == row["email"]
    _no_external_writes(mock, mailpit)


def test_cold_lead_dry_run_records_the_hubspot_calls_only(
    post_lead: PostLead, mock: httpx.Client, mailpit: httpx.Client
) -> None:
    row = final_row(post_company_lead(post_lead, "unknown"))
    assert row["status"] == "cold_recorded"
    assert [a["type"] for a in row["dry_run_actions"]] == [
        "hubspot.contacts.upsert",
        "hubspot.companies.find_or_create",
        "hubspot.notes.create",
    ]
    _no_external_writes(mock, mailpit)
