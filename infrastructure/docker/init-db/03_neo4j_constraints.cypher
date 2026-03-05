// ============================================================================
// Neo4j Graph Schema for Hybrid RAG Knowledge Platform
// Version: 3.0
// Updated: 2026-03-05
// Description: Unified schema — aligned with codebase (neo4j_storage.py,
//              batch_entity_extraction.py, initial_data_loader.py, run_etl_fast.py)
//
// Migration Note (v1.0 → v3.0):
//   - TextUnit label → Chunk (code already uses Chunk everywhere)
//   - Community/Category/User labels removed (not used in current codebase)
//   - Knowledge node retained (neo4j_storage.py primary path)
//   - Document node retained (initial_data_loader.py / run_etl_fast.py path)
//   - Relationship consolidation:
//       CONTAINS  : Knowledge → Chunk  (neo4j_storage.py)
//       PART_OF   : Chunk → Document   (initial_data_loader.py, ETL scripts)
//       MENTIONS  : Chunk → Entity     (batch_entity_extraction.py, neo4j_storage.py)
//       MENTIONED_IN : Entity → Knowledge  (neo4j_storage.py)
//       HAS_ENTITY   : Document → Entity   (initial_data_loader.py)
//       RELATED_TO   : Entity ↔ Entity     (all modules)
//   - Existing data is already v3.0 compatible (no destructive migration needed)
// ============================================================================

// ============================================================================
// CLEANUP (Optional - uncomment if resetting)
// ============================================================================
// MATCH (n) DETACH DELETE n;

// ============================================================================
// CONSTRAINTS - Ensure data integrity
// ============================================================================

// ----- Knowledge Node (neo4j_storage.py primary document representation) -----
CREATE CONSTRAINT knowledge_id_unique IF NOT EXISTS
FOR (k:Knowledge) REQUIRE k.knowledge_id IS UNIQUE;

// ----- Document Node (initial_data_loader.py / ETL fast path) -----
CREATE CONSTRAINT document_id_unique IF NOT EXISTS
FOR (d:Document) REQUIRE d.id IS UNIQUE;

// ----- Chunk Node -----
CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS
FOR (c:Chunk) REQUIRE c.id IS UNIQUE;

// ----- Entity Node (base label for all entity types) -----
CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
FOR (e:Entity) REQUIRE e.id IS UNIQUE;

// ----- Person Node (sub-label of Entity) -----
CREATE CONSTRAINT person_id_unique IF NOT EXISTS
FOR (p:Person) REQUIRE p.person_id IS UNIQUE;

// ----- Technology Node (sub-label of Entity) -----
CREATE CONSTRAINT technology_name_unique IF NOT EXISTS
FOR (t:Technology) REQUIRE t.name IS UNIQUE;

// ----- Topic Node (sub-label of Entity) -----
CREATE CONSTRAINT topic_name_unique IF NOT EXISTS
FOR (t:Topic) REQUIRE t.name IS UNIQUE;

// ----- Keyword Node (sub-label of Entity) -----
CREATE CONSTRAINT keyword_value_unique IF NOT EXISTS
FOR (k:Keyword) REQUIRE k.value IS UNIQUE;

// ----- Project Node -----
CREATE CONSTRAINT project_id_unique IF NOT EXISTS
FOR (p:Project) REQUIRE p.id IS UNIQUE;

// ============================================================================
// INDEXES - Optimize query performance
// ============================================================================

// ----- Knowledge Indexes -----
CREATE INDEX knowledge_title_idx IF NOT EXISTS
FOR (k:Knowledge) ON (k.title);

CREATE INDEX knowledge_type_idx IF NOT EXISTS
FOR (k:Knowledge) ON (k.document_type);

// ----- Document Indexes -----
CREATE INDEX document_type_idx IF NOT EXISTS
FOR (d:Document) ON (d.doc_type);

CREATE INDEX document_title_idx IF NOT EXISTS
FOR (d:Document) ON (d.title);

// ----- Chunk Indexes -----
CREATE INDEX chunk_knowledge_idx IF NOT EXISTS
FOR (c:Chunk) ON (c.knowledge_id);

