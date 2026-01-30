/**
 * Authentication Helper for E2E Tests
 *
 * Supports both Mock (local form) and Docker (Keycloak) environments
 */
import { type Page } from '@playwright/test';

/**
 * Universal login function that works with both local and Keycloak forms
 */
export async function login(page: Page, username: string, password: string): Promise<void> {
  await page.goto('/login');

  // Wait for potential Keycloak redirect
  await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

  const currentUrl = page.url();
  const isKeycloak = currentUrl.includes('8180') ||
                     currentUrl.includes('keycloak') ||
                     currentUrl.includes('/realms/');

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
 * Login as admin user
 * Credentials: test-admin / admin123 (Keycloak) or admin@example.com / admin123 (Mock)
 */
export async function loginAsAdmin(page: Page): Promise<void> {
  await page.goto('/login');
  await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

  const isKeycloak = page.url().includes('8180') || page.url().includes('keycloak');

  if (isKeycloak) {
    await login(page, 'test-admin', 'admin123');
  } else {
    await login(page, 'admin@example.com', 'admin123');
  }
}

/**
 * Login as regular user
 * Credentials: test-user / test-password (Keycloak) or test@example.com / password123 (Mock)
 */
export async function loginAsUser(page: Page): Promise<void> {
  await page.goto('/login');
  await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

  const isKeycloak = page.url().includes('8180') || page.url().includes('keycloak');

  if (isKeycloak) {
    await login(page, 'test-user', 'test-password');
  } else {
    await login(page, 'test@example.com', 'password123');
  }
}

/**
 * Check if current environment uses Keycloak
 */
export async function isKeycloakEnvironment(page: Page): Promise<boolean> {
  await page.goto('/login');
  await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
  return page.url().includes('8180') || page.url().includes('keycloak');
}

/**
 * Logout from application
 */
export async function logout(page: Page): Promise<void> {
  // Try clicking logout button if visible
  const logoutButton = page.locator('button:has-text("Logout"), button:has-text("로그아웃"), [data-testid="logout-button"]');
  if (await logoutButton.isVisible({ timeout: 2000 }).catch(() => false)) {
    await logoutButton.click();
  } else {
    // Fallback: navigate to logout endpoint
    await page.goto('/logout');
  }

  // Wait for redirect to login
  await page.waitForURL((url) => url.pathname.includes('/login') || url.href.includes('keycloak'),
    { timeout: 10000 }).catch(() => {});
}
