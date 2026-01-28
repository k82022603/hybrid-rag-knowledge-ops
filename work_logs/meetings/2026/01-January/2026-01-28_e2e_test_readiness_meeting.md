# 긴급 회의: Frontend/Backend E2E 테스트 준비 미흡 대책

**날짜**: 2026-01-28 17:30
**채널**: #proj-hrkp-dev
**소집**: PM
**참석**: Infra, QA, Backend, TechLead
**Jira 이슈**: SCRUM-54 (Priority: Highest)

---

## 회의 배경

Sprint 04 Day 3에서 Frontend/Backend E2E 테스트(STORY-054) 진행 중, 테스트 환경이 준비되지 않은 상태로 확인됨.

사용자 피드백:
- "QA DB도 안 올라가 있는데 무슨 테스트 중이에요?"
- "QA는 E2E 테스트 하기전에는 Infra 도움 받아 무조건 모든 시스템 정상 가동 후 테스트 진행해주세요."

---

## 발견된 문제점 (3건)

### 1. Docker 서비스 중지 상태

| 서비스 | 상태 | 원인 |
|--------|------|------|
| kp-postgresql | Exited (127) → **자동 복구됨** | WAL 비정상 종료 후 자동 복구 |
| kp-elasticsearch | Exited (127) → **자동 복구됨** | 자동 복구 |
| kp-neo4j | Exited (127) → **자동 복구됨** | 자동 복구, APOC 플러그인 로드 |
| kp-keycloak | Exited (127) → **자동 복구됨** | 자동 복구, realm import 완료 |
| kp-nginx | Exited (127) → **미가동** | WSL2 bind mount 경로 해석 실패 |
| kp-loki | Exited (127) → **자동 복구됨** | 자동 복구 |
| kp-prometheus | Exited (127) → **자동 복구됨** | TSDB WAL replay 후 복구 |
| kp-promtail | Exited (127) → **자동 복구됨** | 자동 복구 |

### 2. Backend/API Gateway Unhealthy

| 서비스 | 상태 | 원인 |
|--------|------|------|
| kp-backend | **healthy로 복구됨** | PostgreSQL 복구 후 R2DBC 자동 재연결 |
| kp-api-gateway | **unhealthy (지속)** | healthcheck 경로 오류: `/` → 401 반환 (Spring Security) |

**API Gateway healthcheck 원인**: `docker-compose.yml`의 healthcheck가 `wget http://127.0.0.1:8080/`(루트)을 호출하나, Spring Security가 401 반환. 실제 서비스는 정상 동작 중. `/actuator/health` 호출 시 `{"status":"UP"}` 응답 확인.

### 3. QA E2E 테스트 전부 Mock 기반

| 카테고리 | 파일 수 | 테스트 수 | 모드 |
|---------|--------|----------|------|
| Frontend/Backend E2E | 5개 | 94개 | **Mock (TestClient)** |
| Infrastructure E2E | 5개 | 78개 | Docker 필수 |
| Root E2E (Legacy) | 3개 | 57개 | Docker 필수 |
| Contract 테스트 | 3개 | 62개 | Mock (Schema 검증) |
| **합계** | **16개** | **295개** | - |

- `conftest.py`에서 `TestClient(app)` 사용 → 실제 HTTP 요청 없음 (ASGI in-process)
- JWT 자체 생성 → Keycloak 미연동
- DB/ES/Neo4j 모두 Mock 처리
- `docker_helpers.py` 유틸이 존재하나 테스트에서 미사용

---

## 에이전트별 현황 보고

### Infra 보고

- Docker 서비스 대부분 자동 복구 완료 (7/8 서비스)
- **nginx만 미가동** - WSL2 bind mount 경로 문제. `docker compose up -d nginx`로 해결 가능
- **API Gateway unhealthy** - healthcheck URL을 `/actuator/health`로 변경 필요
- 리소스 경고: Elasticsearch 메모리 77.9% (1.17/1.5GB), Kibana 68.5% (526/768MB)

### QA 보고

- Frontend/Backend E2E 94개 테스트가 전부 Mock 기반
- Mock → Real 전환에 필요한 사항:
  - `conftest.py`에서 `TestClient(app)` → `httpx.AsyncClient(base_url=GATEWAY_URL)` 전환
  - JWT 자체 생성 → Keycloak OAuth2 토큰 취득으로 변경
  - DB 스키마 초기화 및 테스트 데이터 시딩 스크립트 필요
  - 서비스 헬스체크 wait 로직 필요
- `docker_helpers.py`에 컨테이너 제어 유틸리티가 이미 구현되어 있으나 미사용

### Backend 보고

- PostgreSQL 자동 복구 후 Backend R2DBC 자동 재연결 확인
- `DataInitializer`가 `auth_users` 테이블 정상 조회 (test@example.com, admin@example.com 존재)
- DB 연결 설정: `r2dbc:postgresql://postgresql:5432/knowledge` (ConnectionPool: initial=10, max=50)
- API Gateway는 기능 정상, healthcheck 경로만 수정 필요

