# Frontend/Backend E2E 테스트 가이드

**STORY-054** | Sprint 04 | QA Engineer
**최종 업데이트**: 2026-01-28

---

## 1. 개요

Frontend/Backend E2E 테스트는 API Gateway를 통한 전체 서비스 흐름을 검증합니다. **Mock 모드**와 **Docker 모드** 두 가지 실행 방식을 지원하며, `E2E_MODE` 환경변수로 전환합니다.

### 테스트 범위

```
Frontend → API Gateway → Backend/AI Service → DB/ES/Neo4j
                ↓
          5개 카테고리 × 시나리오
```

| 카테고리 | 코드 | 시나리오 수 | 검증 대상 |
|---------|------|-----------|----------|
| A: 인증 흐름 | `test_auth_flow.py` | 17 | 로그인, JWT 갱신, 만료/변조 토큰, CORS |
| B: 검색 흐름 | `test_search_flow.py` | 16 | 키워드/시맨틱/하이브리드 검색, 빈 결과, 대량 쿼리 |
| C: SSE 스트리밍 | `test_sse_streaming.py` | 19 | POST SSE, 토큰 스트리밍, 중단, 한글 처리 |
| D: 보안 검증 | `test_security_verification.py` | 26 | XSS, SQL Injection, CSRF, Rate Limit |
| E: 에러 핸들링 | `test_error_handling.py` | 18 | 서비스 다운, 타임아웃, 동시 요청 |
| **합계** | | **96** | |

추가로 **Contract 테스트 62개**가 서비스 간 API 스키마를 검증합니다.

---

## 2. 디렉토리 구조

```
knowledge_service/src/tests/
├── e2e/
│   └── frontend_backend/
│       ├── conftest.py                    # Mock/Docker 모드 설정, Fixture
│       ├── test_auth_flow.py              # Category A: 인증
│       ├── test_search_flow.py            # Category B: 검색
│       ├── test_sse_streaming.py          # Category C: SSE
│       ├── test_security_verification.py  # Category D: 보안
│       ├── test_error_handling.py         # Category E: 에러
│       └── utils/
│           ├── __init__.py
│           ├── auth_helpers.py            # JWT 토큰 생성 유틸리티
│           ├── docker_helpers.py          # Docker 컨테이너 제어
│           └── sse_test_client.py         # SSE POST 클라이언트
├── contract/
│   ├── conftest.py                        # JSON Schema 정의
│   ├── test_backend_ai_contract.py        # Backend ↔ AI Service
│   ├── test_ai_knowledge_contract.py      # AI ↔ Knowledge Service
│   └── test_sse_event_contract.py         # SSE 이벤트 포맷
└── ...
```

---

## 3. 실행 모드

### 3.1 Mock 모드 (기본값)

Docker 없이 실행 가능. FastAPI `TestClient`로 ASGI in-process 테스트.

```bash
# 전체 실행
E2E_MODE=mock pytest knowledge_service/src/tests/e2e/frontend_backend/ -v

# 카테고리별 실행
E2E_MODE=mock pytest knowledge_service/src/tests/e2e/frontend_backend/test_auth_flow.py -v
```

**특징**:
- Docker 불필요
- `unittest.mock`으로 DB/외부 서비스 Mock
- JWT 토큰 자체 생성 (`auth_helpers.py`)
- 빠른 실행 (수초 이내)
- CI/CD PR 파이프라인에 적합

### 3.2 Docker 모드

Docker Compose 전체 스택이 필요. `httpx.Client`로 실제 HTTP 요청.

```bash
# 전제: Docker 서비스 전체 healthy
cd infrastructure/docker && docker compose ps

# 전체 실행
E2E_MODE=docker pytest knowledge_service/src/tests/e2e/frontend_backend/ -v

# 카테고리별 실행
E2E_MODE=docker pytest knowledge_service/src/tests/e2e/frontend_backend/test_search_flow.py -v
```

**특징**:
- Docker Compose 18개 서비스 필수
- 실제 API Gateway 경유 HTTP 요청
- 실제 DB/ES/Neo4j 연동
- Keycloak 인증 (또는 Backend login API)
- Nightly build / Release 전 검증에 적합

### 3.3 Contract 테스트

