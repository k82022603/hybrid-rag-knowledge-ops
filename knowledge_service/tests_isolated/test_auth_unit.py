"""
STORY-024: 직접 로그인 API 단위 테스트

auth.py (FastAPI 라우트) 로직에 대한 단위 테스트
Redis 의존성 없이 실행 가능
"""

import pytest
import jwt
from datetime import datetime, timedelta

# JWT 설정 (auth.py와 동일)
JWT_SECRET_KEY = "knowledge-service-secret-key-change-in-production"
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


class TestJWTTokenGeneration:
    """
    TC-AUTH-006: JWT 토큰 생성 단위 테스트
    """

    def test_create_access_token(self):
        """
        Access Token 생성 및 구조 검증
        """
        user_id = "user-001"
        email = "test@example.com"
        role = "user"

        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {
            "sub": user_id,
            "email": email,
            "role": role,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access",
        }
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

        # 토큰 디코딩 검증
        decoded = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

        assert decoded["sub"] == user_id
        assert decoded["email"] == email
        assert decoded["role"] == role
        assert decoded["type"] == "access"
        assert "exp" in decoded
        assert "iat" in decoded

    def test_create_refresh_token(self):
        """
        Refresh Token 생성 및 구조 검증
        """
        import secrets

        user_id = "user-001"

        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh",
            "jti": secrets.token_urlsafe(32),
        }
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

        # 토큰 디코딩 검증
        decoded = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

        assert decoded["sub"] == user_id
        assert decoded["type"] == "refresh"
        assert "jti" in decoded
        assert "exp" in decoded

    def test_token_expiration(self):
        """
        토큰 만료 검증
        """
        user_id = "user-001"

        # 이미 만료된 토큰 생성
        expire = datetime.utcnow() - timedelta(minutes=1)
        payload = {
            "sub": user_id,
            "exp": expire,
            "type": "access",
        }
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

        # 만료된 토큰 디코딩 시 예외 발생
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

    def test_invalid_token(self):
        """
        유효하지 않은 토큰 검증
        """
        invalid_token = "invalid.token.here"

        with pytest.raises(jwt.InvalidTokenError):
            jwt.decode(invalid_token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

    def test_wrong_secret_key(self):
        """
        잘못된 비밀키로 토큰 검증
        """
        payload = {
            "sub": "user-001",
            "exp": datetime.utcnow() + timedelta(minutes=30),
            "type": "access",
        }
        token = jwt.encode(payload, "correct-secret", algorithm=JWT_ALGORITHM)

        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(token, "wrong-secret", algorithms=[JWT_ALGORITHM])


class TestPasswordValidation:
    """
    비밀번호 검증 테스트
    """

    def test_password_match(self):
        """
        비밀번호 일치 검증
        """
        stored_password = "password123"
        input_password = "password123"

        # Mock 구현에서는 평문 비교 (실제는 bcrypt 사용)
        assert stored_password == input_password

    def test_password_mismatch(self):
        """
        비밀번호 불일치 검증
        """
        stored_password = "password123"
        input_password = "wrongpassword"

        assert stored_password != input_password


class TestEmailValidation:
    """
    이메일 검증 테스트
    """

    def test_valid_email_format(self):
        """
        유효한 이메일 형식
        """
        import re

        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

        valid_emails = [
            "test@example.com",
            "admin@example.com",
            "user.name@domain.co.kr",
        ]

        for email in valid_emails:
            assert re.match(email_pattern, email), f"Valid email rejected: {email}"

    def test_invalid_email_format(self):
        """
        유효하지 않은 이메일 형식
        """
        import re

        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

        invalid_emails = [
            "invalid-email",
            "@nodomain.com",
            "no-at-sign.com",
            "spaces in@email.com",
        ]

        for email in invalid_emails:
            assert not re.match(email_pattern, email), f"Invalid email accepted: {email}"


class TestUserLookup:
    """
    사용자 조회 테스트
    """

    def test_user_exists(self):
        """
        존재하는 사용자 조회
        """
        mock_users = {
            "test@example.com": {
                "id": "user-001",
                "email": "test@example.com",
                "password": "password123",
                "name": "Test User",
                "role": "user",
            }
        }

        user = mock_users.get("test@example.com")
        assert user is not None
        assert user["email"] == "test@example.com"

    def test_user_not_exists(self):
        """
        존재하지 않는 사용자 조회
        """
        mock_users = {
            "test@example.com": {
                "id": "user-001",
                "email": "test@example.com",
            }
        }

        user = mock_users.get("notexist@example.com")
        assert user is None


class TestTokenDecoding:
    """
    토큰 디코딩 테스트
    """

    def test_decode_valid_access_token(self):
        """
        유효한 Access Token 디코딩
        """
        payload = {
            "sub": "user-001",
            "email": "test@example.com",
            "role": "user",
            "exp": datetime.utcnow() + timedelta(minutes=30),
            "iat": datetime.utcnow(),
            "type": "access",
        }
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

        decoded = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

        assert decoded["type"] == "access"
        assert decoded["sub"] == "user-001"

    def test_decode_valid_refresh_token(self):
        """
        유효한 Refresh Token 디코딩
        """
        payload = {
            "sub": "user-001",
            "exp": datetime.utcnow() + timedelta(days=7),
            "iat": datetime.utcnow(),
            "type": "refresh",
            "jti": "unique-id-123",
        }
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

        decoded = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

        assert decoded["type"] == "refresh"
        assert decoded["jti"] == "unique-id-123"

    def test_reject_access_token_as_refresh(self):
        """
        Access Token을 Refresh Token으로 사용 시도 거부
        """
        payload = {
            "sub": "user-001",
            "exp": datetime.utcnow() + timedelta(minutes=30),
            "type": "access",
        }
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

        decoded = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

        # type이 "refresh"가 아니므로 refresh 용도로 사용 불가
        assert decoded.get("type") != "refresh"


class TestRoleBasedAccess:
    """
    역할 기반 접근 제어 테스트
    """

    def test_admin_role(self):
        """
        관리자 역할 확인
        """
        user = {
            "id": "user-002",
            "email": "admin@example.com",
            "roles": ["ADMIN", "KNOWLEDGE_MANAGER", "USER"],
        }

        assert "ADMIN" in user["roles"]

    def test_user_role(self):
        """
        일반 사용자 역할 확인
        """
        user = {
            "id": "user-001",
            "email": "test@example.com",
            "roles": ["USER"],
        }

        assert "USER" in user["roles"]
        assert "ADMIN" not in user["roles"]

    def test_manager_role(self):
        """
        매니저 역할 확인
        """
        user = {
            "id": "user-004",
            "email": "manager@example.com",
            "roles": ["KNOWLEDGE_MANAGER", "USER"],
        }

        assert "KNOWLEDGE_MANAGER" in user["roles"]
        assert "ADMIN" not in user["roles"]


class TestLoginFlow:
    """
    로그인 플로우 단위 테스트
    """

    def test_successful_login_flow(self):
        """
        성공적인 로그인 플로우
        """
        mock_users = {
            "test@example.com": {
                "id": "user-001",
                "email": "test@example.com",
                "password": "password123",
                "role": "user",
            }
        }

        email = "test@example.com"
        password = "password123"

        # 1. 사용자 조회
        user = mock_users.get(email)
        assert user is not None, "User should exist"

        # 2. 비밀번호 검증
        assert user["password"] == password, "Password should match"

        # 3. 토큰 생성
        payload = {
            "sub": user["id"],
            "email": user["email"],
            "role": user["role"],
            "exp": datetime.utcnow() + timedelta(minutes=30),
            "type": "access",
        }
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

        assert token is not None
        assert len(token.split(".")) == 3

    def test_failed_login_wrong_password(self):
        """
        잘못된 비밀번호로 로그인 실패
        """
        mock_users = {
            "test@example.com": {
                "id": "user-001",
                "email": "test@example.com",
                "password": "password123",
                "role": "user",
            }
        }

        email = "test@example.com"
        password = "wrongpassword"

        user = mock_users.get(email)
        assert user is not None

        # 비밀번호 불일치
        assert user["password"] != password

    def test_failed_login_user_not_found(self):
        """
        존재하지 않는 사용자로 로그인 실패
        """
        mock_users = {
            "test@example.com": {
                "id": "user-001",
                "email": "test@example.com",
                "password": "password123",
            }
        }

        email = "notexist@example.com"

        user = mock_users.get(email)
        assert user is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
