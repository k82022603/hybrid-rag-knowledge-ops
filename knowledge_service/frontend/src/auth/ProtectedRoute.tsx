/**
 * ProtectedRoute
 *
 * 인증된 사용자만 접근 가능한 라우트를 보호하는 컴포넌트
 * Keycloak SSO 및 Direct Login 모두 지원
 */
import React, { type ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from './KeycloakProvider';

interface ProtectedRouteProps {
  children: ReactNode;
  requiredRoles?: string[];
  requiredResourceRoles?: { role: string; resource?: string }[];
  redirectTo?: string;
  fallback?: ReactNode;
}

/**
 * ProtectedRoute 컴포넌트
 *
 * @param children - 보호할 컴포넌트
 * @param requiredRoles - 필요한 Realm 역할 목록 (OR 조건)
 * @param requiredResourceRoles - 필요한 리소스 역할 목록 (OR 조건)
 * @param redirectTo - 인증되지 않은 경우 리다이렉트할 경로
 * @param fallback - 권한이 없을 때 표시할 컴포넌트
 */
export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requiredRoles = [],
  requiredResourceRoles = [],
  redirectTo = '/login',
  fallback,
}) => {
  const { isAuthenticated, isInitialized, isLoading, hasRole, hasResourceRole } = useAuth();
  const location = useLocation();

  // 초기화 중이거나 로딩 중일 때
  if (!isInitialized || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="text-center">
          <div className="spinner-lg text-primary-600 mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Loading...</p>
        </div>
      </div>
    );
  }

  // 인증되지 않은 경우
  if (!isAuthenticated) {
    // Direct login page로 리다이렉트 (Keycloak 대신)
    // SSO 로그인은 LoginPage에서 사용자가 직접 선택하도록 변경
    return <Navigate to={redirectTo} state={{ from: location }} replace />;
  }

  // 역할 확인 (OR 조건: 하나라도 있으면 통과)
  if (requiredRoles.length > 0) {
    const hasRequiredRole = requiredRoles.some((role) => hasRole(role));
    if (!hasRequiredRole) {
      // 권한 없음 - fallback 또는 접근 거부 페이지
      if (fallback) {
        return <>{fallback}</>;
      }
      return <AccessDenied />;
    }
  }

  // 리소스 역할 확인 (OR 조건)
  if (requiredResourceRoles.length > 0) {
    const hasRequiredResourceRole = requiredResourceRoles.some(({ role, resource }) =>
      hasResourceRole(role, resource)
    );
    if (!hasRequiredResourceRole) {
      if (fallback) {
        return <>{fallback}</>;
      }
      return <AccessDenied />;
    }
  }

  // 모든 조건 통과
  return <>{children}</>;
};

/**
 * 접근 거부 컴포넌트
 */
const AccessDenied: React.FC = () => {
  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="text-center max-w-md px-4">
        <div className="mb-6">
          <svg
            className="mx-auto h-16 w-16 text-error-500"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
        </div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
          Access Denied
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mb-6">
          You do not have permission to access this page.
          Please contact your administrator if you believe this is an error.
        </p>
        <a
          href="/"
          className="btn-primary inline-flex items-center"
        >
          <svg
            className="mr-2 h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"
            />
          </svg>
          Go to Home
        </a>
      </div>
    </div>
  );
};

/**
 * RequireAuth 컴포넌트
 *
 * 간단한 인증 체크용 래퍼 컴포넌트
 */
export const RequireAuth: React.FC<{ children: ReactNode }> = ({ children }) => {
  return <ProtectedRoute>{children}</ProtectedRoute>;
};

/**
 * RequireAdmin 컴포넌트
 *
 * 관리자 역할 필요 래퍼 컴포넌트
 */
export const RequireAdmin: React.FC<{ children: ReactNode }> = ({ children }) => {
  return <ProtectedRoute requiredRoles={['ADMIN']}>{children}</ProtectedRoute>;
};

/**
 * RequireKnowledgeManager 컴포넌트
 *
 * 지식 관리자 역할 필요 래퍼 컴포넌트
 */
export const RequireKnowledgeManager: React.FC<{ children: ReactNode }> = ({ children }) => {
  return (
    <ProtectedRoute requiredRoles={['KNOWLEDGE_MANAGER', 'ADMIN']}>
      {children}
    </ProtectedRoute>
  );
};

export default ProtectedRoute;
