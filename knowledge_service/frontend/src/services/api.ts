import axios from 'axios';

/**
 * Axios 인스턴스 설정
 *
 * 기본 URL과 공통 헤더를 설정하고 인터셉터를 추가
 */
const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // TODO: Keycloak 토큰 추가
    // const token = keycloak.token;
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`;
    // }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // TODO: 토큰 갱신 또는 로그인 페이지로 리다이렉트
      console.error('Unauthorized - redirecting to login');
    }
    return Promise.reject(error);
  }
);

export default api;
