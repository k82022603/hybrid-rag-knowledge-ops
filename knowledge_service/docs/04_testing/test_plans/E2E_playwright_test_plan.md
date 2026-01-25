# Playwright E2E Test Plan

**Version**: 1.0
**Created**: 2026-01-25
**Author**: QA Engineer
**Status**: Active

---

## 1. Document Overview

### 1.1 Purpose
본 문서는 Knowledge Portal Frontend의 E2E (End-to-End) 테스트 계획을 정의합니다.
Playwright를 사용하여 사용자 관점에서 전체 애플리케이션 흐름을 검증합니다.

### 1.2 Scope
| 항목 | 범위 |
|------|------|
| **테스트 대상** | Knowledge Portal Frontend (React 18) |
| **테스트 도구** | Playwright 1.58.0 |
| **브라우저** | Chromium (Desktop Chrome) |
| **환경** | Local Development (localhost:3000) |

### 1.3 Reference Documents
- [Unit/Integration Test Plan](../unit_integration_test_plan.md)
- [Frontend Architecture](../../02_design/frontend_architecture.md)
- [Playwright Official Docs](https://playwright.dev)

---

## 2. Test Environment

### 2.1 Prerequisites

| 구성 요소 | 버전 | 설명 |
|----------|------|------|
| Node.js | >= 18.0.0 | JavaScript Runtime |
| npm | >= 9.0.0 | Package Manager |
| Playwright | 1.58.0 | E2E Test Framework |
| Chromium | Latest | 테스트 브라우저 |

### 2.2 System Dependencies (WSL2/Linux)

WSL2 환경에서 Playwright를 실행하기 위한 시스템 라이브러리:

```bash
# 필수 라이브러리 설치
sudo apt-get update
sudo apt-get install -y \
    libnss3 \
    libnspr4 \
    libasound2t64 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libatspi2.0-0 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libglib2.0-0 \
    libpango-1.0-0 \
    libx11-6 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2
```

### 2.3 Playwright Configuration

```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['list'],
  ],
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
});
```

---

## 3. Test Scope

### 3.1 In Scope

| 기능 영역 | 테스트 범위 |
|----------|------------|
| **Authentication** | 로그인, 로그아웃, 세션 관리 |
| **Authorization** | 보호된 라우트 접근 제어 |
| **Form Validation** | 입력 유효성 검증 |
| **Accessibility** | WCAG 2.1 기본 접근성 |
| **Navigation** | 페이지 간 이동, 리다이렉트 |

### 3.2 Out of Scope (Phase 1)

| 기능 영역 | 제외 사유 | 예정 Phase |
|----------|----------|-----------|
| Knowledge Search | RAG 백엔드 연동 필요 | Phase 2 |
| Admin Dashboard | 관리자 기능 미구현 | Phase 2 |
| Multi-browser | Chromium 우선 | Phase 3 |
| Mobile Responsive | Desktop 우선 | Phase 3 |
| Performance Testing | k6 별도 테스트 | Phase 2 |

---

## 4. Test Cases

### 4.1 Authentication Test Suite

#### TC-AUTH-001: Login Form Display
| 항목 | 내용 |
|------|------|
| **ID** | TC-AUTH-001 |
| **Name** | 로그인 폼 표시 |
| **Priority** | Critical |
| **Precondition** | 로그인 페이지 접근 |
| **Steps** | 1. /login 페이지 접속 |
| **Expected** | 제목, 이메일 입력, 비밀번호 입력, 로그인 버튼 표시 |

#### TC-AUTH-002: Empty Field Validation
| 항목 | 내용 |
|------|------|
| **ID** | TC-AUTH-002 |
| **Name** | 빈 필드 유효성 검증 |
| **Priority** | High |
| **Precondition** | 로그인 페이지 접근 |
| **Steps** | 1. 필드 비운 상태로 로그인 버튼 클릭 |
| **Expected** | HTML5 유효성 검증 실패 메시지 |

#### TC-AUTH-003: Invalid Credentials Error
| 항목 | 내용 |
|------|------|
| **ID** | TC-AUTH-003 |
| **Name** | 잘못된 자격 증명 에러 |
| **Priority** | Critical |
| **Precondition** | 로그인 페이지 접근 |
| **Steps** | 1. 잘못된 이메일/비밀번호 입력<br/>2. 로그인 버튼 클릭 |
| **Expected** | 에러 메시지 alert 표시 |

#### TC-AUTH-004: Successful Login (Normal User)
| 항목 | 내용 |
|------|------|
| **ID** | TC-AUTH-004 |
| **Name** | 정상 로그인 (일반 사용자) |
| **Priority** | Critical |
| **Precondition** | 테스트 계정 존재 (test@example.com) |
| **Steps** | 1. 유효한 자격 증명 입력<br/>2. 로그인 버튼 클릭 |
| **Expected** | 로그인 성공 후 대시보드/홈으로 리다이렉트 |

#### TC-AUTH-005: Successful Login (Admin)
| 항목 | 내용 |
|------|------|
| **ID** | TC-AUTH-005 |
| **Name** | 정상 로그인 (관리자) |
| **Priority** | Critical |
| **Precondition** | 관리자 계정 존재 (admin@example.com) |
| **Steps** | 1. 관리자 자격 증명 입력<br/>2. 로그인 버튼 클릭 |
| **Expected** | 로그인 성공 후 리다이렉트 |

### 4.2 Remember Me Test Suite

#### TC-AUTH-006: Remember Me Checkbox
| 항목 | 내용 |
|------|------|
| **ID** | TC-AUTH-006 |
| **Name** | Remember Me 체크박스 |
| **Priority** | Medium |
| **Precondition** | 로그인 페이지 접근 |
| **Steps** | 1. 로그인 페이지에서 체크박스 확인 |
| **Expected** | Remember Me 체크박스 표시됨 |

### 4.3 Logout Test Suite

#### TC-AUTH-007: Logout and Redirect
| 항목 | 내용 |
|------|------|
| **ID** | TC-AUTH-007 |
| **Name** | 로그아웃 및 리다이렉트 |
| **Priority** | High |
| **Precondition** | 로그인 상태 |
| **Steps** | 1. 로그인 수행<br/>2. 로그아웃 버튼 클릭 |
| **Expected** | 로그아웃 후 로그인 페이지로 리다이렉트 |

### 4.4 Protected Routes Test Suite

#### TC-AUTH-008: Protected Route Redirect
| 항목 | 내용 |
|------|------|
| **ID** | TC-AUTH-008 |
| **Name** | 보호된 경로 리다이렉트 |
| **Priority** | Critical |
| **Precondition** | 비로그인 상태 |
| **Steps** | 1. /dashboard 직접 접근 시도 |
| **Expected** | 로그인 페이지로 리다이렉트 |

### 4.5 Accessibility Test Suite

#### TC-A11Y-001: Form Labels
| 항목 | 내용 |
|------|------|
| **ID** | TC-A11Y-001 |
| **Name** | 폼 라벨 접근성 |
| **Priority** | Medium |
| **Precondition** | 로그인 페이지 접근 |
| **Steps** | 1. 이메일/비밀번호 라벨 확인 |
| **Expected** | 적절한 라벨 요소 존재 |

#### TC-A11Y-002: Keyboard Navigation
| 항목 | 내용 |
|------|------|
| **ID** | TC-A11Y-002 |
| **Name** | 키보드 네비게이션 |
| **Priority** | Medium |
| **Precondition** | 로그인 페이지 접근 |
| **Steps** | 1. Tab 키로 포커스 이동 |
| **Expected** | 포커스 가능한 요소(input, button, a)로 이동 |

---

## 5. Test Data

### 5.1 Test Accounts

| 계정 유형 | Email | Password | 권한 |
|----------|-------|----------|------|
| Normal User | test@example.com | password123 | USER |
| Admin | admin@example.com | admin123! | ADMIN |
| Invalid | wrong@example.com | wrongpassword | - |

### 5.2 Test URLs

| 페이지 | URL | 접근 권한 |
|--------|-----|----------|
| Login | /login | Public |
| Dashboard | /dashboard | Authenticated |
| Home | / | Authenticated |

---

## 6. Execution Strategy

### 6.1 Test Commands

```bash
# 모든 E2E 테스트 실행
npm run test:e2e

# 브라우저 창 표시하며 실행
npm run test:e2e:headed

# Playwright UI 모드 (디버깅)
npm run test:e2e:ui

# HTML 리포트 보기
npm run test:e2e:report
```

### 6.2 Execution Schedule

| 실행 시점 | 테스트 범위 | 환경 |
|----------|-----------|------|
| Pre-commit | Smoke Test | Local |
| PR | Full Suite | CI (GitHub Actions) |
| Nightly | Full Suite + Retry | CI |

### 6.3 CI/CD Integration

```yaml
# .github/workflows/e2e-test.yml (예시)
- name: Install dependencies
  run: npm ci
  working-directory: knowledge_service/frontend

- name: Install Playwright browsers
  run: npx playwright install chromium --with-deps
  working-directory: knowledge_service/frontend

- name: Run E2E tests
  run: npm run test:e2e
  working-directory: knowledge_service/frontend
```

---

## 7. Quality Gates

### 7.1 Pass Criteria

| Metric | Threshold | 현재 상태 |
|--------|-----------|----------|
| Test Pass Rate | 100% | 100% (10/10) |
| Critical Tests | All Pass | Pass |
| No Flaky Tests | 0 flaky | 0 |

### 7.2 Exit Criteria

- 모든 Critical 우선순위 테스트 통과
- High 우선순위 테스트 95% 이상 통과
- 테스트 리포트 생성 및 공유

---

## 8. Risk Assessment

### 8.1 Identified Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| 환경 의존성 | High | Medium | Docker 환경 표준화 |
| 네트워크 지연 | Medium | Low | timeout 설정 조정 |
| 테스트 데이터 불일치 | Medium | Medium | 테스트 격리, Mock 사용 |
| WSL2 호환성 | Medium | Low | 시스템 의존성 문서화 |

### 8.2 Mitigation Strategies

1. **환경 의존성**: Playwright 설정에 webServer 옵션으로 자동 서버 시작
2. **네트워크 지연**: 적절한 timeout 설정 (10초)
3. **테스트 데이터**: Mock 인증 서비스 사용
4. **WSL2 호환성**: 설치 매뉴얼에 시스템 의존성 명시

---

## 9. Future Enhancements (Phase 2+)

### 9.1 Phase 2 계획

- [ ] Knowledge Search E2E 테스트
- [ ] RAG 응답 품질 E2E 검증
- [ ] Admin Dashboard 테스트
- [ ] k6 성능 테스트 통합

### 9.2 Phase 3 계획

- [ ] Multi-browser 테스트 (Firefox, Safari)
- [ ] Mobile Responsive 테스트
- [ ] Visual Regression 테스트
- [ ] Accessibility Audit (axe-core)

---

## 10. Appendix

### 10.1 Test File Structure

```
knowledge_service/frontend/
├── e2e/
│   └── auth.spec.ts          # Authentication E2E Tests
├── playwright.config.ts       # Playwright Configuration
├── playwright-report/         # HTML Test Reports (generated)
└── package.json              # npm scripts
```

### 10.2 Related npm Scripts

```json
{
  "scripts": {
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui",
    "test:e2e:headed": "playwright test --headed",
    "test:e2e:report": "playwright show-report"
  }
}
```

---

**Document Control**

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 1.0 | 2026-01-25 | QA Engineer | Initial creation |
