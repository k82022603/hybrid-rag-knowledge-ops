"""
인증 API 엔드포인트

JWT 토큰 기반 인증
- 환경변수 기반 JWT_SECRET_KEY (필수)
- bcrypt 비밀번호 해싱
- PostgreSQL 사용자 테이블 연동 (또는 환경변수 기반 관리자 계정)
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
import jwt

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# 보안 설정 (P0 - 환경변수 필수)
# ---------------------------------------------------------------------------

# JWT Secret Key - 환경변수에서 로드 (필수)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    raise ValueError(
        "JWT_SECRET_KEY environment variable is required. "
        "Set it in .env file or environment variables."
    )

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# bcrypt 비밀번호 해싱 컨텍스트
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호 검증 (bcrypt)"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """비밀번호 해시 생성 (bcrypt)"""
    return pwd_context.hash(password)


# ---------------------------------------------------------------------------
# 사용자 저장소 (환경변수 기반 + PostgreSQL 연동 준비)
# ---------------------------------------------------------------------------

def _load_users_from_env() -> Dict[str, Dict[str, Any]]:
    """
    환경변수에서 관리자 계정 로드

    환경변수:
        ADMIN_EMAIL: 관리자 이메일 (기본: admin@example.com)
        ADMIN_PASSWORD_HASH: bcrypt 해시된 비밀번호 (필수)
        ADMIN_NAME: 관리자 이름 (기본: 시스템 관리자)

        TEST_USER_EMAIL: 테스트 사용자 이메일 (선택)
        TEST_USER_PASSWORD_HASH: bcrypt 해시된 비밀번호 (선택)
        TEST_USER_NAME: 테스트 사용자 이름 (선택)

    Returns:
        사용자 딕셔너리 (email -> user_info)
    """
    users: Dict[str, Dict[str, Any]] = {}

    # 관리자 계정 (환경변수)
    admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
    admin_password_hash = os.getenv("ADMIN_PASSWORD_HASH")

    if admin_password_hash:
        users[admin_email] = {
            "id": "user-admin",
            "email": admin_email,
            "password_hash": admin_password_hash,
            "name": os.getenv("ADMIN_NAME", "시스템 관리자"),
            "role": "admin",
            "created_at": "2026-01-01T00:00:00Z",
        }
        logger.info(f"Admin user loaded from environment: {admin_email}")
    else:
        logger.warning(
            "ADMIN_PASSWORD_HASH not set. Admin account not available. "
            "Generate hash with: python -c \"from passlib.context import CryptContext; "
            "print(CryptContext(schemes=['bcrypt']).hash('your_password'))\""
        )

    # 테스트 사용자 계정 (환경변수, 선택)
    test_email = os.getenv("TEST_USER_EMAIL")
    test_password_hash = os.getenv("TEST_USER_PASSWORD_HASH")

    if test_email and test_password_hash:
        users[test_email] = {
            "id": "user-test",
            "email": test_email,
            "password_hash": test_password_hash,
            "name": os.getenv("TEST_USER_NAME", "테스트 사용자"),
            "role": "user",
            "created_at": "2026-01-01T00:00:00Z",
        }
        logger.info(f"Test user loaded from environment: {test_email}")

    return users


# 사용자 저장소 (환경변수 기반)
# TODO: PostgreSQL users 테이블 연동 시 이 부분을 DB 조회로 대체
USERS: Dict[str, Dict[str, Any]] = _load_users_from_env()

# 리프레시 토큰 저장소
# TODO: Redis 또는 PostgreSQL로 마이그레이션 권장 (분산 환경 대응)
REFRESH_TOKENS: Dict[str, str] = {}


async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    이메일로 사용자 조회

    현재: 환경변수 기반 사용자 저장소에서 조회
    TODO: PostgreSQL users 테이블 연동

    Args:
        email: 사용자 이메일

    Returns:
        사용자 정보 딕셔너리 또는 None
    """
    # 환경변수 기반 사용자 조회
    user = USERS.get(email)
    if user:
        return user

    # TODO: PostgreSQL 연동 시 아래 코드 활성화
    # async with get_async_session() as session:
    #     result = await session.execute(
    #         select(UserModel).where(UserModel.email == email)
    #     )
    #     user_model = result.scalar_one_or_none()
    #     if user_model:
    #         return {
    #             "id": str(user_model.id),
    #             "email": user_model.email,
    #             "password_hash": user_model.password_hash,
    #             "name": user_model.name,
    #             "role": user_model.role,
    #             "created_at": user_model.created_at.isoformat(),
    #         }

    return None


async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """
    ID로 사용자 조회

    Args:
        user_id: 사용자 ID

    Returns:
        사용자 정보 딕셔너리 또는 None
    """
    for user in USERS.values():
        if user["id"] == user_id:
            return user

    # TODO: PostgreSQL 연동 시 DB 조회 추가

    return None

# HTTP Bearer 인증
security = HTTPBearer(auto_error=False)


# ============================================================================
# Request/Response Models
# ============================================================================

class LoginRequest(BaseModel):
    """로그인 요청 모델"""
    email: EmailStr = Field(description="이메일 주소")
    password: str = Field(min_length=6, description="비밀번호 (최소 6자)")


class TokenResponse(BaseModel):
    """토큰 응답 모델 (camelCase - ADR-001)"""
    access_token: str = Field(description="JWT 액세스 토큰", serialization_alias="accessToken")
    refresh_token: str = Field(description="리프레시 토큰", serialization_alias="refreshToken")
    token_type: str = Field(default="Bearer", description="토큰 타입", serialization_alias="tokenType")
    expires_in: int = Field(description="액세스 토큰 만료 시간 (초)", serialization_alias="expiresIn")

    model_config = {"populate_by_name": True}


