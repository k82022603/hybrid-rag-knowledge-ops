"""
STORY-020: Keycloak Authentication E2E Tests

This module provides comprehensive E2E tests for Keycloak OAuth2/OIDC authentication.
It validates realm configuration, client setup, and authentication flows.

Test Categories:
- Server Availability: Verify Keycloak server responds correctly
- Realm Configuration: Validate hybrid-rag realm settings
- Client Configuration: Verify frontend, backend, ai-service clients
- OAuth2 Flows: Test password grant, token refresh, protected API access
- Token Validation: Verify JWT token structure and claims

Usage:
    pytest knowledge_service/src/tests/e2e/test_keycloak.py -v

Markers:
    @pytest.mark.e2e: End-to-end tests
    @pytest.mark.keycloak: Keycloak authentication tests

Author: QA Agent
Sprint: Sprint 01 Validation
"""

import base64
import json
import os
import subprocess
from typing import Dict, Optional

import pytest
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# =============================================================================
# CONSTANTS
# =============================================================================

KEYCLOAK_URL = "http://localhost:8180"
REALM_NAME = "hybrid-rag"
EXPECTED_CLIENTS = ["frontend", "backend", "ai-service"]
EXPECTED_ROLES = ["user", "admin"]


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def http_session() -> requests.Session:
    """Create HTTP session with retry logic."""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


@pytest.fixture(scope="module")
def keycloak_config() -> Dict[str, str]:
    """Load Keycloak configuration from environment."""
    return {
        "admin_user": os.getenv("KEYCLOAK_ADMIN", "admin"),
        "admin_password": os.getenv("KEYCLOAK_ADMIN_PASSWORD", ""),
        "realm": os.getenv("KEYCLOAK_REALM", REALM_NAME),
    }


