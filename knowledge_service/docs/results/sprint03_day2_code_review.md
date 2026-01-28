# Sprint 03 Day 2 - TechLead Architecture Review & Code Review Report

**Reviewer**: TechLead Agent
**Date**: 2026-01-28
**Sprint**: Sprint 03 Day 2
**Review Type**: Architecture Verification + Pre-Review (4 Stories)

---

## Executive Summary

| 검토 항목 | 상태 | 요약 |
|----------|------|------|
| 기존 코드 아키텍처 검증 | **PASS** | VIP 3단계, 싱글톤, Lazy Init 일관 적용 |
| 설계서-구현 일관성 | **PASS** (일부 갭) | 핵심 아키텍처 일치, VIP Agent 스켈레톤 갭 존재 |
| STORY-031 사전 리뷰 | **Ready** | RRF Fusion 통합 포인트 명확, 위험 낮음 |
| STORY-041 사전 리뷰 | **Ready** | Dashboard UI, 기존 패턴 참조 가능 |
| STORY-044 사전 리뷰 | **Ready** | Backend Search API, Circuit Breaker 패턴 필요 |
| STORY-045 사전 리뷰 | **Ready** | ETL 통합, 기존 파서/청커/임베더 연계 명확 |
| 코드 품질 전반 | **Good** | Docstring/Type hints 우수, 일부 개선점 |

**전체 판정**: 기존 코드베이스는 견고하며, 4개 신규 Story 병행 개발을 안전하게 수용할 수 있는 아키텍처 상태입니다.

---

## 1. 기존 코드 아키텍처 검증

### 1.1 VIP 3단계 아키텍처 준수

| 단계 | 설계서 정의 | 구현 상태 | 일치 여부 |
|------|-----------|----------|----------|
| Stage 1: Value | 엔티티 추출 + Gleaning | entity_extraction.py (완전 구현) + vip_agent.py (스켈레톤) | **부분 일치** |
| Stage 2: Intelligent | Hybrid 검색 + RRF 융합 | search.py + retriever.py (완전 구현) + vip_agent.py (스켈레톤) | **부분 일치** |
| Stage 3: Planning | 답변 합성 | rag_pipeline.py + vip_agent.py (스켈레톤) | **부분 일치** |

**분석**: 각 Stage의 핵심 로직은 서비스 레이어에서 완전히 구현되어 있으나, vip_agent.py의 LangGraph 오케스트레이션은 아직 스켈레톤(TODO) 상태입니다. 이는 설계 의도에 부합하며, 서비스 레이어가 먼저 완성되고 오케스트레이션이 후속으로 통합되는 Bottom-Up 접근 방식입니다.

**VIP Agent 스켈레톤 현황** (vip_agent.py 239줄):
- _extract_entities: TODO - entity_extraction.py의 EntityExtractionService와 연결 필요
- _gleaning: TODO - entity_extraction.py의 Gleaning 로직과 연결 필요
- _hybrid_search: TODO - search.py의 SearchService.hybrid_search()와 연결 필요
- _rrf_fusion: TODO - search.py의 SearchService._rrf_fusion()과 연결 필요
- _synthesize_answer: TODO - rag_pipeline.py의 RagPipeline.process_query()와 연결 필요

> **권고 (TECH-DEBT-005)**: VIP Agent 오케스트레이션 통합은 Sprint 04에서 우선적으로 수행하되, 현재 각 서비스 레이어의 단위 테스트가 완전하므로 병렬 개발에 영향 없음.

### 1.2 싱글톤 패턴 일관성

| 모듈 | get_xxx() | reset_xxx() | Lazy Init | 일관성 |
|------|:---------:|:-----------:|:---------:|:------:|
| SearchService | OK | - | OK | OK (reset 미구현) |
| HybridRetriever | OK | OK | OK | OK |
| EmbeddingService | OK | OK | OK | OK |
| EntityExtractionService | OK | OK | OK | OK |
| Neo4jStorageService | OK | OK | OK | OK |
| ElasticsearchStorageService | OK | OK | OK | OK |
| DocumentParser | OK | - | OK | OK (reset 미구현) |
| VIPAgent | OK | - | OK | OK (reset 미구현) |
| RagPipeline | OK | - | OK | OK (reset 미구현) |

> **권고 (TECH-DEBT-006)**: 모든 싱글톤 팩토리에 reset_xxx() 함수 표준화. 테스트 시 인스턴스 초기화가 필요한 모듈에서 누락 방지.

