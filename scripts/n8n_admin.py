"""Admin tasks for the local n8n instance.

Uses the n8n CLI inside the running `n8n` compose service (and psql inside the
`postgres` service), so it works the same on a laptop and in CI.

    uv run python -m scripts.n8n_admin wait         # wait for n8n readiness
    uv run python -m scripts.n8n_admin migrate      # create/upgrade the leads database
    uv run python -m scripts.n8n_admin credentials  # create n8n credentials from .env
    uv run python -m scripts.n8n_admin import       # import + activate /workflows
    uv run python -m scripts.n8n_admin export       # export workflows into /workflows
    uv run python -m scripts.n8n_admin api-key      # ensure N8N_API_KEY in .env
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from typing import Any

import httpx

from scripts.envfile import ROOT, read_env, set_values

WORKFLOWS_DIR = ROOT / "workflows"
IO_DIR = ROOT / ".tmp" / "n8n-io"
MIGRATIONS_DIR = ROOT / "db" / "migrations"
SAFE_NAME = re.compile(r"[a-z0-9_]{1,63}")

# Fixed workflow IDs keep Execute Workflow references stable across export/import.
WORKFLOW_FILES: dict[str, str] = {
    "lpIntakeWebhook1": "intake-webhook.json",
    "lpIntakeForm0001": "intake-form.json",
    "lpSubValidate001": "sub-validate.json",
    "lpMainIntake0001": "main-lead-intake.json",
    "lpSubEnrich00001": "sub-enrich.json",
    "lpSubScore000001": "sub-score.json",
    "lpSubCrmUpdate01": "sub-crm-update.json",
    "lpErrorHandler01": "error-handler.json",
    "lpDailyDigest001": "daily-cold-digest.json",
    "lpSubDraft000001": "sub-draft.json",
    "lpReminders00001": "approval-reminders.json",
    "lpOpsWebhook0001": "ops-webhooks.json",
    "lpSubAlert000001": "sub-alert.json",
    "lpFinishLead0001": "finish-lead.json",
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
            "secure": "${SMTP_SECURE}",
        },
    },
    {
        "id": "lpCredOpsToken01",
        "name": "LeadPilot ops token",
        "type": "httpHeaderAuth",
        "data": {"name": "X-LeadPilot-Ops-Token", "value": "${OPS_WEBHOOK_TOKEN}"},
    },
    {
        "id": "lpCredLeadsDb001",
        "name": "LeadPilot DB",
        "type": "postgres",
        "data": {
            "host": "${DB_POSTGRESDB_HOST}",
            "port": "${DB_POSTGRESDB_PORT}",
            "database": "${LEADPILOT_DB_NAME}",
            "user": "${DB_POSTGRESDB_USER}",
            "password": "${DB_POSTGRESDB_PASSWORD}",
            "ssl": "disable",
        },
    },
]
INTEGER_FIELDS = {"port"}
BOOLEAN_FIELDS = {"secure"}
# Slack's signing secret is only for Slack-triggered workflows; approvals use n8n's signed form URL.
OPTIONAL_FIELDS = {"signatureSecret"}


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
    # Single-instance n8n can't activate on CLI import, so activate through the public API.
    n8n_cli("n8n", "import:workflow", "--separate", "--input=/workflows")
    print(f"imported {len(files)} workflow(s)")
    compose("restart", "n8n")
    wait()
    key = api_key()
    url = read_env().get("N8N_URL", "http://localhost:5678")

    workflows = [json.loads(p.read_text(encoding="utf-8")) for p in files]
    with httpx.Client(base_url=url, headers={"X-N8N-API-KEY": key}, timeout=30) as client:
        for workflow in activation_order(workflows):
            if workflow.get("active"):
                res = client.post(f"/api/v1/workflows/{workflow['id']}/activate")
                if res.status_code >= 400:
                    raise SystemExit(f"activating {workflow['name']} failed: {res.text[:500]}")
                print(f"activated {workflow['name']}")


def referenced_workflows(workflow: dict[str, Any]) -> set[str]:
    """IDs of the sub-workflows this workflow calls (Execute Workflow nodes).

    The error-workflow setting is not a dependency: n8n publishes a workflow whose error
    workflow isn't active yet, and the error handler itself calls sub-alert, whose error
    workflow is the error handler (that would be a cycle)."""
    refs = set()
    for node in workflow.get("nodes", []):
        if node.get("type") == "n8n-nodes-base.executeWorkflow":
            target = node.get("parameters", {}).get("workflowId", {})
            value = target.get("value") if isinstance(target, dict) else target
            if isinstance(value, str) and value:
                refs.add(value)
    return refs - {workflow["id"]}


def activation_order(workflows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Dependencies first: n8n won't publish a workflow whose sub-workflows aren't published."""
    by_id = {w["id"]: w for w in workflows}
    ordered: list[dict[str, Any]] = []
    state: dict[str, str] = {}

    def visit(wid: str) -> None:
        if state.get(wid) == "done":
            return
        if state.get(wid) == "visiting":
            raise SystemExit(f"workflow reference cycle through {wid}")
        state[wid] = "visiting"
        for dep in sorted(referenced_workflows(by_id[wid])):
            if dep in by_id:  # references to workflows not in /workflows are n8n's problem
                visit(dep)
        state[wid] = "done"
        ordered.append(by_id[wid])

    for wid in sorted(by_id):
        visit(wid)
    return ordered


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
        for field in OPTIONAL_FIELDS & data.keys():
            if "CHANGE_ME" in str(data[field]) or "${" in str(data[field]):
                data[field] = ""  # optional and unused: leave it empty instead of warning
        if any(isinstance(v, str) and "CHANGE_ME" in v for v in data.values()):
            placeholders.append(cred["name"])
        for field in INTEGER_FIELDS & data.keys():
            data[field] = int(data[field])
        for field in BOOLEAN_FIELDS & data.keys():
            data[field] = str(data[field]).strip().lower() in {"1", "true", "yes"}
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


