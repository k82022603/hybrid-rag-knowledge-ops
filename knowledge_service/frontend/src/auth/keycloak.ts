/**
 * Keycloak Configuration
 *
 * Keycloak 인스턴스 설정 및 초기화
 */
import Keycloak from 'keycloak-js';

// Keycloak 설정
const keycloakConfig = {
  url: import.meta.env.VITE_KEYCLOAK_URL || 'http://localhost:8180',
  realm: import.meta.env.VITE_KEYCLOAK_REALM || 'knowledge-platform',
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID || 'knowledge-frontend',
};

// Keycloak 인스턴스 생성
const keycloak = new Keycloak(keycloakConfig);

// Keycloak 초기화 옵션
export const keycloakInitOptions: Keycloak.KeycloakInitOptions = {
  onLoad: 'check-sso',
  silentCheckSsoRedirectUri:
    window.location.origin + '/silent-check-sso.html',
  pkceMethod: 'S256',
  checkLoginIframe: false,
  enableLogging: import.meta.env.DEV,
};

// 토큰 갱신 간격 (만료 2분 전에 갱신)
export const TOKEN_REFRESH_MARGIN = 120; // seconds

// 토큰 갱신 함수
export const refreshToken = async (minValidity = TOKEN_REFRESH_MARGIN): Promise<boolean> => {
  try {
    const refreshed = await keycloak.updateToken(minValidity);
    if (refreshed) {
      console.log('Token refreshed');
    }
    return refreshed;
  } catch (error) {
    console.error('Failed to refresh token:', error);
    return false;
  }
};

// 로그인 함수
export const login = (redirectUri?: string): void => {
  keycloak.login({
    redirectUri: redirectUri || window.location.origin,
  });
};

// 로그아웃 함수
export const logout = (redirectUri?: string): void => {
  keycloak.logout({
    redirectUri: redirectUri || window.location.origin,
  });
};

// 토큰 가져오기
export const getToken = (): string | undefined => {
  return keycloak.token;
};

// 토큰 파싱 정보 가져오기
export const getTokenParsed = (): Keycloak.KeycloakTokenParsed | undefined => {
  return keycloak.tokenParsed;
};

// 인증 여부 확인
export const isAuthenticated = (): boolean => {
  return !!keycloak.authenticated;
};

// 역할 확인
export const hasRole = (role: string): boolean => {
  return keycloak.hasRealmRole(role);
};

// 리소스 역할 확인
export const hasResourceRole = (role: string, resource?: string): boolean => {
  return keycloak.hasResourceRole(role, resource);
};

// 사용자 정보 가져오기
export const getUserInfo = () => {
  const tokenParsed = keycloak.tokenParsed;
  if (!tokenParsed) return null;

  return {
    id: tokenParsed.sub || '',
    username: tokenParsed.preferred_username || '',
    email: tokenParsed.email || '',
    name: tokenParsed.name || '',
    firstName: tokenParsed.given_name || '',
    lastName: tokenParsed.family_name || '',
    department: (tokenParsed as any).department || '',
    employeeId: (tokenParsed as any).employee_id || '',
    roles: tokenParsed.realm_access?.roles || [],
  };
};

export default keycloak;
