# Docker 환경 ui-api-verification.spec.ts 테스트 결과 보고서

**작성일**: 2026-01-30
**작성자**: QA Agent
**테스트 환경**: Docker Compose (18 containers)
**관련 회의록**: `11.e2e-test-review-meeting_2026-01-30.md`

---

## 1. 테스트 실행 개요

### 1.1 테스트 명령어

```bash
TEST_ENV=docker npx playwright test ui-api-verification.spec.ts --reporter=list
```

### 1.2 환경 상태

| 서비스 | 컨테이너 | 상태 | 포트 |
|--------|----------|------|------|
| Backend | kp-backend | Up (healthy) | 8081 |
| API Gateway | kp-api-gateway | Up (healthy) | 8080 |
| Frontend | kp-frontend | Up (healthy) | 80 |
| PostgreSQL | kp-postgresql | Up (healthy) | 5432 |
| Keycloak | kp-keycloak | Up (healthy) | 8180 |
| Elasticsearch | kp-elasticsearch | Up (healthy) | 9200 |
| Redis | kp-redis | Up (healthy) | 6379 |
| Neo4j | kp-neo4j | Up (healthy) | 7474, 7687 |
| AI Service | kp-ai-service | Up (healthy) | 8000 |
| MinIO | kp-minio | Up (healthy) | 9000-9001 |

---

## 2. 테스트 결과 요약

| 항목 | 결과 |
|------|------|
| 총 테스트 수 | 11개 |
| 통과 (Passed) | **2개** |
| 실패 (Failed) | **9개** |
| 스킵 (Skipped) | 0개 |
| 실행 시간 | 약 1.8분 |
| 환경 | Docker (TEST_ENV=docker) |

### 통과한 테스트

| 테스트 | 설명 | 소요 시간 |
|--------|------|----------|
| Navigation - track API calls | 페이지 간 이동 시 API 호출 추적 | 6.3s |
| API Response Time - login API | 로그인 API 응답 시간 < 3초 | 2.7s |

### 실패한 테스트

| 테스트 | 실패 원인 | 분류 |
|--------|----------|------|
| Login Flow - call /auth/login API | waitForResponse 타임아웃 | 인프라/라우팅 |
| Login Flow - correct request body | waitForResponse 타임아웃 | 인프라/라우팅 |
| Login Flow - 401 for invalid credentials | waitForResponse 타임아웃 | 인프라/라우팅 |
| Search Flow - call /search API | 로그인 후 페이지 리다이렉트 실패 | 인프라/라우팅 |
| Search Flow - correct search query | 로그인 후 페이지 리다이렉트 실패 | 인프라/라우팅 |
| Search Flow - auth token in headers | 로그인 후 페이지 리다이렉트 실패 | 인프라/라우팅 |
| Dashboard Load - call dashboard API | 로그인 후 페이지 리다이렉트 실패 | 인프라/라우팅 |
| Dashboard Load - track network requests | 테스트 타임아웃 | 인프라/라우팅 |
| API Response Time - search API | Search API 호출 실패 | 백엔드 미구현 |

---

## 3. 근본 원인 분석 (Root Cause Analysis)

### 3.1 Login Flow 테스트 실패

**증상**: `page.waitForResponse()` 타임아웃 (15초)

**원인 분석**:
1. Frontend는 localhost:3000에서 실행 (Vite dev server)
2. Vite proxy 설정: `/api` -> `localhost:8080` (API Gateway)
3. 실제 API 요청은 프록시를 통해 전달되지만, `waitForResponse()`가 원본 요청 URL을 기다림
4. 로그인 자체는 성공 (스크린샷에서 `testuser` 로그인 확인)

**증거**:
```bash
# Backend에서 로그인 성공 로그 확인
2026-01-30T08:14:04.626Z INFO c.knowledge.backend.service.AuthService : Login successful for email: test@example.com
```

**결론**: 로그인 기능은 정상 동작하나, Playwright의 `waitForResponse()` 패턴이 Vite proxy 환경에서 제대로 동작하지 않음

### 3.2 Search Flow 테스트 실패

**증상**: 로그인 후 `/search` 페이지 접근 시 "Search failed - Network Error" 표시

**원인 분석**:
1. Backend에 `/api/v1/search/keyword` 엔드포인트 미구현
2. API Gateway가 요청을 Backend로 전달했으나 404 NOT_FOUND 반환
3. GlobalExceptionHandler에서 500 Internal Server Error로 변환

**증거**:
```bash
# Backend 로그
2026-01-30T08:14:38.853Z ERROR c.k.b.exception.GlobalExceptionHandler: Unexpected error:
org.springframework.web.reactive.resource.NoResourceFoundException: 404 NOT_FOUND "No static resource api/v1/search/keyword."
```

**API 테스트 결과**:
```bash
$ curl -s -X POST http://localhost:8081/api/v1/search/keyword \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"query":"test"}'

{"status":500,"error":"Internal Server Error","message":"An unexpected error occurred"...}
```

### 3.3 Dashboard Load 테스트 실패

**증상**: "Failed to load dashboard statistics. Please try again later."

