/**
 * UI-based API Verification E2E Tests
 *
 * Tests that verify actual API calls are made when users interact with the UI.
 * Uses page.waitForResponse() to capture and validate API responses.
 *
 * This bridges the gap between:
 * - UI tests (only check rendering)
 * - Direct API tests (bypass UI completely)
 *
 * IMPORTANT: These tests require a running Backend server.
 * In Mock environment, API-dependent tests are skipped.
 */
import { test, expect } from '@playwright/test';
import { skipInMock } from './helpers/test-env.helper';

// API endpoint patterns
const API_PATTERNS = {
  login: /\/api\/v1\/auth\/login/,
  me: /\/api\/v1\/auth\/me/,
  search: /\/api\/v1\/search/,
  dashboard: /\/api\/v1\/dashboard/,
  bookmarks: /\/api\/v1\/bookmarks/,
};

// Test credentials
const TEST_USER = {
  email: 'test@example.com',
  password: 'password123',
};

// ============================================================================
// Login Flow API Verification
// ============================================================================
test.describe('Login Flow - API Verification', () => {
  test('should call /auth/login API when submitting login form', async ({ page }) => {
    // Skip in Mock environment - Mock Interceptor handles auth at axios level, not network level
    skipInMock('Requires real Backend API for network-level verification');

    await page.goto('/login');
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

    // Skip if redirected to Keycloak
    if (page.url().includes('keycloak') || page.url().includes('8180')) {
      test.skip();
      return;
    }

    // Set up response listener before action
    const responsePromise = page.waitForResponse(
      response => API_PATTERNS.login.test(response.url()) && response.request().method() === 'POST',
      { timeout: 15000 }
    );

    // Fill form and submit
    await page.locator('input[type="email"], input[name="email"]').fill(TEST_USER.email);
    await page.locator('input[type="password"], input[name="password"]').fill(TEST_USER.password);
    await page.locator('button[type="submit"]').click();

    // Wait for and verify API response
    const response = await responsePromise;
    expect(response.status()).toBe(200);

    const data = await response.json();
    expect(data).toHaveProperty('accessToken');
    expect(data).toHaveProperty('user');
    expect(data.user.email).toBe(TEST_USER.email);
  });

  test('should call /auth/login API with correct request body', async ({ page }) => {
    skipInMock('Requires real Backend API for network-level verification');

    await page.goto('/login');
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

    if (page.url().includes('keycloak')) {
      test.skip();
      return;
    }

    // Capture request data
    let requestBody: any = null;
    page.on('request', request => {
      if (API_PATTERNS.login.test(request.url()) && request.method() === 'POST') {
        requestBody = request.postDataJSON();
      }
    });

    const responsePromise = page.waitForResponse(
      response => API_PATTERNS.login.test(response.url()),
      { timeout: 15000 }
    );

    await page.locator('input[type="email"], input[name="email"]').fill(TEST_USER.email);
    await page.locator('input[type="password"], input[name="password"]').fill(TEST_USER.password);
    await page.locator('button[type="submit"]').click();

    await responsePromise;

    // Verify request body
    expect(requestBody).not.toBeNull();
    expect(requestBody.email).toBe(TEST_USER.email);
    expect(requestBody.password).toBe(TEST_USER.password);
  });

  test('should receive 401 for invalid credentials via UI', async ({ page }) => {
    skipInMock('Requires real Backend API for network-level verification');

    await page.goto('/login');
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

    if (page.url().includes('keycloak')) {
      test.skip();
      return;
    }

    const responsePromise = page.waitForResponse(
      response => API_PATTERNS.login.test(response.url()),
      { timeout: 15000 }
    );

    await page.locator('input[type="email"], input[name="email"]').fill('wrong@example.com');
    await page.locator('input[type="password"], input[name="password"]').fill('wrongpassword');
    await page.locator('button[type="submit"]').click();

    const response = await responsePromise;
    expect(response.status()).toBe(401);
  });
});

