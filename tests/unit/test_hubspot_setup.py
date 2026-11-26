from __future__ import annotations

import json

import httpx

from scripts.hubspot_setup import PROPERTIES, ensure_properties


def _fake_hubspot(existing: set[str], created: list[dict[str, object]]) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer token"
        name = request.url.path.rsplit("/", 1)[-1]
        if request.method == "GET":
            return httpx.Response(200 if name in existing else 404, json={"name": name})
        body = json.loads(request.content)
        created.append(body)
        existing.add(body["name"])
        return httpx.Response(201, json=body)

    return httpx.Client(base_url="https://hubspot.test", transport=httpx.MockTransport(handler),
                        headers={"Authorization": "Bearer token"})  # fmt: skip


def test_creates_missing_properties_in_the_contact_group() -> None:
    created: list[dict[str, object]] = []
    result = ensure_properties(_fake_hubspot({"ai_lead_score"}, created))
    assert result == [
        ("ai_lead_score", "exists"),
        ("ai_lead_tier", "created"),
        ("ai_score_reasons", "created"),
        ("ai_last_processed", "created"),
    ]
    assert {p["name"] for p in created} == {"ai_lead_tier", "ai_score_reasons", "ai_last_processed"}
    assert all(p["groupName"] == "contactinformation" for p in created)


def test_running_twice_creates_nothing_the_second_time() -> None:
    existing: set[str] = set()
    created: list[dict[str, object]] = []
    ensure_properties(_fake_hubspot(existing, created))
    again: list[dict[str, object]] = []
    assert all(s == "exists" for _, s in ensure_properties(_fake_hubspot(existing, again)))
    assert again == []


def test_property_types_match_what_the_workflow_writes() -> None:
    by_name = {p["name"]: p for p in PROPERTIES}
    assert by_name["ai_lead_score"]["type"] == "number"
    assert [o["value"] for o in by_name["ai_lead_tier"]["options"]] == ["hot", "warm", "cold"]
    assert by_name["ai_score_reasons"]["fieldType"] == "textarea"
    assert by_name["ai_last_processed"]["type"] == "datetime"
