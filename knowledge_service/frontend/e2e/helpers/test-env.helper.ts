/**
 * Test Environment Helper
 *
 * Provides environment detection and conditional test utilities.
 * Supports Mock (local) and Docker (Keycloak/real services) environments.
 *
 * P2 Improvement: Environment-based test separation
 */
import { type Page, test } from '@playwright/test';

// ============================================================================
// Environment Detection
// ============================================================================

/**
 * Check if running in Docker environment (Keycloak auth)
 */
export function isDockerEnvironment(): boolean {
  return (
    process.env.TEST_ENV === 'docker' ||
    process.env.KEYCLOAK_PORT !== undefined ||
    process.env.USE_KEYCLOAK === 'true'
  );
}

/**
 * Check if running in Mock environment (local form auth)
 */
export function isMockEnvironment(): boolean {
  return (
    process.env.TEST_ENV === 'mock' ||
    process.env.USE_MOCK === 'true' ||
    !isDockerEnvironment()
  );
}

/**
 * Get current environment name
 */
export function getEnvironmentName(): 'docker' | 'mock' {
  return isDockerEnvironment() ? 'docker' : 'mock';
}

// ============================================================================
// Conditional Test Helpers
// ============================================================================

/**
 * Skip test if running in Docker environment
 * Use for tests that require mock API responses
 */
export function skipInDocker(reason?: string) {
  test.skip(isDockerEnvironment(), reason || 'Skipped in Docker environment');
}

/**
 * Skip test if running in Mock environment
 * Use for tests that require real API/Keycloak integration
 */
export function skipInMock(reason?: string) {
  test.skip(isMockEnvironment(), reason || 'Skipped in Mock environment');
}

/**
 * Skip test if feature is not implemented
 * Use for TDD tests where UI is not yet complete
 */
export function skipIfNotImplemented(featureName: string) {
  const notImplementedFeatures = [
    'document-upload-dropzone',
    'advanced-search-filters',
    // Add more as needed
  ];

  test.skip(
    notImplementedFeatures.includes(featureName),
    `Feature not yet implemented: ${featureName}`
  );
}

// ============================================================================
// API Wait Helpers
// ============================================================================

/**
 * Wait for API response with environment-appropriate timeout
 * Docker environments get longer timeouts due to service chain latency
 */
export async function waitForApiResponse(
  page: Page,
  urlPattern: string | RegExp,
  options?: { timeout?: number }
): Promise<void> {
  const baseTimeout = options?.timeout || 5000;
  const adjustedTimeout = isDockerEnvironment() ? baseTimeout * 2 : baseTimeout;

  await page
    .waitForResponse(
      (response) => {
        const url = response.url();
        if (typeof urlPattern === 'string') {
          return url.includes(urlPattern);
        }
        return urlPattern.test(url);
      },
      { timeout: adjustedTimeout }
    )
    .catch(() => {
      // API call might not happen in mock environment
    });
}

/**
 * Wait for content to load with environment-appropriate timeout
 */
export async function waitForContent(
  page: Page,
  selector: string,
  options?: { timeout?: number }
): Promise<boolean> {
  const baseTimeout = options?.timeout || 5000;
  const adjustedTimeout = isDockerEnvironment() ? baseTimeout * 2 : baseTimeout;

  try {
    await page.locator(selector).waitFor({ state: 'visible', timeout: adjustedTimeout });
    return true;
  } catch {
    return false;
  }
}

// ============================================================================
// Resilient Assertion Helpers
// ============================================================================

/**
 * Assert with fallback - try primary assertion, fall back to secondary
 */
export async function assertWithFallback(
  page: Page,
  primarySelector: string,
  fallbackSelector: string,
  options?: { timeout?: number }
): Promise<void> {
  const timeout = options?.timeout || 5000;

  const primaryVisible = await page
    .locator(primarySelector)
    .isVisible({ timeout })
    .catch(() => false);

  if (primaryVisible) {
    // Primary assertion passed
    return;
  }

  // Try fallback
  const fallbackVisible = await page
    .locator(fallbackSelector)
    .isVisible({ timeout })
    .catch(() => false);

  if (!fallbackVisible) {
    throw new Error(
      `Neither primary (${primarySelector}) nor fallback (${fallbackSelector}) selector is visible`
    );
  }
}

/**
 * Check element exists with any of the given selectors
 */
export async function existsAny(page: Page, selectors: string[]): Promise<boolean> {
  for (const selector of selectors) {
    const exists = await page
      .locator(selector)
      .isVisible({ timeout: 2000 })
      .catch(() => false);
    if (exists) return true;
  }
  return false;
}

// ============================================================================
// Test Configuration
// ============================================================================

/**
 * Get environment-appropriate test configuration
 */
export function getTestConfig() {
  const isDocker = isDockerEnvironment();

  return {
    // Timeouts
    navigationTimeout: isDocker ? 30000 : 10000,
    actionTimeout: isDocker ? 10000 : 5000,
    assertionTimeout: isDocker ? 10000 : 5000,

    // Retries
    maxRetries: isDocker ? 2 : 1,

    // API
    apiBaseUrl: isDocker
      ? 'http://localhost:8080/api'
      : 'http://localhost:5173/api',

    // Auth
    authProvider: isDocker ? 'keycloak' : 'mock',
  };
}

/**
 * Log environment info for debugging
 */
export function logEnvironmentInfo(): void {
  console.log(`
╔════════════════════════════════════════╗
║         Test Environment Info          ║
╠════════════════════════════════════════╣
║  Environment: ${getEnvironmentName().padEnd(24)}║
║  Docker: ${isDockerEnvironment().toString().padEnd(29)}║
║  Mock: ${isMockEnvironment().toString().padEnd(31)}║
╚════════════════════════════════════════╝
  `);
}
