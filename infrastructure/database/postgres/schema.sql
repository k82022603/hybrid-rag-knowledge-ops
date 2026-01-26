-- ============================================================================
-- PostgreSQL Schema for Hybrid RAG Knowledge Platform
-- Version: 3.0 (Design ERD Aligned)
-- Created: 2026-01-12
-- Updated: 2026-01-26
-- Description: SSOT schema aligned with hybrid_rag_platform_detailed_design.md ERD
-- Migration: knowledge_master -> documents (UUID PK), SERIAL -> UUID
-- Ref: architecture_compliance_review_2026-01-26.md Critical C1
-- ============================================================================

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================================================
-- 0. AUTHENTICATION USERS (Backend Direct Login - Sprint 02)
-- NOTE: Separate from knowledge domain 'users' table.
--       Used by Backend R2DBC for Direct Login (HS256 JWT).
--       SERIAL PK maintained for R2DBC compatibility.
-- ============================================================================

CREATE TABLE IF NOT EXISTS auth_users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    roles VARCHAR(255) DEFAULT 'USER',  -- Comma-separated: USER,ADMIN,DEVELOPER,VIEWER
    is_active BOOLEAN DEFAULT true,
    is_locked BOOLEAN DEFAULT false,
    failed_login_attempts INT DEFAULT 0,
    locked_until TIMESTAMP,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_auth_users_email ON auth_users(email);
CREATE INDEX IF NOT EXISTS idx_auth_users_username ON auth_users(username);
CREATE INDEX IF NOT EXISTS idx_auth_users_active ON auth_users(is_active);

-- ============================================================================
-- 1. USERS (Knowledge Domain - Design ERD)
-- ============================================================================

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(200),
    department VARCHAR(100),
    position VARCHAR(100),
    role VARCHAR(50) DEFAULT 'user',  -- admin, user, viewer
    is_active BOOLEAN DEFAULT true,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);

-- ============================================================================
-- 2. AUDIT LOGS
-- ============================================================================

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(50) NOT NULL,  -- CREATE, READ, UPDATE, DELETE, SEARCH, LOGIN, LOGOUT
    resource_type VARCHAR(50) NOT NULL,  -- document, user, entity, search
    resource_id UUID,
    old_value JSONB,
    new_value JSONB,
    ip_address INET,
    user_agent TEXT,
    request_path TEXT,
    status VARCHAR(20) DEFAULT 'success',  -- success, failure
    error_message TEXT,
    duration_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource_type ON audit_logs(resource_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource_id ON audit_logs(resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_status ON audit_logs(status);

-- ============================================================================
-- 3. PROJECTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    start_date DATE,
    end_date DATE,
    status VARCHAR(20) DEFAULT 'active',  -- active, completed, archived
    owner_id UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_projects_code ON projects(code);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);

-- ============================================================================
-- 4. PERSONS (Document authors, mentioned people)
-- ============================================================================

CREATE TABLE IF NOT EXISTS persons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE,
    department VARCHAR(100),
    position VARCHAR(100),
    user_id UUID REFERENCES users(id),  -- Link to user if they are a platform user
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_persons_name ON persons(name);
CREATE INDEX IF NOT EXISTS idx_persons_email ON persons(email);
CREATE INDEX IF NOT EXISTS idx_persons_name_trgm ON persons USING gin(name gin_trgm_ops);

-- ============================================================================
-- 5. DOCUMENTS (Master Records - SSOT)
-- Design ERD: 'documents' table with UUID PK
-- Replaces old 'knowledge_master' (SERIAL PK)
-- ============================================================================

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    document_type VARCHAR(50) NOT NULL,  -- manual, specification, report, meeting_note, etc.
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    author_id UUID REFERENCES persons(id) ON DELETE SET NULL,
    uploaded_by UUID REFERENCES users(id) ON DELETE SET NULL,

    -- Temporal metadata
    valid_start_date DATE,
    valid_end_date DATE,

    -- File information
    file_path TEXT NOT NULL,
    file_name VARCHAR(500),
    file_size BIGINT,
    file_type VARCHAR(50),  -- pdf, docx, xlsx, etc.
    file_hash VARCHAR(128),  -- SHA-256 hash for deduplication

    -- Processing status
    processing_status VARCHAR(30) DEFAULT 'pending',  -- pending, processing, completed, failed
    processing_error TEXT,
    processed_at TIMESTAMP,

    -- Statistics
    chunk_count INTEGER DEFAULT 0,
    entity_count INTEGER DEFAULT 0,

    -- Raw metadata extracted from document
    raw_metadata JSONB DEFAULT '{}',

    -- Sync flags for other databases
    es_synced BOOLEAN DEFAULT false,
    es_synced_at TIMESTAMP,
    neo4j_synced BOOLEAN DEFAULT false,
    neo4j_synced_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_date_range CHECK (valid_start_date IS NULL OR valid_end_date IS NULL OR valid_start_date <= valid_end_date)
);