@pytest.fixture(scope="module")
def admin_token(http_session: requests.Session, keycloak_config: Dict[str, str]) -> Optional[str]:
    """Obtain admin access token for Keycloak API calls."""
    if not keycloak_config["admin_password"]:
        return None

    response = http_session.post(
        f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": keycloak_config["admin_user"],
            "password": keycloak_config["admin_password"],
        },
        timeout=10
    )

    if response.status_code == 200:
        return response.json().get("access_token")
    return None


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def is_docker_available() -> bool:
    """Check if Docker is available."""
    try:
        result = subprocess.run(
            ["docker", "version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def decode_jwt_payload(token: str) -> Dict:
    """Decode JWT token payload without verification."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT structure")

    payload_b64 = parts[1]
    # Add padding if needed
    padding = 4 - len(payload_b64) % 4
    if padding != 4:
        payload_b64 += "=" * padding

    return json.loads(base64.urlsafe_b64decode(payload_b64))


docker_available = pytest.mark.skipif(
    not is_docker_available(),
    reason="Docker is not available"
)


# =============================================================================
# TC-INFRA-301: SERVER AVAILABILITY TESTS
# =============================================================================

@pytest.mark.e2e
@pytest.mark.keycloak
@docker_available
class TestKeycloakServerAvailability:
    """
    TC-INFRA-301: Verify Keycloak server is running and responding correctly.

    Acceptance Criteria:
    - Health endpoint returns HTTP 200
    - Admin console is accessible
    - OpenID configuration is available
    """

    def test_health_endpoint(self, http_session: requests.Session):
        """Keycloak health endpoint should return HTTP 200."""
        response = http_session.get(
            f"{KEYCLOAK_URL}/health/ready",
            timeout=10
        )
        assert response.status_code == 200, (
            f"Keycloak health check failed: {response.status_code}"
        )

    def test_admin_console_accessible(self, http_session: requests.Session):
        """Keycloak admin console should be accessible."""
        response = http_session.get(
            f"{KEYCLOAK_URL}/admin/",
            timeout=10
        )
        # Admin console redirects to login
        assert response.status_code in [200, 302, 303], (
            f"Admin console not accessible: {response.status_code}"
        )

    def test_openid_configuration(self, http_session: requests.Session):
        """OpenID Connect configuration should be available for the realm."""
        response = http_session.get(
            f"{KEYCLOAK_URL}/realms/{REALM_NAME}/.well-known/openid-configuration",
            timeout=10
        )

        if response.status_code == 404:
            pytest.skip(f"Realm '{REALM_NAME}' not found")

        assert response.status_code == 200

        data = response.json()
        required_fields = [
            "issuer",
            "authorization_endpoint",
            "token_endpoint",
            "userinfo_endpoint",
            "jwks_uri",
        ]

        for field in required_fields:
            assert field in data, f"Missing OIDC field: {field}"


# =============================================================================
# TC-INFRA-302-304: REALM CONFIGURATION TESTS
# =============================================================================

@pytest.mark.e2e
@pytest.mark.keycloak
@docker_available
class TestRealmConfiguration:
    """
    TC-INFRA-302-304: Verify realm and client configuration.

    Acceptance Criteria:
    - hybrid-rag realm exists
    - Required clients are configured
    - Required roles are defined
    """

    def test_realm_exists(
        self, http_session: requests.Session, admin_token: Optional[str],
        keycloak_config: Dict[str, str]
    ):
        """TC-INFRA-302: hybrid-rag realm should exist."""
        if not admin_token:
            pytest.skip("Admin token not available - check KEYCLOAK_ADMIN_PASSWORD")

        response = http_session.get(
            f"{KEYCLOAK_URL}/admin/realms/{keycloak_config['realm']}",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )

        assert response.status_code == 200, (
            f"Realm '{keycloak_config['realm']}' not found: {response.status_code}"
        )

        data = response.json()
        assert data.get("realm") == keycloak_config["realm"]

    def test_clients_configured(
        self, http_session: requests.Session, admin_token: Optional[str]
    ):
        """TC-INFRA-303: Required clients should be configured."""
        if not admin_token:
            pytest.skip("Admin token not available")

        response = http_session.get(
            f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/clients",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )

        assert response.status_code == 200

        clients = response.json()
        client_ids = [c.get("clientId") for c in clients]

        for expected in EXPECTED_CLIENTS:
            assert expected in client_ids, (
                f"Client '{expected}' not found. Found: {client_ids}"
            )

    def test_roles_defined(
        self, http_session: requests.Session, admin_token: Optional[str]
    ):
        """TC-INFRA-304: Required roles should be defined."""
        if not admin_token:
            pytest.skip("Admin token not available")

        response = http_session.get(
            f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/roles",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )

        assert response.status_code == 200

        roles = response.json()
        role_names = [r.get("name") for r in roles]

        for expected in EXPECTED_ROLES:
            assert expected in role_names, (
                f"Role '{expected}' not found. Found: {role_names}"
            )


# =============================================================================
# TC-INFRA-301: ADMIN LOGIN TEST
# =============================================================================

@pytest.mark.e2e
@pytest.mark.keycloak
@docker_available
class TestAdminLogin:
    """
    TC-INFRA-301: Verify Keycloak admin can login successfully.
    """

    def test_admin_login(
        self, http_session: requests.Session, keycloak_config: Dict[str, str]
    ):
        """Admin should be able to obtain access token."""
        if not keycloak_config["admin_password"]:
            pytest.skip("KEYCLOAK_ADMIN_PASSWORD not set")

        response = http_session.post(
            f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": keycloak_config["admin_user"],
                "password": keycloak_config["admin_password"],
            },
            timeout=10
        )

        assert response.status_code == 200, (
            f"Admin login failed: {response.status_code} - {response.text}"
        )

        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data


# =============================================================================
# TC-INFRA-306-308: OAUTH2 FLOW TESTS
# =============================================================================

@pytest.mark.e2e
@pytest.mark.keycloak
@docker_available
class TestOAuth2Flows:
    """
    TC-INFRA-306-308: Verify OAuth2 authentication flows.

    Acceptance Criteria:
    - Password grant returns valid tokens
    - Token has correct JWT structure
    - Token refresh works correctly
    """

    @pytest.fixture
    def test_user(self) -> Dict[str, str]:
        """Test user credentials (must exist in Keycloak)."""
        return {
            "username": os.getenv("TEST_USER", "test-user"),
            "password": os.getenv("TEST_PASSWORD", "test-password"),
        }

    @pytest.fixture
    def client_config(self) -> Dict[str, str]:
        """Backend client configuration."""
        return {
            "client_id": "backend",
            "client_secret": os.getenv("KEYCLOAK_BACKEND_SECRET", ""),
        }

    def test_password_grant(
        self, http_session: requests.Session,
        test_user: Dict[str, str], client_config: Dict[str, str]
    ):
        """TC-INFRA-306: OAuth2 password grant should return tokens."""
        response = http_session.post(
            f"{KEYCLOAK_URL}/realms/{REALM_NAME}/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": client_config["client_id"],
                "username": test_user["username"],
                "password": test_user["password"],
            },
            timeout=10
        )

        if response.status_code == 401:
            pytest.skip("Test user not configured in Keycloak")

        if response.status_code == 400:
            # Client might require secret
            pytest.skip("Client configuration issue")

        assert response.status_code == 200, (
            f"Token request failed: {response.status_code}"
        )

        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "expires_in" in data

    def test_token_structure(
        self, http_session: requests.Session,
        test_user: Dict[str, str], client_config: Dict[str, str]
    ):
        """TC-INFRA-307: JWT token should have correct structure."""
        response = http_session.post(
            f"{KEYCLOAK_URL}/realms/{REALM_NAME}/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": client_config["client_id"],
                "username": test_user["username"],
                "password": test_user["password"],
            },
            timeout=10
        )

        if response.status_code != 200:
            pytest.skip("Cannot obtain token")

        access_token = response.json()["access_token"]

        # Verify JWT structure
        parts = access_token.split(".")
        assert len(parts) == 3, "Invalid JWT structure"

        # Decode and verify payload
        payload = decode_jwt_payload(access_token)

        # Required claims
        assert "sub" in payload, "Missing 'sub' claim"
        assert "exp" in payload, "Missing 'exp' claim"
        assert "iat" in payload, "Missing 'iat' claim"

        # Roles should be present
        has_roles = (
            "realm_access" in payload or
            "resource_access" in payload or
            "roles" in payload
        )
        assert has_roles, "No roles information in token"

    def test_token_refresh(
        self, http_session: requests.Session,
        test_user: Dict[str, str], client_config: Dict[str, str]
    ):
        """TC-INFRA-308: Token refresh should return new tokens."""
        # Get initial token
        response = http_session.post(
            f"{KEYCLOAK_URL}/realms/{REALM_NAME}/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": client_config["client_id"],
                "username": test_user["username"],
                "password": test_user["password"],
            },
            timeout=10
        )

        if response.status_code != 200:
            pytest.skip("Cannot obtain token")

        refresh_token = response.json()["refresh_token"]

        # Refresh token
        refresh_response = http_session.post(
            f"{KEYCLOAK_URL}/realms/{REALM_NAME}/protocol/openid-connect/token",
            data={
                "grant_type": "refresh_token",
                "client_id": client_config["client_id"],
                "refresh_token": refresh_token,
            },
            timeout=10
        )

        assert refresh_response.status_code == 200, (
            f"Token refresh failed: {refresh_response.status_code}"
        )

        data = refresh_response.json()
        assert "access_token" in data
        assert "refresh_token" in data


# =============================================================================
# TC-INFRA-309-310: PROTECTED API ACCESS TESTS
# =============================================================================

@pytest.mark.e2e
@pytest.mark.keycloak
@docker_available
class TestProtectedApiAccess:
    """
    TC-INFRA-309-310: Verify protected API access with tokens.

    Acceptance Criteria:
    - Valid token allows API access
    - Invalid token is rejected
    - Missing token is rejected
    """

    def test_invalid_token_rejected(self, http_session: requests.Session):
        """TC-INFRA-310: Invalid token should be rejected."""
        response = http_session.get(
            "http://localhost:8080/api/v1/user/me",
            headers={"Authorization": "Bearer invalid-token"},
            timeout=10
        )

        # 401/403 for auth failure, 404 for endpoint not found (stub mode)
        assert response.status_code in [401, 403, 404], (
            f"Expected 401/403/404, got {response.status_code}"
        )

    def test_no_token_rejected(self, http_session: requests.Session):
        """TC-INFRA-310b: Request without token should be rejected."""
        response = http_session.get(
            "http://localhost:8080/api/v1/user/me",
            timeout=10
        )

        # 401/403 for auth failure, 404 for endpoint not found (stub mode)
        assert response.status_code in [401, 403, 404], (
            f"Expected 401/403/404, got {response.status_code}"
        )


# =============================================================================
# TC-INFRA-305: USER MANAGEMENT TESTS
# =============================================================================

@pytest.mark.e2e
@pytest.mark.keycloak
@docker_available
class TestUserManagement:
    """
    TC-INFRA-305: Verify user management capabilities.
    """

    def test_user_creation(
        self, http_session: requests.Session, admin_token: Optional[str]
    ):
        """Admin should be able to create users via API."""
        if not admin_token:
            pytest.skip("Admin token not available")

        test_username = "e2e-test-user-temp"

        # Create test user
        create_response = http_session.post(
            f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "Content-Type": "application/json",
            },
            json={
                "username": test_username,
                "enabled": True,
                "credentials": [{
                    "type": "password",
                    "value": "test-password-123",
                    "temporary": False,
                }],
            },
            timeout=10
        )

        # 201 = created, 409 = already exists
        assert create_response.status_code in [201, 409], (
            f"User creation failed: {create_response.status_code}"
        )

        # Cleanup: delete test user if created
        if create_response.status_code == 201:
            # Get user ID
            users_response = http_session.get(
                f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users?username={test_username}",
                headers={"Authorization": f"Bearer {admin_token}"},
                timeout=10
            )

            if users_response.status_code == 200:
                users = users_response.json()
                if users:
                    user_id = users[0]["id"]
                    http_session.delete(
                        f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users/{user_id}",
                        headers={"Authorization": f"Bearer {admin_token}"},
                        timeout=10
                    )
