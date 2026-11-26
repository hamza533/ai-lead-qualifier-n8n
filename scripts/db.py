"""Query the leadpilot database through the running postgres container (it has no host port)."""

from __future__ import annotations

import json
import subprocess
from typing import Any

from scripts.envfile import ROOT, read_env


def sql(query: str) -> list[list[str]]:
    """Rows as lists of strings (psql unaligned output). Empty lines are dropped, so select
    at least one non-empty column; use rows_json() for values that may contain newlines."""
    env = read_env()
    result = subprocess.run(  # noqa: S603
        ["docker", "compose", "exec", "-T", "postgres", "psql", "-qAt", "-F", "\t",  # noqa: S607
         "-U", env.get("DB_POSTGRESDB_USER", "n8n"),
         "-d", env.get("LEADPILOT_DB_NAME", "leadpilot"),
         "-c", query],
        cwd=ROOT, capture_output=True, text=True, check=True, encoding="utf-8",
    )  # fmt: skip
    return [line.split("\t") for line in result.stdout.splitlines() if line]


def rows_json(query: str) -> list[dict[str, Any]]:
    """Run `SELECT row_to_json(x) FROM (<query>) x` and parse each row."""
    return [json.loads(r[0]) for r in sql(f"SELECT row_to_json(x) FROM ({query}) x")]  # noqa: S608
