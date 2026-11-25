# AGENTS.md

## Project
Every new lead researched, scored and answered within minutes, with a human approving every email. Built as n8n workflows (n8n Community Edition, self-hosted). Full requirements: docs/SPEC.md. Shared rules: docs/CONVENTIONS.md (SPEC.md wins where they differ).

## Start here
1. Read docs/PROGRESS.md (current status + next step).
2. Read docs/SPEC.md, docs/architecture.md (workflow contracts) and docs/DECISIONS.md before changing the stack.

## Commands
make setup | make dev | make test | make lint | make check | make eval | make seed
make export | make import | make credentials | make hubspot-setup | make tunnel
make test-e2e (boots n8n + mock server, imports, runs pytest -m e2e) | make e2e-down

Without GNU make, every target is a one-liner in the Makefile you can run directly, e.g. `uv run python -m scripts.n8n_admin import`.

## Structure
```
workflows/      exported n8n workflow JSON (one file per workflow, fixed IDs)
config/         icp.json + reply_style.md, mounted read-only into n8n
scripts/        admin (import/export/credentials), workflow linter, env init, seed, hubspot setup
tests/          unit tests, e2e tests (pytest -m e2e), mock_server/ (FastAPI Tavily + Gemini mock)
eval/           30-lead evaluation set, harness, committed results
deploy/azure/   Bicep production profile (n8n queue mode)
docs/           SPEC, CONVENTIONS, PROGRESS, DECISIONS, architecture, ui/
```

## Rules
- Follow docs/SPEC.md stack; adding a dependency requires a DECISIONS.md entry.
- `make check` must pass before committing; never commit secrets.
- Small conventional commits on a feat/ or fix/ branch.
- End every session by updating docs/PROGRESS.md (status, next step, session log line).

## MCP servers
None by default (no Next.js UI, no Neon). If a newer n8n version offers its own MCP server or workflow-building MCP features, you may use them while building; record that in docs/DECISIONS.md and add the setup line here.

## Gotchas
- **Edit workflows in n8n, then `make export`.** Never hand-edit `workflows/*.json` while n8n is running; if you must, stop n8n, edit, then `make import`. Workflow IDs are fixed (see `scripts/n8n_admin.py` `WORKFLOW_FILES`), so new workflows need an entry there.
- **Credentials are never exported.** `make credentials` creates them from `.env` with fixed IDs; workflows reference them by ID and name only. CI (`scripts/lint_workflows.py`) fails on inline credential data or secret-looking strings.
- **The Slack interactivity URL must be public.** Run `make tunnel` and set `WEBHOOK_URL` to the tunnel URL, then restart n8n, before testing Slack approvals.
- **Gemini free-tier limits** (requests per minute/day are low and change; see https://ai.google.dev/gemini-api/docs/rate-limits). The eval harness throttles and caches; free-tier data may be used by Google, so only synthetic/public data goes through it.
- **Score maths lives in the Code node** in `sub-score` (`points = rating/3*weight`, total normalised to 0–100). The model only rates criteria; never let it produce the total.
- **`DRY_RUN=true`** skips real HubSpot, Slack and email writes (CI/e2e). **`EVAL_AUTO_APPROVE=true`** auto-approves drafts and is ignored unless `DEMO_MODE=true`.
- **Execution pruning** is on (`EXECUTIONS_DATA_PRUNE=true`, 336 h). Execution data older than 14 days is deleted, so evaluation reads results soon after each run.
- **n8n 2.x specifics:** Code nodes run in task runners; `$env` access is enabled on purpose (`N8N_BLOCK_ENV_ACCESS_IN_NODE=false`) for non-secret settings only; `node:crypto` is the only allowed built-in; file nodes can only read `/home/node/.n8n-files` (the mounted `config/`). Workflows are activated by import (`--activeState=fromJson`), then n8n is restarted.
- **Windows:** run make from Git Bash; `make` is not bundled with Git for Windows.
