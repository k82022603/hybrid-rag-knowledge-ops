# Playwright E2E Testing Setup Guide

**Version**: 1.0
**Created**: 2026-01-25
**Author**: QA Engineer
**Target**: Knowledge Portal Frontend Developers

---

## 1. Overview

### 1.1 What is Playwright?

Playwright는 Microsoft가 개발한 E2E (End-to-End) 테스트 프레임워크입니다.
Chromium, Firefox, WebKit을 지원하며, 단일 API로 크로스 브라우저 테스트가 가능합니다.

### 1.2 Why Playwright?

| 특징 | 설명 |
|------|------|
| **Auto-waiting** | 요소가 액션 가능할 때까지 자동 대기 |
| **Web-first assertions** | 요소 상태 자동 재시도 |
| **Tracing** | 실패 시 상세 트레이스 제공 |
| **Codegen** | 브라우저 조작을 코드로 자동 생성 |
| **Isolation** | 각 테스트가 완전히 격리됨 |

### 1.3 Project Structure

```
knowledge_service/frontend/
├── e2e/                       # E2E 테스트 디렉토리
│   └── auth.spec.ts           # 인증 테스트
├── playwright.config.ts       # Playwright 설정
├── playwright-report/         # HTML 리포트 (자동 생성)
└── package.json              # npm scripts
```

---

## 2. Installation

### 2.1 Prerequisites

| 요구사항 | 버전 | 확인 방법 |
|---------|------|----------|
| Node.js | >= 18.0.0 | `node --version` |
| npm | >= 9.0.0 | `npm --version` |
| WSL2 (optional) | - | Windows 사용자용 |

### 2.2 Step 1: npm Package Installation

```bash
# 프로젝트 디렉토리로 이동
cd knowledge_service/frontend

# Playwright 설치 (devDependency)
npm install -D @playwright/test
```

**package.json에 추가됨**:
```json
{
  "devDependencies": {
    "@playwright/test": "^1.58.0"
  }
}
```

### 2.3 Step 2: Browser Installation

```bash
# Chromium만 설치 (권장 - 빠른 설치)
npx playwright install chromium

# 모든 브라우저 설치 (선택)
npx playwright install

# 브라우저 + 시스템 의존성 함께 설치 (root 권한 필요)
npx playwright install chromium --with-deps
```

### 2.4 Step 3: System Dependencies (WSL2/Linux)

WSL2 또는 Linux 환경에서는 추가 시스템 라이브러리가 필요합니다.

```bash
# Ubuntu/Debian 기반 (WSL2 포함)
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

**의존성 설명**:

| 패키지 | 용도 |
|--------|------|
| libnss3, libnspr4 | Mozilla NSS 라이브러리 (SSL/TLS) |
| libasound2t64 | ALSA 오디오 라이브러리 |
| libatk1.0-0, libatk-bridge2.0-0 | 접근성 도구킷 |
| libatspi2.0-0 | AT-SPI (보조 기술 서비스) |
| libcairo2 | 2D 그래픽 라이브러리 |
| libcups2 | 프린팅 시스템 |
| libdbus-1-3 | D-Bus 메시지 버스 |
| libdrm2 | Direct Rendering Manager |
| libgbm1 | Generic Buffer Management |
| libglib2.0-0 | GLib 유틸리티 라이브러리 |
| libpango-1.0-0 | 텍스트 렌더링 |
| libx11-6, libxcb1 | X Window System |
| libxcomposite1 | X Composite 확장 |
| libxdamage1 | X Damage 확장 |
| libxext6 | X 확장 라이브러리 |
| libxfixes3 | X Fixes 확장 |
| libxkbcommon0 | XKB 공통 라이브러리 |
| libxrandr2 | X RandR 확장 |

---

## 3. Configuration

### 3.1 playwright.config.ts

```typescript
import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E Test Configuration
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  // 테스트 파일 위치
  testDir: './e2e',

  // 병렬 실행
  fullyParallel: true,

  // CI에서 test.only 금지
  forbidOnly: !!process.env.CI,

  // CI에서 재시도 횟수
  retries: process.env.CI ? 2 : 0,

  // CI에서 worker 수
  workers: process.env.CI ? 1 : undefined,

  // 리포터 설정
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['list'],
  ],

  // 전역 설정
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  // 브라우저 프로젝트
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  // 개발 서버 자동 시작
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
});
```

### 3.2 npm Scripts

**package.json**:
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

## 4. Running Tests

### 4.1 Basic Commands

```bash
# 모든 E2E 테스트 실행 (headless)
npm run test:e2e

