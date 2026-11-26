"""The score is always the weighted total of the per-criterion ratings.

Runs the *exported* "Compute score" Code node from workflows/sub-score.json under
Node.js with fixed ratings, and compares it with an independent Python reference.
"""

from __future__ import annotations

import copy
import json
import math
import random
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
ICP: dict[str, Any] = json.loads((ROOT / "config" / "icp.json").read_text(encoding="utf-8"))
KEYS = [c["key"] for c in ICP["criteria"]]
NODE = shutil.which("node")

HARNESS = r"""
const code = process.argv[1];
let input = '';
process.stdin.on('data', (d) => (input += d)).on('end', async () => {
  const out = [];
  for (const c of JSON.parse(input)) {
    const nodes = {
      'Parse ICP config': { icp: c.icp },
      'When called by the pipeline': {
        lead: { lead_id: 'ld_test' },
        enrichment: { sources: c.sources.map((url) => ({ url })) },
      },
    };
    const $ = (name) => ({ first: () => ({ json: nodes[name] }) });
    const $input = { first: () => ({ json: c.response }) };
    const run = new Function('$', '$input', `return (async () => {\n${code}\n})();`);
    try {
      out.push({ ok: (await run($, $input))[0].json });
    } catch (e) {
      out.push({ error: e.message });
    }
  }
  process.stdout.write(JSON.stringify(out));
});
"""


def compute_code() -> str:
    workflow = json.loads((ROOT / "workflows" / "sub-score.json").read_text(encoding="utf-8"))
    node = next(n for n in workflow["nodes"] if n["name"] == "Compute score")
    return str(node["parameters"]["jsCode"])