class RefreshRequest(BaseModel):
    """토큰 갱신 요청 모델 (camelCase - ADR-001)"""
    refresh_token: str = Field(description="리프레시 토큰", alias="refreshToken")

    model_config = {"populate_by_name": True}


class UserResponse(BaseModel):
    """사용자 정보 응답 모델 (camelCase - ADR-001)"""
    id: str = Field(description="사용자 ID")
    email: str = Field(description="이메일 주소")
    name: str = Field(description="사용자 이름")
    role: str = Field(description="사용자 역할")
    created_at: str = Field(description="계정 생성일", serialization_alias="createdAt")

    model_config = {"populate_by_name": True}


class LogoutResponse(BaseModel):
    """로그아웃 응답 모델"""
    message: str = Field(default="로그아웃 되었습니다")
    success: bool = Field(default=True)


# ============================================================================
# Helper Functions
# ============================================================================

def create_access_token(user_id: str, email: str, role: str) -> str:
    """
    JWT 액세스 토큰 생성

    Args:
        user_id: 사용자 ID
        email: 이메일 주소
        role: 사용자 역할

    Returns:
        JWT 토큰 문자열
    """
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    """
    리프레시 토큰 생성

    Args:
        user_id: 사용자 ID

    Returns:
        리프레시 토큰 문자열
    """
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh",
        "jti": secrets.token_urlsafe(32),
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    # 저장소에 등록
    REFRESH_TOKENS[user_id] = token
    return token


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    JWT 토큰 디코딩

    Args:
        token: JWT 토큰 문자열

    Returns:
        토큰 페이로드 또는 None (실패 시)
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    """
    현재 인증된 사용자 정보 조회 (Dependency)

    Args:
        credentials: HTTP Bearer 토큰

    Returns:
        사용자 정보 딕셔너리

    Raises:
        HTTPException: 인증 실패 시
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않거나 만료된 토큰입니다",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 사용자 정보 조회
    email = payload.get("email")
    user = await get_user_by_email(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사용자를 찾을 수 없습니다",
        )

    return user


# ============================================================================
# API Endpoints
# ============================================================================

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="로그인",
    description="이메일/비밀번호로 로그인하여 JWT 토큰 발급",
)
async def login(request: LoginRequest) -> TokenResponse:
    """
    사용자 로그인

    환경변수로 설정된 계정 사용:
    - ADMIN_EMAIL / ADMIN_PASSWORD_HASH (관리자)
    - TEST_USER_EMAIL / TEST_USER_PASSWORD_HASH (테스트 사용자, 선택)

    Args:
        request: 로그인 요청 (email, password)

    Returns:
        JWT 토큰 (access_token, refresh_token)

    Raises:
        HTTPException: 인증 실패 시
    """
    logger.info(f"Login attempt: {request.email}")

    # 사용자 조회
    user = await get_user_by_email(request.email)
    if user is None:
        logger.warning(f"User not found: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다",
        )

    # 비밀번호 검증 (bcrypt 해싱)
    password_hash = user.get("password_hash")
    if not password_hash or not verify_password(request.password, password_hash):
        logger.warning(f"Invalid password for: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다",
        )

    # 토큰 생성
    access_token = create_access_token(user["id"], user["email"], user["role"])
    refresh_token = create_refresh_token(user["id"])

    logger.info(f"Login successful: {request.email}")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="로그아웃",
    description="현재 세션 로그아웃 (리프레시 토큰 무효화)",
)
async def logout(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> LogoutResponse:
    """
    사용자 로그아웃

    Args:
        current_user: 현재 인증된 사용자 (Dependency)

    Returns:
        로그아웃 성공 메시지
    """
    user_id = current_user["id"]

    # 리프레시 토큰 무효화
    if user_id in REFRESH_TOKENS:
        del REFRESH_TOKENS[user_id]

    logger.info(f"Logout: {current_user['email']}")

    return LogoutResponse(
        message="로그아웃 되었습니다",
        success=True,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="현재 사용자 정보",
    description="인증된 사용자의 프로필 정보 조회",
)
async def get_me(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> UserResponse:
    """
    현재 인증된 사용자 정보 조회

    Args:
        current_user: 현재 인증된 사용자 (Dependency)

    Returns:
        사용자 프로필 정보
    """
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        name=current_user["name"],
        role=current_user["role"],
        created_at=current_user["created_at"],
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="토큰 갱신",
    description="리프레시 토큰으로 새 액세스 토큰 발급",
)
async def refresh_token(request: RefreshRequest) -> TokenResponse:
    """
    토큰 갱신

    유효한 리프레시 토큰으로 새 액세스 토큰과 리프레시 토큰 발급

    Args:
        request: 갱신 요청 (refresh_token)

    Returns:
        새 JWT 토큰

    Raises:
        HTTPException: 토큰 검증 실패 시
    """
    payload = decode_token(request.refresh_token)

    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않거나 만료된 리프레시 토큰입니다",
        )

    user_id = payload.get("sub")

    # 저장된 리프레시 토큰과 비교
    stored_token = REFRESH_TOKENS.get(user_id)
    if stored_token != request.refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="리프레시 토큰이 유효하지 않습니다",
        )

    # 사용자 조회
    user = await get_user_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사용자를 찾을 수 없습니다",
        )

    # 새 토큰 생성
    access_token = create_access_token(user["id"], user["email"], user["role"])
    refresh_token = create_refresh_token(user["id"])

    logger.info(f"Token refreshed for: {user['email']}")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
