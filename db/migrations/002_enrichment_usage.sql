-- Enrichment result and per-lead usage (tokens, Tavily credits) for cost tracking
-- and the evaluation report. Usage columns are accumulated by each pipeline step.
ALTER TABLE leads
    ADD COLUMN IF NOT EXISTS enrichment         jsonb,
    ADD COLUMN IF NOT EXISTS llm_input_tokens   integer NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS llm_output_tokens  integer NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS tavily_credits     integer NOT NULL DEFAULT 0;
