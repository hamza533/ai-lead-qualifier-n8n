# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]
### Added
- Repo foundation: AGENTS.md, Makefile, docker compose (pinned n8n 2.49.6), Python test harness with mock server, workflow JSON linter, CI.
- Showcase visuals in `docs/ui` (Stitch export, 1920×1080 frames, render script).
- Intake (M1): `intake-webhook` (HMAC-signed, 401/422/200/202 responses), `intake-form` (hosted form, bot filter, honeypot), shared `sub-validate` (normalisation, free-mail flag, spam rules, 24 h idempotency), `main-lead-intake` pipeline entry.
- `config/icp.json` (criteria, weights, tiers, free-mail domains, spam rules).
- `leadpilot` database with a `leads` ledger (`db/migrations`, `make migrate`).
- `make seed` with synthetic sample leads; 24 end-to-end tests for intake.
- `make import` activates workflows in dependency order derived from their references.
- Scoring (M3): `sub-score` (Gemini rates each `config/icp.json` criterion 0–3 with reason and evidence; the "Compute score" Code node computes points, the 0–100 score and the tier, and reports invalid or missing ratings as 0 with an issue); the pipeline stores score, tier and the scorecard (migration `003`). Unit tests run the exported node code against a Python reference; 9 end-to-end tests. The workflow linter now compiles every Code node. The mock can fail one Gemini task (`gemini:score`).
- Enrichment (M2): `sub-enrich` (Tavily search + extract, Gemini structured profile, grounding guard that drops facts citing unread pages, `ok`/`partial`/`failed` status, retries then graceful degradation); the pipeline stores the profile and per-lead usage (migration `002`). 10 end-to-end tests; mock server matches companies by name and picks Gemini answers by response schema.

### Changed
- Postgres 17.6 (n8n 2.49 no longer fully supports 16); Code nodes run in an external `task-runners` container; `WEBHOOK_URL` renamed to `N8N_WEBHOOK_URL`.
- `make import` activates workflows through the public API (sub-workflows first) and creates an API key when needed.
- Reply draft and approval (M4): `sub-draft` with code checks, Slack approval request + n8n form (approve / edit / reject / timeout), threaded reminders, ops webhook.
- Send + CRM (M5): SMTP send with demo allow-list redirect, `sub-crm-update` (HubSpot v3), Slack outcome update, cold-lead digest + retention purge, `make hubspot-setup`.
- Errors (M6): active `error-handler` (alerts with masked email, `error_recoverable`), pipeline start marker, `replay` via the ops webhook, `make ops`.
- Evaluation (M7): 30-lead test set + duplicate + spam, `make eval` / `make eval-mock` with an LLM grounding judge, latency, usage and cost.
- Production profile (M8): `deploy/azure/` Bicep (n8n queue mode), deploy workflow (disabled by default), CodeQL, Dependabot, Trivy, full README.
