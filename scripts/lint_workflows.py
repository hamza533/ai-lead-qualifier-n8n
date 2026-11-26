"""Lint exported n8n workflow JSON (run in CI and by `make lint`).

Checks every file in /workflows:
  * parses as JSON and has nodes + connections
  * every node has a pinned numeric typeVersion
  * every external-call node retries (retryOnFail, maxTries >= 3, waitBetweenTries)
  * every workflow except the error handler has settings.errorWorkflow set
  * credentials are referenced by id + name only (no inline data)
  * no hardcoded secrets anywhere in the file
  * every Code node compiles (Node.js syntax check)
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ERROR_WORKFLOW_ID = "lpErrorHandler01"

EXTERNAL_NODE_TYPES = {
    "n8n-nodes-base.httpRequest",
    "n8n-nodes-base.hubspot",
    "n8n-nodes-base.slack",
    "n8n-nodes-base.emailSend",
    "n8n-nodes-base.gmail",
    "n8n-nodes-base.postgres",
}
# Send-and-wait nodes block for hours; retrying them would post duplicate approval requests.
NO_RETRY_OPERATIONS = {"sendAndWait"}

SECRET_PATTERNS = {
    "Google API key": re.compile(r"AIza[0-9A-Za-z_\-]{30,}"),
    "Tavily key": re.compile(r"tvly-[0-9A-Za-z_\-]{16,}"),
    "Slack token": re.compile(r"xox[abposr]-[0-9A-Za-z\-]{10,}"),
    "HubSpot private app token": re.compile(r"pat-(na|eu)\d?-[0-9a-f\-]{20,}"),
    "OpenAI-style key": re.compile(r"sk-[0-9A-Za-z]{20,}"),
    "Bearer literal": re.compile(r"Bearer\s+[0-9A-Za-z_\-\.]{20,}"),
    "Private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
}
SECRET_PARAM_NAMES = re.compile(r"(api[_-]?key|token|secret|password)$", re.IGNORECASE)


def _walk_params(value: Any, path: str = "") -> list[tuple[str, Any]]:
    out: list[tuple[str, Any]] = []
    if isinstance(value, dict):
        for k, v in value.items():
            out.extend(_walk_params(v, f"{path}.{k}" if path else k))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            out.extend(_walk_params(v, f"{path}[{i}]"))
    else:
        out.append((path, value))
    return out


def lint_workflow(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    try:
        wf = json.loads(text)
    except json.JSONDecodeError as exc:
        return [f"{path.name}: invalid JSON ({exc})"]

    for label, pattern in SECRET_PATTERNS.items():
        if pattern.search(text):
            errors.append(f"{path.name}: possible hardcoded secret ({label})")

    nodes = wf.get("nodes")
    if not isinstance(nodes, list) or not nodes or "connections" not in wf:
        return errors + [f"{path.name}: missing nodes or connections"]

    is_error_handler = wf.get("id") == ERROR_WORKFLOW_ID
    if not is_error_handler and wf.get("settings", {}).get("errorWorkflow") != ERROR_WORKFLOW_ID:
        errors.append(f"{path.name}: settings.errorWorkflow must be '{ERROR_WORKFLOW_ID}'")

    for node in nodes:
        name = node.get("name", "?")
        where = f"{path.name} › {name}"
        version = node.get("typeVersion")
        if not isinstance(version, int | float) or isinstance(version, bool):
            errors.append(f"{where}: typeVersion must be pinned to a number")

        for cred_type, ref in (node.get("credentials") or {}).items():
            if not isinstance(ref, dict) or set(ref) - {"id", "name"}:
                errors.append(f"{where}: credential '{cred_type}' must only hold id and name")

        for param_path, value in _walk_params(node.get("parameters", {})):
            leaf = param_path.rsplit(".", 1)[-1]
            if (
                SECRET_PARAM_NAMES.search(leaf)
                and isinstance(value, str)
                and value
                and not value.startswith("=")
                and len(value) > 12
            ):
                errors.append(f"{where}: parameter '{param_path}' looks like a literal secret")

        operation = node.get("parameters", {}).get("operation")
        if node.get("type") in EXTERNAL_NODE_TYPES and operation not in NO_RETRY_OPERATIONS:
            if node.get("disabled"):
                continue
            if not node.get("retryOnFail"):
                errors.append(f"{where}: external call must set retryOnFail")
            if int(node.get("maxTries", 3 if node.get("retryOnFail") else 0)) < 3:
                errors.append(f"{where}: maxTries must be >= 3")
            if not node.get("waitBetweenTries"):
                errors.append(f"{where}: waitBetweenTries must be set (backoff)")
    return errors


# Compiles each Code node the way n8n runs it (the body of an async function).
_SYNTAX_CHECK = r"""
const vm = require('vm');
let input = '';
process.stdin.on('data', (d) => (input += d)).on('end', () => {
  const errors = [];
  for (const [where, code] of JSON.parse(input)) {
    try { new vm.Script(`(async function () {\n${code}\n})`); }
    catch (e) { errors.push(`${where}: JavaScript syntax error: ${e.message}`); }
  }
  process.stdout.write(JSON.stringify(errors));
});
"""


def check_code_syntax(files: list[Path]) -> list[str]:
    """Syntax-check every Code node with Node.js (skipped with a note if node is missing)."""
    snippets = []
    for path in files:
        try:
            wf = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for node in wf.get("nodes", []):
            code = node.get("parameters", {}).get("jsCode")
            if node.get("type") == "n8n-nodes-base.code" and isinstance(code, str):
                snippets.append((f"{path.name} › {node.get('name', '?')}", code))
    node_bin = shutil.which("node")
    if not snippets:
        return []
    if node_bin is None:
        print("lint_workflows: node not found, Code node syntax not checked")
        return []
    proc = subprocess.run(  # noqa: S603 - fixed argv, code passed on stdin
        [node_bin, "-e", _SYNTAX_CHECK], input=json.dumps(snippets),
        capture_output=True, text=True, check=True, encoding="utf-8",
    )  # fmt: skip
    errors: list[str] = json.loads(proc.stdout)
    return errors


def main(argv: list[str]) -> int:
    folder = Path(argv[1]) if len(argv) > 1 else ROOT / "workflows"
    files = sorted(folder.glob("*.json"))
    if not files:
        print(f"lint_workflows: no workflow files in {folder} (nothing to check)")
        return 0
    errors = [e for f in files for e in lint_workflow(f)] + check_code_syntax(files)
    for error in errors:
        print(f"ERROR {error}")
    print(f"lint_workflows: {len(files)} file(s), {len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
