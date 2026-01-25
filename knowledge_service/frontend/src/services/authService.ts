/**
 * Auth Service
 *
 * Direct authentication API service (non-Keycloak)
 * - Login/Logout
 * - Token refresh
 * - Password reset
 */
import api from './api';
import type { User } from '@/types';

// API response types
interface LoginRequest {
  email: string;
  password: string;
}

interface LoginResponse {
  user: User;
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
}

interface RefreshTokenRequest {
  refreshToken: string;
}

interface RefreshTokenResponse {
  accessToken: string;
  expiresIn: number;
}

interface PasswordResetRequest {
  email: string;
}

interface PasswordResetConfirmRequest {
  token: string;
  newPassword: string;
}

/**
 * Auth Service
 */
export const authService = {
  /**
   * Login with email and password
   */
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const response = await api.post<LoginResponse>('/auth/login', credentials);
    return response.data;
  },

  /**
   * Logout
   */
  async logout(): Promise<void> {
    try {
      await api.post('/auth/logout');
    } catch (error) {
      // Ignore logout errors - we'll clear local state anyway
      console.warn('Logout API call failed:', error);
    }
  },

  /**
   * Refresh access token
   */
  async refreshToken(refreshToken: string): Promise<RefreshTokenResponse> {
    const response = await api.post<RefreshTokenResponse>('/auth/refresh', {
      refreshToken,
    } as RefreshTokenRequest);
    return response.data;
  },

  /**
   * Request password reset email
   */
  async requestPasswordReset(email: string): Promise<void> {
    await api.post('/auth/password-reset/request', { email } as PasswordResetRequest);
  },

  /**
   * Confirm password reset with token
   */
  async confirmPasswordReset(token: string, newPassword: string): Promise<void> {
    await api.post('/auth/password-reset/confirm', {
      token,
      newPassword,
    } as PasswordResetConfirmRequest);
  },

  /**
   * Validate current token
   */
  async validateToken(): Promise<User | null> {
    try {
      const response = await api.get<{ user: User }>('/auth/me');
      return response.data.user;
    } catch (error) {
      return null;
    }
  },
};

export default authService;
