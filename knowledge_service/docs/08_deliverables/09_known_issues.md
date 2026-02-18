# Known Issues & Technical Debt Registry

**Project**: Hybrid RAG Knowledge Operations
**Version**: 1.0
**Date**: 2026-02-19
**Sprint**: 12 (Final)
**Status**: Project Closed

---

## 1. Technical Debt

### TD-001: Storage Layer Duplication

| Item | Detail |
|------|--------|
| **Severity** | Medium |
| **Component** | AI Service (knowledge_service) |
| **Description** | Online API uses `es_storage.py` abstraction layer, while batch ETL scripts access Elasticsearch client directly. Two different code paths for the same storage operations. |
| **Impact** | Maintenance burden doubles when ES schema or client API changes. Bug fixes in one path may not propagate to the other. |
| **Root Cause** | Batch scripts were developed independently for performance optimization (3-Phase ETL), bypassing the service layer. |
| **Recommended Fix** | Unify storage operations through a shared `StorageClient` interface that both online and batch paths use. Extract common ES operations into a shared module. |
| **Effort Estimate** | 5 SP |
| **Files Affected** | `src/app/services/es_storage.py`, `scripts/run_etl_*.py`, `scripts/embedding_*.py` |

**TechLead Risk Assessment (Sprint 12)**:
- **변경 규모**: ~180 라인
- **핵심 차단 요소**: Neo4j 스키마 불일치 -- Online은 `(Knowledge)-[:CONTAINS]->(Chunk)`, Batch는 `(Chunk)-[:PART_OF]->(Document)` 구조 사용
- **통합 시 필요**: 기존 169K+ 엔티티의 그래프 마이그레이션 수반
- **리스크 판정**: **HIGH** -- 마지막 스프린트에서 진행 시 서비스 장애 위험
- **초기 결정**: 리팩토링 대신 문서화로 대체 (Sprint 12 TechLead 검토 결과)
- **최종 조치 (Sprint 12 마감일)**: 사용자 직접 지시로 스키마 통일 실행
  - 코드 5개 파일 수정: `HAS_ENTITY` -> `MENTIONS`, `RELATED` -> `RELATED_TO`, `Chunk.chunk_id` -> `Chunk.id`
  - DB 마이그레이션 실행: 298K RELATED->RELATED_TO, 13 HAS_ENTITY->MENTIONS, 11 Chunk.id 보정
  - 서비스 중단 없이 25.7초 완료
  - **상태**: ~~문서화로 대체~~ -> **해결 완료** (커밋 ebf822b)

### TD-002: Pipeline Class Duplication

| Item | Detail |
|------|--------|
| **Severity** | Medium |
| **Component** | AI Service (knowledge_service) |
| **Description** | Two document processing pipeline classes exist: `DocumentProcessingPipeline` (online, single-document) and `InitialDataLoader` (batch, multi-document). Both perform parsing, chunking, and storage but with different interfaces and error handling. |
| **Impact** | Feature additions (e.g., new parser, new chunking strategy) must be implemented twice. Behavior inconsistencies between online and batch processing. |
| **Root Cause** | `InitialDataLoader` was created for bulk initial data loading before the online pipeline was mature. Over time both evolved independently. |
| **Recommended Fix** | Refactor into a single `DocumentPipeline` with configurable batch/single modes. Use strategy pattern for batch-specific optimizations (bulk indexing, parallel processing). |
| **Effort Estimate** | 8 SP |
| **Files Affected** | `src/app/services/document_processing_pipeline.py`, `scripts/initial_data_loader.py` |

**TechLead Risk Assessment (Sprint 12)**:
- **로직 차이**: 두 클래스의 **93%가 상이** (공유 가능한 코드 거의 없음)
- **Online**: 단일 문서, 동기 처리, JWT 인증, 즉시 Neo4j/Entity 생성
- **Batch**: 다중 문서, 비동기 벌크 처리, Phase별 분리, GPU 오프로드 지원
- **BasePipeline 추출 시도**: 추상화 레벨에서 공통점이 적어 오히려 복잡도 증가
- **리스크 판정**: **HIGH** -- 추상화의 이점 < 리팩토링 비용 + 회귀 버그 위험
- **결정**: 리팩토링 대신 문서화로 대체 (Sprint 12 TechLead 검토 결과)

