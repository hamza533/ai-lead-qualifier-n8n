"""Mock Tavily + Gemini server for the end-to-end tests and CI.

n8n reaches it through TAVILY_BASE_URL=http://mock:8099/tavily and
GEMINI_BASE_URL=http://mock:8099/gemini. Tests steer it through /_control:

  POST /_control/fail   {"service": "tavily_search", "times": 5, "status": 503}
  POST /_control/reset
  GET  /_control/calls  -> list of recorded calls (service, path, body excerpt)

Responses come from fixtures in ./fixtures, keyed by company domain. Gemini
requests carry a task marker ("[task:profile]", "[task:score]", "[task:draft]",
"[task:judge]") in the prompt so the mock knows which shape to return.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

FIXTURES = Path(__file__).parent / "fixtures"
app = FastAPI(title="LeadPilot mock services")

_state: dict[str, Any] = {"fail": {}, "calls": []}
SERVICES = ("tavily_search", "tavily_extract", "gemini")


def _load(name: str) -> dict[str, Any]:
    path = FIXTURES / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _company_fixture(text: str) -> dict[str, Any]:
    """Pick the fixture whose domain (or one of its company-name aliases) appears in text."""
    companies: dict[str, Any] = _load("companies")
    lowered = text.lower()
    for domain, data in companies.items():
        if domain.startswith("_"):
            continue
        names = [domain, *data.get("aliases", [])]
        if any(name.lower() in lowered for name in names):
            return {"domain": domain, **data}
    return {"domain": None, **companies.get("_default", {})}


def _gemini_task(body: dict[str, Any]) -> str:
    """Tell the request type apart by the response schema, so prompts need no test markers."""
    schema = json.dumps(body.get("generationConfig", {}).get("responseSchema", {}))
    for key, task in (("what_they_do", "profile"), ("ratings", "score"),
                      ("subject", "draft"), ("claims", "judge")):  # fmt: skip
        if f'"{key}"' in schema:
            return task
    match = TASK_RE.search(json.dumps(body))
    return match.group(1) if match else "unknown"


def _maybe_fail(service: str) -> None:
    rule = _state["fail"].get(service)
    if rule and rule["times"] > 0:
        rule["times"] -= 1
        raise HTTPException(status_code=rule["status"], detail=f"injected {service} failure")


def _record(service: str, path: str, body: Any) -> None:
    _state["calls"].append({"service": service, "path": path, "body": json.dumps(body)[:2000]})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/_control/fail")
async def control_fail(request: Request) -> dict[str, Any]:
    body = await request.json()
    service = body["service"]
    if service not in SERVICES:
        raise HTTPException(400, f"service must be one of {SERVICES}")
    _state["fail"][service] = {
        "times": int(body.get("times", 1)),
        "status": int(body.get("status", 503)),
    }
    return {"ok": True, "fail": _state["fail"]}


@app.post("/_control/reset")
def control_reset() -> dict[str, bool]:
    _state["fail"].clear()
    _state["calls"].clear()
    return {"ok": True}


@app.get("/_control/calls")
def control_calls() -> list[dict[str, Any]]:
    return list(_state["calls"])


# --- Tavily -----------------------------------------------------------------
@app.post("/tavily/search")
async def tavily_search(request: Request) -> dict[str, Any]:
    body = await request.json()
    _record("tavily_search", "/search", body)
    _maybe_fail("tavily_search")
    fixture = _company_fixture(json.dumps(body))
    return {
        "query": body.get("query", ""),
        "results": fixture.get("search_results", []),
        "response_time": 0.1,
    }


@app.post("/tavily/extract")
async def tavily_extract(request: Request) -> dict[str, Any]:
    body = await request.json()
    _record("tavily_extract", "/extract", body)
    _maybe_fail("tavily_extract")
    urls = body.get("urls", [])
    urls = [urls] if isinstance(urls, str) else urls
    # Third-party pages known from any fixture's search results can be extracted too.
    known_pages = {
        r["url"]: r["content"]
        for data in _load("companies").values()
        for r in data.get("search_results", [])
    }
    results, failed = [], []
    for url in urls:
        fixture = _company_fixture(url)
        own_site = fixture["domain"] is not None and fixture["domain"] in url
        if own_site and fixture.get("unreachable"):
            failed.append({"url": url, "error": "Failed to fetch url"})
        elif own_site:
            page = fixture.get("page_text", "") or known_pages.get(url, "")
            results.append({"url": url, "raw_content": page})
        elif url in known_pages:
            results.append({"url": url, "raw_content": known_pages[url]})
        else:
            failed.append({"url": url, "error": "Failed to fetch url"})
    return {"results": results, "failed_results": failed, "response_time": 0.1}


# --- Gemini -----------------------------------------------------------------
TASK_RE = re.compile(r"\[task:(\w+)\]")


@app.post("/gemini/v1beta/models/{model_action}")
async def gemini_generate(model_action: str, request: Request) -> JSONResponse:
    if not model_action.endswith(":generateContent"):
        raise HTTPException(404, "only :generateContent is mocked")
    body = await request.json()
    task = _gemini_task(body)
    _record("gemini", f"{model_action}#{task}", body)
    _maybe_fail("gemini")
    prompt = json.dumps(body.get("contents", body))
    fixture = _company_fixture(prompt)
    answer = fixture.get("gemini", {}).get(task) or _load("gemini_defaults").get(task, {})
    text = json.dumps(answer)
    return JSONResponse(
        {
            "candidates": [
                {"content": {"role": "model", "parts": [{"text": text}]}, "finishReason": "STOP"}
            ],
            "usageMetadata": {
                "promptTokenCount": max(1, len(prompt) // 4),
                "candidatesTokenCount": max(1, len(text) // 4),
                "totalTokenCount": max(1, len(prompt) // 4) + max(1, len(text) // 4),
            },
            "modelVersion": model_action.split(":")[0],
        }
    )