# 브라우저 창 표시하며 실행
npm run test:e2e:headed

# Playwright UI 모드 (디버깅용)
npm run test:e2e:ui

# HTML 리포트 보기
npm run test:e2e:report
```

### 4.2 Advanced Commands

```bash
# 특정 테스트 파일만 실행
npx playwright test e2e/auth.spec.ts

# 특정 테스트만 실행 (grep)
npx playwright test -g "should display login form"

# 디버그 모드
npx playwright test --debug

# 특정 브라우저만 실행
npx playwright test --project=chromium

# 병렬 워커 수 지정
npx playwright test --workers=4

# 재시도 횟수 지정
npx playwright test --retries=3
```

### 4.3 Code Generation (Codegen)

Playwright의 강력한 기능 중 하나인 Codegen을 사용하면 브라우저 조작을 코드로 자동 생성할 수 있습니다.

```bash
# 코드 생성기 실행
npx playwright codegen http://localhost:3000

# 특정 파일에 저장
npx playwright codegen http://localhost:3000 -o e2e/new-test.spec.ts
```

---

## 5. Writing Tests

### 5.1 Basic Test Structure

```typescript
import { test, expect } from '@playwright/test';

test.describe('Test Suite Name', () => {
  // 각 테스트 전 실행
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
  });

  test('test case name', async ({ page }) => {
    // 요소 찾기
    const button = page.locator('button[type="submit"]');

    // 액션
    await button.click();

    // 검증
    await expect(button).toBeVisible();
  });
});
```

### 5.2 Common Locators

```typescript
// CSS Selector
page.locator('button.submit-btn')

// Text
page.locator('text=Login')
page.getByText('Login')

// Role
page.getByRole('button', { name: 'Login' })

// Label
page.getByLabel('Email')

// Placeholder
page.getByPlaceholder('Enter your email')

// Test ID (권장)
page.getByTestId('login-button')

// XPath (가급적 사용 자제)
page.locator('//button[@type="submit"]')
```

### 5.3 Common Actions

```typescript
// 클릭
await page.click('button');
await button.click();

// 입력
await page.fill('input[name="email"]', 'test@example.com');
await emailInput.fill('test@example.com');

// 키보드
await page.keyboard.press('Tab');
await page.keyboard.press('Enter');

// 네비게이션
await page.goto('/dashboard');
await page.goBack();

// 대기
await page.waitForURL('**/dashboard');
await page.waitForSelector('.loading', { state: 'hidden' });
```

### 5.4 Common Assertions

```typescript
// 가시성
await expect(element).toBeVisible();
await expect(element).toBeHidden();

// 텍스트
await expect(element).toHaveText('Hello');
await expect(element).toContainText('Hello');

// 속성
await expect(element).toHaveAttribute('href', '/home');
await expect(element).toHaveClass('active');

// 입력값
await expect(input).toHaveValue('test@example.com');

// URL
await expect(page).toHaveURL('/dashboard');
await expect(page).toHaveURL(/.*dashboard.*/);

// 타이틀
await expect(page).toHaveTitle('Knowledge Portal');
```

---

## 6. Debugging

### 6.1 Debug Mode

```bash
# 디버그 모드로 실행
npx playwright test --debug

# 특정 테스트만 디버그
npx playwright test -g "login" --debug
```

### 6.2 Pause in Test

```typescript
test('debug example', async ({ page }) => {
  await page.goto('/login');

  // 여기서 일시 정지 (Inspector 열림)
  await page.pause();

  await page.fill('input[name="email"]', 'test@example.com');
});
```

### 6.3 Trace Viewer

테스트 실패 시 생성된 trace 파일을 확인할 수 있습니다.

```bash
# Trace 파일 열기
npx playwright show-trace trace.zip
```

### 6.4 Screenshots and Videos

설정에 따라 자동으로 캡처되지만, 수동으로도 가능합니다.

```typescript
test('screenshot example', async ({ page }) => {
  await page.goto('/login');

  // 스크린샷 저장
  await page.screenshot({ path: 'screenshot.png' });

  // 전체 페이지 스크린샷
  await page.screenshot({ path: 'full-page.png', fullPage: true });
});
```

---

## 7. CI/CD Integration

### 7.1 GitHub Actions Example

```yaml
name: E2E Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  e2e:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: knowledge_service/frontend/package-lock.json

      - name: Install dependencies
        run: npm ci
        working-directory: knowledge_service/frontend

      - name: Install Playwright browsers
        run: npx playwright install chromium --with-deps
        working-directory: knowledge_service/frontend

      - name: Run E2E tests
        run: npm run test:e2e
        working-directory: knowledge_service/frontend

      - name: Upload test report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: playwright-report
          path: knowledge_service/frontend/playwright-report/
          retention-days: 30
