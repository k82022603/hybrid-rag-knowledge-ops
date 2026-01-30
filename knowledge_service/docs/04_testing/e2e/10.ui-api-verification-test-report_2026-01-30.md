# UI-API 통합 테스트 검증 보고서

**작성일**: 2026-01-30
**작성자**: QA Agent
**테스트 파일**: `ui-api-verification.spec.ts`
**실행 환경**: Mock (Backend 미실행)

---

## 1. 테스트 실행 결과 요약

| 항목 | 결과 |
|------|------|
| 총 테스트 수 | 11개 |
| 통과 (Passed) | 0개 |
| 실패 (Failed) | 0개 |
| 스킵 (Skipped) | 11개 |
| 실행 시간 | < 5초 |

### 실행 명령어
```bash
npx playwright test ui-api-verification.spec.ts --reporter=list
```

### 실행 결과
```
Running 11 tests using 8 workers

  -   1 [chromium] › Login Flow - API Verification › should call /auth/login API when submitting login form
  -   2 [chromium] › Login Flow - API Verification › should call /auth/login API with correct request body
  -   3 [chromium] › Login Flow - API Verification › should receive 401 for invalid credentials via UI
  -   4 [chromium] › Search Flow - API Verification › should call /search API when performing keyword search
  -   5 [chromium] › Search Flow - API Verification › should send correct search query in request body
  -   6 [chromium] › Search Flow - API Verification › should include auth token in search request headers
  -   7 [chromium] › Dashboard Load - API Verification › should call dashboard API when loading dashboard page
  -   8 [chromium] › Dashboard Load - API Verification › should track all network requests on dashboard load
  -   9 [chromium] › Navigation - API Verification › should track API calls when navigating between pages
  -  10 [chromium] › API Response Time - Via UI › login API response time should be under 3 seconds
  -  11 [chromium] › API Response Time - Via UI › search API response time should be under 5 seconds

  11 skipped
```

---

## 2. 테스트 케이스 분석

### 2.1 테스트 구성 (5개 카테고리, 11개 테스트)

| 카테고리 | 테스트 수 | 검증 목적 |
|----------|----------|----------|
| Login Flow - API Verification | 3 | 로그인 폼 제출 시 실제 API 호출 검증 |
| Search Flow - API Verification | 3 | 검색 수행 시 API 요청/응답 검증 |
| Dashboard Load - API Verification | 2 | 대시보드 로딩 시 API 호출 추적 |
| Navigation - API Verification | 1 | 페이지 이동 시 API 호출 패턴 검증 |
| API Response Time - Via UI | 2 | UI 동작 시 API 응답 시간 측정 |

### 2.2 테스트 케이스 상세

#### Login Flow - API Verification (3개)

| # | 테스트명 | 검증 내용 |
|---|---------|----------|
| 1 | should call /auth/login API when submitting login form | POST /api/v1/auth/login 호출 및 응답 검증 (status 200, accessToken, user) |
| 2 | should call /auth/login API with correct request body | 요청 본문에 email, password 포함 검증 |
| 3 | should receive 401 for invalid credentials via UI | 잘못된 자격증명 시 401 응답 검증 |

#### Search Flow - API Verification (3개)

| # | 테스트명 | 검증 내용 |
|---|---------|----------|
| 4 | should call /search API when performing keyword search | POST /api/v1/search 호출 및 결과 배열 검증 |
| 5 | should send correct search query in request body | 요청 본문에 query 필드 검증 |
| 6 | should include auth token in search request headers | Authorization: Bearer 헤더 검증 |

#### Dashboard Load - API Verification (2개)

