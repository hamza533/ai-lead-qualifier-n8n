from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.lint_workflows import ERROR_WORKFLOW_ID, lint_workflow, main


def _workflow(nodes: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    return {
        "id": "lpSubEnrich00001",
        "name": "sub-enrich",
        "nodes": nodes,
        "connections": {},
        "settings": {"errorWorkflow": ERROR_WORKFLOW_ID},
        **extra,
    }


def _http_node(**extra: Any) -> dict[str, Any]:
    node = {
        "name": "Tavily search",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "parameters": {"url": "={{ $env.TAVILY_BASE_URL }}/search"},
        "retryOnFail": True,
        "maxTries": 3,
        "waitBetweenTries": 2000,
    }
    node.update(extra)
    return node


def _write(tmp_path: Path, wf: dict[str, Any]) -> Path:
    path = tmp_path / "wf.json"
    path.write_text(json.dumps(wf), encoding="utf-8")
    return path


def test_clean_workflow_passes(tmp_path: Path) -> None:
    assert lint_workflow(_write(tmp_path, _workflow([_http_node()]))) == []


def test_missing_retry_is_reported(tmp_path: Path) -> None:
    node = _http_node(retryOnFail=False)
    errors = lint_workflow(_write(tmp_path, _workflow([node])))
    assert any("retryOnFail" in e for e in errors)


def test_send_and_wait_is_exempt_from_retry(tmp_path: Path) -> None:
    node = {
        "name": "Ask approval",
        "type": "n8n-nodes-base.slack",
        "typeVersion": 2.3,
        "parameters": {"operation": "sendAndWait"},
    }
    assert lint_workflow(_write(tmp_path, _workflow([node]))) == []


def test_unpinned_type_version_is_reported(tmp_path: Path) -> None:
    errors = lint_workflow(_write(tmp_path, _workflow([_http_node(typeVersion=None)])))
    assert any("typeVersion" in e for e in errors)


def test_error_workflow_must_be_assigned(tmp_path: Path) -> None:
    wf = _workflow([_http_node()])
    wf["settings"] = {}
    assert any("errorWorkflow" in e for e in lint_workflow(_write(tmp_path, wf)))


def test_error_handler_itself_needs_no_error_workflow(tmp_path: Path) -> None:
    wf = _workflow([_http_node()], id=ERROR_WORKFLOW_ID)
    wf["settings"] = {}
    assert lint_workflow(_write(tmp_path, wf)) == []


def test_hardcoded_secret_is_reported(tmp_path: Path) -> None:
    node = _http_node(parameters={"url": "https://x", "headerValue": "Bearer " + "a1" * 15})
    errors = lint_workflow(_write(tmp_path, _workflow([node])))
    assert any("secret" in e for e in errors)


def test_inline_credential_data_is_reported(tmp_path: Path) -> None:
    node = _http_node(
        credentials={"httpHeaderAuth": {"id": "x", "name": "Gemini API", "data": "encrypted"}}
    )
    errors = lint_workflow(_write(tmp_path, _workflow([node])))
    assert any("credential" in e for e in errors)


def test_expression_values_are_not_secrets(tmp_path: Path) -> None:
    node = _http_node(parameters={"url": "https://x", "apiKey": "={{ $env.SOMETHING_LONG }}"})
    assert lint_workflow(_write(tmp_path, _workflow([node]))) == []


def test_invalid_json_is_reported(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    assert "invalid JSON" in lint_workflow(path)[0]


def test_main_on_empty_folder_passes(tmp_path: Path) -> None:
    assert main(["lint", str(tmp_path)]) == 0
