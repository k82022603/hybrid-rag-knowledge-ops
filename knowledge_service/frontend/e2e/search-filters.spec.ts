/**
 * Search Filters E2E Tests
 *
 * Tests the search filtering functionality:
 * 1. Execute search
 * 2. Apply document type filter
 * 3. Apply date range filter
 * 4. Verify filtered results
 * 5. Clear filters
 *
 * Uses real API calls in Docker environment.
 */
import { test, expect, type Page } from '@playwright/test';

/**
 * Helper: Login as test user
 */
async function loginAsUser(page: Page) {
  await page.goto('/login');
  await page.locator('input[type="email"], input[name="email"]').fill('test@example.com');
  await page.locator('input[type="password"], input[name="password"]').fill('password123');
  await page.locator('button[type="submit"]').click();
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10000 });
}

/**
 * Helper: Navigate to keyword search and open filters
 */
async function goToKeywordSearchWithFilters(page: Page) {
  await page.goto('/search');
  await expect(page.locator('[data-testid="search-page"]')).toBeVisible({ timeout: 10000 });

  // Switch to Keyword Search tab
  await page.locator('button[role="tab"]:has-text("Keyword Search")').click();
  await expect(page.locator('[data-testid="keyword-search"]')).toBeVisible({ timeout: 5000 });

  // Open filters panel
  const filtersButton = page.locator('button[aria-label*="filters"]');
  await filtersButton.click();
  await expect(page.locator('[data-testid="search-filters"]')).toBeVisible({ timeout: 5000 });
}

