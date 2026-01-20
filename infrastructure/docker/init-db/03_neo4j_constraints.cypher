// ============================================================================
// Neo4j Graph Schema for Hybrid RAG Knowledge Platform
// Version: 1.0
// Created: 2026-01-20
// Description: Constraints, indexes, and initial schema for knowledge graph
// ============================================================================

// ============================================================================
// CLEANUP (Optional - uncomment if resetting)
// ============================================================================
// MATCH (n) DETACH DELETE n;

// ============================================================================
// CONSTRAINTS - Ensure data integrity
// ============================================================================

// ----- Entity Node Constraints -----
CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
FOR (e:Entity) REQUIRE e.id IS UNIQUE;

// ----- Document Node Constraints -----
CREATE CONSTRAINT document_id_unique IF NOT EXISTS
FOR (d:Document) REQUIRE d.id IS UNIQUE;

// ----- TextUnit (Chunk) Node Constraints -----
CREATE CONSTRAINT textunit_id_unique IF NOT EXISTS
FOR (t:TextUnit) REQUIRE t.id IS UNIQUE;

// ----- Community Node Constraints -----
CREATE CONSTRAINT community_id_unique IF NOT EXISTS
FOR (c:Community) REQUIRE c.id IS UNIQUE;

// ----- Project Node Constraints -----
CREATE CONSTRAINT project_id_unique IF NOT EXISTS
FOR (p:Project) REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT project_code_unique IF NOT EXISTS
FOR (p:Project) REQUIRE p.code IS UNIQUE;

// ----- Person Node Constraints -----
CREATE CONSTRAINT person_id_unique IF NOT EXISTS
FOR (p:Person) REQUIRE p.id IS UNIQUE;

// ----- Technology Node Constraints -----
CREATE CONSTRAINT technology_id_unique IF NOT EXISTS
FOR (t:Technology) REQUIRE t.id IS UNIQUE;

// ----- Category Node Constraints -----
CREATE CONSTRAINT category_id_unique IF NOT EXISTS
FOR (c:Category) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT category_code_unique IF NOT EXISTS
FOR (c:Category) REQUIRE c.code IS UNIQUE;

// ============================================================================
// INDEXES - Optimize query performance
// ============================================================================

// ----- Entity Indexes -----
CREATE INDEX entity_type_idx IF NOT EXISTS
FOR (e:Entity) ON (e.type);

CREATE INDEX entity_name_idx IF NOT EXISTS
FOR (e:Entity) ON (e.name);

CREATE INDEX entity_canonical_name_idx IF NOT EXISTS
FOR (e:Entity) ON (e.canonical_name);

// Full-text search index for entities
CREATE FULLTEXT INDEX entity_fulltext_idx IF NOT EXISTS
FOR (e:Entity) ON EACH [e.name, e.description];

// ----- Document Indexes -----
CREATE INDEX document_type_idx IF NOT EXISTS
FOR (d:Document) ON (d.document_type);

CREATE INDEX document_title_idx IF NOT EXISTS
FOR (d:Document) ON (d.title);

CREATE INDEX document_valid_start_idx IF NOT EXISTS
FOR (d:Document) ON (d.valid_start_date);

CREATE INDEX document_valid_end_idx IF NOT EXISTS
FOR (d:Document) ON (d.valid_end_date);

CREATE INDEX document_processing_status_idx IF NOT EXISTS
FOR (d:Document) ON (d.processing_status);

// Full-text search index for documents
CREATE FULLTEXT INDEX document_fulltext_idx IF NOT EXISTS
FOR (d:Document) ON EACH [d.title];

// ----- TextUnit Indexes -----
CREATE INDEX textunit_document_idx IF NOT EXISTS
FOR (t:TextUnit) ON (t.document_id);

CREATE INDEX textunit_chunk_index_idx IF NOT EXISTS
FOR (t:TextUnit) ON (t.chunk_index);

// ----- Community Indexes -----
CREATE INDEX community_level_idx IF NOT EXISTS
FOR (c:Community) ON (c.level);

// ----- Project Indexes -----
CREATE INDEX project_status_idx IF NOT EXISTS
FOR (p:Project) ON (p.status);

CREATE INDEX project_name_idx IF NOT EXISTS
FOR (p:Project) ON (p.name);

// ----- Person Indexes -----
CREATE INDEX person_name_idx IF NOT EXISTS
FOR (p:Person) ON (p.name);

CREATE INDEX person_department_idx IF NOT EXISTS
FOR (p:Person) ON (p.department);

// Full-text search for persons
CREATE FULLTEXT INDEX person_fulltext_idx IF NOT EXISTS
FOR (p:Person) ON EACH [p.name, p.department, p.position];

// ----- Technology Indexes -----
CREATE INDEX technology_name_idx IF NOT EXISTS
FOR (t:Technology) ON (t.name);

// ----- Category Indexes -----
CREATE INDEX category_level_idx IF NOT EXISTS
FOR (c:Category) ON (c.level);

// ============================================================================
// NODE LABELS & EXPECTED PROPERTIES
// ============================================================================