### 1.3 의존성 방향 검증

의존성 방향이 올바릅니다 (외부 -> 내부). 순환 의존이 없으며, retriever.py가 SearchService를 지연 import하여 순환 참조를 방지.

### 1.4 비동기 처리 패턴

| 패턴 | 적용 상태 | 비고 |
|------|----------|------|
| asyncio.gather(return_exceptions=True) | OK | SearchService, HybridRetriever 모두 적용 |
| Graceful Degradation | OK | 부분 검색 실패 시 나머지 결과로 계속 |
| run_in_executor | OK | EmbeddingService의 동기 모델 호출을 비동기로 래핑 |
| Compensating Transaction | OK | StorageTransaction의 Neo4j/ES 롤백 패턴 |

### 1.5 에러 계층 구조

에러 계층이 체계적으로 설계되었습니다. KnowledgeServiceError를 루트로 LLMError(502), SearchError(500)+ElasticsearchError+Neo4jError, DataError(400)+ValidationError+DocumentNotFoundError(404), EmbeddingError(500), ConfigurationError(500), AuthenticationError(401)+InvalidCredentialsError+TokenExpiredError+InvalidTokenError, AuthorizationError(403) 등의 도메인별 분리가 적절합니다.

---

## 2. 설계서-구현 일관성 검증

### 2.1 데이터 모델 일치

| 설계서 항목 | 구현 상태 | 일치 |
|-----------|----------|:----:|
| PostgreSQL SSOT | models/document.py Pydantic 모델 | OK |
| Neo4j Knowledge Graph | neo4j_storage.py MERGE+UNWIND | OK |
| ES Vector Index (1024-dim) | es_storage.py kNN mapping | OK |
| BGE-M3 1024차원 Dense+Sparse | embedding.py EmbeddingService | OK |
| RRF k=60 | search.py _rrf_fusion() + config.py settings.rrf_k | OK |
| Nori Korean Analyzer | es_storage.py korean_analyzer 매핑 | OK |

### 2.2 API 설계 일치

| 설계서 API | 구현 파일 | 상태 |
|-----------|----------|:----:|
| /api/v1/search/hybrid | api/routes/search.py | OK |
| /api/v1/search/semantic | api/routes/search.py | OK |
| /api/v1/search/keyword | api/routes/search.py | OK |
| /api/v1/search/chat | api/routes/search.py | OK |
| /api/v1/search/chat/stream | api/routes/search.py (SSE) | OK |
| /api/v1/documents/upload | api/routes/documents.py | OK |
| /api/v1/documents/{id} | api/routes/documents.py | OK |
| /api/v1/documents/{id}/status | api/routes/documents.py | OK |

### 2.3 아키텍처 갭 (설계 vs 구현)

| # | 설계서 명세 | 구현 상태 | 심각도 | 조치 |
|---|-----------|----------|:------:|------|
| 1 | VIP LangGraph 오케스트레이션 | 스켈레톤 (TODO) | Medium | Sprint 04 통합 |
| 2 | PostgreSQL SSOT 연동 | 인메모리 임시 저장소 | Medium | Sprint 04 DB 연동 |
| 3 | Redis 캐시 레이어 | EmbeddingCache만 구현 | Low | 점진적 확대 |
| 4 | Keycloak JWT 검증 (AI Service) | Frontend만 구현 | Medium | STORY-044에서 처리 |

---

## 3. 신규 Story 사전 리뷰 (Pre-Review)

### 3.1 STORY-031: RRF Fusion 통합

| 기존 코드 | 통합 방법 | 위험도 |
|----------|----------|:------:|
| SearchService._rrf_fusion() (L585-645) | RRF 로직 이미 완전 구현됨 | Low |
| HybridRetriever.retrieve() (L291-357) | SearchService 위임 구조 | Low |
| HybridRetriever._fallback_retrieve() (L424-493) | settings.rrf_k로 튜닝 가능 | Low |

**아키텍처 적합성**: **A (Excellent)** - RRF 알고리즘 score=sum(1/(k+rank)) 이미 정확히 구현됨. 소스별 가중치, Score Normalization, 임계치 필터링 추가 가능.

