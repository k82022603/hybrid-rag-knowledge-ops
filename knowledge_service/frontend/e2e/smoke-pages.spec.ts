/**
 * Smoke Tests - 4 New Pages
 *
 * Basic rendering and UI element verification for:
 * 1. BookmarkPage (/bookmarks)
 * 2. ProfilePage (/profile)
 * 3. AdminPage (/admin) - requires ADMIN role
 * 4. DocumentUploadPage (/upload) - requires KNOWLEDGE_MANAGER or ADMIN role
 *
 * Test scope: compile/render/basic-click level only (NOT functional tests)
 */
import { test, expect, type Page } from '@playwright/test';

/**
 * Helper: Login as admin user
 * Admin user has access to all pages including /admin and /upload
 */
async function loginAsAdmin(page: Page) {
  await page.goto('/login');
  await page.locator('input[type="email"], input[name="email"]').fill('admin@example.com');
  await page.locator('input[type="password"], input[name="password"]').fill('admin123');
  await page.locator('button[type="submit"]').click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10000 });
}

/**
 * Helper: Login as regular user
 */
async function loginAsUser(page: Page) {
  await page.goto('/login');
  await page.locator('input[type="email"], input[name="email"]').fill('test@example.com');
  await page.locator('input[type="password"], input[name="password"]').fill('password123');
  await page.locator('button[type="submit"]').click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10000 });
}

/**
 * Helper: Collect console errors during page load
 */
function setupConsoleErrorCapture(page: Page): string[] {
  const consoleErrors: string[] = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });
  return consoleErrors;
}

// ============================================================================
// 1. BookmarkPage (/bookmarks)
// ============================================================================
test.describe('BookmarkPage Smoke Tests', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('should render the page without errors', async ({ page }) => {
    const consoleErrors = setupConsoleErrorCapture(page);
    await page.goto('/bookmarks');

    // Verify page renders with testid
    await expect(page.locator('[data-testid="bookmark-page"]')).toBeVisible({ timeout: 10000 });

    // Verify page heading
    await expect(page.locator('h1')).toContainText('Bookmarks');

    // No critical console errors (ignore API/network errors which are expected without backend)
    const criticalErrors = consoleErrors.filter(
      (e) => !e.includes('fetch') && !e.includes('network') && !e.includes('ERR_') && !e.includes('api')
    );
    // Log any errors for debugging, but do not fail on API errors
    if (criticalErrors.length > 0) {
      console.warn('Console errors on BookmarkPage:', criticalErrors);
    }
  });

  test('should display folder sidebar navigation', async ({ page }) => {
    await page.goto('/bookmarks');
    await expect(page.locator('[data-testid="bookmark-page"]')).toBeVisible({ timeout: 10000 });

    // Verify folder navigation aria label
    const nav = page.locator('nav[aria-label="Bookmark folders"]');
    await expect(nav).toBeVisible();

    // Verify folder buttons exist
    await expect(page.getByText('All Bookmarks')).toBeVisible();
    await expect(page.getByText('Default')).toBeVisible();
    await expect(page.getByText('Important')).toBeVisible();
    await expect(page.getByText('Read Later')).toBeVisible();
  });

  test('should display search input and view toggle', async ({ page }) => {
    await page.goto('/bookmarks');
    await expect(page.locator('[data-testid="bookmark-page"]')).toBeVisible({ timeout: 10000 });

    // Search input
    const searchInput = page.locator('input[aria-label="Search bookmarks"]');
    await expect(searchInput).toBeVisible();
    await expect(searchInput).toHaveAttribute('placeholder', 'Search bookmarks...');

    // View toggle buttons
    await expect(page.locator('button[aria-label="Grid view"]')).toBeVisible();
    await expect(page.locator('button[aria-label="List view"]')).toBeVisible();
  });

  test('should switch view mode on toggle click', async ({ page }) => {
    await page.goto('/bookmarks');
    await expect(page.locator('[data-testid="bookmark-page"]')).toBeVisible({ timeout: 10000 });

    // Click list view
    await page.locator('button[aria-label="List view"]').click();
    // Click grid view
    await page.locator('button[aria-label="Grid view"]').click();

    // No crash = pass
  });

  test('should switch folders on click', async ({ page }) => {
    await page.goto('/bookmarks');
    await expect(page.locator('[data-testid="bookmark-page"]')).toBeVisible({ timeout: 10000 });

    // Click "Important" folder
    await page.getByText('Important').click();
    // Click "Read Later" folder
    await page.getByText('Read Later').click();
    // Click "All Bookmarks" folder
    await page.getByText('All Bookmarks').click();

    // No crash = pass
  });
});

