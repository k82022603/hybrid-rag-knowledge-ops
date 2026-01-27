/**
 * KeycloakProvider
 *
 * Keycloak 인증 상태를 관리하는 React Context Provider
 * Direct login (Redux) + Keycloak SSO 통합 지원
 *
 * Features:
 * - Keycloak SSO 초기화 (check-sso + PKCE S256)
 * - Direct login fallback (Redux 기반)
 * - 토큰 자동 갱신 (만료 5분 전 Silent Refresh)
 * - onTokenExpired 이벤트 핸들링
 * - 인증 상태 Context 제공
 */
import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  useMemo,
  useRef,
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

/** Authentication context type exposed via useAuth hook */
export interface AuthContextType {
  /** Whether Keycloak has been initialized (or skipped) */
  isInitialized: boolean;
  /** Whether user is authenticated (via Keycloak SSO or direct login) */
  isAuthenticated: boolean;
  /** Whether initialization or login is in progress */
  isLoading: boolean;
  /** Current user information */
  user: User | null;
  /** Current access token (Keycloak managed) */
  token: string | undefined;
  /** Which authentication method is active */
  authMethod: 'keycloak' | 'direct' | null;
  /** Redirect to Keycloak login page */
  login: (redirectUri?: string) => void;
  /** Logout from Keycloak and clear session */
  logout: (redirectUri?: string) => void;
  /** Manually trigger token refresh */
  refreshToken: () => Promise<boolean>;
  /** Check if user has a specific realm role */
  hasRole: (role: string) => boolean;
  /** Check if user has a specific resource role */
  hasResourceRole: (role: string, resource?: string) => boolean;
}

// Context
const AuthContext = createContext<AuthContextType | undefined>(undefined);

/** Provider Props */
interface KeycloakProviderProps {
  children: ReactNode;
  /** Component to show while initializing */
  loadingComponent?: ReactNode;
  /** Callback when authentication succeeds */
  onAuthSuccess?: (user: User) => void;
  /** Callback when authentication fails */
  onAuthError?: (error: Error) => void;
  /** Callback when user logs out */
  onAuthLogout?: () => void;
}

/**
 * KeycloakProvider component
 *
 * Wraps the application to provide authentication context.
 * Supports both Keycloak SSO and direct (Redux-based) login.
 *
 * @example
 * ```tsx
 * <KeycloakProvider
 *   loadingComponent={<LoadingScreen />}
 *   onAuthSuccess={(user) => console.log('Logged in:', user.username)}
 * >
 *   <App />
 * </KeycloakProvider>
 * ```
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

  // Ref to track token refresh interval for proper cleanup
  const refreshIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

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

  // Update user info from Keycloak token
  const updateUserInfo = useCallback(() => {
    const userInfo = getUserInfo();
    if (userInfo) {
      setKeycloakUser(userInfo);
      setKeycloakToken(getToken());
      return userInfo;
    }
    return null;
  }, []);

  // Set up automatic token refresh interval
  const setupTokenRefresh = useCallback(() => {
    // Clear any existing interval
    if (refreshIntervalRef.current) {
      clearInterval(refreshIntervalRef.current);
      refreshIntervalRef.current = null;
    }

    // Refresh token periodically (every 60 seconds, requesting validity for TOKEN_REFRESH_MARGIN)
    // TOKEN_REFRESH_MARGIN = 300s (5 min), so Keycloak will only refresh if expiry < 5 min away
    refreshIntervalRef.current = setInterval(async () => {
      if (keycloak.authenticated) {
        try {
          const success = await refreshToken(TOKEN_REFRESH_MARGIN);
          if (success) {
            updateUserInfo();
          }
        } catch (error) {
          console.error('[Auth] Periodic token refresh failed:', error);
        }
      }
    }, 60 * 1000); // Check every 60 seconds
  }, [updateUserInfo]);

  // Keycloak initialization
  useEffect(() => {
    let mounted = true;

    const initKeycloak = async () => {
      try {
        // Skip Keycloak init if already authenticated via Redux (direct login)
        if (isReduxAuthenticated) {
          console.log('[Auth] Using Redux direct login - skipping Keycloak init');
          if (mounted) {
            setIsInitialized(true);
            setIsLoading(false);
          }
          return;
        }

        const authenticated = await keycloak.init(keycloakInitOptions);

        if (!mounted) return;

        setIsKeycloakAuthenticated(authenticated);
        setIsInitialized(true);

        if (authenticated) {
          const userInfo = updateUserInfo();
          if (userInfo && onAuthSuccess) {
            onAuthSuccess(userInfo);
          }

          // Set up automatic token refresh
          setupTokenRefresh();
        }
      } catch (error) {
        console.error('[Auth] Keycloak initialization failed:', error);
        if (mounted) {
          setIsInitialized(true);
          // Don't treat Keycloak init failure as error if we can use direct login
          if (!isReduxAuthenticated && onAuthError) {
            onAuthError(error instanceof Error ? error : new Error('Keycloak init failed'));
          }
        }
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    };

    initKeycloak();

    // Keycloak event handlers
    keycloak.onAuthSuccess = () => {
      if (!mounted) return;
      setIsKeycloakAuthenticated(true);
      const userInfo = updateUserInfo();
      if (userInfo && onAuthSuccess) {
        onAuthSuccess(userInfo);
      }
    };

    keycloak.onAuthError = (error) => {
      console.error('[Auth] Authentication error:', error);
      if (!mounted) return;
      setIsKeycloakAuthenticated(false);
      setKeycloakUser(null);
      setKeycloakToken(undefined);
      if (onAuthError) {
        onAuthError(new Error(error?.error || 'Authentication error'));
      }
    };

    keycloak.onAuthLogout = () => {
      if (!mounted) return;
      setIsKeycloakAuthenticated(false);
      setKeycloakUser(null);
      setKeycloakToken(undefined);
      if (onAuthLogout) {
        onAuthLogout();
      }
    };

    keycloak.onTokenExpired = async () => {
      console.log('[Auth] Token expired, attempting refresh...');
      try {
        const success = await refreshToken(TOKEN_REFRESH_MARGIN);
        if (success) {
          if (mounted) updateUserInfo();
          console.log('[Auth] Token refreshed after expiry');
        } else {
          console.warn('[Auth] Token refresh returned false, logging out');
          keycloakLogout();
        }
      } catch (error) {
        console.error('[Auth] Token refresh failed after expiry:', error);
        keycloakLogout();
      }
    };

    keycloak.onAuthRefreshSuccess = () => {
      if (mounted) updateUserInfo();
    };

    keycloak.onAuthRefreshError = () => {
      console.error('[Auth] Token refresh error');
      if (!mounted) return;
      setIsKeycloakAuthenticated(false);
      setKeycloakUser(null);
      setKeycloakToken(undefined);
    };

    // Cleanup
    return () => {
      mounted = false;
      keycloak.onAuthSuccess = undefined;
      keycloak.onAuthError = undefined;
      keycloak.onAuthLogout = undefined;
      keycloak.onTokenExpired = undefined;
      keycloak.onAuthRefreshSuccess = undefined;
      keycloak.onAuthRefreshError = undefined;

      // Clean up token refresh interval
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
        refreshIntervalRef.current = null;
      }
    };
  }, [onAuthSuccess, onAuthError, onAuthLogout, updateUserInfo, isReduxAuthenticated, setupTokenRefresh]);

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
