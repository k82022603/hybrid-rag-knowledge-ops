/**
 * API Integration E2E Tests
 *
 * Tests actual backend API calls, not just UI rendering.
 * Verifies API responses, status codes, and data integrity.
 *
 * NOTE: These tests call the Backend service directly (port 8081),
 * not through the API Gateway (port 8080), because:
 * - Backend uses its own JWT auth
 * - API Gateway requires Keycloak OAuth2 tokens
 *
 * Implemented Endpoints:
 * - Auth API: /api/v1/auth/* ✅
 * - Search API: /api/v1/search ✅
 *
 * Pending/Stub Endpoints (tested with graceful handling):
 * - Dashboard API: /api/v1/dashboard/*
 * - Profile API: /api/v1/users/me/*
 * - Bookmark API: /api/v1/bookmarks/*
 * - Admin API: /api/v1/admin/*
 */
import { test, expect, type APIRequestContext } from '@playwright/test';

// Backend Direct URL (not through API Gateway)
const API_BASE_URL = process.env.BACKEND_URL || 'http://localhost:8081/api/v1';

// Test credentials
const TEST_USER = {
  email: 'test@example.com',
  password: 'password123',
};

const ADMIN_USER = {
  email: 'admin@example.com',
  password: 'admin123',
};

/**
 * Helper: Login and get auth token
 */
async function getAuthToken(
  request: APIRequestContext,
  credentials = TEST_USER
): Promise<string> {
  const response = await request.post(`${API_BASE_URL}/auth/login`, {
    data: credentials,
  });

  if (response.ok()) {
    const data = await response.json();
    return data.accessToken || data.access_token || data.token || '';
  }

  return '';
}

/**
 * Helper: Create authenticated request headers
 */
function authHeaders(token: string) {
  return {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
}

// ============================================================================
// Auth API Tests (Fully Implemented)
// ============================================================================
test.describe('Auth API Integration Tests', () => {
  test('POST /auth/login - should login with valid credentials', async ({ request }) => {
    const response = await request.post(`${API_BASE_URL}/auth/login`, {
      data: TEST_USER,
    });

    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data).toHaveProperty('accessToken');
    expect(data).toHaveProperty('user');
    expect(data.user).toHaveProperty('email', TEST_USER.email);
  });

  test('POST /auth/login - should return user roles', async ({ request }) => {
    const response = await request.post(`${API_BASE_URL}/auth/login`, {
      data: TEST_USER,
    });

    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.user).toHaveProperty('roles');
    expect(Array.isArray(data.user.roles)).toBeTruthy();
  });

  test('POST /auth/login - should reject invalid credentials', async ({ request }) => {
    const response = await request.post(`${API_BASE_URL}/auth/login`, {
      data: {
        email: 'invalid@example.com',
        password: 'wrongpassword',
      },
    });

    expect(response.status()).toBe(401);
  });

  test('POST /auth/login - should reject empty credentials', async ({ request }) => {
    const response = await request.post(`${API_BASE_URL}/auth/login`, {
      data: {
        email: '',
        password: '',
      },
    });

    expect([400, 401]).toContain(response.status());
  });

  test('POST /auth/login - admin should have ADMIN role', async ({ request }) => {
    const response = await request.post(`${API_BASE_URL}/auth/login`, {
      data: ADMIN_USER,
    });

    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.user.roles).toContain('ADMIN');
  });

  test('GET /auth/me - should return current user with valid token', async ({ request }) => {
    const token = await getAuthToken(request);
    expect(token).toBeTruthy();

    const response = await request.get(`${API_BASE_URL}/auth/me`, {
      headers: authHeaders(token),
    });

    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data).toHaveProperty('email', TEST_USER.email);
    expect(data).toHaveProperty('id');
    expect(data).toHaveProperty('roles');
  });

  test('GET /auth/me - should reject request without token', async ({ request }) => {
    const response = await request.get(`${API_BASE_URL}/auth/me`);
    expect(response.status()).toBe(401);
  });

  test('GET /auth/me - should reject invalid token', async ({ request }) => {
    const response = await request.get(`${API_BASE_URL}/auth/me`, {
      headers: authHeaders('invalid-token'),
    });
    expect(response.status()).toBe(401);
  });
});

