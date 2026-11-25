# Google Stitch prompt – showcase visuals

This project has no custom app UI: the real product runs in n8n (form), Slack (approval) and HubSpot (CRM). These designs are **showcase visuals** for the demo video, the README and the Upwork cover. **They are not built as an app.** In the video, use real screen recordings for the n8n, Slack and HubSpot moments, and use these frames for the opener, the explainers and the results.

Paste everything inside the code block into Stitch and choose **Web**. Export each screen as a PNG at 1920×1080 and save it here as `01-landing.png` … `07-results.png`.

```
Design a set of 7 polished showcase screens (web, desktop 1440px wide) for "LeadPilot" — an AI lead qualification agent that researches every new lead, scores it with reasons, drafts a personalised reply, asks a human to approve it in a team chat, then updates the CRM. Use ONE consistent design system. Use realistic sample data (no lorem ipsum). Do not draw or imitate the user interface of any real product (no Slack, HubSpot, Gmail or n8n look-alikes, no real logos); show chat, CRM and email only as generic, unbranded panels.

SAMPLE STORY (use these exact details everywhere)
Business using LeadPilot: "Northwind Digital", a web development agency. Booking link: northwind.example/book.
Lead: Daniel Reyes, Head of Operations at "Harbor Logistics" (harborlogistics.example), email daniel.reyes@harborlogistics.example. Message: "We need a customer portal for shipment tracking, ideally live by Q2. Budget around $25–40k." Budget range: $25k–$50k.
Research found: mid-size freight logistics company, ~180 employees, offices in Rotterdam and Singapore, launched a new cold-chain service this year (2 source links).
Score: 82 / 100 — HOT. Criteria: Industry fit 3/3 (weight 25), Company size 2/3 (weight 20), Role seniority 3/3 (weight 20), Budget 3/3 (weight 20), Clear need 3/3 (weight 15). Time from form to approval request: 48 seconds.

GLOBAL STYLE
Confident, modern B2B SaaS style. Light theme, neutral slate grays with one violet accent color. Tier colors: hot = red-orange, warm = amber, cold = blue-gray; success = green. Use shadcn/ui-style components (Tailwind CSS): cards, badges, progress bars, tables, tabs, avatars with initials, timeline. Rounded corners, soft shadows, generous spacing, readable 14–15px text, accessible contrast. Simple line icons. No stock photos of people.

SCREEN 1 — LANDING PAGE (video opener / Upwork cover)
Hero headline "Every lead researched, scored and answered in minutes", subline "An AI agent that qualifies new leads, drafts a personal reply, and waits for your approval before anything is sent." Buttons "See how it works" and "View the workflow". Right side: a floating lead scorecard card for Daniel Reyes showing "82 · HOT", three criteria bars, and a "Draft ready for approval" chip. Below: a 5-step horizontal flow (New lead → Research → Score → Human approval → CRM updated) with icons; a 3-card feature row (Explainable scores, Grounded replies — no invented claims, Human approves every email); a results strip ("48 s to first reply draft", "100% of claims traceable to sources", "30 test leads evaluated"); footer.

SCREEN 2 — LEAD FORM ON A BUSINESS WEBSITE
A clean Northwind Digital website "Contact us" section with a form: Name, Work email, Company, Website, Role, Budget range (dropdown), Message (textarea), "Send" button. Filled in with Daniel's details. Small note under the button: "We reply within one business day."

SCREEN 3 — RESEARCH IN PROGRESS (explainer frame)
A centered card titled "Researching Harbor Logistics…" with a vertical step timeline: Validated email ✓, Checked for duplicates ✓, Searched the web (2 sources) ✓, Read company website ✓, Built company profile (in progress spinner). Beside it, a "Company profile" card filling in: what they do, industry, size ~180, locations, recent news — each fact with a small source link icon and a confidence badge (high/medium).

SCREEN 4 — LEAD SCORECARD (explainer frame)
Large score "82 / 100" with a HOT badge and a circular progress ring. A table of 5 criteria: name, rating dots (0–3), weight, points, one-line reason with evidence (e.g., Budget 3/3 — "Stated $25–40k, within target range"). A "How the score is calculated" footnote: "AI rates each criterion; the total is calculated from your weights." A sources list with 2 links.

SCREEN 5 — APPROVAL REQUEST IN A TEAM CHAT (generic, unbranded)
A generic team-chat window (neutral styling, channel name "#lead-approvals", bot avatar "LeadPilot"). A rich message card: lead name and company, "82 · HOT", top 3 reasons, collapsed sources, and the drafted email (greeting to Daniel, references their cold-chain launch and Q2 portal goal, proposes a 20-minute call with the booking link, signed by Northwind Digital). Buttons: "Approve", "Approve with edits", "Reject". A second state below: the same card updated to "✓ Approved by Sara · email sent · CRM updated" in green.

SCREEN 6 — CRM RECORD + EMAIL SENT (generic, unbranded, split view)
Left: a generic CRM contact record for Daniel Reyes / Harbor Logistics with properties AI lead score 82, AI lead tier Hot, AI score reasons (multi-line), a note "Enrichment summary + sources + sent email", and a task "Follow up with Daniel — due in 3 days". Right: a generic email reading view showing the sent reply from Northwind Digital to Daniel with the subject "A customer portal for Harbor Logistics' shipment tracking".

SCREEN 7 — RESULTS / EVALUATION
Title "Tested on 30 leads". Stat cards: Tier accuracy 90%, Claims traceable to sources 100%, Median time to approval request 48 s, Duplicates & spam blocked 100%. A 3×3 confusion matrix (Expected vs Predicted: Hot / Warm / Cold). A small table of "Tricky cases handled" (personal email from a good company, vague message, unreachable website, duplicate submission, spam) with green checks. A cost card: "≈ $0.00X per lead in production".
```
