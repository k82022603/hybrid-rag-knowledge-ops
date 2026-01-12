// Neo4j Graph Schema for Hybrid RAG Knowledge Operations
// Version: 2.6
// Created: 2026-01-12
// Purpose: Knowledge graph relationships and entity connections

// ============================================================================
// 1. CREATE NODES
// ============================================================================

// Create User nodes
CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE;
CREATE INDEX user_username_idx IF NOT EXISTS FOR (u:User) ON (u.username);
CREATE INDEX user_department_idx IF NOT EXISTS FOR (u:User) ON (u.department);

// Create Project nodes
CREATE CONSTRAINT project_id_unique IF NOT EXISTS FOR (p:Project) REQUIRE p.project_id IS UNIQUE;
CREATE INDEX project_name_idx IF NOT EXISTS FOR (p:Project) ON (p.project_name);
CREATE INDEX project_code_idx IF NOT EXISTS FOR (p:Project) ON (p.project_code);

// Create Knowledge nodes (documents/chunks)
CREATE CONSTRAINT knowledge_id_unique IF NOT EXISTS FOR (k:Knowledge) REQUIRE k.knowledge_id IS UNIQUE;
CREATE INDEX knowledge_title_idx IF NOT EXISTS FOR (k:Knowledge) ON (k.title);
CREATE INDEX knowledge_type_idx IF NOT EXISTS FOR (k:Knowledge) ON (k.knowledge_type);

// Create Chunk nodes
CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS FOR (c:Chunk) REQUIRE c.chunk_id IS UNIQUE;
CREATE INDEX chunk_knowledge_idx IF NOT EXISTS FOR (c:Chunk) ON (c.knowledge_id);

// Create Entity nodes (Person, Technology, Topic, Keyword)
CREATE CONSTRAINT person_id_unique IF NOT EXISTS FOR (p:Person) REQUIRE p.person_id IS UNIQUE;
CREATE INDEX person_name_idx IF NOT EXISTS FOR (p:Person) ON (p.name);

CREATE CONSTRAINT technology_name_unique IF NOT EXISTS FOR (t:Technology) REQUIRE t.name IS UNIQUE;
CREATE INDEX technology_name_idx IF NOT EXISTS FOR (t:Technology) ON (t.name);

CREATE CONSTRAINT topic_name_unique IF NOT EXISTS FOR (t:Topic) REQUIRE t.name IS UNIQUE;
CREATE INDEX topic_name_idx IF NOT EXISTS FOR (t:Topic) ON (t.name);

CREATE CONSTRAINT keyword_value_unique IF NOT EXISTS FOR (k:Keyword) REQUIRE k.value IS UNIQUE;
CREATE INDEX keyword_value_idx IF NOT EXISTS FOR (k:Keyword) ON (k.value);

// ============================================================================
// 2. RELATIONSHIP TYPES & INDEXES
// ============================================================================

// User -> Knowledge: CREATED, CONTRIBUTED_TO, REVIEWED
// Knowledge -> Project: BELONGS_TO, OUTPUT_OF
// Knowledge -> Chunk: CONTAINS
// Knowledge -> Topic: CATEGORIZED_BY
// Knowledge -> Keyword: TAGGED_WITH
// Person -> Knowledge: MENTIONED_IN, CREATED, AUTHORED
// Technology -> Knowledge: USED_IN, REFERENCED_IN
// Person -> Person: COLLABORATED_WITH
// Knowledge -> Knowledge: REFERENCES, DEPENDS_ON, RELATED_TO

// Create relationship indexes for common queries
CREATE INDEX created_rel_idx IF NOT EXISTS FOR ()-[r:CREATED]-() ON (r.timestamp);
CREATE INDEX contains_rel_idx IF NOT EXISTS FOR ()-[r:CONTAINS]-() ON (r.chunk_index);
CREATE INDEX belongs_rel_idx IF NOT EXISTS FOR ()-[r:BELONGS_TO]-() ON (r.created_at);

// ============================================================================
// 3. SAMPLE DATA & INITIALIZATION
// ============================================================================

// Create initial Users
MERGE (u1:User {user_id: 1, username: "admin", full_name: "Administrator", department: "IT"})
SET u1.created_at = datetime(),
    u1.is_active = true;

// Create initial Topics
MERGE (t1:Topic {name: "Architecture", slug: "architecture"})
SET t1.created_at = datetime();

MERGE (t2:Topic {name: "Security", slug: "security"})
SET t2.created_at = datetime();

MERGE (t3:Topic {name: "Development", slug: "development"})
SET t3.created_at = datetime();

MERGE (t4:Topic {name: "Operations", slug: "operations"})
SET t4.created_at = datetime();

MERGE (t5:Topic {name: "Database", slug: "database"})
SET t5.created_at = datetime();

// Create initial Technologies
MERGE (tech1:Technology {name: "Python", version: "*"})
SET tech1.created_at = datetime(),
    tech1.category = "Programming Language";

MERGE (tech2:Technology {name: "PostgreSQL", version: "16+"})
SET tech2.created_at = datetime(),
    tech2.category = "Database";

MERGE (tech3:Technology {name: "Neo4j", version: "5.x"})
SET tech3.created_at = datetime(),
    tech3.category = "Database";

