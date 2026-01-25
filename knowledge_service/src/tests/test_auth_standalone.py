"""
STORY-024: 직접 로그인 API 테스트 (Standalone)

auth_server.py에 대한 독립 테스트
의존성: pytest, httpx
"""

import pytest
from httpx import AsyncClient, ASGITransport
import sys
import os

# auth_server.py 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import after path setup
try:
    from auth_server import app
    AUTH_SERVER_AVAILABLE = True
except ImportError as e:
    AUTH_SERVER_AVAILABLE = False
    print(f"Warning: Could not import auth_server: {e}")

# Skip all tests if auth_server is not available
pytestmark = pytest.mark.skipif(
    not AUTH_SERVER_AVAILABLE,
    reason="auth_server.py not available"
)


@pytest.fixture
async def client():
    """비동기 테스트 클라이언트"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestLoginEndpoint:
    """
    TC-AUTH-001 ~ TC-AUTH-005: 로그인 API 테스트
    """

    @pytest.mark.asyncio
    async def test_tc_auth_001_login_success(self, client):
        """
        TC-AUTH-001: 유효한 자격 증명으로 로그인 성공

        우선순위: P0
        """
        response = await client.post(
            "/api/auth/login",
            json={
                "email": "test@example.com",
                "password": "password123",
                "rememberMe": False
            }
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert "accessToken" in data, "Missing accessToken"
        assert "refreshToken" in data, "Missing refreshToken"
        assert "expiresIn" in data, "Missing expiresIn"
        assert "user" in data, "Missing user"

        # User 정보 검증
        user = data["user"]
        assert user["email"] == "test@example.com"
        assert "id" in user
        assert "roles" in user

    @pytest.mark.asyncio
    async def test_tc_auth_002_login_invalid_password(self, client):
        """
        TC-AUTH-002: 잘못된 비밀번호로 로그인 실패

        우선순위: P0
        """
        response = await client.post(
            "/api/auth/login",
            json={
                "email": "test@example.com",
                "password": "wrongpassword",
                "rememberMe": False
            }
        )

        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        assert "이메일 또는 비밀번호" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_tc_auth_003_login_nonexistent_email(self, client):
        """
        TC-AUTH-003: 존재하지 않는 이메일로 로그인 실패

        우선순위: P0
        """
        response = await client.post(
            "/api/auth/login",
            json={
                "email": "notexist@example.com",
                "password": "password123",
                "rememberMe": False
            }
        )

        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        assert "이메일 또는 비밀번호" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_tc_auth_004_login_invalid_email_format(self, client):
        """
        TC-AUTH-004: 잘못된 이메일 형식 검증

        우선순위: P0
        """
        response = await client.post(
            "/api/auth/login",
            json={
                "email": "invalid-email",
                "password": "password123",
                "rememberMe": False
            }
        )

        # Pydantic EmailStr validation error
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"

    @pytest.mark.asyncio
    async def test_tc_auth_005_login_empty_password(self, client):
        """
        TC-AUTH-005: 빈 비밀번호 검증

        우선순위: P0
        """
        response = await client.post(
            "/api/auth/login",
            json={
                "email": "test@example.com",
                "password": "",
                "rememberMe": False
            }
        )

        # Should fail login (401) or validation (422)
        assert response.status_code in [401, 422], f"Expected 401 or 422, got {response.status_code}"


class TestTokenEndpoint:
    """
    TC-AUTH-006 ~ TC-AUTH-011: 토큰 관련 테스트
    """

    @pytest.mark.asyncio
    async def test_tc_auth_006_access_token_structure(self, client):
        """
        TC-AUTH-006: Access Token 생성 검증

        우선순위: P0
        """
        # 로그인
        response = await client.post(
            "/api/auth/login",
            json={
                "email": "test@example.com",
                "password": "password123",
                "rememberMe": False
            }
        )

        assert response.status_code == 200

        data = response.json()
        access_token = data["accessToken"]

        # JWT 구조 검증 (header.payload.signature)
        parts = access_token.split(".")
        assert len(parts) == 3, f"Invalid JWT structure: {len(parts)} parts"

        # Base64 디코딩으로 payload 확인
        import base64
        import json as json_lib

        # Padding 추가
        payload_b64 = parts[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding

        payload = json_lib.loads(base64.urlsafe_b64decode(payload_b64))

        # 필수 claims 확인
        assert "sub" in payload, "Missing 'sub' claim"
        assert "exp" in payload, "Missing 'exp' claim"
        assert "iat" in payload, "Missing 'iat' claim"
        assert "type" in payload, "Missing 'type' claim"
        assert payload["type"] == "access", f"Wrong type: {payload['type']}"

    @pytest.mark.asyncio
    async def test_tc_auth_007_admin_login(self, client):
        """
        TC-AUTH-007: 관리자 역할 로그인 검증

        우선순위: P1
        """
        response = await client.post(
            "/api/auth/login",
            json={
                "email": "admin@example.com",
                "password": "admin123!",
                "rememberMe": False
            }
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        user = data["user"]

        # 관리자 역할 확인
        assert "ADMIN" in user["roles"], f"Expected ADMIN role, got {user['roles']}"

    @pytest.mark.asyncio
    async def test_tc_auth_010_refresh_token_success(self, client):
        """
        TC-AUTH-010: Refresh Token 갱신 성공

        우선순위: P0
        """
        # 로그인
        login_response = await client.post(
            "/api/auth/login",
            json={
                "email": "test@example.com",
                "password": "password123",
                "rememberMe": False
            }
        )

        assert login_response.status_code == 200
        refresh_token = login_response.json()["refreshToken"]

        # 토큰 갱신
        refresh_response = await client.post(
            "/api/auth/refresh",
            json={"refreshToken": refresh_token}
        )

        assert refresh_response.status_code == 200, f"Expected 200, got {refresh_response.status_code}: {refresh_response.text}"

        data = refresh_response.json()
        assert "accessToken" in data, "Missing accessToken"
        assert "refreshToken" in data, "Missing refreshToken"
        assert "expiresIn" in data, "Missing expiresIn"

    @pytest.mark.asyncio
    async def test_tc_auth_011_refresh_token_invalid(self, client):
        """
        TC-AUTH-011: 만료된/유효하지 않은 Refresh Token 갱신 실패

        우선순위: P1
        """
        response = await client.post(
            "/api/auth/refresh",
            json={"refreshToken": "invalid-token"}
        )

        assert response.status_code == 401, f"Expected 401, got {response.status_code}"


class TestLogoutEndpoint:
    """
    TC-AUTH-012: 로그아웃 테스트
    """

    @pytest.mark.asyncio
    async def test_tc_auth_012_logout_success(self, client):
        """
        TC-AUTH-012: 로그아웃 성공

        우선순위: P1
        """
        response = await client.post("/api/auth/logout")

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()
        assert data["success"] is True
        assert "로그아웃" in data["message"]


class TestHealthEndpoint:
    """
    Health Check 테스트
    """

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """
        Health Check 엔드포인트 테스트
        """
        response = await client.get("/health")

        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "auth-server"


class TestUserRoles:
    """
    사용자 역할별 테스트
    """

    @pytest.mark.asyncio
    async def test_user_role_login(self, client):
        """
        일반 사용자 역할 테스트
        """
        response = await client.post(
            "/api/auth/login",
            json={
                "email": "user@example.com",
                "password": "user123!",
                "rememberMe": False
            }
        )

        assert response.status_code == 200

        data = response.json()
        user = data["user"]
        assert "USER" in user["roles"]

    @pytest.mark.asyncio
    async def test_manager_role_login(self, client):
        """
        매니저 역할 테스트
        """
        response = await client.post(
            "/api/auth/login",
            json={
                "email": "manager@example.com",
                "password": "manager123!",
                "rememberMe": False
            }
        )

        assert response.status_code == 200

        data = response.json()
        user = data["user"]
        assert "KNOWLEDGE_MANAGER" in user["roles"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
