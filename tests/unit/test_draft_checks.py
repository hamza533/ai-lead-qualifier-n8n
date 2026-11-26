"""The code checks on every reply draft (workflows/sub-draft.json › "Check draft")."""

from __future__ import annotations

from typing import Any

import pytest

from tests.unit.n8n_code import NODE, ROOT, gemini_response, node_code, run_node

pytestmark = pytest.mark.skipif(NODE is None, reason="Node.js not installed")
STYLE = (ROOT / "config" / "reply_style.md").read_text(encoding="utf-8")
BOOKING = "https://northwind.example/book"
LEAD = {"lead_id": "ld_test", "message": "We need a customer portal by Q2. Budget $25-40k.",
        "budget_range": "$20k-$50k", "company": "Harbor Logistics"}  # fmt: skip
ENRICHMENT = {
    "sources": [{"url": "https://harborlogistics.example/about"}],
    "profile": {"size_estimate": {"value": "~180 employees"}},
}
GOOD_BODY = (
    "Hi Daniel,\n\nYou want a customer portal live by Q2, with a budget of $25-40k.\n\n"
    f"Could we have a 20-minute call? Pick a time here: {BOOKING}\n\n"
    "Best regards,\nThe Northwind Digital team"
)


def check(draft: dict[str, Any], **ctx: Any) -> dict[str, Any]:
    case = {
        "nodes": {
            "When called by the pipeline": {"lead": ctx.get("lead", LEAD),
                                            "enrichment": ctx.get("enrichment", ENRICHMENT)},
            "Extract reply style": {"style": STYLE},
        },
        "input": gemini_response(draft),
        "env": {"BOOKING_LINK": BOOKING},
    }  # fmt: skip
    result = run_node(node_code("sub-draft.json", "Check draft"), [case])[0]
    assert "ok" in result, result
    out: dict[str, Any] = result["ok"][0]
    return out


def draft(body: str = GOOD_BODY, **extra: Any) -> dict[str, Any]:
    return {"subject": "Your portal", "body": body, "facts_used": [], **extra}


def test_grounded_draft_has_no_flags() -> None:
    facts = [
        {"fact": "portal by Q2", "source": "form: message"},
        {"fact": "180 staff", "source": "https://harborlogistics.example/about"},
    ]
    out = check(draft(facts_used=facts))
    assert out["flags"] == []
    assert out["body"] == GOOD_BODY
    assert out["usage"] == {"llm_input_tokens": 120, "llm_output_tokens": 80}


def test_forbidden_phrase_from_the_style_guide_is_flagged() -> None:
    body = GOOD_BODY.replace("You want", "We are industry-leading. You want")
    assert 'forbidden phrase: "industry-leading"' in check(draft(body))["flags"]


def test_guarantee_is_flagged() -> None:
    body = GOOD_BODY.replace("You want", "We guarantee results. You want")
    assert "mentions a guarantee" in check(draft(body))["flags"]


@pytest.mark.parametrize("figure", ["30%", "$9,000", "£15k", "250 clients"])
def test_figures_not_in_the_message_or_research_are_flagged(figure: str) -> None:
    body = GOOD_BODY.replace("You want", f"We delivered {figure} before. You want")
    flags = check(draft(body))["flags"]
    assert any(f.startswith("figure not found") for f in flags), flags


@pytest.mark.parametrize("figure", ["$25-40k", "Q2", "180", "20-minute"])
def test_figures_from_the_message_research_or_style_guide_are_allowed(figure: str) -> None:
    body = GOOD_BODY.replace("You want", f"About {figure}. You want")
    assert check(draft(body))["flags"] == []


def test_citing_an_unresearched_page_is_flagged() -> None:
    out = check(draft(facts_used=[{"fact": "won an award", "source": "https://invented.example"}]))
    assert out["flags"] == ["cites a page that was not researched: https://invented.example"]


def test_missing_booking_link_is_added_before_the_sign_off() -> None:
    body = "Hi Daniel,\n\nThanks for your message.\n\nBest regards,\nThe Northwind Digital team"
    out = check(draft(body))
    assert out["flags"] == ["booking link was missing and has been added"]
    assert out["body"] == (
        "Hi Daniel,\n\nThanks for your message.\n\n"
        f"You can pick a time for a short call here: {BOOKING}\n\n"
        "Best regards,\nThe Northwind Digital team"
    )


def test_booking_link_goes_at_the_end_when_there_is_no_sign_off() -> None:
    out = check(draft("Hi Daniel,\n\nThanks for reaching out about the portal."))
    assert out["body"].endswith(f"You can pick a time for a short call here: {BOOKING}")


def test_thanks_in_the_first_paragraph_is_not_mistaken_for_the_sign_off() -> None:
    body = "Hi Daniel,\n\nThanks for your message about the portal.\n\nBest,\nThe team"
    out = check(draft(body))
    assert out["body"].index(BOOKING) > out["body"].index("about the portal")


def test_long_email_is_flagged() -> None:
    body = GOOD_BODY.replace("You want", "word " * 230 + "You want")
    assert any(f.startswith("long email") for f in check(draft(body))["flags"])


def test_empty_subject_is_replaced_and_flagged() -> None:
    out = check(draft(subject="  "))
    assert out["subject"] == "Thanks for getting in touch"
    assert "subject was empty and has been replaced" in out["flags"]


def test_unreadable_model_output_fails_loudly() -> None:
    case = {"nodes": {"When called by the pipeline": {"lead": LEAD, "enrichment": ENRICHMENT},
                      "Extract reply style": {"style": STYLE}},
            "input": {"candidates": [{"content": {"parts": [{"text": "not json"}]}}]},
            "env": {"BOOKING_LINK": BOOKING}}  # fmt: skip
    result = run_node(node_code("sub-draft.json", "Check draft"), [case])[0]
    assert "could not be read" in result["error"]
