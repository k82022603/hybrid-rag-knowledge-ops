# Sprint 04 Day 1 - Technical Architecture Review

**Author**: TechLead Agent
**Date**: 2026-01-28
**Sprint**: Sprint 04 (Improvement + Quality Enhancement)
**Status**: Completed
**Review Scope**: STORY-050, STORY-051, STORY-053

---

## 1. Executive Summary

### 1.1 Review Objective

Sprint 04 Day 1 focuses on three parallel stories addressing quality, security, and integration concerns from Sprint 03. This review analyzes technical risks, proposes architecture guidelines, and prepares code review checklists.

### 1.2 Overall Risk Assessment

| Story | Risk Level | Key Concern |
|-------|-----------|-------------|
| **STORY-050** (SSE Refactor) | **Medium** | Browser compat, reconnection, error boundary |
| **STORY-051** (Pipeline Integration) | **High** | Two-service coupling, timeout cascading, error propagation |
| **STORY-053** (Security Hardening) | **High** | Hardcoded JWT secret, plaintext passwords, no input validation |

### 1.3 Codebase Score: 72.5/100 B+

---

## 2. Current Architecture Status

### 2.1 System Architecture

Layered architecture: React Frontend -> Spring Cloud Gateway (:8080) -> SpringBoot Backend (:8081) -> Knowledge Service (FastAPI :8000) -> AI Service (LangGraph) -> DeepSeek LLM. Data: PostgreSQL (SSOT), Elasticsearch (Vector), Neo4j (Graph), Redis (Cache).

### 2.2 Code Structure

| Service | Language | Key Files | Maturity |
|---------|----------|-----------|----------|
| **knowledge_service** | Python (FastAPI) | api/routes/search.py, services/rag_pipeline.py | Active |
| **ai_service** | Python (LangGraph) | workflows/rag_workflow.py, nodes/generator.py | Sprint 03 |
| **Backend** | Java (SpringBoot) | Design only | Design phase |
| **Frontend** | TypeScript (React) | Design only | Design phase |

### 2.3 Key Finding: Dual RAG Pipeline

Critical: **two parallel RAG implementations** exist:
1. knowledge_service/services/rag_pipeline.py: Direct RAG with SearchService + LLM
2. ai_service/workflows/rag_workflow.py: LangGraph StateGraph (Planner->Retriever->Generator->Validator)

STORY-051 must clarify the canonical path.

---

## 3. STORY-050: SSE EventSource to fetch+ReadableStream

### 3.1 Current State

Frontend design (Section 15) already defines ChatSSEService using fetch() + ReadableStream. Features: POST method, Bearer auth header, AbortController, TextDecoder. Story addresses implementation gap.

### 3.2 Technical Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Browser Compat** | Medium | ReadableStream: Chrome 43+, Firefox 65+, Safari 10.1+ |
| **Reconnection** | High | EventSource auto-reconnects; fetch needs manual impl |
| **Partial Parsing** | Medium | SSE chunks may split across read boundaries |
| **Memory Leaks** | Medium | reader.releaseLock() must be in finally block |
| **Token Expiry** | High | Long streams may encounter JWT expiration |

### 3.3 Guidelines

**Reconnection Strategy (Required)**: Exponential backoff - maxRetries=3, baseDelay=1000ms, maxDelay=10000ms, multiplier=2. Retry on network errors, NOT 4xx.

**Partial Message Buffer (Required)**: Accumulate partial data across chunk boundaries. Keep incomplete lines in buffer.

**Component Lifecycle (Required)**: AbortController per-stream, cleanup on unmount, previous stream aborted before new one, releaseLock() in finally.

### 3.4 Acceptance Criteria

- [ ] fetch() API used (NOT EventSource) for POST support
- [ ] ReadableStream reader properly acquired and released
- [ ] SSE parser handles partial chunks correctly
- [ ] AbortController for cancellation
- [ ] Exponential backoff reconnection
- [ ] JWT token refresh before stream if near expiry
- [ ] Component unmount cleanup
- [ ] Error boundary integration
- [ ] TypeScript strict types for SSE events
- [ ] Unit tests for SSE parser edge cases

---

## 4. STORY-051: ai_service - knowledge_service Pipeline Integration

