# Daily Standup Meeting - UAT Issue Analysis

**Date**: 2026-02-06
**Time**: Standup Meeting
**Channel**: #proj-hrkp-standup
**Theme**: Incomplete Feature Completion - UAT Findings

---

## Meeting Background

User conducted UAT (User Acceptance Testing) and discovered two critical issues:
1. **File Upload -> 3 Storage Not Reflected**: Files uploaded but data not appearing in PostgreSQL, Neo4j, Elasticsearch
2. **Chat Retriever Error**: RAG search through chat interface returns errors

---

## PM Status Report

**[PM]**
- Yesterday: Sprint 01 backlog management, test coverage improvement oversight
- Today: UAT issue deep analysis, work distribution planning, agent task delegation
- Blocker: None (analysis phase)
- Note: These are P0 issues that block core functionality demonstration

---

## Code Investigation Results

### Issue 1: File Upload -> 3 Storage Pipeline

#### Current State: PARTIALLY IMPLEMENTED (Auto-trigger MISSING)

The complete pipeline code exists in individual modules, but **critical integration gaps** prevent end-to-end operation:

**What IS implemented:**
1. **File Upload API** (`/api/v1/documents/upload`) - WORKING
   - File: `knowledge_service/src/app/api/routes/documents.py`
   - Accepts PDF/DOCX/HWP/PPTX files
   - Saves to MinIO or local filesystem fallback
   - Creates in-memory document record with status "queued"

2. **Document Processing Pipeline** - CODE EXISTS BUT NOT AUTO-TRIGGERED
   - File: `knowledge_service/src/app/services/document_processing_pipeline.py`
   - Full pipeline: Download -> Parse -> Chunk -> Embed -> ES Store -> Neo4j Store
   - Properly integrates with all 3 storage backends

3. **Manual Process Trigger** (`POST /documents/{id}/process`) - IMPLEMENTED
   - File: `knowledge_service/src/app/api/routes/documents.py` (line 474-559)
   - Can manually trigger processing for a specific document

4. **Background Worker** - IMPLEMENTED BUT DISABLED BY DEFAULT
   - File: `knowledge_service/src/app/services/background_worker.py`
   - Polls for queued/uploaded documents and processes them
   - **BUT**: Requires `ENABLE_BACKGROUND_WORKER=true` environment variable (line 80 of main.py)
   - Docker Compose does NOT set this variable

**ROOT CAUSES IDENTIFIED:**

| # | Problem | Location | Impact |
|---|---------|----------|--------|
| 1 | **Background worker disabled by default** | `main.py` line 80: `ENABLE_BACKGROUND_WORKER` defaults to `false` | Documents stay in "queued" state forever |
| 2 | **No auto-processing after upload** | `documents.py` upload endpoint does NOT call `process_document()` | Upload succeeds but no ETL pipeline runs |
| 3 | **In-memory document store** | `documents.py` line 68: `_document_store: Dict` | Data lost on service restart, not in PostgreSQL |
| 4 | **SearchService singleton has no ES/Neo4j client** | `search.py` line 906: `SearchService()` initialized with no args | `es_client=None`, `neo4j_driver=None` |
| 5 | **ES/Neo4j clients created in lifespan but not passed to SearchService** | `main.py` saves to `app.state` but SearchService singleton doesn't use it | Search returns empty results |

**Data Flow Analysis:**

```
CURRENT (Broken):
Upload -> MinIO/Local -> In-Memory Store (queued) -> STOPS HERE
                                                      ^
                                                      No auto-trigger!

EXPECTED (Working):
Upload -> MinIO/Local -> PostgreSQL -> Background Worker polls ->
  Parse -> Chunk -> Embed -> ES Index -> Neo4j Graph -> PostgreSQL (completed)
```

---

### Issue 2: Chat Retriever Error

#### Current State: CODE EXISTS BUT DEPENDENCY CHAIN BROKEN

**What IS implemented:**
1. **Chat API** (`POST /api/v1/search/chat`) - CODE EXISTS
   - File: `knowledge_service/src/app/api/routes/search.py` (line 354-449)
   - Uses LangGraph RAG Workflow (STORY-051)
   - Supports conversation history (STORY-057)
   - Supports SSE streaming (`/chat/stream`)

2. **RAG Workflow** - IMPLEMENTED
   - File: `knowledge_service/src/app/agents/rag_workflow.py`
   - Pipeline: Plan -> Retrieve -> Generate
   - Uses SearchService for hybrid search

3. **Search Service** - PARTIALLY WORKING
   - File: `knowledge_service/src/app/services/search.py`
   - Hybrid search (Vector + Keyword + Graph) with RRF fusion
   - Cache integration (STORY-060)

**ROOT CAUSES IDENTIFIED:**

