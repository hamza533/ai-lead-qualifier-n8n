from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from tests.mock_server.app import app


@pytest.fixture()
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        c.post("/_control/reset")
        yield c


def test_tavily_search_returns_fixture(client: TestClient) -> None:
    res = client.post("/tavily/search", json={"query": "Harbor Logistics harborlogistics.example"})
    assert res.status_code == 200
    assert len(res.json()["results"]) == 2


def test_extract_unreachable_site_reports_failure(client: TestClient) -> None:
    res = client.post("/tavily/extract", json={"urls": ["https://unreachable.example"]})
    body = res.json()
    assert body["results"] == []
    assert body["failed_results"][0]["url"] == "https://unreachable.example"


def test_injected_failures_then_recovery(client: TestClient) -> None:
    client.post("/_control/fail", json={"service": "gemini", "times": 2, "status": 503})
    url = "/gemini/v1beta/models/gemini-2.5-flash:generateContent"
    body = {"contents": [{"parts": [{"text": "[task:profile] acme.example"}]}]}
    assert client.post(url, json=body).status_code == 503
    assert client.post(url, json=body).status_code == 503
    assert client.post(url, json=body).status_code == 200
    assert len(client.get("/_control/calls").json()) == 3


def test_gemini_returns_task_shaped_json(client: TestClient) -> None:
    url = "/gemini/v1beta/models/gemini-2.5-flash:generateContent"
    res = client.post(url, json={"contents": [{"parts": [{"text": "[task:score] lead"}]}]})
    data = res.json()
    assert "ratings" in data["candidates"][0]["content"]["parts"][0]["text"]
    assert data["usageMetadata"]["totalTokenCount"] > 0
