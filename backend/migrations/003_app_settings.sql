-- Migration: Application Settings Table
-- Description: Create table for storing user settings and preferences
-- Date: 2024

-- Create app_settings table
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_app_settings_updated_at ON app_settings(updated_at DESC);

-- Add comments for documentation
COMMENT ON TABLE app_settings IS 'Stores application-wide settings and user preferences';
COMMENT ON COLUMN app_settings.key IS 'Setting key (e.g., default_llm_profile, sandbox_timeout)';
COMMENT ON COLUMN app_settings.value IS 'Setting value stored as JSONB for flexibility';

-- Insert default settings
INSERT INTO app_settings (key, value) VALUES
    ('default_llm_profile', 'null'::jsonb),
    ('sandbox_timeout', '30'::jsonb),
    ('max_retries', '5'::jsonb),
    ('debug_mode', 'false'::jsonb)
ON CONFLICT (key) DO NOTHING;
