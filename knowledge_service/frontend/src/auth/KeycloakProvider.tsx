/**
 * KeycloakProvider
 *
 * Keycloak 인증 상태를 관리하는 React Context Provider
 */
import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  useMemo,
  type ReactNode,
} from 'react';
import keycloak, {
  keycloakInitOptions,
  refreshToken,
  login as keycloakLogin,
  logout as keycloakLogout,
  getToken,
  getUserInfo,
  hasRole,
  hasResourceRole,
  TOKEN_REFRESH_MARGIN,
} from './keycloak';
import type { User } from '@/types';

// 인증 컨텍스트 타입
interface AuthContextType {
  isInitialized: boolean;
  isAuthenticated: boolean;
  isLoading: boolean;
  user: User | null;
  token: string | undefined;
  login: (redirectUri?: string) => void;
  logout: (redirectUri?: string) => void;
  refreshToken: () => Promise<boolean>;
  hasRole: (role: string) => boolean;
  hasResourceRole: (role: string, resource?: string) => boolean;
}

// 컨텍스트 생성
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Provider Props
interface KeycloakProviderProps {
  children: ReactNode;
  loadingComponent?: ReactNode;
  onAuthSuccess?: (user: User) => void;
  onAuthError?: (error: Error) => void;
  onAuthLogout?: () => void;
}

/**
 * Keycloak Provider 컴포넌트
 */
export const KeycloakProvider: React.FC<KeycloakProviderProps> = ({
  children,
  loadingComponent,
  onAuthSuccess,
  onAuthError,
  onAuthLogout,
}) => {
  const [isInitialized, setIsInitialized] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | undefined>(undefined);

  // 사용자 정보 업데이트
  const updateUserInfo = useCallback(() => {
    const userInfo = getUserInfo();
    if (userInfo) {
      setUser(userInfo);
      setToken(getToken());
      return userInfo;
    }
    return null;
  }, []);

  // Keycloak 초기화
  useEffect(() => {
    const initKeycloak = async () => {
      try {
        const authenticated = await keycloak.init(keycloakInitOptions);

        setIsAuthenticated(authenticated);
        setIsInitialized(true);

        if (authenticated) {
          const userInfo = updateUserInfo();
          if (userInfo && onAuthSuccess) {
            onAuthSuccess(userInfo);
          }

          // 토큰 자동 갱신 설정
          setupTokenRefresh();
        }
      } catch (error) {
        console.error('Keycloak initialization failed:', error);
        setIsInitialized(true);
        if (onAuthError) {
          onAuthError(error instanceof Error ? error : new Error('Keycloak init failed'));
        }
      } finally {
        setIsLoading(false);
      }
    };

    initKeycloak();

    // Keycloak 이벤트 핸들러
    keycloak.onAuthSuccess = () => {
      setIsAuthenticated(true);
      const userInfo = updateUserInfo();
      if (userInfo && onAuthSuccess) {
        onAuthSuccess(userInfo);
      }
    };

    keycloak.onAuthError = (error) => {
      console.error('Auth error:', error);
      setIsAuthenticated(false);
      setUser(null);
      setToken(undefined);
      if (onAuthError) {
        onAuthError(new Error(error?.error || 'Authentication error'));
      }
    };

    keycloak.onAuthLogout = () => {
      setIsAuthenticated(false);
      setUser(null);
      setToken(undefined);
      if (onAuthLogout) {
        onAuthLogout();
      }
    };

    keycloak.onTokenExpired = async () => {
      console.log('Token expired, attempting refresh...');
      const success = await refreshToken();
      if (success) {
        updateUserInfo();
      } else {
        // 갱신 실패 시 로그아웃
        keycloakLogout();
      }
    };

    keycloak.onAuthRefreshSuccess = () => {
      updateUserInfo();
    };

    keycloak.onAuthRefreshError = () => {
      console.error('Token refresh failed');
      setIsAuthenticated(false);
      setUser(null);
      setToken(undefined);
    };

    // Cleanup
    return () => {
      keycloak.onAuthSuccess = undefined;
      keycloak.onAuthError = undefined;
      keycloak.onAuthLogout = undefined;
      keycloak.onTokenExpired = undefined;
      keycloak.onAuthRefreshSuccess = undefined;
      keycloak.onAuthRefreshError = undefined;
    };
  }, [onAuthSuccess, onAuthError, onAuthLogout, updateUserInfo]);

  // 토큰 자동 갱신 설정
  const setupTokenRefresh = useCallback(() => {
    // 토큰 만료 전에 갱신하도록 인터벌 설정
    const refreshInterval = setInterval(async () => {
      if (keycloak.authenticated) {
        const success = await refreshToken(TOKEN_REFRESH_MARGIN);
        if (success) {
          updateUserInfo();
        }
      }
    }, (TOKEN_REFRESH_MARGIN - 30) * 1000); // 만료 30초 전에 갱신 시도

    return () => clearInterval(refreshInterval);
  }, [updateUserInfo]);

  // 로그인 함수
  const login = useCallback((redirectUri?: string) => {
    setIsLoading(true);
    keycloakLogin(redirectUri);
  }, []);

  // 로그아웃 함수
  const logout = useCallback((redirectUri?: string) => {
    setIsLoading(true);
    keycloakLogout(redirectUri);
  }, []);

  // 토큰 갱신 함수
  const handleRefreshToken = useCallback(async () => {
    const success = await refreshToken();
    if (success) {
      updateUserInfo();
    }
    return success;
  }, [updateUserInfo]);

  // 역할 확인 함수
  const checkRole = useCallback((role: string) => {
    return hasRole(role);
  }, []);

  // 리소스 역할 확인 함수
  const checkResourceRole = useCallback((role: string, resource?: string) => {
    return hasResourceRole(role, resource);
  }, []);

  // 컨텍스트 값
  const contextValue = useMemo(
    () => ({
      isInitialized,
      isAuthenticated,
      isLoading,
      user,
      token,
      login,
      logout,
      refreshToken: handleRefreshToken,
      hasRole: checkRole,
      hasResourceRole: checkResourceRole,
    }),
    [
      isInitialized,
      isAuthenticated,
      isLoading,
      user,
      token,
      login,
      logout,
      handleRefreshToken,
      checkRole,
      checkResourceRole,
    ]
  );

  // 초기화 중일 때 로딩 컴포넌트 표시
  if (!isInitialized || isLoading) {
    return (
      <>
        {loadingComponent || (
          <div className="flex items-center justify-center min-h-screen bg-gray-50 dark:bg-gray-900">
            <div className="text-center">
              <div className="spinner-lg text-primary-600 mx-auto mb-4" />
              <p className="text-gray-600 dark:text-gray-400">Loading...</p>
            </div>
          </div>
        )}
      </>
    );
  }

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};

/**
 * useAuth 훅
 *
 * 인증 컨텍스트에 접근하기 위한 커스텀 훅
 */
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within a KeycloakProvider');
  }
  return context;
};

export default KeycloakProvider;
