# AGENTS.md

## Project
Every new lead researched, scored and answered within minutes, with a human approving every email. Built as n8n workflows (n8n Community Edition, self-hosted). Full requirements: docs/SPEC.md. Shared rules: docs/CONVENTIONS.md (SPEC.md wins where they differ).

## Start here
1. Read docs/PROGRESS.md (current status + next step).
2. Read docs/SPEC.md, docs/architecture.md (workflow contracts) and docs/DECISIONS.md before changing the stack.

## Commands
make setup | make dev | make test | make lint | make check | make eval | make seed | make migrate
make export | make import | make credentials | make hubspot-setup | make tunnel | make ops ACTION=…
make test-e2e (test stack: mocks for every external service + mailpit; runs pytest -m "e2e and not dryrun")
make test-e2e-dryrun (same stack with DRY_RUN=true; pytest -m dryrun) | make eval-mock | make e2e-down

Without GNU make, every target is a one-liner in the Makefile you can run directly, e.g. `uv run python -m scripts.n8n_admin import`.

## Structure
```
workflows/      exported n8n workflow JSON (one file per workflow, fixed IDs)
config/         icp.json + reply_style.md, mounted read-only into n8n
db/migrations/  SQL for the leadpilot database (leads ledger), applied by make migrate
sample_data/    synthetic leads for make seed
scripts/        admin (migrate/import/export/credentials/api-key), workflow linter, env init, seed,
                hubspot setup, ops webhook client, db helper, Stitch frame renderer
tests/          unit (incl. exported Code nodes run under Node.js), e2e (pytest -m e2e / dryrun),
                mock_server/ (FastAPI Tavily, Gemini, Slack, HubSpot mock)
eval/           test sets (leads.jsonl, leads_mock.jsonl), harness, prices, committed results
deploy/azure/   Bicep production profile (n8n queue mode) + runbook
docs/           SPEC, CONVENTIONS, PROGRESS, DECISIONS, architecture, case-study, ui/
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
- **The Slack interactivity URL must be public.** Run `make tunnel` and set `N8N_WEBHOOK_URL` to the tunnel URL, then restart n8n, before testing Slack approvals.
- **Gemini free-tier limits** (requests per minute/day are low and change; see https://ai.google.dev/gemini-api/docs/rate-limits). The eval harness throttles and caches; free-tier data may be used by Google, so only synthetic/public data goes through it.
- **Score maths lives in the Code node** "Compute score" in `sub-score` (`points = rating/3*weight`, total normalised to 0–100). The model only rates criteria; never let it produce the total. `tests/unit/test_score_maths.py` runs that node's exported code, so after changing it in n8n, `make export` before `make test`. Never send weights, contact names or emails to the model.
- **Code nodes are syntax-checked by `make lint`** (needs Node.js). If you generate workflow JSON with a script, beware `"""` inside Python triple-quoted strings: it silently ends the string.
- **Pipeline status moves fast in tests:** the pipeline runs in the background, so a test that reads `status` right after a step may already see a later status. Assert on the step's own columns (`enrichment_status`, `score`) instead.
- **`DRY_RUN=true`** skips real HubSpot, Slack and email writes (CI/e2e). **`EVAL_AUTO_APPROVE=true`** auto-approves drafts and is ignored unless `DEMO_MODE=true`.
- **Execution pruning** is on (`EXECUTIONS_DATA_PRUNE=true`, 336 h). Execution data older than 14 days is deleted, so evaluation reads results soon after each run.
- **n8n 2.x specifics:**
  - Code nodes run in the separate `task-runners` container. `node:crypto` is the only allowed built-in, and the **`URL` global is not available** there: parse URLs with string code (see `sub-validate`).
  - `$env` access is enabled on purpose (`N8N_BLOCK_ENV_ACCESS_IN_NODE=false`) for non-secret settings; the only secret read this way is `WEBHOOK_HMAC_SECRET` (DECISIONS 7).
  - File nodes can only read `/home/node/.n8n-files` (the mounted `config/`).
  - **A workflow with a Form Trigger may not contain a "Respond to Webhook" node**; that's why the form and webhook intakes are separate workflows.
  - `import:workflow --activeState` doesn't work in single-instance mode. `make import` activates through the public API instead, in dependency order derived from the Execute Workflow references (`activation_order` in `scripts/n8n_admin.py`).
  - n8n's hosted form returns 401 to bot user agents (`ignoreBots`). Use a browser user agent when testing it with curl.
- **Leads database:** schema changes go in a new numbered file in `db/migrations/` (lowercase letters, digits, underscores), applied by `make migrate`. Never edit an applied migration.
- **Mock server:** companies live in `tests/mock_server/fixtures/companies.json`, matched by domain or `aliases` (company name). Gemini answers are chosen by the request's `responseSchema` keys, so keep the schema property names (`what_they_do`, `ratings`, `subject`, `claims`) stable or update `_gemini_task`. Tests steer failures with `POST /_control/fail`; reset with `/_control/reset`.
- **Enrichment never stops a lead:** external nodes in `sub-enrich` continue on error after 3 tries. Don't switch them to "stop workflow"; failures surface as `enrichment_status` + `error` on the lead row.
- **Webhook signing:** `X-Signature-256: sha256=<hex HMAC-SHA256(raw body, WEBHOOK_HMAC_SECRET)>`. `make seed` and `tests/e2e/conftest.py` show how to sign.
- **Windows:** run make from Git Bash; `make` is not bundled with Git for Windows.
- **Every write to Slack, HubSpot or SMTP has a DRY_RUN branch** that records the call in `leads.dry_run_actions`. A new write node needs one too, plus a `dryrun` test.
- **Slack replies HTTP 200 with `ok: false`** on errors; every Slack HTTP node is followed by a Code node that throws on `!ok`.
- **The error workflow must stay active**, and sub-workflow failures are reported by their caller (`lpSub*` IDs are skipped), so keep sub-workflow IDs starting with `lpSub`.
- **Wait-node forms return answers keyed by field label** ("Decision", "Your name"), not by field name; "Read decision" accepts both. Resume URLs are signed (`?signature=`).
- **The test stack's credentials point at mailpit** (`make e2e-up` passes `SMTP_HOST=mailpit` …); run `make credentials` again before using the dev stack with real SMTP.
- **Local port clashes:** set `N8N_HOST_PORT` / `MAILPIT_HOST_PORT` in `.env` (and `N8N_URL` / `MAILPIT_URL` to match) if 5678 or 8025 are taken.
- **`make eval` deletes previous eval leads** (`source = 'eval'`) first; otherwise the 24 h duplicate check would ignore the re-run.
- **After the decision, everything runs in `finish-lead`**, loaded from the lead row, so it can be resumed. Never send the email anywhere else, and keep `email_sent_at` written right after the send: that is what stops a replay from emailing the lead twice. Only "Record outcome" writes final statuses and `completed_at`; the error handler only touches leads with `completed_at IS NULL`.
- **"Send email" deliberately has no retry** (notes start with `no-retry:`; the linter requires the reason).
- **Duplicates are claimed in `lead_claims`**, not by querying `leads`; tests that age a lead past 24 h must age its claim too.
- **Alerts go through `sub-alert`** (level `error` from the error handler, `warning` for degraded research). Slack text built from lead or model input must be escaped (`&`, `<`, `>`).
- **n8n's environment is an explicit list** in `docker-compose.yml`. A new workflow setting must be added there (and in `deploy/azure/main.bicep`); never add API keys or passwords to it.
- **Real HubSpot rejects `.test` email domains** (`INVALID_EMAIL`; the mock accepts them). For a live run use a real-looking domain such as `example.com`, and turn off HubSpot's automatic company creation from email domains (README, HubSpot setup), or contacts get a second company.