서비스 간 API 스키마를 검증. Docker 불필요.

```bash
pytest knowledge_service/src/tests/contract/ -v
```

---

## 4. 환경 설정

### 4.1 환경변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `E2E_MODE` | `mock` | 테스트 모드 (`mock` / `docker`) |
| `E2E_GATEWAY_URL` | `http://localhost:8080` | API Gateway URL (Docker 모드) |
| `E2E_BACKEND_URL` | `http://localhost:8081` | Backend 직접 URL |
| `E2E_AI_SERVICE_URL` | `http://localhost:8000` | AI Service URL |
| `JWT_SECRET_KEY` | (내장 기본값) | JWT 서명 키 (Mock 모드) |

### 4.2 Docker 모드 전제조건

Docker 모드 실행 전 반드시 확인:

```bash
# 1. 서비스 상태 확인 (모두 healthy 필수)
cd infrastructure/docker
docker compose ps

# 2. 핵심 서비스 헬스체크
curl -s http://localhost:8080/actuator/health  # API Gateway
curl -s http://localhost:8081/actuator/health  # Backend
curl -s http://localhost:8000/health           # AI Service
```

**서비스 의존성 체인** (기동 순서):

```
Tier 0 (DB):     PostgreSQL, Elasticsearch, Neo4j, Redis, MinIO
Tier 1 (인증):    Keycloak → keycloak-db
Tier 2 (서비스):   Backend → postgresql, redis, minio
                  AI-Service → elasticsearch, neo4j, redis
Tier 3 (프록시):   API-Gateway → keycloak, backend, redis
                  Nginx → frontend, api-gateway
Tier 4 (UI):     Frontend
```

### 4.3 Python 의존성

```bash
cd knowledge_service
pip install pytest pytest-asyncio httpx PyJWT
```

---

## 5. conftest.py 핵심 구조

### 5.1 모드 전환 메커니즘

```python
# conftest.py
E2E_MODE = os.getenv("E2E_MODE", "mock")

def is_docker_mode() -> bool:
    return E2E_MODE == "docker"
```

### 5.2 Client Fixture

```python
@pytest.fixture(scope="module")
def client():
    if is_docker_mode():
        return httpx.Client(base_url=GATEWAY_URL, timeout=30.0)
    else:
        return TestClient(app)
```

### 5.3 Docker 서비스 헬스체크 (자동)

```python
@pytest.fixture(scope="session", autouse=True)
def check_docker_services():
    """Docker 모드에서 서비스 헬스체크 자동 검증."""
    if is_docker_mode():
        services = [
            ("Gateway", GATEWAY_URL + "/actuator/health"),
            ("Backend", BACKEND_URL + "/actuator/health"),
            ("AI Service", AI_SERVICE_URL + "/health"),
        ]
        for name, url in services:
            try:
                resp = httpx.get(url, timeout=5.0)
                if resp.status_code != 200:
                    pytest.skip(f"{name} not healthy")
            except Exception as e:
                pytest.skip(f"{name} not reachable: {e}")
```

### 5.4 JWT 토큰 Fixture

```python
@pytest.fixture
def valid_token():
    if is_docker_mode():
        # 실제 로그인 API로 토큰 취득
        resp = httpx.post(f"{GATEWAY_URL}/api/v1/auth/login",
                         json={"email": "test@example.com", "password": "testpass123"})
        return resp.json().get("access_token") or resp.json().get("accessToken")
    else:
        # Mock JWT 자체 생성
        return generate_valid_token(user_id="user-001", ...)
```

---

## 6. 테스트 카테고리 상세

### 6.1 Category A: 인증 흐름

| ID | 시나리오 | 우선순위 | 검증 내용 |
|----|---------|---------|----------|
| A-001 | 정상 로그인 → JWT 발급 | P0 | 이메일/패스워드 로그인, 토큰 구조 검증 |
| A-002 | 만료 JWT → 401 → 토큰 갱신 | P0 | 만료 토큰 거부, refresh token으로 갱신 |
| A-003 | 변조 JWT → 401 | P0 | 서명 위조 토큰 거부 |
| A-004 | Keycloak 장애 시 로그인 실패 | P1 | 외부 인증 서비스 장애 처리 |
| A-005 | CORS 정책 검증 | P1 | 허용 Origin, 차단 Origin |

