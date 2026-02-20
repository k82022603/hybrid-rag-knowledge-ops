# UAT Issue Emergency Standup Meeting

**Date**: 2026-02-06
**Time**: Session-based (asynchronous)
**Channel**: #proj-hrkp-standup / #proj-hrkp-dev
**Type**: Emergency UAT Issue Resolution
**Facilitator**: PM Agent

---

## Background

User performed UAT on 2026-02-05 and discovered two critical issues:
1. **File Upload -> 3-Store Pipeline Broken**: Uploaded files do not propagate to PostgreSQL/Neo4j/Elasticsearch
2. **Chat Retriever Error**: Search functionality in the chat interface fails

## Root Causes Identified (Pre-Meeting Analysis)

| # | Root Cause | File | Line | Severity |
|---|-----------|------|------|----------|
| RC-1 | `ENABLE_BACKGROUND_WORKER` defaults to `"false"` | `main.py` | 80 | P0 |
| RC-2 | Upload does not auto-trigger processing pipeline | `documents.py` | 338 | P0 |
| RC-3 | In-memory document store (`Dict`) loses data on restart | `documents.py` | 68 | P0 |
| RC-4 | SearchService singleton has no ES/Neo4j client injection | `search.py` | 906 | P0 |
| RC-5 | ES field name mismatch: storage uses `text`/`dense_vector`, search uses `content`/`embedding` | `search.py` vs `es_storage.py` | multiple | P1 |

---

## Agent Reports

### 1. RAG Engineer - SearchService & ES Field Mismatch

**Issues Analyzed**:

**RC-4: SearchService Client Not Injected**
- `get_search_service()` at line 902-907 creates `SearchService()` with no arguments
- Constructor defaults `es_client=None` and `neo4j_driver=None` (line 174-178)
- Even though `main.py` lifespan connects ES and Neo4j to `app.state`, the SearchService singleton never receives these references
- Result: All vector/keyword/graph searches return empty results

**RC-5: ES Field Name Inconsistency**
- **Storage layer** (`es_storage.py` line 379): Stores content as `text`, vector as `dense_vector`
- **Search layer** (`search.py` line 482-484): kNN queries field `embedding` (should be `dense_vector`)
- **Search layer** (`search.py` line 570-571): BM25 queries field `content` (should be `text`)
- **ES Mapping** (`mappings.json`): Defines `text` (not `content`) and `dense_vector` (not `embedding`)
- The `_parse_es_results` in search.py line 885 reads `content` from `_source` but the field is stored as `text`

**Proposed Fix**:
1. Modify `get_search_service()` to accept and pass `es_client` and `neo4j_driver` from `app.state`
2. Add a FastAPI dependency or startup hook that initializes SearchService with the connected clients
3. Fix kNN search field: `"field": "embedding"` -> `"field": "dense_vector"`
4. Fix BM25 search fields: `"content^3", "content.nori^2"` -> `"text^3", "text.standard^2"`
5. Fix `_parse_es_results`: `src.get("content", "")` -> `src.get("text", "")`

**Estimated Effort**: 3-4 hours

---

### 2. ETL Engineer - Background Worker & Auto-Processing Pipeline

**Issues Analyzed**:

**RC-1: Background Worker Disabled by Default**
- `main.py` line 80: `os.getenv("ENABLE_BACKGROUND_WORKER", "false")`
- Default is `"false"`, and this env var is NOT set in `docker-compose.yml` ai-service environment block
- Worker never starts, so `queued` documents are never polled/processed
- Even if manually started, it uses the in-memory store which loses data on restart

**RC-2: Upload Does Not Auto-Trigger Processing**
- `upload_document()` (documents.py line 201-357) ends at line 338: stores to `_document_store` and returns
- Status is set to `DocumentStatus.QUEUED` (line 330) but no processing is triggered
- Manual trigger exists at `POST /{document_id}/process` (line 480) but frontend doesn't call it after upload
- Batch endpoint exists at `POST /process-pending` (line 568) but also not auto-triggered

