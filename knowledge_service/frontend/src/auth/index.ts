/**
 * Auth Module Exports
 *
 * Central export point for all authentication-related functionality:
 * - Keycloak instance and utilities
 * - KeycloakProvider and useAuth hook
 * - Protected route components
 */

// Keycloak instance and utilities
export {
  default as keycloak,
  keycloakInitOptions,
  refreshToken,
  login,
  logout,
  getToken,
  getTokenParsed,
  isAuthenticated,
  hasRole,
  hasResourceRole,
  getUserInfo,
  TOKEN_REFRESH_MARGIN,
} from './keycloak';

// Provider, hooks, and types
export { KeycloakProvider, useAuth } from './KeycloakProvider';
export type { AuthContextType } from './KeycloakProvider';

// Protected routes
export {
  ProtectedRoute,
  RequireAuth,
  RequireAdmin,
  RequireKnowledgeManager,
} from './ProtectedRoute';