### TD-003: Batch Script Proliferation (7+ Variants)

| Item | Detail |
|------|--------|
| **Severity** | Low |
| **Component** | AI Service scripts |
| **Description** | 7+ similar ETL batch scripts exist with overlapping functionality: `run_etl_full.py`, `run_etl_phase1.py`, `run_etl_phase2_embed.py`, `run_etl_phase3_entity.py`, `run_embedding_batch.py`, `run_entity_extraction.py`, `initial_data_loader.py`, plus monitor scripts. |
| **Impact** | Confusion about which script to use for which scenario. Inconsistent parameter handling across scripts. |
| **Root Cause** | Scripts were created incrementally as the 3-Phase ETL strategy evolved. Each phase got its own script, and earlier monolithic scripts were not removed. |
| **Recommended Fix** | Create a unified `etl_cli.py` with subcommands: `etl_cli.py phase1 --input-dir ...`, `etl_cli.py phase2 --batch-size ...`, `etl_cli.py phase3 --concurrency ...`. Deprecate individual scripts. |
| **Effort Estimate** | 5 SP |
| **Files Affected** | `scripts/run_etl_*.py`, `scripts/run_embedding_*.py`, `scripts/run_entity_*.py` |

### TD-004: InitialDataLoader Monkey-Patching

| Item | Detail |
|------|--------|
| **Severity** | Medium |
| **Component** | AI Service (knowledge_service) |
| **Description** | `InitialDataLoader` uses monkey-patching to override pipeline behavior at runtime, bypassing normal class inheritance and dependency injection patterns. |
| **Impact** | Difficult to test, debug, and maintain. Runtime behavior depends on import order. Can cause subtle bugs when internal APIs change. |
| **Root Cause** | Quick fix to adapt existing pipeline for batch mode without refactoring the class hierarchy. |
| **Recommended Fix** | Replace monkey-patching with proper dependency injection. Use composition over inheritance. Define clear interfaces for pipeline stages. |
| **Effort Estimate** | 5 SP |
| **Files Affected** | `scripts/initial_data_loader.py`, `src/app/services/document_processing_pipeline.py` |

---

## 2. Known Limitations

### KL-001: Small File Upload Rejection

| Item | Detail |
|------|--------|
| **Description** | Files smaller than 100 bytes are rejected by the upload API |
| **Reason** | ChunkQualityGate minimum threshold prevents meaningless documents from entering the pipeline |
| **Workaround** | Combine small files or add contextual content before uploading |
| **Severity** | Low |

### KL-002: Batch ETL Neo4j Sync (Phase 3 Only)

| Item | Detail |
|------|--------|
| **Description** | Knowledge Graph entity extraction in batch ETL only runs during Phase 3 (entity extraction). Online uploads trigger immediate entity extraction, but batch-processed documents require a separate Phase 3 run. |
| **Reason** | 3-Phase ETL design separates CPU-bound parsing (Phase 1), GPU-bound embedding (Phase 2), and API-bound entity extraction (Phase 3) for resource optimization. |
| **Workaround** | Run Phase 3 entity extraction after Phase 1+2 completion: `python scripts/run_etl_phase3_entity.py` |
| **Severity** | Low |

### KL-003: CPU Embedding Speed Limitation

| Item | Detail |
|------|--------|
| **Description** | BGE-M3 embedding on CPU is limited to approximately 0.7 chunks/second (batch_size=4, max_text_length=1000) |
| **Reason** | BGE-M3 model (568M parameters) is compute-intensive. CPU inference is inherently slower than GPU. |
| **Workaround** | Use GPU (Google Colab T4 achieves 65.6 chunks/second, ~94x faster). Phase 2 Colab notebook provided in `scripts/colab/`. |
| **Impact** | Full corpus embedding (56K chunks) takes ~22 hours on CPU vs ~14 minutes on GPU T4 |
| **Severity** | Medium (production should use GPU) |

### KL-004: DeepSeek API Dependency

