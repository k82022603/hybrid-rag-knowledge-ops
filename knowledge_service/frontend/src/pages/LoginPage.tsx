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
      <div className="flex items-center justify-center min-h-screen bg-dark-200">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-neon-cyan mx-auto" />
          <p className="mt-4 text-gray-400">Loading system...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-dark-200 relative overflow-hidden px-4 py-12">
      {/* Background Ambient Glow */}
      <div className="absolute top-0 left-0 w-full h-full bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-neon-purple/20 via-dark-200 to-dark-300 -z-10 pointer-events-none" />
      <div className="absolute bottom-0 left-0 w-1/2 h-1/2 bg-[radial-gradient(ellipse_at_bottom_left,_var(--tw-gradient-stops))] from-neon-cyan/10 via-transparent to-transparent -z-10 pointer-events-none" />

      {/* Grid Pattern Overlay */}
      <div className="absolute inset-0 bg-[url('/grid.svg')] bg-center [mask-image:linear-gradient(180deg,white,rgba(255,255,255,0))] opacity-20 pointer-events-none" />

      <div className="relative max-w-md w-full">
        {/* Logo and Title */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br from-neon-cyan/20 to-neon-purple/20 mb-6 shadow-[0_0_30px_rgba(6,182,212,0.3)] backdrop-blur-xl border border-white/10 relative group">
            <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-neon-cyan to-neon-purple opacity-0 group-hover:opacity-20 transition-opacity duration-500" />
            <span className="text-4xl font-bold text-white relative z-10 font-display">N</span>
          </div>
          <h1 className="text-4xl font-bold font-display text-white tracking-widest text-glow mb-2">
            NEXUS
          </h1>
          <p className="text-sm text-neon-cyan/80 font-medium tracking-wider uppercase">
            Intelligent Knowledge Operations
          </p>
        </div>

        {/* Login Card */}
        <div className="glass-panel p-8 border border-white/10 shadow-[0_0_50px_rgba(0,0,0,0.5)] relative overflow-hidden">
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-neon-cyan via-neon-purple to-neon-pink" />
          <LoginForm
            onForgotPassword={handleForgotPassword}
            onSSOLogin={handleSSOLogin}
            redirectPath={from}
          />
        </div>

        {/* Development Info */}
        {import.meta.env.DEV && import.meta.env.VITE_DEV_TEST_ACCOUNTS && (
          <div className="mt-6 p-4 bg-yellow-900/10 rounded-xl border border-yellow-800/30 backdrop-blur-sm">
            <h3 className="text-sm font-medium text-yellow-500 mb-2 uppercase tracking-wide">
              System Access Codes (Dev)
            </h3>
            <ul className="text-xs text-yellow-600/80 font-mono space-y-1">
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
        <div className="text-center mt-8 space-y-2">
          <p className="text-xs text-gray-500 font-mono">
            SECURE ACCESS REQUIRED
          </p>
          <p className="text-[10px] text-gray-600">
            © 2026 NEXUS System · Classification: CONFIDENTIAL
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