CREATE INDEX IF NOT EXISTS idx_documents_project_id ON documents(project_id);
CREATE INDEX IF NOT EXISTS idx_documents_author_id ON documents(author_id);
CREATE INDEX IF NOT EXISTS idx_documents_uploaded_by ON documents(uploaded_by);
CREATE INDEX IF NOT EXISTS idx_documents_document_type ON documents(document_type);
CREATE INDEX IF NOT EXISTS idx_documents_valid_dates ON documents(valid_start_date, valid_end_date);
CREATE INDEX IF NOT EXISTS idx_documents_processing_status ON documents(processing_status);
CREATE INDEX IF NOT EXISTS idx_documents_file_hash ON documents(file_hash);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_documents_title_trgm ON documents USING gin(title gin_trgm_ops);

-- ============================================================================
-- 6. CHUNKS (Document segments for RAG)
-- Design ERD: 'chunks' table with UUID PK
-- Replaces old 'knowledge_chunks'
-- ============================================================================

CREATE TABLE IF NOT EXISTS chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    token_count INTEGER,

    -- Chunking metadata
    start_char INTEGER,
    end_char INTEGER,
    heading VARCHAR(500),  -- Section heading if available

    -- ES sync reference
    es_id VARCHAR(100),  -- Elasticsearch document ID

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(document_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_chunk_index ON chunks(document_id, chunk_index);

-- ============================================================================
-- 7. CATEGORIES (Hierarchical structure - Design ERD v2.5)
-- ============================================================================

CREATE TABLE IF NOT EXISTS categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    code VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    parent_id UUID REFERENCES categories(id) ON DELETE SET NULL,
    level INTEGER NOT NULL DEFAULT 1,  -- 1: large, 2: medium, 3: small
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_level CHECK (level BETWEEN 1 AND 3)
);

CREATE INDEX IF NOT EXISTS idx_categories_parent_id ON categories(parent_id);
CREATE INDEX IF NOT EXISTS idx_categories_level ON categories(level);
CREATE INDEX IF NOT EXISTS idx_categories_code ON categories(code);

-- Document-Category relationship
CREATE TABLE IF NOT EXISTS document_categories (
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    category_id UUID REFERENCES categories(id) ON DELETE CASCADE,
    confidence FLOAT DEFAULT 1.0,  -- AI classification confidence
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (document_id, category_id)
);

CREATE INDEX IF NOT EXISTS idx_document_categories_document_id ON document_categories(document_id);
CREATE INDEX IF NOT EXISTS idx_document_categories_category_id ON document_categories(category_id);

-- ============================================================================
-- 8. ENTITIES (for PostgreSQL-Neo4j sync)
-- Design ERD: 'entities' table with UUID PK
-- Replaces old 'extracted_entities'
-- ============================================================================

CREATE TABLE IF NOT EXISTS entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,  -- Person, Project, Technology, Concept, Organization
    description TEXT,
    canonical_name VARCHAR(255),  -- Normalized name for deduplication

    -- Neo4j sync
    neo4j_id VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(canonical_name, type)
);

CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type);
CREATE INDEX IF NOT EXISTS idx_entities_canonical_name ON entities(canonical_name);
CREATE INDEX IF NOT EXISTS idx_entities_name_trgm ON entities USING gin(name gin_trgm_ops);

-- Document-Entity relationship
CREATE TABLE IF NOT EXISTS document_entities (
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    entity_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    relevance_score FLOAT DEFAULT 1.0,
    mention_count INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (document_id, entity_id)
);

CREATE INDEX IF NOT EXISTS idx_document_entities_document_id ON document_entities(document_id);
CREATE INDEX IF NOT EXISTS idx_document_entities_entity_id ON document_entities(entity_id);

-- Entity relationships
CREATE TABLE IF NOT EXISTS entity_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    target_entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL,  -- COLLABORATED_WITH, WORKS_ON, USES, etc.
    description TEXT,
    weight FLOAT DEFAULT 1.0,

    -- Neo4j sync
    neo4j_synced BOOLEAN DEFAULT false,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT no_self_relationship CHECK (source_entity_id != target_entity_id)
);