**원인**: Dashboard API 엔드포인트 미구현 또는 연결 오류

---

## 4. 스크린샷 분석

### 4.1 Dashboard 화면 (실패 상태)

![Dashboard Screenshot](/mnt/d/Users/KTDS/Documents/06.과제/hybrid-rag-knowledge-ops/knowledge_service/frontend/test-results/ui-api-verification-Dashbo-976ea--requests-on-dashboard-load-chromium/test-failed-1.png)

**관찰 사항**:
- 사용자 `testuser` / `test@example.com` 로그인 성공
- "Good afternoon, testuser" 인사말 표시
- Dashboard 통계 로딩 실패 메시지 표시
- Quick Search, Getting Started 섹션은 정상 렌더링

### 4.2 Search 화면 (실패 상태)

![Search Screenshot](/mnt/d/Users/KTDS/Documents/06.과제/hybrid-rag-knowledge-ops/knowledge_service/frontend/test-results/ui-api-verification-API-Re-0b49f-e-should-be-under-5-seconds-chromium/test-failed-1.png)

**관찰 사항**:
- 사용자 로그인 상태 유지
- Keyword Search 탭 선택
- "test query" 검색어 입력
- "Search failed - Network Error" 오류 표시

---

## 5. 결론

### 5.1 테스트 결과 해석

| 구분 | 상태 | 설명 |
|------|------|------|
| Frontend UI | **정상** | 로그인, 네비게이션, UI 렌더링 동작 |
| Backend Auth API | **정상** | `/api/v1/auth/login` 정상 응답 |
| Backend Search API | **미구현** | `/api/v1/search/keyword` 404 |
| Backend Dashboard API | **미구현 또는 오류** | 통계 로딩 실패 |
| E2E 테스트 설계 | **수정 필요** | Vite proxy 환경 고려 필요 |

### 5.2 품질 평가

| 항목 | 목표 | 실제 | 달성 |
|------|------|------|------|
| 테스트 통과율 | 100% (11/11) | 18% (2/11) | 미달성 |
| Login API | 검증 | 기능 정상, 테스트 실패 | 부분 달성 |
| Search API | 검증 | 미구현 | 미달성 |
| Dashboard API | 검증 | 미구현 또는 오류 | 미달성 |

---

## 6. 권장 조치 사항

### 6.1 P0 - 즉시 조치 (Backend Team)

| 작업 | 담당 | 우선순위 |
|------|------|----------|
| `/api/v1/search/keyword` 엔드포인트 구현 | Backend | P0 |
| `/api/v1/dashboard/statistics` 엔드포인트 구현 | Backend | P0 |
| API 라우팅 검증 | Backend/Infra | P0 |

### 6.2 P1 - 테스트 코드 개선 (QA Team)

| 작업 | 설명 |
|------|------|
| `waitForResponse()` 패턴 수정 | Vite proxy 환경에서 동작하도록 URL 패턴 조정 |
| 테스트 타임아웃 증가 | Docker 환경에서 30초 -> 60초 |
| 조건부 스킵 로직 추가 | API 미구현 시 graceful skip |

### 6.3 P2 - 인프라 개선 (DevOps Team)

| 작업 | 설명 |
|------|------|
| API Gateway 라우팅 검증 | `/api/v1/search/**` 경로 확인 |
| CI/CD 파이프라인 통합 | Docker 환경 E2E 테스트 자동화 |

---

## 7. 다음 단계

- [x] Docker 환경에서 테스트 실행
- [x] 테스트 결과 분석
- [x] 근본 원인 파악
- [ ] PM에게 결과 보고
- [ ] Backend Team에 API 구현 요청 전달
- [ ] 테스트 코드 개선 (P1)

---

## 8. 첨부 자료

### 8.1 테스트 출력 로그

```
Running 11 tests using 8 workers

  X  1 Login Flow - should call /auth/login API (35.6s)
  X  2 Login Flow - should receive 401 for invalid credentials (35.7s)
  X  3 Search Flow - should call /search API (36.8s)
  X  4 Dashboard Load - should call dashboard API (36.6s)
  X  5 Login Flow - should call /auth/login API with correct request body (35.3s)
  X  6 Search Flow - should send correct search query (35.1s)
  X  7 Search Flow - should include auth token in headers (32.6s)
  X  8 Dashboard Load - should track all network requests (30.6s)
  OK 9 Navigation - should track API calls (6.3s)
  OK 10 API Response Time - login API < 3 seconds (2.7s)
  X  11 API Response Time - search API < 5 seconds (17.7s)

9 failed, 2 passed (1.8m)
```

### 8.2 Login API 정상 동작 확인

```bash
$ curl -s -X POST http://localhost:8080/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"password123"}'

{
  "user": {
    "id": "1",
    "email": "test@example.com",
    "username": "testuser",
    "roles": ["USER"]
  },
  "accessToken": "eyJhbGci...",
  "refreshToken": "eyJhbGci..."
}
```

---

**보고서 끝**

*작성: QA Agent | 검토 대기: PM, TechLead, Backend*