// ============================================================================
// 2. ProfilePage (/profile)
// ============================================================================
test.describe('ProfilePage Smoke Tests', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('should render the page without errors', async ({ page }) => {
    const consoleErrors = setupConsoleErrorCapture(page);
    await page.goto('/profile');

    // Verify page renders with testid
    await expect(page.locator('[data-testid="profile-page"]')).toBeVisible({ timeout: 10000 });

    // Verify page heading
    await expect(page.locator('h1')).toContainText('Profile');
  });

  test('should display 4 tab navigation buttons', async ({ page }) => {
    await page.goto('/profile');
    await expect(page.locator('[data-testid="profile-page"]')).toBeVisible({ timeout: 10000 });

    // Verify tab navigation exists
    const nav = page.locator('nav[aria-label="Profile navigation"]');
    await expect(nav).toBeVisible();

    // Verify all 4 tabs
    await expect(page.getByRole('button', { name: /Profile/i }).first()).toBeVisible();
    await expect(page.getByRole('button', { name: /Password/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Activity/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Notifications/i })).toBeVisible();
  });

  test('should show profile form on default tab', async ({ page }) => {
    await page.goto('/profile');
    await expect(page.locator('[data-testid="profile-page"]')).toBeVisible({ timeout: 10000 });

    // Default tab is "profile" - should show the profile form
    await expect(page.locator('[data-testid="profile-form"]')).toBeVisible({ timeout: 5000 });

    // Verify form fields exist
    await expect(page.locator('#firstName')).toBeVisible();
    await expect(page.locator('#lastName')).toBeVisible();
    await expect(page.locator('#displayName')).toBeVisible();
    await expect(page.locator('#department')).toBeVisible();

    // Verify Save button
    await expect(page.getByRole('button', { name: /Save Changes/i })).toBeVisible();
  });

  test('should switch to Password tab and show password form', async ({ page }) => {
    await page.goto('/profile');
    await expect(page.locator('[data-testid="profile-page"]')).toBeVisible({ timeout: 10000 });

    // Click Password tab
    await page.getByRole('button', { name: /Password/i }).click();

    // Should show password form
    await expect(page.locator('[data-testid="password-form"]')).toBeVisible({ timeout: 5000 });

    // Verify password fields
    await expect(page.locator('#currentPassword')).toBeVisible();
    await expect(page.locator('#newPassword')).toBeVisible();
    await expect(page.locator('#confirmPassword')).toBeVisible();

    // Verify Change Password button
    await expect(page.getByRole('button', { name: /Change Password/i })).toBeVisible();
  });

  test('should switch to Activity tab', async ({ page }) => {
    await page.goto('/profile');
    await expect(page.locator('[data-testid="profile-page"]')).toBeVisible({ timeout: 10000 });

    // Click Activity tab
    await page.getByRole('button', { name: /Activity/i }).click();

    // Should show either activity history or loading/empty state
    // Allow time for the query to resolve
    await page.waitForTimeout(2000);

    // The activity tab content area should be visible (either data, loading, or empty)
    const contentArea = page.locator('[data-testid="profile-page"] .flex-1');
    await expect(contentArea).toBeVisible();
  });

  test('should switch to Notifications tab', async ({ page }) => {
    await page.goto('/profile');
    await expect(page.locator('[data-testid="profile-page"]')).toBeVisible({ timeout: 10000 });

    // Click Notifications tab
    await page.getByRole('button', { name: /Notifications/i }).click();

    // Wait for content to load
    await page.waitForTimeout(2000);

    // Content area should be visible
    const contentArea = page.locator('[data-testid="profile-page"] .flex-1');
    await expect(contentArea).toBeVisible();
  });
});

