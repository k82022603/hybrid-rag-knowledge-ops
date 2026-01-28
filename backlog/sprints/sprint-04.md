# Sprint 04: Sprint 03 보완 + 품질 강화

## 스프린트 정보

| 항목 | 값 |
|------|-----|
| **기간** | 2026-01-29 ~ (2주) |
| **Velocity (계획)** | 52 pts (13 Stories) |
| **Velocity (실제)** | - |
| **Status** | active |
| **Jira Sprint ID** | - |
| **근거** | [Sprint 03 완료 리뷰](../../work_logs/meetings/2026/01-January/2026-01-28_sprint03_completion_review.md) |

---

## 스프린트 목표

> **Sprint 03에서 발견된 Critical/High 이슈 해결 + 프로덕션 준비도 65% → 85% 달성**

핵심 목표:
1. SSE 프로토콜 수정 (EventSource GET → fetch+ReadableStream POST)
2. RAG 파이프라인 통합 (ai_service ↔ knowledge_service 연결)
3. 보안 강화 (JWT Secret, 입력 검증, 기본 자격증명 제거)
4. 서비스 간 통합/보안 테스트 확립
5. RAGAS 평가 프레임워크 통합

---

## 선행 조건

Sprint 03 완료 항목 (모두 충족):
- [x] HybridRetriever 구현 (STORY-030) ✅
- [x] RRF Fusion 알고리즘 (STORY-031) ✅
- [x] BGE Reranker 통합 (STORY-032) ✅
- [x] LangGraph 워크플로우 (STORY-033) ✅
- [x] Frontend Keycloak 연동 (STORY-040) ✅
- [x] Dashboard UI (STORY-041) ✅
- [x] Search UI 컴포넌트 (STORY-042) ✅
- [x] SSE 스트리밍 응답 (STORY-043) ✅
- [x] Backend Search Service (STORY-044) ✅
- [x] 초기 데이터 ETL (STORY-045) ✅

---

## 백로그

### P0 - Critical (Week 1)

| Priority | ID | Jira | 제목 | Points | Assignee | Status |
|----------|-----|------|------|--------|----------|--------|
| P0 | STORY-050 | SCRUM-40 | SSE 프로토콜 수정 (fetch+ReadableStream 전환) | 5 | Frontend | **In Progress** |
| P0 | STORY-051 | SCRUM-41 | RAG 파이프라인 통합 (ai_service ↔ knowledge_service) | 8 | RAG | **In Progress** |
| P0 | STORY-052 | SCRUM-42 | Reranker async 전환 (asyncio.to_thread) | 2 | RAG | To Do |
| P0 | STORY-053 | SCRUM-43 | 보안 강화 (JWT Secret, 입력 검증, 기본 자격증명 제거) | 3 | Backend | **In Progress** |

**소계**: 18 pts (4 Stories)

### P1 - High (Week 2)

| Priority | ID | Jira | 제목 | Points | Assignee | Status |
|----------|-----|------|------|--------|----------|--------|
| P1 | STORY-054 | SCRUM-44 | 서비스 간 통합 테스트 (Contract Test) | 5 | QA | To Do |
| P1 | STORY-055 | SCRUM-45 | 보안 테스트 (XSS, SQL Injection, Auth) | 3 | QA | To Do |
| P1 | STORY-056 | SCRUM-46 | Frontend ErrorBoundary + 성능 최적화 | 3 | Frontend | To Do |
| P1 | STORY-057 | SCRUM-47 | Generator 대화이력 전달 + 진정한 스트리밍 | 5 | RAG | To Do |
| P1 | STORY-058 | SCRUM-48 | RAGAS 평가 프레임워크 통합 | 5 | RAG | To Do |

**소계**: 21 pts (5 Stories)

### P2 - Medium (Sprint 04+ 또는 Sprint 05)

| Priority | ID | Jira | 제목 | Points | Assignee | Status |
|----------|-----|------|------|--------|----------|--------|
| P2 | STORY-059 | SCRUM-49 | Frontend 테스트 커버리지 확장 (25%→60%) | 5 | Frontend | To Do |
| P2 | STORY-060 | SCRUM-50 | Planner 전략 유효화 + 검색 캐싱 | 3 | RAG | To Do |
| P2 | STORY-061 | SCRUM-51 | 파이프라인 타임아웃 + Circuit Breaker | 3 | RAG | To Do |
| P2 | STORY-062 | SCRUM-52 | 접근성 (WCAG 2.1 AA) 보완 | 2 | Frontend | To Do |