def psql(database: str, sql: str) -> str:
    env = read_env()
    user = env.get("DB_POSTGRESDB_USER", "n8n")
    return compose(
        "exec", "-T", "postgres",
        "psql", "-v", "ON_ERROR_STOP=1", "-qAt", "-U", user, "-d", database,
        stdin=sql,
    )  # fmt: skip


def migrate() -> None:
    """Create the leads database if needed and apply new files from db/migrations."""
    env = read_env()
    db = env.get("LEADPILOT_DB_NAME", "leadpilot")
    # Names are interpolated into SQL, so only plain identifiers are accepted.
    if not SAFE_NAME.fullmatch(db):
        raise SystemExit(f"LEADPILOT_DB_NAME must match {SAFE_NAME.pattern}, got {db!r}")
    bad = [p.name for p in MIGRATIONS_DIR.glob("*.sql") if not SAFE_NAME.fullmatch(p.stem)]
    if bad:
        raise SystemExit(f"migration file names must match {SAFE_NAME.pattern}: {bad}")
    exists = psql("postgres", f"SELECT 1 FROM pg_database WHERE datname = '{db}';").strip()  # noqa: S608
    if not exists:
        psql("postgres", f'CREATE DATABASE "{db}";')
        print(f"created database {db}")
    psql(
        db,
        "CREATE TABLE IF NOT EXISTS schema_migrations "
        "(version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now());",
    )
    applied = set(psql(db, "SELECT version FROM schema_migrations;").split())
    pending = [p for p in sorted(MIGRATIONS_DIR.glob("*.sql")) if p.stem not in applied]
    for path in pending:
        sql = path.read_text(encoding="utf-8")
        record = f"INSERT INTO schema_migrations (version) VALUES ('{path.stem}');"  # noqa: S608
        psql(db, f"BEGIN;\n{sql}\n{record}\nCOMMIT;\n")
        print(f"applied migration {path.name}")
    print(f"database {db} is up to date ({len(applied) + len(pending)} migration(s))")


def api_key() -> str:
    """Return a public-API key, creating one from the owner login if .env has none."""
    env = read_env()
    url = env.get("N8N_URL", "http://localhost:5678")
    if env.get("N8N_API_KEY"):
        probe = httpx.get(
            f"{url}/api/v1/workflows",
            params={"limit": 1},
            headers={"X-N8N-API-KEY": env["N8N_API_KEY"]},
            timeout=10,
        )
        if probe.status_code != 401:
            return env["N8N_API_KEY"]
        print("N8N_API_KEY in .env is not valid for this instance; creating a new one")
    with httpx.Client(base_url=url, timeout=15) as client:
        login = {
            "emailOrLdapLoginId": env["N8N_INSTANCE_OWNER_EMAIL"],
            "password": env["N8N_OWNER_PASSWORD"],
        }
        client.post("/rest/login", json=login).raise_for_status()
        scopes = client.get("/rest/api-keys/scopes").raise_for_status().json()["data"]
        body = {"label": "leadpilot-harness", "expiresAt": None, "scopes": scopes}
        key = client.post("/rest/api-keys", json=body).raise_for_status().json()["data"]
    set_values({"N8N_API_KEY": key["rawApiKey"]})
    print("created n8n API key 'leadpilot-harness' and saved it to .env")
    return str(key["rawApiKey"])


def main() -> None:
    commands = {
        "wait": wait,
        "migrate": migrate,
        "import": import_workflows,
        "export": export,
        "credentials": credentials,
        "api-key": api_key,
    }
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=list(commands))
    commands[parser.parse_args().command]()


if __name__ == "__main__":
    main()
