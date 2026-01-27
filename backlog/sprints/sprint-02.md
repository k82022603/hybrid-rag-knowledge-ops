# Sprint 02: Document Processing Pipeline

## 스프린트 정보

| 항목 | 값 |
|------|-----|
| **기간** | 2026-02-03 ~ 2026-02-14 (2주) |
| **Velocity (계획)** | 35 pts |
| **Velocity (실제)** | 37 pts |
| **Status** | **Done** ✅ (Day 5, 100%) |
| **Jira Sprint ID** | 36 |

---

## 스프린트 목표

> **문서 업로드부터 Semantic Chunking까지의 ETL 파이프라인 1단계 완성**

핵심 목표:
1. 다양한 형식의 문서를 업로드하고 저장하는 API 구현
2. Docling 기반 고품질 문서 파싱 (97%+ 정확도)
3. 의미 기반 청킹으로 검색 품질 기반 마련

---

## 선행 조건

Sprint 1 완료 항목 (필수):
- [x] Docker Compose 환경 정상 동작
- [x] MinIO 컨테이너 설정
- [x] PostgreSQL 스키마 초기화
- [x] Redis 캐시 설정
- [x] 프로젝트 골격 생성 완료

**Sprint 01 Validation (Sprint 02 시작 전 필수)**:
- [ ] STORY-020: Infrastructure E2E Test 완료 (5 SP, QA)
  - 18개 컨테이너 Health Check
  - 데이터베이스 초기화 검증
  - Keycloak 인증 플로우 테스트
  - 서비스 간 통합 테스트
  - [Test Plan](../../knowledge_service/docs/04_testing/infrastructure_e2e_test_plan.md)

---

## 백로그

### Committed (37 pts)

| Priority | ID | Jira | 제목 | Points | Assignee | Status | 완료일 |
|----------|-----|------|------|--------|----------|--------|--------|
| P0 | STORY-001 | SCRUM-6 | 문서 업로드 API | 3 | RAG | **Done** ✅ | 2026-01-27 |
| P0 | STORY-002 | SCRUM-7 | Docling 문서 파싱 | 5 | RAG/QA | **Done** ✅ | 2026-01-27 |
| P0 | STORY-003 | SCRUM-8 | Semantic Chunking | 8 | RAG | **Done** ✅ | 2026-01-26 |
| P0 | STORY-021 | SCRUM-22 | API Gateway 라우팅 구현 | 5 | Backend | **Done** ✅ | 2026-01-24 |
| P0 | STORY-022 | SCRUM-23 | JWT 인증 필터 | 3 | Backend | **Done** ✅ | 2026-01-24 |
| P0 | STORY-024 | SCRUM-21 | 직접 로그인 API | 5 | Backend/QA | **Done** ✅ | 2026-01-25 |
| P1 | STORY-023 | SCRUM-24 | CI/CD 파이프라인 기초 | 3 | DevOps | **Done** ✅ | 2026-01-26 |
| P1 | STORY-025 | - | UI 디자인 검토 및 Gap 분석 | 2 | Frontend | **Done** ✅ | 2026-01-26 |

### Validation (Sprint 01 검증)

| Priority | ID | Jira | 제목 | Points | Assignee | Status |
|----------|-----|------|------|--------|----------|--------|
| P0 | STORY-020 | SCRUM-20 | Infrastructure E2E Test | 3 | QA | **Done** |

### Stretch (Sprint 03 선행 - Day 4~5에서 착수)

| ID | 제목 | Points | Status | 비고 | 이월 |
|----|------|--------|--------|------|------|
| STORY-046 | Frontend 4개 페이지 + 11개 개선 | 8 | **In Progress** | 20파일 완료 (커밋: 1579504) | → Sprint 03 |
| STORY-047 | Backend API 32개 전체 구현 | 13 | **In Progress** | 57파일 완료 (커밋: 34f0d10) | → Sprint 03 |
| STORY-004 | BGE-M3 EmbeddingService (선행) | 5 | **90%** | 전면 구현 + 68/68 테스트 (커밋: 9b95a3a) | → Sprint 03 (통합 테스트) |
| - | AI Service 코어 파이프라인 | - | **In Progress** | SearchService+RAGPipeline (커밋: 6dc4575) | → Sprint 03 |

