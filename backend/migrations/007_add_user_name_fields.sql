-- Add first_name and last_name columns to users table
-- Migration: 007_add_user_name_fields.sql
-- Date: 2026-02-05

ALTER TABLE users ADD COLUMN first_name VARCHAR(100);
ALTER TABLE users ADD COLUMN last_name VARCHAR(100);

COMMENT ON COLUMN users.first_name IS 'First name from WordPress user meta';
COMMENT ON COLUMN users.last_name IS 'Last name from WordPress user meta';