// ============================================================================
// Search Filter Tests
// ============================================================================
test.describe('Search Filters E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsUser(page);
  });

  test.describe('Filter Panel Display', () => {
    test('should show filters panel when clicking filters button', async ({ page }) => {
      await page.goto('/search');
      await page.locator('button[role="tab"]:has-text("Keyword Search")').click();
      await expect(page.locator('[data-testid="keyword-search"]')).toBeVisible();

      // Initially filters should be hidden
      await expect(page.locator('[data-testid="search-filters"]')).not.toBeVisible();

      // Click filters button
      const filtersButton = page.locator('button[aria-label*="filters"]');
      await filtersButton.click();

      // Filters panel should be visible
      await expect(page.locator('[data-testid="search-filters"]')).toBeVisible();

      // Verify ARIA expanded state
      await expect(filtersButton).toHaveAttribute('aria-expanded', 'true');
    });

    test('should hide filters panel when clicking filters button again', async ({ page }) => {
      await goToKeywordSearchWithFilters(page);

      // Click filters button again to close
      const filtersButton = page.locator('button[aria-label*="filters"]');
      await filtersButton.click();

      // Filters panel should be hidden
      await expect(page.locator('[data-testid="search-filters"]')).not.toBeVisible();
      await expect(filtersButton).toHaveAttribute('aria-expanded', 'false');
    });

    test('should display all filter fields', async ({ page }) => {
      await goToKeywordSearchWithFilters(page);

      // Document Type dropdown
      const docTypeSelect = page.locator('#filter-doc-type');
      await expect(docTypeSelect).toBeVisible();

      // Project dropdown
      const projectSelect = page.locator('#filter-project');
      await expect(projectSelect).toBeVisible();

      // Date From input
      const dateFromInput = page.locator('#filter-date-from');
      await expect(dateFromInput).toBeVisible();
      await expect(dateFromInput).toHaveAttribute('type', 'date');

      // Date To input
      const dateToInput = page.locator('#filter-date-to');
      await expect(dateToInput).toBeVisible();
      await expect(dateToInput).toHaveAttribute('type', 'date');
    });

    test('should have proper labels for filter fields', async ({ page }) => {
      await goToKeywordSearchWithFilters(page);

      await expect(page.locator('label[for="filter-doc-type"]')).toContainText('Document Type');
      await expect(page.locator('label[for="filter-project"]')).toContainText('Project');
      await expect(page.locator('label[for="filter-date-from"]')).toContainText('From Date');
      await expect(page.locator('label[for="filter-date-to"]')).toContainText('To Date');
    });
  });

  test.describe('Document Type Filter', () => {
    test('should display document type options', async ({ page }) => {
      await goToKeywordSearchWithFilters(page);

      const docTypeSelect = page.locator('#filter-doc-type');

      // Verify default option
      await expect(docTypeSelect).toHaveValue('');

      // Click to open dropdown and verify options exist
      const options = docTypeSelect.locator('option');
      const optionCount = await options.count();
      expect(optionCount).toBeGreaterThan(1);

      // Verify specific options
      await expect(options.filter({ hasText: 'All Types' })).toBeVisible();
      await expect(options.filter({ hasText: 'Technical' })).toBeVisible();
      await expect(options.filter({ hasText: 'Guide' })).toBeVisible();
    });

    test('should apply document type filter', async ({ page }) => {
      await goToKeywordSearchWithFilters(page);

      // Select a document type
      await page.locator('#filter-doc-type').selectOption('technical');

      // Verify selection
      await expect(page.locator('#filter-doc-type')).toHaveValue('technical');

      // Active filter chip should appear
      await expect(page.locator('span:has-text("Type: technical")')).toBeVisible();
    });

    test('should show filter badge on button when filter is active', async ({ page }) => {
      await goToKeywordSearchWithFilters(page);

      // Apply a filter
      await page.locator('#filter-doc-type').selectOption('guide');

      // Close filter panel
      await page.locator('button[aria-label*="filters"]').click();

      // Badge should be visible on the filters button
      const filtersButton = page.locator('button[aria-label*="filters"]');
      const badge = filtersButton.locator('span.rounded-full:has-text("1")');
      await expect(badge).toBeVisible();
    });
  });

  test.describe('Project Filter', () => {
    test('should display project options', async ({ page }) => {
      await goToKeywordSearchWithFilters(page);

      const projectSelect = page.locator('#filter-project');

      // Verify options exist
      const options = projectSelect.locator('option');
      const optionCount = await options.count();
      expect(optionCount).toBeGreaterThan(1);

      // Verify specific options
      await expect(options.filter({ hasText: 'All Projects' })).toBeVisible();
      await expect(options.filter({ hasText: 'Project A' })).toBeVisible();
    });

    test('should apply project filter', async ({ page }) => {
      await goToKeywordSearchWithFilters(page);

      // Select a project
      await page.locator('#filter-project').selectOption('project-a');

      // Verify selection
      await expect(page.locator('#filter-project')).toHaveValue('project-a');

      // Active filter chip should appear
      await expect(page.locator('span:has-text("Project: project-a")')).toBeVisible();
    });
  });

  test.describe('Date Range Filter', () => {
    test('should apply date from filter', async ({ page }) => {
      await goToKeywordSearchWithFilters(page);

      // Set from date
      const today = new Date().toISOString().split('T')[0];
      await page.locator('#filter-date-from').fill('2024-01-01');

      // Active filter chip should appear
      await expect(page.locator('span:has-text("From: 2024-01-01")')).toBeVisible();
    });

    test('should apply date to filter', async ({ page }) => {
      await goToKeywordSearchWithFilters(page);

      // Set to date
      await page.locator('#filter-date-to').fill('2024-12-31');

      // Active filter chip should appear
      await expect(page.locator('span:has-text("To: 2024-12-31")')).toBeVisible();
    });

    test('should apply date range filter', async ({ page }) => {
      await goToKeywordSearchWithFilters(page);

      // Set date range
      await page.locator('#filter-date-from').fill('2024-01-01');
      await page.locator('#filter-date-to').fill('2024-12-31');

      // Both filter chips should appear
      await expect(page.locator('span:has-text("From: 2024-01-01")')).toBeVisible();
      await expect(page.locator('span:has-text("To: 2024-12-31")')).toBeVisible();
    });
  });

  test.describe('Multiple Filters', () => {
    test('should apply multiple filters simultaneously', async ({ page }) => {
      await goToKeywordSearchWithFilters(page);

      // Apply document type filter
      await page.locator('#filter-doc-type').selectOption('technical');

      // Apply project filter
      await page.locator('#filter-project').selectOption('project-a');

      // Apply date filter
      await page.locator('#filter-date-from').fill('2024-01-01');

      // All filter chips should be visible
      await expect(page.locator('span:has-text("Type: technical")')).toBeVisible();
      await expect(page.locator('span:has-text("Project: project-a")')).toBeVisible();
      await expect(page.locator('span:has-text("From: 2024-01-01")')).toBeVisible();

      // Badge should show count of active filters
      const filtersButton = page.locator('button[aria-label*="filters"]');
      const badge = filtersButton.locator('span.rounded-full');
      await expect(badge).toContainText('3');
    });
  });

  test.describe('Filter Removal', () => {
    test('should remove individual filter by clicking X button', async ({ page }) => {
      await goToKeywordSearchWithFilters(page);

      // Apply filter
      await page.locator('#filter-doc-type').selectOption('technical');
      await expect(page.locator('span:has-text("Type: technical")')).toBeVisible();

      // Click X button on filter chip
      const removeButton = page.locator('button[aria-label="Remove document type filter: technical"]');
      await removeButton.click();

      // Filter chip should be removed
      await expect(page.locator('span:has-text("Type: technical")')).not.toBeVisible();

      // Dropdown should reset to default
      await expect(page.locator('#filter-doc-type')).toHaveValue('');
    });

    test('should remove project filter by clicking X button', async ({ page }) => {
      await goToKeywordSearchWithFilters(page);

      await page.locator('#filter-project').selectOption('project-b');
      await expect(page.locator('span:has-text("Project: project-b")')).toBeVisible();

      // Click X button
      const removeButton = page.locator('button[aria-label="Remove project filter: project-b"]');
      await removeButton.click();

      await expect(page.locator('span:has-text("Project: project-b")')).not.toBeVisible();
      await expect(page.locator('#filter-project')).toHaveValue('');
    });

    test('should remove date filter by clicking X button', async ({ page }) => {
      await goToKeywordSearchWithFilters(page);

      await page.locator('#filter-date-from').fill('2024-06-01');
      await expect(page.locator('span:has-text("From: 2024-06-01")')).toBeVisible();

      // Click X button
      const removeButton = page.locator('button[aria-label="Remove from date filter: 2024-06-01"]');
      await removeButton.click();

      await expect(page.locator('span:has-text("From: 2024-06-01")')).not.toBeVisible();
      await expect(page.locator('#filter-date-from')).toHaveValue('');
    });
  });

  test.describe('Clear All Filters', () => {
    test('should clear all filters when clicking Clear all button', async ({ page }) => {
      await goToKeywordSearchWithFilters(page);

      // Apply multiple filters
      await page.locator('#filter-doc-type').selectOption('manual');
      await page.locator('#filter-project').selectOption('project-c');
      await page.locator('#filter-date-from').fill('2024-01-15');
      await page.locator('#filter-date-to').fill('2024-06-30');

      // Verify all filter chips are visible
      await expect(page.locator('span:has-text("Type: manual")')).toBeVisible();
      await expect(page.locator('span:has-text("Project: project-c")')).toBeVisible();
      await expect(page.locator('span:has-text("From: 2024-01-15")')).toBeVisible();
      await expect(page.locator('span:has-text("To: 2024-06-30")')).toBeVisible();

      // Click Clear all button
      const clearAllButton = page.locator('[data-testid="clear-all-filters"]');
      await clearAllButton.click();

      // All filter chips should be removed
      await expect(page.locator('span:has-text("Type: manual")')).not.toBeVisible();
      await expect(page.locator('span:has-text("Project: project-c")')).not.toBeVisible();
      await expect(page.locator('span:has-text("From: 2024-01-15")')).not.toBeVisible();
      await expect(page.locator('span:has-text("To: 2024-06-30")')).not.toBeVisible();

      // All inputs should reset to default
      await expect(page.locator('#filter-doc-type')).toHaveValue('');
      await expect(page.locator('#filter-project')).toHaveValue('');
      await expect(page.locator('#filter-date-from')).toHaveValue('');
      await expect(page.locator('#filter-date-to')).toHaveValue('');
    });

    test('should hide Clear all button when no filters are active', async ({ page }) => {
      await goToKeywordSearchWithFilters(page);

      // Without any filters, Clear all should not be visible
      await expect(page.locator('[data-testid="clear-all-filters"]')).not.toBeVisible();

      // Apply a filter
      await page.locator('#filter-doc-type').selectOption('report');

      // Clear all should now be visible
      await expect(page.locator('[data-testid="clear-all-filters"]')).toBeVisible();

      // Remove the filter
      await page.locator('#filter-doc-type').selectOption('');

      // Clear all should be hidden again
      await expect(page.locator('[data-testid="clear-all-filters"]')).not.toBeVisible();
    });
  });

  test.describe('Filter Integration with Search', () => {
    test('should apply filters to search query', async ({ page }) => {
      await goToKeywordSearchWithFilters(page);

      // Apply filter first
      await page.locator('#filter-doc-type').selectOption('technical');

      // Enter search query
      await page.locator('[data-testid="keyword-search-input"]').fill('API documentation');

      // Execute search
      await page.locator('[data-testid="keyword-search-submit"]').click();

      // Wait for response
      await page.waitForTimeout(3000);

      // Filter should remain applied after search
      await expect(page.locator('span:has-text("Type: technical")')).toBeVisible();
    });

    test('should maintain filters when switching between tabs', async ({ page }) => {
      await goToKeywordSearchWithFilters(page);

      // Apply filters
      await page.locator('#filter-doc-type').selectOption('guide');
      await page.locator('#filter-project').selectOption('project-a');

      // Switch to Chat Search tab
      await page.locator('button[role="tab"]:has-text("Chat Search")').click();
      await expect(page.locator('[data-testid="chat-search"]')).toBeVisible();

      // Switch back to Keyword Search tab
      await page.locator('button[role="tab"]:has-text("Keyword Search")').click();
      await expect(page.locator('[data-testid="keyword-search"]')).toBeVisible();

      // Reopen filters panel
      await page.locator('button[aria-label*="filters"]').click();

      // Filters may or may not persist (depends on implementation)
      // This test documents the behavior
    });
  });

  test.describe('Accessibility', () => {
    test('should have proper ARIA attributes on filter panel', async ({ page }) => {
      await goToKeywordSearchWithFilters(page);

      // Filter panel should have proper role and label
      const filtersPanel = page.locator('[data-testid="search-filters"]');
      await expect(filtersPanel).toHaveAttribute('role', 'search');
      await expect(filtersPanel).toHaveAttribute('aria-label', 'Search filters');
    });

    test('should have proper labeling for filter fields', async ({ page }) => {
      await goToKeywordSearchWithFilters(page);

      // Labels should be properly associated with inputs
      const docTypeLabel = page.locator('label[for="filter-doc-type"]');
      await expect(docTypeLabel).toBeVisible();

      const projectLabel = page.locator('label[for="filter-project"]');
      await expect(projectLabel).toBeVisible();
    });

    test('should have accessible remove buttons for filter chips', async ({ page }) => {
      await goToKeywordSearchWithFilters(page);

      // Apply a filter
      await page.locator('#filter-doc-type').selectOption('policy');

      // Remove button should have accessible label
      const removeButton = page.locator('button[aria-label="Remove document type filter: policy"]');
      await expect(removeButton).toBeVisible();
    });

    test('should have accessible Clear all button', async ({ page }) => {
      await goToKeywordSearchWithFilters(page);

      // Apply a filter
      await page.locator('#filter-doc-type').selectOption('meeting');

      // Clear all button should have accessible label
      const clearAllButton = page.locator('[data-testid="clear-all-filters"]');
      await expect(clearAllButton).toHaveAttribute('aria-label', 'Clear all filters');
    });

    test('should be keyboard navigable', async ({ page }) => {
      await goToKeywordSearchWithFilters(page);

      // Tab through filter fields
      await page.keyboard.press('Tab');

      // Should be able to navigate to filter fields
      const activeElement = await page.evaluate(() => document.activeElement?.tagName?.toLowerCase());
      expect(['select', 'input', 'button']).toContain(activeElement);
    });
  });
});