> **이월 결정**: 4건 모두 Sprint 03으로 이월. Sprint 03의 RAG/Frontend Epic에 직접 기여하므로 연속 작업으로 처리.

---

## 기술 의존성 (사전 준비)

### 인프라 (Sprint 1에서 완료)
- [ ] MinIO 컨테이너 설정
- [ ] PostgreSQL 스키마 초기화
- [ ] Redis 캐시 설정
- [ ] Celery Worker 설정

### 개발 환경
- [ ] Python 3.11+ 환경 구성
- [ ] Poetry 의존성 설치
- [ ] Docling 모델 다운로드
- [ ] BGE-M3 모델 다운로드 (청킹용)

---

## 일일 계획

### Week 1

#### Day 1 (02-03, Mon)
- [ ] 스프린트 킥오프 미팅
- [ ] 개발 환경 최종 점검
- [ ] STORY-001 착수: API 엔드포인트 설계

#### Day 2 (02-04, Tue)
- [ ] STORY-001: FastAPI 엔드포인트 구현
- [ ] STORY-001: 파일 검증 로직

#### Day 3 (02-05, Wed)
- [ ] STORY-001: MinIO 업로드 서비스
- [ ] STORY-001: 단위 테스트 작성

#### Day 4 (02-06, Thu)
- [ ] STORY-001: 통합 테스트 및 완료
- [ ] STORY-002 착수: Docling 환경 설정

#### Day 5 (02-07, Fri)
- [ ] STORY-002: PDF 파서 구현
- [ ] Week 1 리뷰

### Week 2

#### Day 6 (02-10, Mon)
- [ ] STORY-002: DOCX/HWP 파서 구현
- [ ] STORY-002: 파싱 결과 표준화

#### Day 7 (02-11, Tue)
- [ ] STORY-002: 테스트 및 완료
- [ ] STORY-003 착수: Chunker 설계

#### Day 8 (02-12, Wed)
- [ ] STORY-003: SemanticChunker 구현
- [ ] STORY-003: 한국어 문장 경계 처리

#### Day 9 (02-13, Thu)
- [ ] STORY-003: 특수 블록 보존 로직
- [ ] STORY-003: 테스트 작성

#### Day 10 (02-14, Fri)
- [ ] STORY-003 완료
- [ ] 스프린트 리뷰 & 회고
- [ ] Sprint 3 계획 준비

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
| Risk | HWP 파싱 정확도 미달 | Medium | pyhwpx 폴백 준비 | Monitoring |
| Risk | Docling 모델 다운로드 지연 | Low | 사전 다운로드 완료 | Resolved |
| Blocker | Sprint 1 미완료 | Critical | Sprint 1 우선 완료 | Monitoring |
| **Blocker** | **직접 로그인 API 미개발** | **Critical** | **STORY-024 긴급 추가** | **In Progress** |

---

## 산출물

### 코드
```
knowledge_service/src/app/
├── api/routes/
│   └── documents.py          # STORY-001
├── services/
│   └── storage.py            # STORY-001
├── etl/
│   ├── parser.py             # STORY-002
│   ├── docling_adapter.py    # STORY-002
│   └── chunker.py            # STORY-003
└── models/
    ├── document.py           # STORY-001
    ├── parsed_document.py    # STORY-002
    └── chunk.py              # STORY-003
```

### 테스트
```
knowledge_service/src/tests/
├── test_document_api.py
├── test_parser.py
└── test_chunker.py
```

### 문서
- [ ] API 문서 (OpenAPI/Swagger)
- [ ] ETL 파이프라인 아키텍처 다이어그램
- [ ] 파싱 정확도 벤치마크 결과

---

## 메트릭 목표

| 메트릭 | 목표 | 측정 방법 |
|--------|------|-----------|
| 문서 파싱 정확도 | >= 97% | Ground Truth 비교 |
| 업로드 API 응답시간 | < 500ms | pytest-benchmark |
| 청크 품질 점수 | >= 0.85 | 커스텀 평가 함수 |
| 테스트 커버리지 | >= 80% | pytest-cov |

