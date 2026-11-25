"""End-to-end smoke test: needs `docker compose --profile test up` (make test-e2e)."""

from __future__ import annotations

import httpx
import pytest

from scripts.envfile import read_env

pytestmark = pytest.mark.e2e


def test_n8n_is_ready() -> None:
    url = read_env().get("N8N_URL", "http://localhost:5678")
    assert httpx.get(f"{url}/healthz/readiness", timeout=5).status_code == 200


def test_mock_server_is_up() -> None:
    url = read_env().get("MOCK_URL", "http://localhost:8099")
    assert httpx.get(f"{url}/health", timeout=5).json() == {"status": "ok"}
