# Sprint 03 완료 리뷰 및 보완사항 종합 회의록

**날짜**: 2026-01-28
**참석자**: PM, TechLead, QA Engineer, RAG Engineer, Frontend Developer
**Sprint**: Sprint 03 (RAG Pipeline + Frontend)
**결과**: 15/15 Story Done (84/84pts = 100%)

---

## 1. Sprint 03 완료 현황

### Epic 002: Hybrid RAG Search (34pts - 6/6 Done)

| Story | Points | Tests | Commit |
|-------|--------|-------|--------|
| STORY-030 HybridRetriever | 8 | 43/43 | Wave 1 |
| STORY-031 RRF Fusion | 5 | 55/55 | Wave 2 |
| STORY-032 BGE Reranker | 5 | 65 | Wave 2 |
| STORY-033 LangGraph Workflow | 8 | 79/79 | `62aa40a` |
| STORY-044 Backend Search Service | 5 | 32 | Wave 2 |
| STORY-045 Initial Data ETL | 3 | 60 | Wave 2 |

### Epic 003: Frontend UI/UX (18pts - 4/4 Done)

| Story | Points | Tests | Commit |
|-------|--------|-------|--------|
| STORY-040 Keycloak Auth | 5 | AC 5/5 | Wave 1 |
| STORY-041 Dashboard UI | 5 | 63 | Wave 2 |
| STORY-042 Search UI | 5 | 11파일 1272줄 | Wave 2 |
| STORY-043 SSE Streaming | 3 | 56 | `25633bb` |

### 이월 Stories (32pts - 5/5 Done)

| Story | Points | Tests | Commit |
|-------|--------|-------|--------|
| STORY-005 KG Entity Extraction | 5 | 106/106 | Day 1 |
| STORY-006 Neo4j/ES Storage | 5 | 84/86 | Day 1 |
| STORY-004 BGE-M3 Integration | 1 | 12/12 | Day 1 |
| STORY-046 Frontend 4 Pages | 8 | 2552줄 | Wave 1 |
| STORY-047 Backend API 32+ | 13 | 40+ endpoints | Wave 2 |

---

## 2. 팀원별 분석 결과 요약

### 2.1 TechLead 분석

**분석 범위**: 8개 코드 영역, 5,000+ LOC

**핵심 발견사항**:
- **ARCH-001**: ai_service LangGraph workflow ↔ knowledge_service RAGPipeline 간 통합 코드(glue code) 부재. `RetrieverNode.retrieve_fn`에 `HybridRetriever.retrieve()`를 주입하는 부트스트랩 코드가 없음
- **ARCH-002**: SSE GET 방식에서 conversation_history, topK 등 파라미터 전달 불가
- **GAP-001**: BGE Reranker의 동기 CPU 작업이 async 이벤트루프 블로킹 (CRITICAL)
- **GAP-002/003**: Reranker + HybridRetriever 싱글톤의 thread-safety 미보장
- **SEC-001**: JWT Secret 기본값 하드코딩 (`application.yml:52`, `JwtTokenProvider.java:36`)
- **SEC-002**: SSE 엔드포인트 쿼리 입력 길이 검증 없음
- **ERR-001**: SSE fallback 응답이 JSON 에러를 답변 텍스트로 표시

**기술 부채 재평가**: 16건 → 우선순위 재분류
- P0 (Critical): TECH-DEBT-014 (Reranker 블로킹)
- P1 (High): TECH-DEBT-016 (이중 파이프라인), TECH-DEBT-015 (SSE 불일치), SEC-001 (JWT)
- P2 (Medium): TECH-DEBT-013 (가짜 스트리밍), PERF-002 (Frontend 토큰 복사)

### 2.2 QA Engineer 분석

**분석 범위**: 390+ 기존 테스트, 8개 테스트 파일

**도출된 추가 테스트 필요**: 47 TC

| 분류 | P0 | P1 | P2 | 합계 |
|------|:--:|:--:|:--:|:---:|
| 미테스트 코드경로 | 1 | 12 | 2 | 15 |
| Edge Case/경계값 | 1 | 8 | 2 | 11 |
| 서비스 간 통합 | 3 | 3 | 0 | 6 |
| 성능 | 0 | 3 | 2 | 5 |
| 에러 시나리오 | 1 | 3 | 1 | 5 |
| 보안 (XSS/SQLi/Auth) | 3 | 3 | 0 | 6 |
| **합계** | **9** | **32** | **7** | **47** |

**Top 10 즉시 필요 테스트**:
1. XSS Injection 테스트
2. SQL Injection 테스트
3. SSE Auth Token 필수 검증
4. Backend → AI Service 계약 테스트
5. AI Service → Knowledge Service 계약 테스트
6. SSE 이벤트 포맷 계약 테스트
7. Reranker negative top_k 입력 검증
8. RetrieverNode 문자열 문서 정규화
9. Planner 에러 시 파이프라인 계속 실행 검증
10. RAG Workflow P95 레이턴시 < 3s 검증

### 2.3 RAG Engineer 분석

**분석 범위**: 16개 RAG 관련 파일

**핵심 발견사항**:
1. **이중 파이프라인 미연결**: `RetrieverNode.retrieve_fn`이 테스트에서만 Mock되고 실제 SearchService와 연결 안 됨
2. **Planner 전략 무효**: keyword/semantic/hybrid 결정하나 SearchService는 항상 3가지 모두 실행
3. **Generator 대화이력 미전달**: `conversation_history`가 프롬프트에 포함되지 않아 멀티턴 불가
4. **Validator 자기평가 편향**: 답변 생성 LLM이 동일하게 평가 수행 → 높은 점수 편향
5. **RAGAS 미통합**: 자체 faithfulness/relevance ≠ RAGAS 메트릭 (claim decomposition, embedding similarity)
6. **캐싱 레이어 없음**: 동일 쿼리 매번 재검색/재임베딩
7. **파이프라인 타임아웃 없음**: 노드 hang 시 전체 파이프라인 무한 대기

