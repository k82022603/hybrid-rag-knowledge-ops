"""
Unit Test 전용 conftest

app.main import를 피하기 위한 가벼운 fixture 제공
"""

import pytest


# Override the session-level setup_test_users fixture from parent conftest
@pytest.fixture(scope="session", autouse=True)
def setup_test_users():
    """
    Unit 테스트에서는 auth 관련 fixture가 필요 없으므로 빈 fixture로 대체
    """
    yield


# Provide real TestClient for unit tests that need API endpoint testing
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
