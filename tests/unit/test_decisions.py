"""Reading the reviewer's decision (workflows/main-lead-intake.json › "Read decision")."""

from __future__ import annotations

from typing import Any

import pytest

from tests.unit.n8n_code import NODE, node_code, run_node

pytestmark = pytest.mark.skipif(NODE is None, reason="Node.js not installed")
DRAFT = {"subject": "Your portal", "body": "Hi Daniel,\n\nDraft body.\n\nBest regards"}


def decide(answer: dict[str, Any], mode: str = "live") -> dict[str, Any]:
    case = {"nodes": {"Draft reply": DRAFT, "Build approval request": {"mode": mode}},
            "input": answer}  # fmt: skip
    result = run_node(node_code("main-lead-intake.json", "Read decision"), [case])[0]
    assert "ok" in result, result
    out: dict[str, Any] = result["ok"][0]
    return out


def form(decision: str, **fields: str) -> dict[str, str]:
    """Answers as the Wait node returns them: keyed by field label."""
    return {"Your name": "Sara Chen", "Decision": decision, "Email subject": DRAFT["subject"],
            "Email body": DRAFT["body"], "Reason (only if rejecting)": "", **fields}  # fmt: skip


def test_approve_sends_the_draft_as_it_is() -> None:
    out = decide(form("Approve"))
    assert (out["outcome"], out["approver"]) == ("approved", "Sara Chen")
    assert (out["subject"], out["body"]) == (DRAFT["subject"], DRAFT["body"])


def test_approve_with_edits_sends_the_edited_text() -> None:
    out = decide(form("Approve with edits", **{"Email body": "New body"}))
    assert out["outcome"] == "approved_edited"
    assert out["body"] == "New body"


def test_any_change_counts_as_an_edit_even_with_plain_approve() -> None:
    out = decide(form("Approve", **{"Email subject": "Changed subject"}))
    assert out["outcome"] == "approved_edited"
    assert out["subject"] == "Changed subject"


def test_emptied_fields_fall_back_to_the_draft() -> None:
    out = decide(form("Approve with edits", **{"Email body": "  ", "Email subject": ""}))
    assert (out["subject"], out["body"]) == (DRAFT["subject"], DRAFT["body"])


def test_reject_keeps_the_reason() -> None:
    out = decide(form("Reject", **{"Reason (only if rejecting)": "Not a fit"}))
    assert (out["outcome"], out["reject_reason"]) == ("rejected", "Not a fit")


def test_reject_without_a_reason_gets_a_default() -> None:
    assert decide(form("Reject"))["reject_reason"] == "No reason given"


def test_no_answer_is_a_timeout() -> None:
    out = decide({"lead_id": "ld_test"})  # the Wait node passes its input through on timeout
    assert (out["outcome"], out["approver"]) == ("timeout", "")


def test_eval_mode_is_auto_approved() -> None:
    out = decide({"lead_id": "ld_test"}, mode="auto")
    assert (out["outcome"], out["approver"]) == ("approved", "eval auto-approve")


def test_answers_keyed_by_field_name_are_accepted_too() -> None:
    answer = {"reviewer": "Sam", "decision": "Reject", "reject_reason": "Duplicate"}
    assert decide(answer)["reject_reason"] == "Duplicate"