**권고 체크리스트**:
- [ ] _rrf_fusion() 시그니처에 weights 파라미터 추가 시 기존 호출 사이트(2곳) 하위 호환성 유지
- [ ] settings 클래스에 rrf_weights 설정 추가
- [ ] 기존 43개 HybridRetriever 테스트 회귀 없음 확인

### 3.2 STORY-041: Dashboard UI (Tailwind CSS)

| 기존 코드 | 통합 방법 | 위험도 |
|----------|----------|:------:|
| api/routes/search.py | Search API 이미 완비 | Low |
| api/routes/documents.py | Document CRUD/Upload API 이미 완비 | Low |
| Frontend Keycloak (STORY-040) | 인증 Provider 재사용 | Low |

**아키텍처 적합성**: **A (Excellent)** - Backend API 완전 구현됨, Frontend는 순수 UI 구현에 집중 가능.

**권고 체크리스트**:
- [ ] Tailwind CSS 유틸리티 클래스 일관성 (기존 STORY-040 LoginPage 패턴 참조)
- [ ] React.memo / useMemo / useCallback 패턴 적용
- [ ] SearchResponse 타입을 TypeScript 인터페이스로 정확히 매핑
- [ ] 접근성: ARIA 라벨, 키보드 네비게이션, WCAG AA
- [ ] 에러 바운더리 컴포넌트 적용

### 3.3 STORY-044: Backend Search API + Circuit Breaker

| 기존 코드 | 통합 방법 | 위험도 |
|----------|----------|:------:|
| SearchService.hybrid_search() (L175-303) | asyncio.gather(return_exceptions=True)로 부분 실패 허용 | Low |
| SearchService.semantic_search() (L305-393) | ES 클라이언트 None 체크 존재 | Low |
| SearchService._graph_search() (L507-583) | Neo4j 드라이버 None 체크 존재 | Low |
| ElasticsearchError / Neo4jError | 적절한 에러 코드 매핑 필요 | Medium |

**아키텍처 적합성**: **B+ (Good with considerations)** - Graceful Degradation 적용됨, 명시적 Circuit Breaker 미적용.

**추가 필요 항목**:
1. Circuit Breaker 구현 (aiobreaker 또는 자체 구현)
2. ES/Neo4j 명시적 timeout 설정 (ES: 5s, Neo4j: 3s, 전체: 10s 제안)
3. Health Check 통합 (StorageTransaction.health_check() 패턴 참조)
4. Rate Limiting (FastAPI middleware)

**권고 체크리스트**:
- [ ] Circuit Breaker 상태(CLOSED/OPEN/HALF_OPEN) 전이 로직 구현
- [ ] 연속 실패 임계치, 복구 대기 시간 설정값 config.py에 추가
- [ ] Circuit Breaker 상태를 health_check 응답에 포함
- [ ] 기존 return_exceptions=True 패턴과 Circuit Breaker의 역할 분리 명확화

### 3.4 STORY-045: ETL 통합

| 기존 코드 | 통합 방법 | 위험도 |
|----------|----------|:------:|
| DocumentParser (parser.py, 710줄) | PDF/DOCX/HWP/MD/TXT/HTML 파싱 완비 | Low |
| SemanticChunker (chunker.py, 681줄) | 문장 경계 + 특수 블록 보존 청킹 완비 | Low |
| EmbeddingService (embedding.py, 855줄) | Dense/Sparse 임베딩 + Redis 캐시 완비 | Low |
| EntityExtractionService | Gleaning 포함 엔티티 추출 완비 | Low |
| StorageTransaction (transaction.py, 471줄) | Neo4j+ES 원자적 저장 + 롤백 완비 | Low |

**아키텍처 적합성**: **A (Excellent)** - 각 구성 요소 완전 구현됨. STORY-045는 오케스트레이션 통합 레이어 구현에 집중.

**ETL 파이프라인 플로우**: DocumentParser.parse() -> SemanticChunker.chunk_document() -> EmbeddingService.embed_chunks() -> EntityExtractionService.extract_entities() -> StorageTransaction.save_document()

**권고 체크리스트**:
- [ ] ETL 파이프라인 오케스트레이터 클래스 (etl/pipeline.py) 신규 생성
- [ ] 비동기 처리: aembed_batch() 활용
- [ ] 진행률 추적: DocumentStatusResponse.progress_percent 업데이트
- [ ] 실패 복구: StorageTransaction._rollback() 활용
- [ ] 배치 처리: 대용량 문서의 청크를 배치 단위로 임베딩/저장

