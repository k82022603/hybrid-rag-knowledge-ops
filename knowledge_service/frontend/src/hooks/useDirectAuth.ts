/**
 * useDirectAuth Hook
 *
 * Redux-based direct authentication hook
 * For use cases where Keycloak SSO is not used
 */
import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  loginAsync,
  logout as logoutAction,
  clearError,
  selectAuth,
} from '@/store/slices/authSlice';
import { useAppDispatch, useAppSelector } from '@/store';
import { authService } from '@/services';

/**
 * Direct authentication hook
 *
 * Provides login/logout functionality using Redux state management
 * rather than Keycloak SSO
 */
export const useDirectAuth = () => {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const auth = useAppSelector(selectAuth);

  /**
   * Login with email and password
   */
  const login = useCallback(
    async (email: string, password: string, rememberMe = false) => {
      try {
        const result = await dispatch(
          loginAsync({ email, password, rememberMe })
        ).unwrap();
        return result;
      } catch (error) {
        throw error;
      }
    },
    [dispatch]
  );

  /**
   * Logout
   */
  const logout = useCallback(
    async (redirectTo = '/login') => {
      try {
        // Call backend logout API
        await authService.logout();
      } catch {
        // Ignore logout API errors
      } finally {
        // Always clear local state
        dispatch(logoutAction());
        navigate(redirectTo, { replace: true });
      }
    },
    [dispatch, navigate]
  );

  /**
   * Clear authentication error
   */
  const clearAuthError = useCallback(() => {
    dispatch(clearError());
  }, [dispatch]);

  /**
   * Check if user has a specific role
   */
  const hasRole = useCallback(
    (role: string) => {
      return auth.user?.roles?.includes(role) ?? false;
    },
    [auth.user]
  );

  /**
   * Check if user has any of the specified roles
   */
  const hasAnyRole = useCallback(
    (roles: string[]) => {
      return roles.some((role) => auth.user?.roles?.includes(role));
    },
    [auth.user]
  );

  /**
   * Check if user has all of the specified roles
   */
  const hasAllRoles = useCallback(
    (roles: string[]) => {
      return roles.every((role) => auth.user?.roles?.includes(role));
    },
    [auth.user]
  );

  return {
    // State
    user: auth.user,
    isAuthenticated: auth.isAuthenticated,
    isLoading: auth.isLoading,
    error: auth.error,
    accessToken: auth.accessToken,
    authMethod: auth.authMethod,

    // Actions
    login,
    logout,
    clearAuthError,

    // Role checks
    hasRole,
    hasAnyRole,
    hasAllRoles,
  };
};

export default useDirectAuth;
