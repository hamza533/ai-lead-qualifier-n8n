-- Draft, approval, email, CRM and outcome for each lead, plus the alerts log.
ALTER TABLE leads
    ADD COLUMN IF NOT EXISTS pipeline_execution_id  text,
    ADD COLUMN IF NOT EXISTS draft                  jsonb,
    ADD COLUMN IF NOT EXISTS approval_url           text,
    ADD COLUMN IF NOT EXISTS slack_channel          text,
    ADD COLUMN IF NOT EXISTS slack_ts               text,
    ADD COLUMN IF NOT EXISTS approval_requested_at  timestamptz,
    ADD COLUMN IF NOT EXISTS reminder_sent_at       timestamptz,
    ADD COLUMN IF NOT EXISTS decision               jsonb,
    ADD COLUMN IF NOT EXISTS email                  jsonb,
    ADD COLUMN IF NOT EXISTS email_sent_at          timestamptz,
    ADD COLUMN IF NOT EXISTS crm                    jsonb,
    ADD COLUMN IF NOT EXISTS completed_at           timestamptz,
    -- With DRY_RUN=true, the Slack/HubSpot/email calls that were skipped, in order.
    ADD COLUMN IF NOT EXISTS dry_run_actions        jsonb NOT NULL DEFAULT '[]'::jsonb;

CREATE INDEX IF NOT EXISTS leads_pipeline_execution_idx ON leads (pipeline_execution_id);
CREATE INDEX IF NOT EXISTS leads_awaiting_idx ON leads (approval_requested_at)
    WHERE status = 'awaiting_approval';

-- Failures reported by the error workflow. Emails are stored masked.
CREATE TABLE IF NOT EXISTS alerts (
    id             bigserial PRIMARY KEY,
    created_at     timestamptz NOT NULL DEFAULT now(),
    workflow       text NOT NULL,
    node           text,
    message        text NOT NULL,
    lead_id        text,
    masked_email   text,
    execution_id   text,
    execution_url  text,
    delivered      boolean NOT NULL DEFAULT false
);
CREATE INDEX IF NOT EXISTS alerts_created_idx ON alerts (created_at DESC);
