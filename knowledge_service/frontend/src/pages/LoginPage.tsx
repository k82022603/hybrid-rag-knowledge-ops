/**
 * LoginPage
 *
 * 로그인 페이지 - 직접 로그인(이메일/비밀번호) + Keycloak SSO 지원
 *
 * Features:
 * - Direct login form (email + password)
 * - Keycloak SSO login button
 * - Auto-redirect if already authenticated
 * - Redirect to original page after login
 * - Development mode test account display
 */
import React, { useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/auth';
import { LoginForm } from '@/components/auth';

interface LocationState {
  from?: {
    pathname: string;
  };
}

const LoginPage: React.FC = () => {
  const { isAuthenticated, isLoading, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // Get the page user was trying to access before being redirected to login
  const from = (location.state as LocationState)?.from?.pathname || '/dashboard';

  useEffect(() => {
    // Already authenticated - redirect to original page or dashboard
    if (isAuthenticated) {
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, from]);

  const handleSSOLogin = () => {
    // Keycloak SSO login - redirect to Keycloak login page
    login(window.location.origin + from);
  };

  const handleForgotPassword = () => {
    // TODO: Implement forgot password modal or page navigation
    console.log('[LoginPage] Forgot password clicked');
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto" />
          <p className="mt-4 text-gray-600 dark:text-gray-400">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 via-primary-50/30 to-accent-50/20 dark:from-gray-900 dark:via-gray-900 dark:to-gray-800 px-4 py-12">
      {/* Decorative background pattern */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none" aria-hidden="true">
        <div className="absolute -top-40 -right-40 w-80 h-80 rounded-full bg-primary-100/40 dark:bg-primary-900/10 blur-3xl" />
        <div className="absolute -bottom-40 -left-40 w-80 h-80 rounded-full bg-accent-100/30 dark:bg-accent-900/10 blur-3xl" />
      </div>

      <div className="relative max-w-md w-full">
        {/* Logo and Title */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-500 to-primary-700 text-white mb-5 shadow-lg shadow-primary-500/25">
            <svg
              className="w-8 h-8"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
              />
            </svg>
          </div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white tracking-tight">
            Knowledge Portal
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
            Graph RAG 기반 지능형 지식 검색 시스템
          </p>
        </div>

        {/* Login Card */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl shadow-gray-200/50 dark:shadow-none dark:border dark:border-gray-700 p-8">
          <LoginForm
            onForgotPassword={handleForgotPassword}
            onSSOLogin={handleSSOLogin}
            redirectPath={from}
          />
        </div>

        {/* Development Info */}
        {import.meta.env.DEV && import.meta.env.VITE_DEV_TEST_ACCOUNTS && (
          <div className="mt-6 p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-xl border border-yellow-200 dark:border-yellow-800">
            <h3 className="text-sm font-medium text-yellow-800 dark:text-yellow-200 mb-2">
              Development Mode - Test Accounts
            </h3>
            <ul className="text-xs text-yellow-700 dark:text-yellow-300 space-y-1">
              {(import.meta.env.VITE_DEV_TEST_ACCOUNTS as string).split(',').map((account, index) => {
                const [email, password] = account.split(':');
                const role = email.split('@')[0].charAt(0).toUpperCase() + email.split('@')[0].slice(1);
                return (
                  <li key={index}>{role}: {email} / {password}</li>
                );
              })}
            </ul>
          </div>
        )}

        {/* Footer */}
        <div className="text-center mt-8 space-y-1.5">
          <p className="text-xs text-gray-400 dark:text-gray-500">
            SSO: Keycloak · Direct Login: API Gateway
          </p>
          <p className="text-[11px] text-gray-300 dark:text-gray-600">
            © 2026 Knowledge Portal
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
