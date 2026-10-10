-- ==============================================================================
-- Migration Script: scripts/add_call_timestamps.sql
-- Description: Adds started_at, answered_at, and ended_at timestamp columns
--              to the calls table.
-- ==============================================================================

ALTER TABLE calls ADD COLUMN IF NOT EXISTS started_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE calls ADD COLUMN IF NOT EXISTS answered_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE calls ADD COLUMN IF NOT EXISTS ended_at TIMESTAMP WITH TIME ZONE;

-- Create index on started_at for fast date-range queries
CREATE INDEX IF NOT EXISTS ix_calls_started_at ON calls (started_at);