```

### 7.2 Docker Example

```dockerfile
FROM mcr.microsoft.com/playwright:v1.58.0-jammy

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

CMD ["npm", "run", "test:e2e"]
```

---

## 8. Best Practices

### 8.1 Test Organization

```typescript
// Good: 명확한 describe/test 구조
test.describe('Authentication', () => {
  test.describe('Login', () => {
    test('should display login form', async ({ page }) => { });
    test('should login successfully', async ({ page }) => { });
  });

  test.describe('Logout', () => {
    test('should logout and redirect', async ({ page }) => { });
  });
});
```

### 8.2 Use Test IDs

```tsx
// React Component
<button data-testid="login-button">Login</button>

// Playwright Test
const button = page.getByTestId('login-button');
```

### 8.3 Avoid Flaky Tests

```typescript
// Bad: 고정된 timeout
await page.waitForTimeout(5000);

// Good: 조건 기반 대기
await page.waitForSelector('.loading', { state: 'hidden' });
await expect(page.locator('.content')).toBeVisible();
```

### 8.4 Test Isolation

```typescript
// 각 테스트는 독립적이어야 함
test.beforeEach(async ({ page }) => {
  // 초기 상태 설정
  await page.goto('/login');
});

test.afterEach(async ({ page }) => {
  // 정리 (필요시)
  await page.evaluate(() => localStorage.clear());
});
```

---

## 9. Troubleshooting

### 9.1 Common Issues

#### Issue 1: Browser launch failed

**증상**:
```
Error: browserType.launch: Executable doesn't exist at ...
```

**해결**:
```bash
npx playwright install chromium
```

#### Issue 2: Missing system dependencies (WSL2)

**증상**:
```
error while loading shared libraries: libnss3.so: cannot open shared object file
```

**해결**:
```bash
sudo apt-get install -y libnss3 libnspr4
```

#### Issue 3: Timeout waiting for element

**증상**:
```
Error: Timeout 30000ms exceeded.
```

**해결**:
```typescript
// timeout 늘리기
await expect(element).toBeVisible({ timeout: 60000 });

// 또는 전역 설정
// playwright.config.ts
use: {
  actionTimeout: 60000,
}
```

#### Issue 4: Port already in use

**증상**:
```
Error: listen EADDRINUSE :::3000
```

**해결**:
```bash
# 기존 프로세스 종료
lsof -ti:3000 | xargs kill -9

# 또는 다른 포트 사용
# playwright.config.ts
webServer: {
  command: 'PORT=3001 npm run dev',
  url: 'http://localhost:3001',
}
```

### 9.2 Debug Checklist

1. [ ] 브라우저 설치 확인: `npx playwright install chromium`
2. [ ] 시스템 의존성 확인 (WSL2)
3. [ ] 개발 서버 실행 확인: `npm run dev`
4. [ ] 네트워크 연결 확인
5. [ ] 테스트 격리 확인 (상태 의존성)

---

## 10. Resources

### 10.1 Official Documentation

- [Playwright Docs](https://playwright.dev/docs/intro)
- [API Reference](https://playwright.dev/docs/api/class-playwright)
- [Best Practices](https://playwright.dev/docs/best-practices)

### 10.2 Project References

- [E2E Test Plan](../04_testing/test_plans/E2E_playwright_test_plan.md)
- [E2E Test Results](../04_testing/test_results/E2E_playwright_test_result.md)
- [Frontend Architecture](../02_design/frontend_architecture.md)

### 10.3 Useful Commands Summary

| Command | Description |
|---------|-------------|
| `npm run test:e2e` | 전체 E2E 테스트 실행 |
| `npm run test:e2e:headed` | 브라우저 표시하며 실행 |
| `npm run test:e2e:ui` | UI 모드로 실행 |
| `npm run test:e2e:report` | HTML 리포트 열기 |
| `npx playwright codegen` | 코드 자동 생성 |
| `npx playwright test --debug` | 디버그 모드 |

---

**Document Control**

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 1.0 | 2026-01-25 | QA Engineer | Initial creation |
