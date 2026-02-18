# Sprint 01: Infrastructure Setup

## 스프린트 정보

| 항목 | 값 |
|------|-----|
| **기간** | 2026-01-20 ~ 2026-01-31 (2주) |
| **Velocity (계획)** | 21 pts |
| **Velocity (실제)** | 21 pts (100%) |
| **Status** | **completed** |
| **Completed Date** | 2026-01-20 (Day 1!) |
| **Jira Sprint ID** | 3 |

---

## 스프린트 목표

> **Docker Compose 기반 개발 환경 구축 및 프로젝트 골격 생성**

핵심 목표:
1. 18개 컨테이너 환경 구축 (docker-compose up 단일 명령)
2. 데이터베이스 스키마 자동 초기화 (PostgreSQL, ES, Neo4j)
3. Keycloak 인증 인프라 설정
4. 각 서비스 프로젝트 골격 생성 및 빌드 가능 상태

---

## 백로그

### Committed (21 pts) - ALL COMPLETED!

| Priority | ID | Jira | 제목 | Points | Assignee | Status |
|----------|-----|------|------|--------|----------|--------|
| P0 | STORY-010 | SCRUM-10 | Docker Compose 환경 구성 | 5 | Infra | **Done** |
| P0 | STORY-011 | SCRUM-11 | 데이터베이스 초기화 | 3 | Data | **Done** |
| P0 | STORY-012 | SCRUM-12 | 인증 인프라 (Keycloak) | 5 | Backend | **Done** |
| P0 | STORY-013 | SCRUM-13 | 프로젝트 골격 생성 | 5 | Backend, Frontend, MLRag | **Done** |
| P1 | STORY-014 | SCRUM-14 | 개발 환경 가이드 | 3 | TechLead | **Done** |

### Stretch (여유 시 추가)

| ID | 제목 | Points |
|----|------|--------|
| - | Observability 기본 설정 (Prometheus, Grafana) | 3 |
| - | CI/CD 파이프라인 초기 구성 | 2 |

---

## 기술 의존성 (사전 준비)

### 환경 요구사항
- [x] Docker Desktop 설치
- [x] Docker Compose v2 설치
- [ ] 최소 16GB RAM (권장 32GB)
- [ ] 50GB 디스크 공간

### 환경 변수 (.env 파일)
```bash
POSTGRES_PASSWORD=
KEYCLOAK_ADMIN_PASSWORD=
KEYCLOAK_DB_PASSWORD=
NEO4J_PASSWORD=
MINIO_ROOT_USER=
MINIO_ROOT_PASSWORD=
GRAFANA_PASSWORD=
DEEPSEEK_API_KEY=
```

---

## 일일 계획

### Week 1

#### Day 1 (01-20, Mon)
- [x] 스프린트 킥오프
- [x] STORY-010 완료: docker-compose.yml 18개 컨테이너 구성
- [x] STORY-011, 012, 013 착수

#### Day 2 (01-21, Tue)
- [ ] STORY-010: Data Layer 컨테이너 설정
- [ ] STORY-010: Observability Layer 설정

#### Day 3 (01-22, Wed)
- [ ] STORY-010: 네트워크 및 볼륨 설정, .env.example
- [ ] STORY-010 완료
- [ ] STORY-011 착수: PostgreSQL 초기화

#### Day 4 (01-23, Thu)
- [ ] STORY-011: Elasticsearch 인덱스 생성
- [ ] STORY-011: Neo4j 제약조건 생성

#### Day 5 (01-24, Fri)
- [ ] STORY-011 완료
- [ ] STORY-012 착수: Keycloak Realm 설정
- [ ] Week 1 리뷰

### Week 2

#### Day 6 (01-27, Mon)
- [ ] STORY-012: Client 설정, 역할 정의
- [ ] STORY-012: 초기 사용자 생성

#### Day 7 (01-28, Tue)
- [ ] STORY-012 완료
- [ ] STORY-013 착수: Backend/API Gateway 초기화

#### Day 8 (01-29, Wed)
- [ ] STORY-013: Frontend/AI Service 초기화
- [ ] STORY-013: 공통 설정

#### Day 9 (01-30, Thu)
- [ ] STORY-013 완료
- [ ] STORY-014: README 및 가이드 작성

#### Day 10 (01-31, Fri)
- [ ] STORY-014 완료
- [ ] 전체 통합 테스트
- [ ] 스프린트 리뷰 & 회고
- [ ] Sprint 2 계획 준비

---

## Definition of Done

각 Story 완료 기준:
- [ ] 모든 Acceptance Criteria 충족
- [ ] 단위 테스트 작성 (해당 시)
- [ ] 코드 리뷰 완료
- [ ] 문서 업데이트
- [ ] 기술 부채 없음