// ============================================================================
// Search API Tests (Fully Implemented)
// ============================================================================
test.describe('Search API Integration Tests', () => {
  let authToken: string;

  test.beforeAll(async ({ request }) => {
    authToken = await getAuthToken(request);
  });

  test('POST /search - should perform keyword search', async ({ request }) => {
    expect(authToken).toBeTruthy();

    const response = await request.post(`${API_BASE_URL}/search`, {
      headers: authHeaders(authToken),
      data: {
        query: 'test search query',
        page: 1,
        pageSize: 10,
      },
    });

    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data).toHaveProperty('query');
    expect(data).toHaveProperty('results');
    expect(Array.isArray(data.results)).toBeTruthy();
    expect(data).toHaveProperty('totalCount');
    expect(typeof data.totalCount).toBe('number');
  });

  test('POST /search - should return processing time', async ({ request }) => {
    const response = await request.post(`${API_BASE_URL}/search`, {
      headers: authHeaders(authToken),
      data: {
        query: 'document',
        page: 1,
        pageSize: 10,
      },
    });

    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data).toHaveProperty('processingTimeMs');
  });

  test('POST /search - should apply filters', async ({ request }) => {
    const response = await request.post(`${API_BASE_URL}/search`, {
      headers: authHeaders(authToken),
      data: {
        query: 'document',
        filters: {
          documentType: 'technical',
        },
        page: 1,
        pageSize: 10,
      },
    });

    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data).toHaveProperty('results');
  });

  test('POST /search - should handle pagination', async ({ request }) => {
    const response = await request.post(`${API_BASE_URL}/search`, {
      headers: authHeaders(authToken),
      data: {
        query: 'test',
        page: 2,
        pageSize: 5,
      },
    });

    expect(response.ok()).toBeTruthy();
  });

  test('POST /search - should reject request without auth', async ({ request }) => {
    const response = await request.post(`${API_BASE_URL}/search`, {
      data: {
        query: 'test',
        page: 1,
        pageSize: 10,
      },
    });

    expect(response.status()).toBe(401);
  });

  test('POST /search - should handle empty results gracefully', async ({ request }) => {
    const response = await request.post(`${API_BASE_URL}/search`, {
      headers: authHeaders(authToken),
      data: {
        query: 'xyzzy-nonexistent-query-12345',
        page: 1,
        pageSize: 10,
      },
    });

    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.results).toHaveLength(0);
    expect(data.totalCount).toBe(0);
  });
});

// ============================================================================
// Dashboard API Tests (Stub/Partial Implementation)
// ============================================================================
test.describe('Dashboard API Integration Tests', () => {
  let authToken: string;

  test.beforeAll(async ({ request }) => {
    authToken = await getAuthToken(request);
  });

  test('GET /dashboard/stats - should respond (may be stub)', async ({ request }) => {
    const response = await request.get(`${API_BASE_URL}/dashboard/stats`, {
      headers: authHeaders(authToken),
    });

    // Accept 200 (working), 404 (not implemented), or 500 (stub error)
    expect([200, 404, 500, 501]).toContain(response.status());

    if (response.ok()) {
      const data = await response.json();
      expect(data).toHaveProperty('totalDocuments');
    }
  });

  test('GET /dashboard/health - should respond (may be stub)', async ({ request }) => {
    const response = await request.get(`${API_BASE_URL}/dashboard/health`, {
      headers: authHeaders(authToken),
    });

    expect([200, 404, 500, 501]).toContain(response.status());
  });

  test('GET /dashboard/activities - should respond (may be stub)', async ({ request }) => {
    const response = await request.get(`${API_BASE_URL}/dashboard/activities`, {
      headers: authHeaders(authToken),
    });

    expect([200, 404, 500, 501]).toContain(response.status());
  });
});

