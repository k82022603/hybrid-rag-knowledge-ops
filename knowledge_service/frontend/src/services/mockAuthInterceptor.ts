/**
 * Mock Auth Interceptor
 *
 * Development-only mock for authentication API
 * This file simulates backend auth responses during development
 */
import type { User } from '@/types';

// Mock user database
const MOCK_USERS: Array<{
  email: string;
  password: string;
  user: User;
}> = [
  {
    email: 'admin@example.com',
    password: 'admin123!',
    user: {
      id: 'user-001',
      username: 'admin',
      email: 'admin@example.com',
      name: 'Admin User',
      firstName: 'Admin',
      lastName: 'User',
      department: 'IT',
      employeeId: 'EMP001',
      roles: ['ADMIN', 'KNOWLEDGE_MANAGER', 'USER'],
    },
  },
  {
    email: 'manager@example.com',
    password: 'manager123!',
    user: {
      id: 'user-002',
      username: 'manager',
      email: 'manager@example.com',
      name: 'Knowledge Manager',
      firstName: 'Knowledge',
      lastName: 'Manager',
      department: 'Knowledge Management',
      employeeId: 'EMP002',
      roles: ['KNOWLEDGE_MANAGER', 'USER'],
    },
  },
  {
    email: 'user@example.com',
    password: 'user123!',
    user: {
      id: 'user-003',
      username: 'user',
      email: 'user@example.com',
      name: 'Regular User',
      firstName: 'Regular',
      lastName: 'User',
      department: 'General',
      employeeId: 'EMP003',
      roles: ['USER'],
    },
  },
];

// Mock token generator
const generateMockToken = (userId: string): string => {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const payload = btoa(
    JSON.stringify({
      sub: userId,
      iat: Math.floor(Date.now() / 1000),
      exp: Math.floor(Date.now() / 1000) + 3600, // 1 hour
    })
  );
  const signature = btoa('mock-signature');
  return `${header}.${payload}.${signature}`;
};

// Response delay simulation
const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Mock login response
 */
export const mockLogin = async (
  email: string,
  password: string
): Promise<Response> => {
  // Simulate network delay
  await delay(500 + Math.random() * 500);

  const mockUser = MOCK_USERS.find(
    (u) => u.email.toLowerCase() === email.toLowerCase() && u.password === password
  );

  if (!mockUser) {
    return new Response(
      JSON.stringify({ message: '이메일 또는 비밀번호가 올바르지 않습니다.' }),
      {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }

  const accessToken = generateMockToken(mockUser.user.id);
  const refreshToken = generateMockToken(mockUser.user.id + '-refresh');

  return new Response(
    JSON.stringify({
      user: mockUser.user,
      accessToken,
      refreshToken,
      expiresIn: 3600,
    }),
    {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }
  );
};

/**
 * Mock token refresh response
 */
export const mockRefreshToken = async (refreshToken: string): Promise<Response> => {
  await delay(200);

  if (!refreshToken) {
    return new Response(
      JSON.stringify({ message: 'Invalid refresh token' }),
      {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }

  const newAccessToken = generateMockToken('refreshed-user');

  return new Response(
    JSON.stringify({
      accessToken: newAccessToken,
      expiresIn: 3600,
    }),
    {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }
  );
};

/**
 * Check if mock auth should be used
 */
export const shouldUseMockAuth = (): boolean => {
  // Use mock auth in development when VITE_USE_MOCK_AUTH is true
  // or when backend is not available
  return (
    import.meta.env.DEV &&
    (import.meta.env.VITE_USE_MOCK_AUTH === 'true' ||
      !import.meta.env.VITE_API_BASE_URL)
  );
};

/**
 * Install mock fetch interceptor
 */
export const installMockAuthInterceptor = (): void => {
  if (!shouldUseMockAuth()) return;

  const originalFetch = window.fetch;

  window.fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const url = typeof input === 'string' ? input : input.toString();

    // Mock auth endpoints
    if (url.includes('/api/v1/auth/login') && init?.method === 'POST') {
      try {
        const body = JSON.parse(init.body as string);
        return await mockLogin(body.email, body.password);
      } catch {
        return new Response(
          JSON.stringify({ message: 'Invalid request' }),
          { status: 400, headers: { 'Content-Type': 'application/json' } }
        );
      }
    }

    if (url.includes('/api/v1/auth/refresh') && init?.method === 'POST') {
      try {
        const body = JSON.parse(init.body as string);
        return await mockRefreshToken(body.refreshToken);
      } catch {
        return new Response(
          JSON.stringify({ message: 'Invalid request' }),
          { status: 400, headers: { 'Content-Type': 'application/json' } }
        );
      }
    }

    if (url.includes('/api/v1/auth/logout') && init?.method === 'POST') {
      await delay(100);
      return new Response(null, { status: 204 });
    }

    if (url.includes('/api/v1/auth/me') && init?.method === 'GET') {
      await delay(100);
      // Return the first mock user for testing
      return new Response(
        JSON.stringify({ user: MOCK_USERS[0].user }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      );
    }

    // Pass through to original fetch for non-auth endpoints
    return originalFetch(input, init);
  };

  console.log('[Mock Auth] Mock auth interceptor installed');
  console.log('[Mock Auth] Test accounts:');
  MOCK_USERS.forEach((u) => {
    console.log(`  - ${u.email} / ${u.password} (${u.user.roles.join(', ')})`);
  });
};

export default installMockAuthInterceptor;
