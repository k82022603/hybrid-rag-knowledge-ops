import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios';
import keycloak, { refreshToken, logout } from '@/auth/keycloak';

/**
 * Axios 인스턴스 설정
 *
 * 기본 URL과 공통 헤더를 설정하고 인터셉터를 추가
 */
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Request interceptor - Keycloak 토큰 추가
api.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    // 토큰이 만료 임박한 경우 갱신
    if (keycloak.authenticated) {
      const tokenExpiry = keycloak.tokenParsed?.exp;
      const now = Math.floor(Date.now() / 1000);

      // 토큰이 2분 이내에 만료되면 갱신
      if (tokenExpiry && tokenExpiry - now < 120) {
        try {
          await refreshToken(120);
        } catch (error) {
          console.error('Failed to refresh token before request:', error);
        }
      }

      // Authorization 헤더에 토큰 추가
      if (keycloak.token) {
        config.headers.Authorization = `Bearer ${keycloak.token}`;
      }
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor - 에러 처리
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    // 401 Unauthorized 처리
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        // 토큰 갱신 시도
        const refreshed = await refreshToken(0);

        if (refreshed && keycloak.token) {
          // 새 토큰으로 원래 요청 재시도
          originalRequest.headers.Authorization = `Bearer ${keycloak.token}`;
          return api(originalRequest);
        } else {
          // 갱신 실패 시 로그아웃
          console.error('Token refresh failed - logging out');
          logout();
        }
      } catch (refreshError) {
        console.error('Error during token refresh:', refreshError);
        logout();
      }
    }

    // 403 Forbidden 처리
    if (error.response?.status === 403) {
      console.error('Access denied - insufficient permissions');
      // 권한 부족 알림 또는 리다이렉트 처리 가능
    }

    // 500 Server Error 처리
    if (error.response?.status && error.response.status >= 500) {
      console.error('Server error:', error.response.data);
    }

    return Promise.reject(error);
  }
);

export default api;
