-- =============================================================================
-- PostgreSQL Initialization Script - Knowledge Platform
-- =============================================================================
-- This script runs on first container startup to initialize the database
-- =============================================================================

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- For encryption functions (gen_random_uuid, crypt, etc.)
-- Note: vector extension requires pgvector/pgvector Docker image
-- CREATE EXTENSION IF NOT EXISTS "vector";  -- For pgvector embeddings support (disabled for standard postgres image)

-- Create application user (if not using default)
-- Note: Default user is created via POSTGRES_USER environment variable
-- This is for additional users if needed

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE knowledge TO knowledge;

-- Create schemas
CREATE SCHEMA IF NOT EXISTS documents;
CREATE SCHEMA IF NOT EXISTS search;
CREATE SCHEMA IF NOT EXISTS audit;

-- Set default search path
ALTER DATABASE knowledge SET search_path TO public, documents, search, audit;

-- Create audit log table
CREATE TABLE IF NOT EXISTS audit.activity_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID,
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID,
    old_value JSONB,
    new_value JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index for audit log
CREATE INDEX IF NOT EXISTS idx_activity_log_user_id ON audit.activity_log(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_log_entity ON audit.activity_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_activity_log_created_at ON audit.activity_log(created_at);

-- Create function for updating timestamps
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'Knowledge Platform database initialized successfully at %', CURRENT_TIMESTAMP;
END $$;
