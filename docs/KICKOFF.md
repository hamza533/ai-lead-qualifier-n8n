# Kickoff – instructions for the AI coding agent

**Paste this into Claude Code (or any AI coding tool) to start:**
> Read `docs/KICKOFF.md`, then `docs/SPEC.md` and `docs/CONVENTIONS.md`, and build this project milestone by milestone as described in KICKOFF.md.

---

## Your job
Build `ai-lead-qualifier-n8n` exactly as described in `docs/SPEC.md`, following `docs/CONVENTIONS.md`.

This project is **n8n-first**, so some CONVENTIONS defaults don't apply. `SPEC.md` section 9 lists them. Where they conflict, `SPEC.md` wins. Don't add or swap tools without a `docs/DECISIONS.md` entry explaining why.

## How to work
1. **Plan first.** Before building, create `docs/architecture.md` (workflow diagram, sub-workflow contracts with the input and output JSON of each one, and the config files) and `docs/PROGRESS.md` using the milestones below. Commit both.
2. **Build workflows in a running n8n instance,** using its UI or its public API. Then `make export` writes them to `/workflows`. Never hand-edit the exported JSON while n8n is running.
3. **One milestone at a time** on `feat/<milestone>` branches:
   - Small conventional commits.
   - `make check` passes before every commit.
   - Merge when the milestone's checks pass.
4. **After each milestone:** update `docs/PROGRESS.md` (status, next step, how to verify, session-log line) and `docs/DECISIONS.md`.
5. **Ask the user only when truly blocked,** usually for accounts or credentials (see the list at the end). Otherwise pick the option that fits the spec and record it.
6. **Never commit secrets.** Workflows reference credentials by name only. CI checks this.

## Milestones
| # | Milestone | Done when |
|---|---|---|
| M0 | **Repo foundation** | `AGENTS.md` (template + gotchas from SPEC), `CLAUDE.md` (`@AGENTS.md`), `Makefile` (setup, dev, check, test, eval, export, import, credentials, hubspot-setup, tunnel), `docker-compose.yml` (pinned n8n + Postgres, plus a `test` profile with the mock server), `.env.example`, `.gitignore`, Python test harness skeleton (`uv`, pytest), CI (workflow JSON lint + harness lint), MIT `LICENSE`, `CHANGELOG.md`. `make setup && make dev` boots n8n. |
| M1 | **Intake + validation** | Form Trigger and HMAC-signed webhook, normalisation, spam and free-mail checks, idempotency check. Tests cover a bad signature (401), a duplicate and spam. |
| M2 | **Enrichment sub-workflow** | Tavily search and extract plus a Gemini structured profile through HTTP Request nodes with environment base URLs. Mock server fixtures. Retries and the "website unreachable" path. |
| M3 | **Scoring sub-workflow** | `config/icp.json`, Gemini per-criterion ratings, a Code node computing the weighted total and tier. A test proves the total equals the weighted ratings. |
| M4 | **Draft + Slack approval** | Grounded reply draft from `config/reply_style.md`. Slack Send and Wait custom form (approve / edit / reject), 4-hour reminder, 24-hour timeout path. |
| M5 | **Send + CRM sub-workflow** | Email send (demo allow-list), HubSpot contact and company upsert, custom properties (`make hubspot-setup`), note, follow-up task, Slack message update. Cold-lead path and daily digest. |
| M6 | **Errors + reliability** | Error workflow to the Slack alerts channel, retry settings on every external node, recoverable statuses, execution pruning, `DRY_RUN` flag. A CI end-to-end run against mocks boots n8n, imports, posts leads and asserts the outcomes. |
| M7 | **Evaluation** | `eval/leads.jsonl` (30 leads, tricky cases included), and `make eval` produces `eval/results.md` and `.json` with tier accuracy, grounding, latency and cost. |
| M8 | **Production profile + docs** | `deploy/azure/` Bicep (n8n queue mode: main + workers, Postgres Flexible Server, Azure Cache for Redis, Key Vault, Application Insights), validated in CI, with a deploy workflow disabled by default. README per the CONVENTIONS template, plus the License note, setup guides for each account, production deployment and cost estimate. `make tunnel` documented. |
| M9 | **Final check** | Every acceptance criterion in `SPEC.md` section 9 and the CONVENTIONS section 8 checklist ticked in `PROGRESS.md`. A fresh clone works with `make setup && make dev && make credentials && make import`. |

## What the user does (not the agent)
- Creates a **HubSpot** free account and a private app (scopes: contacts, companies, notes, tasks) and puts the token in `.env`.
- Creates a **Slack** workspace and app: bot token, signing secret, interactivity enabled, and the approval and alerts channels.
- Gets a **Tavily** API key and a **Gemini** API key.
- Sets up a **Gmail app password** (or other SMTP) and a demo inbox for the allow-list.
- Installs **cloudflared** for `make tunnel`.
- Records the demo video at the end.

When you reach a step that needs one of these, stop, list exactly what's needed and where it goes in `.env`, and continue with any unblocked work, using the mock server.