// Entity Node Properties:
// - id: string (UUID) - REQUIRED
// - name: string - REQUIRED
// - type: string (Person, Project, Technology, Concept, Organization) - REQUIRED
// - description: string
// - canonical_name: string (normalized for deduplication)
// - pg_id: string (PostgreSQL reference ID)
// - created_at: datetime
// - updated_at: datetime

// Document Node Properties:
// - id: string (UUID) - REQUIRED
// - title: string - REQUIRED
// - document_type: string - REQUIRED
// - valid_start_date: date
// - valid_end_date: date
// - processing_status: string
// - chunk_count: integer
// - pg_id: string (PostgreSQL reference ID)
// - created_at: datetime

// TextUnit Node Properties:
// - id: string (UUID) - REQUIRED
// - document_id: string - REQUIRED
// - chunk_index: integer - REQUIRED
// - token_count: integer
// - es_id: string (Elasticsearch reference ID)
// - created_at: datetime

// Community Node Properties:
// - id: string (UUID) - REQUIRED
// - title: string
// - summary: string
// - level: integer (hierarchy level) - REQUIRED
// - rank: float (importance score)
// - created_at: datetime

// Project Node Properties:
// - id: string (UUID) - REQUIRED
// - name: string - REQUIRED
// - code: string - REQUIRED (unique)
// - status: string
// - start_date: date
// - end_date: date
// - pg_id: string (PostgreSQL reference ID)

// Person Node Properties:
// - id: string (UUID) - REQUIRED
// - name: string - REQUIRED
// - email: string
// - department: string
// - position: string
// - pg_id: string (PostgreSQL reference ID)

// Technology Node Properties:
// - id: string (UUID) - REQUIRED
// - name: string - REQUIRED
// - category: string (language, framework, database, tool, etc.)
// - version: string

// Category Node Properties:
// - id: string (UUID) - REQUIRED
// - name: string - REQUIRED
// - code: string - REQUIRED (unique)
// - level: integer
// - pg_id: string (PostgreSQL reference ID)

// ============================================================================
// RELATIONSHIP TYPES
// ============================================================================

// Entity relationships:
// (Entity)-[:RELATED_TO {type, description, weight, source}]->(Entity)
// (Entity)-[:MENTIONED_IN {relevance, mention_count}]->(TextUnit)
// (Entity)-[:BELONGS_TO {rank}]->(Community)

// Document relationships:
// (TextUnit)-[:PART_OF {position}]->(Document)
// (Document)-[:BELONGS_TO_PROJECT]->(Project)
// (Document)-[:AUTHORED_BY]->(Person)
// (Document)-[:CATEGORIZED_AS]->(Category)

// Community relationships:
// (Community)-[:PARENT_OF]->(Community)

// Person relationships:
// (Person)-[:WORKS_ON]->(Project)
// (Person)-[:COLLABORATED_WITH {project_id, description}]->(Person)

// Technology relationships:
// (Technology)-[:USED_IN]->(Project)
// (Technology)-[:RELATED_TO {type}]->(Technology)

// Category relationships:
// (Category)-[:PARENT_OF]->(Category)

// ============================================================================
// INITIAL DATA - Default Categories
// ============================================================================

// Create default categories (matching PostgreSQL initial data)
MERGE (c1:Category {code: 'tech_doc'})
SET c1.id = randomUUID(),
    c1.name = 'Technical Documentation',
    c1.level = 1,
    c1.sort_order = 1,
    c1.created_at = datetime();

MERGE (c2:Category {code: 'meeting'})
SET c2.id = randomUUID(),
    c2.name = 'Meeting Notes',
    c2.level = 1,
    c2.sort_order = 2,
    c2.created_at = datetime();

MERGE (c3:Category {code: 'report'})
SET c3.id = randomUUID(),
    c3.name = 'Reports',
    c3.level = 1,
    c3.sort_order = 3,
    c3.created_at = datetime();

MERGE (c4:Category {code: 'spec'})
SET c4.id = randomUUID(),
    c4.name = 'Specifications',
    c4.level = 1,
    c4.sort_order = 4,
    c4.created_at = datetime();

// ============================================================================
// APOC PROCEDURES (if APOC plugin is installed)
// ============================================================================

// Note: The following requires APOC plugin to be installed
// You can uncomment and use these for advanced operations

// Create schema assertion (validates schema on startup)
// CALL apoc.schema.assert(
//   {Entity: ['id'], Document: ['id'], TextUnit: ['id'], Community: ['id']},
//   {Entity: ['name', 'type'], Document: ['title', 'document_type']}
// );

// ============================================================================
// USEFUL QUERIES FOR VERIFICATION
// ============================================================================

// Verify constraints:
// SHOW CONSTRAINTS;

// Verify indexes:
// SHOW INDEXES;

// Count nodes by label:
// MATCH (n)
// RETURN labels(n) AS label, count(*) AS count
// ORDER BY count DESC;

// Count relationships by type:
// MATCH ()-[r]->()
// RETURN type(r) AS relationship_type, count(*) AS count
// ORDER BY count DESC;

// ============================================================================
// END OF SCHEMA DEFINITION
// ============================================================================
