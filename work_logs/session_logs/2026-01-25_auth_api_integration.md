# Session Log: Auth API Integration Test

**Date**: 2026-01-25
**Author**: QA Engineer
**Session Duration**: ~2 hours
**Status**: Completed Successfully

---

## 1. Objective

로그인 기능의 실제 API 연동 테스트를 위한 독립 인증 서버 구축 및 Redis 세션 저장 검증

---

## 2. Background

### 2.1 기존 상태
- Mock 인증 (`VITE_USE_MOCK_AUTH=true`) 기반 개발 환경
- 백엔드 API 서버 없이 프론트엔드 개발 진행 중

### 2.2 필요성
- 실제 API 통신 검증 필요
- JWT 토큰 발급/검증 플로우 확인
- Redis 기반 세션 관리 테스트

---

## 3. Implementation Details

### 3.1 Auth Server 구축

**파일 위치**: `/mnt/d/Users/KTDS/Documents/06.과제/hybrid-rag-knowledge-ops/knowledge_service/auth_server.py`

**기술 스택**:
- FastAPI (Python)
- PyJWT (JWT 토큰 처리)
- Redis (세션/토큰 저장)
- Pydantic (데이터 검증)

**주요 기능**:
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | 서버 상태 확인 |
| `/api/auth/login` | POST | 로그인 및 토큰 발급 |
| `/api/auth/logout` | POST | 로그아웃 |
| `/api/auth/refresh` | POST | 토큰 갱신 |

**Mock 사용자 계정**:
| Email | Password | Role |
|-------|----------|------|
| test@example.com | password123 | user |
| admin@example.com | admin123! | admin |
| user@example.com | user123! | user |
| manager@example.com | manager123! | manager |

### 3.2 환경 설정 변경

**파일**: `/mnt/d/Users/KTDS/Documents/06.과제/hybrid-rag-knowledge-ops/knowledge_service/frontend/.env.development`

```env
# Before
VITE_USE_MOCK_AUTH=true

# After
VITE_USE_MOCK_AUTH=false
VITE_API_BASE_URL=http://localhost:8002
```

### 3.3 Vite Proxy 설정

**파일**: `/mnt/d/Users/KTDS/Documents/06.과제/hybrid-rag-knowledge-ops/knowledge_service/frontend/vite.config.ts`

```typescript
server: {
  port: 3000,
  proxy: {
    '/api': {
      target: 'http://localhost:8002',
      changeOrigin: true,
    },
  },
},
```

**프록시 역할**:
- 프론트엔드 (localhost:3000) 요청 -> Auth Server (localhost:8002) 전달
- CORS 문제 해결
- 개발/운영 환경 일관성 유지

### 3.4 Redis 연동

**저장 데이터**:
| Key Pattern | Data | TTL |
|-------------|------|-----|
| `auth:session:{user_id}` | 세션 정보 (JSON) | 30분 |
| `auth:refresh_token:{user_id}` | 리프레시 토큰 | 7일 |

**세션 데이터 구조**:
```json
{
  "user_id": "user-001",
  "email": "test@example.com",
  "role": "user",
  "login_at": "2026-01-25T10:30:00.000000"
}
```

---

## 4. Test Execution

### 4.1 사전 조건
1. Redis 서버 실행 (localhost:6379)
2. Auth Server 실행 (localhost:8002)
3. Frontend Dev Server 실행 (localhost:3000)

### 4.2 테스트 시나리오

**Scenario 1: 정상 로그인**
- Input: `test@example.com / password123`
- Expected: 로그인 성공, 토큰 발급, Redis 세션 저장
- Result: PASS

**Scenario 2: 잘못된 비밀번호**
- Input: `test@example.com / wrongpassword`
- Expected: 401 Unauthorized
- Result: PASS

**Scenario 3: 존재하지 않는 사용자**
- Input: `notexist@example.com / password123`
- Expected: 401 Unauthorized
- Result: PASS

### 4.3 Redis 데이터 검증

```bash
# 세션 확인
redis-cli GET auth:session:user-001
# Result: {"user_id": "user-001", "email": "test@example.com", ...}

# 리프레시 토큰 확인
redis-cli GET auth:refresh_token:user-001
# Result: eyJhbGciOiJIUzI1NiIs...

# TTL 확인
redis-cli TTL auth:session:user-001
# Result: 1799 (약 30분)
```

---

## 5. Issues & Resolutions

### 5.1 CORS 에러
**문제**: 프론트엔드에서 Auth Server로 직접 요청 시 CORS 에러 발생

**해결**:
1. Auth Server에 CORS 미들웨어 추가
2. Vite Proxy 설정으로 우회

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 5.2 Redis 연결 실패
**문제**: Redis 서버 미실행 시 Auth Server 시작 실패

**해결**: Docker Compose로 Redis 컨테이너 실행
```bash
docker-compose up -d redis
```

---

## 6. Architecture

```
+------------------+       +------------------+       +------------------+
|   Frontend       |       |   Auth Server    |       |     Redis        |
|   (React)        |       |   (FastAPI)      |       |                  |
|   localhost:3000 | ----> |   localhost:8002 | ----> |   localhost:6379 |
+------------------+       +------------------+       +------------------+
         |                          |
         |                          |
         v                          v
    Vite Proxy               JWT + Session
    /api -> 8002             Management
```

---

## 7. Files Modified

| File | Change |
|------|--------|
| `auth_server.py` | New - 독립 인증 서버 |
| `frontend/.env.development` | Modified - Mock 비활성화 |
| `frontend/vite.config.ts` | Modified - Proxy 설정 추가 |

---

## 8. Lessons Learned

1. **독립 서버의 장점**: 백엔드 개발 지연 시에도 프론트엔드 테스트 가능
2. **Proxy 설정 중요성**: CORS 문제를 우회하고 환경 일관성 유지
3. **Redis 세션 관리**: 서버 재시작 시에도 세션 유지 가능
4. **Mock Data 설계**: 다양한 역할(admin, manager, user) 테스트 가능하도록 설계

---

## 9. Next Steps

- [ ] 토큰 갱신 플로우 E2E 테스트
- [ ] 로그아웃 후 Redis 세션 삭제 검증
- [ ] 만료된 토큰 처리 테스트
- [ ] Keycloak 연동 전환 준비

---

## 10. Related Documents

- [Login Redis Integration Test](../knowledge_service/docs/04_testing/test_cases/auth/login_redis_integration_test.md)
- [Auth Server Source](../knowledge_service/auth_server.py)
- [Vite Config](../knowledge_service/frontend/vite.config.ts)
