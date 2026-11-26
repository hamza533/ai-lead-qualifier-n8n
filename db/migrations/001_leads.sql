-- Lead ledger: idempotency, status tracking (incl. recoverable states) and
-- the cold-lead digest. Personal data here is purged after LEAD_RETENTION_DAYS
-- by the daily workflow; HubSpot is the long-term record.
CREATE TABLE IF NOT EXISTS leads (
    lead_id            text PRIMARY KEY,
    lead_hash          text        NOT NULL,
    source             text        NOT NULL CHECK (source IN ('form', 'webhook', 'eval')),
    status             text        NOT NULL,
    received_at        timestamptz NOT NULL DEFAULT now(),
    updated_at         timestamptz NOT NULL DEFAULT now(),
    name               text,
    email              text,
    company            text,
    website_domain     text,
    personal_email     boolean,
    -- normalised lead as received, so a lead in a recoverable status can be replayed
    payload            jsonb,
    enrichment_status  text,
    score              integer CHECK (score BETWEEN 0 AND 100),
    tier               text CHECK (tier IN ('hot', 'warm', 'cold')),
    error              text,
    execution_id       text
);

CREATE INDEX IF NOT EXISTS leads_hash_received_idx ON leads (lead_hash, received_at DESC);
CREATE INDEX IF NOT EXISTS leads_status_received_idx ON leads (status, received_at DESC);
