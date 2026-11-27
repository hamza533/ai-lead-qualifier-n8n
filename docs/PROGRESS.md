# PROGRESS – handoff log

## Status
**Current milestone:** M9 – Final check. Development and testing are complete against mocks; the remaining items need the owner's accounts (see Blockers).

| # | Milestone | Status |
|---|---|---|
| M0 | Repo foundation | done |
| M1 | Intake + validation | done |
| M2 | Enrichment sub-workflow | done |
| M3 | Scoring sub-workflow | done |
| M4 | Draft + Slack approval | done |
| M5 | Send + CRM sub-workflow | done |
| M6 | Errors + reliability | done (incl. fixes from an independent review, DECISIONS 51–62) |
| M7 | Evaluation | harness + test set done; **real numbers need real Gemini/Tavily keys** |
| M8 | Production profile + docs | done (Bicep validates; README, setup guides, cost estimate) |
| M9 | Final check | done except the items blocked on accounts |

All milestones are on `main` at https://github.com/hamza533/ai-lead-qualifier-n8n (public); CI is green (lint/unit, full e2e + dry-run, eval smoke, Bicep, image scan) and CodeQL passes.

**Real keys:** loaded on 2026-11-27 (`make credentials import hubspot-setup` done). One real lead (Flexport, synthetic contact) ran end to end with `DRY_RUN=true`: Tavily + Gemini research with 6 sources and no unsourced claims, score 93 (hot), a grounded draft, approval through the real form, and all 7 Slack/SMTP/HubSpot calls recorded. Default model is now `gemini-3.5-flash` (DECISIONS 63).

**Next step (owner):** one live lead with `DRY_RUN=false` (real Slack post, email to the allow-listed inbox, HubSpot writes), then `make tunnel` for Slack-button approvals from outside, `make eval` and copy the numbers into the README, `docs/ui` (re-render) and `docs/case-study.md`. Record the demo GIF and video.

## Acceptance criteria (SPEC §9)

| Criterion | Status | Evidence |
|---|---|---|
| `make setup && make dev`, then `make credentials`, `make import`, `make hubspot-setup` → working instance from a fresh clone | ✅ (hubspot-setup needs a real token; unit-tested) | Every e2e run rebuilds from empty volumes: migrate, credentials, import + activate all 14 workflows. |
| Form submission reaches Slack within about a minute with summary, score, per-criterion reasons, sources, draft | ✅ against mocks (2–7 s) | `test_approval.py::test_hot_lead_reaches_slack…` |
| Approve / approve-with-edits / reject / 24 h timeout → correct email, HubSpot, Slack outcome (timeout via short override) | ✅ | `test_send_crm.py`, `test_approval.py` (`APPROVAL_TIMEOUT_HOURS=0.02` in the test stack) |
| No valid HMAC → 401; duplicates within 24 h ignored; existing HubSpot contact updated, not duplicated | ✅ (also simultaneous duplicates) | `test_intake.py`, `test_send_crm.py::test_existing_contact…` |
| Final score always equals the weighted ratings (fixed ratings) | ✅ | `tests/unit/test_score_maths.py` runs the exported node on 300 seeded rating sets + edge cases |
| Forcing Tavily or Gemini to fail → retries → alert in the alerts channel → recoverable status | ✅ | `test_errors.py` (Gemini: error alert + `error_recoverable` + replay; Tavily: retries, warning alert, lead degrades and continues), `test_enrich.py`, `test_resilience.py` |
| Cold leads in the daily digest and HubSpot, no email | ✅ | `test_send_crm.py::test_cold_lead…`, `…daily_digest…` |
| Workflows exported with no credentials/secrets (CI) | ✅ | `scripts/lint_workflows.py` in `make check` |
| `make eval` reproduces the README numbers | ⏳ blocked on keys | Harness verified with `make eval-mock` (`eval/results-mock.md`) |
| CI: JSON lint (parses, pinned versions, retries, error workflow, no secrets); boot n8n, import, pytest e2e against mocks with `DRY_RUN=true` | ✅ green on GitHub | `.github/workflows/ci.yml`: lint/test, full e2e, dry-run e2e, eval-mock, Bicep, image scan; CodeQL; Dependabot |
| Production readiness: encryption key, pruning, Postgres backups, webhook HMAC, least-privilege scopes, retention, pinned n8n + upgrade runbook, Bicep (queue mode, Flexible Server, Redis, Key Vault, App Insights) in CI, cost at 500 and 5,000 leads | ✅ | README "Production deployment", `deploy/azure/` |
| README: License note; setup steps for HubSpot, Slack, Gmail/SMTP, Tavily, Gemini | ✅ | README |
| AGENTS.md Gotchas (edit in n8n + export, credentials never exported, public Slack URL, Gemini limits, score maths in Code node, DRY_RUN/EVAL_AUTO_APPROVE, pruning) | ✅ | AGENTS.md |

**Not applicable (SPEC §9):** built-in user accounts (n8n has owner/members), Alembic (n8n manages its schema; the leads ledger uses plain SQL migrations, DECISIONS 16), Playwright (no custom UI).

