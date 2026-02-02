# E2E 테스트 검토 회의록

**날짜**: 2026-02-02
**참석자**: TechLead, QA, PM
**주제**: E2E 테스트 현황 및 개선 방안

---

## 1. 현황 분석

### 1.1 테스트 파일 구조

| 파일명 | 테스트 수 | 설명 |
|--------|----------|------|
| `auth.spec.ts` | 11개 | 로그인/로그아웃, 인증 흐름 |
| `api-integration.spec.ts` | 35개 | Backend API 직접 호출 테스트 |
| `chat-search.spec.ts` | 22개 | 채팅 기반 검색 UI |
| `dashboard.spec.ts` | 33개 | 대시보드 기능 |
| `search-filters.spec.ts` | 21개 | 검색 필터 기능 |
| `search-workflow.spec.ts` | 16개 | 키워드 검색 워크플로우 |
| `smoke-pages.spec.ts` | 33개 | 페이지 스모크 테스트 |
| `ui-api-verification.spec.ts` | 12개 | UI-API 연동 검증 |
| **합계** | **~183개** | **E2E 시나리오** |

### 1.2 테스트 시나리오 분류

#### 인증 관련 (auth.spec.ts)
- 로그인 폼 표시 검증
- 빈 필드 유효성 검사
- 잘못된 자격 증명 오류 처리
- 정상 로그인 (일반 사용자/관리자)
- Remember Me 체크박스
- 로그아웃 및 리다이렉트
- 보호된 라우트 접근 제어
- 접근성 (폼 레이블, 키보드 네비게이션)

#### API 통합 테스트 (api-integration.spec.ts)
- Auth API: 로그인, 토큰 발급, 현재 사용자 조회
- Search API: 키워드 검색, 필터 적용, 페이지네이션
- Dashboard API: 통계, 건강 상태, 활동 로그
- Profile API: 사용자 정보, 활동, 알림
- Bookmark API: 북마크 CRUD
- Admin API: 사용자 관리, 감사 로그
- Security: 만료된 토큰, 잘못된 토큰, 헤더 필수
- 응답 형식 및 성능 검증

#### 검색 기능 (chat-search.spec.ts, search-*.spec.ts)
- 채팅 인터페이스 표시
- 입력 동작 (Enter, Shift+Enter)
- 메시지 전송 및 스트리밍 응답
- 대화 이력 유지 및 삭제
- 소스 인용 표시
- 오류 처리 및 스트리밍 취소
- 키워드 검색 워크플로우
- 필터 패널 및 적용
- 페이지네이션
- 접근성 (ARIA 속성, 키보드 네비게이션)

#### 대시보드 (dashboard.spec.ts)
- 페이지 로드 및 환영 메시지
- 통계 카드 (4개: 문서, 검색, 사용자, 응답시간)
- 빠른 검색 (Ctrl+K, Enter, Escape)
- 최근 검색 관리
- 시작하기 섹션
- 반응형 레이아웃
- 사이드바 네비게이션
- 시간대별 인사말
- 관리자 전용 UI

#### 페이지 스모크 테스트 (smoke-pages.spec.ts)
- BookmarkPage: 렌더링, 폴더 네비게이션, 뷰 토글
- ProfilePage: 탭 네비게이션 (Profile, Password, Activity, Notifications)
- AdminPage: 시스템 통계, 사용자 관리, 설정, 감사 로그 탭
- DocumentUploadPage: 드래그앤드롭, 지원 형식, 최근 업로드
- 사이드바 네비게이션 검증
- 라우트 보호 검증

### 1.3 헬퍼 함수 분석

#### auth.helper.ts
- `login()`: 범용 로그인 (Keycloak/Mock 자동 감지)
- `loginAsAdmin()`: 관리자 로그인 + Mock 폴백
- `loginAsUser()`: 사용자 로그인 + Mock 폴백
- `logout()`: 로그아웃 + localStorage 정리
- `setupMockAuth()`: Mock 인증 설정 (API 불가 시)

