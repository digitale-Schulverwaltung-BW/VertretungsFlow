-- Migration 006: Add start_time and end_time to affected_lessons
-- Author: Claude Sonnet 4.5
-- Date: 2026-02-05
-- Description: Store WebUntis time data (startTime/endTime) in affected_lessons table
--              for accurate PDF form filling (e.g., "07:45" instead of just period "1")

-- Add time columns to affected_lessons
ALTER TABLE affected_lessons ADD COLUMN start_time INTEGER;
ALTER TABLE affected_lessons ADD COLUMN end_time INTEGER;

-- Add comments for documentation
COMMENT ON COLUMN affected_lessons.start_time IS 'WebUntis startTime format (e.g., 730 = 07:30). Used for PDF form pre-filling.';
COMMENT ON COLUMN affected_lessons.end_time IS 'WebUntis endTime format (e.g., 815 = 08:15). Used for PDF form pre-filling.';

-- Optional: Create index for faster queries (if we ever filter by time)
-- CREATE INDEX idx_affected_lessons_start_time ON affected_lessons(start_time);

-- Note: Nullable columns, as existing lessons won't have time data
--       and future lessons might not have it if WebUntis doesn't provide it
