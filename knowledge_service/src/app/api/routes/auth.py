"""
인증 API 엔드포인트

JWT 토큰 기반 인증
- 중앙화된 config.py 설정 사용
- bcrypt 비밀번호 해싱
- 환경변수 기반 관리자 계정
"""

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
# bcrypt 비밀번호 해싱 컨텍스트
# ---------------------------------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호 검증 (bcrypt)"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """비밀번호 해시 생성 (bcrypt)"""
    return pwd_context.hash(password)


def _get_jwt_secret() -> str:
    """
    JWT Secret Key를 settings에서 가져옴

    Raises:
        ValueError: jwt_secret_key가 설정되지 않았거나 너무 짧은 경우
    """
    secret = settings.jwt_secret_key
    if not secret:
        raise ValueError(
            "JWT_SECRET_KEY is not set. Add it to .env file."
        )
    if len(secret) < 32:
        logger.warning(
            "JWT_SECRET_KEY is shorter than recommended (32+ chars). "
            "Consider using a longer key for production."
        )
    return secret


# ---------------------------------------------------------------------------
# 사용자 저장소 (환경변수 기반 + PostgreSQL 연동 준비)
# ---------------------------------------------------------------------------

def _load_users_from_settings() -> Dict[str, Dict[str, Any]]:
    """
    settings에서 관리자/테스트 계정 로드

    Returns:
        사용자 딕셔너리 (email -> user_info)
    """
    users: Dict[str, Dict[str, Any]] = {}

    # 관리자 계정
    if settings.admin_password_hash:
        users[settings.admin_email] = {
            "id": "user-admin",
            "email": settings.admin_email,
            "password_hash": settings.admin_password_hash,
            "name": settings.admin_name,
            "role": "admin",
            "created_at": "2026-01-01T00:00:00Z",
        }
        logger.info(f"Admin user loaded from settings: {settings.admin_email}")
    else:
        logger.warning(
            "ADMIN_PASSWORD_HASH not set. Admin account not available. "
            "Generate hash with: python -c \"import bcrypt; "
            "print(bcrypt.hashpw(b'password', bcrypt.gensalt()).decode())\""
        )

    # 테스트 사용자 계정 (선택)
    if settings.test_user_email and settings.test_user_password_hash:
        users[settings.test_user_email] = {
            "id": "user-test",
            "email": settings.test_user_email,
            "password_hash": settings.test_user_password_hash,
            "name": settings.test_user_name or "테스트 사용자",
            "role": "user",
            "created_at": "2026-01-01T00:00:00Z",
        }
        logger.info(f"Test user loaded from settings: {settings.test_user_email}")

    return users


# 사용자 저장소 (환경변수 기반)
# TODO: PostgreSQL users 테이블 연동 시 이 부분을 DB 조회로 대체
USERS: Dict[str, Dict[str, Any]] = _load_users_from_settings()

# 리프레시 토큰 저장소
# TODO: Redis 또는 PostgreSQL로 마이그레이션 권장 (분산 환경 대응)
REFRESH_TOKENS: Dict[str, str] = {}


async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    이메일로 사용자 조회

    Args:
        email: 사용자 이메일

    Returns:
        사용자 정보 딕셔너리 또는 None
    """
    return USERS.get(email)


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
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access",
    }
    return jwt.encode(payload, _get_jwt_secret(), algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: str) -> str:
    """
    리프레시 토큰 생성

    Args:
        user_id: 사용자 ID

    Returns:
        리프레시 토큰 문자열
    """
    expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh",
        "jti": secrets.token_urlsafe(32),
    }
    token = jwt.encode(payload, _get_jwt_secret(), algorithm=settings.jwt_algorithm)
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
        payload = jwt.decode(
            token,
            _get_jwt_secret(),
            algorithms=[settings.jwt_algorithm]
        )
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
        expires_in=settings.access_token_expire_minutes * 60,
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
        expires_in=settings.access_token_expire_minutes * 60,
    )