CREATE INDEX chunk_index_idx IF NOT EXISTS
FOR (c:Chunk) ON (c.chunk_index);

// ----- Entity Indexes -----
CREATE INDEX entity_type_idx IF NOT EXISTS
FOR (e:Entity) ON (e.type);

CREATE INDEX entity_name_idx IF NOT EXISTS
FOR (e:Entity) ON (e.name);

CREATE INDEX entity_canonical_name_idx IF NOT EXISTS
FOR (e:Entity) ON (e.canonical_name);

// ----- Person Indexes -----
CREATE INDEX person_name_idx IF NOT EXISTS
FOR (p:Person) ON (p.name);

// ----- Technology Indexes -----
CREATE INDEX technology_name_idx IF NOT EXISTS
FOR (t:Technology) ON (t.name);

// ----- Topic Indexes -----
CREATE INDEX topic_name_idx IF NOT EXISTS
FOR (t:Topic) ON (t.name);

// ----- Keyword Indexes -----
CREATE INDEX keyword_value_idx IF NOT EXISTS
FOR (k:Keyword) ON (k.value);

// ----- Project Indexes -----
CREATE INDEX project_name_idx IF NOT EXISTS
FOR (p:Project) ON (p.name);

// ----- Full-text Search Indexes -----
// Entity full-text (multi-label search across all entity sub-types)
CREATE FULLTEXT INDEX entity_fulltext_idx IF NOT EXISTS
FOR (n:Person|Technology|Topic|Keyword|Entity) ON EACH [n.name, n.description];

// Document full-text
CREATE FULLTEXT INDEX document_fulltext_idx IF NOT EXISTS
FOR (d:Document) ON EACH [d.title];

// ----- Relationship Indexes -----
CREATE INDEX contains_rel_idx IF NOT EXISTS FOR ()-[r:CONTAINS]-() ON (r.chunk_index);
CREATE INDEX belongs_rel_idx IF NOT EXISTS FOR ()-[r:BELONGS_TO]-() ON (r.created_at);

// ============================================================================
// RELATIONSHIP TYPES (reference documentation)
// ============================================================================

// Core document-chunk-entity graph:
//   (Knowledge)-[:CONTAINS]->(Chunk)           -- neo4j_storage.py: save_chunks()
//   (Chunk)-[:PART_OF]->(Document)              -- initial_data_loader.py, run_etl_fast.py
//   (Chunk)-[:MENTIONS]->(Entity)               -- neo4j_storage.py: save_chunk_entity_mentions()
//                                                   batch_entity_extraction.py
//   (Entity)-[:MENTIONED_IN]->(Knowledge)       -- neo4j_storage.py: _create_mentioned_in_relation()
//   (Document)-[:HAS_ENTITY]->(Entity)          -- initial_data_loader.py
//   (Entity)-[:RELATED_TO {type}]->(Entity)     -- all modules (entity_extraction.py types:
//                                                   CREATED, PARTICIPATED, USES, BELONGS_TO,
//                                                   RELATED_TO, MANAGES, DEPENDS_ON)

// Extended relationships (graph.py, search.py):
//   (Person:Entity)-[:RELATED_TO]->(Project)    -- graph.py: topic_experts()
//   (Document)-[:BELONGS_TO_PROJECT]->(Project)  -- extended linking

// ============================================================================
// INITIAL DATA (minimal seed data)
// ============================================================================

// No seed data — documents, chunks, and entities are created by ETL pipeline
// and document_processing_pipeline.py at runtime.

// ============================================================================
// VERIFICATION QUERIES
// ============================================================================

// Verify constraints: SHOW CONSTRAINTS;
// Verify indexes:     SHOW INDEXES;
// Count by label:     MATCH (n) RETURN labels(n) AS label, count(*) AS count ORDER BY count DESC;
// Count by rel type:  MATCH ()-[r]->() RETURN type(r) AS rel, count(*) AS count ORDER BY count DESC;

// ============================================================================
// END OF SCHEMA DEFINITION
// ============================================================================