---

## 4. 코드 품질 분석

### 4.1 Docstring 품질

| 모듈 | 클래스 | 메서드 | Args/Returns | 평가 |
|------|:-----:|:------:|:------------:|:----:|
| search.py (770줄) | OK | OK | OK | **A** |
| retriever.py (555줄) | OK | OK | OK | **A** |
| embedding.py (855줄) | OK | OK | OK | **A** |
| entity_extraction.py | OK | OK | OK | **A** |
| neo4j_storage.py (938줄) | OK | OK | OK | **A** |
| es_storage.py (799줄) | OK | OK | OK | **A** |
| transaction.py (471줄) | OK | OK | OK | **A** |
| parser.py (710줄) | OK | OK | OK | **A** |
| chunker.py (681줄) | OK | OK | OK | **A** |
| vip_agent.py (239줄) | OK | OK | 일부 미흡 | **B+** |

**전체 평가**: Docstring 품질이 **매우 우수**합니다. Google style docstring 일관 적용.

### 4.2 Type Hints

전 모듈에 Type hints가 **전수 적용**되어 있습니다. Optional, Union, Tuple, Dict, List 등 적절한 제네릭 활용. **전체 등급: A**

### 4.3 에러 핸들링 패턴

| 패턴 | 적용 현황 | 평가 |
|------|----------|:----:|
| Domain-specific exceptions | 모든 서비스에서 적절한 도메인 예외 사용 | **A** |
| Graceful degradation | SearchService, HybridRetriever | **A** |
| Compensating transaction | StorageTransaction Neo4j/ES 롤백 | **A** |
| Retry with backoff | DocumentParser max_retries + 지수 대기 | **A** |
| None-safe access | ES/Neo4j 클라이언트 None 체크 일관 | **A** |
| 로깅 연동 | 모든 except 블록에서 logging | **A** |

### 4.4 코드 중복 분석

| 중복 패턴 | 위치 | 심각도 | 권고 |
|----------|------|:------:|------|
| 싱글톤 팩토리 반복 | 모든 서비스 | **Low** | 수용 가능 |
| SearchResult 모델 이중 정의 | agents/state.py vs api/routes/search.py | **Medium** | 통합 검토 필요 |
| f-string 로깅 | search.py, parser.py, chunker.py 등 | **Low** | %s 포맷 권장 |

> **권고 (TECH-DEBT-007)**: SearchResult 모델이 TypedDict 기반과 Pydantic BaseModel 기반으로 이중 정의됨. 변환 유틸리티 추가 권장.

### 4.5 네이밍 일관성

파일명(snake_case), 클래스명(PascalCase), 함수/변수명(snake_case), 상수명(UPPER_SNAKE_CASE), 비공개 메서드(_prefix) 모두 **일관 적용**. **등급: A**

### 4.6 보안 검토

| 항목 | 상태 | 비고 |
|------|:----:|------|
| API 키 하드코딩 | OK | 환경변수 사용 |
| Cypher Injection | OK | 파라미터화 쿼리 |
| XSS 방지 | OK | FastAPI JSON 직렬화 + React JSX |
| 파일 업로드 검증 | OK | 확장자 화이트리스트 + sanitize |
| TLS/SSL | **Warning** | es_storage.py verify_certs=False |
| 인증 토큰 | **Warning** | AI Service JWT 검증 미구현 |

---

## 5. 기술 부채 현황 (누적)

### 5.1 기존 기술 부채 (Day 1)

| ID | Story | 내용 | 우선순위 | 상태 |
|----|-------|------|:--------:|:----:|
| TECH-DEBT-001 | STORY-006 | _save_entities_by_label 전략 패턴 리팩토링 | Medium | Open |
| TECH-DEBT-002 | STORY-006 | query_subgraph depth 파라미터화 쿼리 전환 | Medium | Open |
| TECH-DEBT-003 | STORY-040 | Keycloak 토큰 확장 인터페이스 정의 | Medium | Open |
| TECH-DEBT-004 | STORY-040 | 테스트 계정 정보 환경 변수 분리 | Medium | Open |

### 5.2 신규 기술 부채 (Day 2 발견)