| # | Problem | Location | Impact |
|---|---------|----------|--------|
| 1 | **SearchService singleton initialized without ES/Neo4j clients** | `search.py` line 906: `SearchService()` - no args | All searches return empty results |
| 2 | **ES client from lifespan not passed to search service** | `main.py` saves `app.state.es_client` but `get_search_service()` doesn't use it | Vector/keyword search returns [] |
| 3 | **Neo4j driver from lifespan not passed to search service** | `main.py` saves `app.state.neo4j_driver` but `get_search_service()` doesn't use it | Graph search returns [] |
| 4 | **EmbeddingService not initialized at startup** | `main.py` line 77: "will be initialized on first request" | First query triggers model loading (slow/may fail) |
| 5 | **Chat endpoint requires authentication** | `search.py` line 362: `Depends(get_current_user)` | May fail if token not properly set |
| 6 | **No indexed data** (depends on Issue 1) | Even if search works, no documents are indexed | Empty search results |

**Error Chain Analysis:**

```
Chat Request -> auth check -> get_rag_workflow() -> workflow.run() ->
  _retrieve() -> SearchService.hybrid_search() ->
    semantic_search() -> es_client=None -> empty results
    keyword_search() -> es_client=None -> empty results
    _graph_search() -> neo4j_driver=None -> empty results
  -> _generate() -> no context -> fallback answer OR LLM error
```

---

## Work Distribution Plan

### P0 - Critical (Must Fix for Core Functionality)

#### TASK-01: Connect ES/Neo4j Clients to SearchService [Backend/RAG]
- **Priority**: P0
- **Assignee**: RAG Engineer (primary), Backend (secondary)
- **Description**: The `get_search_service()` singleton is created without ES/Neo4j clients. The lifespan creates these clients in `app.state` but never passes them to SearchService.
- **Fix Required**:
  - Option A: Pass `app.state.es_client` and `app.state.neo4j_driver` to SearchService initialization
  - Option B: Have SearchService lazily resolve clients from app state or create its own connections
- **Files to modify**:
  - `knowledge_service/src/app/services/search.py` - accept clients or resolve them
  - `knowledge_service/src/app/main.py` - pass clients at startup
- **Acceptance Criteria**:
  - SearchService.hybrid_search returns actual results from ES/Neo4j
  - Vector search (kNN) works against Elasticsearch
  - Graph search works against Neo4j

#### TASK-02: Enable Auto-Processing After Upload [RAG/ETL]
- **Priority**: P0
- **Assignee**: RAG Engineer (primary), ETL Engineer (secondary)
- **Description**: After file upload, the ETL pipeline must automatically run. Currently documents stay in "queued" state.
- **Fix Required** (choose one approach):
  - Option A: Auto-call `process_document()` after upload (synchronous or async task)
  - Option B: Enable background worker by default (`ENABLE_BACKGROUND_WORKER=true` in docker-compose)
  - Option C (recommended): Both - immediate async task + background worker as safety net
- **Files to modify**:
  - `knowledge_service/src/app/api/routes/documents.py` - trigger processing after upload
  - `infrastructure/docker/docker-compose.yml` - add `ENABLE_BACKGROUND_WORKER=true`
- **Acceptance Criteria**:
  - Upload a PDF -> automatically parsed, chunked, embedded, stored in ES + Neo4j
  - Document status progresses: queued -> processing -> parsing -> chunking -> embedding -> storing -> completed

#### TASK-03: Migrate Document Store from In-Memory to PostgreSQL [Backend/DB]
- **Priority**: P0
- **Assignee**: Backend (primary), Database Designer (secondary)
- **Description**: The document store is in-memory (`_document_store: Dict`). Data is lost on restart.
- **Fix Required**:
  - Use `DocumentModel` (already defined in `database.py`) for PostgreSQL persistence
  - The `DocumentRepository` class already supports PostgreSQL - just need to pass `document_store=None`
- **Files to modify**:
  - `knowledge_service/src/app/api/routes/documents.py` - use PostgreSQL-backed repository
  - Ensure PostgreSQL tables are created (Alembic migration or auto-create)
- **Acceptance Criteria**:
  - Uploaded documents persist across service restarts
  - Document list/status queries hit PostgreSQL

### P1 - High Priority (Important for UX)

#### TASK-04: Fix ES Index Field Mapping for Search [RAG]
- **Priority**: P1
- **Assignee**: RAG Engineer
- **Description**: ES storage uses `text` field for content, but search service queries `content` field. Also, kNN query uses `embedding` field but storage uses `dense_vector`.
- **Analysis**:
  - `es_storage.py` indexes as: `text`, `dense_vector`
  - `search.py` semantic_search queries: `knn.field = "embedding"` (line 482)
  - `search.py` keyword_search queries: `content^3`, `content.nori^2` (line 571-574)
- **Fix Required**:
  - Align field names: either change storage to use `content`/`embedding` OR change search to use `text`/`dense_vector`
- **Files to modify**:
  - `knowledge_service/src/app/services/search.py` - fix field names in queries
