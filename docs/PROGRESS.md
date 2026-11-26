# PROGRESS – handoff log

## Status
**Current milestone:** M6 – Errors + reliability (next)

| # | Milestone | Status |
|---|---|---|
| M0 | Repo foundation | done (merged to `main` locally) |
| M1 | Intake + validation | done (merged to `main` locally) |
| M2 | Enrichment sub-workflow | done (merged to `main` locally) |
| M3 | Scoring sub-workflow | done (merged to `main` locally) |
| M4 | Draft + Slack approval | done (merged to `main` locally) |
| M5 | Send + CRM sub-workflow | done (merged to `main` locally) |
| M6 | Errors + reliability | not started |
| M7 | Evaluation | not started |
| M8 | Production profile + docs | not started |
| M9 | Final check | not started |

**Done in M0:** AGENTS.md (+ gotchas), CLAUDE.md, Makefile, docker compose (n8n 2.49.6 + Postgres 16.6, `test` profile with mock server + `docker-compose.test.yml` overlay), `.env.example`, `.gitignore`, uv/pytest harness, FastAPI mock server (Tavily + Gemini, failure injection), workflow JSON linter + tests, admin script (wait/import/export/credentials via n8n CLI, fixed IDs), CI (lint/test + e2e job), MIT LICENSE, CHANGELOG, architecture with sub-workflow contracts, DECISIONS.

**Done in M1:** `intake-webhook` (HMAC over raw body → 401; 422 invalid, 200 spam/duplicate, 202 accepted), `intake-form` (hosted form, `ignoreBots`, hidden honeypot), shared `sub-validate` (normalisation, website/email domain, free-mail flag, spam rules, 24 h idempotency via the `leads` table), `main-lead-intake` pipeline entry (started async). `config/icp.json`, `db/migrations/001_leads.sql` + `make migrate`, `make seed` + `sample_data/leads.jsonl`, API-key bootstrap, activation via public API. Stack moved to Postgres 17.6 + external task runners. 22 intake e2e tests (`tests/e2e/test_intake.py`, 24 with the smoke tests), green on a from-scratch rebuild. See DECISIONS 12–19.

**Done in M2:** `sub-enrich` (Tavily search → extract up to 3 pages → Gemini profile with `responseSchema` → grounding guard), statuses `ok`/`partial`/`failed`, retries 3× then graceful degradation (lead continues as `enrichment_failed`, scored on form data only), pipeline stores profile + usage (migration `002`). Mock: company aliases, schema-based Gemini task detection, third-party page extraction. 10 enrichment e2e tests. `make import` now activates in dependency order derived from workflow references (unit-tested; the old name-based order broke on a fresh rebuild).

**Done in M3:** `sub-score` (rating prompt with criteria + rating guides, no names/emails/weights, injection warning; Gemini `responseSchema`; "Compute score" Code node: points, score, tier, `issues` for missing/invalid ratings and unresearched evidence), pipeline stores score/tier/scorecard (migration `003`). `tests/unit/test_score_maths.py` runs the exported node under Node.js vs a Python reference (300 seeded rating sets + edge cases). Linter compiles Code nodes. Mock per-task Gemini failures (`gemini:score`). 9 scoring e2e tests; enrichment tests now assert `enrichment_status` (status moves on to `scored`).

**Done in M4:** `sub-draft` (style guide + message + research → Gemini draft → code checks: forbidden phrases, unsupported figures, unread sources, booking link), approval request in Slack (HTTP) with a "Review and decide" button to an n8n Wait-node form (approve / approve with edits / reject, reviewer name), timeout → `needs_manual_follow_up`, threaded reminders (`approval-reminders`), ops webhook, eval auto-approve. Test stack fakes Slack/HubSpot/SMTP. See DECISIONS 28–35.