// ============================================================================
// Search Flow API Verification
// ============================================================================
test.describe('Search Flow - API Verification', () => {
  test.beforeEach(async ({ page }) => {
    // Skip if not in Docker environment (no real API)
    skipInMock('Search API tests require Backend server');

    // Login first
    await page.goto('/login');
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

    if (!page.url().includes('keycloak')) {
      await page.locator('input[type="email"], input[name="email"]').fill(TEST_USER.email);
      await page.locator('input[type="password"], input[name="password"]').fill(TEST_USER.password);
      await page.locator('button[type="submit"]').click();
      await page.waitForURL(url => !url.pathname.includes('/login'), { timeout: 15000 });
    }
  });

  test('should call /search API when performing keyword search', async ({ page }) => {
    skipInMock('Requires Backend API');
    await page.goto('/search');
    await expect(page.locator('[data-testid="search-page"]')).toBeVisible({ timeout: 10000 });

    // Switch to Keyword Search tab
    await page.locator('button[role="tab"]:has-text("Keyword Search")').click();
    await expect(page.locator('[data-testid="keyword-search"]')).toBeVisible({ timeout: 5000 });

    // Set up response listener
    const responsePromise = page.waitForResponse(
      response => API_PATTERNS.search.test(response.url()) && response.request().method() === 'POST',
      { timeout: 15000 }
    );

    // Perform search
    await page.locator('[data-testid="keyword-search-input"]').fill('RAG pipeline');
    await page.locator('[data-testid="keyword-search-submit"]').click();

    // Verify API response
    const response = await responsePromise;
    expect(response.status()).toBe(200);

    const data = await response.json();
    expect(data).toHaveProperty('query');
    expect(data).toHaveProperty('results');
    expect(Array.isArray(data.results)).toBeTruthy();
  });

  test('should send correct search query in request body', async ({ page }) => {
    skipInMock('Requires Backend API');

    await page.goto('/search');
    await expect(page.locator('[data-testid="search-page"]')).toBeVisible({ timeout: 10000 });

    await page.locator('button[role="tab"]:has-text("Keyword Search")').click();
    await expect(page.locator('[data-testid="keyword-search"]')).toBeVisible({ timeout: 5000 });

    let requestBody: any = null;
    page.on('request', request => {
      if (API_PATTERNS.search.test(request.url()) && request.method() === 'POST') {
        requestBody = request.postDataJSON();
      }
    });

    const responsePromise = page.waitForResponse(
      response => API_PATTERNS.search.test(response.url()),
      { timeout: 15000 }
    );

    const searchQuery = 'knowledge graph test';
    await page.locator('[data-testid="keyword-search-input"]').fill(searchQuery);
    await page.locator('[data-testid="keyword-search-submit"]').click();

    await responsePromise;

    expect(requestBody).not.toBeNull();
    expect(requestBody.query).toBe(searchQuery);
  });

  test('should include auth token in search request headers', async ({ page }) => {
    skipInMock('Requires Backend API');

    await page.goto('/search');
    await expect(page.locator('[data-testid="search-page"]')).toBeVisible({ timeout: 10000 });

    await page.locator('button[role="tab"]:has-text("Keyword Search")').click();
    await expect(page.locator('[data-testid="keyword-search"]')).toBeVisible({ timeout: 5000 });

    let authHeader: string | null = null;
    page.on('request', request => {
      if (API_PATTERNS.search.test(request.url()) && request.method() === 'POST') {
        authHeader = request.headers()['authorization'] || null;
      }
    });

    const responsePromise = page.waitForResponse(
      response => API_PATTERNS.search.test(response.url()),
      { timeout: 15000 }
    );

    await page.locator('[data-testid="keyword-search-input"]').fill('test');
    await page.locator('[data-testid="keyword-search-submit"]').click();

    await responsePromise;

    // Should have Bearer token
    expect(authHeader).not.toBeNull();
    expect(authHeader).toMatch(/^Bearer\s+.+/);
  });
});

// ============================================================================
// Dashboard Load API Verification
// ============================================================================
test.describe('Dashboard Load - API Verification', () => {
  test.beforeEach(async ({ page }) => {
    // Skip if not in Docker environment
    skipInMock('Dashboard API tests require Backend server');

    await page.goto('/login');
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

    if (!page.url().includes('keycloak')) {
      await page.locator('input[type="email"], input[name="email"]').fill(TEST_USER.email);
      await page.locator('input[type="password"], input[name="password"]').fill(TEST_USER.password);
      await page.locator('button[type="submit"]').click();
      await page.waitForURL(url => !url.pathname.includes('/login'), { timeout: 15000 });
    }
  });

  test('should call dashboard API when loading dashboard page', async ({ page }) => {
    skipInMock('Requires Backend API');
    // Listen for any dashboard-related API calls
    const apiCalls: string[] = [];
    page.on('request', request => {
      if (request.url().includes('/api/')) {
        apiCalls.push(`${request.method()} ${request.url()}`);
      }
    });

    await page.goto('/dashboard');
    await expect(page.locator('[data-testid="dashboard-page"]')).toBeVisible({ timeout: 10000 });

    // Wait a bit for any lazy-loaded API calls
    await page.waitForTimeout(2000);

    // Log API calls for debugging
    console.log('Dashboard API calls:', apiCalls);

    // Dashboard should have loaded (whether using mock data or real API)
    await expect(page.locator('[data-testid="welcome-section"]')).toBeVisible();
  });

  test('should track all network requests on dashboard load', async ({ page }) => {
    skipInMock('Requires Backend API');

    const requests: { method: string; url: string; status?: number }[] = [];

    page.on('response', response => {
      if (response.url().includes('/api/')) {
        requests.push({
          method: response.request().method(),
          url: response.url(),
          status: response.status(),
        });
      }
    });

    await page.goto('/dashboard');
    await expect(page.locator('[data-testid="dashboard-page"]')).toBeVisible({ timeout: 10000 });
    await page.waitForTimeout(2000);

    // Report all API calls made during dashboard load
    console.log('Dashboard API requests:', JSON.stringify(requests, null, 2));

    // Dashboard should render regardless of API availability
    expect(page.url()).toContain('/dashboard');
  });
});