CREATE INDEX IF NOT EXISTS idx_entity_relationships_source ON entity_relationships(source_entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_relationships_target ON entity_relationships(target_entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_relationships_type ON entity_relationships(relationship_type);

-- ============================================================================
-- 9. SEARCH HISTORY & FEEDBACK
-- ============================================================================

CREATE TABLE IF NOT EXISTS search_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    query_text TEXT NOT NULL,
    query_hash VARCHAR(64) NOT NULL,  -- For cache lookup
    intent VARCHAR(50),  -- temporal_comparison, fact_retrieval, relationship_exploration
    filters JSONB DEFAULT '{}',
    result_count INTEGER,
    search_duration_ms INTEGER,
    cached BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_search_history_user_id ON search_history(user_id);
CREATE INDEX IF NOT EXISTS idx_search_history_query_hash ON search_history(query_hash);
CREATE INDEX IF NOT EXISTS idx_search_history_created_at ON search_history(created_at DESC);

CREATE TABLE IF NOT EXISTS search_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    search_id UUID REFERENCES search_history(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    feedback_type VARCHAR(50),  -- relevant, irrelevant, helpful, not_helpful
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_search_feedback_search_id ON search_feedback(search_id);
CREATE INDEX IF NOT EXISTS idx_search_feedback_user_id ON search_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_search_feedback_document_id ON search_feedback(document_id);

-- ============================================================================
-- 10. LLM COST TRACKING
-- ============================================================================

CREATE TABLE IF NOT EXISTS llm_cost_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_type VARCHAR(100),  -- entity_extraction, orchestration, synthesis, embedding
    model_name VARCHAR(100),  -- deepseek-chat, deepseek-reasoner, bge-m3

    -- Token Count
    input_tokens INT,
    output_tokens INT,
    total_tokens INT,

    -- Pricing
    unit_price_per_1m_tokens DECIMAL(10, 6),
    cost_usd DECIMAL(10, 6),

    -- Caching
    cache_hit BOOLEAN DEFAULT false,
    cache_discount_percent INT DEFAULT 0,

    -- Metadata
    execution_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_key DATE DEFAULT CURRENT_DATE
);

CREATE INDEX IF NOT EXISTS idx_cost_model ON llm_cost_logs(model_name);
CREATE INDEX IF NOT EXISTS idx_cost_task ON llm_cost_logs(task_type);
CREATE INDEX IF NOT EXISTS idx_cost_date ON llm_cost_logs(date_key);
CREATE INDEX IF NOT EXISTS idx_cost_timestamp ON llm_cost_logs(execution_timestamp DESC);

-- ============================================================================
-- 11. SYSTEM CONFIGURATION
-- ============================================================================

CREATE TABLE IF NOT EXISTS system_config (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_by UUID REFERENCES users(id),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 12. FUNCTIONS & TRIGGERS
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to relevant tables
DO $$
BEGIN
    -- users
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_users_updated_at') THEN
        CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    -- documents
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_documents_updated_at') THEN
        CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    -- projects
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_projects_updated_at') THEN
        CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    -- persons
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_persons_updated_at') THEN
        CREATE TRIGGER update_persons_updated_at BEFORE UPDATE ON persons FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    -- categories
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_categories_updated_at') THEN
        CREATE TRIGGER update_categories_updated_at BEFORE UPDATE ON categories FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    -- entities
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_entities_updated_at') THEN
        CREATE TRIGGER update_entities_updated_at BEFORE UPDATE ON entities FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- ============================================================================
-- 13. INITIAL DATA
-- ============================================================================

-- Default admin user (knowledge domain)
INSERT INTO users (username, email, password_hash, display_name, role)
VALUES ('admin', 'admin@knowledge.local', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.vjuZDHZL3T/hGe', 'System Administrator', 'admin')
ON CONFLICT (username) DO NOTHING;

-- Test Users for E2E Testing (auth_users table)
-- BCrypt hashed with strength 10 ($2a$10$ format for Java BCryptPasswordEncoder)
INSERT INTO auth_users (email, username, password_hash, first_name, last_name, roles, is_active, is_locked, failed_login_attempts)
VALUES
  ('test@example.com', 'testuser', '$2a$10$AJfMv872SXOwwTOB9HNP7eir9LEhj1pihhFt/Dhpd1.R1PVvtHq3S', 'Test', 'User', 'USER', true, false, 0),
  ('admin@example.com', 'adminuser', '$2a$10$TklJOu/IfeMpihl740smseaj.Y1MaJHcFTvFjPc6k62Bdce4XJq22', 'Admin', 'User', 'ADMIN,USER', true, false, 0)
ON CONFLICT (email) DO NOTHING;

-- Default categories
INSERT INTO categories (name, code, level, sort_order) VALUES
    ('Technical Documentation', 'tech_doc', 1, 1),
    ('Meeting Notes', 'meeting', 1, 2),
    ('Reports', 'report', 1, 3),
    ('Specifications', 'spec', 1, 4)
ON CONFLICT (code) DO NOTHING;

-- Default system config
INSERT INTO system_config (key, value, description) VALUES
    ('document_types', '["manual", "specification", "report", "meeting_note", "design_doc", "api_doc"]', 'Allowed document types'),
    ('max_file_size_mb', '100', 'Maximum file size in MB'),
    ('supported_file_types', '["pdf", "docx", "xlsx", "pptx", "txt", "md", "hwp"]', 'Supported file types for upload'),
    ('chunk_size', '600', 'Default chunk size in tokens'),
    ('chunk_overlap', '50', 'Default chunk overlap in tokens'),
    ('embedding_model', '"BAAI/bge-m3"', 'BGE-M3 multilingual embedding model'),
    ('embedding_dim', '1024', 'BGE-M3 embedding dimension'),
    ('metadata_extraction_model', '"deepseek-chat"', 'Model for entity extraction'),
    ('elasticsearch_index_name', '"knowledge-chunks"', 'Primary ES index name')
ON CONFLICT (key) DO NOTHING;

-- ============================================================================
-- 14. CONVENIENCE VIEWS
-- ============================================================================

CREATE OR REPLACE VIEW v_active_documents AS
SELECT
    d.id as document_id,
    d.title,
    d.document_type,
    p.name as project_name,
    p.code as project_code,
    pe.name as author_name,
    d.valid_start_date,
    d.valid_end_date,
    d.processing_status,
    d.chunk_count,
    d.created_at,
    CASE
        WHEN d.valid_start_date IS NULL OR d.valid_end_date IS NULL THEN 'INDEFINITE'
        WHEN CURRENT_DATE BETWEEN d.valid_start_date AND d.valid_end_date THEN 'VALID'
        WHEN CURRENT_DATE > d.valid_end_date THEN 'EXPIRED'
        ELSE 'NOT_YET_VALID'
    END as validity_status
FROM documents d
LEFT JOIN projects p ON d.project_id = p.id
LEFT JOIN persons pe ON d.author_id = pe.id;

CREATE OR REPLACE VIEW v_document_statistics AS
SELECT
    COUNT(DISTINCT d.id) as total_documents,
    COUNT(DISTINCT c.id) as total_chunks,
    COUNT(DISTINCT d.project_id) as projects_count,
    COUNT(CASE WHEN d.processing_status = 'completed' THEN 1 END) as completed_count,
    COUNT(CASE WHEN d.processing_status = 'failed' THEN 1 END) as failed_count,
    COUNT(CASE WHEN d.processing_status = 'pending' THEN 1 END) as pending_count
FROM documents d
LEFT JOIN chunks c ON d.id = c.document_id;

-- ============================================================================
-- 15. PERMISSIONS (commented out - adjust for your setup)
-- ============================================================================

-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO knowledge_app;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO knowledge_app;

-- Table comments
COMMENT ON TABLE auth_users IS 'Backend authentication users (Direct Login, R2DBC)';
COMMENT ON TABLE users IS 'Platform users for knowledge domain (Design ERD)';
COMMENT ON TABLE audit_logs IS 'Audit trail for all system activities';
COMMENT ON TABLE documents IS 'Master document records (SSOT) - replaces knowledge_master';
COMMENT ON TABLE chunks IS 'Document text chunks for RAG processing - replaces knowledge_chunks';
COMMENT ON TABLE entities IS 'Named entities extracted from documents - replaces extracted_entities';
COMMENT ON TABLE entity_relationships IS 'Relationships between entities';
COMMENT ON TABLE categories IS 'Hierarchical document categorization (Design ERD v2.5)';

-- ============================================================================
-- Schema v3.0 Complete - Design ERD Aligned
-- ============================================================================
