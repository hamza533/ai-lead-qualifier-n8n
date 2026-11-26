"""Static checks on db/migrations (they are plain SQL applied in order by make migrate)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = sorted((ROOT / "db" / "migrations").glob("*.sql"))
# 004 re-added "email" (a no-op that hid a bug); fixed by 005. Applied migrations stay as they are.
KNOWN_NOOPS = {("004_approval_crm_alerts", "email")}


def _columns_created(sql: str) -> list[str]:
    match = re.search(r"CREATE TABLE IF NOT EXISTS leads \((.*?)\n\);", sql, re.S)
    if not match:
        return []
    return [line.split()[0] for line in match.group(1).splitlines()
            if line.strip() and not line.strip().startswith("--")]  # fmt: skip


def test_migration_names_are_numbered_and_safe() -> None:
    assert MIGRATIONS
    for i, path in enumerate(MIGRATIONS, start=1):
        assert re.fullmatch(r"\d{3}_[a-z0-9_]+", path.stem), path.name
        assert int(path.stem[:3]) == i, f"{path.name} breaks the numbering"


def test_no_migration_adds_a_column_that_already_exists() -> None:
    """ADD COLUMN IF NOT EXISTS silently does nothing when the column exists."""
    existing: set[str] = set()
    for path in MIGRATIONS:
        sql = path.read_text(encoding="utf-8")
        existing.update(_columns_created(sql))
        for column in re.findall(r"ADD COLUMN IF NOT EXISTS\s+([a-z_]+)", sql):
            if (path.stem, column) in KNOWN_NOOPS:
                continue
            assert column not in existing, f"{path.name} re-adds existing column {column!r}"
            existing.add(column)


def test_every_column_the_workflows_write_exists() -> None:
    created = set()
    for path in MIGRATIONS:
        sql = path.read_text(encoding="utf-8")
        created.update(_columns_created(sql))
        created.update(re.findall(r"ADD COLUMN IF NOT EXISTS\s+([a-z_]+)", sql))
    written: set[str] = set()
    for wf in (ROOT / "workflows").glob("*.json"):
        text = wf.read_text(encoding="utf-8")
        for update in re.findall(r"UPDATE leads SET(.*?)WHERE", text, re.S):
            written.update(re.findall(r"(?:\\n|\s)+([a-z_]+) = ", update))
    assert written, "no UPDATE statements found"
    assert written <= created, f"columns written but never created: {written - created}"
