-- Alerts are failures ('error': the lead stopped and is recoverable) or warnings
-- ('warning': e.g. research degraded by an outage, the lead continued).
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS level text NOT NULL DEFAULT 'error';
