-- Race-safe idempotency: one claim per lead_hash (email + message). A new submission
-- claims the hash if it is free or the previous claim is older than 24 h; the primary key
-- makes two simultaneous identical submissions serialise, so only one lead is created.
CREATE TABLE IF NOT EXISTS lead_claims (
    lead_hash   text PRIMARY KEY,
    lead_id     text NOT NULL,
    claimed_at  timestamptz NOT NULL DEFAULT now()
);

-- Backfill from leads accepted in the last 24 h, so the switch doesn't reopen the window.
INSERT INTO lead_claims (lead_hash, lead_id, claimed_at)
SELECT DISTINCT ON (lead_hash) lead_hash, lead_id, received_at
FROM leads
WHERE status <> 'rejected_spam' AND received_at > now() - interval '24 hours'
ORDER BY lead_hash, received_at DESC
ON CONFLICT (lead_hash) DO NOTHING;
