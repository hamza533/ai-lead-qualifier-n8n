# Real-key spot check (5 leads)

Runs 2026-11-27 · model `gemini-3.5-flash` · n8n 2.49.6 · real Tavily and Gemini

> This is **not** the 30-lead evaluation. On 2026-11-27 Gemini's free tier allowed 20
> requests per model per day, and a lead needs 3 Gemini calls (plus 1 for the judge), so
> `make eval` stopped after a few leads. These are the leads that finished: three from
> `eval/leads.jsonl` (judged) and two Flexport runs from the first live test (one dry run,
> one live). All five are hot leads, so this says nothing yet about warm/cold accuracy.
> Run `make eval` on Gemini's paid tier for the full numbers (`eval/results.md`).

| Metric | Result |
|---|---|
| Hot leads scored hot | **5/5** (scores 93–100) |
| Factual claims in drafts traceable to the message or sources (LLM judge, 3 drafts) | **9/9**¹ |
| Drafts flagged by the code checks | 0/5 |
| Research status | ok on 5/5, 0 unsourced facts dropped |
| Time from submission to approval request, median (range) | **81 s** (20–142 s)² |
| Avg tokens per lead (in / out) | 7,185 / 1,347 |
| Avg Tavily credits per lead | 2 |
| Estimated paid-tier cost per lead | **≈ $0.026** (Gemini ≈ $0.010 at the ceiling price, Tavily $0.016)³ |

¹ The judge also listed the greeting ("Hi Marta") as unsupported, because the contact's
name is withheld from the model on purpose. The judge prompt now ignores greetings.

² Almost all of the time is Gemini: in the slowest runs single calls took 41–91 s while the
model was under load; the same lead took 20 s end to end when it wasn't.

³ `gemini-3.5-flash` isn't on Gemini's pricing page; `eval/prices.json` uses the Gemini 3.8
Flash list price as a ceiling.

## Leads

| Lead | Company | Tier (score) | s to approval request | Tokens in / out | Claims supported |
|---|---|---|---|---|---|
| hot-01 | Freightos | hot (100) | 109.0 | 7,881 / 1,299 | 3/3 (+ greeting) |
| hot-02 | Shippo | hot (100) | 81.1 | 7,774 / 1,297 | 3/3 |
| hot-03 | Loadsmart | hot (100) | 66.7 | 6,387 / 1,433 | 3/3 |
| first test, dry run | Flexport | hot (93) | 20 | 6,966 / 1,438 | not judged |
| first test, live | Flexport | hot (93) | 142 | 6,916 / 1,269 | not judged |
