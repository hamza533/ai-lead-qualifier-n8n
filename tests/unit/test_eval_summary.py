from __future__ import annotations

from typing import Any

from eval.run import percentile, summarise, to_markdown

PRICES = {
    "checked": "2026-11-27",
    "gemini": {"input_per_million_tokens_usd": 0.30, "output_per_million_tokens_usd": 2.50},
    "tavily": {"per_credit_usd": 0.008},
}


def case(expected: str, actual: str, **extra: Any) -> dict[str, Any]:
    base = {"id": f"{expected}-{actual}", "case": "normal", "expected": expected,
            "actual": actual, "ok": expected == actual, "tokens_in": 1000, "tokens_out": 400,
            "tavily_credits": 2, "seconds_to_review": 10.0,
            "judge": {"judged": True, "all_grounded": True,
                      "claims": [{"claim": "x", "supported": True}]}}  # fmt: skip
    return {**base, **extra}


def test_percentile_is_nearest_rank() -> None:
    values = [float(v) for v in range(1, 21)]  # 1..20
    assert percentile(values, 50) == 10
    assert percentile(values, 95) == 19
    assert percentile([], 50) is None


def test_tier_accuracy_and_confusion_matrix() -> None:
    cases = [case("hot", "hot"), case("hot", "warm"), case("warm", "warm"), case("cold", "cold"),
             case("spam", "spam"), case("duplicate", "duplicate")]  # fmt: skip
    s = summarise(cases, PRICES)
    assert (s["tier_correct"], s["tier_total"], s["tier_accuracy"]) == (3, 4, 0.75)
    assert s["confusion"]["hot"] == {"hot": 1, "warm": 1, "cold": 0}
    assert s["spam_and_duplicates_handled"] == "2/2"


def test_grounding_counts_claims_across_judged_drafts() -> None:
    claims = [{"claim": "a", "supported": True}, {"claim": "b", "supported": False}]
    bad = {"judged": True, "all_grounded": False, "claims": claims}
    s = summarise([case("hot", "hot"), case("warm", "warm", judge=bad)], PRICES)
    assert s["grounding"] == {"drafts_judged": 2, "drafts_fully_grounded": 1, "claims": 3,
                              "claims_supported": 2, "claims_supported_ratio": 0.667}  # fmt: skip


def test_cost_per_lead_uses_average_usage_and_list_prices() -> None:
    s = summarise([case("hot", "hot")], PRICES)
    # 1000 in * 0.30/M + 400 out * 2.50/M + 2 credits * 0.008
    assert s["est_paid_cost_per_lead_usd"] == round(0.0003 + 0.001 + 0.016, 4)


def test_markdown_report_has_the_headline_numbers() -> None:
    cases = [case("hot", "hot"), case("cold", "cold")]
    run = {"mock": True, "leads": 2, "finished": "now", "model": "m", "n8n_version": "2.49.6",
           "prices_checked": "2026-11-27"}  # fmt: skip
    md = to_markdown(run, summarise(cases, PRICES), cases)
    assert "| Tier accuracy | **100%** (2/2) |" in md
    assert "Mock run" in md
    assert "| **hot** | 1 | 0 | 0 |" in md
