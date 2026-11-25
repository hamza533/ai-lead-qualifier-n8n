# PROGRESS – handoff log

## Status
**Current milestone:** M0 – Repo foundation (in progress)

| # | Milestone | Status |
|---|---|---|
| M0 | Repo foundation | in progress |
| M1 | Intake + validation | not started |
| M2 | Enrichment sub-workflow | not started |
| M3 | Scoring sub-workflow | not started |
| M4 | Draft + Slack approval | not started |
| M5 | Send + CRM sub-workflow | not started |
| M6 | Errors + reliability | not started |
| M7 | Evaluation | not started |
| M8 | Production profile + docs | not started |
| M9 | Final check | not started |

**Next step:** finish M0 (boot n8n with `make dev`), then M1 on `feat/m1-intake`.

## Blockers / open questions
- Accounts the user still has to create (needed from M4 on; mocks cover earlier milestones): HubSpot private app, Slack app, Tavily key, Gemini key, SMTP/Gmail app password, cloudflared.
- Stitch showcase screens (`docs/ui/01-landing.png` … `07-results.png`) are not exported yet.

## How to verify
```
make setup        # uv sync + creates .env with generated secrets
make dev          # n8n + Postgres; open http://localhost:5678
make check        # ruff, mypy, workflow lint, unit tests
```

## Session log
- 2026-11-25 – Claude Code – Repo initialised; docs, architecture and progress plan written.