### 6.2 Category B: 검색 흐름

| ID | 시나리오 | 우선순위 | 검증 내용 |
|----|---------|---------|----------|
| B-001 | 키워드 검색 | P0 | `/search/hybrid` POST, 결과 구조 |
| B-002 | 시맨틱 검색 | P0 | 벡터 유사도 기반 검색 |
| B-003 | 하이브리드 검색 (RRF) | P0 | RRF Fusion 통합 검색 |
| B-004 | 빈 결과 처리 | P1 | 존재하지 않는 쿼리 처리 |
| B-005 | 대량 쿼리 (1000자) | P1 | 경계값 테스트 |

### 6.3 Category C: SSE 스트리밍

| ID | 시나리오 | 우선순위 | 검증 내용 |
|----|---------|---------|----------|
| C-001 | POST SSE 스트리밍 | P0 | `start` → `chunk` → `end` 이벤트 순서 |
| C-002 | 토큰(chunk) 스트리밍 | P0 | 여러 chunk 이벤트 수신 및 조합 |
| C-003 | 스트리밍 중단 (Abort) | P1 | 클라이언트 중단 시 서버 정리 |
| C-004 | 재연결 처리 | P1 | 연결 끊김 후 재시도 |
| C-005 | 한글 텍스트 보존 | P1 | UTF-8 한글 라운드트립 |

**SSE 이벤트 타입** (실제 API 명세):

| 이벤트 | 필드 | 설명 |
|--------|------|------|
| `start` | `sources`, `context_length` | 검색 시작, 출처 정보 |
| `chunk` | `content` | 답변 텍스트 조각 |
| `end` | - | 스트리밍 완료 |
| `error` | `message` | 오류 발생 |

### 6.4 Category D: 보안 검증

| ID | 시나리오 | 우선순위 | 검증 내용 |
|----|---------|---------|----------|
| D-001 | XSS 페이로드 차단 | P0 | `<script>`, `onerror` 등 7개 패턴 |
| D-002 | SQL Injection 차단 | P0 | `DROP TABLE`, `UNION SELECT` 등 7개 패턴 |
| D-003 | CSRF 토큰 검증 | P1 | 토큰 없는 상태 변경 요청 거부 |
| D-004 | Rate Limiting | P1 | 대량 요청 시 429 응답 |
| D-005 | 비인증 접근 차단 | P0 | 보호 엔드포인트 401 응답 |

### 6.5 Category E: 에러 핸들링

| ID | 시나리오 | 우선순위 | 검증 내용 |
|----|---------|---------|----------|
| E-001 | Backend 다운 시 | P0 | 서비스 장애 시 적절한 에러 응답 |
| E-002 | AI Service 타임아웃 | P1 | 30초 타임아웃 시 에러 처리 |
| E-003 | Elasticsearch 장애 | P1 | 검색 엔진 장애 시 fallback |
| E-004 | 네트워크 오류 | P1 | 연결 실패 시 에러 응답 |
| E-005 | 동시 5개 요청 | P1 | 동시성 처리 검증 |

---

## 7. 유틸리티

### 7.1 auth_helpers.py

JWT 토큰 생성/검증 유틸리티.

```python
from .utils.auth_helpers import (
    generate_valid_token,       # 정상 JWT 생성
    generate_expired_token,     # 만료 JWT 생성
    generate_tampered_token,    # 변조 JWT 생성
    generate_refresh_token,     # 갱신 토큰 생성
    build_auth_headers,         # Authorization 헤더 생성
    TEST_ACCOUNTS,              # 테스트 계정 정보
)
```

### 7.2 sse_test_client.py

POST 기반 SSE 스트리밍 클라이언트.

```python
from .utils.sse_test_client import SSETestClient, SSEEvent

client = SSETestClient(base_url="http://localhost:8080", token="jwt-token")
events = await client.collect_all_events("RAG 시스템 동작 원리")
```

### 7.3 docker_helpers.py

Docker 컨테이너 상태 확인 및 제어.

