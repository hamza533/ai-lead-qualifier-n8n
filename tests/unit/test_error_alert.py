"""Alerts: error-handler.json › "Describe failure" and sub-alert.json › "Format alert"."""

from __future__ import annotations

from typing import Any

import pytest

from tests.unit.n8n_code import NODE, node_code, run_node

pytestmark = pytest.mark.skipif(NODE is None, reason="Node.js not installed")

EVENT = {
    "workflow": {"id": "lpMainIntake0001", "name": "LeadPilot – Main lead pipeline"},
    "execution": {"id": "42", "url": "https://n8n.example/workflow/x/executions/42",
                  "lastNodeExecuted": "Score lead",
                  "error": {"message": "Service unavailable"}},
}  # fmt: skip
LEAD = {"lead_id": "ld_1", "email": "daniel.reyes@harborlogistics.example"}


def describe(event: dict[str, Any], lead: dict[str, Any]) -> dict[str, Any]:
    case = {"nodes": {"Error Trigger": event}, "input": lead}
    result = run_node(node_code("error-handler.json", "Describe failure"), [case])[0]
    assert "ok" in result, result
    out: dict[str, Any] = result["ok"][0]
    return out


def fmt(alert: dict[str, Any]) -> dict[str, Any]:
    case = {"input": alert, "env": {"SLACK_ALERTS_CHANNEL": "C0ALERTS"}}
    result = run_node(node_code("sub-alert.json", "Format alert"), [case])[0]
    assert "ok" in result, result
    out: dict[str, Any] = result["ok"][0]
    return out


def test_failure_alert_masks_the_email_and_explains_how_to_replay() -> None:
    out = fmt(describe(EVENT, LEAD))
    assert out["masked_email"] == "d***@harborlogistics.example"
    text = out["slack"]["text"]
    assert text.startswith(":rotating_light: *LeadPilot failure*")
    assert "daniel.reyes" not in text
    assert "LeadPilot – Main lead pipeline › Score lead" in text
    assert '{"action": "replay", "lead_id": "ld_1"}' in text
    assert "<https://n8n.example/workflow/x/executions/42|Open the execution in n8n>" in text
    assert out["slack"]["channel"] == "C0ALERTS"
    assert out["level"] == "error"


def test_failure_without_a_lead_still_reports() -> None:
    out = fmt(describe(EVENT, {}))
    assert out["lead_id"] is None and out["masked_email"] is None
    assert "No lead is attached to this execution." in out["slack"]["text"]


def test_sub_workflow_failures_are_left_to_their_caller() -> None:
    event = {**EVENT, "workflow": {"id": "lpSubScore000001", "name": "LeadPilot – Sub: score"}}
    assert describe(event, {})["skip"] is True
    assert describe(EVENT, {})["skip"] is False


def test_trigger_errors_are_reported_too() -> None:
    event = {"workflow": {"id": "lpIntakeWebhook1", "name": "Intake"},
             "trigger": {"error": {"message": "Bad webhook config"}}}  # fmt: skip
    out = describe(event, {})
    assert out["message"] == "Bad webhook config"
    assert out["execution_id"] is None


def test_warning_says_the_lead_continued_and_has_no_replay_hint() -> None:
    out = fmt({**LEAD, "level": "warning", "workflow": "Pipeline", "node": "Enrich company",
               "message": "Research degraded (failed): tavily: 503",
               "note": "The lead continued: scored on form data only."})  # fmt: skip
    text = out["slack"]["text"]
    assert text.startswith(":warning: *LeadPilot warning*")
    assert "The lead continued" in text and "replay" not in text
    assert out["level"] == "warning"