#### test-env.helper.ts
- `isDockerEnvironment()`: Docker 환경 감지
- `isMockEnvironment()`: Mock 환경 감지
- `skipInDocker()`: Docker에서 스킵
- `skipInMock()`: Mock에서 스킵
- `waitForApiResponse()`: 환경별 타임아웃 조정
- `getTestConfig()`: 환경별 설정값 반환

---

## 2. 발견된 문제

### 2.1 Rate Limiting 문제 (심각도: High)

```
WARN c.knowledge.backend.service.AuthService : Rate limit exceeded for email: admin@example.com
Login attempts exceeded. Please try again after 15 minutes.
```

**원인**: 
- E2E 테스트 반복 실행 시 동일 계정으로 다수의 로그인 시도
- Backend에 Rate Limiting 정책이 적용되어 있음

**현재 대응**:
- `auth.spec.ts`에서 Rate Limit 감지 시 Mock 인증으로 폴백 (lines 109-130)
- 하지만 API 테스트에서는 폴백 불가

### 2.2 환경 불일치 문제 (심각도: Medium)

| 항목 | Mock 환경 | Docker 환경 |
|------|----------|-------------|
| 인증 | localStorage Mock | Backend JWT |
| API 호출 | Mock Interceptor | 실제 API |
| Rate Limit | 없음 | 적용됨 |
| 데이터 | 하드코딩 | 실제 DB |

**영향**:
- Mock 환경에서 Pass한 테스트가 Docker에서 Fail 가능
- API 응답 형식 불일치 가능성

### 2.3 테스트 스킵 로직 (심각도: Low)

많은 테스트에서 `expect(true).toBeTruthy()` 패턴 사용:
```typescript
// Example from chat-search.spec.ts
expect(hasAiResponse || hasError || true).toBeTruthy();
```

**문제점**:
- 실제 검증 없이 항상 Pass
- False Positive 위험

### 2.4 현재 Playwright 설정

```typescript
// playwright.config.ts
use: {
  baseURL: 'http://localhost:3000',  // Vite dev server
  trace: 'on-first-retry',
  screenshot: 'only-on-failure',
  video: 'retain-on-failure',
},
webServer: {
  command: 'npm run dev',
  url: 'http://localhost:3000',
  reuseExistingServer: !process.env.CI,
  timeout: 120 * 1000,
},
```

**문제점**:
- Docker 환경의 Backend API (8081) 연결 설정 없음
- API Gateway (8080) 연결 설정 없음

---

## 3. 개선 방안

### 3.1 Rate Limiting 대응 방안

#### 옵션 A: 테스트용 Rate Limit 설정 (권장)

```yaml
# application-test.yml
security:
  rate-limit:
    login:
      max-attempts: 1000  # 테스트 환경에서 제한 완화
      window-minutes: 1
```

**장점**: 테스트 코드 수정 불필요
**단점**: 테스트 환경 별도 구성 필요

#### 옵션 B: 테스트 전 Rate Limit 리셋

```bash
# 테스트 시작 전 실행
./scripts/reset-rate-limit.sh admin@example.com
```

**구현 필요 사항**:
- Backend에 Rate Limit 리셋 API 추가 (admin 권한 필요)
- 또는 Redis 직접 접근하여 키 삭제

#### 옵션 C: 테스트별 고유 계정 사용

```typescript
const testUser = {
  email: `test-${Date.now()}@example.com`,
  password: 'password123'
};
```

**장점**: Rate Limit 회피 완전 해결
**단점**: 테스트 데이터 정리 필요

### 3.2 Docker 환경 E2E 테스트 프로세스

#### 소스 컴파일/배포 절차

```bash
# 1. 프론트엔드 빌드
cd knowledge_service/frontend
npm run build

# 2. Backend 빌드 (Gradle)
cd ../backend
./gradlew bootJar

# 3. Docker 이미지 재빌드
docker-compose build kp-frontend kp-backend

# 4. 컨테이너 재시작
docker-compose up -d kp-frontend kp-backend
```

#### Docker 환경 E2E 테스트 실행

```bash
# 환경 변수 설정
export TEST_ENV=docker
export KEYCLOAK_PORT=8180
export BACKEND_URL=http://localhost:8081/api/v1

# 테스트 실행
npm run test:e2e

# 또는 특정 테스트만
npx playwright test auth.spec.ts
```

