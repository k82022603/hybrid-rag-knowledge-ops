// ============================================================================
// Neo4j Graph Schema for Hybrid RAG Knowledge Operations
// Version: 3.0 (unified with init-db/03_neo4j_constraints.cypher)
// Updated: 2026-03-05
// Purpose: Authoritative schema reference — aligned with actual codebase
//
// Source of truth: This file and init-db/03_neo4j_constraints.cypher are
// kept in sync. Any schema change must update BOTH files.
//
// History:
//   v1.0 (2026-01-20): init-db — Entity/Document/TextUnit/Community
//   v2.6 (2026-01-12): schema.cypher — User/Knowledge/Chunk/Entity subtypes
//   v3.0 (2026-03-05): Unified — codebase audit, removed unused labels,
//                       consolidated relationships
// ============================================================================

// ============================================================================
// 1. NODE LABELS & PROPERTIES
// ============================================================================

// Knowledge Node (neo4j_storage.py — primary document representation)
// Properties:
//   - knowledge_id: string (UUID) — UNIQUE, maps to PG document ID
//   - title: string — document title
//   - document_type: string — e.g. "tech_doc", "meeting", "report"
//   - valid_start_date: string/date
//   - valid_end_date: string/date
//   - chunk_count: integer
//   - pg_id: string — PostgreSQL reference
//   - created_at: datetime
//   - updated_at: datetime

// Document Node (initial_data_loader.py, run_etl_fast.py — ETL path)
// Properties:
//   - id: string (UUID) — UNIQUE, maps to PG document ID
//   - title: string
//   - file_path: string
//   - doc_type: string
//   - created_at: datetime

// Chunk Node
// Properties:
//   - id: string (chunk_id) — UNIQUE
//   - knowledge_id: string — parent knowledge/document ID
//   - content: string (truncated to 500 chars in Neo4j)
//   - chunk_index: integer — position within document
//   - heading: string — section heading
//   - token_count: integer
//   - created_at: datetime

// Entity Node (base label — all entities also have :Entity label)
// Properties:
//   - id: string (UUID)
//   - name: string — REQUIRED
//   - type: string — Person, Technology, Topic, Keyword, etc.
//   - description: string
//   - canonical_name: string — normalized for deduplication
//   - confidence: float
//   - created_at: datetime
//   - updated_at: datetime

// Person Node (sub-label, always also :Entity)
// Properties:
//   - person_id: string — UNIQUE
//   - name: string
//   - department: string
//   - position: string

// Technology Node (sub-label, always also :Entity)
// Properties:
//   - name: string — UNIQUE
//   - category: string — "Programming Language", "Database", "Framework", etc.
//   - version: string

// Topic Node (sub-label, always also :Entity)
// Properties:
//   - name: string — UNIQUE
//   - slug: string

// Keyword Node (sub-label, always also :Entity)
// Properties:
//   - value: string — UNIQUE (merge key)
//   - name: string

// Project Node
// Properties:
//   - id: string (UUID) — UNIQUE
//   - name: string
//   - project_name: string
//   - status: string

// ============================================================================
// 2. CONSTRAINTS
// ============================================================================

CREATE CONSTRAINT knowledge_id_unique IF NOT EXISTS
FOR (k:Knowledge) REQUIRE k.knowledge_id IS UNIQUE;

CREATE CONSTRAINT document_id_unique IF NOT EXISTS
FOR (d:Document) REQUIRE d.id IS UNIQUE;

CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS
FOR (c:Chunk) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
FOR (e:Entity) REQUIRE e.id IS UNIQUE;

CREATE CONSTRAINT person_id_unique IF NOT EXISTS
FOR (p:Person) REQUIRE p.person_id IS UNIQUE;

CREATE CONSTRAINT technology_name_unique IF NOT EXISTS
FOR (t:Technology) REQUIRE t.name IS UNIQUE;

CREATE CONSTRAINT topic_name_unique IF NOT EXISTS
FOR (t:Topic) REQUIRE t.name IS UNIQUE;

CREATE CONSTRAINT keyword_value_unique IF NOT EXISTS
FOR (k:Keyword) REQUIRE k.value IS UNIQUE;

CREATE CONSTRAINT project_id_unique IF NOT EXISTS
FOR (p:Project) REQUIRE p.id IS UNIQUE;

// ============================================================================
// 3. INDEXES
// ============================================================================

// Knowledge
CREATE INDEX knowledge_title_idx IF NOT EXISTS FOR (k:Knowledge) ON (k.title);
CREATE INDEX knowledge_type_idx IF NOT EXISTS FOR (k:Knowledge) ON (k.document_type);

// Document
CREATE INDEX document_type_idx IF NOT EXISTS FOR (d:Document) ON (d.doc_type);
CREATE INDEX document_title_idx IF NOT EXISTS FOR (d:Document) ON (d.title);

// Chunk
CREATE INDEX chunk_knowledge_idx IF NOT EXISTS FOR (c:Chunk) ON (c.knowledge_id);
CREATE INDEX chunk_index_idx IF NOT EXISTS FOR (c:Chunk) ON (c.chunk_index);

// Entity
CREATE INDEX entity_type_idx IF NOT EXISTS FOR (e:Entity) ON (e.type);
CREATE INDEX entity_name_idx IF NOT EXISTS FOR (e:Entity) ON (e.name);
CREATE INDEX entity_canonical_name_idx IF NOT EXISTS FOR (e:Entity) ON (e.canonical_name);