| # | 테스트명 | 검증 내용 |
|---|---------|----------|
| 7 | should call dashboard API when loading dashboard page | 대시보드 로딩 시 /api/** 호출 로깅 |
| 8 | should track all network requests on dashboard load | 모든 API 요청 추적 및 상태 코드 검증 |

#### Navigation - API Verification (1개)

| # | 테스트명 | 검증 내용 |
|---|---------|----------|
| 9 | should track API calls when navigating between pages | 페이지별 API 호출 패턴 추적 |

#### API Response Time - Via UI (2개)

| # | 테스트명 | 검증 내용 |
|---|---------|----------|
| 10 | login API response time should be under 3 seconds | 로그인 API 응답 시간 < 3초 |
| 11 | search API response time should be under 5 seconds | 검색 API 응답 시간 < 5초 |

---

## 3. UI 테스트 vs API 통합 테스트 구분

### 3.1 테스트 유형 비교

```
+---------------------------------------------------------------------+
|  테스트 유형 스펙트럼                                                  |
+---------------------------------------------------------------------+
|                                                                     |
|  [순수 UI 테스트]                                                    |
|  +-----------------------+                                          |
|  | Browser -> React UI   |                                          |
|  | (Mock 데이터 사용)      |                                          |
|  +-----------------------+                                          |
|  예: dashboard.spec.ts, smoke-pages.spec.ts                         |
|  검증: DOM 렌더링, 컴포넌트 상태, 사용자 인터랙션                      |
|  Backend 호출: 없음 (Mock)                                          |
|                                                                     |
|  [API 직접 테스트]                                                   |
|  +----------------------------+                                     |
|  | API Client -> Backend      |                                     |
|  | (UI 우회)                   |                                     |
|  +----------------------------+                                     |
|  예: api-integration.spec.ts                                        |
|  검증: API 응답 구조, 상태 코드, 에러 처리                            |
|  Backend 호출: 직접                                                  |
|                                                                     |
|  [UI-API 통합 테스트] <-- ui-api-verification.spec.ts                |
|  +------------------------------------------+                       |
|  | Browser -> React UI -> Backend API        |                       |
|  | (실제 네트워크 호출 검증)                   |                       |
|  +------------------------------------------+                       |
|  예: ui-api-verification.spec.ts                                    |
|  검증: UI 동작 -> API 호출 -> 응답 처리 전체 흐름                     |
|  Backend 호출: UI 동작을 통한 간접 호출                              |
|                                                                     |
+---------------------------------------------------------------------+
```

### 3.2 ui-api-verification.spec.ts의 역할

이 테스트 파일은 **UI 테스트와 API 테스트의 간극을 메우는** 중요한 역할을 합니다:

| 기존 문제 | 해결 방안 |
|----------|----------|
| UI 테스트가 Mock 데이터만 사용 | `page.waitForResponse()`로 실제 네트워크 요청 캡처 |
| API 직접 테스트가 UI 로직 우회 | 실제 사용자 시나리오(폼 입력, 버튼 클릭)를 통한 API 호출 |
| 통합 지점 미검증 | UI 동작 -> API 호출 -> 응답 처리 전체 흐름 검증 |

### 3.3 `skipInMock()` 조건의 의미

```typescript
// test-env.helper.ts
export function skipInMock(reason?: string) {
  test.skip(isMockEnvironment(), reason || 'Skipped in Mock environment');
}

export function isMockEnvironment(): boolean {
  return (
    process.env.TEST_ENV === 'mock' ||
    process.env.USE_MOCK === 'true' ||
    !isDockerEnvironment()
  );
}
```

**Mock 환경에서 스킵하는 이유**:
1. Mock Interceptor가 auth API를 가로채어 실제 Backend로 전달하지 않음
2. `page.waitForResponse()`는 네트워크 레벨에서 응답을 대기하므로, Mock은 감지 불가
3. 테스트 타임아웃 발생 방지

---

## 4. Docker 환경에서 실행 조건

### 4.1 필요한 환경 변수

```bash
# 필수 설정
TEST_ENV=docker
VITE_USE_MOCK_AUTH=false
VITE_API_BASE_URL=http://localhost:8081

# 선택 설정 (Keycloak 사용 시)
KEYCLOAK_PORT=8180
USE_KEYCLOAK=true
```

### 4.2 필요한 인프라

| 서비스 | 포트 | 역할 | 필수 여부 |
|--------|------|------|----------|
| Backend (Spring Boot) | 8081 | API 서버 | 필수 |
| Frontend (Vite) | 5173 | 웹 UI | 필수 |
| PostgreSQL | 5432 | 데이터베이스 | 필수 |
| Keycloak | 8180 | 인증 서버 | 선택 (Docker 환경) |

### 4.3 실행 명령어

```bash
# Docker 환경에서 테스트 실행
TEST_ENV=docker npx playwright test ui-api-verification.spec.ts --reporter=list

# 또는 환경 파일 사용
cp .env.docker .env
npx playwright test ui-api-verification.spec.ts
```

### 4.4 예상 결과 (Docker 환경)

```
Running 11 tests using 8 workers

  [1/11] Login Flow - API Verification › should call /auth/login API...
  [2/11] Login Flow - API Verification › should call /auth/login API with correct request body
  ...

  11 passed (약 30-60초)
```

---

## 5. 테스트 파일 구조

```
e2e/
├── helpers/
│   ├── auth.helper.ts          # 로그인 헬퍼 (환경 자동 감지)
│   └── test-env.helper.ts      # 환경 감지 유틸리티
├── api-integration.spec.ts     # API 직접 테스트 (27개)
├── ui-api-verification.spec.ts # UI-API 통합 테스트 (11개) <-- 이번 테스트
├── auth.spec.ts                # 인증 테스트 (10개)
├── dashboard.spec.ts           # 대시보드 UI 테스트 (49개)
├── search-filters.spec.ts      # 검색 필터 UI 테스트 (25개)
├── smoke-pages.spec.ts         # 페이지 렌더링 테스트 (45개)
├── chat-search.spec.ts         # 채팅 검색 테스트 (13개)
└── search-workflow.spec.ts     # 검색 워크플로우 테스트
```

---

## 6. 결론 및 권장사항

### 6.1 결론

`ui-api-verification.spec.ts`는 Mock 환경에서 올바르게 **11개 테스트 모두 스킵**되었습니다. 이는 설계된 대로 동작하며, 다음을 확인합니다:

1. `skipInMock()` 함수가 정상적으로 환경을 감지
2. Backend 미실행 상태에서 불필요한 테스트 실패 방지
3. 테스트 실행 시간 절약 (< 5초)

### 6.2 권장사항

| 우선순위 | 작업 | 담당 |
|---------|------|------|
| P0 | Docker 환경에서 ui-api-verification.spec.ts 실행 검증 | QA |
| P1 | Dashboard, Bookmarks API 통합 테스트 추가 | QA |
| P1 | 테스트 결과 리포트에 환경별 분류 추가 | DevOps |
| P2 | CI/CD 파이프라인에 Docker 환경 테스트 통합 | DevOps |

---

## 7. 관련 문서

- PM 보고서: `docs/04_testing/e2e/09.qa_test_issue_report_2026-01-30.md`
- 테스트 환경 헬퍼: `e2e/helpers/test-env.helper.ts`
- API 통합 테스트: `e2e/api-integration.spec.ts`

---

**보고서 끝**

*이 보고서는 QA Agent가 작성했습니다.*