---

## 리스크 및 블로커

| 유형 | 설명 | 영향 | 대응 | 상태 |
|------|------|------|------|------|
| Risk | 메모리 부족 | High | Observability 선택적 기동 | Monitoring |
| Risk | 포트 충돌 | Medium | .env 포트 커스터마이징 | Open |
| Risk | Keycloak 초기 설정 복잡 | Medium | 자동화 스크립트 | Open |

---

## 산출물

### 코드/설정
```
infrastructure/
├── docker-compose.yml
├── docker-compose.override.yml
├── .env.example
├── nginx/nginx.conf
├── init-db/
│   ├── 01-init-postgres.sql
│   ├── 02-init-elasticsearch.sh
│   └── 03-init-neo4j.cypher
├── keycloak/realm-export.json
└── prometheus/prometheus.yml
```

### 프로젝트 골격
```
backend/
├── api-gateway/
└── backend-service/
frontend/
ai-service/
```

### 문서
- [ ] README.md 업데이트
- [ ] docs/development/local-setup.md
- [ ] docs/development/ide-setup.md

---

## 메트릭 목표

| 메트릭 | 목표 | 측정 방법 |
|--------|------|-----------|
| 컨테이너 기동 | 18개 healthy | docker-compose ps |
| Keycloak 로그인 | 성공 | 수동 테스트 |
| 프로젝트 빌드 | 모두 성공 | 빌드 스크립트 |
| 문서 완성도 | 100% | 체크리스트 |

---

## 스프린트 리뷰

### 완료된 항목 (5/5 Stories, 21/21 SP)
1. **SCRUM-10**: Docker Compose 18개 컨테이너 환경 구성
2. **SCRUM-11**: PostgreSQL, Elasticsearch, Neo4j 초기화 스크립트
3. **SCRUM-12**: Keycloak SSO + OAuth2 인증 인프라
4. **SCRUM-13**: Backend, Frontend, AI Service 프로젝트 스켈레톤
5. **SCRUM-14**: 개발 환경 가이드 3종 완성

### 미완료 항목
- 없음 (100% 완료!)

### 데모 노트
- Day 1에 전체 Sprint 완료 (10일 계획 대비 1일 완료)
- 6개 Agent 병렬 작업으로 효율 극대화
- 인프라 레이어 완전 구축 (docker-compose up 단일 명령으로 18개 서비스 기동)

---

## 회고 (Retrospective)

### Keep (계속할 것)
- Agent 병렬 작업 체계 유지
- Jira/Slack 자동 연동으로 투명한 진행 상황 공유
- Story별 명확한 Acceptance Criteria 정의

### Problem (문제점)
- 없음 (완벽한 Sprint 실행)

### Try (시도할 것)
- Sprint 02에서 더 복잡한 비즈니스 로직 구현 도전
- 테스트 커버리지 80% 이상 달성

---

## Post-Sprint Validation (Sprint 02 시작 전 필수)

### Infrastructure E2E Test

Sprint 01 인프라 산출물의 품질 검증을 위한 관통 테스트입니다.

| Priority | ID | Jira | 제목 | Points | Assignee | Status |
|----------|-----|------|------|--------|----------|--------|
| P0 | STORY-020 | SCRUM-20 | Infrastructure E2E Test | 5 | QA | **Done** |

**테스트 범위**:
- 18개 컨테이너 Health Check
- 데이터베이스 초기화 검증 (PostgreSQL, ES, Neo4j)
- Keycloak 인증 플로우 테스트
- 서비스 간 통합 테스트
- Observability 스택 검증

**일정**: 2026-01-21 ~ 2026-01-27 (5.5일)

**관련 문서**:
- [Infrastructure E2E Test Plan](../../knowledge_service/docs/04_testing/infrastructure_e2e_test_plan.md)
- [STORY-020: Infrastructure E2E Test](../stories/STORY-020-infrastructure-e2e-test.md)

---

## 참고 자료

- [EPIC-000: Infrastructure Setup](../epics/EPIC-000-infrastructure.md)
- [STORY-010: Docker Compose 환경 구성](../stories/STORY-010-docker-compose.md)
- [STORY-011: 데이터베이스 초기화](../stories/STORY-011-database-init.md)
- [STORY-012: 인증 인프라 (Keycloak)](../stories/STORY-012-keycloak.md)
- [STORY-013: 프로젝트 골격 생성](../stories/STORY-013-project-skeleton.md)
- [STORY-014: 개발 환경 가이드](../stories/STORY-014-dev-guide.md)
- [스프린트 실행 계획서](../../docs/02_스프린트_실행_계획서.md)
