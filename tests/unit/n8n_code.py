"""Run an exported n8n Code node under Node.js with stubbed $, $input and $env.

Tests use it to check the exact code n8n runs (taken from workflows/*.json), not a copy.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
NODE = shutil.which("node")

_HARNESS = r"""
const code = process.argv[1];
let input = '';
process.stdin.on('data', (d) => (input += d)).on('end', async () => {
  const out = [];
  for (const c of JSON.parse(input)) {
    const $ = (name) => {
      if (!(name in c.nodes)) throw new Error(`test stub: no data for node "${name}"`);
      return { first: () => ({ json: c.nodes[name] }), isExecuted: true };
    };
    const $input = { first: () => ({ json: c.input }), all: () => [{ json: c.input }] };
    const run = new Function('$', '$input', '$env', '$execution',
      `return (async () => {\n${code}\n})();`);
    try {
      const execution = { id: 'test', resumeFormUrl: 'http://n8n/form-waiting/test' };
      const result = await run($, $input, c.env, execution);
      out.push({ ok: result.map((r) => r.json) });
    } catch (e) {
      out.push({ error: e.message });
    }
  }
  process.stdout.write(JSON.stringify(out));
});
"""


def node_code(workflow_file: str, node_name: str) -> str:
    workflow = json.loads((ROOT / "workflows" / workflow_file).read_text(encoding="utf-8"))
    node = next(n for n in workflow["nodes"] if n["name"] == node_name)
    return str(node["parameters"]["jsCode"])


def run_node(code: str, cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Each case: {"nodes": {name: json}, "input": json, "env": {...}} -> {"ok": [json...]} or
    {"error": message}."""
    assert NODE, "node is required"
    full = [{"nodes": {}, "input": {}, "env": {}, **c} for c in cases]
    proc = subprocess.run(  # noqa: S603
        [NODE, "-e", _HARNESS, code],
        input=json.dumps(full), capture_output=True, text=True, check=True, encoding="utf-8",
    )  # fmt: skip
    result: list[dict[str, Any]] = json.loads(proc.stdout)
    return result


def gemini_response(payload: dict[str, Any]) -> dict[str, Any]:
    return {"candidates": [{"content": {"parts": [{"text": json.dumps(payload)}]}}],
            "usageMetadata": {"promptTokenCount": 120, "candidatesTokenCount": 80}}  # fmt: skip