**Done in M5:** approved email via SMTP (demo allow-list redirect), `sub-crm-update` (HubSpot v3: contact upsert by email, company by domain/name, association, `ai_*` properties, note, follow-up task; DRY_RUN records the calls), Slack message updated with the outcome, final statuses, cold path, `daily-cold-digest` (digest + retention purge, also via ops `run_digest`), `make hubspot-setup`. Migration 005 fixes a column clash found by the e2e tests. 9 send/CRM e2e tests, 2 dry-run tests.

**Next step:** M6 on `feat/m6-errors`: `error-handler` workflow (alert to the Slack alerts channel with execution link and masked email; lead → `error_recoverable`), replay of recoverable leads via the ops webhook, CI running both e2e passes.

## Blockers / open questions
- **No GitHub remote yet.** Milestones are merged locally with `--no-ff`; CI runs once the repo is pushed. Creating the public repo needs the owner's OK.
- **GNU make is not installed on the dev machine** (winget's SourceForge download failed twice). Run the targets' one-liners with `uv run …` directly, or install make (`winget install ezwinports.make`, or `choco install make`).
- **uv on Windows:** run uv from PowerShell; in Git Bash, uv's Python 3.12 junction isn't resolved.
- **Port 5678 is used by another local n8n**, so this machine's `.env` sets `N8N_HOST_PORT=5680` (N8N_WEBHOOK_URL/N8N_URL match).
- Accounts still needed (from M4; mocks cover earlier milestones): HubSpot private app, Slack app, Tavily key, Gemini key, SMTP/Gmail app password, cloudflared.
- Showcase numbers on `docs/ui` screens 1, 4 and 7 are placeholders; replace them with real `eval/results.md` values after M7 and re-render (see `docs/ui/README.md`).

## How to verify
```
make setup        # uv sync + .env with generated secrets
make dev          # n8n + Postgres → http://localhost:${N8N_HOST_PORT} (owner login: .env N8N_INSTANCE_OWNER_EMAIL / N8N_OWNER_PASSWORD)
make check        # ruff, ruff format --check, mypy --strict, workflow lint (incl. Code node syntax), 38 unit tests
make test-e2e     # boots n8n + runners + mock (DRY_RUN), migrates, imports credentials + workflows, runs pytest -m e2e (43 tests: 2 smoke + 22 intake + 10 enrichment + 9 scoring)
make seed         # posts sample_data/leads.jsonl to the signed webhook (expect 202, 202, 202, 202, 200 spam)
```
Expected: `n8n ready at http://localhost:5680`, `created/updated 6 credentials`, `activated` ×6, `38 passed`, `43 passed`.

## Session log
- 2026-11-25 – Claude Code – Repo initialised; docs, architecture and progress plan written.
- 2026-11-26 – Claude Code – M0 foundation built and verified (n8n boots on Postgres, owner from env, credentials import encrypted with fixed IDs, check + e2e smoke green).
- 2026-11-26 – Claude Code – Stitch showcase exported to docs/ui (7 frames 1920×1080 + full pages + HTML + design tokens); invented claims and real-looking domains corrected.
- 2026-11-26 – Claude Code – M1 intake + validation: webhook/form intakes, sub-validate, leads ledger, Postgres 17 + external runners; 24 e2e tests green on a fresh rebuild.
- 2026-11-26 – Claude Code – M2 enrichment: sub-enrich with grounding guard and graceful degradation, usage tracking; 34 e2e tests green on a fresh rebuild.
- 2026-11-26 – Claude Code – M3 scoring: sub-score with deterministic Compute score node, maths unit-tested on the exported node code, Code-node syntax lint; 43 e2e tests.
- 2026-11-26 – Claude Code – M4 draft + approval: sub-draft with code checks, Slack request + Wait-node form (approve/edit/reject/timeout), threaded reminders, ops webhook, eval auto-approve; unit tests run the exported Check draft / Read decision code; 11 approval e2e tests.
- 2026-11-27 – Claude Code – M5 send + CRM: SMTP send with demo redirect, sub-crm-update (HubSpot v3), Slack outcome update, cold path, daily digest + purge, hubspot-setup; fixed the sent-email column clash; 9 + 2 dry-run e2e tests.
