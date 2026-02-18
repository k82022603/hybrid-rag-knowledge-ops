# Known Issues & Technical Debt Registry

**Project**: Hybrid RAG Knowledge Operations
**Version**: 1.0
**Date**: 2026-02-18
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
- **핵심 차단 요소**: Neo4j 스키마 불일치 — Online은 `(Knowledge)-[:CONTAINS]->(Chunk)`, Batch는 `(Chunk)-[:PART_OF]->(Document)` 구조 사용
- **통합 시 필요**: 기존 169K+ 엔티티의 그래프 마이그레이션 수반
- **리스크 판정**: **HIGH** — 마지막 스프린트에서 진행 시 서비스 장애 위험
- **초기 결정**: 리팩토링 대신 문서화로 대체 (Sprint 12 TechLead 검토 결과)
- **최종 조치 (Sprint 12 마감일)**: 사용자 직접 지시로 스키마 통일 실행
  - 코드 5개 파일 수정: `HAS_ENTITY` → `MENTIONS`, `RELATED` → `RELATED_TO`, `Chunk.chunk_id` → `Chunk.id`
  - DB 마이그레이션 실행: 298K RELATED→RELATED_TO, 13 HAS_ENTITY→MENTIONS, 11 Chunk.id 보정
  - 서비스 중단 없이 25.7초 완료
  - **상태**: ~~문서화로 대체~~ → **해결 완료** (커밋 ebf822b)

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
- **리스크 판정**: **HIGH** — 추상화의 이점 < 리팩토링 비용 + 회귀 버그 위험
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

---

## 3. Deferred Backlog Items

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

## 4. Future Improvement Recommendations

### 4.1 Storage Layer Unification

**Priority**: High
**Effort**: 2-3 weeks

Consolidate the dual storage approach (online `es_storage.py` vs batch direct client) into a unified `StorageClient` interface. This would:
- Eliminate TD-001 and partially address TD-002
- Reduce maintenance overhead by 40-50%
- Enable consistent error handling and retry logic across all data paths

### 4.2 Batch Script CLI Consolidation

**Priority**: Medium
**Effort**: 1-2 weeks

Replace 7+ individual batch scripts with a single CLI tool using Python's `argparse` or `click`:
```
etl_cli.py phase1 --input-dir /data --batch-size 10
etl_cli.py phase2 --gpu --batch-size 64
etl_cli.py phase3 --concurrency 10 --api-key-partition 0
etl_cli.py status  # Show pipeline status across all phases
```

### 4.3 Kubernetes Migration

**Priority**: Low (when scale demands)
**Effort**: 4-6 weeks

Current Docker Compose (18 containers) works well for single-node deployment. Migration path:
```
Docker Compose (current) --> Docker Swarm (medium scale) --> Kubernetes (enterprise scale)
```

K8s reference architecture is already documented in `docs/02_design/technical_assessment/infrastructure_k8s_reference_design.md`.

### 4.4 HWP Parsing Enhancement

**Priority**: Low
**Effort**: 2-3 weeks

Options:
1. Integrate specialized HWP library (e.g., `python-hwp` or `hwp5`)
2. Pre-conversion pipeline: HWP -> DOCX -> Docling
3. OCR fallback for complex HWP layouts

### 4.5 Search Quality Enhancement

**Priority**: Medium
**Effort**: 3-4 weeks

- Complete the Tailwind + Antigravity UI migration for better UX
- Implement search result highlighting (STORY-096)
- Add content viewer modal for full-text chunk inspection (STORY-093)
- Implement document download links via MinIO presigned URLs (STORY-092)

### 4.6 Production GPU Infrastructure

**Priority**: High (for production)
**Effort**: 1-2 weeks

- Deploy BGE-M3 on GPU (T4 or better) for real-time embedding
- Expected latency reduction: 650ms -> 50ms per query
- Estimated cost: ~$0.50/hour (cloud GPU) vs current CPU-only

---

## 5. Project Metrics Summary

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

## 6. Risk Register (Closed)

| ID | Risk | Likelihood | Impact | Mitigation | Final Status |
|----|------|:----------:|:------:|------------|:------------:|
| R-001 | ES Nori plugin not installed | Realized | High | Custom Dockerfile with plugin | Resolved (Sprint 09) |
| R-002 | DeepSeek API rate limiting | Medium | Medium | Dual API key + Circuit Breaker | Mitigated |
| R-003 | CPU embedding too slow | Realized | Medium | GPU offload (Colab Phase 2) | Mitigated |
| R-004 | Neo4j memory pressure | Realized | Medium | Override YML 2GB cap | Resolved |
| R-005 | RAGAS NaN scores | Realized | High | ChatOpenAI(n=1) workaround | Resolved |
| R-006 | HWP parsing quality | Low | Low | DOCX conversion recommended | Accepted |

---

*Hybrid RAG Knowledge Operations | Sprint 12 (Final) | 2026-02-18*

*Author: PM Agent | Reviewed: Claude Code (Opus 4.6)*
