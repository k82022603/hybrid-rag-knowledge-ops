/**
 * Auth Module Exports
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

// Provider and hooks
export { KeycloakProvider, useAuth } from './KeycloakProvider';

// Protected routes
export {
  ProtectedRoute,
  RequireAuth,
  RequireAdmin,
  RequireKnowledgeManager,
} from './ProtectedRoute';