| Item | Detail |
|------|--------|
| **Description** | Entity extraction (Phase 3) and metadata extraction depend on DeepSeek V3.2 API availability |
| **Reason** | LLM-based extraction requires API calls. Local LLM alternative not implemented. |
| **Impact** | API downtime or rate limiting directly affects entity extraction throughput. DeepSeek n>1 not supported (RAGAS compatibility workaround needed). |
| **Workaround** | Dual API key strategy for rate limit mitigation. Circuit breaker pattern implemented for graceful degradation. |
| **Severity** | Medium |

### KL-005: Hybrid Search Latency on CPU

| Item | Detail |
|------|--------|
| **Description** | Hybrid Search end-to-end latency is ~984ms on CPU, exceeding the 500ms P95 target |
| **Reason** | BGE-M3 query embedding (~650ms) is the bottleneck on CPU |
| **Workaround** | GPU environment reduces embedding to ~50ms, bringing total latency well under 500ms |
| **Severity** | Medium (CPU-only environments) |

### KL-006: Frontend MUI to Tailwind Migration Incomplete

| Item | Detail |
|------|--------|
| **Description** | Frontend still uses MUI components. Planned Tailwind CSS + Antigravity migration was not executed. |
| **Reason** | Project prioritized backend RAG quality (RAGAS A- achievement) over UI migration. |
| **Impact** | Higher bundle size than necessary. Dual styling approach if partially migrated. |
| **Severity** | Low |

### KL-007: HWP Document Parsing Limitations

| Item | Detail |
|------|--------|
| **Description** | HWP (Korean word processor) file parsing has limited fidelity. Complex layouts, embedded objects, and some formatting may not be accurately extracted. |
| **Reason** | Docling HWP parser handles basic text extraction but has limitations with proprietary HWP binary format. |
| **Workaround** | Convert HWP to DOCX or PDF before uploading for better fidelity. |
| **Severity** | Low |

### KL-008: Admin UI vs config.py Dual Configuration

| Item | Detail |
|------|--------|
| **Description** | Admin UI의 System Settings와 AI Service의 config.py/.env가 독립적으로 운영됨. Admin UI에서 변경한 설정이 AI Service에 반영되지 않음. |
| **Reason** | Admin UI는 Spring Boot DB(system_config 테이블)를 변경하고, AI Service는 config.py + 환경변수(.env)를 사용. 두 시스템이 별도 설정 저장소를 사용하여 동기화되지 않음. |
| **Impact** | Admin UI에서 모델/파라미터 변경 시 AI Service에 반영되지 않아 혼란 유발 가능. |
| **Workaround** | AI Service 설정 변경은 `.env` 파일 수정 + 컨테이너 재시작으로 적용. Admin UI의 System Settings는 Spring Boot 서비스 설정에만 영향. |
| **Severity** | Low |

---

## 3. Resolved Issues (2026-02-18 Sprint 12 User Test)

### RI-001: Large PDF Upload Timeout (Resolved)

| Item | Detail |
|------|--------|
| **Severity** | High |
| **Discovered** | 2026-02-18 (Sprint 12 사용자 테스트) |
| **Symptom** | Nike 10-K (140+ pages) PDF 업로드 시 504 Gateway Timeout. 3건 전부 실패 (0/3). |
| **Root Cause** | Frontend axios (120s), Nginx proxy_read_timeout (300s), Docling docling_parse_timeout (300s) 등 타임아웃 체인이 대용량 PDF 처리 시간보다 짧게 설정됨. SEC 공시 서류의 표/차트/이미지에 대한 OCR(RapidOCR) 처리가 300초를 초과. |
| **Resolution** | 전체 타임아웃 체인을 1200초(20분)로 통일 적용 (2026-02-18). Frontend axios, Nginx proxy_send/read_timeout, Docling parse_timeout 6개 설정 변경. kp-frontend, kp-nginx, kp-ai-service 3개 컨테이너 재빌드/재배포. |
| **Remaining Risk** | Spring Cloud Gateway response-timeout (120s)이 미적용 상태. 대용량 문서가 Gateway를 경유할 경우 추가 타임아웃 발생 가능 (Section 4 KI-001 참조). |
| **Verification** | 타임아웃 증가 적용 완료. 대용량 PDF 재테스트는 미수행 (컨테이너 재배포 후 추가 검증 필요). |