**Proposed Fix**:
1. **Short-term (P0)**: Add `ENABLE_BACKGROUND_WORKER=true` to docker-compose.yml ai-service env block
2. **Short-term (P0)**: After file upload success (line 338), auto-trigger `asyncio.create_task(run_processing())` to process the document immediately (similar to `trigger_document_processing`)
3. **Medium-term (P1)**: Set `WORKER_POLL_INTERVAL=10` and `WORKER_BATCH_SIZE=5` in docker-compose env
4. **Long-term**: When PostgreSQL backend is ready, switch `_get_document_store()` from in-memory to DB queries

**Estimated Effort**: 2-3 hours

---

### 3. Backend Developer - In-Memory to PostgreSQL ORM Transition

**Issues Analyzed**:

**RC-3: In-Memory Document Store**
- `documents.py` line 68: `_document_store: Dict[UUID, Dict[str, Any]] = {}`
- All uploaded document metadata lives only in Python process memory
- Container restart or crash = all document records lost
- Upload/status/list APIs all depend on this in-memory dict
- Background worker and processing pipeline both reference this same dict

**Current PostgreSQL Readiness**:
- `DocumentProcessingPipeline` already has `DocumentRepository` class (document_processing_pipeline.py line 99-356)
- `DocumentRepository` has dual mode: in-memory (when `document_store` provided) or PostgreSQL (when `None`)
- PostgreSQL path uses `app.core.database.DocumentModel` and `get_async_session()`
- Docker-compose already has PostgreSQL with schema init scripts
- Schema file exists at `infrastructure/database/postgres/schema.sql`

**Proposed Fix**:
1. **Phase 1 (P0)**: Create `DocumentModel` SQLAlchemy ORM class in `app/core/database.py` with columns: id, filename, format, size_bytes, status, storage_path, progress_percent, error_message, created_at, updated_at, metadata
2. **Phase 2 (P0)**: Replace `_document_store` dict usage in `documents.py` routes with `DocumentRepository` calls
3. **Phase 3 (P1)**: Ensure upload, status query, list query, and process trigger all use PostgreSQL
4. **Phase 4 (P1)**: Add Alembic migration for the documents table
5. **Immediate workaround**: Add auto-processing after upload so at least the file gets to ES/Neo4j before restart

**Estimated Effort**: 6-8 hours (full ORM), 2 hours (immediate workaround)

---

### 4. Infra Engineer - Docker Compose Environment Variables

**Issues Analyzed**:

**Docker Compose ai-service Section** (docker-compose.yml line 298-365):
- Missing `ENABLE_BACKGROUND_WORKER` environment variable
- Missing `WORKER_POLL_INTERVAL` and `WORKER_BATCH_SIZE`
- Missing `MINIO_ENDPOINT` for MinIO download in processing pipeline
- ES/Neo4j connection settings are present but SearchService singleton does not use them

**Current Environment Variables Set**:
```
ELASTICSEARCH_HOST=elasticsearch
ELASTICSEARCH_PORT=9200
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER, NEO4J_PASSWORD
POSTGRES_HOST=postgresql (etc.)
MINIO_URL=http://minio:9000
```

**Missing Environment Variables**:
```
ENABLE_BACKGROUND_WORKER=true         # P0: Enable auto-processing
WORKER_POLL_INTERVAL=10               # P1: 10-second polling
WORKER_BATCH_SIZE=5                   # P1: 5 docs per batch
MINIO_ENDPOINT=minio:9000             # P0: For MinIO SDK download
MINIO_SECURE=false                    # P0: HTTP not HTTPS
```

**Proposed Fix**:
1. Add missing environment variables to ai-service section in docker-compose.yml
2. Verify `MINIO_ENDPOINT` vs `MINIO_URL` usage - pipeline uses `MINIO_ENDPOINT` (document_processing_pipeline.py FileStorage line 405) while compose sets `MINIO_URL`
3. Ensure all service connections are consistently named

**Estimated Effort**: 30 minutes

---

### 5. Frontend Developer - Upload Status & Processing UI

**Issues Analyzed**:

**Current Upload Flow (Frontend)**:
- Upload page exists at `DocumentUploadPage.tsx`
- Uses `knowledgeService.ts` for API calls
- After upload, likely shows "queued" status but no progress indication
- No auto-refresh or polling for processing status
- Chat interface uses search API which returns empty due to RC-4/RC-5

