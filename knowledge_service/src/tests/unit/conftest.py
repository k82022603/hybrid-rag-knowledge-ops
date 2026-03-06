"""
Unit Test 전용 conftest

app.main import를 피하기 위한 가벼운 fixture 제공
인증이 필요한 API 테스트를 위해 테스트 사용자 및 auth_headers 제공
"""

from datetime import datetime, timedelta
from typing import Any, Dict

import jwt
import pytest


# =============================================================================
# Test User Setup
# =============================================================================


# 테스트 사용자 정보 (parent conftest.py의 TEST_USER_DATA와 동일)
TEST_USER_DATA = {
    "id": "user-test-001",
    "email": "test@example.com",
    "password_hash": "$2b$12$sriFYJkYkErkTeRD39HH.e1lHoiikNXUBLj.nASqeRIM.hLChpQBK",
    "name": "테스트 사용자",
    "role": "user",
    "created_at": "2026-01-01T00:00:00Z",
}


@pytest.fixture(scope="session", autouse=True)
def setup_test_users():
    """
    테스트 세션 시작 시 USERS 딕셔너리에 테스트 사용자 추가

    auth 미들웨어가 적용된 API 엔드포인트 테스트를 위해
    인메모리 사용자 저장소에 테스트 사용자를 등록합니다.
    """
    from app.api.routes.auth import USERS

    USERS["test@example.com"] = TEST_USER_DATA.copy()

    yield

    if "test@example.com" in USERS:
        del USERS["test@example.com"]


# =============================================================================
# JWT / Auth Fixtures
# =============================================================================


def _get_test_jwt_secret() -> str:
    """테스트용 JWT Secret 키 반환"""
    from app.core.config import settings

    if settings.jwt_secret_key:
        return settings.jwt_secret_key
    return "test-jwt-secret-key-for-unit-testing-32chars"


@pytest.fixture(scope="session")
def jwt_secret() -> str:
    """JWT Secret Key"""
    return _get_test_jwt_secret()


@pytest.fixture(scope="session")
def jwt_algorithm() -> str:
    """JWT Algorithm"""
    from app.core.config import settings

    return settings.jwt_algorithm


@pytest.fixture(scope="function")
def valid_access_token(jwt_secret: str, jwt_algorithm: str) -> str:
    """유효한 JWT 액세스 토큰 생성"""
    payload = {
        "sub": "user-test-001",
        "email": "test@example.com",
        "role": "user",
        "type": "access",
        "exp": datetime.utcnow() + timedelta(minutes=30),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, jwt_secret, algorithm=jwt_algorithm)


@pytest.fixture(scope="function")
def auth_headers(valid_access_token: str) -> Dict[str, str]:
    """인증 헤더 (Bearer Token) - 인증이 필요한 API 테스트용"""
    return {"Authorization": f"Bearer {valid_access_token}"}


# =============================================================================
# HTTP Client Fixtures
# =============================================================================


@pytest.fixture(scope="function")
def client():
    """
    TestClient for API endpoint unit tests (document upload, status, etc.)
    """
    from fastapi.testclient import TestClient
    from app.main import app

    return TestClient(app)


# Override async_client fixture
@pytest.fixture(scope="function")
async def async_client():
    """
    Unit 테스트에서는 AsyncClient가 필요 없으므로 None 반환
    """
    yield None
