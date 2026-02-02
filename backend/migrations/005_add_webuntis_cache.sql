-- Migration: Add WebUntis Cache Table
-- Description: Persistent cache for WebUntis master data (subjects, classes, rooms, timegrid)
-- Date: 2026-02-02

CREATE TABLE webuntis_cache (
    id SERIAL PRIMARY KEY,
    cache_key VARCHAR(100) UNIQUE NOT NULL,
    cache_data JSONB NOT NULL,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_webuntis_cache_key ON webuntis_cache(cache_key);
CREATE INDEX idx_webuntis_cache_expires ON webuntis_cache(expires_at);

COMMENT ON TABLE webuntis_cache IS 'Persistent cache for WebUntis master data (subjects, classes, rooms, timegrid)';
