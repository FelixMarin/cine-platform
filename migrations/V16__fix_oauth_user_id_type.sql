-- V16: Fix oauth_user_id type from integer to varchar
-- Reason: OAuth2 providers return string identifiers (e.g., "admin", "12345")
-- This prevents "invalid input syntax for type integer" errors

-- Change oauth_user_id from INTEGER to VARCHAR(255)
ALTER TABLE app_users ALTER COLUMN oauth_user_id TYPE VARCHAR(255);

-- Note: PostgreSQL automatically converts existing integer values to strings
-- The UNIQUE constraint remains intact
