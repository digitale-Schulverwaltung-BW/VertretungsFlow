-- Migration: Add end_period to affected_lessons table
-- Date: 2026-01-29
-- Description: Adds end_period column to support multi-period lesson blocks (Doppelstunden)

-- Add the column
ALTER TABLE affected_lessons ADD COLUMN end_period INTEGER;

-- Rollback instructions:
-- ALTER TABLE affected_lessons DROP COLUMN end_period;