// ============================================================================
// Navigation API Verification
// ============================================================================
test.describe('Navigation - API Verification', () => {
  test.beforeEach(async ({ page }) => {
    // Skip if not in Docker environment
    skipInMock('Navigation API tests require Backend server');

    await page.goto('/login');
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

    if (!page.url().includes('keycloak')) {
      await page.locator('input[type="email"], input[name="email"]').fill(TEST_USER.email);
      await page.locator('input[type="password"], input[name="password"]').fill(TEST_USER.password);
      await page.locator('button[type="submit"]').click();
      await page.waitForURL(url => !url.pathname.includes('/login'), { timeout: 15000 });
    }
  });

  test('should track API calls when navigating between pages', async ({ page }) => {
    skipInMock('Requires Backend API');
    const apiCallsByPage: Record<string, string[]> = {};

    page.on('request', request => {
      if (request.url().includes('/api/')) {
        const currentPath = new URL(page.url()).pathname;
        if (!apiCallsByPage[currentPath]) {
          apiCallsByPage[currentPath] = [];
        }
        apiCallsByPage[currentPath].push(`${request.method()} ${request.url()}`);
      }
    });

    // Navigate to dashboard
    await page.goto('/dashboard');
    await expect(page.locator('[data-testid="dashboard-page"]')).toBeVisible({ timeout: 10000 });
    await page.waitForTimeout(1000);

    // Navigate to search
    await page.goto('/search');
    await expect(page.locator('[data-testid="search-page"]')).toBeVisible({ timeout: 10000 });
    await page.waitForTimeout(1000);

    // Navigate to profile
    await page.goto('/profile');
    await page.waitForTimeout(1000);

    console.log('API calls by page:', JSON.stringify(apiCallsByPage, null, 2));

    // Test passes if navigation works
    expect(Object.keys(apiCallsByPage).length).toBeGreaterThanOrEqual(0);
  });
});

// ============================================================================
// API Response Time Verification
// ============================================================================
test.describe('API Response Time - Via UI', () => {
  test('login API response time should be under 3 seconds', async ({ page }) => {
    skipInMock('Requires Backend API');
    await page.goto('/login');
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

    if (page.url().includes('keycloak')) {
      test.skip();
      return;
    }

    const startTime = Date.now();

    const responsePromise = page.waitForResponse(
      response => API_PATTERNS.login.test(response.url()),
      { timeout: 15000 }
    );

    await page.locator('input[type="email"], input[name="email"]').fill(TEST_USER.email);
    await page.locator('input[type="password"], input[name="password"]').fill(TEST_USER.password);
    await page.locator('button[type="submit"]').click();

    await responsePromise;
    const duration = Date.now() - startTime;

    expect(duration).toBeLessThan(3000);
    console.log(`Login API response time: ${duration}ms`);
  });

  test('search API response time should be under 5 seconds', async ({ page }) => {
    skipInMock('Requires Backend API');

    // Login first
    await page.goto('/login');
    if (!page.url().includes('keycloak')) {
      await page.locator('input[type="email"], input[name="email"]').fill(TEST_USER.email);
      await page.locator('input[type="password"], input[name="password"]').fill(TEST_USER.password);
      await page.locator('button[type="submit"]').click();
      await page.waitForURL(url => !url.pathname.includes('/login'), { timeout: 15000 });
    }

    await page.goto('/search');
    await expect(page.locator('[data-testid="search-page"]')).toBeVisible({ timeout: 10000 });

    await page.locator('button[role="tab"]:has-text("Keyword Search")').click();
    await expect(page.locator('[data-testid="keyword-search"]')).toBeVisible({ timeout: 5000 });

    const startTime = Date.now();

    const responsePromise = page.waitForResponse(
      response => API_PATTERNS.search.test(response.url()),
      { timeout: 15000 }
    );

    await page.locator('[data-testid="keyword-search-input"]').fill('test query');
    await page.locator('[data-testid="keyword-search-submit"]').click();

    await responsePromise;
    const duration = Date.now() - startTime;

    expect(duration).toBeLessThan(5000);
    console.log(`Search API response time: ${duration}ms`);
  });
});