**Proposed Fix**:
1. **P1**: After successful upload, show a processing status indicator (spinner/progress bar)
2. **P1**: Add polling mechanism to `GET /documents/{id}/status` endpoint to track progress (0-100%)
3. **P1**: Show status transitions: queued -> parsing -> chunking -> embedding -> storing -> completed
4. **P2**: Add toast/notification when document processing completes
5. **P2**: Auto-refresh document list after processing completes
6. **P2**: Display processing errors in the UI when status is "failed"

**Estimated Effort**: 4-6 hours

---

## Action Items Summary

### P0 - Critical (Must fix for basic functionality)

| # | Action Item | Agent | File(s) | Est. Hours |
|---|------------|-------|---------|------------|
| A-1 | Add `ENABLE_BACKGROUND_WORKER=true` + `MINIO_ENDPOINT=minio:9000` to docker-compose.yml | **Infra** | `docker-compose.yml` | 0.5h |
| A-2 | Fix SearchService singleton to receive ES/Neo4j clients from app.state | **RAG** | `search.py`, `main.py` or search route | 2h |
| A-3 | Fix ES field name mismatch (embedding->dense_vector, content->text) | **RAG** | `search.py` | 1h |
| A-4 | Add auto-trigger processing after upload (asyncio.create_task) | **ETL** | `documents.py` | 1h |

### P1 - Important (Required for production readiness)

| # | Action Item | Agent | File(s) | Est. Hours |
|---|------------|-------|---------|------------|
| B-1 | Implement DocumentModel ORM and migrate from in-memory to PostgreSQL | **Backend** | `database.py`, `documents.py` | 6h |
| B-2 | Add document processing status polling UI | **Frontend** | `DocumentUploadPage.tsx`, `knowledgeService.ts` | 4h |
| B-3 | Add `WORKER_POLL_INTERVAL`, `WORKER_BATCH_SIZE` env vars | **Infra** | `docker-compose.yml` | 0.5h |

### P2 - Nice to have (User experience improvements)

| # | Action Item | Agent | File(s) | Est. Hours |
|---|------------|-------|---------|------------|
| C-1 | Toast notification on processing completion | **Frontend** | Frontend components | 2h |
| C-2 | Error display in UI for failed documents | **Frontend** | Frontend components | 2h |

---

## Execution Order (Dependency Graph)

```
Phase 1 (Parallel - No dependencies):
  A-1 (Infra: docker-compose env)
  A-3 (RAG: ES field name fix)

Phase 2 (Depends on Phase 1):
  A-2 (RAG: SearchService client injection - needs ES connection working)
  A-4 (ETL: Auto-trigger processing - needs background worker enabled)

Phase 3 (Parallel - After Phase 2):
  B-1 (Backend: ORM migration)
  B-2 (Frontend: Status polling UI)

Phase 4 (After Phase 3):
  B-3 (Infra: Fine-tune worker settings)
  C-1, C-2 (Frontend: UX improvements)
```

---

## Agreements

1. **P0 items first**: A-1 through A-4 must be completed before any other work
2. **Testing**: After P0 fixes, perform end-to-end UAT: upload PDF -> verify 3-store -> search via chat
3. **No Mock testing**: All validation must be done with Docker containers running (TEST_MODE=docker)
4. **Branch strategy**: Create `fix/uat-upload-pipeline` branch for all P0 fixes
5. **Coordination**: RAG and ETL engineers should coordinate on SearchService changes since both touch related files

---

## Risk Monitor

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| PostgreSQL ORM migration breaks existing tests | Medium | High | Keep in-memory fallback for tests, add integration tests |
| ES field name fix causes index recreation | Low | Medium | Fix code to match existing mappings, no mapping change needed |
| Background worker overloads AI service | Low | Medium | Configure batch_size=5, poll_interval=10s |
| Frontend polling causes excessive API calls | Low | Low | Use exponential backoff, stop polling on completion |

---

## Next Steps

1. PM assigns P0 tasks to agents immediately
2. Infra Engineer starts with A-1 (fastest, unblocks others)
3. RAG Engineer starts A-2 and A-3 in parallel
4. ETL Engineer starts A-4
5. After P0 validation, proceed to P1 tasks
6. Sprint review after all P0/P1 complete

---

*Meeting recorded by PM Agent*
*Next standup: After P0 completion*
