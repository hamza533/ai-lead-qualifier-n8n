-- Per-criterion scorecard (ratings, reasons, evidence, points) next to the final score.
ALTER TABLE leads ADD COLUMN IF NOT EXISTS scoring jsonb;