def response(ratings: list[dict[str, Any]]) -> dict[str, Any]:
    text = json.dumps({"ratings": ratings})
    return {"candidates": [{"content": {"parts": [{"text": text}]}}],
            "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 40}}  # fmt: skip


def rated(values: dict[str, Any], evidence: str = "form: message") -> list[dict[str, Any]]:
    return [{"key": k, "rating": v, "reason": f"{k} reason", "evidence": evidence}
            for k, v in values.items()]  # fmt: skip


def run_cases(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    assert NODE, "node is required"
    full = [{"icp": ICP, "sources": [], **c} for c in cases]
    proc = subprocess.run(  # noqa: S603
        [NODE, "-e", HARNESS, compute_code()],
        input=json.dumps(full), capture_output=True, text=True, check=True, encoding="utf-8",
    )  # fmt: skip
    result: list[dict[str, Any]] = json.loads(proc.stdout)
    return result


def run_one(**case: Any) -> dict[str, Any]:
    result = run_cases([case])[0]
    assert "ok" in result, result
    ok: dict[str, Any] = result["ok"]
    return ok


def reference(icp: dict[str, Any], ratings: dict[str, int]) -> tuple[int, str]:
    """Independent re-implementation of the documented formula."""
    weights = {c["key"]: c["weight"] for c in icp["criteria"]}
    earned = sum(ratings.get(k, 0) / 3 * w for k, w in weights.items())
    score = math.floor(earned / sum(weights.values()) * 100 + 0.5)  # JS Math.round
    tiers = icp["tiers"]
    tier = "hot" if score >= tiers["hot"] else "warm" if score >= tiers["warm"] else "cold"
    return score, tier


pytestmark = pytest.mark.skipif(NODE is None, reason="Node.js not installed")


def test_score_equals_weighted_total_for_random_fixed_ratings() -> None:
    rng = random.Random(20261126)  # fixed seed: the same 300 rating sets every run
    sets = [{k: rng.randint(0, 3) for k in KEYS} for _ in range(300)]
    results = run_cases([{"response": response(rated(s))} for s in sets])
    for ratings, result in zip(sets, results, strict=True):
        out = result["ok"]
        assert (out["score"], out["tier"]) == reference(ICP, ratings), ratings
        assert [c["rating"] for c in out["criteria"]] == [ratings[k] for k in KEYS]
        assert out["issues"] == []


@pytest.mark.parametrize(
    ("value", "score", "tier"), [(0, 0, "cold"), (3, 100, "hot")], ids=["all-0", "all-3"]
)
def test_extremes(value: int, score: int, tier: str) -> None:
    out = run_one(response=response(rated(dict.fromkeys(KEYS, value))))
    assert (out["score"], out["tier"]) == (score, tier)


def test_points_per_criterion_are_rating_over_three_times_weight() -> None:
    ratings = {"industry_fit": 3, "company_size": 2, "role_seniority": 3, "budget": 2,
               "clear_need": 3}  # fmt: skip
    out = run_one(response=response(rated(ratings)))
    assert [c["points"] for c in out["criteria"]] == [25, 13.33, 20, 13.33, 15]
    assert out["score"] == 87
    assert out["tier"] == "hot"


def test_tier_thresholds_are_inclusive_and_configurable() -> None:
    icp = copy.deepcopy(ICP)
    ratings = {"industry_fit": 3, "company_size": 0, "role_seniority": 3, "budget": 0,
               "clear_need": 3}  # fmt: skip
    score, _ = reference(icp, ratings)  # 60
    icp["tiers"] = {"hot": score, "warm": score - 10}
    assert run_one(icp=icp, response=response(rated(ratings)))["tier"] == "hot"
    icp["tiers"] = {"hot": score + 1, "warm": score}
    assert run_one(icp=icp, response=response(rated(ratings)))["tier"] == "warm"
    icp["tiers"] = {"hot": score + 2, "warm": score + 1}
    assert run_one(icp=icp, response=response(rated(ratings)))["tier"] == "cold"


def test_weights_are_normalised_when_they_do_not_sum_to_100() -> None:
    icp = copy.deepcopy(ICP)
    for c in icp["criteria"]:
        c["weight"] = 1
    ratings = dict(zip(KEYS, [3, 3, 0, 0, 0], strict=True))
    out = run_one(icp=icp, response=response(rated(ratings)))
    assert out["score"] == 40  # 2 of 5 equal-weight criteria at full marks


def test_missing_criterion_counts_as_zero_and_is_reported() -> None:
    ratings = dict.fromkeys(KEYS[1:], 3)
    out = run_one(response=response(rated(ratings)))
    assert out["criteria"][0]["rating"] == 0
    assert out["score"] == reference(ICP, ratings)[0] == 75
    assert out["issues"] == [f"{KEYS[0]}: not rated, counted as 0"]


@pytest.mark.parametrize("bad", [4, -1, 2.5, "high", None])
def test_invalid_rating_counts_as_zero(bad: Any) -> None:
    ratings: dict[str, Any] = dict.fromkeys(KEYS, 3)
    ratings[KEYS[0]] = bad
    out = run_one(response=response(rated(ratings)))
    assert out["criteria"][0]["rating"] == 0
    assert out["score"] == 75
    assert "invalid rating" in out["issues"][0]


def test_unknown_and_duplicate_keys_cannot_inflate_the_score() -> None:
    ratings = rated(dict.fromkeys(KEYS, 0)) + rated({KEYS[0]: 3, "bonus": 3})
    out = run_one(response=response(ratings))
    assert out["score"] == 0
    assert out["issues"] == ["bonus: not a configured criterion, ignored"]


def test_evidence_url_must_be_a_researched_source() -> None:
    researched = "https://harborlogistics.example/about"
    ratings = rated({KEYS[0]: 3}, evidence=researched) + rated(
        dict.fromkeys(KEYS[1:], 3), evidence="https://invented.example/page"
    )
    out = run_one(sources=[researched], response=response(ratings))
    assert out["criteria"][0]["evidence"] == researched
    assert all(c["evidence"] == "" for c in out["criteria"][1:])
    assert len(out["issues"]) == 4
    assert out["score"] == 100  # evidence problems are reported, not used to change ratings


def test_unreadable_model_output_fails_loudly() -> None:
    bad = {"candidates": [{"content": {"parts": [{"text": "not json"}]}}]}
    assert "could not be read" in run_cases([{"response": bad}])[0]["error"]


def test_non_positive_weight_in_config_fails_loudly() -> None:
    icp = copy.deepcopy(ICP)
    icp["criteria"][0]["weight"] = 0
    result = run_cases([{"icp": icp, "response": response(rated(dict.fromkeys(KEYS, 3)))}])[0]
    assert "positive weight" in result["error"]
