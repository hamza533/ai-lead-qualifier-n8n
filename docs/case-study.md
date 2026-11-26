# Upwork case study (draft)

> Fill in the bracketed numbers from `eval/results.md` after `make eval` with real keys.

**Title:** AI lead qualification agent in n8n: researched, scored and answered in minutes, with a human approving every email

**Problem.** A B2B service business got inbound leads from its website and form tools. Each one waited hours for a reply while someone looked up the company, judged the fit and wrote an email; good leads went cold and nothing was recorded consistently in the CRM.

**Solution.** An n8n agent the client can see and change without a developer:
- Takes leads from a hosted form or any form tool (HMAC-signed webhook), filters spam and duplicates.
- Researches the company on the web (Tavily) and builds a sourced profile with Gemini; every fact must cite a page that was actually read.
- Scores the lead against the client's ideal-customer profile, kept in a simple config file: the model rates each criterion with a reason, and code computes the score and tier, so it is explainable and auditable.
- Drafts a personal reply in the client's style, checked in code for unsupported claims, and asks the sales team in Slack: approve, edit or reject in one click. Reminders after 4 h; manual follow-up after 24 h.
- Sends the email and updates HubSpot: contact, company, score properties, a research note and a follow-up task. Cold leads get a daily digest instead of an email.
- Failures alert a Slack channel and leave the lead recoverable, replayable with one call.

**Stack.** n8n (self-hosted, Postgres, task runners) · Gemini 2.5 Flash · Tavily · Slack · HubSpot CRM v3 · SMTP · Postgres · pytest with mocks for every external service in CI · Azure Container Apps (n8n queue mode), Postgres Flexible Server, Redis, Key Vault (Bicep, validated in CI).

**Result.** Researches and scores a lead in about [N] s and has a reply waiting in Slack within [p50] s; [X]% tier accuracy on 30 test leads; [Y]% of email claims traceable to the lead's message or sources; approval in one click; about $0.02 per lead in production API costs. Spam and duplicate submissions are blocked 100% of the time (tested), and an existing CRM contact is always updated, never duplicated (tested).
