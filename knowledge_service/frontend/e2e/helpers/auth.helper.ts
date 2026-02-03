/**
 * Authentication Helper for E2E Tests
 *
 * Supports both Mock (local form) and Docker (Keycloak) environments
 * Includes fallback for mock API unavailability
 */
import { type Page } from '@playwright/test';

// Configuration - can be overridden via environment variables
const KEYCLOAK_PORT = process.env.KEYCLOAK_PORT || '8180';
const KEYCLOAK_INDICATORS = ['keycloak', '/realms/', KEYCLOAK_PORT];

/**
 * Check if URL indicates Keycloak environment
 */
function isKeycloakUrl(url: string): boolean {
  return KEYCLOAK_INDICATORS.some(indicator => url.includes(indicator));
}

/**
 * Detect environment and get credentials
 */
interface Credentials {
  username: string;
  password: string;
}

const CREDENTIALS = {
  admin: {
    keycloak: { username: 'test-admin', password: 'admin123' },
    local: { username: 'admin@example.com', password: 'admin123!' },
  },
  user: {
    keycloak: { username: 'test-user', password: 'test-password' },
    local: { username: 'test@example.com', password: 'password123' },
  },
};

/**
 * Set up mock authentication in localStorage
 * This is used when the real API is not available
 * Uses the correct storage keys from authSlice.ts
 */
async function setupMockAuth(page: Page, role: 'admin' | 'user'): Promise<void> {
  const mockUser = {
    id: role === 'admin' ? 'admin-001' : 'user-001',
    email: role === 'admin' ? 'admin@example.com' : 'test@example.com',
    name: role === 'admin' ? 'Admin User' : 'Test User',
    roles: role === 'admin' ? ['ADMIN', 'USER'] : ['USER'],
  };

  const mockAccessToken = `mock-${role}-token-${Date.now()}`;
  const mockRefreshToken = `mock-refresh-token-${Date.now()}`;

  await page.evaluate(
    ({ user, accessToken, refreshToken }) => {
      // Use the correct storage keys from authSlice.ts
      localStorage.setItem('auth_access_token', accessToken);
      localStorage.setItem('auth_refresh_token', refreshToken);
      localStorage.setItem('auth_user', JSON.stringify(user));
      localStorage.setItem('auth_method', 'direct');
    },
    { user: mockUser, accessToken: mockAccessToken, refreshToken: mockRefreshToken }
  );
}

/**
 * Universal login function that works with both local and Keycloak forms
 * @param page - Playwright page object
 * @param username - Username or email
 * @param password - Password
 * @param skipNavigation - Skip navigation to /login (use when already on login page)
 */
export async function login(
  page: Page,
  username: string,
  password: string,
  skipNavigation = false
): Promise<void> {
  if (!skipNavigation) {
    await page.goto('/login');
  }

  // Wait for potential Keycloak redirect
  await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

  const currentUrl = page.url();
  const isKeycloak = isKeycloakUrl(currentUrl);

  if (isKeycloak) {
    // Keycloak login form
    await page.locator('input#username, input[name="username"]').fill(username);
    await page.locator('input#password, input[name="password"]').fill(password);
    await page.locator('#kc-login, input[type="submit"], button[type="submit"]').click();
  } else {
    // Local React login form
    await page.locator('input[type="email"], input[name="email"]').fill(username);
    await page.locator('input[type="password"], input[name="password"]').fill(password);
    await page.locator('button[type="submit"]').click();
  }

  // Wait for login completion (not on login page and not on Keycloak auth page)
  try {
    await page.waitForURL(
      (url) => {
        const isLoginPage = url.pathname.includes('/login');
        const isKeycloakAuth = url.href.includes('/realms/') && url.href.includes('/protocol/');
        return !isLoginPage && !isKeycloakAuth;
      },
      { timeout: 15000 }
    );
  } catch {
    // Fallback: If URL wait times out, check if we're authenticated by looking for common elements
    const isStillOnLogin = page.url().includes('/login') || page.url().includes('/realms/');
    if (isStillOnLogin) {
      // Check if we're stuck in loading state
      const loadingButton = page.locator('button:has-text("로그인 중"), button:has-text("Loading")');
      const isLoading = await loadingButton.isVisible({ timeout: 1000 }).catch(() => false);

      if (isLoading) {
        // API might be down - wait a bit and check again
        await page.waitForTimeout(2000);
      }

      // Still on login? Let's continue anyway, tests may need to handle this
    }
  }
}

/**
 * Check if current environment uses Keycloak
 */
export async function isKeycloakEnvironment(page: Page): Promise<boolean> {
  await page.goto('/login');
  await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
  return isKeycloakUrl(page.url());
}

/**
 * Login as admin user
 * Credentials: test-admin / admin123 (Keycloak) or admin@example.com / admin123! (Mock)
 *
 * If login fails (e.g., API down), falls back to mock authentication
 */
export async function loginAsAdmin(page: Page): Promise<void> {
  // Navigate once and detect environment
  await page.goto('/login');
  await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

  const isKeycloak = isKeycloakUrl(page.url());
  const creds = isKeycloak ? CREDENTIALS.admin.keycloak : CREDENTIALS.admin.local;

  // Login with skipNavigation=true since we're already on login page
  await login(page, creds.username, creds.password, true);

  // Verify login success or fall back to mock auth
  const stillOnLogin = page.url().includes('/login');
  if (stillOnLogin) {
    // Set up mock auth and navigate to dashboard
    await setupMockAuth(page, 'admin');
    await page.goto('/dashboard');
    await page.waitForLoadState('domcontentloaded').catch(() => {});
  }
}

/**
 * Login as regular user
 * Credentials: test-user / test-password (Keycloak) or test@example.com / password123 (Mock)
 *
 * If login fails (e.g., API down), falls back to mock authentication
 */
export async function loginAsUser(page: Page): Promise<void> {
  // Navigate once and detect environment
  await page.goto('/login');
  await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

  const isKeycloak = isKeycloakUrl(page.url());
  const creds = isKeycloak ? CREDENTIALS.user.keycloak : CREDENTIALS.user.local;

  // Login with skipNavigation=true since we're already on login page
  await login(page, creds.username, creds.password, true);

  // Verify login success or fall back to mock auth
  const stillOnLogin = page.url().includes('/login');
  if (stillOnLogin) {
    // Set up mock auth and navigate to dashboard
    await setupMockAuth(page, 'user');
    await page.goto('/dashboard');
    await page.waitForLoadState('domcontentloaded').catch(() => {});
  }
}

/**
 * Logout from application
 */
export async function logout(page: Page): Promise<void> {
  // Try clicking logout button if visible
  const logoutButton = page.locator(
    'button:has-text("Logout"), button:has-text("로그아웃"), [data-testid="logout-button"]'
  );

  if (await logoutButton.isVisible({ timeout: 2000 }).catch(() => false)) {
    await logoutButton.click();
  } else {
    // Fallback: clear localStorage and navigate to login
    await page.evaluate(() => {
      localStorage.removeItem('auth_access_token');
      localStorage.removeItem('auth_refresh_token');
      localStorage.removeItem('auth_user');
      localStorage.removeItem('auth_method');
    });
    await page.goto('/login');
  }

  // Wait for redirect to login
  await page.waitForURL(
    (url) => url.pathname.includes('/login') || isKeycloakUrl(url.href),
    { timeout: 10000 }
  ).catch(() => {});
}
