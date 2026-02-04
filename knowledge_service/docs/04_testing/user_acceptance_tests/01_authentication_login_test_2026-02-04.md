# UAT-01: Authentication & Login Test Report

**Test Date**: 2026-02-04
**Tester**: User
**Environment**: Development (Docker Compose)
**Version**: Sprint 07 (Phase 5 Deployment Preparation)

---

## 1. Test Summary

| Item | Value |
|------|-------|
| **Test ID** | UAT-01 |
| **Test Name** | Authentication & Login Flow Test |
| **Test Type** | User Acceptance Test (UAT) |
| **Priority** | P0 - Critical |
| **Status** | **PASS** |
| **Test Duration** | ~2 hours (including debugging) |

---

## 2. Test Objectives

1. Verify user login functionality via Direct Login (non-Keycloak)
2. Validate JWT token generation and validation
3. Confirm dashboard access after successful authentication
4. End-to-end authentication flow from frontend to backend

---

## 3. Test Environment

### 3.1 Infrastructure

| Component | Container | Status |
|-----------|-----------|--------|
| Nginx (Reverse Proxy) | kp-nginx | Running |
| API Gateway | kp-api-gateway | Running |
| Backend | kp-backend | Running |
| Frontend | kp-frontend | Running |
| PostgreSQL | kp-postgresql | Running |
| Redis | kp-redis | Running |
| Keycloak | kp-keycloak | Running |

### 3.2 Test Credentials

| Account | Email | Password | Roles |
|---------|-------|----------|-------|
| Admin | admin@example.com | admin1234 | ADMIN, USER |

### 3.3 Access URL

- **Frontend**: http://localhost
- **API Gateway**: http://localhost/api/v1

---

## 4. Test Scenarios & Results

### 4.1 Scenario: User Login via Frontend

| Step | Action | Expected Result | Actual Result | Status |
|------|--------|-----------------|---------------|--------|
| 1 | Navigate to http://localhost | Login page displayed | Login page displayed | PASS |
| 2 | Enter email: admin@example.com | Email input accepted | Email input accepted | PASS |
| 3 | Enter password: admin1234 | Password input accepted (masked) | Password input accepted | PASS |
| 4 | Click "Login" button | Login request sent | Login request sent | PASS |
| 5 | Wait for response | Redirect to Dashboard | Redirect to Dashboard | **PASS** |
| 6 | Verify Dashboard loads | Dashboard stats displayed | Dashboard displayed | PASS |

### 4.2 API-Level Verification

| API Endpoint | Method | Request | Response Code | Status |
|--------------|--------|---------|---------------|--------|
| /api/v1/auth/login | POST | {email, password} | 200 OK | PASS |
| /api/v1/dashboard/stats | GET | Bearer Token | 200 OK | PASS |

---

## 5. Issues Found & Resolutions

### 5.1 Issue #1: Login Success but No Screen Transition

**Symptom**:
- Login API returns 200 with valid JWT token
- Browser localStorage stores token
- Dashboard API returns 401 Unauthorized
- Frontend clears localStorage and redirects back to login

**Root Cause Analysis**:
1. Gateway's `JwtAuthenticationFilter` validates HS256 token correctly
2. After validation, filter **strips Authorization header** to prevent OAuth2 re-validation
3. Backend receives request **without** authentication information
4. Backend returns 401, triggering frontend logout

**Resolution**:
Modified `JwtAuthenticationFilter` to forward user information via custom headers:

```java
// Before (problematic)
ServerHttpRequest mutatedRequest = request.mutate()
    .headers(headers -> headers.remove(HttpHeaders.AUTHORIZATION))
    .build();

// After (fixed)
ServerHttpRequest mutatedRequest = request.mutate()
    .headers(headers -> {
        headers.remove(HttpHeaders.AUTHORIZATION);
        headers.set("X-Auth-User-Id", userId);
        headers.set("X-Auth-User-Email", email);
        headers.set("X-Auth-User-Name", username);
        headers.set("X-Auth-User-Roles", rolesString);
        headers.set("X-Auth-Method", "direct");
    })
    .build();
```

**Files Modified**:
- `knowledge_service/gateway/src/main/java/com/knowledge/gateway/filter/JwtAuthenticationFilter.java`

---

### 5.2 Issue #2: Backend Not Reading Gateway Headers

**Symptom**:
- Gateway correctly forwards X-Auth-* headers
- Backend still returns 401

**Root Cause**:
Backend's `SecurityConfig` only checked for Authorization header, not X-Auth-* headers

**Resolution**:
Modified `SecurityConfig.jwtAuthenticationFilter()` to check X-Auth-* headers first:

```java
// Check for Gateway-forwarded authentication (X-Auth-* headers)
String gatewayUserId = headers.getFirst("X-Auth-User-Id");
String gatewayEmail = headers.getFirst("X-Auth-User-Email");
String authMethod = headers.getFirst("X-Auth-Method");

if (gatewayUserId != null && gatewayEmail != null && "direct".equals(authMethod)) {
    // Gateway has already validated the token, trust the headers
    // Create authentication from headers...
}
```

**Files Modified**:
- `knowledge_service/backend/src/main/java/com/knowledge/backend/config/SecurityConfig.java`

---

### 5.3 Issue #3: Missing Database Tables

**Symptom**:
- Authentication passes (200 OK)
- Dashboard API returns 500 Internal Server Error
- Log: `relation "documents" does not exist`

**Root Cause**:
- Backend entities expect `documents`, `chunks` tables
- Database has `knowledge_master`, `knowledge_chunks` tables (different schema)

**Resolution**:
Created missing tables to match Backend entity expectations:

```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    document_type VARCHAR(100),
    processing_status VARCHAR(50) DEFAULT 'pending',
    ...
);

CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id),
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    ...
);

CREATE TABLE search_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query TEXT NOT NULL,
    result_count INTEGER,
    ...
);
```

**Note**: This is a temporary fix. Long-term solution should align Backend entities with the actual database schema (`knowledge_master`, etc.).

---

## 6. Authentication Flow Diagram

```
┌─────────────┐    ┌─────────┐    ┌─────────────┐    ┌─────────┐    ┌────────────┐
│  Frontend   │───▶│  Nginx  │───▶│ API Gateway │───▶│ Backend │───▶│ PostgreSQL │
│  (React)    │    │         │    │             │    │         │    │            │
└─────────────┘    └─────────┘    └─────────────┘    └─────────┘    └────────────┘
      │                                  │                 │
      │ 1. POST /api/v1/auth/login      │                 │
      │ ─────────────────────────────────▶                 │
      │                                  │ 2. Forward      │
      │                                  │ ────────────────▶
      │                                  │                 │ 3. Validate
      │                                  │                 │    credentials
      │                                  │ 4. JWT Token    │◀───DB Query
      │                                  │◀────────────────│
      │ 5. Response {accessToken}        │                 │
      │◀─────────────────────────────────│                 │
      │                                  │                 │
      │ 6. GET /api/v1/dashboard/stats   │                 │
      │    Authorization: Bearer <JWT>   │                 │
      │ ─────────────────────────────────▶                 │
      │                                  │ 7. Validate HS256│
      │                                  │    Add X-Auth-*  │
      │                                  │    headers       │
      │                                  │ ────────────────▶│
      │                                  │                 │ 8. Read X-Auth-*
      │                                  │                 │    Create Auth
      │                                  │ 9. Dashboard data│
      │                                  │◀────────────────│
      │ 10. Response {stats}             │                 │
      │◀─────────────────────────────────│                 │
```

---

## 7. Test Evidence

### 7.1 Login API Response

```json
{
  "accessToken": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIyIiwiaXNzIjoia25vd2xlZGdlLXBsYXRmb3JtIiwiaWF0IjoxNzcwMTg1Njc2LCJleHAiOjE3NzAxODkyNzYsInVzZXJuYW1lIjoiYWRtaW51c2VyIiwicm9sZXMiOlsiQURNSU4iLCJVU0VSIl0sImVtYWlsIjoiYWRtaW5AZXhhbXBsZS5jb20iLCJ0eXBlIjoiYWNjZXNzIn0.nyboQql_hoG-lBMbaqRPndPgvc_2rGKkuXBahUTTgJ4",
  "refreshToken": "...",
  "user": {
    "id": 2,
    "email": "admin@example.com",
    "username": "adminuser",
    "roles": ["ADMIN", "USER"]
  }
}
```

### 7.2 Dashboard API Response (After Fix)

```json
{
  "totalDocuments": 3,
  "totalChunks": 1,
  "totalUsers": 1,
  "activeUsers": 1,
  "totalSearches": 1,
  "completedDocuments": 2,
  "pendingDocuments": 1,
  "failedDocuments": 0
}
```

### 7.3 Gateway Debug Logs (Token Validation)

```
DEBUG JwtAuthenticationFilter: HS256 token detected at /api/v1/dashboard/stats, validating with JwtTokenValidator
DEBUG JwtAuthenticationFilter: HS256 token validated - user: adminuser (id: 2), email: admin@example.com, roles: [ADMIN, USER]
DEBUG AuthorizationWebFilter: Authorization successful
INFO  LoggingFilter: Response: GET /api/v1/dashboard/stats - Status: 200 OK
```

---

## 8. Code Changes Summary

| File | Change Type | Description |
|------|-------------|-------------|
| `gateway/.../JwtAuthenticationFilter.java` | Modified | Add X-Auth-* headers for backend |
| `backend/.../SecurityConfig.java` | Modified | Read X-Auth-* headers for authentication |
| `docker-compose.yml` | Modified | Add DEBUG logging env vars for gateway |
| PostgreSQL | DDL | Create `documents`, `chunks`, `search_history` tables |

---

## 9. Recommendations

### 9.1 Short-term (Immediate)

1. **Database Schema Alignment**: Reconcile Backend entities with existing database schema
   - Option A: Update Backend entities to use `knowledge_master`
   - Option B: Migrate data from `knowledge_master` to `documents`

2. **Security Review**: Ensure X-Auth-* headers are only trusted from internal network
   - Add header validation to reject external requests with these headers

### 9.2 Long-term

1. **Token Relay Improvement**: Consider passing encrypted token claim info instead of plain headers
2. **Centralized Auth Service**: Implement dedicated auth service for token validation
3. **Audit Logging**: Log all authentication events for security audit trail

---

## 10. Conclusion

| Criteria | Result |
|----------|--------|
| **Login Functionality** | PASS |
| **Token Generation** | PASS |
| **Token Validation** | PASS |
| **Dashboard Access** | PASS |
| **Session Persistence** | PASS |

**Overall Test Result**: **PASS**

The authentication and login flow is now functioning correctly. Users can:
1. Access the login page
2. Enter credentials and submit
3. Receive valid JWT tokens
4. Access protected resources (Dashboard)
5. Maintain session across page refreshes

---

## 11. Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Tester | User | 2026-02-04 | Approved |
| Developer | Claude Code | 2026-02-04 | Implemented |

---

*Document Generated: 2026-02-04*
*Test Environment: Development (Docker Compose)*
*Version: v1.0*