### TechLead 보고

**심각 이슈 4건 발견:**

1. **Mock-Only 실행**: `conftest.py` line 110-112에서 client fixture가 항상 Mock 모드만 반환. Docker 모드 전환 분기 없음.
2. **docker_helpers.py 미활용**: Docker 유틸이 구현되어 있으나 어떤 테스트에서도 import 안 함.
3. **SSE 이벤트 타입 불일치**: `conftest.py`의 mock_sse_events는 `type=chunk` 사용하지만, `test_sse_streaming.py`의 `extract_tokens_from_events()`는 `type=token` 필터링. 런타임 실패 가능.
4. **보안 테스트 기대값 불일치**: `test_security_verification.py` D-005에서 `/search`, `/knowledge`에 401 기대하지만, `conftest.py`에서 이들을 public 엔드포인트로 명시.

**서비스 의존성 체인:**
```
Tier 0 (DB):     PostgreSQL, Keycloak-DB, Neo4j, ES, Redis, MinIO
Tier 1 (인증):    Keycloak → keycloak-db
Tier 2 (서비스):   Backend → postgresql, redis, minio
                  AI-Service → elasticsearch, neo4j, redis
Tier 3 (프록시):   API-Gateway → keycloak, backend, redis
                  Nginx → frontend, api-gateway
Tier 4 (UI):     Frontend (독립)
```

**3단계 E2E 전략 제안:**

| Phase | 범위 | 실행 환경 | CI/CD 전략 |
|-------|------|----------|-----------|
| Phase 1 | Mock E2E (TestClient 기반) | Docker 불필요 | 매 PR마다 실행 |
| Phase 2 | Docker E2E (httpx + 실제 서비스) | 전체 스택 필요 | Nightly build |
| Phase 3 | 풀스택 E2E (Playwright/Cypress) | 브라우저 포함 | Release 전 |

---

## 결정 사항

### 즉시 조치 (P0)

| # | 액션 아이템 | 담당 | 상태 |
|---|-----------|------|------|
| 1 | nginx 컨테이너 재시작 (`docker compose up -d nginx`) | Infra | 대기 |
| 2 | API Gateway healthcheck `/actuator/health`로 수정 | Infra | 대기 |
| 3 | SSE 이벤트 타입 불일치 수정 (chunk vs token) | QA | 대기 |
| 4 | conftest.py Docker 모드 client fixture 추가 (Mock→Real 전환) | QA | 대기 |

### 단기 조치 (P1)

| # | 액션 아이템 | 담당 | 상태 |
|---|-----------|------|------|
| 5 | 보안 테스트 기대값 현재 구현 기준 정렬 | QA | 대기 |
| 6 | docker_helpers.py를 장애 시나리오 테스트에 연결 | QA | 대기 |
| 7 | 테스트 데이터 시딩 스크립트 작성 | QA + ETL | 대기 |
| 8 | 3단계 E2E 전략 문서화 | TechLead | 대기 |

### 중기 조치 (P2)

| # | 액션 아이템 | 담당 | 상태 |
|---|-----------|------|------|
| 9 | Playwright 풀스택 E2E 검토 | TechLead + Frontend | Sprint 05 |
| 10 | CI/CD에 Docker E2E 단계 추가 | DevOps | Sprint 05 |

---

## 원칙 합의

> **"QA는 E2E 테스트 하기 전에 Infra 도움 받아 무조건 모든 시스템 정상 가동 후 테스트 진행한다."**

1. E2E 테스트 실행 전 반드시 `docker compose ps`로 전체 서비스 healthy 확인
2. Mock 기반 테스트는 Phase 1으로 분류하고, 실제 서비스 연동 테스트(Phase 2)를 별도 추진
3. Phase 2 테스트는 Infra가 인프라 준비 완료 확인 후 QA가 실행

---

## 다음 단계

1. Infra: nginx 재시작 + API Gateway healthcheck 수정 (즉시)
2. QA: SSE 이벤트 타입 수정 + conftest.py Docker 모드 추가 (Day 3 내)
3. QA: Docker 서비스 정상 확인 후 실제 E2E 테스트 실행
4. PM: SCRUM-54 진행 상태 추적 및 Sprint 04 일정 영향 평가

---

## 참고 자료

- Jira: [SCRUM-54](https://hybrid-rag-knowledge-ops.atlassian.net/browse/SCRUM-54) - E2E 테스트 준비 미흡 이슈
- Story: STORY-054 (서비스 간 통합 테스트)
- Sprint: [sprint-04.md](../../../backlog/sprints/sprint-04.md)
- E2E 테스트 계획: [sprint04_frontend_backend_e2e_test_plan.md](../../../knowledge_service/docs/04_testing/sprint04_frontend_backend_e2e_test_plan.md)
- conftest.py: `knowledge_service/src/tests/e2e/frontend_backend/conftest.py`
- docker_helpers.py: `knowledge_service/src/tests/e2e/frontend_backend/utils/docker_helpers.py`
