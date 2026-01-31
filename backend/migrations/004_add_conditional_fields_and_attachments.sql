-- Migration: Add conditional fields and attachments support
-- Date: 2026-01-31
-- Description: Adds excursion_classes, personal_reason, admin_notes fields to absences
--              and creates absence_attachments table for file uploads

-- Add new fields to absences table
ALTER TABLE absences
ADD COLUMN excursion_classes TEXT,           -- Bei Exkursion: betroffene Klassen (Pflichtfeld)
ADD COLUMN personal_reason TEXT,             -- Bei Privat/Sonstiges: Begründung (Pflichtfeld)
ADD COLUMN admin_notes TEXT;                 -- Bemerkungen für Schulleitung/Planer (optional)

-- Create absence_attachments table
CREATE TABLE absence_attachments (
    id SERIAL PRIMARY KEY,
    absence_id INTEGER NOT NULL,

    -- File metadata
    filename VARCHAR(255) NOT NULL,           -- Original filename
    stored_filename VARCHAR(255) NOT NULL,    -- UUID-based filename in storage
    file_path VARCHAR(512) NOT NULL,          -- Full path in storage
    mime_type VARCHAR(100) NOT NULL,          -- e.g. 'application/pdf'
    file_size INTEGER NOT NULL,               -- in bytes

    -- Timestamp
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Foreign key with CASCADE DELETE
    CONSTRAINT fk_absence
        FOREIGN KEY (absence_id)
        REFERENCES absences(id)
        ON DELETE CASCADE
);

-- Create index for performance
CREATE INDEX idx_absence_attachments_absence_id ON absence_attachments(absence_id);

-- Optional: Add comments for documentation
COMMENT ON COLUMN absences.excursion_classes IS 'Betroffene Klassen bei Exkursionen (Pflichtfeld wenn reason=excursion)';
COMMENT ON COLUMN absences.personal_reason IS 'Begründung bei privaten Abwesenheiten (Pflichtfeld wenn reason=personal oder other)';
COMMENT ON COLUMN absences.admin_notes IS 'Bemerkungen für Schulleitung und Vertretungsplaner (optional)';
COMMENT ON TABLE absence_attachments IS 'Datei-Anhänge zu Abwesenheiten (z.B. Einladungen, Atteste)';