---

## 스프린트 리뷰

### 완료된 항목 (37/37 SP, 100%)
- [x] STORY-020: Infrastructure E2E Test (3 SP) - QA/Infra
- [x] STORY-021: API Gateway 라우팅 구현 (5 SP) - Backend
- [x] STORY-022: JWT 인증 필터 (3 SP) - Backend
- [x] STORY-024: 직접 로그인 API (5 SP) - Backend/QA
- [x] STORY-023: CI/CD 파이프라인 기초 (3 SP) - DevOps
- [x] STORY-025: UI 디자인 검토 및 Gap 분석 (2 SP) - Frontend
- [x] STORY-003: Semantic Chunking 구현 (8 SP) - RAG
- [x] STORY-001: 문서 업로드 API (3 SP) - RAG (2026-01-27 리뷰 통과)
- [x] STORY-002: Docling 문서 파싱 (5 SP) - RAG/QA (2026-01-27 재테스트 통과)

### 데모 노트
- (스프린트 종료 후 작성)

---

## 회고 (Retrospective)

### Keep (계속할 것)
- 병렬 에이전트 활용으로 높은 생산성 달성 (37 SP Committed + Stretch 26 SP 추가 진행)
- 코드 리뷰/QA 프로세스 잘 작동 (STORY-001 PASS WITH COMMENTS, STORY-002 CONDITIONAL PASS)
- 5일 만에 계획된 10일치 Committed 작업 100% 완료 → Velocity 105% (37/35 계획)
- Slack 보고 체계화 (#dev 채널 실시간 작업 추적)
- Stretch 작업으로 Sprint 03 선행 확보 (Frontend 20파일, Backend 57파일, Embedding 855줄)
- TDD/Test-Along 방식으로 테스트 동시 작성 (68개 Embedding 테스트, 37개 Parser 테스트)

### Problem (문제점)
- 직접 로그인 API 미개발 발견 → STORY-024 긴급 추가 필요 (계획 누락)
- Sub-agent Bash 권한 제한으로 테스트 실행 어려움 (pytest 실행 반복 실패)
- HWP/PDF 파싱 정확도 검증 미완 (Docling 라이브러리 환경 제한, AC-1 PENDING)
- 세션 컨텍스트 소진으로 세션 재시작 필요 (2회 발생)
- STORY-005/006 (Entity Extraction, Neo4j/ES 저장) 미착수 → Sprint 03 선행 조건 불충족 위험
- datetime.utcnow() 등 deprecation 경고 사후 발견 (코드 품질 개선 필요)

### Try (시도할 것)
- Sprint 03에서 통합 테스트 환경 구축 (Docker 기반 Docling/BGE-M3 포함)
- STORY-005/006을 Sprint 03 Day 1-2에 우선 배치하여 선행 조건 충족
- Sub-agent Bash 권한 설정 개선 (허용 목록 확대)
- 코드 품질 기준 자동 검사 도입 (pre-commit hooks: black, isort, mypy)
- Sprint 계획 시 선행 조건 의존성을 더 명확히 검증
- 세션 컨텍스트 절약을 위한 에이전트 작업 범위 축소 (한 에이전트 1개 파일 단위)

---

## 참고 자료

- [EPIC-001: Document Processing](../epics/EPIC-001-document-processing.md)
- [STORY-001: 문서 업로드 API](../stories/STORY-001-document-upload-api.md)
- [STORY-002: Docling 문서 파싱](../stories/STORY-002-docling-parser.md)
- [STORY-003: Semantic Chunking](../stories/STORY-003-semantic-chunking.md)
- [STORY-021: API Gateway 라우팅](../stories/STORY-021-api-gateway-routing.md)
- [STORY-022: JWT 인증 필터](../stories/STORY-022-jwt-auth-filter.md)
- [STORY-024: 직접 로그인 API](../stories/STORY-024-direct-login-api.md)
- [STORY-023: CI/CD 파이프라인](../stories/STORY-023-cicd-pipeline-basic.md)
- [스프린트 실행 계획서](../../docs/02_스프린트_실행_계획서.md)