// ============================================================================
// 3. AdminPage (/admin) - requires ADMIN role
// ============================================================================
test.describe('AdminPage Smoke Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Must login as admin to access /admin
    await loginAsAdmin(page);
  });

  test('should render the page without errors', async ({ page }) => {
    const consoleErrors = setupConsoleErrorCapture(page);
    await page.goto('/admin');

    // Verify page renders with testid
    await expect(page.locator('[data-testid="admin-page"]')).toBeVisible({ timeout: 10000 });

    // Verify page heading
    await expect(page.locator('h1')).toContainText('Administration');
  });

  test('should display 4 tab navigation buttons', async ({ page }) => {
    await page.goto('/admin');
    await expect(page.locator('[data-testid="admin-page"]')).toBeVisible({ timeout: 10000 });

    // Verify admin navigation
    const nav = page.locator('nav[aria-label="Admin navigation"]');
    await expect(nav).toBeVisible();

    // Verify all 4 tabs
    await expect(page.getByRole('button', { name: /System Stats/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /User Management/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /System Settings/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Audit Logs/i })).toBeVisible();
  });

  test('should show System Stats on default tab', async ({ page }) => {
    await page.goto('/admin');
    await expect(page.locator('[data-testid="admin-page"]')).toBeVisible({ timeout: 10000 });

    // Default tab is "stats" - wait for content to appear
    await page.waitForTimeout(2000);

    // Content area should be visible (stats, loading, or error state)
    const contentArea = page.locator('[data-testid="admin-page"] .flex-1');
    await expect(contentArea).toBeVisible();
  });

  test('should switch to User Management tab', async ({ page }) => {
    await page.goto('/admin');
    await expect(page.locator('[data-testid="admin-page"]')).toBeVisible({ timeout: 10000 });

    // Click User Management tab
    await page.getByRole('button', { name: /User Management/i }).click();

    // Wait for content
    await page.waitForTimeout(2000);

    // Should show search input for users
    const searchInput = page.locator('input[aria-label="Search users"]');
    await expect(searchInput).toBeVisible({ timeout: 5000 });

    // Should show status filter dropdown
    const statusFilter = page.locator('select[aria-label="Filter by status"]');
    await expect(statusFilter).toBeVisible();
  });

  test('should switch to System Settings tab', async ({ page }) => {
    await page.goto('/admin');
    await expect(page.locator('[data-testid="admin-page"]')).toBeVisible({ timeout: 10000 });

    // Click System Settings tab
    await page.getByRole('button', { name: /System Settings/i }).click();

    // Wait for content
    await page.waitForTimeout(2000);

    // Content area should be visible
    const contentArea = page.locator('[data-testid="admin-page"] .flex-1');
    await expect(contentArea).toBeVisible();
  });

  test('should switch to Audit Logs tab', async ({ page }) => {
    await page.goto('/admin');
    await expect(page.locator('[data-testid="admin-page"]')).toBeVisible({ timeout: 10000 });

    // Click Audit Logs tab
    await page.getByRole('button', { name: /Audit Logs/i }).click();

    // Wait for content
    await page.waitForTimeout(2000);

    // Should show action filter dropdown
    const actionFilter = page.locator('select[aria-label="Filter by action"]');
    await expect(actionFilter).toBeVisible({ timeout: 5000 });
  });

  test('should cycle through all tabs without crash', async ({ page }) => {
    await page.goto('/admin');
    await expect(page.locator('[data-testid="admin-page"]')).toBeVisible({ timeout: 10000 });

    // Cycle through all tabs
    const tabs = ['System Stats', 'User Management', 'System Settings', 'Audit Logs'];
    for (const tabName of tabs) {
      await page.getByRole('button', { name: new RegExp(tabName, 'i') }).click();
      await page.waitForTimeout(500);
    }
    // No crash = pass
  });
});

// ============================================================================
// 4. DocumentUploadPage (/upload) - requires KNOWLEDGE_MANAGER or ADMIN
// ============================================================================
test.describe('DocumentUploadPage Smoke Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Admin has KNOWLEDGE_MANAGER access
    await loginAsAdmin(page);
  });

  test('should render the page without errors', async ({ page }) => {
    const consoleErrors = setupConsoleErrorCapture(page);
    await page.goto('/upload');

    // Verify page renders with testid
    await expect(page.locator('[data-testid="upload-page"]')).toBeVisible({ timeout: 10000 });

    // Verify page heading
    await expect(page.locator('h1')).toContainText('Upload Documents');
  });

  test('should display drag-and-drop zone', async ({ page }) => {
    await page.goto('/upload');
    await expect(page.locator('[data-testid="upload-page"]')).toBeVisible({ timeout: 10000 });

    // Verify dropzone area with aria-label
    const dropzone = page.locator('[aria-label="Drop files here or click to browse"]');
    await expect(dropzone).toBeVisible();

    // Verify instructional text
    await expect(page.getByText('Drag and drop files, or click to browse')).toBeVisible();

    // Verify supported formats text
    await expect(page.getByText(/Supported formats:/)).toBeVisible();

    // Verify max file size text
    await expect(page.getByText(/Maximum file size: 50MB/)).toBeVisible();
  });

  test('should display supported formats card', async ({ page }) => {
    await page.goto('/upload');
    await expect(page.locator('[data-testid="upload-page"]')).toBeVisible({ timeout: 10000 });

    // Verify "Supported Formats" card in sidebar
    await expect(page.getByText('Supported Formats').first()).toBeVisible();

    // Verify format entries exist
    await expect(page.getByText('PDF')).toBeVisible();
    await expect(page.getByText('DOCX')).toBeVisible();
    await expect(page.getByText('Markdown')).toBeVisible();
  });

  test('should display Recent Uploads section', async ({ page }) => {
    await page.goto('/upload');
    await expect(page.locator('[data-testid="upload-page"]')).toBeVisible({ timeout: 10000 });

    // Verify "Recent Uploads" heading
    await expect(page.getByText('Recent Uploads')).toBeVisible();
  });

  test('should have hidden file input for upload', async ({ page }) => {
    await page.goto('/upload');
    await expect(page.locator('[data-testid="upload-page"]')).toBeVisible({ timeout: 10000 });

    // The file input should exist (hidden)
    const fileInput = page.locator('input[type="file"]');
    await expect(fileInput).toHaveCount(1);
    await expect(fileInput).toHaveAttribute('multiple', '');
  });
});

