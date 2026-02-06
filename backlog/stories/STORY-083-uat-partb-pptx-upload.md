# STORY-083: UAT Part B - PPTX Upload + Processing Pipeline

## Story Information

| Item | Value |
|------|-------|
| **ID** | STORY-083 |
| **Jira** | SCRUM-79 |
| **Epic** | EPIC-005 RAG Quality & Performance |
| **Sprint** | Sprint 08 |
| **Points** | 5 |
| **Priority** | P0 - Critical |
| **Assignee** | QA/RAG |
| **Status** | Done |

---

## Background

Sprint 07 completed Phase 5 (Deployment Preparation) with TechLead approval (39/40). UAT Part B focuses on validating the core document processing pipeline with real-world PPTX files to ensure production readiness.

---

## User Story

**As a** knowledge platform user,
**I want** to upload PPTX files and have them automatically processed through the full pipeline,
**So that** I can search and retrieve knowledge from presentation documents.

---

## Acceptance Criteria

- [x] **Given** 5 PPTX files are uploaded, **When** processing starts, **Then** Docling parser extracts text successfully
- [x] **Given** parsed documents, **When** chunking occurs, **Then** semantic chunks are created with appropriate sizes
- [x] **Given** chunked documents, **When** embedding runs, **Then** BGE-M3 produces 1024-dim vectors
- [x] **Given** processing pipeline, **When** user monitors status, **Then** SSE streaming shows real-time progress
- [x] **Given** all documents processed, **When** checking PostgreSQL, **Then** all documents show "completed" status

---

## Test Scenarios

| ID | Scenario | Description | Result |
|----|----------|-------------|--------|
| B-01 | PPTX Upload | 5 PPTX files uploaded via UI | PASS |
| B-02 | Document Parsing | Docling parser extracts text from PPTX | PASS |
| B-03 | Semantic Chunking | Documents chunked into semantic units | PASS |

---

## Test Results (2026-02-06)

### Upload Details
- Files: 5 PPTX presentation files
- Total size: varied
- Upload method: UI drag-and-drop

### Processing Pipeline
1. **Upload**: Files received by AI Service via multipart upload
2. **Parsing**: Docling parser extracted text and structure from PPTX
3. **Chunking**: Semantic chunking applied with overlap
4. **Status**: All documents reached "completed" in PostgreSQL

### Issues Discovered
- Neo4j MERGE ON CREATE syntax error (logged as STORY-088)
- PG-AI Service document sync not implemented (logged as STORY-089)

---

## Completion Date

2026-02-06

---

## References

- [Sprint 08](../../backlog/sprints/sprint-08.md)
- [UAT Part A Results](../../knowledge_service/docs/04_testing/)
