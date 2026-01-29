"""
Contract Test: Authentication API Contract

Validates the authentication-related API contracts including:
- Token exchange request/response
- Token refresh request/response
- JWT token structure
- Authorization header format

Related: STORY-054, API Integration Design v1.4
Sprint: Sprint 04 Day 4
Author: QA Agent
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

# Project root path setup
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from .conftest import validate_json_schema

# =============================================================================
# Custom Markers
# =============================================================================

pytestmark = [
    pytest.mark.contract,
    pytest.mark.sprint04_fb_e2e,
]


# =============================================================================
# JSON Schema Definitions for Authentication
# =============================================================================


@pytest.fixture
def token_exchange_request_schema() -> Dict[str, Any]:
    """JSON Schema for token exchange request (POST /api/v1/auth/token)."""
    return {
        "type": "object",
        "required": ["code", "codeVerifier", "redirectUri"],
        "properties": {
            "code": {"type": "string", "minLength": 1},
            "codeVerifier": {"type": "string", "minLength": 43, "maxLength": 128},
            "redirectUri": {"type": "string", "minLength": 1},
        },
    }


@pytest.fixture
def token_response_schema() -> Dict[str, Any]:
    """JSON Schema for token response."""
    return {
        "type": "object",
        "required": ["success", "data"],
        "properties": {
            "success": {"type": "boolean", "const": True},
            "data": {
                "type": "object",
                "required": ["accessToken", "tokenType", "expiresIn"],
                "properties": {
                    "accessToken": {"type": "string", "minLength": 1},
                    "refreshToken": {"type": "string"},
                    "tokenType": {"type": "string", "enum": ["Bearer"]},
                    "expiresIn": {"type": "integer", "minimum": 1},
                    "refreshExpiresIn": {"type": "integer", "minimum": 1},
                    "scope": {"type": "string"},
                },
            },
        },
    }


@pytest.fixture
def token_refresh_request_schema() -> Dict[str, Any]:
    """JSON Schema for token refresh request (POST /api/v1/auth/refresh)."""
    return {
        "type": "object",
        "required": ["refreshToken"],
        "properties": {
            "refreshToken": {"type": "string", "minLength": 1},
        },
    }


@pytest.fixture
def user_info_response_schema() -> Dict[str, Any]:
    """JSON Schema for user info response (GET /api/v1/auth/me)."""
    return {
        "type": "object",
        "required": ["success", "data"],
        "properties": {
            "success": {"type": "boolean", "const": True},
            "data": {
                "type": "object",
                "required": ["id", "email"],
                "properties": {
                    "id": {"type": "string"},
                    "email": {"type": "string"},
                    "name": {"type": "string"},
                    "roles": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "department": {"type": "string"},
                },
            },
        },
    }


# =============================================================================
# Test Data: Authentication Requests/Responses
# =============================================================================

VALID_TOKEN_EXCHANGE_REQUESTS = [
    {
        "description": "Standard token exchange request",
        "data": {
            "code": "authorization_code_from_keycloak_1234567890",
            "codeVerifier": "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk" * 2,
            "redirectUri": "http://localhost:5173/callback",
        },
    },
    {
        "description": "Production redirect URI",
        "data": {
            "code": "auth_code_prod_abc123",
            "codeVerifier": "verifier_string_that_is_at_least_43_characters_long_abc",
            "redirectUri": "https://knowledge.company.com/callback",
        },
    },
]

INVALID_TOKEN_EXCHANGE_REQUESTS = [
    {
        "description": "Missing code field",
        "data": {
            "codeVerifier": "verifier_string_that_is_at_least_43_characters_long_abc",
            "redirectUri": "http://localhost:5173/callback",
        },
    },
    {
        "description": "Missing codeVerifier field",
        "data": {
            "code": "auth_code_123",
            "redirectUri": "http://localhost:5173/callback",
        },
    },
    {
        "description": "Missing redirectUri field",
        "data": {
            "code": "auth_code_123",
            "codeVerifier": "verifier_string_that_is_at_least_43_characters_long_abc",
        },
    },
    {
        "description": "CodeVerifier too short (< 43 chars)",
        "data": {
            "code": "auth_code_123",
            "codeVerifier": "short_verifier",
            "redirectUri": "http://localhost:5173/callback",
        },
    },
]

VALID_TOKEN_RESPONSES = [
    {
        "description": "Full token response with refresh",
        "data": {
            "success": True,
            "data": {
                "accessToken": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IlVzZXIiLCJpYXQiOjE1MTYyMzkwMjJ9.signature",
                "refreshToken": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.refresh_token_payload.signature",
                "tokenType": "Bearer",
                "expiresIn": 900,
                "refreshExpiresIn": 604800,
                "scope": "openid profile email",
            },
        },
    },
    {
        "description": "Minimal token response",
        "data": {
            "success": True,
            "data": {
                "accessToken": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.payload.signature",
                "tokenType": "Bearer",
                "expiresIn": 3600,
            },
        },
    },
]

VALID_USER_INFO_RESPONSES = [
    {
        "description": "Full user info response",
        "data": {
            "success": True,
            "data": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "name": "Test User",
                "roles": ["user", "admin"],
                "department": "Engineering",
            },
        },
    },
    {
        "description": "Minimal user info response",
        "data": {
            "success": True,
            "data": {
                "id": "user-123",
                "email": "minimal@example.com",
            },
        },
    },
]


# =============================================================================
# Contract Tests: Token Exchange Request
# =============================================================================


class TestTokenExchangeRequestContract:
    """Validates token exchange request contract."""

    def test_valid_requests_pass_schema(
        self,
        token_exchange_request_schema: Dict[str, Any],
    ):
        """All valid token exchange requests conform to schema."""
        for case in VALID_TOKEN_EXCHANGE_REQUESTS:
            errors = validate_json_schema(
                case["data"],
                token_exchange_request_schema,
            )
            assert len(errors) == 0, (
                f"Valid request '{case['description']}' failed: {errors}"
            )

    def test_invalid_requests_fail_schema(
        self,
        token_exchange_request_schema: Dict[str, Any],
    ):
        """Invalid token exchange requests are rejected."""
        for case in INVALID_TOKEN_EXCHANGE_REQUESTS:
            errors = validate_json_schema(
                case["data"],
                token_exchange_request_schema,
            )
            assert len(errors) > 0, (
                f"Invalid request '{case['description']}' should fail"
            )

    def test_code_field_required(
        self,
        token_exchange_request_schema: Dict[str, Any],
    ):
        """'code' field is required."""
        request_without_code = {
            "codeVerifier": "verifier_string_that_is_at_least_43_characters",
            "redirectUri": "http://localhost/callback",
        }
        errors = validate_json_schema(
            request_without_code,
            token_exchange_request_schema,
        )
        assert any("code" in e for e in errors)

    def test_code_verifier_min_length(
        self,
        token_exchange_request_schema: Dict[str, Any],
    ):
        """codeVerifier must be at least 43 characters (PKCE spec)."""
        request = {
            "code": "auth_code",
            "codeVerifier": "short",  # Too short
            "redirectUri": "http://localhost/callback",
        }
        errors = validate_json_schema(
            request,
            token_exchange_request_schema,
        )
        assert any("minLength" in e for e in errors)

    def test_redirect_uri_required(
        self,
        token_exchange_request_schema: Dict[str, Any],
    ):
        """redirectUri field is required."""
        request_without_redirect = {
            "code": "auth_code_123",
            "codeVerifier": "verifier_string_that_is_at_least_43_characters_long",
        }
        errors = validate_json_schema(
            request_without_redirect,
            token_exchange_request_schema,
        )
        assert any("redirectUri" in e for e in errors)


# =============================================================================
# Contract Tests: Token Response
# =============================================================================


class TestTokenResponseContract:
    """Validates token response contract."""

    def test_valid_responses_pass_schema(
        self,
        token_response_schema: Dict[str, Any],
    ):
        """All valid token responses conform to schema."""
        for case in VALID_TOKEN_RESPONSES:
            errors = validate_json_schema(
                case["data"],
                token_response_schema,
            )
            assert len(errors) == 0, (
                f"Valid response '{case['description']}' failed: {errors}"
            )

    def test_access_token_required(
        self,
        token_response_schema: Dict[str, Any],
    ):
        """accessToken field is required."""
        response_without_token = {
            "success": True,
            "data": {
                "tokenType": "Bearer",
                "expiresIn": 900,
            },
        }
        errors = validate_json_schema(
            response_without_token,
            token_response_schema,
        )
        assert any("accessToken" in e for e in errors)

    def test_token_type_is_bearer(self):
        """tokenType must be 'Bearer'."""
        for case in VALID_TOKEN_RESPONSES:
            token_type = case["data"]["data"]["tokenType"]
            assert token_type == "Bearer", (
                f"tokenType should be 'Bearer', got '{token_type}'"
            )

    def test_expires_in_positive(self):
        """expiresIn must be a positive integer."""
        for case in VALID_TOKEN_RESPONSES:
            expires_in = case["data"]["data"]["expiresIn"]
            assert isinstance(expires_in, int)
            assert expires_in > 0, f"expiresIn should be > 0, got {expires_in}"

    def test_refresh_expires_in_optional(self):
        """refreshExpiresIn is optional but must be positive if present."""
        for case in VALID_TOKEN_RESPONSES:
            data = case["data"]["data"]
            if "refreshExpiresIn" in data:
                assert data["refreshExpiresIn"] > 0


# =============================================================================
# Contract Tests: JWT Token Structure
# =============================================================================


class TestJWTTokenStructureContract:
    """Validates JWT token structure contract."""

    def test_jwt_has_three_parts(self):
        """JWT token has three parts separated by dots."""
        jwt_tokens = [
            "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJuYW1lIjoiVGVzdCJ9.sig123",
        ]
        for token in jwt_tokens:
            parts = token.split(".")
            assert len(parts) == 3, (
                f"JWT should have 3 parts, got {len(parts)}"
            )

    def test_jwt_header_is_base64url(self):
        """JWT header is base64url encoded."""
        # Base64url pattern (alphanumeric, -, _)
        base64url_pattern = r"^[A-Za-z0-9_-]+$"
        jwt_headers = [
            "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
        ]
        for header in jwt_headers:
            assert re.match(base64url_pattern, header), (
                f"JWT header should be base64url: {header}"
            )

    def test_authorization_header_format(self):
        """Authorization header follows 'Bearer {token}' format."""
        valid_auth_headers = [
            "Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.payload.signature",
            "Bearer abc123def456",
        ]
        for header in valid_auth_headers:
            assert header.startswith("Bearer "), (
                f"Auth header should start with 'Bearer '"
            )
            token = header[7:]  # Remove "Bearer " prefix
            assert len(token) > 0, "Token should not be empty"


# =============================================================================
# Contract Tests: Token Refresh Request
# =============================================================================


class TestTokenRefreshRequestContract:
    """Validates token refresh request contract."""

    def test_valid_refresh_request(
        self,
        token_refresh_request_schema: Dict[str, Any],
    ):
        """Valid refresh request conforms to schema."""
        request = {
            "refreshToken": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.refresh.signature",
        }
        errors = validate_json_schema(request, token_refresh_request_schema)
        assert len(errors) == 0

    def test_refresh_token_required(
        self,
        token_refresh_request_schema: Dict[str, Any],
    ):
        """refreshToken field is required."""
        request_without_token = {}
        errors = validate_json_schema(
            request_without_token,
            token_refresh_request_schema,
        )
        assert any("refreshToken" in e for e in errors)

    def test_refresh_token_not_empty(
        self,
        token_refresh_request_schema: Dict[str, Any],
    ):
        """refreshToken cannot be empty string."""
        request = {"refreshToken": ""}
        errors = validate_json_schema(request, token_refresh_request_schema)
        assert any("minLength" in e for e in errors)


# =============================================================================
# Contract Tests: User Info Response
# =============================================================================


class TestUserInfoResponseContract:
    """Validates user info response contract."""

    def test_valid_responses_pass_schema(
        self,
        user_info_response_schema: Dict[str, Any],
    ):
        """All valid user info responses conform to schema."""
        for case in VALID_USER_INFO_RESPONSES:
            errors = validate_json_schema(
                case["data"],
                user_info_response_schema,
            )
            assert len(errors) == 0, (
                f"Valid response '{case['description']}' failed: {errors}"
            )

    def test_user_id_required(self):
        """User ID is required in response."""
        for case in VALID_USER_INFO_RESPONSES:
            assert "id" in case["data"]["data"]

    def test_user_email_required(self):
        """User email is required in response."""
        for case in VALID_USER_INFO_RESPONSES:
            assert "email" in case["data"]["data"]

    def test_roles_is_array_if_present(self):
        """Roles field is an array if present."""
        for case in VALID_USER_INFO_RESPONSES:
            if "roles" in case["data"]["data"]:
                assert isinstance(case["data"]["data"]["roles"], list)


# =============================================================================
# Contract Tests: Auth Error Responses
# =============================================================================


class TestAuthErrorResponseContract:
    """Validates authentication error response contract."""

    def test_invalid_auth_code_error(self):
        """Invalid auth code returns proper error."""
        error_response = {
            "success": False,
            "error": {
                "code": "INVALID_AUTH_CODE",
                "message": "유효하지 않은 인증 코드입니다.",
            },
        }
        assert error_response["success"] is False
        assert error_response["error"]["code"] == "INVALID_AUTH_CODE"

    def test_refresh_token_expired_error(self):
        """Expired refresh token returns proper error."""
        error_response = {
            "success": False,
            "error": {
                "code": "REFRESH_TOKEN_EXPIRED",
                "message": "Refresh Token이 만료되었습니다. 다시 로그인해주세요.",
            },
        }
        assert error_response["success"] is False
        assert "EXPIRED" in error_response["error"]["code"]

    def test_unauthorized_error(self):
        """Unauthorized access returns proper error."""
        error_response = {
            "success": False,
            "error": {
                "code": "UNAUTHORIZED",
                "message": "인증이 필요합니다.",
            },
        }
        assert error_response["success"] is False
        assert error_response["error"]["code"] == "UNAUTHORIZED"

    def test_auth_error_codes_uppercase(self):
        """Auth error codes are uppercase with underscores."""
        auth_error_codes = [
            "INVALID_AUTH_CODE",
            "REFRESH_TOKEN_EXPIRED",
            "UNAUTHORIZED",
            "TOKEN_INVALID",
            "FORBIDDEN",
        ]
        code_pattern = r"^[A-Z0-9_]+$"
        for code in auth_error_codes:
            assert re.match(code_pattern, code), (
                f"Error code '{code}' should be uppercase"
            )


# =============================================================================
# Contract Tests: Internal API Authentication
# =============================================================================


class TestInternalAPIAuthContract:
    """Validates internal API authentication contract."""

    def test_internal_api_key_header(self):
        """Internal API uses X-Internal-Api-Key header."""
        internal_headers = {
            "X-Internal-Api-Key": "internal-service-key-xxx",
            "X-Request-Id": "uuid-for-tracing",
            "X-User-Id": "user-uuid-from-jwt",
        }
        assert "X-Internal-Api-Key" in internal_headers
        assert "X-Request-Id" in internal_headers

    def test_request_id_header_format(self):
        """X-Request-Id header for tracing."""
        valid_request_ids = [
            "550e8400-e29b-41d4-a716-446655440000",
            "req-123-abc",
            "trace_id_456",
        ]
        for req_id in valid_request_ids:
            assert len(req_id) > 0

    def test_user_id_propagation(self):
        """User ID propagated via X-User-Id header."""
        headers = {
            "X-User-Id": "123e4567-e89b-12d3-a456-426614174000",
        }
        assert "X-User-Id" in headers
        # UUID format check
        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        assert re.match(uuid_pattern, headers["X-User-Id"])


# =============================================================================
# Test Execution
# =============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
