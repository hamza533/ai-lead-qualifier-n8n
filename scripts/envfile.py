"""Minimal .env reader/writer (no dependency needed for KEY=VALUE files)."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value


def read_env(path: Path = ENV_PATH) -> dict[str, str]:
    """Parse KEY=VALUE lines; process environment variables win over the file."""
    values: dict[str, str] = {}
    if path.exists():
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = _unquote(value)
    for key in list(values):
        if key in os.environ:
            values[key] = os.environ[key]
    return values


def set_values(updates: dict[str, str], path: Path = ENV_PATH) -> None:
    """Replace the value of existing keys in place (keeps comments and order)."""
    lines = path.read_text(encoding="utf-8").splitlines()
    for i, raw in enumerate(lines):
        key = raw.partition("=")[0].strip()
        if not raw.lstrip().startswith("#") and key in updates:
            lines[i] = f"{key}={updates[key]}"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
