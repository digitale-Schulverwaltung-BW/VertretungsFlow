-- Migration: Add can_be_canceled field to affected_lessons
-- Date: 2026-01-29

ALTER TABLE affected_lessons
ADD COLUMN can_be_canceled BOOLEAN DEFAULT FALSE;

-- Optional: Update existing records (all default to FALSE)
UPDATE affected_lessons SET can_be_canceled = FALSE WHERE can_be_canceled IS NULL;