- **Acceptance Criteria**:
  - kNN search properly queries `dense_vector` field
  - BM25 search properly queries `text` field

#### TASK-05: Frontend Upload -> Process Flow Integration [Frontend]
- **Priority**: P1
- **Assignee**: Frontend Developer
- **Description**: Frontend upload page calls `/documents/upload` but doesn't trigger processing or show processing status.
- **Fix Required**:
  - After upload, either auto-call `/documents/{id}/process` or poll status
  - Show processing progress (parsing -> chunking -> embedding -> completed)
  - Handle processing errors in UI
- **Files to modify**:
  - `knowledge_service/frontend/src/pages/DocumentUploadPage.tsx`
  - `knowledge_service/frontend/src/services/knowledgeService.ts`
- **Acceptance Criteria**:
  - Upload triggers processing
  - UI shows processing stages and progress
  - Error states are displayed

#### TASK-06: Docker Compose Environment Variables [Infra]
- **Priority**: P1
- **Assignee**: Infra Engineer
- **Description**: Add required environment variables to docker-compose for auto-processing.
- **Fix Required**:
  - Add `ENABLE_BACKGROUND_WORKER=true` to ai-service container
  - Ensure MinIO credentials are properly set
  - Verify ES/Neo4j connection strings are correct
- **Files to modify**:
  - `infrastructure/docker/docker-compose.yml`
- **Acceptance Criteria**:
  - Background worker starts automatically
  - All service connections (ES, Neo4j, MinIO, PostgreSQL) work

### P2 - Medium Priority (Polish)

#### TASK-07: Add Document Processing Status WebSocket/SSE [Backend/Frontend]
- **Priority**: P2
- **Assignee**: Backend (primary), Frontend (secondary)
- **Description**: Add real-time processing status updates via WebSocket or SSE
- **Acceptance Criteria**: Frontend receives live updates during document processing

#### TASK-08: Add Error Recovery and Retry for Failed Documents [RAG/ETL]
- **Priority**: P2
- **Assignee**: RAG Engineer
- **Description**: Failed documents should be retryable from the UI
- **Acceptance Criteria**: "Retry" button for failed documents, automatic retry for transient failures

---

## Dependency Graph

```
TASK-06 (Infra: Docker env) ----+
                                 |
TASK-03 (DB: PostgreSQL) --------+----> TASK-02 (RAG: Auto-process) ----> TASK-05 (FE: UI flow)
                                 |
TASK-01 (RAG: ES/Neo4j clients) -+----> TASK-04 (RAG: Field mapping)
                                                        |
                                                        v
                                            Chat Retriever Works!
```

**Critical Path**: TASK-01 + TASK-02 + TASK-03 must be completed FIRST before end-to-end demo works.

---

## Sprint Impact Assessment

| Metric | Before Fix | After Fix (Expected) |
|--------|-----------|---------------------|
| File Upload -> Storage | 0% (stuck at queued) | 100% (3 storage systems) |
| Chat Retriever | Error (no data, no clients) | Working (hybrid search + LLM answer) |
| Document Processing Pipeline | Exists but never runs | Auto-runs on upload |
| Data Persistence | In-memory (lost on restart) | PostgreSQL backed |
| Search Results | Empty (no ES/Neo4j client) | Actual results from indexed data |

---

## Risk Monitoring

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| BGE-M3 model loading slow/fails | Medium | High | Pre-load at startup, fallback to sentence-transformers |
| Docling PDF parsing fails | Medium | Medium | Test with actual user documents, add format-specific error handling |
| Neo4j entity extraction LLM cost | Low | Medium | Rate limit, batch processing |
| ES index mapping conflicts | Medium | High | Drop and recreate index if needed |

---

## Next Action Items

### Immediate (Today)
1. **PM**: Assign TASK-01 to RAG Engineer
2. **PM**: Assign TASK-06 to Infra Engineer (parallel with TASK-01)
3. **PM**: Assign TASK-03 to Backend Developer
4. **PM**: Schedule follow-up check after TASK-01 + TASK-02 complete

### Short-term (This Week)
1. **RAG Engineer**: Complete TASK-01, TASK-02, TASK-04
2. **Backend Developer**: Complete TASK-03
3. **Infra Engineer**: Complete TASK-06
4. **Frontend Developer**: Complete TASK-05 after backend tasks done

### Validation
1. End-to-end test: Upload PDF -> Wait for processing -> Search via chat -> Get answer with sources
2. Verify all 3 storage systems have data after upload
3. Verify chat returns relevant answers from uploaded documents

---

## Standup End

**Meeting concluded**. Critical P0 issues identified with clear root causes and action plan.
Total 8 tasks identified: 3 P0, 3 P1, 2 P2.
Critical path: TASK-01 (ES/Neo4j clients) + TASK-02 (Auto-processing) + TASK-03 (PostgreSQL)
