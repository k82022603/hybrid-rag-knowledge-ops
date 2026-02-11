# STORY-088: BUG - Neo4j MERGE ON CREATE Syntax Compatibility

## Story Information

| Item | Value |
|------|-------|
| **ID** | STORY-088 |
| **Jira** | SCRUM-84 |
| **Epic** | EPIC-002 Hybrid RAG Search |
| **Sprint** | Sprint 08 |
| **Points** | 2 |
| **Priority** | P2 - Medium |
| **Assignee** | RAG |
| **Status** | To Do |

---

## Bug Report

### Summary
Neo4j MERGE ON CREATE SET syntax fails during Knowledge Graph entity storage in the document processing pipeline.

### Discovered
2026-02-06, during UAT Part B testing (STORY-083)

### Environment
- Neo4j Community Edition (Docker container `kp-neo4j`)
- APOC plugin installed
- Accessed from AI Service (Python neo4j driver)

### Steps to Reproduce
1. Upload PPTX document through UI
2. Document parsing and chunking completes
3. Entity extraction produces entities (Person, Organization, etc.)
4. AI Service attempts to store entities in Neo4j
5. Cypher query with `MERGE ... ON CREATE SET ...` fails with syntax error

### Expected Behavior
Entities should be created or merged in Neo4j Knowledge Graph, allowing graph-based search.

### Actual Behavior
Cypher syntax error on `MERGE ... ON CREATE SET ...` pattern. Entities are not stored.

### Impact
- Knowledge Graph entities are NOT being stored
- Graph-based search (subgraph traversal) is NOT available
- Vector + keyword Hybrid Search still works (degraded mode)
- Overall search quality slightly reduced (no graph context)

---

## Root Cause Analysis (Pending)

Possible causes:
1. Neo4j version incompatibility with MERGE ON CREATE syntax
2. APOC plugin version mismatch
3. Property type conflict in SET clause
4. Missing constraint/index required for MERGE

---

## Acceptance Criteria

- [ ] **Given** entity extraction results, **When** analyzing the Cypher query, **Then** root cause is identified
- [ ] **Given** root cause, **When** fix is applied, **Then** MERGE or alternative pattern works
- [ ] **Given** fixed entity storage, **When** uploading new documents, **Then** entities are stored in Neo4j
- [ ] **Given** stored entities, **When** querying Knowledge Graph, **Then** subgraph results are returned

---

## Tasks

- [ ] Reproduce the error in development environment
- [ ] Check Neo4j version and APOC compatibility matrix
- [ ] Identify exact Cypher syntax causing the error
- [ ] Implement fix (MERGE ON CREATE fix or fallback to CREATE+MATCH pattern)
- [ ] Test with real PPTX data from UAT
- [ ] Verify graph-based search returns results

---

## Workaround

Currently, the system operates in **degraded mode** - Hybrid Search (vector + keyword) works without graph enhancement. This is acceptable for initial UAT but should be fixed before production.

---

## References

- [STORY-006 Neo4j ES Storage](./STORY-006-neo4j-es-storage.md)
- [TECH-DEBT-001 Neo4j Strategy Pattern](../tech-debt/sprint-03-tech-debt.md)
- [Hybrid RAG Design](../../knowledge_service/docs/02_design/01_hybrid_rag_platform_detailed_design.md)