**우선순위 권고**:
- P0: 이중 파이프라인 통합, Reranker 워크플로우 연결, LLM Service 어댑터
- P1: 진정한 스트리밍, 대화이력 전달, Planner 전략 유효화, RAGAS 통합
- P2: 캐싱, 타임아웃, 프롬프트 버전관리, Circuit Breaker

### 2.4 Frontend Developer 분석

**분석 범위**: 35+ Frontend 소스 파일

**핵심 발견사항**:
1. **SSE 프로토콜 불일치 (CRITICAL)**: `EventSource`(GET only) vs Backend POST → `@microsoft/fetch-event-source` 또는 `fetch+ReadableStream` 전환 필요
2. **ErrorBoundary 없음**: React ErrorBoundary 미구현 → 렌더링 에러 시 흰 화면
3. **토큰 스트리밍 성능**: 매 토큰 `setMessages` 전체 배열 복사 → `useRef` + RAF 버퍼링 필요
4. **MessageBubble 미메모이제이션**: `React.memo` 미적용 → 토큰마다 전체 리렌더링
5. **테스트 커버리지 25-30%**: 16개 unit 중 4개만 테스트
6. **접근성 Gap 7건**: 에러 dismiss aria-label, SourceCitation 키보드, 페이지네이션 등
7. **dark:bg-gray-750 무효**: 비표준 Tailwind 색상 (silent fail)
8. **spinner-lg, btn-primary 미정의**: 커스텀 CSS 클래스 정의 누락

**긍정 평가**: Feature-based 폴더 구조, 일관된 Tailwind 사용, 우수한 다크모드 적용, 강력한 타입 안전성

---

## 3. 종합 판정

### Sprint 03 품질 등급

| 영역 | 등급 | 비고 |
|------|:----:|------|
| AI Service (RAG Pipeline) | **A-** | 아키텍처 우수, 통합 연결 필요 |
| Frontend (Search + SSE) | **B+** | SSE 프로토콜 수정 필요 |
| Backend (API + Gateway) | **B+** | 보안 강화 필요 |
| 테스트 커버리지 | **B** | 390+ tests, 통합테스트 부족 |
| 기술 부채 | **C+** | 16건 (High 3, Medium 9, Low 4) |

### 프로덕션 준비도: **65%** (Sprint 04에서 보완 필요)

---

## 4. Sprint 04 백로그 도출 (Action Items)

### P0 - Critical (Sprint 04 Week 1)

| ID | 제목 | Points | Assignee |
|----|------|--------|----------|
| STORY-050 | SSE 프로토콜 수정 (fetch+ReadableStream 전환) | 5 | Frontend |
| STORY-051 | RAG 파이프라인 통합 (ai_service ↔ knowledge_service 연결) | 8 | RAG |
| STORY-052 | Reranker async 전환 (asyncio.to_thread 래핑) | 2 | RAG |
| STORY-053 | 보안 강화 (JWT Secret, 입력 검증, 기본 자격증명 제거) | 3 | Backend |

### P1 - High (Sprint 04 Week 2)

| ID | 제목 | Points | Assignee |
|----|------|--------|----------|
| STORY-054 | 서비스 간 통합 테스트 (Contract Test) | 5 | QA |
| STORY-055 | 보안 테스트 (XSS, SQL Injection, Auth) | 3 | QA |
| STORY-056 | Frontend ErrorBoundary + 성능 최적화 | 3 | Frontend |
| STORY-057 | Generator 대화이력 전달 + 진정한 스트리밍 | 5 | RAG |
| STORY-058 | RAGAS 평가 프레임워크 통합 | 5 | RAG |

### P2 - Medium (Sprint 04+ 또는 Sprint 05)

| ID | 제목 | Points | Assignee |
|----|------|--------|----------|
| STORY-059 | Frontend 테스트 커버리지 확장 (25%→60%) | 5 | Frontend |
| STORY-060 | Planner 전략 유효화 + 검색 캐싱 | 3 | RAG |
| STORY-061 | 파이프라인 타임아웃 + Circuit Breaker | 3 | RAG |
| STORY-062 | 접근성 (WCAG 2.1 AA) 보완 | 2 | Frontend |

### 합계: 52 Story Points (13 Stories)

---

## 5. 리스크 모니터링

| 리스크 | 확률 | 영향 | 대응 |
|--------|:----:|:----:|------|
| SSE 전환 시 기존 UI 회귀 | Medium | High | 기존 useSearchChat wrapper 유지 |
| 파이프라인 통합 시 성능 저하 | Medium | High | 벤치마크 테스트 선행 |
| RAGAS 점수 목표 미달 | High | Medium | 프롬프트 튜닝 + few-shot 예시 |
| JWT Secret 노출 | Low | Critical | 환경변수 강제 + Docker 프로파일 수정 |

---

## 6. 다음 단계

1. Sprint 04 백로그 확정 (위 13개 Story 기반)
2. DevOps 빌드/배포 파이프라인 점검 결과 반영
3. Sprint 04 킥오프 준비

---

*작성: PM Agent | 2026-01-28*
*참석: TechLead, QA Engineer, RAG Engineer, Frontend Developer*