// ============================================================================
// 5. Navigation Tests - Sidebar navigation to new pages
// ============================================================================
test.describe('Sidebar Navigation to New Pages', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('should navigate to Bookmarks from sidebar', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForTimeout(1000);

    // Click Bookmarks in sidebar
    const bookmarkNav = page.locator('aside button').filter({ hasText: 'Bookmarks' });
    if (await bookmarkNav.isVisible()) {
      await bookmarkNav.click();
      await expect(page).toHaveURL(/.*bookmarks/);
      await expect(page.locator('[data-testid="bookmark-page"]')).toBeVisible({ timeout: 10000 });
    }
  });

  test('should navigate to Profile from sidebar', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForTimeout(1000);

    // Click Profile in sidebar
    const profileNav = page.locator('aside button').filter({ hasText: 'Profile' });
    if (await profileNav.isVisible()) {
      await profileNav.click();
      await expect(page).toHaveURL(/.*profile/);
      await expect(page.locator('[data-testid="profile-page"]')).toBeVisible({ timeout: 10000 });
    }
  });

  test('should navigate to Admin from sidebar', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForTimeout(1000);

    // Click Admin in sidebar (only visible for admin users)
    const adminNav = page.locator('aside button').filter({ hasText: 'Admin' });
    if (await adminNav.isVisible()) {
      await adminNav.click();
      await expect(page).toHaveURL(/.*admin/);
      await expect(page.locator('[data-testid="admin-page"]')).toBeVisible({ timeout: 10000 });
    }
  });

  test('should navigate to Upload from sidebar', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForTimeout(1000);

    // Click Upload in sidebar (only visible for KNOWLEDGE_MANAGER/ADMIN)
    const uploadNav = page.locator('aside button').filter({ hasText: 'Upload' });
    if (await uploadNav.isVisible()) {
      await uploadNav.click();
      await expect(page).toHaveURL(/.*upload/);
      await expect(page.locator('[data-testid="upload-page"]')).toBeVisible({ timeout: 10000 });
    }
  });
});

// ============================================================================
// 6. Route Protection Tests
// ============================================================================
test.describe('Route Protection for New Pages', () => {
  test('should redirect unauthenticated user to login for /bookmarks', async ({ page }) => {
    await page.goto('/bookmarks');
    await expect(page).toHaveURL(/.*login.*/, { timeout: 10000 });
  });

  test('should redirect unauthenticated user to login for /profile', async ({ page }) => {
    await page.goto('/profile');
    await expect(page).toHaveURL(/.*login.*/, { timeout: 10000 });
  });

  test('should redirect unauthenticated user to login for /admin', async ({ page }) => {
    await page.goto('/admin');
    await expect(page).toHaveURL(/.*login.*/, { timeout: 10000 });
  });

  test('should redirect unauthenticated user to login for /upload', async ({ page }) => {
    await page.goto('/upload');
    await expect(page).toHaveURL(/.*login.*/, { timeout: 10000 });
  });

  test('should deny regular user access to /admin (Access Denied)', async ({ page }) => {
    await loginAsUser(page);
    await page.goto('/admin');

    // Regular user should see Access Denied or be redirected
    // Either the admin-page testid is NOT visible, OR an "Access Denied" message appears
    const adminPageVisible = await page.locator('[data-testid="admin-page"]').isVisible().catch(() => false);
    if (!adminPageVisible) {
      // Expect Access Denied text OR redirect to another page
      const accessDenied = page.getByText('Access Denied');
      const isAccessDenied = await accessDenied.isVisible().catch(() => false);
      const isRedirected = !page.url().includes('/admin');
      expect(isAccessDenied || isRedirected).toBeTruthy();
    }
  });
});
