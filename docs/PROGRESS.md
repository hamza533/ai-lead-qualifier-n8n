# PROGRESS – handoff log

## Status
**Current milestone:** M1 – Intake + validation (next)

| # | Milestone | Status |
|---|---|---|
| M0 | Repo foundation | done (merged to `main` locally) |
| M1 | Intake + validation | not started |
| M2 | Enrichment sub-workflow | not started |
| M3 | Scoring sub-workflow | not started |
| M4 | Draft + Slack approval | not started |
| M5 | Send + CRM sub-workflow | not started |
| M6 | Errors + reliability | not started |
| M7 | Evaluation | not started |
| M8 | Production profile + docs | not started |
| M9 | Final check | not started |

**Done in M0:** AGENTS.md (+ gotchas), CLAUDE.md, Makefile, docker compose (n8n 2.49.6 + Postgres 16.6, `test` profile with mock server + `docker-compose.test.yml` overlay), `.env.example`, `.gitignore`, uv/pytest harness, FastAPI mock server (Tavily + Gemini, failure injection), workflow JSON linter + tests, admin script (wait/import/export/credentials via n8n CLI, fixed IDs), CI (lint/test + e2e job), MIT LICENSE, CHANGELOG, architecture with sub-workflow contracts, DECISIONS.

**Next step:** M1 on `feat/m1-intake`: build `main-lead-intake` (Form Trigger + HMAC webhook, normalise, spam/free-mail, idempotency) in the running n8n, `make export`, then e2e tests for 401 / duplicate / spam. Also `config/icp.json` (free-mail domains + spam rules are needed by M1).

## Blockers / open questions
- **No GitHub remote yet.** Milestones are merged locally with `--no-ff`; CI runs once the repo is pushed. Creating the public repo needs the owner's OK.
- **GNU make is not installed on the dev machine** (winget's SourceForge download failed twice). Run the targets' one-liners with `uv run …` directly, or install make (`winget install ezwinports.make`, or `choco install make`).
- **uv on Windows:** run uv from PowerShell; in Git Bash, uv's Python 3.12 junction isn't resolved.
- **Port 5678 is used by another local n8n**, so this machine's `.env` sets `N8N_HOST_PORT=5680` (WEBHOOK_URL/N8N_URL match).
- Accounts still needed (from M4; mocks cover earlier milestones): HubSpot private app, Slack app, Tavily key, Gemini key, SMTP/Gmail app password, cloudflared.
- Showcase numbers on `docs/ui` screens 1, 4 and 7 are placeholders; replace them with real `eval/results.md` values after M7 and re-render (see `docs/ui/README.md`).

## How to verify
```
make setup        # uv sync + .env with generated secrets
make dev          # n8n + Postgres → http://localhost:${N8N_HOST_PORT} (owner login: .env N8N_INSTANCE_OWNER_EMAIL / N8N_OWNER_PASSWORD)
make check        # ruff, ruff format --check, mypy --strict, workflow lint, 15 unit tests
make test-e2e     # boots n8n + mock (DRY_RUN), imports credentials + workflows, runs pytest -m e2e (2 smoke tests)
```
Expected: `n8n ready at http://localhost:5680`, `created/updated 5 credentials`, `15 passed`, `2 passed`.

## Session log
- 2026-11-25 – Claude Code – Repo initialised; docs, architecture and progress plan written.
- 2026-11-26 – Claude Code – M0 foundation built and verified (n8n boots on Postgres, owner from env, credentials import encrypted with fixed IDs, check + e2e smoke green).
- 2026-11-26 – Claude Code – Stitch showcase exported to docs/ui (7 frames 1920×1080 + full pages + HTML + design tokens); invented claims and real-looking domains corrected.
