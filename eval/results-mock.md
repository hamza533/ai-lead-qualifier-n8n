# Evaluation results (mock run)

Run 2026-11-26 20:30 UTC · 6 leads · model `gemini-2.5-flash` · n8n 2.49.6 · `make eval-mock`

> Mock run: Tavily and Gemini are the test fakes, so these numbers only show
> that the harness works. Real numbers come from `make eval` with real keys.

| Metric | Result |
|---|---|
| Tier accuracy | **100%** (4/4) |
| Spam and duplicates handled | 2/2 |
| Drafts fully grounded (LLM judge) | 2/3 |
| Claims traceable to message or sources | 3/4 (75%) |
| Time from submission to approval request, p50 / p95 | 3.2 s / 3.3 s |
| Avg tokens per lead (in / out) | 735 / 367 |
| Avg Tavily credits per lead | 1.75 |
| Estimated paid-tier cost per lead | $0.0151 |

## Confusion matrix (rows: expected, columns: predicted)

| | hot | warm | cold |
|---|---|---|---|
| **hot** | 1 | 0 | 0 |
| **warm** | 0 | 2 | 0 |
| **cold** | 0 | 0 | 1 |

## Leads

| Lead | Case | Expected | Result | Score | Research | s to review |
|---|---|---|---|---|---|---|
| mock-hot | normal | hot | ✓ hot | 87 | ok | 3.1 |
| mock-warm-personal | personal_email | warm | ✓ warm | 60 | partial | 3.3 |
| mock-warm-unreachable | unreachable_website | warm | ✓ warm | 48 | partial | 3.2 |
| mock-cold | vague | cold | ✓ cold | 33 | failed |  |
| mock-dup | duplicate | duplicate | ✓ duplicate |  |  |  |
| mock-spam | spam | spam | ✓ spam |  |  |  |

Prices: 2026-11-27 list prices from `eval/prices.json`.