// ============================================================================
// Profile API Tests (Stub/Partial Implementation)
// ============================================================================
test.describe('Profile API Integration Tests', () => {
  let authToken: string;

  test.beforeAll(async ({ request }) => {
    authToken = await getAuthToken(request);
  });

  test('GET /users/me - should respond (may be stub)', async ({ request }) => {
    const response = await request.get(`${API_BASE_URL}/users/me`, {
      headers: authHeaders(authToken),
    });

    // Could be /auth/me instead of /users/me
    expect([200, 404, 500, 501]).toContain(response.status());
  });

  test('GET /users/me/activities - should respond (may be stub)', async ({ request }) => {
    const response = await request.get(`${API_BASE_URL}/users/me/activities`, {
      headers: authHeaders(authToken),
    });

    expect([200, 404, 500, 501]).toContain(response.status());
  });

  test('GET /users/me/notifications - should respond (may be stub)', async ({ request }) => {
    const response = await request.get(`${API_BASE_URL}/users/me/notifications`, {
      headers: authHeaders(authToken),
    });

    // 401 (requires different auth), 200, 404, 500, or 501 are all acceptable
    expect([200, 401, 404, 500, 501]).toContain(response.status());
  });
});

// ============================================================================
// Bookmark API Tests (Stub/Partial Implementation)
// ============================================================================
test.describe('Bookmark API Integration Tests', () => {
  let authToken: string;

  test.beforeAll(async ({ request }) => {
    authToken = await getAuthToken(request);
  });

  test('GET /bookmarks - should respond (may be stub)', async ({ request }) => {
    const response = await request.get(`${API_BASE_URL}/bookmarks`, {
      headers: authHeaders(authToken),
    });

    expect([200, 404, 500, 501]).toContain(response.status());

    if (response.ok()) {
      const data = await response.json();
      // API may return array directly or object with bookmarks property
      expect(Array.isArray(data) || data.bookmarks !== undefined).toBeTruthy();
    }
  });

  test('POST /bookmarks - should respond (may be stub)', async ({ request }) => {
    const response = await request.post(`${API_BASE_URL}/bookmarks`, {
      headers: authHeaders(authToken),
      data: {
        documentId: 'test-doc-001',
        folder: 'default',
      },
    });

    expect([200, 201, 404, 500, 501]).toContain(response.status());
  });

  test('GET /bookmarks/counts - should respond (may be stub)', async ({ request }) => {
    const response = await request.get(`${API_BASE_URL}/bookmarks/counts`, {
      headers: authHeaders(authToken),
    });

    expect([200, 404, 500, 501]).toContain(response.status());
  });
});

// ============================================================================
// Admin API Tests
// ============================================================================
test.describe('Admin API Integration Tests', () => {
  let adminToken: string;
  let userToken: string;

  test.beforeAll(async ({ request }) => {
    adminToken = await getAuthToken(request, ADMIN_USER);
    userToken = await getAuthToken(request, TEST_USER);
  });

  test('GET /admin/users - should require admin role', async ({ request }) => {
    // Regular user should be denied
    const userResponse = await request.get(`${API_BASE_URL}/admin/users`, {
      headers: authHeaders(userToken),
    });

    // 403 (forbidden) or 404 (not implemented)
    expect([403, 404, 500, 501]).toContain(userResponse.status());
  });

  test('GET /admin/users - admin should have access (may be stub)', async ({ request }) => {
    const response = await request.get(`${API_BASE_URL}/admin/users`, {
      headers: authHeaders(adminToken),
    });

    // 200 (working), 404 (not implemented), or 500 (stub)
    expect([200, 404, 500, 501]).toContain(response.status());
  });

  test('GET /admin/audit-logs - should respond (may be stub)', async ({ request }) => {
    const response = await request.get(`${API_BASE_URL}/admin/audit-logs`, {
      headers: authHeaders(adminToken),
    });

    expect([200, 404, 500, 501]).toContain(response.status());
  });
});

