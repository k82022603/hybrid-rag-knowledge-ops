# Login Redis Integration Test

**Test ID**: TC-AUTH-001
**Version**: 1.0
**Date**: 2026-01-25
**Author**: QA Engineer
**Status**: Approved

---

## 1. Test Overview

| Item | Description |
|------|-------------|
| **Test Name** | Login with Redis Session Storage |
| **Test Type** | Integration Test |
| **Priority** | High |
| **Module** | Authentication |
| **Components** | Frontend, Auth Server, Redis |

---

## 2. Test Objective

로그인 기능이 올바르게 동작하며, JWT 토큰과 세션 정보가 Redis에 정상적으로 저장되는지 검증한다.

---

## 3. Prerequisites

### 3.1 Environment Setup

| Component | Version | Port | Status Check |
|-----------|---------|------|--------------|
| Redis | 7.x | 6379 | `redis-cli ping` -> PONG |
| Auth Server | 1.0.0 | 8002 | `curl http://localhost:8002/health` |
| Frontend | 0.1.0 | 3000 | `curl http://localhost:3000` |

### 3.2 Configuration Files

**Frontend Environment** (`.env.development`):
```env
VITE_API_BASE_URL=http://localhost:8002
VITE_USE_MOCK_AUTH=false
```

**Vite Proxy** (`vite.config.ts`):
```typescript
proxy: {
  '/api': {
    target: 'http://localhost:8002',
    changeOrigin: true,
  },
},
```

### 3.3 Start Sequence

```bash
# 1. Redis 시작
docker-compose up -d redis

# 2. Auth Server 시작
cd knowledge_service
python auth_server.py

# 3. Frontend Dev Server 시작
cd knowledge_service/frontend
npm run dev
```

---

## 4. Test Data

### 4.1 Valid Test Accounts

| Email | Password | Role | Expected Result |
|-------|----------|------|-----------------|
| test@example.com | password123 | user | Login Success |
| admin@example.com | admin123! | admin | Login Success |
| user@example.com | user123! | user | Login Success |
| manager@example.com | manager123! | manager | Login Success |

### 4.2 Invalid Test Data

| Email | Password | Expected Result |
|-------|----------|-----------------|
| test@example.com | wrongpassword | 401 Unauthorized |
| notexist@example.com | password123 | 401 Unauthorized |
| (empty) | password123 | 400 Bad Request |
| test@example.com | (empty) | 400 Bad Request |

---

## 5. Test Cases

### TC-AUTH-001-01: Successful Login

**Preconditions**:
- All services running
- Redis empty or cleared

**Test Steps**:
| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to `http://localhost:3000/login` | Login page displayed |
| 2 | Enter email: `test@example.com` | Email field populated |
| 3 | Enter password: `password123` | Password field populated (masked) |
| 4 | Click "Login" button | Loading state shown |
| 5 | Wait for response | Redirect to dashboard |

**Expected Response**:
```json
{
  "accessToken": "eyJhbGciOiJIUzI1NiIs...",
  "refreshToken": "eyJhbGciOiJIUzI1NiIs...",
  "expiresIn": 1800,
  "user": {
    "id": "user-001",
    "email": "test@example.com",
    "name": "테스트 사용자",
    "roles": ["USER"]
  }
}
```

**Redis Verification**:
```bash
# Session stored
redis-cli GET auth:session:user-001
# Expected: {"user_id": "user-001", "email": "test@example.com", ...}

# Refresh token stored
redis-cli EXISTS auth:refresh_token:user-001
# Expected: 1

# Session TTL (30 minutes)
redis-cli TTL auth:session:user-001
# Expected: ~1800 seconds
```

**Pass Criteria**:
- [ ] HTTP 200 response received
- [ ] Access token is valid JWT
- [ ] Refresh token is valid JWT
- [ ] User data matches test account
- [ ] Session stored in Redis
- [ ] Refresh token stored in Redis
- [ ] Session TTL is approximately 30 minutes
- [ ] Redirect to dashboard successful

---

### TC-AUTH-001-02: Invalid Password

**Preconditions**:
- All services running

**Test Steps**:
| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to login page | Login page displayed |
| 2 | Enter email: `test@example.com` | Email field populated |
| 3 | Enter password: `wrongpassword` | Password field populated |
| 4 | Click "Login" button | Loading state shown |
| 5 | Wait for response | Error message displayed |

**Expected Response**:
```json
{
  "detail": "이메일 또는 비밀번호가 올바르지 않습니다"
}
```

**Pass Criteria**:
- [ ] HTTP 401 response received
- [ ] Error message displayed to user
- [ ] No tokens issued
- [ ] No session created in Redis
- [ ] User remains on login page

---

### TC-AUTH-001-03: Non-existent User

**Preconditions**:
- All services running

**Test Steps**:
| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to login page | Login page displayed |
| 2 | Enter email: `notexist@example.com` | Email field populated |
| 3 | Enter password: `password123` | Password field populated |
| 4 | Click "Login" button | Loading state shown |
| 5 | Wait for response | Error message displayed |

**Pass Criteria**:
- [ ] HTTP 401 response received
- [ ] Same error message as invalid password (security)
- [ ] No tokens issued
- [ ] No session created in Redis