## Done checklist (CONVENTIONS §8)
- [x] Every SPEC acceptance criterion passes against mocks (eval numbers pending keys).
- [x] Production readiness met or marked not applicable; `deploy/azure/` Bicep validates (`az bicep build` + lint).
- [x] Handoff: AGENTS.md, CLAUDE.md (`@AGENTS.md`), Makefile targets, this file. A fresh clone runs `make setup && make check` with no tool-specific files.
- [x] `docker compose up` works on a clean machine (verified repeatedly from empty volumes).
- [ ] Evaluation numbers in the README: needs `make eval` with real keys.
- [x] CI green on GitHub.
- [ ] Demo GIF and 60–90 s video: owner records them (`make tunnel`, `docs/ui` frames).
- [x] Live demo: README explains why there is no always-on demo (local + tunnel).
- [x] Upwork case study drafted: `docs/case-study.md` (numbers to fill from `make eval`).

## Blockers / open questions
- **Accounts and keys** (put them in `.env`; nothing else is needed from the owner to finish):
  - `GEMINI_API_KEY` (aistudio.google.com), `TAVILY_API_KEY` (app.tavily.com)
  - `HUBSPOT_PRIVATE_APP_TOKEN` (scopes in README), then `make hubspot-setup`
  - `SLACK_BOT_TOKEN` (`chat:write`), `SLACK_APPROVAL_CHANNEL`, `SLACK_ALERTS_CHANNEL`
  - `SMTP_USER`, `SMTP_PASSWORD` (Gmail app password), `EMAIL_FROM`, `DEMO_EMAIL_ALLOWLIST` (your inbox)
  - `cloudflared` installed for `make tunnel` (then set `N8N_WEBHOOK_URL` to the tunnel URL)
- **Dependabot:** mailpit v1.34.0 (#1) and Python 3.15 for the mock image (#2) merged with green CI. The Postgres 19 bump (#3) was closed: 17 → 19 is a major upgrade that needs a dump/restore and a check that n8n supports it; do it through the README upgrade runbook.
- **This machine:** GNU make isn't installed (run the Makefile one-liners with `uv run …`, or install make); run uv from PowerShell (Git Bash doesn't resolve uv's Python link); ports 5678/8025 are used by another project, so `.env` sets `N8N_HOST_PORT=5680` and `MAILPIT_HOST_PORT=8026`.
- **After running the test stack**, n8n's SMTP credential points at mailpit; run `make credentials` again before using the dev stack with real email.
- **Not verified against the real services** (no keys): Gemini's acceptance of the response schemas, Tavily response shapes beyond the documented ones, HubSpot v3 association type IDs (202/190/204/192), Slack Block Kit rendering. The first real lead with `make tunnel` checks all of them; `DRY_RUN=true` lets you inspect every outgoing payload first.

## How to verify
```
make setup             # uv sync + .env with generated secrets
make check             # ruff, format, mypy --strict, workflow lint (incl. Code node syntax), unit tests
make test-e2e          # fresh test stack (mocks + mailpit), import 14 workflows, full e2e suite
make test-e2e-dryrun   # same stack with DRY_RUN=true
make eval-mock         # evaluation harness smoke run → eval/results-mock.md
make e2e-down
```
Expected: `make check` all green; e2e and dry-run suites all passed; eval-mock writes the report.

## Session log
- 2026-11-25 – Claude Code – Repo initialised; docs, architecture and progress plan written.
- 2026-11-26 – Claude Code – M0 foundation built and verified (n8n boots on Postgres, owner from env, credentials import encrypted with fixed IDs, check + e2e smoke green).
- 2026-11-26 – Claude Code – Stitch showcase exported to docs/ui (7 frames 1920×1080 + full pages + HTML + design tokens); invented claims and real-looking domains corrected.
- 2026-11-26 – Claude Code – M1 intake + validation: webhook/form intakes, sub-validate, leads ledger, Postgres 17 + external runners; 24 e2e tests green on a fresh rebuild.
- 2026-11-26 – Claude Code – M2 enrichment: sub-enrich with grounding guard and graceful degradation, usage tracking; 34 e2e tests green on a fresh rebuild.
- 2026-11-26 – Claude Code – M3 scoring: sub-score with deterministic Compute score node, maths unit-tested on the exported node code, Code-node syntax lint; 43 e2e tests.
- 2026-11-26 – Claude Code – M4 draft + approval: sub-draft with code checks, Slack request + Wait-node form (approve/edit/reject/timeout), threaded reminders, ops webhook, eval auto-approve; unit tests run the exported Check draft / Read decision code; 11 approval e2e tests.
- 2026-11-27 – Claude Code – M5 send + CRM: SMTP send with demo redirect, sub-crm-update (HubSpot v3), Slack outcome update, cold path, daily digest + purge, hubspot-setup; fixed the sent-email column clash; 9 + 2 dry-run e2e tests.
- 2026-11-27 – Claude Code – M6–M9: error handler + sub-alert, replay (resume/restart), resumable finish-lead, race-safe claims, eval harness (30 leads + judge), Azure Bicep (queue mode, private Postgres, secrets as files), CI/CodeQL/Dependabot/Trivy, full README; independent review: 11 findings fixed with tests.
- 2026-11-27 – Claude Code – Pushed to GitHub (public); fixed CI (YAML quoting, trivy-action pinned by SHA, readiness wait before eval-mock, patched mock image CVEs); CI and CodeQL green.
- 2026-11-27 – Claude Code – Real keys: switched to gemini-3.5-flash (2.5 Flash is closed to new users, 3.8 Flash was overloaded), first real dry-run lead passed end to end; `make credentials` no longer warns about the unused Slack signing secret.