```python
from .utils.docker_helpers import (
    get_all_container_statuses,    # 전체 컨테이너 상태
    wait_for_container_health,     # 헬스체크 대기
    container_down,                # 컨테이너 중지 (장애 시뮬레이션)
)
```

---

## 8. 테스트 결과 (2026-01-28 기준)

### 8.1 Mock 모드

| 카테고리 | 테스트 수 | Pass | Fail | 통과율 |
|---------|----------|------|------|--------|
| A: 인증 | 17 | 17 | 0 | **100%** |
| B: 검색 | 16 | 16 | 0 | **100%** |
| C: SSE | 19 | 19 | 0 | **100%** |
| D: 보안 | 26 | 26 | 0 | **100%** |
| E: 에러 | 18 | 18 | 0 | **100%** |
| **합계** | **96** | **96** | **0** | **100%** |

### 8.2 Docker 모드

| 카테고리 | 테스트 수 | Pass | Fail | Skip |
|---------|----------|------|------|------|
| A: 인증 | 17 | 11 | 4 | 2 |
| B: 검색 | 16 | 9 | 7 | 0 |
| C: SSE | 19 | 9 | 1 | 9 |
| D: 보안 | 26 | 6 | 7 | 13 |
| E: 에러 | 18 | 4 | 0 | 14 |
| **합계** | **96** | **39** | **19** | **38** |

### 8.3 Docker 모드 실패 원인 분류

| 이슈 | 건수 | 근본 원인 | 해결 방향 |
|------|------|----------|----------|
| Gateway JWT 강제 | 10 | Gateway가 `/search/**`에 JWT 요구, AI Service는 미요구 | Gateway SecurityConfig 통일 |
| Logout 인증 미적용 | 3 | `/auth/logout`이 인증 없이 200 반환 | Backend SecurityConfig 수정 |
| Login 필드명 불일치 | 2 | Gateway: `accessToken` (camelCase) vs AI Service: `access_token` | DTO 통일 |
| 테스트 JWT 미인식 | 2 | 자체 생성 JWT가 Gateway JwtFilter 통과 불가 | Keycloak 토큰 사용 |
| Health 인증 강제 | 1 | `/health` 엔드포인트에 JWT 요구 | SecurityConfig에서 제외 |
| httpx 빈 Bearer | 1 | `httpx`가 빈 Bearer 헤더 거부 | 빈 문자열 대신 None 사용 |

### 8.4 Contract 테스트

| 계약 | 테스트 수 | 결과 |
|------|----------|------|
| Backend ↔ AI Service | 15 | **ALL PASS** |
| AI ↔ Knowledge Service | 18 | **ALL PASS** |
| SSE 이벤트 프로토콜 | 29 | **ALL PASS** |
| **합계** | **62** | **100%** |

---

## 9. 알려진 이슈

### 9.1 Gateway-AI Service 보안 정책 불일치

```
Gateway SecurityConfig: /api/v1/search/** → JWT 필수
AI Service (FastAPI):   /api/v1/search/** → 인증 없음 (public)
```

**영향**: Docker 모드에서 검색 테스트 시 Gateway 경유 시 401, AI Service 직접 호출 시 200.

**해결 방향**: Sprint 05에서 Gateway SecurityConfig과 AI Service 인증 정책 통일 예정.

### 9.2 Login 응답 필드명 불일치

```
Gateway (Java):    { "accessToken": "...", "refreshToken": "..." }
AI Service (Python): { "access_token": "...", "refresh_token": "..." }
```

**영향**: Frontend가 두 가지 필드명을 모두 처리해야 함.

### 9.3 Logout 엔드포인트 보안 갭

`POST /api/v1/auth/logout`이 JWT 없이도 200을 반환합니다. 인증되지 않은 사용자의 로그아웃 요청이 성공하는 보안 문제.

---

## 10. Troubleshooting

### Docker 서비스가 시작되지 않을 때

```bash
# 서비스 로그 확인
docker compose logs --tail=30 <service-name>

# 전체 재시작
docker compose down && docker compose up -d

# 특정 서비스 재시작
docker compose restart <service-name>

# 컨테이너 강제 재생성
docker compose up -d --force-recreate <service-name>
```

### pytest 실행 시 import 에러

