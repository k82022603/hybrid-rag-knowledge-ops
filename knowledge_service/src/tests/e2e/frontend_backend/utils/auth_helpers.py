"""
Authentication Helper Utilities for E2E Testing

Provides JWT token generation, validation, and management helpers
for Frontend/Backend E2E test scenarios.

Features:
- Generate valid/expired/tampered JWT tokens
- Simulate login flows via API
- Token refresh lifecycle helpers

Author: QA Agent
Sprint: Sprint 04 Day 3
"""

import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt

# Default test JWT configuration (matches knowledge_service auth.py)
DEFAULT_JWT_SECRET = "knowledge-service-secret-key-change-in-production"
DEFAULT_JWT_ALGORITHM = "HS256"

# Test account constants (from E2E Test Plan Section 3.5)
TEST_ACCOUNTS = {
    "user": {
        "email": "test@example.com",
        "password": "password123",
        "role": "USER",
        "sub": "user-001",
    },
    "admin": {
        "email": "admin@example.com",
        "password": "admin123!",
        "role": "ADMIN",
        "sub": "admin-001",
    },
    "readonly": {
        "email": "readonly@example.com",
        "password": "readonly123!",
        "role": "VIEWER",
        "sub": "readonly-001",
    },
    "invalid": {
        "email": "wrong@example.com",
        "password": "wrongpassword",
        "role": None,
        "sub": None,
    },
}


def generate_valid_token(
    user_id: str = "user-001",
    email: str = "test@example.com",
    role: str = "user",
    expires_in_minutes: int = 30,
    secret: str = DEFAULT_JWT_SECRET,
    algorithm: str = DEFAULT_JWT_ALGORITHM,
    additional_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate a valid JWT access token for testing.

    Args:
        user_id: Subject claim (user identifier)
        email: User email claim
        role: User role claim
        expires_in_minutes: Token lifetime in minutes
        secret: JWT signing secret
        algorithm: JWT algorithm
        additional_claims: Extra claims to include

    Returns:
        Encoded JWT token string
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": now + timedelta(minutes=expires_in_minutes),
        "iat": now,
        "type": "access",
    }

    if additional_claims:
        payload.update(additional_claims)

    return jwt.encode(payload, secret, algorithm=algorithm)


def generate_expired_token(
    user_id: str = "user-001",
    email: str = "test@example.com",
    role: str = "user",
    expired_hours_ago: int = 1,
    secret: str = DEFAULT_JWT_SECRET,
    algorithm: str = DEFAULT_JWT_ALGORITHM,
) -> str:
    """Generate an expired JWT access token for testing.

    Args:
        user_id: Subject claim
        email: User email claim
        role: User role claim
        expired_hours_ago: How many hours ago the token expired
        secret: JWT signing secret
        algorithm: JWT algorithm

    Returns:
        Encoded JWT token string (expired)
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": now - timedelta(hours=expired_hours_ago),
        "iat": now - timedelta(hours=expired_hours_ago + 1),
        "type": "access",
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


def generate_tampered_token(
    valid_token: Optional[str] = None,
    secret: str = DEFAULT_JWT_SECRET,
    algorithm: str = DEFAULT_JWT_ALGORITHM,
) -> str:
    """Generate a tampered JWT token (modified payload without re-signing).

    Creates a token where the payload has been altered but the signature
    was computed with a different secret, making it invalid.

    Args:
        valid_token: Optional base token to tamper with
        secret: Original secret (will sign with different secret)
        algorithm: JWT algorithm

    Returns:
        Tampered JWT token string
    """
    payload = {
        "sub": "hacker-001",
        "email": "hacker@evil.com",
        "role": "admin",
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    # Sign with a different secret to create invalid signature
    return jwt.encode(payload, "wrong-secret-key-for-tampering", algorithm=algorithm)


def generate_refresh_token(
    user_id: str = "user-001",
    email: str = "test@example.com",
    expires_in_days: int = 7,
    secret: str = DEFAULT_JWT_SECRET,
    algorithm: str = DEFAULT_JWT_ALGORITHM,
) -> str:
    """Generate a refresh token for testing token refresh flows.

    Args:
        user_id: Subject claim
        email: User email
        expires_in_days: Refresh token lifetime in days
        secret: JWT signing secret
        algorithm: JWT algorithm

    Returns:
        Encoded JWT refresh token string
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "exp": now + timedelta(days=expires_in_days),
        "iat": now,
        "type": "refresh",
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


def build_auth_headers(token: str) -> Dict[str, str]:
    """Build Authorization headers with Bearer token.

    Args:
        token: JWT token string

    Returns:
        Headers dict with Authorization and Content-Type
    """
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def decode_token(
    token: str,
    secret: str = DEFAULT_JWT_SECRET,
    algorithm: str = DEFAULT_JWT_ALGORITHM,
    verify: bool = True,
) -> Dict[str, Any]:
    """Decode and optionally verify a JWT token.

    Args:
        token: JWT token string
        secret: JWT signing secret
        algorithm: JWT algorithm
        verify: Whether to verify signature and expiration

    Returns:
        Decoded token payload dict

    Raises:
        jwt.ExpiredSignatureError: If token is expired and verify=True
        jwt.InvalidTokenError: If token is invalid and verify=True
    """
    options = {}
    if not verify:
        options = {
            "verify_exp": False,
            "verify_signature": False,
        }

    return jwt.decode(
        token,
        secret,
        algorithms=[algorithm],
        options=options,
    )
