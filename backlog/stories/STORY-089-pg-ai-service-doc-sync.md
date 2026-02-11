# STORY-089: BUG - PG-AI Service Document Sync Not Implemented

## Story Information

| Item | Value |
|------|-------|
| **ID** | STORY-089 |
| **Jira** | SCRUM-85 |
| **Epic** | EPIC-001 Document Processing |
| **Sprint** | Sprint 08 |
| **Points** | 3 |
| **Priority** | P2 - Medium |
| **Assignee** | Backend/RAG |
| **Status** | To Do |

---

## Bug Report

### Summary
After document upload and processing through the AI Service pipeline, the document processing status is not synchronized back to PostgreSQL (managed by Backend/Gateway). The UI shows documents as "uploaded" but cannot reflect the actual processing status (parsing, chunking, embedding, complete).

### Discovered
2026-02-06, during UAT Part B testing (STORY-083)

### Environment
- Backend: SpringBoot Gateway
- AI Service: FastAPI (Python)
- Database: PostgreSQL (SSOT for document metadata)

### Steps to Reproduce
1. Upload document through UI
2. Backend saves document metadata to PostgreSQL (status: "uploaded")
3. AI Service begins processing (parsing -> chunking -> embedding)
4. AI Service completes processing
5. Check PostgreSQL - document status still shows "uploaded"
6. UI does not reflect "completed" status

### Expected Behavior
Document status in PostgreSQL should be updated as processing progresses:
- uploaded -> parsing -> chunking -> embedding -> completed

### Actual Behavior
Document status remains "uploaded" after AI Service completes processing.

### Impact
- Users cannot see accurate processing status in UI
- Manual page refresh does not fix (data not updated in PG)
- SSE streaming shows pipeline events but PG is not updated
- Functional impact is medium - search works, but status display is incorrect

---

## Architecture Gap

```
Current Flow:
  UI -> Backend/PG (upload) -> AI Service (process) -> ES/Neo4j (store)
                                    [no callback to PG]

Required Flow:
  UI -> Backend/PG (upload) -> AI Service (process) -> ES/Neo4j (store)
                                    |
                                    +--> Backend/PG (status update callback)
```

---

## Acceptance Criteria

- [ ] **Given** AI Service starts processing, **When** each stage completes, **Then** status event is published
- [ ] **Given** a status event, **When** Backend receives it, **Then** PostgreSQL document record is updated
- [ ] **Given** updated PG record, **When** UI queries document status, **Then** current processing stage is shown
- [ ] **Given** processing completion, **When** checking document list, **Then** status shows "completed"

---

## Tasks

- [ ] Design callback API or event mechanism (webhook vs polling vs message queue)
- [ ] Implement status update endpoint in Backend
- [ ] Implement status callback in AI Service processing pipeline
- [ ] Update PostgreSQL document schema if needed (add processing_status column)
- [ ] Test end-to-end status flow
- [ ] Update UI to display processing status from PG

---

## Design Options

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **A. Webhook callback** | Simple, direct | Coupling, retry needed | Recommended for MVP |
| **B. Polling** | Decoupled | Delay, resource waste | Not recommended |
| **C. Message queue** | Async, reliable | Complexity, new infra | Future consideration |

---

## References

- [API Integration Design](../../knowledge_service/docs/02_design/04_api_integration_design.md)
- [Backend Detailed Design](../../knowledge_service/docs/02_design/06_backend_detailed_design.md)
