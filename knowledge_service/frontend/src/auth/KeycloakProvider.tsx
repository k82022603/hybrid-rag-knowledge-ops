/**
 * KeycloakProvider
 *
 * Keycloak 인증 상태를 관리하는 React Context Provider
 * Direct login (Redux) + Keycloak SSO 통합 지원
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
import { useSelector } from 'react-redux';
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
import { selectIsAuthenticated as selectReduxAuth, selectUser as selectReduxUser } from '@/store/slices/authSlice';
import type { User } from '@/types';

// 인증 컨텍스트 타입
interface AuthContextType {
  isInitialized: boolean;
  isAuthenticated: boolean;
  isLoading: boolean;
  user: User | null;
  token: string | undefined;
  authMethod: 'keycloak' | 'direct' | null;
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
  // Keycloak state
  const [isInitialized, setIsInitialized] = useState(false);
  const [isKeycloakAuthenticated, setIsKeycloakAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [keycloakUser, setKeycloakUser] = useState<User | null>(null);
  const [keycloakToken, setKeycloakToken] = useState<string | undefined>(undefined);

  // Redux direct auth state
  const isReduxAuthenticated = useSelector(selectReduxAuth);
  const reduxUser = useSelector(selectReduxUser);

  // Combined auth state - either Keycloak or Redux
  const isAuthenticated = isKeycloakAuthenticated || isReduxAuthenticated;
  const user = keycloakUser || reduxUser;
  const token = keycloakToken;
  const authMethod: 'keycloak' | 'direct' | null = isKeycloakAuthenticated
    ? 'keycloak'
    : isReduxAuthenticated
      ? 'direct'
      : null;

  // 사용자 정보 업데이트 (Keycloak)
  const updateUserInfo = useCallback(() => {
    const userInfo = getUserInfo();
    if (userInfo) {
      setKeycloakUser(userInfo);
      setKeycloakToken(getToken());
      return userInfo;
    }
    return null;
  }, []);

  // Keycloak 초기화
  useEffect(() => {
    const initKeycloak = async () => {
      try {
        // Skip Keycloak init if already authenticated via Redux (direct login)
        if (isReduxAuthenticated) {
          console.log('[Auth] Using Redux direct login - skipping Keycloak init');
          setIsInitialized(true);
          setIsLoading(false);
          return;
        }

        const authenticated = await keycloak.init(keycloakInitOptions);

        setIsKeycloakAuthenticated(authenticated);
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
        // Don't treat Keycloak init failure as error if we can use direct login
        if (!isReduxAuthenticated && onAuthError) {
          onAuthError(error instanceof Error ? error : new Error('Keycloak init failed'));
        }
      } finally {
        setIsLoading(false);
      }
    };

    initKeycloak();

    // Keycloak 이벤트 핸들러
    keycloak.onAuthSuccess = () => {
      setIsKeycloakAuthenticated(true);
      const userInfo = updateUserInfo();
      if (userInfo && onAuthSuccess) {
        onAuthSuccess(userInfo);
      }
    };

    keycloak.onAuthError = (error) => {
      console.error('Auth error:', error);
      setIsKeycloakAuthenticated(false);
      setKeycloakUser(null);
      setKeycloakToken(undefined);
      if (onAuthError) {
        onAuthError(new Error(error?.error || 'Authentication error'));
      }
    };

    keycloak.onAuthLogout = () => {
      setIsKeycloakAuthenticated(false);
      setKeycloakUser(null);
      setKeycloakToken(undefined);
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
      setIsKeycloakAuthenticated(false);
      setKeycloakUser(null);
      setKeycloakToken(undefined);
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
  }, [onAuthSuccess, onAuthError, onAuthLogout, updateUserInfo, isReduxAuthenticated]);

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

  // 리소스 역할 확인 함수
  const checkResourceRole = useCallback((role: string, resource?: string) => {
    return hasResourceRole(role, resource);
  }, []);

  // Role check that works with both Keycloak and Redux
  const checkRoleWithFallback = useCallback((role: string) => {
    // Check Keycloak role first
    if (isKeycloakAuthenticated) {
      return hasRole(role);
    }
    // Fall back to Redux user roles
    if (reduxUser?.roles) {
      return reduxUser.roles.includes(role);
    }
    return false;
  }, [isKeycloakAuthenticated, reduxUser]);

  // 컨텍스트 값
  const contextValue = useMemo(
    () => ({
      isInitialized,
      isAuthenticated,
      isLoading,
      user,
      token,
      authMethod,
      login,
      logout,
      refreshToken: handleRefreshToken,
      hasRole: checkRoleWithFallback,
      hasResourceRole: checkResourceRole,
    }),
    [
      isInitialized,
      isAuthenticated,
      isLoading,
      user,
      token,
      authMethod,
      login,
      logout,
      handleRefreshToken,
      checkRoleWithFallback,
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