**소계**: 13 pts (4 Stories)

---

## 기술 의존성 (사전 준비)

### SSE 프로토콜 전환
- [ ] `@microsoft/fetch-event-source` 또는 `fetch+ReadableStream` 라이브러리 선정
- [ ] Backend SSE 엔드포인트 POST 지원 확인

### RAG 파이프라인 통합
- [ ] RetrieverNode.retrieve_fn ↔ HybridRetriever.retrieve() 부트스트랩 코드
- [ ] ai_service ↔ knowledge_service HTTP/gRPC 통신 방식 확정
- [ ] LLM Service 어댑터 패턴 설계

### 보안 강화
- [ ] JWT Secret 환경변수 주입 방식 확정 (Docker Secret vs .env)
- [ ] Spring Security 입력 검증 패턴 결정

### RAGAS 통합
- [ ] ragas 패키지 설치 및 호환성 확인
- [ ] Ground truth 데이터셋 준비 (최소 30개 QA 쌍)

---

## 일일 계획

### Week 1 (P0 Critical)

#### Day 1 (완료)
- [x] 스프린트 킥오프 미팅
- [x] STORY-050 착수: SSE 프로토콜 전환 설계 -- SSEPostClient, useStreamingSearch 리팩토링, 72개 테스트, EventSource 제거
- [x] STORY-051 착수: 파이프라인 통합 아키텍처 설계 -- LLMAdapter, KnowledgeServiceClient(이중모드), RetrieverAdapter, RerankerAdapter, bootstrap_rag_pipeline(), 31개 통합 테스트
- [x] STORY-053 착수: JWT Secret 환경변수화 -- JWT Secret 환경변수, InputSanitizer, Bean Validation, 기본 자격증명 환경변수 전환, 30개 보안 테스트

#### Day 2
- [ ] STORY-050: fetch+ReadableStream 구현
- [ ] STORY-051: RetrieverNode ↔ HybridRetriever 연결
- [ ] STORY-052 착수: Reranker asyncio.to_thread 래핑
- [ ] STORY-053: 입력 검증 + 기본 자격증명 제거

#### Day 3
- [ ] STORY-050: useSearchChat 훅 리팩토링
- [ ] STORY-051: LLM Service 어댑터 구현
- [ ] STORY-052 완료: 비동기 성능 검증

#### Day 4
- [ ] STORY-050 완료: 회귀 테스트
- [ ] STORY-051: Planner → Retriever → Generator 연결
- [ ] STORY-053 완료: 보안 설정 검증

#### Day 5
- [ ] STORY-051 완료: E2E 파이프라인 검증
- [ ] Week 1 리뷰
- [ ] P0 4건 완료 확인

### Week 2 (P1 High + P2 Medium)

#### Day 6
- [ ] STORY-054 착수: Backend ↔ AI Service 계약 테스트
- [ ] STORY-056 착수: ErrorBoundary 구현
- [ ] STORY-057 착수: conversation_history 프롬프트 주입

#### Day 7
- [ ] STORY-054: AI Service ↔ Knowledge Service 계약
- [ ] STORY-055 착수: XSS/SQL Injection 테스트
- [ ] STORY-057: 진정한 토큰 스트리밍 구현

#### Day 8
- [ ] STORY-054 완료: SSE 이벤트 포맷 계약
- [ ] STORY-055 완료: Auth 토큰 검증 테스트
- [ ] STORY-056: React.memo + RAF 버퍼링 최적화
- [ ] STORY-058 착수: ragas 패키지 연동

#### Day 9
- [ ] STORY-056 완료: 성능 측정
- [ ] STORY-057 완료: 멀티턴 대화 검증
- [ ] STORY-058: faithfulness/relevancy 메트릭 연동

#### Day 10
- [ ] STORY-058 완료: 평가 보고서 생성
- [ ] P2 Stories 착수/진행 (여유 시)
- [ ] 전체 통합 검증
- [ ] 스프린트 리뷰 & 회고
- [ ] Sprint 05 계획 준비