### 4.1 Current State

Two Python services with overlapping RAG: knowledge_service (HTTP API + direct RAG) and ai_service (LangGraph workflow with retry).

### 4.2 Technical Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Circular Dependencies** | High | ai_service wraps knowledge_service HybridRetriever |
| **HTTP vs Direct Import** | High | Python imports; breaks if separate containers |
| **Timeout Cascading** | High | Workflow retry cascades: HTTP > LLM > search |
| **Error Propagation** | High | Must translate to HTTP codes |
| **Streaming** | High | SSE from LangGraph needs async generator chaining |

### 4.3 Architecture Decision: Unified Service (Option C)

**Recommended**: Merge ai_service as internal module within knowledge_service. Both Python, shared code, same host.

| Option | Verdict |
|--------|----------|
| A: Direct Import | Tight coupling |
| B: HTTP API | Unnecessary overhead |
| **C: Unified** | **Recommended** |

### 4.4 Guidelines

**Module Structure**: Merge ai_service workflows into knowledge_service/src/app/workflows/.

**Timeout Strategy**: HTTP=120s, Workflow=90s, Search=30s, LLM=60s, Reranking=15s. Use asyncio.wait_for().

**Error Translation**:

| Error | HTTP | Code |
|-------|------|------|
| ValueError | 400 | RAG001 |
| LLM timeout | 504 | LLM002 |
| LLM rate limit | 429 | LLM003 |
| Search failure | 502 | SRCH001 |
| Max retries | 200 | N/A (best-effort) |
| Unexpected | 500 | RAG100 |

### 4.5 Acceptance Criteria

- [ ] Clear integration pattern chosen
- [ ] RAGWorkflow invoked from search routes
- [ ] Error translation to HTTP responses
- [ ] Timeout at each layer
- [ ] SSE events mapped from LangGraph
- [ ] No circular imports
- [ ] Shared SearchService
- [ ] traceId propagation
- [ ] Unit + integration tests

---

## 5. STORY-053: JWT Secret, Input Validation, Default Credentials

### 5.1 Critical Security Issues Found

**5.1.1 Hardcoded JWT Secret (CRITICAL)**: auth.py line 25 - JWT_SECRET_KEY hardcoded. Anyone reading source can forge tokens.

**5.1.2 Plaintext Passwords (CRITICAL)**: MOCK_USERS with password123 and admin123 in plaintext.

**5.1.3 Missing Input Validation**: LoginRequest - email format only, min_length=6. No max_length.

**5.1.4 No Brute Force Protection**: No rate limiting or lockout.

### 5.2 OWASP Risk Assessment

| Risk | Severity | OWASP |
|------|----------|-------|
| Hardcoded JWT Secret | **Critical** | A02:2021 |
| Default Credentials | **Critical** | A07:2021 |
| Plaintext Passwords | **Critical** | A02:2021 |
| No Rate Limiting | **High** | A07:2021 |
| Weak Validation | **Medium** | A03:2021 |

### 5.3 Guidelines

**JWT Secret (Required)**: Add jwt_secret_key to Settings - Required, no default, min 32 chars, reject old hardcoded default.

**Password Hashing (Required)**: passlib with bcrypt, cost factor 12.

**Input Validation (Required)**: Email max=255, Password min=8 max=128.

**Rate Limiting (Required)**: Login 5/min/IP. Use slowapi.

**Default Credentials (Required)**: Gate MOCK_USERS behind ENABLE_MOCK_AUTH (default false).

**Token Enhancement**: Add iss/aud claims, Redis for refresh tokens, jti for revocation.

### 5.4 Acceptance Criteria

- [ ] JWT_SECRET_KEY from env only (no default)
- [ ] Min 32-char validation
- [ ] Old hardcoded secret rejected
- [ ] bcrypt password hashing
- [ ] MOCK_USERS gated (default false)
- [ ] Login rate limiting (5/min/IP)
- [ ] Email max=255, Password min=8 max=128
- [ ] Token iss/aud claims
- [ ] .env.example updated
- [ ] No hardcoded credentials anywhere

---

## 6. Cross-Story Integration Risks

### 6.1 SSE + JWT Token Expiry (STORY-050 x STORY-053)

