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


# Override client fixture to avoid app.main import
@pytest.fixture(scope="function")
def client():
    """
    Unit 테스트에서는 TestClient가 필요 없으므로 None 반환
    실제 client가 필요한 테스트는 integration/e2e로 이동
    """
    return None


# Override async_client fixture
@pytest.fixture(scope="function")
async def async_client():
    """
    Unit 테스트에서는 AsyncClient가 필요 없으므로 None 반환
    """
    yield None