#### 권장 테스트 스크립트 (신규 작성 필요)

```bash
#!/bin/bash
# scripts/run-e2e-docker.sh

# 1. Rate Limit 리셋
docker exec kp-backend curl -X POST http://localhost:8081/api/v1/admin/reset-rate-limit

# 2. 테스트 데이터 초기화
./scripts/seed-initial-data.sh

# 3. E2E 테스트 실행
cd knowledge_service/frontend
TEST_ENV=docker npx playwright test

# 4. 결과 리포트
npx playwright show-report
```

### 3.3 테스트 품질 개선

#### False Positive 패턴 수정

**Before**:
```typescript
expect(hasAiResponse || hasError || true).toBeTruthy();
```

**After**:
```typescript
// 명시적 스킵 또는 실제 검증
if (!hasAiResponse && !hasError) {
  test.skip('API response not available');
}
expect(hasAiResponse || hasError).toBeTruthy();
```

#### 환경별 테스트 분리

```typescript
// e2e/docker-only/api-integration.spec.ts
test.describe('Docker-only API Tests', () => {
  test.beforeAll(() => {
    skipInMock('Requires real Backend API');
  });
  // ...
});

// e2e/mock-only/ui-rendering.spec.ts
test.describe('Mock-only UI Tests', () => {
  test.beforeAll(() => {
    skipInDocker('Uses mock data');
  });
  // ...
});
```

---

## 4. 액션 아이템

| 순번 | 작업 | 담당자 | 우선순위 | 예상 소요 |
|------|------|--------|----------|----------|
| 1 | Backend Rate Limit 테스트 프로파일 추가 | Backend | High | 2h |
| 2 | Rate Limit 리셋 스크립트 작성 | DevOps | High | 1h |
| 3 | Docker E2E 테스트 실행 스크립트 작성 | QA | High | 2h |
| 4 | False Positive 패턴 수정 | QA | Medium | 4h |
| 5 | 환경별 테스트 분리 리팩토링 | QA | Medium | 4h |
| 6 | playwright.config.ts Docker 설정 추가 | Frontend | Medium | 1h |
| 7 | CI/CD 파이프라인 E2E 단계 추가 | DevOps | Low | 3h |

---

## 5. 테스트 시나리오 커버리지 요약

### 기능별 커버리지

| 기능 영역 | 시나리오 수 | 커버리지 상태 |
|----------|------------|--------------|
| 인증/인가 | 11 | 양호 (Mock 폴백 포함) |
| API 통합 | 35 | 양호 (Docker 환경 필요) |
| 채팅 검색 | 22 | 양호 |
| 키워드 검색 | 16 | 양호 |
| 검색 필터 | 21 | 양호 |
| 대시보드 | 33 | 양호 |
| 페이지 스모크 | 33 | 양호 |
| UI-API 검증 | 12 | Docker 전용 |

### 미구현 시나리오 (향후 추가 필요)

1. **문서 업로드 E2E**: 실제 파일 업로드 → 처리 → 검색 가능 확인
2. **Knowledge Graph 시각화**: Neo4j 연동 UI 테스트
3. **실시간 알림**: WebSocket 기반 알림 테스트
4. **성능 테스트**: 동시 사용자 시뮬레이션
5. **다국어 테스트**: i18n 전환 테스트

---

## 6. 결론

현재 E2E 테스트 스위트는 **Mock 환경에서 양호하게 동작**하나, **Docker 환경에서 Rate Limiting으로 인한 실패**가 발생하고 있습니다.

### 즉시 조치 필요
1. **Rate Limit 테스트 프로파일** 추가 (Backend)
2. **Docker E2E 실행 스크립트** 작성 (DevOps/QA)

### 중기 개선
1. False Positive 패턴 제거
2. 환경별 테스트 분리
3. CI/CD 통합

---

**작성자**: TechLead
**검토자**: QA, PM
**다음 회의**: Rate Limit 해결 후 Docker E2E 테스트 검증
