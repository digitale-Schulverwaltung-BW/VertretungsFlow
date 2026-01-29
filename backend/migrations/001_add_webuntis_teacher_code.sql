-- Migration: Add webuntis_teacher_code field to users table
-- Date: 2026-01-29
-- Description: Adds optional WebUntis teacher code field for mapping WordPress users to WebUntis teacher abbreviations

-- Add the column
ALTER TABLE users ADD COLUMN webuntis_teacher_code VARCHAR(20);

-- Create index for performance
CREATE INDEX ix_users_webuntis_teacher_code ON users(webuntis_teacher_code);

-- Rollback instructions:
-- DROP INDEX ix_users_webuntis_teacher_code;
-- ALTER TABLE users DROP COLUMN webuntis_teacher_code;