### RI-002: Dashboard Quick Search Not Working (Resolved)

| Item | Detail |
|------|--------|
| **Severity** | Medium |
| **Discovered** | 2026-02-18 (Sprint 12 사용자 테스트) |
| **Symptom** | 대시보드에서 "빠른 검색" 입력 후 엔터 -> `/search?q=` 페이지로 이동하지만 검색이 실행되지 않음. 검색 페이지의 입력창이 비어 있고 Chat Search가 자동 실행되지 않음. |
| **Root Cause** | `SearchPage.tsx`에서 URL `?q=` 파라미터를 읽지 않음. `ChatSearch` 컴포넌트에 초기 쿼리를 전달하는 로직이 없음. |
| **Resolution** | 3개 파일 수정 (2026-02-18): `SearchPage.tsx` (useSearchParams로 ?q= 읽기), `ChatSearch.tsx` (initialQuery prop 수신), `useChatSearch.ts` (useEffect로 자동 sendMessage). kp-frontend 재빌드/재배포. |
| **Verification** | 수정 완료 후 배포. 대시보드 -> 검색 페이지 자동 검색 실행 확인. |

### RI-003: Upload Endpoint Authentication Missing (Resolved)

| Item | Detail |
|------|--------|
| **Severity** | High (Security) |
| **Discovered** | 2026-02-18 (업로드 E2E 테스트 케이스 #9) |
| **Symptom** | `/api/v1/documents/upload` 등 13개 엔드포인트에 JWT 인증 없이 접근 가능 |
| **Root Cause** | `documents.py` (7개), `extract.py` (3개), `embed.py` (3개) 라우트에 `Depends(get_current_user)` 누락 |
| **Resolution** | 3개 라우트 파일 전체에 JWT 인증 dependency 추가 (2026-02-18) |
| **Verification** | 인증 없이 요청 시 401 Unauthorized 반환 확인 |

### RI-004: Neo4j Online Upload Not Syncing (Resolved)

| Item | Detail |
|------|--------|
| **Severity** | High |
| **Discovered** | 2026-02-18 (업로드 E2E 테스트) |
| **Symptom** | 실시간 업로드 후 Neo4j에 Document/Chunk 노드 미생성. 엔티티 추출도 온라인에서 미수행. |
| **Root Cause** | 업로드 파이프라인에 Neo4j 기본 노드 생성 로직 없음. 엔티티 추출이 배치 ETL Phase 3에만 존재. |
| **Resolution** | `document_processing_pipeline.py` + `neo4j_storage.py` 수정. 업로드 시 Knowledge/Chunk/CONTAINS 즉시 생성 + 엔티티 추출 온라인 실행 (2026-02-18) |
| **Verification** | 테스트 문서 업로드 -> Neo4j에 Entity + MENTIONS + RELATED_TO 관계 생성 확인 |

### RI-005: Neo4j Schema Unification (Resolved)

| Item | Detail |
|------|--------|
| **Severity** | High |
| **Discovered** | 2026-02-18 (TechLead TD-001 분석) |
| **Symptom** | 검색 코드(search.py)가 참조하는 스키마와 온라인 파이프라인이 생성하는 스키마 불일치. 온라인 업로드 문서의 엔티티가 그래프 검색에서 누락. |
| **Root Cause** | Online: `HAS_ENTITY`, `RELATED_TO`, `Chunk.chunk_id` / Batch: `MENTIONS`, `RELATED`, `Chunk.id` -- 3종 혼재 |
| **Resolution** | 코드 5개 파일 통일 + DB 마이그레이션 (298,636 RELATED_TO + 404,411 MENTIONS). 25.7초, 서비스 중단 없음. (커밋 ebf822b, 2026-02-18) |
| **Verification** | 14건 검색 재검증 전체 PASS. 기존 42,458 chunks 검색 영향 없음. |

---

## 4. Known Issues (Open)

### KI-001: Spring Cloud Gateway Timeout

| Item | Detail |
|------|--------|
| **Severity** | Medium |
| **Component** | API Gateway (Spring Cloud Gateway) |
| **Discovered** | 2026-02-18 (타임아웃 체인 분석) |
| **Description** | API Gateway의 `response-timeout`이 120초로 설정되어 있음. Frontend/Nginx/Docling은 1200초로 통일했으나 Gateway 단은 미적용. |
| **Impact** | 대용량 문서 처리 시 Gateway를 경유하는 API 호출에서 120초 초과 시 504 Gateway Timeout 발생 가능. 현재 AI Service 직접 호출(/api/v1/documents/upload)은 영향 없음. |
| **Root Cause** | Spring Cloud Gateway 빌드가 별도 필요하며, Sprint 12 마감일에 게이트웨이 재빌드 범위에 포함하지 않음. |
| **Recommended Fix** | `application.yml`의 `response-timeout`을 1200s로 변경 + Gateway 컨테이너 재빌드. Resilience4j `ai-service-circuit-breaker` TimeLimiter도 함께 조정. |
| **Workaround** | 대용량 문서 업로드는 Nginx -> AI Service 직접 경로 사용 (Gateway 미경유) |
| **Effort Estimate** | 1 SP |

---

## 5. Deferred Backlog Items

The following stories were planned but not implemented due to project closure at Sprint 12. They are categorized by priority for potential future work.

### High Priority (Recommended for Next Phase)

| Story ID | Title | SP | Reason for Deferral |
|----------|-------|:--:|---------------------|
| STORY-092 | Document download link (MinIO presigned URL) | 5 | Feature enhancement, not critical for core search |
| STORY-096 | RRF Metadata merge + search highlight | 5 | UX improvement, core search functional without it |
| STORY-088 | Neo4j MERGE ON CREATE bug | 2 | Worked around with alternative Cypher patterns |
| STORY-089 | PG-AI Service document sync | 3 | Manual refresh available as workaround |
| STORY-103 | Search API embedding flag | 2 | Nice-to-have indicator for search quality |

### Medium Priority

| Story ID | Title | SP | Reason for Deferral |
|----------|-------|:--:|---------------------|
| STORY-093 | Content Viewer modal | 3 | UX enhancement |
| STORY-094 | Document title extraction | 3 | Files show filename instead of semantic title |
| STORY-095 | camelCase/snake_case residual fixes | 3 | 4 inconsistencies remaining, not blocking |
| STORY-097 | Graph RAG A/B evaluation | 5 | Evaluation framework exists, specific test not run |
| STORY-101 | File type auto-classification | 5 | Manual classification works |
| STORY-104 | Embedding status UX | 2 | Backend data available, UI not implemented |
| STORY-105 | RAGAS evaluation criteria docs | 3 | RAGAS v11 report serves as de facto criteria |

### Low Priority

| Story ID | Title | SP | Reason for Deferral |
|----------|-------|:--:|---------------------|
| STORY-090 | Hybrid Search latency (CPU) | 2 | Expected GPU resolution in production |
| STORY-098 | Admin Redis cache reset | 2 | Manual cache clear available via CLI |
| STORY-102 | WSL memory estimation tool | 3 | Manual memory management documented |
| STORY-106 | Embedding quality comparison test | 3 | RAGAS evaluations cover search quality |
| STORY-107 | Batch healthcheck CI/CD | 3 | Manual monitoring scripts available |
| STORY-109 | docker-compose memory config | 1 | Override file in use |
| STORY-110 | Git credential helper docs | 1 | Issue resolved, docs not written |
| STORY-111 | Cross-system RAGAS evaluation | 3 | Deferred to post-project |

**Total Deferred**: 20 stories, ~58 SP

---

## 6. Future Improvement Recommendations

### 6.1 Storage Layer Unification

**Priority**: High
**Effort**: 2-3 weeks

Consolidate the dual storage approach (online `es_storage.py` vs batch direct client) into a unified `StorageClient` interface. This would:
- Eliminate TD-001 and partially address TD-002
- Reduce maintenance overhead by 40-50%
- Enable consistent error handling and retry logic across all data paths

### 6.2 Batch Script CLI Consolidation

**Priority**: Medium
**Effort**: 1-2 weeks

Replace 7+ individual batch scripts with a single CLI tool using Python's `argparse` or `click`:
```
etl_cli.py phase1 --input-dir /data --batch-size 10
etl_cli.py phase2 --gpu --batch-size 64
etl_cli.py phase3 --concurrency 10 --api-key-partition 0
etl_cli.py status  # Show pipeline status across all phases
```

### 6.3 Kubernetes Migration

**Priority**: Low (when scale demands)
**Effort**: 4-6 weeks

Current Docker Compose (18 containers) works well for single-node deployment. Migration path:
```
Docker Compose (current) --> Docker Swarm (medium scale) --> Kubernetes (enterprise scale)
```

K8s reference architecture is already documented in `docs/02_design/technical_assessment/infrastructure_k8s_reference_design.md`.

### 6.4 HWP Parsing Enhancement

**Priority**: Low
**Effort**: 2-3 weeks

Options:
1. Integrate specialized HWP library (e.g., `python-hwp` or `hwp5`)
2. Pre-conversion pipeline: HWP -> DOCX -> Docling
3. OCR fallback for complex HWP layouts

### 6.5 Search Quality Enhancement

**Priority**: Medium
**Effort**: 3-4 weeks

- Complete the Tailwind + Antigravity UI migration for better UX
- Implement search result highlighting (STORY-096)
- Add content viewer modal for full-text chunk inspection (STORY-093)
- Implement document download links via MinIO presigned URLs (STORY-092)

### 6.6 Production GPU Infrastructure

**Priority**: High (for production)
**Effort**: 1-2 weeks

- Deploy BGE-M3 on GPU (T4 or better) for real-time embedding
- Expected latency reduction: 650ms -> 50ms per query
- Estimated cost: ~$0.50/hour (cloud GPU) vs current CPU-only

### 6.7 Async Upload Pipeline for Large Documents

**Priority**: High
**Effort**: 2-3 weeks

- Implement fully asynchronous upload: upload returns immediately, processing runs in background
- SSE (Server-Sent Events) for real-time progress notification to frontend
- Page-level PDF splitting: parse 50-page segments in parallel for faster throughput
- Would resolve remaining large PDF processing concerns even after timeout increase

---

## 7. Project Metrics Summary

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| RAGAS Grade | A- (v11) | B+ | Exceeded |
| Faithfulness | 0.935 | > 0.90 | Met |
| Context Precision | 0.618 | > 0.50 | Met |
| Context Recall | 0.672 | > 0.60 | Met |
| Test Coverage | 97% | > 80% | Exceeded |
| Documents Processed | 1,437 | 1,000+ | Met |
| Chunks Created | 42,462 | - | - |
| Entity Nodes | 169,886 | - | - |
| Relationships | 775,366 | - | - |
| Sprint Velocity (avg) | ~30 SP | - | - |
| Total Story Points | ~350 SP | - | 12 Sprints |
| Production Readiness | 98% | 95% | Exceeded |

---

## 8. Risk Register (Closed)

| ID | Risk | Likelihood | Impact | Mitigation | Final Status |
|----|------|:----------:|:------:|------------|:------------:|
| R-001 | ES Nori plugin not installed | Realized | High | Custom Dockerfile with plugin | Resolved (Sprint 09) |
| R-002 | DeepSeek API rate limiting | Medium | Medium | Dual API key + Circuit Breaker | Mitigated |
| R-003 | CPU embedding too slow | Realized | Medium | GPU offload (Colab Phase 2) | Mitigated |
| R-004 | Neo4j memory pressure | Realized | Medium | Override YML 2GB cap | Resolved |
| R-005 | RAGAS NaN scores | Realized | High | ChatOpenAI(n=1) workaround | Resolved |
| R-006 | HWP parsing quality | Low | Low | DOCX conversion recommended | Accepted |
| R-007 | Large PDF timeout chain | Realized | High | Timeout unification to 1200s | Mitigated (Gateway pending) |
| R-008 | Neo4j schema inconsistency | Realized | High | Schema unification + migration | Resolved (Sprint 12) |

---

*Hybrid RAG Knowledge Operations | Sprint 12 (Final) | 2026-02-19*

*Author: QA Agent | Reviewed: Claude Code (Opus 4.6)*
