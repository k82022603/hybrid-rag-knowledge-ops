# Sprint 03: RAG Pipeline + Frontend

## 스프린트 정보

| 항목 | 값 |
|------|-----|
| **기간** | 2026-02-17 ~ 2026-02-28 (2주) |
| **Velocity (계획)** | 52 pts (신규) + 32 pts (이월) = **84 pts (총)** |
| **Velocity (실제)** | - |
| **Status** | planned |
| **Jira Sprint ID** | 69 |

---

## 스프린트 목표

> **Hybrid RAG 검색 파이프라인 완성 + Frontend 핵심 UI 구현**

핵심 목표:
1. HybridRetriever 구현 (ES + Neo4j + RRF)
2. LangGraph 기반 RAG 워크플로우 구축
3. Frontend 로그인, 대시보드, 검색 UI 완성
4. SSE 스트리밍 응답 구현
5. 초기 데이터 ETL 및 인덱싱

---

## 선행 조건

Sprint 2 완료 항목 (필수):
- [x] 문서 업로드 API (STORY-001) ✅ 2026-01-27
- [x] Docling 문서 파싱 (STORY-002) ✅ 2026-01-27
- [x] Semantic Chunking (STORY-003) ✅ 2026-01-26
- [x] BGE-M3 임베딩 생성 (STORY-004) ✅ 2026-01-27 (Basic 5/5, Integration 7/7)
- [x] **Knowledge Graph 엔티티 추출 (STORY-005)** ✅ 2026-01-28 Done (106/106 테스트)
- [x] **Neo4j/ES 저장 (STORY-006)** ✅ 2026-01-28 Done (84/86 테스트)
- [x] API Gateway 라우팅 (STORY-021) ✅ 2026-01-24
- [x] JWT 인증 필터 (STORY-022) ✅ 2026-01-24
- [x] CI/CD 파이프라인 기초 (STORY-023) ✅ 2026-01-26

---

## 백로그

### Sprint 02 이월 + 선행 조건 (P0, Day 1-3 집중)

| Priority | ID | Jira | 제목 | Points | Assignee | Status | 비고 |
|----------|-----|------|------|--------|----------|--------|------|
| P0 | STORY-005 | SCRUM-35 | KG 엔티티 추출 | 5 | ETL/RAG | **Done** ✅ (106/106 테스트) | 2026-01-28 완료 |
| P0 | STORY-006 | SCRUM-36 | Neo4j/ES 저장 | 5 | ETL/DB | **Done** ✅ (84/86 테스트) | 2026-01-28 완료 |
| P1 | STORY-004 | SCRUM-37 | BGE-M3 Embedding 통합 테스트 | 1 | RAG | **Done** ✅ (Basic 5/5, Integration 7/7) | 2026-01-28 완료 |
| P1 | STORY-046 | SCRUM-38 | Frontend 4페이지 + 11개 개선 (이월) | 8 | Frontend | **Done** ✅ (4페이지 2552줄) | 2026-01-28 완료 |
| P1 | STORY-047 | SCRUM-39 | Backend API 32개 (이월) | 13 | Backend | **Done** ✅ (40+ endpoints) | 2026-01-28 완료 |

### Epic 002: Hybrid RAG Search (34 pts)

| Priority | ID | Jira | 제목 | Points | Assignee | Status |
|----------|-----|------|------|--------|----------|--------|
| P0 | STORY-030 | SCRUM-25 | HybridRetriever 구현 | 8 | MLRag | **Done** ✅ (43/43 테스트) |
| P0 | STORY-031 | SCRUM-26 | RRF Fusion 알고리즘 | 5 | MLRag | **Done** ✅ (55/55 테스트) |
| P0 | STORY-032 | SCRUM-27 | BGE Reranker 통합 | 5 | MLRag | **Done** ✅ (65 테스트) |
| P0 | STORY-033 | SCRUM-28 | LangGraph 워크플로우 | 8 | MLRag | To Do |
| P1 | STORY-044 | SCRUM-33 | Backend Search Service | 5 | Backend | **Done** ✅ (32건 테스트) |
| P1 | STORY-045 | SCRUM-34 | 초기 데이터 ETL | 3 | Data | **Done** ✅ (60건 테스트) |

