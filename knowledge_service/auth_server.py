#!/usr/bin/env python3
"""
Standalone Auth Server for Development Testing
Minimal FastAPI server with JWT authentication endpoints
"""

import secrets
import redis
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
import jwt

# JWT Configuration
JWT_SECRET_KEY = "knowledge-service-secret-key-change-in-production"
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Redis Connection
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Mock user database
MOCK_USERS: Dict[str, Dict[str, Any]] = {
    "test@example.com": {
        "id": "user-001",
        "email": "test@example.com",
        "password": "password123",
        "name": "테스트 사용자",
        "firstName": "테스트",
        "lastName": "사용자",
        "role": "user",
        "roles": ["USER"],
        "department": "개발팀",
        "employeeId": "EMP001",
        "created_at": "2026-01-01T00:00:00Z",
    },
    "admin@example.com": {
        "id": "user-002",
        "email": "admin@example.com",
        "password": "admin123!",
        "name": "관리자",
        "firstName": "시스템",
        "lastName": "관리자",
        "role": "admin",
        "roles": ["ADMIN", "KNOWLEDGE_MANAGER", "USER"],
        "department": "IT",
        "employeeId": "EMP002",
        "created_at": "2026-01-01T00:00:00Z",
    },
    "user@example.com": {
        "id": "user-003",
        "email": "user@example.com",
        "password": "user123!",
        "name": "일반 사용자",
        "firstName": "일반",
        "lastName": "사용자",
        "role": "user",
        "roles": ["USER"],
        "department": "General",
        "employeeId": "EMP003",
        "created_at": "2026-01-01T00:00:00Z",
    },
    "manager@example.com": {
        "id": "user-004",
        "email": "manager@example.com",
        "password": "manager123!",
        "name": "매니저",
        "firstName": "지식",
        "lastName": "매니저",
        "role": "manager",
        "roles": ["KNOWLEDGE_MANAGER", "USER"],
        "department": "Knowledge Management",
        "employeeId": "EMP004",
        "created_at": "2026-01-01T00:00:00Z",
    },
}

# Refresh token storage (Redis)
REFRESH_TOKEN_PREFIX = "auth:refresh_token:"
SESSION_PREFIX = "auth:session:"


# Models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    rememberMe: bool = False


class TokenResponse(BaseModel):
    accessToken: str
    refreshToken: str
    expiresIn: int
    user: Dict[str, Any]


class RefreshRequest(BaseModel):
    refreshToken: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    firstName: str
    lastName: str
    role: str
    roles: list
    department: str
    employeeId: str


# Helper functions
def create_access_token(user_id: str, email: str, role: str) -> str:
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
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh",
        "jti": secrets.token_urlsafe(32),
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    # Store in Redis with TTL
    redis_client.setex(
        f"{REFRESH_TOKEN_PREFIX}{user_id}",
        REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,  # TTL in seconds
        token
    )
    return token


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# FastAPI app
app = FastAPI(title="Auth Server", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "auth-server"}


@app.post("/api/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Login endpoint"""
    print(f"[AUTH] Login attempt: {request.email}")

    user = MOCK_USERS.get(request.email.lower())
    if user is None:
        print(f"[AUTH] User not found: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다",
        )

    if user["password"] != request.password:
        print(f"[AUTH] Invalid password for: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다",
        )

    access_token = create_access_token(user["id"], user["email"], user["role"])
    refresh_token = create_refresh_token(user["id"])

    # Store session info in Redis
    import json
    session_data = {
        "user_id": user["id"],
        "email": user["email"],
        "role": user["role"],
        "login_at": datetime.utcnow().isoformat(),
    }
    redis_client.setex(
        f"{SESSION_PREFIX}{user['id']}",
        ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        json.dumps(session_data)
    )

    print(f"[AUTH] Login successful: {request.email} (session stored in Redis)")

    user_response = {
        "id": user["id"],
        "username": user["email"].split("@")[0],
        "email": user["email"],
        "name": user["name"],
        "firstName": user["firstName"],
        "lastName": user["lastName"],
        "department": user["department"],
        "employeeId": user["employeeId"],
        "roles": user["roles"],
    }

    return TokenResponse(
        accessToken=access_token,
        refreshToken=refresh_token,
        expiresIn=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_response,
    )


@app.post("/api/auth/logout")
async def logout():
    """Logout endpoint"""
    return {"message": "로그아웃 되었습니다", "success": True}


@app.post("/api/auth/refresh")
async def refresh_token(request: RefreshRequest):
    """Refresh token endpoint"""
    payload = decode_token(request.refreshToken)

    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 리프레시 토큰입니다",
        )

    user_id = payload.get("sub")

    # Verify refresh token from Redis
    stored_token = redis_client.get(f"{REFRESH_TOKEN_PREFIX}{user_id}")
    if stored_token != request.refreshToken:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="리프레시 토큰이 유효하지 않습니다",
        )

    user = None
    for u in MOCK_USERS.values():
        if u["id"] == user_id:
            user = u
            break

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사용자를 찾을 수 없습니다",
        )

    access_token = create_access_token(user["id"], user["email"], user["role"])
    new_refresh_token = create_refresh_token(user["id"])

    return {
        "accessToken": access_token,
        "refreshToken": new_refresh_token,
        "expiresIn": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 60)
    print("Auth Server Starting...")
    print("=" * 60)
    print("\nTest Accounts:")
    for email, user in MOCK_USERS.items():
        print(f"  - {email} / {user['password']} ({user['role']})")
    print("\n" + "=" * 60 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8002)