---

## Definition of Done

각 Story 완료 기준:
- [ ] 모든 Acceptance Criteria 충족
- [ ] 단위 테스트 작성 (커버리지 80%+)
- [ ] 코드 리뷰 완료 (TechLead)
- [ ] 기존 테스트 회귀 없음
- [ ] 문서 업데이트
- [ ] Jira 상태 Done 전환

---

## 리스크 및 블로커

| 유형 | 설명 | 영향 | 대응 | 상태 |
|------|------|------|------|------|
| Risk | SSE 전환 시 기존 UI 회귀 | High | 기존 useSearchChat wrapper 유지 | Open |
| Risk | 파이프라인 통합 시 성능 저하 | High | 벤치마크 테스트 선행 | Open |
| Risk | RAGAS 점수 목표 미달 | Medium | 프롬프트 튜닝 + few-shot 예시 | Open |
| Risk | JWT Secret 노출 | Critical | 환경변수 강제 + Docker 프로파일 수정 | Open |
| Risk | P2 Stories 미완료 시 이월 | Low | Sprint 05로 이월 가능 | Open |

---

## 산출물

### Frontend
```
frontend/src/
├── features/search/
│   └── hooks/
│       └── useStreamingSearch.ts  # STORY-050 (fetch+ReadableStream)
├── shared/
│   └── components/
│       └── ErrorBoundary.tsx      # STORY-056
└── tests/                         # STORY-059
```

### AI Service
```
ai_service/src/
├── services/
│   └── llm_adapter.py            # STORY-051 (LLM Service Adapter)
├── workflows/
│   └── bootstrap.py              # STORY-051 (Pipeline Integration)
├── reranking/
│   └── bge_reranker.py           # STORY-052 (async 전환)
└── evaluation/
    └── ragas_evaluator.py        # STORY-058
```

### Backend
```
backend/backend-service/src/
└── main/java/com/hybridrag/
    ├── config/SecurityConfig.java # STORY-053
    └── search/
        └── dto/SearchRequest.java # STORY-053 (입력 검증)
```

### 테스트
```
tests/
├── contract/
│   ├── test_backend_ai_contract.py    # STORY-054
│   ├── test_ai_knowledge_contract.py  # STORY-054
│   └── test_sse_event_contract.py     # STORY-054
├── security/
│   ├── test_xss_injection.py          # STORY-055
│   ├── test_sql_injection.py          # STORY-055
│   └── test_auth_token.py             # STORY-055
└── evaluation/
    └── ragas_benchmark.py             # STORY-058
```

---

## 메트릭 목표

| 메트릭 | 현재 | 목표 | 측정 방법 |
|--------|------|------|-----------|
| 프로덕션 준비도 | 65% | 85% | 팀 리뷰 |
| 기술 부채 | 16건 | < 8건 | TechLead 추적 |
| 테스트 커버리지 (Frontend) | 25-30% | 60%+ | vitest |
| 보안 취약점 | 2건 (JWT, 입력) | 0건 | 보안 테스트 |
| RAG 파이프라인 통합 | 미연결 | 완전 통합 | E2E 테스트 |
| RAGAS Faithfulness | 미측정 | ≥ 0.7 | ragas |
| RAGAS Relevancy | 미측정 | ≥ 0.7 | ragas |

---

## 스프린트 리뷰

### 완료된 항목
- (스프린트 종료 후 작성)

### 미완료 항목
- (스프린트 종료 후 작성)

### 데모 노트
- (스프린트 종료 후 작성)

---

## 회고 (Retrospective)

### Keep (계속할 것)
-

### Problem (문제점)
-

### Try (시도할 것)
-

---

## 참고 자료

- [Sprint 03 완료 리뷰](../../work_logs/meetings/2026/01-January/2026-01-28_sprint03_completion_review.md)
- [DevOps 파이프라인 점검](../../work_logs/meetings/2026/01-January/2026-01-28_devops_pipeline_audit.md)
- [상세 설계서 v2.4](../../knowledge_service/docs/02_design/hybrid_rag_platform_detailed_design.md)