### Epic 003: Frontend UI/UX (18 pts)

| Priority | ID | Jira | 제목 | Points | Assignee | Status |
|----------|-----|------|------|--------|----------|--------|
| P0 | STORY-040 | SCRUM-29 | Frontend Keycloak 연동 | 5 | Frontend | **Done** ✅ (AC 5/5) |
| P0 | STORY-041 | SCRUM-30 | Dashboard UI | 5 | Frontend | **Done** ✅ (63건 테스트) |
| P0 | STORY-042 | SCRUM-31 | Search UI 컴포넌트 | 5 | Frontend | **Done** ✅ (11파일 1272줄) |
| P1 | STORY-043 | SCRUM-32 | SSE 스트리밍 응답 | 3 | Frontend | To Do |

### Stretch (여유 시 추가)

| ID | 제목 | Points |
|----|------|--------|
| - | 검색 히스토리 저장 | 3 |
| - | 북마크 기능 | 2 |
| - | 다크 모드 지원 | 2 |

---

## 기술 의존성 (사전 준비)

### AI Service
- [x] BGE-M3 모델 다운로드 (~1.5GB) ✅ ~/embedding-test venv, HF cache
- [ ] BGE-reranker-v2-m3 모델 다운로드 (~1GB)
- [ ] DeepSeek API 키 설정

### Frontend
- [x] Keycloak JS Adapter 설치 ✅ (keycloak-js 26.2.2)
- [x] **Tailwind CSS 설치 및 설정** ✅ (3.4.17, MUI 대체, 2026-01-25 결정)
- [x] **Headless UI 설치** ✅ (2.2.9, 접근성 지원 컴포넌트)
- [x] **Heroicons 설치** ✅ (2.2.0, MUI Icons 대체)
- [ ] Zustand 상태관리 설정
- [ ] 마이그레이션 가이드 참조: [MUI to Tailwind](../../knowledge_service/docs/05_development/mui_to_tailwind_migration.md)

### 데이터
- [ ] 초기 문서 수집 (~65개)
- [ ] Elasticsearch 인덱스 매핑
- [ ] Neo4j 제약조건/인덱스

---

## 일일 계획

### Week 1

#### Day 1 (02-17, Mon) — 2026-01-27 실행
- [x] 스프린트 킥오프 미팅 ✅ (스탠드업 완료)
- [x] **STORY-005 착수: KG 엔티티 추출** ✅ (RAG Agent, 테스트 작성 중)
- [x] **STORY-006 착수: Neo4j/ES 저장** ✅ (ETL Agent, 구현 중)
- [x] STORY-030 착수: HybridRetriever 구현 ✅ (RAG Agent, 43/43 테스트 완료)
- [x] STORY-040 착수: Keycloak 연동 ✅ (Frontend Agent, 구현 중)

#### Day 2 (02-18, Tue)
- [ ] **STORY-005 완료: 엔티티 추출 테스트**
- [ ] **STORY-006 계속: 인덱스 매핑 + 저장 로직**
- [ ] STORY-030: Neo4jRetriever 구현
- [ ] STORY-040: 로그인/로그아웃 플로우

#### Day 3 (02-19, Wed)
- [ ] **STORY-006 완료: 통합 테스트**
- [x] STORY-004 통합 테스트 완료 ✅ (Day 1에 조기 완료)
- [ ] STORY-030: Retriever 통합
- [ ] STORY-031 착수: RRF Fusion 알고리즘
- [ ] STORY-041 착수: Dashboard 레이아웃

#### Day 4 (02-20, Thu)
- [ ] STORY-031: 가중치 튜닝
- [ ] STORY-032 착수: BGE Reranker
- [ ] STORY-041: 대시보드 위젯

#### Day 5 (02-21, Fri)
- [ ] STORY-030, 031 완료
- [ ] STORY-032: Reranker 테스트
- [ ] Week 1 리뷰

### Week 2

#### Day 6 (02-24, Mon)
- [ ] STORY-032 완료
- [ ] STORY-033 착수: LangGraph 노드 정의
- [ ] STORY-042 착수: Search UI 컴포넌트

#### Day 7 (02-25, Tue)
- [ ] STORY-033: Planner, Retriever 노드
- [ ] STORY-042: 채팅 모드 UI