Long chat stream + strict JWT validation = mid-stream failure.
**Mitigation**: Check expiry before stream. Refresh if <5min. Error handler detects 401 and retries.

### 6.2 Streaming Format Mismatch (STORY-050 x STORY-051)

Event format changes in pipeline break frontend parser.
**Mitigation**: Shared SSE event contract (Section 7.1).

### 6.3 Security Changes Break Tests (STORY-053)

JWT secret change breaks existing tests.
**Mitigation**: conftest.py fixture setting JWT_SECRET_KEY env var.

---

## 7. Architecture Guidelines

### 7.1 SSE Event Contract

Format: data: {"type": "<event_type>", ...}\n\n

| Type | Payload | Description |
|------|---------|-------------|
| start | conversationId, sources[] | Stream started |
| chunk | content | Answer text chunk |
| step | node, status | Workflow progress |
| done | messageId, totalTokens? | Complete |
| error | code, message, traceId | Error |

### 7.2 HTTP Standards

| Aspect | Standard |
|--------|----------|
| Timeout | Connect: 5s, Read: 120s |
| Retry | Exponential backoff, max 3 for 5xx |
| Circuit Breaker | 50% failure, 30s half-open |
| Tracing | X-Request-Id propagation |

### 7.3 Security Standards

| Standard | Requirement |
|----------|-------------|
| Secrets | All via env vars, validated at startup |
| Passwords | bcrypt, cost factor 12 |
| JWT | HS256 min, RS256 preferred |
| Token Life | Access: 15-30 min, Refresh: 7 days |
| Rate Limiting | Auth: 5/min/IP, Search: 30/min/user |

---

## 8. Code Review Checklists

### 8.1 STORY-050 (Frontend SSE)

- [ ] Uses fetch() NOT EventSource
- [ ] ReadableStream with getReader()
- [ ] UTF-8 TextDecoder
- [ ] SSE parser handles split chunks
- [ ] HTTP errors handled before stream
- [ ] AbortError handled separately
- [ ] Exponential backoff retry
- [ ] Token refresh if near expiry
- [ ] releaseLock() in finally
- [ ] AbortController cleanup on unmount
- [ ] SSEEvent types match contract
- [ ] Unit tests for parser

### 8.2 STORY-051 (Pipeline Integration)

- [ ] Clear integration pattern
- [ ] No circular imports
- [ ] RAGWorkflow singleton
- [ ] SSE format matches contract
- [ ] Error codes match standards
- [ ] Timeout at each layer
- [ ] Fallback on max retries
- [ ] traceId propagated
- [ ] LangGraph astream to SSE
- [ ] Termination event always sent
- [ ] Async throughout
- [ ] Unit + integration tests

### 8.3 STORY-053 (Security)

- [ ] JWT_SECRET_KEY from env only
- [ ] Min 32-char validation
- [ ] Old secret rejected
- [ ] bcrypt hashing
- [ ] Password not logged
- [ ] MOCK_USERS gated
- [ ] No hardcoded credentials
- [ ] Email max=255, Password min=8 max=128
- [ ] Login rate limited
- [ ] Token iss/aud claims
- [ ] .env.example updated
- [ ] Fixture-based test config
- [ ] OWASP A02/A03/A07 compliant

---

## 9. ADR Records

### ADR-S04-001: SSE with fetch+ReadableStream

**Status**: Accepted. EventSource only supports GET; chat is POST. Use fetch() + ReadableStream.

### ADR-S04-002: ai_service as Internal Module

**Status**: Proposed. Both Python with overlap. Integrate as internal module for zero overhead.

### ADR-S04-003: JWT Secret via Environment Variables

**Status**: Accepted. Hardcoded secret is OWASP A02:2021. Move to env var, min 32 chars.

---

## Appendix: Priority Order

| Priority | Story | Reason |
|----------|-------|--------|
| **P0** | STORY-053 (Security) | Critical vulnerabilities first |
| **P1** | STORY-051 (Pipeline) | Streaming foundation |
| **P2** | STORY-050 (SSE Frontend) | Depends on backend streaming |

---

*Document generated by TechLead Agent on 2026-01-28*
*Sprint 04 Day 1 Architecture Review*