```bash
# 프로젝트 루트에서 실행 (경로 해석 문제 방지)
cd /path/to/hybrid-rag-knowledge-ops
pytest knowledge_service/src/tests/e2e/frontend_backend/ -v
```

### Docker 모드에서 모든 테스트 Skip될 때

```bash
# 서비스 헬스체크 확인
curl -s http://localhost:8080/actuator/health
curl -s http://localhost:8081/actuator/health
curl -s http://localhost:8000/health

# 서비스가 응답하지 않으면 Docker 상태 확인
docker compose ps
```

### SSE 스트리밍 테스트 실패 시

SSE 이벤트 타입이 올바른지 확인:
- `start` (검색 시작) → `chunk` (텍스트 조각) → `end` (완료)
- 이전 명세의 `token`, `done`, `sources`는 더 이상 사용하지 않음

---

## 11. CI/CD 통합 가이드

### Phase 1: PR 파이프라인 (Fast Feedback)

```yaml
# GitHub Actions
- name: Run Mock E2E Tests
  run: |
    E2E_MODE=mock pytest knowledge_service/src/tests/e2e/frontend_backend/ -v --tb=short
    pytest knowledge_service/src/tests/contract/ -v --tb=short
```

### Phase 2: Nightly Build (Full Validation)

```yaml
- name: Start Docker Services
  run: |
    cd infrastructure/docker
    docker compose up -d
    sleep 60  # 서비스 안정화 대기

- name: Run Docker E2E Tests
  run: |
    E2E_MODE=docker pytest knowledge_service/src/tests/e2e/frontend_backend/ -v --tb=long
```

### Phase 3: Release Validation (Sprint 05 예정)

```yaml
- name: Run Playwright E2E
  run: |
    cd knowledge_service/frontend
    npx playwright test
```

---

## 12. 새 테스트 추가 가이드

### 12.1 테스트 파일 생성

```python
"""
Category X: New Category E2E Tests

Author: QA Agent
Sprint: Sprint XX
"""

import pytest
from unittest.mock import MagicMock, patch

class TestX001ScenarioName:
    """X-001: 시나리오 설명."""

    @pytest.mark.e2e
    @pytest.mark.sprint04_fb_e2e
    @pytest.mark.p0
    def test_scenario_happy_path(self, client, api_prefix, auth_headers):
        """정상 시나리오 검증."""
        response = client.post(
            f"{api_prefix}/endpoint",
            json={"key": "value"},
            headers=auth_headers,
        )
        assert response.status_code == 200
```

### 12.2 Mock/Docker 호환성

Mock/Docker 양쪽에서 동작하도록 작성:

```python
def test_example(self, client, api_prefix):
    # client는 conftest.py에서 모드에 따라 자동 전환됨
    # Mock 모드: TestClient (ASGI in-process)
    # Docker 모드: httpx.Client (실제 HTTP)
    response = client.post(f"{api_prefix}/search/hybrid",
                          json={"query": "test", "top_k": 5})
    assert response.status_code in [200, 401]  # Docker에서는 JWT 필요할 수 있음
```

### 12.3 Marker 규칙

```python
@pytest.mark.e2e                    # E2E 테스트
@pytest.mark.sprint04_fb_e2e        # Sprint 04 Frontend/Backend
@pytest.mark.auth_flow              # Category A
@pytest.mark.search_flow            # Category B
@pytest.mark.sse_streaming          # Category C
@pytest.mark.security_verification  # Category D
@pytest.mark.error_handling         # Category E
@pytest.mark.p0                     # Priority 0 (Critical)
@pytest.mark.p1                     # Priority 1 (High)
@pytest.mark.mock_mode              # Mock 전용
@pytest.mark.docker_mode            # Docker 전용
```

---

## 참고 자료

- [Sprint 04 E2E 테스트 계획](sprint04_frontend_backend_e2e_test_plan.md)
- [Mock 테스트 전수 조사 보고서](mock_test_audit_report.md)
- [E2E 테스트 준비 미흡 회의록](../../../work_logs/meetings/2026/01-January/2026-01-28_e2e_test_readiness_meeting.md)
- [API 통합 설계서](../02_design/04_api_integration_design.md)
- Jira: SCRUM-44 (STORY-054), SCRUM-54 (E2E 이슈)
