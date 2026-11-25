"""Admin tasks for the local n8n instance: wait, import, export, credentials.

Uses the n8n CLI inside the running `n8n` compose service, so it needs no API
key and works the same on a laptop and in CI.

    uv run python -m scripts.n8n_admin wait
    uv run python -m scripts.n8n_admin import
    uv run python -m scripts.n8n_admin export
    uv run python -m scripts.n8n_admin credentials
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from typing import Any

import httpx

from scripts.envfile import ROOT, read_env

WORKFLOWS_DIR = ROOT / "workflows"
IO_DIR = ROOT / ".tmp" / "n8n-io"

# Fixed workflow IDs keep Execute Workflow references stable across export/import.
WORKFLOW_FILES: dict[str, str] = {
    "lpMainIntake0001": "main-lead-intake.json",
    "lpSubEnrich00001": "sub-enrich.json",
    "lpSubScore000001": "sub-score.json",
    "lpSubCrmUpdate01": "sub-crm-update.json",
    "lpErrorHandler01": "error-handler.json",
    "lpDailyDigest001": "daily-cold-digest.json",
}

# Fields n8n adds on export that change on every save and would only add noise to diffs.
VOLATILE_KEYS = (
    "createdAt",
    "updatedAt",
    "versionId",
    "activeVersionId",
    "shared",
    "triggerCount",
    "versionCounter",
    "isArchived",
    "activeVersion",
)

# Fixed credential IDs; workflows reference credentials by these IDs and names only.
CREDENTIALS: list[dict[str, Any]] = [
    {
        "id": "lpCredGemini0001",
        "name": "Gemini API",
        "type": "httpHeaderAuth",
        "data": {"name": "x-goog-api-key", "value": "${GEMINI_API_KEY}"},
    },
    {
        "id": "lpCredTavily0001",
        "name": "Tavily API",
        "type": "httpHeaderAuth",
        "data": {"name": "Authorization", "value": "Bearer ${TAVILY_API_KEY}"},
    },
    {
        "id": "lpCredHubspot001",
        "name": "HubSpot",
        "type": "hubspotAppToken",
        "data": {"appToken": "${HUBSPOT_PRIVATE_APP_TOKEN}"},
    },
    {
        "id": "lpCredSlack00001",
        "name": "Slack Bot",
        "type": "slackApi",
        "data": {"accessToken": "${SLACK_BOT_TOKEN}", "signatureSecret": "${SLACK_SIGNING_SECRET}"},
    },
    {
        "id": "lpCredSmtp000001",
        "name": "SMTP",
        "type": "smtp",
        "data": {
            "user": "${SMTP_USER}",
            "password": "${SMTP_PASSWORD}",
            "host": "${SMTP_HOST}",
            "port": "${SMTP_PORT}",
            "secure": True,
        },
    },
]


def compose(*args: str, stdin: str | None = None, check: bool = True) -> str:
    cmd = ["docker", "compose", *args]
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell
        cmd,
        cwd=ROOT,
        input=stdin,
        text=True,
        capture_output=True,
        check=False,
        encoding="utf-8",
    )
    if check and result.returncode != 0:
        sys.stderr.write(result.stdout + result.stderr)
        raise SystemExit(f"command failed: {' '.join(cmd)}")
    return result.stdout


def n8n_cli(*args: str, stdin: str | None = None) -> str:
    return compose("exec", "-T", "-u", "node", "n8n", *args, stdin=stdin)


def wait(timeout: float = 240.0) -> None:
    """Wait until *this project's* n8n container is up and its readiness probe passes.

    Probing inside the container avoids being fooled by another n8n on the same host port.
    """
    probe = "wget -qO- http://localhost:5678/healthz/readiness"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = subprocess.run(  # noqa: S603 - fixed argv, no shell
            ["docker", "compose", "exec", "-T", "n8n", "sh", "-c", probe],  # noqa: S607
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            url = read_env().get("N8N_URL", "http://localhost:5678")
            try:
                httpx.get(f"{url}/healthz", timeout=3).raise_for_status()
            except httpx.HTTPError as exc:
                raise SystemExit(
                    f"n8n is ready in Docker but not reachable at {url}: {exc}"
                ) from exc
            print(f"n8n ready at {url}")
            return
        time.sleep(2)
    raise SystemExit(f"n8n not ready after {timeout:.0f}s; see `docker compose logs n8n`")


def normalise(workflow: dict[str, Any]) -> dict[str, Any]:
    for key in VOLATILE_KEYS:
        workflow.pop(key, None)
    meta = workflow.get("meta") or {}
    meta.pop("instanceId", None)
    workflow["meta"] = meta
    for tag in workflow.get("tags", []):
        for key in ("createdAt", "updatedAt"):
            tag.pop(key, None)
    return workflow


def export() -> None:
    out = IO_DIR / "export"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    n8n_cli("n8n", "export:workflow", "--all", "--separate", "--pretty", "--output=/io/export/")
    WORKFLOWS_DIR.mkdir(exist_ok=True)
    count = 0
    for path in sorted(out.glob("*.json")):
        workflow = normalise(json.loads(path.read_text(encoding="utf-8")))
        if workflow.get("isArchived"):
            continue
        filename = WORKFLOW_FILES.get(workflow["id"])
        if filename is None:
            print(f"skip: workflow {workflow['id']} '{workflow['name']}' has no fixed ID mapping")
            continue
        text = json.dumps(workflow, indent=2, ensure_ascii=False) + "\n"
        (WORKFLOWS_DIR / filename).write_text(text, encoding="utf-8")
        count += 1
    print(f"exported {count} workflow(s) to {WORKFLOWS_DIR.relative_to(ROOT)}/")


def import_workflows() -> None:
    files = sorted(WORKFLOWS_DIR.glob("*.json"))
    if not files:
        print("no workflows to import")
        return
    n8n_cli("n8n", "import:workflow", "--separate", "--input=/workflows", "--activeState=fromJson")
    print(f"imported {len(files)} workflow(s); restarting n8n to register triggers")
    compose("restart", "n8n")
    wait()


def _fill(value: Any, env: dict[str, str]) -> Any:
    if isinstance(value, str):
        for key, val in env.items():
            value = value.replace("${" + key + "}", val)
        return value
    return value


def credentials() -> None:
    env = read_env()
    payload = []
    placeholders = []
    for cred in CREDENTIALS:
        data = {k: _fill(v, env) for k, v in cred["data"].items()}
        if any(isinstance(v, str) and "CHANGE_ME" in v for v in data.values()):
            placeholders.append(cred["name"])
        if cred["type"] == "smtp":
            data["port"] = int(data["port"] or 465)
        payload.append({**cred, "data": data})
    script = (
        "umask 077; cat > /tmp/lp-creds.json && "
        "n8n import:credentials --input=/tmp/lp-creds.json; "
        "rc=$?; rm -f /tmp/lp-creds.json; exit $rc"
    )
    n8n_cli("sh", "-c", script, stdin=json.dumps(payload))
    print(f"created/updated {len(payload)} credentials: " + ", ".join(c["name"] for c in payload))
    if placeholders:
        print("still placeholders (fill .env and re-run): " + ", ".join(placeholders))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["wait", "import", "export", "credentials"])
    args = parser.parse_args()
    {"wait": wait, "import": import_workflows, "export": export, "credentials": credentials}[
        args.command
    ]()


if __name__ == "__main__":
    main()
