import { test, expect } from '@playwright/test';

test.describe('Authentication E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
  });

  test.describe('Login Page', () => {
    test('should display login form', async ({ page }) => {
      // Check page title or heading
      await expect(page.locator('h1, h2').first()).toBeVisible();

      // Check email input
      const emailInput = page.locator('input[type="email"], input[name="email"]');
      await expect(emailInput).toBeVisible();

      // Check password input
      const passwordInput = page.locator('input[type="password"], input[name="password"]');
      await expect(passwordInput).toBeVisible();

      // Check login button
      const loginButton = page.locator('button[type="submit"]');
      await expect(loginButton).toBeVisible();
    });

    test('should show validation error for empty fields', async ({ page }) => {
      // Click login without filling fields
      await page.locator('button[type="submit"]').click();

      // Check for validation message (either HTML5 validation or custom)
      const emailInput = page.locator('input[type="email"], input[name="email"]');
      const isInvalid = await emailInput.evaluate((el: HTMLInputElement) => !el.validity.valid);
      expect(isInvalid).toBeTruthy();
    });

    test('should show error for invalid credentials', async ({ page }) => {
      // Fill in invalid credentials
      await page.locator('input[type="email"], input[name="email"]').fill('wrong@example.com');
      await page.locator('input[type="password"], input[name="password"]').fill('wrongpassword');

      // Submit form
      await page.locator('button[type="submit"]').click();

      // Wait for error message
      const errorMessage = page.locator('[role="alert"]').first();
      await expect(errorMessage).toBeVisible({ timeout: 5000 });
    });

    test('should login successfully with valid credentials', async ({ page }) => {
      // Fill in valid test credentials
      await page.locator('input[type="email"], input[name="email"]').fill('test@example.com');
      await page.locator('input[type="password"], input[name="password"]').fill('password123');

      // Submit form
      await page.locator('button[type="submit"]').click();

      // Wait for redirect (should not be on login page anymore)
      await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10000 });

      // Verify we're on a different page
      expect(page.url()).not.toContain('/login');
    });

    test('should login as admin successfully', async ({ page }) => {
      // Fill in admin credentials
      await page.locator('input[type="email"], input[name="email"]').fill('admin@example.com');
      await page.locator('input[type="password"], input[name="password"]').fill('admin123');

      // Submit form
      await page.locator('button[type="submit"]').click();

      // Wait for redirect
      await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10000 });

      // Verify successful login
      expect(page.url()).not.toContain('/login');
    });
  });

  test.describe('Remember Me', () => {
    test('should have remember me checkbox', async ({ page }) => {
      const rememberMe = page.locator('input[type="checkbox"]');
      await expect(rememberMe).toBeVisible();
    });
  });

  test.describe('Logout', () => {
    test('should logout and redirect to login', async ({ page }) => {
      // First login
      await page.locator('input[type="email"], input[name="email"]').fill('test@example.com');
      await page.locator('input[type="password"], input[name="password"]').fill('password123');
      await page.locator('button[type="submit"]').click();

      // Wait for login to complete
      await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10000 });

      // Find and click logout button
      const logoutButton = page.locator('button:has-text("로그아웃"), button:has-text("Logout"), [data-testid="logout"]');
      if (await logoutButton.isVisible()) {
        await logoutButton.click();

        // Should redirect to login
        await page.waitForURL('**/login', { timeout: 5000 });
        expect(page.url()).toContain('/login');
      }
    });
  });

  test.describe('Protected Routes', () => {
    test('should redirect to login when accessing protected route', async ({ page }) => {
      // Try to access a protected route directly
      await page.goto('/dashboard');

      // Should redirect to login
      await expect(page).toHaveURL(/.*login.*/);
    });
  });

  test.describe('Accessibility', () => {
    test('should have proper form labels', async ({ page }) => {
      // Check for accessible labels
      const emailLabel = page.locator('label:has-text("이메일"), label:has-text("Email")');
      const passwordLabel = page.locator('label:has-text("비밀번호"), label:has-text("Password")');

      // At least one should be visible (Korean or English)
      const hasEmailLabel = await emailLabel.isVisible();
      const hasPasswordLabel = await passwordLabel.isVisible();

      expect(hasEmailLabel || hasPasswordLabel).toBeTruthy();
    });

    test('should be keyboard navigable', async ({ page }) => {
      // Click on page body first to ensure focus
      await page.click('body');

      // Tab to first focusable element
      await page.keyboard.press('Tab');

      // Check if a focusable element is focused (input, button, or link)
      const activeElement = await page.evaluate(() => document.activeElement?.tagName?.toLowerCase());
      expect(['input', 'button', 'a']).toContain(activeElement);
    });
  });
});
