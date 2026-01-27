import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios';
import keycloak, { refreshToken, logout, TOKEN_REFRESH_MARGIN } from '@/auth/keycloak';

/**
 * Axios API 인스턴스
 *
 * 기본 URL과 공통 헤더를 설정하고 인증 인터셉터를 추가.
 * Keycloak SSO 토큰 또는 Direct login 토큰을 자동으로 요청에 포함.
 */
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

/**
 * Request interceptor - 인증 토큰 자동 추가
 *
 * 1. Keycloak 인증: 토큰 만료 임박 시 자동 갱신 후 Bearer 토큰 추가
 * 2. Direct 인증: localStorage에서 토큰 읽어서 Bearer 토큰 추가
 */
api.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    // Strategy 1: Keycloak SSO token
    if (keycloak.authenticated) {
      const tokenExpiry = keycloak.tokenParsed?.exp;
      const now = Math.floor(Date.now() / 1000);

      // 토큰이 5분 이내에 만료되면 갱신 (TOKEN_REFRESH_MARGIN = 300s)
      if (tokenExpiry && tokenExpiry - now < TOKEN_REFRESH_MARGIN) {
        try {
          await refreshToken(TOKEN_REFRESH_MARGIN);
        } catch (error) {
          console.error('[API] Failed to refresh Keycloak token before request:', error);
        }
      }

      // Authorization 헤더에 Keycloak 토큰 추가
      if (keycloak.token) {
        config.headers.Authorization = `Bearer ${keycloak.token}`;
      }
    } else {
      // Strategy 2: Direct login token from localStorage
      const directToken = localStorage.getItem('auth_access_token');
      if (directToken) {
        config.headers.Authorization = `Bearer ${directToken}`;
      }
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

/**
 * Response interceptor - 인증 에러 및 서버 에러 처리
 *
 * - 401: Keycloak 토큰 갱신 시도 후 재요청, 실패 시 로그아웃
 * - 403: 권한 부족 로깅
 * - 500+: 서버 에러 로깅
 */
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    // 401 Unauthorized - attempt token refresh and retry
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      // Only try Keycloak refresh if Keycloak is the auth method
      if (keycloak.authenticated) {
        try {
          const refreshed = await refreshToken(0);

          if (refreshed && keycloak.token) {
            // Retry original request with new token
            originalRequest.headers.Authorization = `Bearer ${keycloak.token}`;
            return api(originalRequest);
          } else {
            console.error('[API] Keycloak token refresh failed - logging out');
            logout();
          }
        } catch (refreshError) {
          console.error('[API] Error during Keycloak token refresh:', refreshError);
          logout();
        }
      } else {
        // Direct login - clear stored tokens and redirect to login
        console.error('[API] Direct auth token invalid/expired');
        localStorage.removeItem('auth_access_token');
        localStorage.removeItem('auth_refresh_token');
        localStorage.removeItem('auth_user');
        localStorage.removeItem('auth_method');
        window.location.href = '/login';
      }
    }

    // 403 Forbidden
    if (error.response?.status === 403) {
      console.error('[API] Access denied - insufficient permissions');
    }

    // 500+ Server Error
    if (error.response?.status && error.response.status >= 500) {
      console.error('[API] Server error:', error.response.status, error.response.data);
    }

    return Promise.reject(error);
  }
);

export default api;
