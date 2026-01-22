-- PostgreSQL Schema for Hybrid RAG Knowledge Operations
-- Version: 2.7
-- Created: 2026-01-12
-- Updated: 2026-01-22
-- Purpose: Master records, temporal metadata, and project information

-- ============================================================================
-- 1. USERS & ORGANIZATIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(255),
    department VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_department ON users(department);

-- ============================================================================
-- 2. PROJECTS & ORGANIZATIONAL METADATA
-- ============================================================================

CREATE TABLE IF NOT EXISTS projects (
    project_id SERIAL PRIMARY KEY,
    project_name VARCHAR(500) NOT NULL UNIQUE,
    project_code VARCHAR(100),
    description TEXT,
    owner_id INT REFERENCES users(user_id),
    status VARCHAR(50) DEFAULT 'active',  -- active, completed, archived
    start_date DATE,
    end_date DATE,
    category VARCHAR(100),
    tags JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT project_date_check CHECK (end_date >= start_date OR end_date IS NULL)
);

CREATE INDEX idx_projects_name ON projects(project_name);
CREATE INDEX idx_projects_code ON projects(project_code);
CREATE INDEX idx_projects_owner ON projects(owner_id);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_dates ON projects(start_date, end_date);

-- ============================================================================
-- 3. MASTER KNOWLEDGE RECORDS
-- ============================================================================

CREATE TABLE IF NOT EXISTS knowledge_master (
    knowledge_id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    contributor_id INT REFERENCES users(user_id),
    project_id INT REFERENCES projects(project_id),  -- NULL for general knowledge

    -- Document Classification
    knowledge_type VARCHAR(50),  -- 'General', 'Project_Output', 'SOP', 'Meeting_Notes', 'Tech_Doc'
    document_type VARCHAR(100),  -- '프로젝트_보고서', '일반_가이드', '회의록', 'API_문서'

    -- Temporal Information (DeepSeek extracted)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    valid_start_date DATE DEFAULT CURRENT_DATE,
    valid_end_date DATE DEFAULT '9999-12-31',  -- NULL/max for indefinite

    -- Metadata
    tags JSONB,           -- Topics, keywords extracted by DeepSeek
    entities JSONB,       -- persons, projects, technologies
    summary TEXT,         -- 3-line summary

    -- Source Information
    source_file VARCHAR(500),
    file_hash VARCHAR(64),  -- SHA-256 for deduplication
    file_size INT,

    -- Status
    is_active BOOLEAN DEFAULT true,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT valid_period_check CHECK (valid_end_date >= valid_start_date),
    CONSTRAINT future_end_check CHECK (valid_end_date > CURRENT_DATE OR valid_end_date = '9999-12-31')
);

CREATE INDEX idx_knowledge_title ON knowledge_master(title);
CREATE INDEX idx_knowledge_type ON knowledge_master(knowledge_type, document_type);
CREATE INDEX idx_knowledge_project ON knowledge_master(project_id);
CREATE INDEX idx_knowledge_contributor ON knowledge_master(contributor_id);
CREATE INDEX idx_knowledge_valid_period ON knowledge_master(valid_start_date, valid_end_date);
CREATE INDEX idx_knowledge_active ON knowledge_master(is_active);
CREATE INDEX idx_knowledge_created ON knowledge_master(created_at DESC);
CREATE UNIQUE INDEX idx_knowledge_file_hash ON knowledge_master(file_hash);

-- ============================================================================
-- 4. DOCUMENT CHUNKS & EMBEDDINGS
-- ============================================================================

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    chunk_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),  -- UUID 타입으로 통일 (v2.7)
    knowledge_id INT REFERENCES knowledge_master(knowledge_id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    total_chunks INT NOT NULL,

    -- Content
    text_content TEXT NOT NULL,
    text_length INT,
    char_count INT,

    -- Vector Embedding (stored in Elasticsearch, cached here for reference)
    embedding_dim INT DEFAULT 1024,  -- BGE-M3 dimension
    embedding_model VARCHAR(100) DEFAULT 'BAAI/bge-m3',

    -- Metadata (denormalized from knowledge_master for fast access)
    project_name VARCHAR(500),
    valid_start_date DATE,
    valid_end_date DATE,
    document_type VARCHAR(100),

    -- Ingestion
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,

    CONSTRAINT chunk_index_check CHECK (chunk_index >= 0 AND chunk_index < total_chunks)
);

