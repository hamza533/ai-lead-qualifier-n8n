-- When the draft was ready for a person (approval request posted, or auto-approved in eval).
-- Used for the "submission to Slack" latency in the evaluation.
ALTER TABLE leads ADD COLUMN IF NOT EXISTS ready_for_review_at timestamptz;
