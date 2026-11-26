"""M6 – failures: retries, the error workflow, alerts, recoverable status and replay."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from tests.e2e.conftest import (
    PostLead,
    fail,
    final_row,
    gemini_calls,
    post_company_lead,
    slack_for,
    sql,
    wait_for,
)

pytestmark = pytest.mark.e2e


def recoverable(lead_id: str) -> dict[str, str]:
    def row() -> list[list[str]]:
        return sql(
            "SELECT row_to_json(l) FROM leads l "
            f"WHERE lead_id = '{lead_id}' AND status = 'error_recoverable'"
        )

    result: dict[str, str] = json.loads(wait_for(row, 90)[0][0])
    return result


def alerts_for(lead_id: str) -> list[dict[str, Any]]:
    query = f"SELECT row_to_json(a) FROM alerts a WHERE lead_id = '{lead_id}' ORDER BY id"
    return [json.loads(r[0]) for r in sql(query)]


def test_model_outage_retries_then_alerts_and_leaves_the_lead_recoverable(
    post_lead: PostLead, mock: httpx.Client
) -> None:
    fail(mock, "gemini:score", 3)  # all three tries fail, then the mock recovers
    lead_id = post_company_lead(post_lead, "harbor", _eval=True)
    row = recoverable(lead_id)
    assert gemini_calls(mock, "score") == 3
    assert "Service unavailable" in row["error"]
    assert row["enrichment_status"] == "ok"  # research done before the failure is kept

    [alert] = alerts_for(lead_id)
    assert alert["workflow"] == "LeadPilot – Main lead pipeline"
    assert alert["node"] == "Score lead"
    assert alert["masked_email"] == "d***@harborlogistics.example"
    assert alert["delivered"]
    assert f"/executions/{alert['execution_id']}" in str(alert["execution_url"])

    [message] = slack_for(mock, lead_id)["alerts"]
    assert message["text"].startswith(":rotating_light: *LeadPilot failure*")
    assert "d***@harborlogistics.example" in message["text"]
    assert "daniel.reyes@" not in message["text"]  # never the full address
    assert f'"lead_id": "{lead_id}"' in message["text"]  # how to replay


def test_one_failure_gives_one_alert(post_lead: PostLead, mock: httpx.Client) -> None:
    """The scoring sub-workflow and the pipeline both fail; only the pipeline reports."""
    fail(mock, "gemini:score", 3)
    lead_id = post_company_lead(post_lead, "harbor", _eval=True)
    recoverable(lead_id)
    wait_for(lambda: len(slack_for(mock, lead_id)["alerts"]) >= 1)
    time.sleep(5)  # give a second (duplicate) alert the chance to show up
    assert len(slack_for(mock, lead_id)["alerts"]) == 1
    assert sql("SELECT count(*) FROM alerts WHERE workflow LIKE '%Sub:%' "
               "AND created_at > now() - interval '2 minutes'") == [["0"]]  # fmt: skip


def test_recoverable_lead_can_be_replayed_once_the_service_is_back(
    post_lead: PostLead, mock: httpx.Client, ops: Callable[..., httpx.Response]
) -> None:
    fail(mock, "gemini:score", 3)
    lead_id = post_company_lead(post_lead, "harbor", _eval=True)
    recoverable(lead_id)
    res = ops("replay", lead_id=lead_id)
    assert res.status_code == 202
    assert res.json() == {"ok": True, "action": "replay", "lead_id": lead_id, "mode": "restart"}
    row = final_row(lead_id)
    assert (row["status"], row["score"], row["tier"]) == ("approved_sent", 87, "hot")
    assert row["error"] is None


def test_only_recoverable_leads_can_be_replayed(
    post_lead: PostLead, mock: httpx.Client, ops: Callable[..., httpx.Response]
) -> None:
    done = final_row(post_company_lead(post_lead, "unknown"))
    assert ops("replay", lead_id=done["lead_id"]).status_code == 409
    assert ops("replay", lead_id="ld_does_not_exist").status_code == 409


def test_research_outage_degrades_the_lead_and_sends_a_warning(
    post_lead: PostLead, mock: httpx.Client
) -> None:
    """Spec: forcing Tavily (or Gemini) to fail triggers retries and an alert; research
    failures don't stop the lead, so the alert is a warning and the lead carries on."""
    fail(mock, "tavily_search", 10)
    fail(mock, "gemini:profile", 10)
    row = final_row(post_company_lead(post_lead, "harbor", _eval=True))
    assert row["status"] == "approved_sent"
    assert row["enrichment_status"] == "failed"
    assert "injected tavily_search failure" in row["error"]
    [alert] = alerts_for(row["lead_id"])
    assert (alert["level"], alert["node"], alert["delivered"]) == (
        "warning",
        "Enrich company",
        True,
    )
    [message] = slack_for(mock, row["lead_id"])["alerts"]
    assert message["text"].startswith(":warning: *LeadPilot warning*")
    assert "The lead continued" in message["text"]
