/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** API base URL (e.g., http://localhost:8002) */
  readonly VITE_API_BASE_URL: string;
  /** Keycloak server URL (e.g., http://localhost:8180) */
  readonly VITE_KEYCLOAK_URL: string;
  /** Keycloak realm name (e.g., knowledge-platform) */
  readonly VITE_KEYCLOAK_REALM: string;
  /** Keycloak client ID (e.g., knowledge-frontend) */
  readonly VITE_KEYCLOAK_CLIENT_ID: string;
  /** Enable mock authentication for development (true/false) */
  readonly VITE_USE_MOCK_AUTH: string;
  /** Application display name */
  readonly VITE_APP_NAME: string;
  /** Application version */
  readonly VITE_APP_VERSION: string;
  /** Development test accounts (format: email:password,email:password,...) */
  readonly VITE_DEV_TEST_ACCOUNTS?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