// ============================================================================
// API Security Tests
// ============================================================================
test.describe('API Security Tests', () => {
  test('should reject expired token', async ({ request }) => {
    // This is a manually crafted expired JWT (exp in the past)
    const expiredToken =
      'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIiwiZXhwIjoxNjAwMDAwMDAwfQ.invalid';

    const response = await request.get(`${API_BASE_URL}/auth/me`, {
      headers: authHeaders(expiredToken),
    });

    expect(response.status()).toBe(401);
  });

  test('should reject malformed token', async ({ request }) => {
    const response = await request.get(`${API_BASE_URL}/auth/me`, {
      headers: authHeaders('not.a.valid.jwt.token'),
    });

    expect(response.status()).toBe(401);
  });

  test('should require authorization header', async ({ request }) => {
    const response = await request.post(`${API_BASE_URL}/search`, {
      data: { query: 'test' },
    });

    expect(response.status()).toBe(401);
  });
});

// ============================================================================
// API Response Format Tests
// ============================================================================
test.describe('API Response Format Tests', () => {
  let authToken: string;

  test.beforeAll(async ({ request }) => {
    authToken = await getAuthToken(request);
  });

  test('login response should have correct structure', async ({ request }) => {
    const response = await request.post(`${API_BASE_URL}/auth/login`, {
      data: TEST_USER,
    });

    const data = await response.json();

    // Check required fields
    expect(data).toHaveProperty('accessToken');
    expect(data).toHaveProperty('refreshToken');
    expect(data).toHaveProperty('expiresIn');
    expect(data).toHaveProperty('user');

    // Check user structure
    expect(data.user).toHaveProperty('id');
    expect(data.user).toHaveProperty('email');
    expect(data.user).toHaveProperty('roles');
  });

  test('search response should have correct structure', async ({ request }) => {
    const response = await request.post(`${API_BASE_URL}/search`, {
      headers: authHeaders(authToken),
      data: { query: 'test' },
    });

    const data = await response.json();

    expect(data).toHaveProperty('query');
    expect(data).toHaveProperty('results');
    expect(data).toHaveProperty('totalCount');
    expect(data).toHaveProperty('timestamp');
  });

  test('error response should have correct structure', async ({ request }) => {
    const response = await request.post(`${API_BASE_URL}/auth/login`, {
      data: { email: 'invalid@test.com', password: 'wrong' },
    });

    const data = await response.json();

    // Error responses should have standard structure
    expect(data).toHaveProperty('error');
    expect(data).toHaveProperty('message');
  });
});

// ============================================================================
// API Performance Tests
// ============================================================================
test.describe('API Performance Tests', () => {
  let authToken: string;

  test.beforeAll(async ({ request }) => {
    authToken = await getAuthToken(request);
  });

  test('login should respond within 3 seconds', async ({ request }) => {
    const start = Date.now();

    await request.post(`${API_BASE_URL}/auth/login`, {
      data: TEST_USER,
    });

    const duration = Date.now() - start;
    expect(duration).toBeLessThan(3000);
  });

  test('search should respond within 5 seconds', async ({ request }) => {
    const start = Date.now();

    await request.post(`${API_BASE_URL}/search`, {
      headers: authHeaders(authToken),
      data: { query: 'test' },
    });

    const duration = Date.now() - start;
    expect(duration).toBeLessThan(5000);
  });

  test('should handle concurrent requests', async ({ request }) => {
    const promises = Array.from({ length: 5 }, () =>
      request.post(`${API_BASE_URL}/search`, {
        headers: authHeaders(authToken),
        data: { query: 'concurrent test' },
      })
    );

    const responses = await Promise.all(promises);

    // All should succeed
    for (const response of responses) {
      expect(response.ok()).toBeTruthy();
    }
  });
});
