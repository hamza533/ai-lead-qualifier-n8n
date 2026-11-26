from __future__ import annotations

import json
from typing import Any

import pytest

from scripts.n8n_admin import WORKFLOWS_DIR, activation_order, referenced_workflows


def _wf(wid: str, *calls: str, error: str | None = None) -> dict[str, Any]:
    nodes = [
        {"type": "n8n-nodes-base.executeWorkflow",
         "parameters": {"workflowId": {"__rl": True, "mode": "id", "value": target}}}
        for target in calls
    ]  # fmt: skip
    return {"id": wid, "nodes": nodes, "settings": {"errorWorkflow": error} if error else {}}


def _ids(workflows: list[dict[str, Any]]) -> list[str]:
    return [w["id"] for w in workflows]


def test_sub_workflows_are_activated_before_their_callers() -> None:
    # "aMain" sorts before "zSub" alphabetically: the order must come from the reference.
    order = _ids(activation_order([_wf("aMain", "zSub"), _wf("zSub")]))
    assert order.index("zSub") < order.index("aMain")


def test_call_chains_are_ordered() -> None:
    workflows = [
        _wf("intake", "validate", "pipeline", error="errors"),
        _wf("pipeline", "enrich", error="errors"),
        _wf("enrich", error="errors"),
        _wf("validate", error="errors"),
        _wf("errors", "alert"),
        _wf("alert", error="errors"),
    ]
    order = _ids(activation_order(workflows))
    assert order.index("enrich") < order.index("pipeline") < order.index("intake")
    assert order.index("validate") < order.index("intake")
    assert order.index("alert") < order.index("errors")


def test_error_workflow_setting_is_not_a_dependency() -> None:
    """The error handler calls sub-alert, whose error workflow is the error handler."""
    assert referenced_workflows(_wf("alert", error="errors")) == set()


def test_reference_cycle_is_reported() -> None:
    with pytest.raises(SystemExit, match="cycle"):
        activation_order([_wf("a", "b"), _wf("b", "a")])


def test_unknown_references_are_ignored() -> None:
    assert _ids(activation_order([_wf("a", "not-exported")])) == ["a"]


def test_committed_workflows_have_a_valid_activation_order() -> None:
    workflows = [json.loads(p.read_text(encoding="utf-8")) for p in WORKFLOWS_DIR.glob("*.json")]
    order = _ids(activation_order(workflows))
    for workflow in workflows:
        for dep in referenced_workflows(workflow) & set(order):
            assert order.index(dep) < order.index(workflow["id"]), (workflow["id"], dep)
