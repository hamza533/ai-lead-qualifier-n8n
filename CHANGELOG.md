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
- Enrichment (M2): `sub-enrich` (Tavily search + extract, Gemini structured profile, grounding guard that drops facts citing unread pages, `ok`/`partial`/`failed` status, retries then graceful degradation); the pipeline stores the profile and per-lead usage (migration `002`). 10 end-to-end tests; mock server matches companies by name and picks Gemini answers by response schema.

### Changed
- Postgres 17.6 (n8n 2.49 no longer fully supports 16); Code nodes run in an external `task-runners` container; `WEBHOOK_URL` renamed to `N8N_WEBHOOK_URL`.
- `make import` activates workflows through the public API (sub-workflows first) and creates an API key when needed.
