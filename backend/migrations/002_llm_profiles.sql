-- Migration: LLM Profiles Table
-- Description: Create table for storing LLM profile configurations
-- Date: 2024

-- Create llm_profiles table
CREATE TABLE IF NOT EXISTS llm_profiles (
    id UUID PRIMARY KEY,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    temperature DOUBLE PRECISION NOT NULL DEFAULT 0.2,
    max_tokens INTEGER,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_llm_profiles_is_default ON llm_profiles(is_default);
CREATE INDEX IF NOT EXISTS idx_llm_profiles_created_at ON llm_profiles(created_at DESC);

-- Add constraint to ensure only one default profile
CREATE UNIQUE INDEX IF NOT EXISTS idx_llm_profiles_single_default 
    ON llm_profiles(is_default) 
    WHERE is_default = TRUE;

-- Add comments for documentation
COMMENT ON TABLE llm_profiles IS 'Stores LLM profile configurations for quick model switching';
COMMENT ON COLUMN llm_profiles.provider IS 'LLM provider: groq, openai, anthropic, ollama';
COMMENT ON COLUMN llm_profiles.model IS 'Model identifier (e.g., groq/llama-3.3-70b-versatile)';
COMMENT ON COLUMN llm_profiles.temperature IS 'Sampling temperature (0.0-2.0)';
COMMENT ON COLUMN llm_profiles.max_tokens IS 'Maximum tokens to generate (null = provider default)';
COMMENT ON COLUMN llm_profiles.is_default IS 'Whether this is the default profile for new sessions';