// Sub-type indexes
CREATE INDEX person_name_idx IF NOT EXISTS FOR (p:Person) ON (p.name);
CREATE INDEX technology_name_idx IF NOT EXISTS FOR (t:Technology) ON (t.name);
CREATE INDEX topic_name_idx IF NOT EXISTS FOR (t:Topic) ON (t.name);
CREATE INDEX keyword_value_idx IF NOT EXISTS FOR (k:Keyword) ON (k.value);

// Project
CREATE INDEX project_name_idx IF NOT EXISTS FOR (p:Project) ON (p.name);

// Full-text search
CREATE FULLTEXT INDEX entity_fulltext_idx IF NOT EXISTS
FOR (n:Person|Technology|Topic|Keyword|Entity) ON EACH [n.name, n.description];

CREATE FULLTEXT INDEX document_fulltext_idx IF NOT EXISTS
FOR (d:Document) ON EACH [d.title];

// Relationship indexes
CREATE INDEX contains_rel_idx IF NOT EXISTS FOR ()-[r:CONTAINS]-() ON (r.chunk_index);
CREATE INDEX belongs_rel_idx IF NOT EXISTS FOR ()-[r:BELONGS_TO]-() ON (r.created_at);

// ============================================================================
// 4. RELATIONSHIP TYPES
// ============================================================================

// ┌─────────────────────────────────────────────────────────────────┐
// │  Core Knowledge Graph Relationships                            │
// │                                                                │
// │  Knowledge ──CONTAINS──> Chunk ──MENTIONS──> Entity            │
// │      │                     │                   │               │
// │      │                     │               RELATED_TO          │
// │      │                     │                   │               │
// │      │                     v                   v               │
// │      │                  Document <──HAS_ENTITY── Entity        │
// │      │                     ^                                   │
// │      │                     │                                   │
// │      └── MENTIONED_IN <────┘                                   │
// │           (Entity → Knowledge)                                 │
// └─────────────────────────────────────────────────────────────────┘

// (Knowledge)-[:CONTAINS]->(Chunk)
//   Created by: neo4j_storage.py save_chunks()
//   Properties: chunk_index (integer)

// (Chunk)-[:PART_OF]->(Document)
//   Created by: initial_data_loader.py, run_etl_fast.py
//   Properties: none

// (Chunk)-[:MENTIONS]->(Entity)
//   Created by: neo4j_storage.py save_chunk_entity_mentions(),
//               batch_entity_extraction.py
//   Properties: confidence (float)

// (Entity)-[:MENTIONED_IN]->(Knowledge)
//   Created by: neo4j_storage.py _create_mentioned_in_relation()
//   Properties: relevance (float), mention_count (integer)

// (Document)-[:HAS_ENTITY]->(Entity)
//   Created by: initial_data_loader.py
//   Properties: none

// (Entity)-[:RELATED_TO {type}]->(Entity)
//   Created by: neo4j_storage.py save_relationships(),
//               batch_entity_extraction.py,
//               initial_data_loader.py
//   Properties: type (string: CREATED, PARTICIPATED, USES, BELONGS_TO,
//                     RELATED_TO, MANAGES, DEPENDS_ON),
//               weight (float), description (string),
//               source_doc (string)

// Extended:
// (Person:Entity)-[:RELATED_TO]->(Project)    -- graph.py topic_experts()
// (Document)-[:BELONGS_TO_PROJECT]->(Project) -- future extension

// ============================================================================
// 5. ENTITY TYPE → LABEL MAPPING (neo4j_storage.py)
// ============================================================================

// Entity type string → Neo4j label (dual-label: always also :Entity)
//   Person       → :Person:Entity
//   Organization → :Person:Entity  (shares label with Person)
//   Technology   → :Technology:Entity
//   Project      → :Topic:Entity   (mapped to Topic)
//   Concept      → :Topic:Entity   (mapped to Topic)
//   Date         → :Keyword:Entity
//   Location     → :Keyword:Entity

// ============================================================================
// 6. QUERY PATTERNS (development reference)
// ============================================================================

// Q1: Find entities mentioned in a chunk (post-RRF enrichment)
// MATCH (c:Chunk {id: $chunk_id})-[:MENTIONS]->(e:Entity)
// WHERE size(e.name) >= 2
// RETURN e.name, e.type, e.description

// Q2: Get subgraph around an entity (1-hop expansion)
// MATCH (e:Entity) WHERE toLower(e.name) CONTAINS toLower($query)
// OPTIONAL MATCH (e)-[:RELATED_TO]-(related:Entity)
// RETURN e, related

// Q3: Find topic experts via graph traversal
// MATCH (topic:Entity)
// WHERE toLower(topic.name) CONTAINS toLower($topic_keyword)
// MATCH (person:Person:Entity)-[r:RELATED_TO]-(topic)
// RETURN person.name, count(r) as connections ORDER BY connections DESC

// Q4: Delete document and associated chunks
// MATCH (k:Knowledge {knowledge_id: $doc_id})-[:CONTAINS]->(c:Chunk)
// DETACH DELETE c
// WITH k DETACH DELETE k

// Q5: Count graph statistics
// MATCH (e:Entity) RETURN count(e) as entities
// MATCH ()-[r:RELATED_TO]->() RETURN count(r) as relations
// MATCH ()-[r:MENTIONS]->() RETURN count(r) as mentions

// ============================================================================
// 7. VERIFICATION
// ============================================================================

// SHOW CONSTRAINTS;
// SHOW INDEXES;
// MATCH (n) RETURN labels(n) AS label, count(*) AS count ORDER BY count DESC;
// MATCH ()-[r]->() RETURN type(r) AS rel, count(*) AS count ORDER BY count DESC;

// ============================================================================
// Schema v3.0 — Unified & Complete
// ============================================================================
