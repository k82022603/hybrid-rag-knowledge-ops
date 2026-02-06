# Sprint 08 Known Issues (UAT Part B Findings)

> **Source**: UAT Part B Testing (2026-02-06)
> **Sprint**: Sprint 08

---

## ISSUE-001: Neo4j MERGE ON CREATE Syntax Compatibility

| Item | Value |
|------|-------|
| **Story** | STORY-088 |
| **Jira** | SCRUM-84 |
| **Severity** | Medium |
| **Type** | Bug |
| **Component** | AI Service - Neo4j Storage |
| **Status** | To Do |

**Description**: The `MERGE ... ON CREATE SET ...` Cypher pattern used in entity storage fails with a syntax error in the current Neo4j version. Knowledge Graph entities are not being stored, disabling graph-based search.

**Impact**: Graph-enhanced search unavailable. Vector + keyword Hybrid Search still works (degraded mode).

**Workaround**: System operates without graph enhancement. Core search functionality is unaffected.

---

## ISSUE-002: PG-AI Service Document Sync Not Implemented

| Item | Value |
|------|-------|
| **Story** | STORY-089 |
| **Jira** | SCRUM-85 |
| **Severity** | Medium |
| **Type** | Bug / Missing Feature |
| **Component** | Backend <-> AI Service Integration |
| **Status** | To Do |

**Description**: After document processing completes in AI Service, the processing status is not synchronized back to PostgreSQL. The UI shows documents as "uploaded" even after successful processing.

**Impact**: Users cannot see accurate processing status. Functional search is unaffected.

**Workaround**: Manual verification through AI Service logs or direct ES query.

---

## ISSUE-003: Hybrid Search Latency Exceeds Target (CPU)

| Item | Value |
|------|-------|
| **Story** | STORY-090 |
| **Jira** | SCRUM-86 |
| **Severity** | Low |
| **Type** | Performance |
| **Component** | AI Service - BGE-M3 Embedding |
| **Status** | To Do (Deferred to GPU) |

**Description**: Hybrid Search latency measured at 984ms on CPU, exceeding the 500ms P95 target. CPU-based BGE-M3 embedding inference is the primary bottleneck (66% of total time).

**Impact**: Search response slower than target in development environment. Expected to resolve in production GPU environment.

**Workaround**: Acceptable for development/UAT. Production GPU deployment expected to bring latency under 500ms.

---

## Summary

| ID | Severity | Type | Story | Workaround Available | Target Resolution |
|----|----------|------|-------|:--------------------:|-------------------|
| ISSUE-001 | Medium | Bug | STORY-088 | Yes (degraded mode) | Sprint 08 |
| ISSUE-002 | Medium | Bug/Feature | STORY-089 | Yes (manual check) | Sprint 08-09 |
| ISSUE-003 | Low | Performance | STORY-090 | Yes (CPU acceptable) | Production (GPU) |