#### Day 8 (02-26, Wed)
- [ ] STORY-033: Generator 노드, 워크플로우 연결
- [ ] STORY-043 착수: SSE 스트리밍
- [ ] STORY-044 착수: Backend Search Service

#### Day 9 (02-27, Thu)
- [ ] STORY-033, 044 완료
- [ ] STORY-043 완료
- [ ] STORY-045 착수: 초기 데이터 ETL

#### Day 10 (02-28, Fri)
- [ ] STORY-045 완료
- [ ] 전체 통합 테스트
- [ ] 스프린트 리뷰 & 회고
- [ ] Sprint 4 계획 준비

---

## Definition of Done

각 Story 완료 기준:
- [ ] 모든 Acceptance Criteria 충족
- [ ] 단위 테스트 작성 (커버리지 80%+)
- [ ] 코드 리뷰 완료
- [ ] API 문서 업데이트 (해당 시)
- [ ] 기술 부채 없음

---

## 리스크 및 블로커

| 유형 | 설명 | 영향 | 대응 | 상태 |
|------|------|------|------|------|
| Risk | Reranker 지연시간 | Medium | 캐싱 적용 | Open |
| Risk | LangGraph 학습 곡선 | Medium | 문서/예제 참고 | Open |
| Risk | SSE 브라우저 호환성 | Low | Polyfill | Open |
| Risk | 데이터 품질 | Medium | 검증 스크립트 | Open |

---

## 산출물

### AI Service
```
ai-service/src/
├── retrievers/
│   ├── elasticsearch_retriever.py   # STORY-030
│   ├── neo4j_retriever.py           # STORY-030
│   ├── hybrid_retriever.py          # STORY-030
│   └── rrf_fusion.py                # STORY-031
├── reranking/
│   └── bge_reranker.py              # STORY-032
├── workflows/
│   ├── rag_workflow.py              # STORY-033
│   └── nodes/
│       ├── planner.py
│       ├── retriever.py
│       └── generator.py
└── etl/
    └── initial_data_loader.py       # STORY-045
```

### Backend
```
backend/backend-service/src/main/java/
└── com/hybridrag/
    └── search/
        ├── SearchController.java     # STORY-044
        ├── SearchService.java
        └── dto/
            ├── SearchRequest.java
            └── SearchResponse.java
```

### Frontend
```
frontend/src/
├── features/
│   ├── auth/
│   │   ├── KeycloakProvider.tsx     # STORY-040
│   │   └── useAuth.ts
│   ├── dashboard/
│   │   ├── Dashboard.tsx            # STORY-041
│   │   └── components/
│   └── search/
│       ├── ChatSearch.tsx           # STORY-042
│       ├── KeywordSearch.tsx
│       └── hooks/
│           └── useStreamingSearch.ts # STORY-043
└── shared/
    └── components/
```

### 테스트
```
ai-service/tests/
├── test_hybrid_retriever.py
├── test_rrf_fusion.py
├── test_reranker.py
└── test_rag_workflow.py

frontend/tests/
├── auth.spec.ts
├── dashboard.spec.ts
└── search.spec.ts
```

### 문서
- [ ] API 문서 (OpenAPI/Swagger)
- [ ] LangGraph 워크플로우 다이어그램
- [ ] Frontend 컴포넌트 문서 (Storybook)

---

## 메트릭 목표

| 메트릭 | 목표 | 측정 방법 |
|--------|------|-----------|
| Hybrid Search 응답시간 | < 1초 | pytest-benchmark |
| RAG 응답시간 | < 3초 (P95) | 부하 테스트 |
| Frontend Lighthouse | >= 80 | Lighthouse CI |
| 테스트 커버리지 | >= 80% | pytest-cov, vitest |

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

- [EPIC-002: Hybrid RAG Search](../epics/EPIC-002-hybrid-rag-search.md)
- [EPIC-003: Frontend UI/UX](../epics/EPIC-003-frontend-ui-ux.md)
- [스프린트 실행 계획서](../../docs/02_스프린트_실행_계획서.md)
- [상세 설계서 v2.4](../../knowledge_service/docs/02_design/hybrid_rag_platform_detailed_design.md)
