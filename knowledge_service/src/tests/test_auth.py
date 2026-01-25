"""
인증 API 엔드포인트 테스트

/api/v1/auth 엔드포인트 테스트
"""

import pytest
from fastapi.testclient import TestClient


class TestAuthEndpoints:
    """인증 API 엔드포인트 테스트"""

    # ============================================================================
    # 로그인 테스트
    # ============================================================================

    def test_login_success(self, client: TestClient, api_prefix: str):
        """정상 로그인 테스트"""
        response = client.post(
            f"{api_prefix}/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )

        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"
        assert data["expires_in"] > 0

    def test_login_admin(self, client: TestClient, api_prefix: str):
        """관리자 로그인 테스트"""
        response = client.post(
            f"{api_prefix}/auth/login",
            json={"email": "admin@example.com", "password": "admin123"},
        )

        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data

    def test_login_invalid_email(self, client: TestClient, api_prefix: str):
        """존재하지 않는 이메일로 로그인 시도"""
        response = client.post(
            f"{api_prefix}/auth/login",
            json={"email": "nonexistent@example.com", "password": "password123"},
        )

        assert response.status_code == 401
        assert "이메일 또는 비밀번호" in response.json()["detail"]

    def test_login_invalid_password(self, client: TestClient, api_prefix: str):
        """잘못된 비밀번호로 로그인 시도"""
        response = client.post(
            f"{api_prefix}/auth/login",
            json={"email": "test@example.com", "password": "wrongpassword"},
        )

        assert response.status_code == 401
        assert "이메일 또는 비밀번호" in response.json()["detail"]

    def test_login_invalid_email_format(self, client: TestClient, api_prefix: str):
        """잘못된 이메일 형식으로 로그인 시도"""
        response = client.post(
            f"{api_prefix}/auth/login",
            json={"email": "invalid-email", "password": "password123"},
        )

        assert response.status_code == 422  # Validation error

    def test_login_short_password(self, client: TestClient, api_prefix: str):
        """너무 짧은 비밀번호로 로그인 시도"""
        response = client.post(
            f"{api_prefix}/auth/login",
            json={"email": "test@example.com", "password": "12345"},  # 5자
        )

        assert response.status_code == 422  # Validation error

    # ============================================================================
    # 현재 사용자 정보 테스트
    # ============================================================================

    def test_get_me_success(self, client: TestClient, api_prefix: str):
        """인증된 사용자 정보 조회"""
        # 먼저 로그인
        login_response = client.post(
            f"{api_prefix}/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )
        access_token = login_response.json()["access_token"]

        # 사용자 정보 조회
        response = client.get(
            f"{api_prefix}/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200

        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["name"] == "테스트 사용자"
        assert data["role"] == "user"
        assert "id" in data
        assert "created_at" in data

    def test_get_me_unauthorized(self, client: TestClient, api_prefix: str):
        """인증 없이 사용자 정보 조회 시도"""
        response = client.get(f"{api_prefix}/auth/me")

        assert response.status_code == 401
        assert "인증이 필요합니다" in response.json()["detail"]

    def test_get_me_invalid_token(self, client: TestClient, api_prefix: str):
        """유효하지 않은 토큰으로 사용자 정보 조회 시도"""
        response = client.get(
            f"{api_prefix}/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code == 401
        assert "유효하지 않거나 만료된" in response.json()["detail"]

    # ============================================================================
    # 로그아웃 테스트
    # ============================================================================

    def test_logout_success(self, client: TestClient, api_prefix: str):
        """정상 로그아웃 테스트"""
        # 먼저 로그인
        login_response = client.post(
            f"{api_prefix}/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )
        access_token = login_response.json()["access_token"]

        # 로그아웃
        response = client.post(
            f"{api_prefix}/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "로그아웃" in data["message"]

    def test_logout_unauthorized(self, client: TestClient, api_prefix: str):
        """인증 없이 로그아웃 시도"""
        response = client.post(f"{api_prefix}/auth/logout")

        assert response.status_code == 401

    # ============================================================================
    # 토큰 갱신 테스트
    # ============================================================================

    def test_refresh_token_success(self, client: TestClient, api_prefix: str):
        """토큰 갱신 테스트"""
        # 먼저 로그인
        login_response = client.post(
            f"{api_prefix}/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )
        refresh_token = login_response.json()["refresh_token"]

        # 토큰 갱신
        response = client.post(
            f"{api_prefix}/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"

    def test_refresh_token_invalid(self, client: TestClient, api_prefix: str):
        """유효하지 않은 리프레시 토큰으로 갱신 시도"""
        response = client.post(
            f"{api_prefix}/auth/refresh",
            json={"refresh_token": "invalid-refresh-token"},
        )

        assert response.status_code == 401
        assert "유효하지 않거나 만료된" in response.json()["detail"]

    # ============================================================================
    # 관리자 권한 테스트
    # ============================================================================

    def test_admin_role(self, client: TestClient, api_prefix: str):
        """관리자 역할 확인"""
        # 관리자 로그인
        login_response = client.post(
            f"{api_prefix}/auth/login",
            json={"email": "admin@example.com", "password": "admin123"},
        )
        access_token = login_response.json()["access_token"]

        # 사용자 정보 조회
        response = client.get(
            f"{api_prefix}/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200

        data = response.json()
        assert data["role"] == "admin"
        assert data["name"] == "관리자"
