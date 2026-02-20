# Backend API Docker Deployment Task

**Date**: 2026-01-25
**Assigned By**: PM Agent
**Assigned To**: Infra Agent (or Backend Agent)
**Priority**: P0 (High)
**Status**: Pending

---

## 1. Task Summary

STORY-024 (Direct Login API)가 개발 및 테스트 완료되었습니다.
현재 `kp-backend` 컨테이너는 Stub 서버로 운영 중이며, 새로 개발된 Auth API를 배포해야 합니다.

---

## 2. Current State

### 2.1 kp-backend Container (Stub)
- Image: SpringBoot stub server
- Port: 8080 (internal)
- Status: Running (stub mode)

### 2.2 Developed Auth API
- Location: `knowledge_service/backend/` (SpringBoot)
- Alternative: `knowledge_service/auth_server.py` (FastAPI - 테스트용)

---

## 3. Deployment Options

### Option A: SpringBoot Backend (Recommended)

1. Build SpringBoot application
2. Update Dockerfile in `knowledge_service/backend/`
3. Rebuild kp-backend image
4. Restart container

```bash
# Build
cd knowledge_service/backend
./gradlew build -x test

# Docker rebuild
docker-compose build kp-backend
docker-compose up -d kp-backend
```

### Option B: FastAPI Auth Server (Quick Deploy)

1. Use existing `auth_server.py` as standalone service
2. Add new container `kp-auth` in docker-compose
3. Update frontend proxy configuration

```yaml
# docker-compose.yml (추가)
kp-auth:
  build:
    context: ./knowledge_service
    dockerfile: Dockerfile.auth
  ports:
    - "8002:8002"
  environment:
    - REDIS_URL=redis://kp-redis:6379
    - JWT_SECRET=${JWT_SECRET}
  depends_on:
    - kp-redis
```

---

## 4. Required Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| JWT_SECRET | JWT signing key | Yes |
| REDIS_URL | Redis connection string | Yes |
| DB_URL | PostgreSQL connection (if needed) | Optional |
| DB_USER | Database user | Optional |
| DB_PASSWORD | Database password | Optional |

---

## 5. Verification Steps

After deployment, verify:

1. **Health Check**
   ```bash
   curl http://localhost:8080/health
   # or http://localhost:8002/health for FastAPI
   ```

2. **Login API Test**
   ```bash
   curl -X POST http://localhost:8080/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"test@example.com","password":"password123"}'
   ```

3. **Redis Session Check**
   ```bash
   docker exec kp-redis redis-cli KEYS "auth:*"
   ```

---

## 6. Timeline

| Step | Estimated Time |
|------|----------------|
| Dockerfile preparation | 30 min |
| Image build | 15 min |
| Container restart | 5 min |
| Verification | 15 min |
| **Total** | **~1 hour** |

---

## 7. Slack Notification (Required)

Infra Agent must send:

```bash
# Task start
./scripts/send_slack.sh proj-hrkp-dev Infra "작업 시작: kp-backend Auth API 배포"

# Task complete
./scripts/send_slack.sh proj-hrkp-dev Infra "작업 완료: kp-backend Auth API 배포 완료, Health Check Pass"
```

---

## 8. Related Documents

- [E2E Test Final Report](./2026-01-25_e2e_test_final_report.md)
- [Auth Server Source](../../knowledge_service/auth_server.py)
- [Docker Compose](../../infrastructure/docker-compose.yml)
- [Backend Dockerfile](../../knowledge_service/backend/Dockerfile)

---

**Issued By**: PM Agent
**Date**: 2026-01-25
