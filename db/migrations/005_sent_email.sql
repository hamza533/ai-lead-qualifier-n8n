-- The email that was sent (or would have been, with DRY_RUN): from, to, subject, body and
-- any demo redirect. 004 tried to add this as "email", which already exists (the lead's
-- address), so that line was a no-op; the sent email lives here instead.
ALTER TABLE leads ADD COLUMN IF NOT EXISTS sent_email jsonb;
