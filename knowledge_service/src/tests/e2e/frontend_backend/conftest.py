"""
Frontend/Backend E2E Test Configuration and Shared Fixtures

Provides pytest configuration, fixtures, and mock infrastructure for
Sprint 04 Frontend/Backend E2E tests (25 scenarios).

Mock Mode (default):
    When Docker Compose is not available, tests run in mock mode using
    FastAPI's TestClient with mocked service dependencies.
    Set E2E_MODE=mock or leave unset.

Docker Mode:
    When the full Docker Compose stack is available, tests use httpx
    to make real HTTP requests through the API Gateway.
    Set E2E_MODE=docker to enable.

Actual API Routes (discovered from source):
    - Search: /api/v1/search/hybrid, /search/semantic, /search/keyword,
              /search/chat, /search/chat/stream
    - Auth:   /api/v1/auth/login, /auth/logout, /auth/me, /auth/refresh
    - Docs:   /api/v1/documents
    - SSE event types: start, chunk, end, error

Authentication Policy (ADR-002, ADR-003):
    - All endpoints require JWT except: login, refresh, health
    - Login response uses camelCase: accessToken, refreshToken

Author: QA Agent
Sprint: Sprint 04 Day 3
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

# Project root path setup
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from app.core.config import settings
from app.main import app

from .utils.auth_helpers import (
    DEFAULT_JWT_ALGORITHM,
    DEFAULT_JWT_SECRET,
    TEST_ACCOUNTS,
    build_auth_headers,
    generate_expired_token,
    generate_refresh_token,
    generate_tampered_token,
    generate_valid_token,
)


# =============================================================================
# Pytest Configuration - Custom Markers
# =============================================================================


def pytest_configure(config):
    """Register custom pytest markers for Frontend/Backend E2E tests."""
    markers = [
        "e2e: End-to-end tests",
        "sprint04_fb_e2e: Sprint 04 Frontend/Backend E2E tests",
        "auth_flow: Category A - Authentication flow tests",
        "search_flow: Category B - Search flow tests",
        "sse_streaming: Category C - SSE streaming tests",
        "security_verification: Category D - Security verification tests",
        "error_handling: Category E - Error handling tests",
        "p0: Priority 0 (Critical) tests",
        "p1: Priority 1 (High) tests",
        "mock_mode: Tests that run with mocked services",
        "docker_mode: Tests that require Docker Compose stack",
    ]
    for marker in markers:
        config.addinivalue_line("markers", marker)


# =============================================================================
# Environment Detection
# =============================================================================

# E2E mode: "mock" (default) or "docker"
E2E_MODE = os.getenv("E2E_MODE", "mock")

# Gateway URL for Docker mode
GATEWAY_URL = os.getenv("E2E_GATEWAY_URL", "http://localhost:8080")
BACKEND_URL = os.getenv("E2E_BACKEND_URL", "http://localhost:8081")
AI_SERVICE_URL = os.getenv("E2E_AI_SERVICE_URL", "http://localhost:8000")

# JWT settings
JWT_SECRET = os.getenv(
    "JWT_SECRET_KEY", DEFAULT_JWT_SECRET
)
JWT_ALGORITHM = DEFAULT_JWT_ALGORITHM

# Global flag for AI Service availability
AI_SERVICE_AVAILABLE = False


def is_docker_mode() -> bool:
    """Check if running in Docker mode.

    Returns:
        True if E2E_MODE environment variable is set to 'docker'.
    """
    return E2E_MODE == "docker"


def is_ai_service_available() -> bool:
    """Check if AI Service is available for SSE streaming tests."""
    return AI_SERVICE_AVAILABLE


# =============================================================================
# Docker Mode Prerequisites Check
# =============================================================================


@pytest.fixture(scope="session", autouse=True)
def check_docker_services():
    """Verify Docker services are running when in Docker mode.

    In Docker mode, checks health endpoints of Gateway and Backend (required).
    AI Service is checked but marked as optional - its unavailability will
    only skip SSE-related tests, not the entire session.
    In Mock mode, this fixture is a no-op.
    """
    global AI_SERVICE_AVAILABLE

    if not is_docker_mode():
        return

    import httpx

    # Required services - skip entire session if unavailable
    required_services = [
        ("Gateway", f"{GATEWAY_URL}/actuator/health"),
        ("Backend", f"{BACKEND_URL}/actuator/health"),
    ]

    for name, url in required_services:
        try:
            resp = httpx.get(url, timeout=5.0)
            if resp.status_code != 200:
                pytest.skip(
                    f"Docker mode: {name} not healthy (status={resp.status_code}). "
                    f"URL: {url}"
                )
        except httpx.ConnectError as e:
            pytest.skip(
                f"Docker mode: {name} not reachable at {url}. "
                f"Ensure Docker Compose stack is running. Error: {e}"
            )
        except Exception as e:
            pytest.skip(
                f"Docker mode: {name} health check failed. "
                f"URL: {url}, Error: {e}"
            )

    # Optional service - AI Service (only for SSE streaming tests)
    try:
        resp = httpx.get(f"{AI_SERVICE_URL}/health", timeout=5.0)
        if resp.status_code == 200:
            AI_SERVICE_AVAILABLE = True
            print(f"\n[INFO] AI Service available at {AI_SERVICE_URL}")
        else:
            AI_SERVICE_AVAILABLE = False
            print(f"\n[WARN] AI Service not healthy (status={resp.status_code}). "
                  f"SSE streaming tests will be skipped.")
    except Exception as e:
        AI_SERVICE_AVAILABLE = False
        print(f"\n[WARN] AI Service not reachable at {AI_SERVICE_URL}. "
              f"SSE streaming tests will be skipped. Error: {e}")


# =============================================================================
# SSE Test Skip Decorator
# =============================================================================


def skip_if_no_ai_service(func):
    """Decorator to skip tests that require AI Service."""
    import functools

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if is_docker_mode() and not AI_SERVICE_AVAILABLE:
            pytest.skip("AI Service not available - SSE streaming tests skipped")
        return func(*args, **kwargs)
    return wrapper


# =============================================================================
# Core Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def anyio_backend():
    """Async backend for pytest-asyncio."""
    return "asyncio"


@pytest.fixture(scope="module")
def client():
    """Test client - Mock or Docker mode based on E2E_MODE env var.

    Mock mode (default): Returns FastAPI TestClient with in-process ASGI app.
    Docker mode: Returns httpx.Client pointing to the Gateway URL.
    """
    if is_docker_mode():
        import httpx

        return httpx.Client(base_url=GATEWAY_URL, timeout=30.0)
    else:
        return TestClient(app)


@pytest.fixture(scope="module")
def api_prefix() -> str:
    """API version prefix from settings."""
    return settings.api_v1_prefix


@pytest.fixture(scope="function")
async def async_client() -> AsyncIterator[AsyncClient]:
    """Async test client - Mock or Docker mode based on E2E_MODE env var.

    Mock mode (default): Uses ASGITransport with in-process app.
    Docker mode: Uses httpx AsyncClient pointing to the Gateway URL.
    """
    if is_docker_mode():
        async with AsyncClient(base_url=GATEWAY_URL, timeout=30.0) as ac:
            yield ac
    else:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


# =============================================================================
# AI Service Availability Fixture
# =============================================================================


@pytest.fixture
def require_ai_service():
    """Fixture that skips test if AI Service is not available.

    Use this fixture in SSE streaming tests that require AI Service.
    """
    if is_docker_mode() and not AI_SERVICE_AVAILABLE:
        pytest.skip("AI Service not available - test requires streaming capability")


# =============================================================================
# Authentication Fixtures
# =============================================================================


@pytest.fixture
def valid_token() -> str:
    """Generate a valid JWT access token for the default test user.

    Mock mode: Generates a self-signed JWT token locally.
    Docker mode: Authenticates against the Gateway login API to obtain a real token.
        Falls back to local generation if login fails.

    Note: Login response uses camelCase field names per ADR-002:
        - accessToken (not access_token)
        - refreshToken (not refresh_token)
    """
    if is_docker_mode():
        import httpx

        try:
            resp = httpx.post(
                f"{GATEWAY_URL}/api/v1/auth/login",
                json={
                    "email": TEST_ACCOUNTS["user"]["email"],
                    "password": TEST_ACCOUNTS["user"]["password"],
                },
                timeout=10.0,
            )
            if resp.status_code == 200:
                # Use camelCase field name per ADR-002
                token = resp.json().get("accessToken", "")
                if token:
                    return token
        except Exception:
            pass
        # Fallback: skip if Docker login is unavailable
        pytest.skip(
            "Docker mode: Login API unavailable. Cannot obtain valid token."
        )

    return generate_valid_token(
        user_id="user-001",
        email="test@example.com",
        role="user",
        secret=JWT_SECRET,
    )


@pytest.fixture
def admin_token() -> str:
    """Generate a valid JWT access token for the admin user.

    Mock mode: Generates a self-signed JWT token locally.
    Docker mode: Authenticates against the Gateway login API with admin credentials.
    """
    if is_docker_mode():
        import httpx

        try:
            resp = httpx.post(
                f"{GATEWAY_URL}/api/v1/auth/login",
                json={
                    "email": TEST_ACCOUNTS["admin"]["email"],
                    "password": TEST_ACCOUNTS["admin"]["password"],
                },
                timeout=10.0,
            )
            if resp.status_code == 200:
                # Use camelCase field name per ADR-002
                token = resp.json().get("accessToken", "")
                if token:
                    return token
        except Exception:
            pass
        pytest.skip(
            "Docker mode: Admin login API unavailable. Cannot obtain admin token."
        )

    return generate_valid_token(
        user_id="admin-001",
        email="admin@example.com",
        role="admin",
        secret=JWT_SECRET,
    )


@pytest.fixture
def readonly_token() -> str:
    """Generate a valid JWT access token for the read-only user."""
    return generate_valid_token(
        user_id="readonly-001",
        email="readonly@example.com",
        role="viewer",
        secret=JWT_SECRET,
    )


@pytest.fixture
def expired_token() -> str:
    """Generate an expired JWT access token."""
    return generate_expired_token(secret=JWT_SECRET)


@pytest.fixture
def tampered_token() -> str:
    """Generate a tampered (invalid signature) JWT token."""
    return generate_tampered_token(secret=JWT_SECRET)


@pytest.fixture
def refresh_token() -> str:
    """Generate a valid refresh token."""
    return generate_refresh_token(
        user_id="user-001",
        email="test@example.com",
        secret=JWT_SECRET,
    )


@pytest.fixture
def auth_headers(valid_token: str) -> Dict[str, str]:
    """Authorization headers with valid Bearer token."""
    return build_auth_headers(valid_token)


@pytest.fixture
def admin_auth_headers(admin_token: str) -> Dict[str, str]:
    """Authorization headers with admin Bearer token."""
    return build_auth_headers(admin_token)


# =============================================================================
# Request Body Fixtures
# =============================================================================


@pytest.fixture
def login_request_body() -> Dict[str, str]:
    """Standard login request body."""
    return {
        "email": TEST_ACCOUNTS["user"]["email"],
        "password": TEST_ACCOUNTS["user"]["password"],
    }


@pytest.fixture
def invalid_login_body() -> Dict[str, str]:
    """Invalid login request body."""
    return {
        "email": TEST_ACCOUNTS["invalid"]["email"],
        "password": TEST_ACCOUNTS["invalid"]["password"],
    }


@pytest.fixture
def keyword_search_body() -> Dict[str, Any]:
    """Keyword search request body (actual API model: snake_case)."""
    return {
        "query": "JWT 인증 필터",
        "top_k": 10,
    }


@pytest.fixture
def semantic_search_body() -> Dict[str, Any]:
    """Semantic search request body."""
    return {
        "query": "프로젝트에서 코드 품질을 유지하는 방법은?",
        "top_k": 10,
    }


@pytest.fixture
def hybrid_search_body() -> Dict[str, Any]:
    """Hybrid search (RRF fusion) request body."""
    return {
        "query": "RAG 시스템 동작 원리를 설명해주세요",
        "top_k": 10,
    }


@pytest.fixture
def sse_chat_body() -> Dict[str, Any]:
    """SSE chat streaming request body (ChatRequest model)."""
    return {
        "query": "RAG 시스템 동작 원리",
        "top_k": 5,
    }


@pytest.fixture
def empty_search_body() -> Dict[str, Any]:
    """Search request body expected to return no results."""
    return {
        "query": "zzzxxx9999nonexistent",
        "top_k": 10,
    }


@pytest.fixture
def large_query_1000_chars() -> str:
    """A valid Korean query of exactly 1000 characters."""
    base = "프로젝트에서 코드 품질을 유지하기 위한 방법론에 대해 설명해 주세요. "
    # Repeat and trim to exactly 1000 chars
    repeated = base * 30
    return repeated[:1000]


@pytest.fixture
def large_query_1001_chars(large_query_1000_chars: str) -> str:
    """A query of 1001 characters (exceeds limit)."""
    return large_query_1000_chars + "X"


# =============================================================================
# Mock Response Fixtures
# =============================================================================


@pytest.fixture
def mock_login_response() -> Dict[str, Any]:
    """Expected successful login response structure.

    Note: Uses camelCase field names per ADR-002:
    - accessToken (not access_token)
    - refreshToken (not refresh_token)
    """
    return {
        "accessToken": "mock-access-token",
        "refreshToken": "mock-refresh-token",
        "tokenType": "Bearer",
        "user": {
            "id": "user-001",
            "email": "test@example.com",
            "name": "Test User",
            "role": "USER",
        },
    }


@pytest.fixture
def mock_search_results() -> Dict[str, Any]:
    """Expected successful search response structure (actual API model)."""
    return {
        "query": "JWT 인증 필터",
        "results": [
            {
                "chunk_id": "chunk-001",
                "document_id": "doc-001",
                "content": "JWT 인증 필터는 모든 API 요청을 검증합니다...",
                "score": 0.92,
                "metadata": {
                    "documentType": "기술문서",
                    "projectName": "Knowledge Platform",
                },
            },
            {
                "chunk_id": "chunk-002",
                "document_id": "doc-002",
                "content": "Spring Security는 인증과 권한을...",
                "score": 0.85,
                "metadata": {
                    "documentType": "기술문서",
                    "projectName": "Knowledge Platform",
                },
            },
        ],
        "total": 2,
        "search_type": "hybrid",
        "latency_ms": 320,
    }


@pytest.fixture
def mock_sse_events() -> List[Dict[str, Any]]:
    """Expected SSE event sequence for chat streaming.

    Actual event types: start, chunk, end, error
    (NOT token/sources/done as in earlier test plan)
    """
    return [
        {
            "type": "start",
            "sources": [
                {"knowledgeId": "k-001", "title": "RAG 시스템 개요"},
                {"knowledgeId": "k-002", "title": "검색 파이프라인 가이드"},
            ],
            "context_length": 1500,
        },
        {"type": "chunk", "content": "RAG 시스템은 "},
        {"type": "chunk", "content": "검색 증강 생성을 "},
        {"type": "chunk", "content": "결합한 기술입니다."},
        {"type": "end"},
    ]


# =============================================================================
# XSS and Security Payload Fixtures
# =============================================================================


@pytest.fixture
def xss_payloads() -> List[str]:
    """Collection of XSS attack payloads for security testing."""
    return [
        "<script>alert('xss')</script>",
        '<img onerror="alert(1)" src=x>',
        '<svg onload="alert(1)">test</svg>',
        "javascript:alert(1)",
        '<div onmouseover="alert(1)">hover</div>',
        '"><script>alert(document.cookie)</script>',
        "<iframe src='javascript:alert(1)'></iframe>",
    ]


@pytest.fixture
def sql_injection_payloads() -> List[str]:
    """Collection of SQL injection payloads for security testing."""
    return [
        "'; DROP TABLE users; --",
        "1' OR '1'='1",
        "' UNION SELECT * FROM information_schema.tables --",
        "1; DELETE FROM documents WHERE 1=1",
        "' OR 1=1; --",
        "admin'--",
        "1' AND SLEEP(5) --",
    ]


# =============================================================================
# Protected Endpoint Fixtures
# =============================================================================


@pytest.fixture
def protected_endpoints(api_prefix: str) -> List[Dict[str, str]]:
    """List of protected endpoints that require JWT authentication.

    Per ADR-002, all endpoints except login/refresh/health require JWT.
    This includes search endpoints.
    """
    return [
        {"method": "GET", "path": f"{api_prefix}/auth/me"},
        {"method": "POST", "path": f"{api_prefix}/auth/logout"},
        # Search endpoints now require auth per ADR-002
        {"method": "POST", "path": f"{api_prefix}/search/hybrid"},
        {"method": "POST", "path": f"{api_prefix}/search/semantic"},
        {"method": "POST", "path": f"{api_prefix}/search/keyword"},
        {"method": "POST", "path": f"{api_prefix}/search/chat/stream"},
    ]


@pytest.fixture
def public_endpoints(api_prefix: str) -> List[Dict[str, str]]:
    """List of public endpoints that do not require authentication.

    Per ADR-003, only these endpoints are public:
    - POST /auth/login
    - POST /auth/refresh
    - GET /health

    Note: Search endpoints are NOT public per ADR-002.
    """
    return [
        {"method": "POST", "path": f"{api_prefix}/auth/login"},
        {"method": "POST", "path": f"{api_prefix}/auth/refresh"},
        {"method": "GET", "path": f"{api_prefix}/health"},
    ]


# =============================================================================
# Concurrent Request Fixtures
# =============================================================================


@pytest.fixture
def concurrent_queries() -> List[str]:
    """Set of queries for concurrent request testing (E-005)."""
    return [
        "JWT 인증 필터",
        "문서 업로드 절차",
        "RAG 시스템 동작 원리",
        "보안 감사 보고서",
        "프로젝트 관리 방법론",
    ]