MERGE (tech4:Technology {name: "Elasticsearch", version: "8.x"})
SET tech4.created_at = datetime(),
    tech4.category = "Search Engine";

MERGE (tech5:Technology {name: "LangGraph", version: "0.2.x"})
SET tech5.created_at = datetime(),
    tech5.category = "AI Framework";

// ============================================================================
// 4. UTILITY FUNCTIONS & PATTERNS
// ============================================================================

// Pattern 1: Create or update Knowledge node
// MERGE creates if doesn't exist, updates if does
// Used when processing documents via DeepSeek extraction

// Example: Create Knowledge with metadata
// MERGE (k:Knowledge {knowledge_id: $knowledge_id})
// SET k.title = $title,
//     k.document_type = $document_type,
//     k.valid_start_date = $valid_start_date,
//     k.valid_end_date = $valid_end_date,
//     k.created_at = datetime()

// Pattern 2: Link Knowledge to Project
// MATCH (k:Knowledge {knowledge_id: $knowledge_id})
// MATCH (p:Project {project_id: $project_id})
// MERGE (k)-[r:BELONGS_TO]->(p)
// SET r.created_at = datetime()

// Pattern 3: Extract and link entities
// MATCH (k:Knowledge {knowledge_id: $knowledge_id})
// MERGE (person:Person {name: $person_name})
// MERGE (person)-[r:MENTIONED_IN]->(k)
// SET r.confidence = $confidence,
//     r.created_at = datetime()

// Pattern 4: Link person to knowledge as creator
// MATCH (u:User {user_id: $user_id})
// MATCH (k:Knowledge {knowledge_id: $knowledge_id})
// MERGE (u)-[r:CREATED]->(k)
// SET r.created_at = datetime()

// Pattern 5: Tag knowledge with topics
// MATCH (k:Knowledge {knowledge_id: $knowledge_id})
// MATCH (t:Topic {name: $topic_name})
// MERGE (k)-[r:CATEGORIZED_BY]->(t)
// SET r.created_at = datetime()

// Pattern 6: Mark technologies used in knowledge
// MATCH (k:Knowledge {knowledge_id: $knowledge_id})
// MATCH (tech:Technology {name: $tech_name})
// MERGE (tech)-[r:USED_IN]->(k)
// SET r.created_at = datetime(),
//     r.context = $context

// ============================================================================
// 5. QUERY EXAMPLES (for development reference)
// ============================================================================

// Q1: Find all knowledge related to a project
// MATCH (p:Project {project_name: "ProjectA"})
//       <-[r:BELONGS_TO]-(k:Knowledge)
//       -[c:CONTAINS]->(chunk:Chunk)
// RETURN k, chunk
// ORDER BY k.created_at DESC

// Q2: Find experts (people) in a topic
// MATCH (t:Topic {name: "Security"})
//       <-[r:CATEGORIZED_BY]-(k:Knowledge)
//       <-[m:MENTIONED_IN]-(p:Person)
// RETURN p.name, COUNT(k) as expertise_count
// ORDER BY expertise_count DESC
// LIMIT 10

// Q3: Find related knowledge (transitive)
// MATCH (k1:Knowledge {knowledge_id: 123})
//       -[:REFERENCES|:RELATED_TO]->(k2:Knowledge)
// RETURN k2
// ORDER BY k2.relevance_score DESC

// Q4: Find collaboration networks
// MATCH (p1:Person)-[:COLLABORATED_WITH]->(p2:Person)
// RETURN p1, p2
// LIMIT 50

// Q5: Find knowledge by technology stack
// MATCH (k:Knowledge)
//       <-[used:USED_IN]-(tech:Technology)
// WHERE tech.name IN ["Python", "PostgreSQL"]
// RETURN k, COLLECT(tech.name) as technologies
// GROUP BY k

// ============================================================================
// 6. GRAPH STATISTICS VIEW
// ============================================================================

// Run periodically to update graph stats
// CALL apoc.periodic.iterate(
//   "MATCH (n) WHERE NOT (n:_Synthetic) RETURN n",
//   "SET n:Indexed",
//   {batchSize:1000, parallel:true}
// )

// Get graph statistics
// MATCH (n) RETURN labels(n) as label, count(n) as count
// ORDER BY count DESC

// ============================================================================
// 7. CLEANUP & MAINTENANCE
// ============================================================================

// Delete all nodes and relationships (careful!)
// MATCH (n) DETACH DELETE n

// Delete specific pattern
// MATCH (k:Knowledge {knowledge_id: $knowledge_id})
// DETACH DELETE k

// Archive old knowledge (set timestamp)
// MATCH (k:Knowledge)
// WHERE k.created_at < datetime() - duration('P1Y')
// SET k:Archived, k.archived_at = datetime()

// ============================================================================
// Schema Initialization Complete
// ============================================================================

// Final verification queries:
// SHOW CONSTRAINTS
// SHOW INDEXES
// CALL apoc.schema.visualization()

// For Neo4j Browser visualization, run:
// CALL db.labels() YIELD label
// CALL db.relationshipTypes() YIELD relationshipType
// RETURN label, relationshipType