| ID | 발견 위치 | 내용 | 우선순위 | 조치 시점 |
|----|----------|------|:--------:|----------|
| TECH-DEBT-005 | vip_agent.py | VIP Agent 오케스트레이션 통합 필요 | **High** | Sprint 04 |
| TECH-DEBT-006 | 여러 서비스 | reset_xxx() 미구현 4건 | Low | Sprint 04 |
| TECH-DEBT-007 | agents/state.py, api/routes/search.py | SearchResult 모델 이중 정의 | Medium | Sprint 04 |
| TECH-DEBT-008 | search.py L124 | SearchHistoryStore 인메모리 -> PostgreSQL | Medium | Sprint 04 |
| TECH-DEBT-009 | 전반 | f-string 로깅 -> %s 포맷 전환 | Low | 지속 개선 |

### 5.3 기술 부채 추이

Sprint 03 Day 1: 4건 (TECH-DEBT-001~004), Day 2: +5건 (TECH-DEBT-005~009), **누적 총계: 9건** (High: 1, Medium: 5, Low: 3)

---

## 6. Story별 아키텍처 적합성 종합

| Story | 아키텍처 적합성 | 기존 코드 영향도 | 통합 위험도 | 판정 |
|-------|:-----------:|:-------------:|:----------:|:----:|
| STORY-031 (RRF Fusion) | **A** | Low | Low | **Ready** |
| STORY-041 (Dashboard UI) | **A** | None | Low | **Ready** |
| STORY-044 (Backend Search) | **B+** | Medium | Medium | **Ready with caution** |
| STORY-045 (ETL Integration) | **A** | Low | Low | **Ready** |

---

## 7. 권고사항 종합

### 7.1 즉시 조치 (Blocking)

없음. 기존 코드베이스에 블로킹 이슈 없습니다.

### 7.2 구현 시 주의사항 (Non-blocking)

| # | 대상 Story | 권고 내용 | 중요도 |
|---|-----------|----------|:------:|
| 1 | STORY-031 | _rrf_fusion() 시그니처 변경 시 호출 사이트 2곳 하위 호환성 유지 | Medium |
| 2 | STORY-044 | Circuit Breaker는 기존 return_exceptions=True와 보완 관계로 설계 | Medium |
| 3 | STORY-044 | ES/Neo4j 명시적 timeout 설정 추가 | Medium |
| 4 | STORY-045 | ETL 오케스트레이터에서 aembed_batch() 사용 | Medium |
| 5 | STORY-045 | save_document() 호출 전 청크에 document_id 보장 | Low |
| 6 | STORY-041 | SearchResult API 모델과 내부 모델 매핑 확인 | Low |
| 7 | 전체 | 신규 서비스에 get_xxx()/reset_xxx() 싱글톤 패턴 준수 | Low |

### 7.3 향후 아키텍처 개선 (Sprint 04)

| 우선순위 | 내용 | 영향 범위 |
|:--------:|------|----------|
| **P0** | VIP Agent 오케스트레이션 통합 | 전체 RAG 파이프라인 |
| **P1** | PostgreSQL SSOT 연동 | Document CRUD, ETL |
| **P1** | Circuit Breaker 패턴 도입 | Search API 안정성 |
| **P2** | SearchResult 모델 통합 | API/서비스 레이어 |
| **P2** | reset_xxx() 표준화 | 테스트 인프라 |
| **P3** | f-string 로깅 전환 | 전체 |

---

## 8. 결론

Sprint 03 Day 2 기준, 기존 코드베이스는 **견고한 아키텍처**와 **높은 코드 품질**을 유지하고 있습니다.

**핵심 강점**:
- VIP 3단계 아키텍처의 서비스 레이어가 완전히 구현됨
- 싱글톤 + Lazy Init 패턴이 전체 코드베이스에 일관 적용
- 에러 계층과 Graceful Degradation이 체계적
- 보상 트랜잭션 패턴으로 분산 저장소 일관성 보장
- Docstring, Type hints, 네이밍 규칙이 매우 우수

**주의 영역**:
- VIP Agent 스켈레톤을 Sprint 04에서 반드시 통합해야 함
- STORY-044의 Circuit Breaker는 기존 패턴과 보완 관계로 설계 필요
- 기술 부채 9건 누적 중, High 1건 관리 필요

4개 신규 Story 모두 **병행 개발 가능** 판정이며, 기존 아키텍처와의 충돌 위험은 낮습니다.

---

*Reviewed by TechLead Agent | 2026-01-28*
*Architecture Verification + Pre-Review for Sprint 03 Day 2*