CREATE INDEX idx_chunks_knowledge ON knowledge_chunks(knowledge_id);
CREATE INDEX idx_chunks_index ON knowledge_chunks(chunk_index);
CREATE INDEX idx_chunks_valid_period ON knowledge_chunks(valid_start_date, valid_end_date);
CREATE INDEX idx_chunks_ingestion ON knowledge_chunks(ingestion_timestamp DESC);

-- ============================================================================
-- 5. VECTOR METADATA CACHE (for Elasticsearch sync)
-- ============================================================================

CREATE TABLE IF NOT EXISTS embedding_metadata (
    metadata_id SERIAL PRIMARY KEY,
    chunk_id UUID REFERENCES knowledge_chunks(chunk_id) ON DELETE CASCADE UNIQUE,  -- UUID 타입 (v2.7)
    es_doc_id VARCHAR(100),  -- Elasticsearch document ID
    es_index_name VARCHAR(100) DEFAULT 'pdf-documents',

    -- Metadata snapshot (JSON for flexibility)
    metadata_json JSONB NOT NULL,

    -- Sync status
    synced_to_es BOOLEAN DEFAULT false,
    synced_to_neo4j BOOLEAN DEFAULT false,
    last_synced_at TIMESTAMP,
    sync_status VARCHAR(50) DEFAULT 'pending',  -- pending, syncing, synced, failed

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_embedding_chunk ON embedding_metadata(chunk_id);
CREATE INDEX idx_embedding_es_doc ON embedding_metadata(es_doc_id);
CREATE INDEX idx_embedding_sync_status ON embedding_metadata(sync_status);

-- ============================================================================
-- 6. EXTRACTED ENTITIES (from DeepSeek)
-- ============================================================================

CREATE TABLE IF NOT EXISTS extracted_entities (
    entity_id SERIAL PRIMARY KEY,
    knowledge_id INT REFERENCES knowledge_master(knowledge_id) ON DELETE CASCADE,

    -- Entity Information
    entity_type VARCHAR(50),  -- 'PERSON', 'PROJECT', 'TECHNOLOGY', 'KEYWORD'
    entity_value VARCHAR(500) NOT NULL,
    entity_confidence DECIMAL(3, 2),  -- 0.00 to 1.00

    -- Relationship Context
    relationship_type VARCHAR(100),  -- CREATED, LINKED_TO, USED_IN, MENTIONED_IN

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_entities_knowledge ON extracted_entities(knowledge_id);
CREATE INDEX idx_entities_type ON extracted_entities(entity_type);
CREATE INDEX idx_entities_value ON extracted_entities(entity_value);
CREATE INDEX idx_entities_relationship ON extracted_entities(relationship_type);

-- ============================================================================
-- 7. SEARCH & QUERY LOGS
-- ============================================================================

CREATE TABLE IF NOT EXISTS search_logs (
    log_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id),

    -- Query Information
    query_text TEXT NOT NULL,
    query_embedding_type VARCHAR(50),  -- dense, sparse, hybrid

    -- Results
    results_count INT,
    top_result_knowledge_id INT REFERENCES knowledge_master(knowledge_id),
    top_result_relevance_score DECIMAL(5, 4),  -- 0.0000 to 1.0000

    -- Performance
    query_execution_time_ms INT,

    -- Metadata
    search_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_search_user ON search_logs(user_id);
CREATE INDEX idx_search_timestamp ON search_logs(search_timestamp DESC);
CREATE INDEX idx_search_knowledge ON search_logs(top_result_knowledge_id);

-- ============================================================================
-- 8. COST TRACKING (for LLM usage)
-- ============================================================================

CREATE TABLE IF NOT EXISTS llm_cost_logs (
    cost_id SERIAL PRIMARY KEY,
    task_type VARCHAR(100),  -- entity_extraction, orchestration, synthesis, embedding
    model_name VARCHAR(100),  -- deepseek-chat, gpt-4o, claude-opus, bge-m3

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

CREATE INDEX idx_cost_model ON llm_cost_logs(model_name);
CREATE INDEX idx_cost_task ON llm_cost_logs(task_type);
CREATE INDEX idx_cost_date ON llm_cost_logs(date_key);
CREATE INDEX idx_cost_timestamp ON llm_cost_logs(execution_timestamp DESC);

-- ============================================================================
-- 9. SYSTEM CONFIGURATION
-- ============================================================================

CREATE TABLE IF NOT EXISTS system_config (
    config_id SERIAL PRIMARY KEY,
    config_key VARCHAR(255) NOT NULL UNIQUE,
    config_value TEXT,
    config_type VARCHAR(50),  -- string, int, boolean, json
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by INT REFERENCES users(user_id)
);

CREATE INDEX idx_config_key ON system_config(config_key);

-- ============================================================================
-- 10. AUDIT LOG
-- ============================================================================

CREATE TABLE IF NOT EXISTS audit_logs (
    audit_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id),
    action VARCHAR(100),  -- CREATE, UPDATE, DELETE, SYNC, EXPORT
    table_name VARCHAR(100),
    record_id INT,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_table ON audit_logs(table_name);
CREATE INDEX idx_audit_timestamp ON audit_logs(created_at DESC);

-- ============================================================================
-- 11. DEFAULT DATA
-- ============================================================================

-- Admin User
INSERT INTO users (username, email, full_name, role)
VALUES ('admin', 'admin@example.com', 'Administrator', 'admin')
ON CONFLICT DO NOTHING;

-- System Configuration
INSERT INTO system_config (config_key, config_value, config_type, description)
VALUES
  ('embedding_model', 'BAAI/bge-m3', 'string', 'BGE-M3 multilingual embedding model'),
  ('embedding_dim', '1024', 'int', 'BGE-M3 embedding dimension'),
  ('chunk_size', '1024', 'int', 'Document chunk size in characters'),
  ('chunk_overlap', '200', 'int', 'Chunk overlap for continuity'),
  ('metadata_extraction_model', 'deepseek-chat', 'string', 'Model for entity extraction'),
  ('max_concurrent_embeddings', '4', 'int', 'Concurrent embedding jobs'),
  ('elasticsearch_index_name', 'pdf-documents', 'string', 'Primary ES index name'),
  ('enable_cost_tracking', 'true', 'boolean', 'Enable LLM cost tracking'),
  ('enable_audit_logging', 'true', 'boolean', 'Enable audit logging')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 12. VIEWS (for convenience queries)
-- ============================================================================

CREATE OR REPLACE VIEW v_active_knowledge AS
SELECT
    k.knowledge_id,
    k.title,
    k.document_type,
    k.knowledge_type,
    p.project_name,
    u.full_name as contributor_name,
    k.valid_start_date,
    k.valid_end_date,
    k.created_at,
    CASE
        WHEN CURRENT_DATE BETWEEN k.valid_start_date AND k.valid_end_date THEN 'VALID'
        WHEN CURRENT_DATE > k.valid_end_date THEN 'EXPIRED'
        ELSE 'NOT_YET_VALID'
    END as validity_status
FROM knowledge_master k
LEFT JOIN projects p ON k.project_id = p.project_id
LEFT JOIN users u ON k.contributor_id = u.user_id
WHERE k.is_active = true;

CREATE OR REPLACE VIEW v_knowledge_statistics AS
SELECT
    COUNT(DISTINCT k.knowledge_id) as total_documents,
    COUNT(DISTINCT kc.chunk_id) as total_chunks,
    COUNT(DISTINCT k.project_id) as projects_count,
    COUNT(CASE WHEN CURRENT_DATE > k.valid_end_date THEN 1 END) as expired_count,
    COUNT(CASE WHEN CURRENT_DATE BETWEEN k.valid_start_date AND k.valid_end_date THEN 1 END) as active_count
FROM knowledge_master k
LEFT JOIN knowledge_chunks kc ON k.knowledge_id = kc.knowledge_id
WHERE k.is_active = true;

-- ============================================================================
-- 13. GRANTS (if needed for multi-user setup)
-- ============================================================================

-- GRANT USAGE ON SCHEMA public TO readonly_user;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;

-- ============================================================================
-- Schema Creation Complete
-- ============================================================================

COMMIT;
