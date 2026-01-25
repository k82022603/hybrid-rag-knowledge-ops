# =============================================================================
# Backend Auth Service for Hybrid RAG Knowledge Platform
# STORY-024: FastAPI Auth Server with JWT authentication
# =============================================================================

FROM python:3.11-alpine

# Create non-root user for security
RUN addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
    fastapi==0.109.0 \
    uvicorn==0.27.0 \
    pyjwt==2.8.0 \
    pydantic[email]==2.5.3 \
    redis==5.0.1

# Create auth server
RUN cat > /app/server.py << 'ENDOFFILE'
#!/usr/bin/env python3
"""
Backend Auth Server for Knowledge Platform
STORY-024: FastAPI server with JWT authentication endpoints
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import jwt
import redis
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

# JWT Configuration
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "knowledge-service-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Redis Connection
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", None)

try:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD if REDIS_PASSWORD else None,
        db=0,
        decode_responses=True
    )
    redis_client.ping()
    print(f"[AUTH] Redis connected: {REDIS_HOST}:{REDIS_PORT}")
except Exception as e:
    print(f"[AUTH] Redis connection failed: {e}")
    redis_client = None

# Mock user database
MOCK_USERS: Dict[str, Dict[str, Any]] = {
    "test@example.com": {
        "id": "user-001",
        "email": "test@example.com",
        "password": "password123",
        "name": "Test User",
        "firstName": "Test",
        "lastName": "User",
        "role": "user",
        "roles": ["USER"],
        "department": "Development",
        "employeeId": "EMP001",
        "created_at": "2026-01-01T00:00:00Z",
    },
    "admin@example.com": {
        "id": "user-002",
        "email": "admin@example.com",
        "password": "admin123!",
        "name": "Admin User",
        "firstName": "Admin",
        "lastName": "User",
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
        "name": "Regular User",
        "firstName": "Regular",
        "lastName": "User",
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
        "name": "Knowledge Manager",
        "firstName": "Knowledge",
        "lastName": "Manager",
        "role": "manager",
        "roles": ["KNOWLEDGE_MANAGER", "USER"],
        "department": "Knowledge Management",
        "employeeId": "EMP004",
        "created_at": "2026-01-01T00:00:00Z",
    },
}

# Refresh token storage prefixes
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

    # Store in Redis with TTL if available
    if redis_client:
        try:
            redis_client.setex(
                f"{REFRESH_TOKEN_PREFIX}{user_id}",
                REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
                token
            )
        except Exception as e:
            print(f"[AUTH] Redis store failed: {e}")

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
app = FastAPI(title="Backend Auth Service", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"service": "backend", "status": "running", "version": "auth-1.0"}


@app.get("/actuator/health")
async def health():
    redis_status = "UP" if redis_client else "DOWN"
    return {
        "status": "UP",
        "components": {
            "db": {"status": "UP"},
            "diskSpace": {"status": "UP"},
            "ping": {"status": "UP"},
            "redis": {"status": redis_status}
        }
    }


@app.get("/actuator/info")
async def info():
    return {
        "app": {
            "name": "backend",
            "version": "auth-1.0",
            "description": "Backend Auth Service"
        }
    }


@app.get("/health")
async def health_simple():
    return {"status": "healthy", "service": "backend-auth"}


@app.post("/api/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Login endpoint"""
    print(f"[AUTH] Login attempt: {request.email}")

    user = MOCK_USERS.get(request.email.lower())
    if user is None:
        print(f"[AUTH] User not found: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if user["password"] != request.password:
        print(f"[AUTH] Invalid password for: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token = create_access_token(user["id"], user["email"], user["role"])
    refresh_token = create_refresh_token(user["id"])

    # Store session info in Redis if available
    if redis_client:
        try:
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
        except Exception as e:
            print(f"[AUTH] Session store failed: {e}")

    print(f"[AUTH] Login successful: {request.email}")

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
    return {"message": "Logout successful", "success": True}


@app.post("/api/auth/refresh")
async def refresh_token_endpoint(request: RefreshRequest):
    """Refresh token endpoint"""
    payload = decode_token(request.refreshToken)

    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id = payload.get("sub")

    # Find user
    user = None
    for u in MOCK_USERS.values():
        if u["id"] == user_id:
            user = u
            break

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    access_token = create_access_token(user["id"], user["email"], user["role"])
    new_refresh_token = create_refresh_token(user["id"])

    return {
        "accessToken": access_token,
        "refreshToken": new_refresh_token,
        "expiresIn": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@app.get("/api/auth/me")
async def get_current_user():
    """Get current user - requires valid JWT in header"""
    # For now, return a mock response
    # In production, this would validate the JWT from Authorization header
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
    )


if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 60)
    print("Backend Auth Service Starting...")
    print("=" * 60)
    print("\nTest Accounts:")
    for email, user in MOCK_USERS.items():
        print(f"  - {email} / {user['password']} ({user['role']})")
    print("\n" + "=" * 60 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8081)
ENDOFFILE

RUN chmod +x /app/server.py && chown -R appuser:appgroup /app

USER appuser

EXPOSE 8081

# Health check via Spring Actuator endpoint
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
    CMD wget -q --spider http://localhost:8081/actuator/health || exit 1

CMD ["python", "/app/server.py"]
