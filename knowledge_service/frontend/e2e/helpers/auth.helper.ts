/**
 * Authentication Helper for E2E Tests
 *
 * Supports both Mock (local form) and Docker (Keycloak) environments
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
    local: { username: 'admin@example.com', password: 'admin123' },
  },
  user: {
    keycloak: { username: 'test-user', password: 'test-password' },
    local: { username: 'test@example.com', password: 'password123' },
  },
};

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
  await page.waitForURL(
    (url) => {
      const isLoginPage = url.pathname.includes('/login');
      const isKeycloakAuth = url.href.includes('/realms/') && url.href.includes('/protocol/');
      return !isLoginPage && !isKeycloakAuth;
    },
    { timeout: 15000 }
  );
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
 * Credentials: test-admin / admin123 (Keycloak) or admin@example.com / admin123 (Mock)
 */
export async function loginAsAdmin(page: Page): Promise<void> {
  // Navigate once and detect environment
  await page.goto('/login');
  await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

  const isKeycloak = isKeycloakUrl(page.url());
  const creds = isKeycloak ? CREDENTIALS.admin.keycloak : CREDENTIALS.admin.local;

  // Login with skipNavigation=true since we're already on login page
  await login(page, creds.username, creds.password, true);
}

/**
 * Login as regular user
 * Credentials: test-user / test-password (Keycloak) or test@example.com / password123 (Mock)
 */
export async function loginAsUser(page: Page): Promise<void> {
  // Navigate once and detect environment
  await page.goto('/login');
  await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

  const isKeycloak = isKeycloakUrl(page.url());
  const creds = isKeycloak ? CREDENTIALS.user.keycloak : CREDENTIALS.user.local;

  // Login with skipNavigation=true since we're already on login page
  await login(page, creds.username, creds.password, true);
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
    // Fallback: navigate to logout endpoint
    await page.goto('/logout');
  }

  // Wait for redirect to login
  await page.waitForURL(
    (url) => url.pathname.includes('/login') || isKeycloakUrl(url.href),
    { timeout: 10000 }
  ).catch(() => {});
}
