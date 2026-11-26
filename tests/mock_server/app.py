"""Mock Tavily, Gemini, Slack and HubSpot for the end-to-end tests and CI.

n8n reaches it through TAVILY_BASE_URL=http://mock:8099/tavily,
GEMINI_BASE_URL=http://mock:8099/gemini, SLACK_BASE_URL=http://mock:8099/slack and
HUBSPOT_BASE_URL=http://mock:8099/hubspot (HubSpot state is kept in memory and can be
read at GET /_control/hubspot). Tests steer it through /_control:

  POST /_control/fail   {"service": "tavily_search", "times": 5, "status": 503}
  POST /_control/reset
  GET  /_control/calls  -> list of recorded calls (service, path, body excerpt)

Responses come from fixtures in ./fixtures, keyed by company domain or alias. The
Gemini task (profile, score, draft, judge) is detected from the response schema.
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
SERVICES = ("tavily_search", "tavily_extract", "gemini", "slack", "hubspot")
# Gemini failures can also target one task, e.g. "gemini:score" (profile, score, draft, judge).
GEMINI_TASKS = ("profile", "score", "draft", "judge")


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
    """Fail this request if a rule is armed. A rule with "match" only fails requests whose
    body contains that text (e.g. one lead's email), so other tests' background work can't
    use up the injected failures."""
    rule = _state["fail"].get(service)
    if not rule or rule["times"] <= 0:
        return
    last_body = _state["calls"][-1]["body"] if _state["calls"] else ""
    if rule.get("match") and rule["match"] not in last_body:
        return
    rule["times"] -= 1
    raise HTTPException(status_code=rule["status"], detail=f"injected {service} failure")


def _record(service: str, path: str, body: Any) -> None:
    _state["calls"].append({"service": service, "path": path, "body": json.dumps(body)[:50000]})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/_control/fail")
async def control_fail(request: Request) -> dict[str, Any]:
    body = await request.json()
    service = body["service"]
    allowed = (*SERVICES, *(f"gemini:{t}" for t in GEMINI_TASKS))
    if service not in allowed:
        raise HTTPException(400, f"service must be one of {allowed}")
    _state["fail"][service] = {
        "times": int(body.get("times", 1)),
        "status": int(body.get("status", 503)),
        "match": str(body.get("match", "")),
    }
    return {"ok": True, "fail": _state["fail"]}


@app.post("/_control/reset")
def control_reset() -> dict[str, bool]:
    _state["fail"].clear()
    _state["calls"].clear()
    _state.pop("hubspot", None)
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
    _maybe_fail(f"gemini:{task}")
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


# --- Slack (chat.postMessage / chat.update) --------------------------------------------
def _require_bearer(request: Request) -> None:
    if not request.headers.get("authorization", "").lower().startswith("bearer "):
        raise HTTPException(401, "missing bearer token")


@app.post("/slack/{method}")
async def slack(method: str, request: Request) -> dict[str, Any]:
    _require_bearer(request)
    body = await request.json()
    _record("slack", method, body)
    _maybe_fail("slack")
    if method == "chat.postMessage":
        _state["slack_seq"] = _state.get("slack_seq", 0) + 1
        ts = f"1790000000.{_state['slack_seq']:06d}"
        return {"ok": True, "channel": body.get("channel"), "ts": ts,
                "message": {"text": body.get("text"), "ts": ts}}  # fmt: skip
    if method == "chat.update":
        return {"ok": True, "channel": body.get("channel"), "ts": body.get("ts")}
    return {"ok": False, "error": "unknown_method"}


# --- HubSpot CRM v3/v4 (in-memory) -------------------------------------------------------
def _hs() -> dict[str, Any]:
    store: dict[str, Any] = _state.setdefault(
        "hubspot",
        {"seq": 100, "contacts": {}, "companies": {}, "associations": [], "notes": [],
         "tasks": [], "properties": {}},
    )  # fmt: skip
    return store


def _hs_id() -> str:
    store = _hs()
    store["seq"] += 1
    return str(store["seq"])


@app.post("/hubspot/crm/v3/objects/contacts/batch/upsert")
async def hs_contact_upsert(request: Request) -> dict[str, Any]:
    _require_bearer(request)
    body = await request.json()
    _record("hubspot", "contacts/batch/upsert", body)
    _maybe_fail("hubspot")
    store = _hs()["contacts"]
    results = []
    for item in body["inputs"]:
        assert item.get("idProperty") == "email", "upsert must use idProperty=email"
        email = str(item["id"]).lower()
        new = email not in store
        if new:
            store[email] = {"id": _hs_id(), "properties": {"email": email}}
        store[email]["properties"].update(item.get("properties", {}))
        results.append({**store[email], "new": new})
    return {"status": "COMPLETE", "results": results}


@app.post("/hubspot/crm/v3/objects/companies/search")
async def hs_company_search(request: Request) -> dict[str, Any]:
    _require_bearer(request)
    body = await request.json()
    _record("hubspot", "companies/search", body)
    _maybe_fail("hubspot")
    f = body["filterGroups"][0]["filters"][0]
    hits = [
        {"id": cid, "properties": props}
        for cid, props in _hs()["companies"].items()
        if str(props.get(f["propertyName"], "")).lower() == str(f["value"]).lower()
    ]

    return {"total": len(hits), "results": hits}


@app.post("/hubspot/crm/v3/objects/{object_type}")
async def hs_create(object_type: str, request: Request) -> dict[str, Any]:
    _require_bearer(request)
    body = await request.json()
    _record("hubspot", f"{object_type}/create", body)
    _maybe_fail("hubspot")
    oid = _hs_id()
    store = _hs()
    if object_type == "companies":
        store["companies"][oid] = body["properties"]
    elif object_type in ("notes", "tasks"):
        store[object_type].append({"id": oid, **body})
    else:
        raise HTTPException(404, f"{object_type} not mocked")
    return {"id": oid, "properties": body["properties"]}


@app.put("/hubspot/crm/v4/objects/contact/{contact_id}/associations/default/company/{company_id}")
async def hs_associate(contact_id: str, company_id: str, request: Request) -> dict[str, Any]:
    _require_bearer(request)
    _record("hubspot", "associate", {"contact": contact_id, "company": company_id})
    _maybe_fail("hubspot")
    pair = (contact_id, company_id)
    if pair not in _hs()["associations"]:
        _hs()["associations"].append(pair)
    return {"status": "COMPLETE", "results": [{"from": {"id": contact_id},
                                               "to": {"id": company_id}}]}  # fmt: skip


@app.get("/hubspot/crm/v3/properties/contacts/{name}")
async def hs_get_property(name: str, request: Request) -> dict[str, Any]:
    _require_bearer(request)
    prop = _hs()["properties"].get(name)
    if prop is None:
        raise HTTPException(404, "property not found")
    return dict(prop)


@app.post("/hubspot/crm/v3/properties/contacts")
async def hs_create_property(request: Request) -> dict[str, Any]:
    _require_bearer(request)
    body = await request.json()
    _record("hubspot", "properties/create", body)
    if body["name"] in _hs()["properties"]:
        raise HTTPException(409, "property exists")
    _hs()["properties"][body["name"]] = body
    return dict(body)


@app.get("/_control/hubspot")
def control_hubspot() -> dict[str, Any]:
    store = _hs()
    return {**store, "associations": [list(p) for p in store["associations"]]}
