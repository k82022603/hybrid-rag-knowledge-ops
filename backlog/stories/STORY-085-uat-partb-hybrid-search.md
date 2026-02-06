# STORY-085: UAT Part B - Hybrid Search Validation

## Story Information

| Item | Value |
|------|-------|
| **ID** | STORY-085 |
| **Jira** | SCRUM-81 |
| **Epic** | EPIC-002 Hybrid RAG Search |
| **Sprint** | Sprint 08 |
| **Points** | 3 |
| **Priority** | P1 - High |
| **Assignee** | QA/RAG |
| **Status** | Done |

---

## Background

After PPTX documents were uploaded and processed (STORY-083), this story validates the embedding and search pipeline end-to-end with real data.

---

## User Story

**As a** knowledge platform user,
**I want** to search uploaded PPTX content using Hybrid Search,
**So that** I can find relevant information from presentation documents.

---

## Acceptance Criteria

- [x] **Given** processed PPTX documents, **When** BGE-M3 embedding runs, **Then** 1024-dim vectors are generated
- [x] **Given** embedded documents, **When** indexed in Elasticsearch, **Then** vector and keyword indices are populated
- [x] **Given** a search query, **When** Hybrid Search executes, **Then** both vector and keyword results are returned
- [x] **Given** search results, **When** RRF fusion is applied, **Then** results are ranked by relevancy
- [x] **Given** test queries, **When** compared to expected answers, **Then** relevancy meets quality threshold

---

## Test Scenarios

| ID | Scenario | Description | Result |
|----|----------|-------------|--------|
| B-04 | BGE-M3 Embedding | Documents embedded with BGE-M3 model | PASS |
| B-05 | Elasticsearch Indexing | Embedded vectors stored in ES | PASS |
| B-06 | Hybrid Search | Vector + Keyword search returns relevant results | PASS |

---

## Performance Observations

| Metric | Measured Value | Target | Status |
|--------|---------------|--------|--------|
| Embedding Latency (CPU) | ~650ms/query | < 100ms (GPU) | Deferred to GPU |
| ES Search Latency | ~120ms | < 200ms | PASS |
| Total Hybrid Search | 984ms | < 500ms | FAIL (CPU) |
| Search Relevancy | Satisfactory | Relevant results | PASS |

**Note**: Total latency of 984ms exceeds 500ms target due to CPU-based BGE-M3 inference. This is expected to resolve in production GPU environment. Logged as STORY-090.

---

## Completion Date

2026-02-06

---

## References

- [Hybrid RAG Search Design](../../knowledge_service/docs/02_design/hybrid_rag_platform_detailed_design.md)
- [RAG Performance Test Design](../../knowledge_service/docs/02_design/rag_performance_test_design.md)
