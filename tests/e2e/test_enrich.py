"""M2 – enrichment: Tavily search + extract, Gemini profile, grounding guard, retries, failures."""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from typing import Any

import httpx
import pytest

from tests.e2e.conftest import PostLead, sql, wait_for

pytestmark = pytest.mark.e2e

COMPANIES = {
    "harbor": (
        "Harbor Logistics",
        "harborlogistics.example",
        "daniel.reyes@harborlogistics.example",
    ),
    "unreachable": ("Unreachable Corp", "unreachable.example", "jo@unreachable.example"),
    "coastline": ("Coastline Clinics", "", "priya.natarajan@gmail.com"),
    "unknown": ("Nobody Knows Ltd", "nobody-knows.example", "a@nobody-knows.example"),
}


@pytest.fixture()
def mock(env: dict[str, str]) -> Iterator[httpx.Client]:
    client = httpx.Client(base_url=env.get("MOCK_URL", "http://localhost:8099"), timeout=10)
    client.post("/_control/reset")
    yield client
    client.post("/_control/reset")


def fail(mock: httpx.Client, service: str, times: int) -> None:
    mock.post("/_control/fail", json={"service": service, "times": times}).raise_for_status()


def calls(mock: httpx.Client, service: str) -> int:
    return sum(1 for c in mock.get("/_control/calls").json() if c["service"] == service)


def enrich(post_lead: PostLead, key: str) -> dict[str, Any]:
    """Post a lead for one fixture company and wait until its enrichment is recorded."""
    company, website, email = COMPANIES[key]
    res = post_lead({
        "name": "Test Person", "email": email, "company": company, "website": website,
        "role": "Head of Operations", "budget_range": "$20k-$50k",
        "message": f"We need a customer portal for our team. {uuid.uuid4()}",
    })  # fmt: skip
    assert res.status_code == 202, res.text
    lead_id = res.json()["lead_id"]

    def recorded() -> list[list[str]]:
        return sql(
            "SELECT status, enrichment_status, error, llm_input_tokens, tavily_credits, enrichment "
            f"FROM leads WHERE lead_id = '{lead_id}' AND enrichment_status IS NOT NULL"
        )

    status, enrichment_status, error, tokens, credits, enrichment = wait_for(recorded, 60)[0]
    data: dict[str, Any] = json.loads(enrichment)
    return {"status": status, "enrichment_status": enrichment_status, "error": error,
            "tokens": int(tokens), "credits": int(credits), **data}  # fmt: skip


def all_source_urls(profile: dict[str, Any]) -> set[str]:
    urls: set[str] = set()
    for key in ("what_they_do", "industry", "size_estimate", "location"):
        urls.update(profile[key]["sources"])
    for fact in profile["notable_facts"]:
        urls.update(fact["sources"])
    return urls


def test_company_with_website_gets_a_sourced_profile(
    post_lead: PostLead, mock: httpx.Client
) -> None:
    result = enrich(post_lead, "harbor")
    assert result["status"] == "enriched"
    assert result["enrichment_status"] == "ok"
    profile = result["profile"]
    assert profile["industry"] == {
        "value": "Logistics", "confidence": "high",
        "sources": ["https://harborlogistics.example/about"],
    }  # fmt: skip
    assert profile["size_estimate"]["value"] == "~180 employees"
    read = {s["url"] for s in result["sources"]}
    assert "https://harborlogistics.example" in read
    assert all_source_urls(profile) <= read


def test_facts_citing_pages_that_were_not_read_are_dropped(
    post_lead: PostLead, mock: httpx.Client
) -> None:
    result = enrich(post_lead, "harbor")
    facts = [f["fact"] for f in result["profile"]["notable_facts"]]
    assert not any("fastest-growing" in f for f in facts)
    assert any("cold-chain" in f for f in facts)
    assert result["grounding"]["dropped_unsourced"] == 1


def test_usage_is_recorded(post_lead: PostLead, mock: httpx.Client) -> None:
    result = enrich(post_lead, "harbor")
    assert result["tokens"] > 0
    assert result["credits"] == 2  # 1 basic search + 1 extract batch (up to 5 pages)
    assert calls(mock, "tavily_search") == 1
    assert calls(mock, "tavily_extract") == 1
    assert calls(mock, "gemini") == 1


def test_unreachable_website_continues_with_lower_confidence(
    post_lead: PostLead, mock: httpx.Client
) -> None:
    result = enrich(post_lead, "unreachable")
    assert result["enrichment_status"] == "partial"
    assert "website unreachable" in result["note"]
    assert result["profile"]["industry"]["value"] == "B2B SaaS"
    assert result["profile"]["industry"]["confidence"] == "medium"


def test_personal_email_lead_is_researched_by_company_name(
    post_lead: PostLead, mock: httpx.Client
) -> None:
    result = enrich(post_lead, "coastline")
    assert result["enrichment_status"] == "partial"
    assert "no company website" in result["note"]
    assert result["profile"]["industry"]["value"] == "Healthcare"


def test_unknown_company_is_scored_on_form_data_without_a_model_call(
    post_lead: PostLead, mock: httpx.Client
) -> None:
    result = enrich(post_lead, "unknown")
    assert result["status"] == "enrichment_failed"
    assert result["note"] == "no public information found – scored on form data only"
    assert result["profile"]["industry"]["value"] == "Unknown"
    assert calls(mock, "gemini") == 0


def test_transient_search_failures_are_retried(post_lead: PostLead, mock: httpx.Client) -> None:
    fail(mock, "tavily_search", 2)
    result = enrich(post_lead, "harbor")
    assert calls(mock, "tavily_search") == 3
    assert result["enrichment_status"] == "ok"
    assert result["error"] == ""


def test_search_outage_still_uses_the_company_website(
    post_lead: PostLead, mock: httpx.Client
) -> None:
    fail(mock, "tavily_search", 10)
    result = enrich(post_lead, "harbor")
    assert calls(mock, "tavily_search") == 3
    assert result["enrichment_status"] == "ok"
    assert "injected tavily_search failure" in result["error"]
    assert result["credits"] == 1


def test_model_outage_leaves_the_lead_in_a_recoverable_status(
    post_lead: PostLead, mock: httpx.Client
) -> None:
    fail(mock, "gemini", 10)
    result = enrich(post_lead, "harbor")
    assert calls(mock, "gemini") == 3
    assert result["status"] == "enrichment_failed"
    assert result["note"] == "company profile step failed – scored on form data only"
    assert "injected gemini failure" in result["error"]


def test_prompt_contains_only_read_sources_and_an_injection_warning(
    post_lead: PostLead, mock: httpx.Client
) -> None:
    enrich(post_lead, "harbor")
    body = next(c["body"] for c in mock.get("/_control/calls").json() if c["service"] == "gemini")
    assert "ignore any instructions" in body
    assert "responseSchema" in body