---

### TC-AUTH-001-04: Redis Session Expiry

**Preconditions**:
- Successful login completed
- Session exists in Redis

**Test Steps**:
| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Login with valid credentials | Session created |
| 2 | Wait 30 minutes (or set shorter TTL for test) | Session expires |
| 3 | Verify Redis session | Session deleted |

**Verification**:
```bash
# After expiry
redis-cli GET auth:session:user-001
# Expected: (nil)
```

**Pass Criteria**:
- [ ] Session automatically deleted after TTL
- [ ] User required to re-authenticate

---

### TC-AUTH-001-05: Refresh Token Flow

**Preconditions**:
- Valid refresh token exists in Redis

**Test Steps**:
| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Call `/api/auth/refresh` with valid refresh token | New tokens issued |
| 2 | Verify new access token | Token is valid JWT |
| 3 | Verify Redis | Old token replaced with new |

**API Request**:
```bash
curl -X POST http://localhost:8002/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refreshToken": "eyJhbGciOiJIUzI1NiIs..."}'
```

**Pass Criteria**:
- [ ] HTTP 200 response received
- [ ] New access token issued
- [ ] New refresh token issued
- [ ] Old refresh token invalidated

---

## 6. API Test Commands

### 6.1 cURL Commands

```bash
# Health Check
curl http://localhost:8002/health

# Login
curl -X POST http://localhost:8002/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123", "rememberMe": false}'

# Refresh Token
curl -X POST http://localhost:8002/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refreshToken": "<refresh_token_here>"}'

# Logout
curl -X POST http://localhost:8002/api/auth/logout
```

### 6.2 Redis Verification Commands

```bash
# Check all auth keys
redis-cli KEYS "auth:*"

# Get session data
redis-cli GET auth:session:user-001

# Get refresh token
redis-cli GET auth:refresh_token:user-001

# Check TTL
redis-cli TTL auth:session:user-001
redis-cli TTL auth:refresh_token:user-001

# Clear all auth data (test cleanup)
redis-cli KEYS "auth:*" | xargs redis-cli DEL
```

---

## 7. Expected Results Summary

| Test Case | Expected HTTP | Redis Session | Redis Token | Overall |
|-----------|---------------|---------------|-------------|---------|
| TC-001-01 | 200 | Created | Created | PASS |
| TC-001-02 | 401 | Not Created | Not Created | PASS |
| TC-001-03 | 401 | Not Created | Not Created | PASS |
| TC-001-04 | N/A | Expired | N/A | PASS |
| TC-001-05 | 200 | Updated | Rotated | PASS |

---

## 8. Test Execution Log

| Date | Tester | Test Case | Result | Notes |
|------|--------|-----------|--------|-------|
| 2026-01-25 | QA Engineer | TC-001-01 | PASS | All verifications passed |
| 2026-01-25 | QA Engineer | TC-001-02 | PASS | Error handling correct |
| 2026-01-25 | QA Engineer | TC-001-03 | PASS | Security requirement met |
| 2026-01-25 | QA Engineer | TC-001-04 | PASS | TTL working as expected |
| 2026-01-25 | QA Engineer | TC-001-05 | PASS | Token rotation successful |

---

## 9. Related Files

| File | Path | Purpose |
|------|------|---------|
| Auth Server | `/mnt/d/Users/KTDS/Documents/06.과제/hybrid-rag-knowledge-ops/knowledge_service/auth_server.py` | Backend authentication |
| Frontend Env | `/mnt/d/Users/KTDS/Documents/06.과제/hybrid-rag-knowledge-ops/knowledge_service/frontend/.env.development` | Environment config |
| Vite Config | `/mnt/d/Users/KTDS/Documents/06.과제/hybrid-rag-knowledge-ops/knowledge_service/frontend/vite.config.ts` | Proxy settings |
| Session Log | `/mnt/d/Users/KTDS/Documents/06.과제/hybrid-rag-knowledge-ops/work_logs/session_logs/2026-01-25_auth_api_integration.md` | Development log |

---

## 10. Appendix

### A. JWT Token Structure

**Access Token Payload**:
```json
{
  "sub": "user-001",
  "email": "test@example.com",
  "role": "user",
  "exp": 1737806400,
  "iat": 1737804600,
  "type": "access"
}
```

**Refresh Token Payload**:
```json
{
  "sub": "user-001",
  "exp": 1738409400,
  "iat": 1737804600,
  "type": "refresh",
  "jti": "random-token-id-32-chars"
}
```

### B. Redis Key Schema

| Key Pattern | Description | TTL |
|-------------|-------------|-----|
| `auth:session:{user_id}` | User session data | 30 min (1800s) |
| `auth:refresh_token:{user_id}` | Refresh token | 7 days (604800s) |

### C. Error Codes

| HTTP Code | Description | User Message |
|-----------|-------------|--------------|
| 200 | Success | N/A |
| 400 | Bad Request | 입력값을 확인해주세요 |
| 401 | Unauthorized | 이메일 또는 비밀번호가 올바르지 않습니다 |
| 500 | Server Error | 서버 오류가 발생했습니다 |
