# Keycloak Configuration Guide

Keycloak OAuth 2.0 / OIDC 설정 가이드

**Version**: 1.0
**Last Updated**: 2026-01-30
**Author**: Infra Agent

---

## 개요

이 문서는 Hybrid RAG Knowledge Platform의 Keycloak 인증 시스템 설정 방법을 설명합니다.

### 아키텍처

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Keycloak  │◀────│   Backend   │
│  (React)    │     │  (OAuth2)   │     │ (SpringBoot)│
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    ▼             ▼
              ┌──────────┐  ┌──────────┐
              │ Keycloak │  │   Realm  │
              │    DB    │  │  Export  │
              └──────────┘  └──────────┘
```

---

## 파일 구조

```
infrastructure/docker/keycloak/
├── realm-export.json    # Realm 설정 (자동 import)
└── README.md            # 이 문서
```

---

## Realm 설정

### 기본 정보

| 항목 | 값 |
|------|-----|
| **Realm Name** | `hybrid-rag` |
| **Display Name** | Hybrid RAG Knowledge Platform |
| **SSL Required** | external |
| **Access Token Lifespan** | 3600초 (1시간) |
| **SSO Session Idle Timeout** | 1800초 (30분) |

### Clients

| Client ID | Type | 용도 |
|-----------|------|------|
| `frontend` | Public | React SPA (PKCE) |
| `knowledge-frontend` | Public | Frontend alias |
| `backend` | Confidential | SpringBoot Backend |
| `knowledge-backend` | Public | Backend alias |
| `ai-service` | Confidential | FastAPI AI Service |

### Roles

| Role | 설명 | 권한 |
|------|------|------|
| `admin` | 관리자 | 전체 접근 권한 |
| `user` | 일반 사용자 | 문서 읽기/쓰기, 검색 |
| `viewer` | 읽기 전용 | 문서 읽기만 가능 |

### 테스트 계정

| Username | Password | Role | 용도 |
|----------|----------|------|------|
| `test-user` | `test-password` | user | E2E 테스트 |
| `testuser` | `testpass` | user | 일반 테스트 |
| `test` | `password123` | user | 빠른 테스트 |
| `admin` | `admin123` | admin | 관리자 테스트 |
| `test-admin` | `admin123` | admin | 관리자 E2E 테스트 |

---

## Docker Compose 설정

### Keycloak 서비스

```yaml
keycloak:
  image: quay.io/keycloak/keycloak:23.0
  container_name: kp-keycloak
  command: start-dev --import-realm
  ports:
    - "${KEYCLOAK_PORT:-8180}:8080"
  environment:
    - KC_DB=postgres
    - KC_DB_URL=jdbc:postgresql://keycloak-db:5432/keycloak
    - KC_DB_USERNAME=${KEYCLOAK_DB_USER:-keycloak}
    - KC_DB_PASSWORD=${KEYCLOAK_DB_PASSWORD}
    - KEYCLOAK_ADMIN=${KEYCLOAK_ADMIN:-admin}
    - KEYCLOAK_ADMIN_PASSWORD=${KEYCLOAK_ADMIN_PASSWORD}
  volumes:
    - ./keycloak/realm-export.json:/opt/keycloak/data/import/realm-export.json:ro
```

### 환경변수

```env
# .env
KEYCLOAK_PORT=8180
KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=<secure-password>
KEYCLOAK_DB_USER=keycloak
KEYCLOAK_DB_PASSWORD=<secure-password>
```

---

## Frontend 연동

### 환경변수 설정

```env
# Frontend .env
VITE_KEYCLOAK_URL=http://localhost:8180
VITE_KEYCLOAK_REALM=hybrid-rag
VITE_KEYCLOAK_CLIENT_ID=knowledge-frontend
```

### Keycloak 초기화

```typescript
import Keycloak from 'keycloak-js';

const keycloak = new Keycloak({
  url: import.meta.env.VITE_KEYCLOAK_URL,
  realm: import.meta.env.VITE_KEYCLOAK_REALM,
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID,
});

// 초기화
await keycloak.init({
  onLoad: 'check-sso',
  pkceMethod: 'S256',
  checkLoginIframe: false,
});
```

---

## Backend 연동 (SpringBoot)

### application.yml

```yaml
spring:
  security:
    oauth2:
      resourceserver:
        jwt:
          issuer-uri: http://localhost:8180/realms/hybrid-rag
          jwk-set-uri: http://localhost:8180/realms/hybrid-rag/protocol/openid-connect/certs
```

### Client Credentials (Service-to-Service)

```yaml
keycloak:
  auth-server-url: http://localhost:8180
  realm: hybrid-rag
  resource: backend
  credentials:
    secret: ${BACKEND_CLIENT_SECRET:backend-secret-dev}
```

---

## AI Service 연동 (FastAPI)

### 환경변수

```env
KEYCLOAK_URL=http://localhost:8180
KEYCLOAK_REALM=hybrid-rag
KEYCLOAK_CLIENT_ID=ai-service
KEYCLOAK_CLIENT_SECRET=<secret>
```

### 토큰 검증

```python
from jose import jwt
import httpx

async def verify_token(token: str):
    jwks_url = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/certs"
    async with httpx.AsyncClient() as client:
        response = await client.get(jwks_url)
        jwks = response.json()

    return jwt.decode(token, jwks, algorithms=["RS256"])
```

---

## 관리 작업

### Admin Console 접속

```
URL: http://localhost:8180/admin/
Username: admin
Password: (KEYCLOAK_ADMIN_PASSWORD)
```

### Realm Export

기존 realm 설정을 export하려면:

```bash
# Docker 컨테이너 접속
docker exec -it kp-keycloak /bin/bash

# Realm export (Container 내부)
/opt/keycloak/bin/kc.sh export \
  --dir /tmp/export \
  --realm hybrid-rag \
  --users realm_file

# 호스트로 복사
docker cp kp-keycloak:/tmp/export/hybrid-rag-realm.json ./realm-export-new.json
```

### Realm Import

새로운 realm 설정을 import하려면:

```bash
# 1. realm-export.json 파일 수정

# 2. Keycloak 재시작
docker compose restart keycloak

# 또는 수동 import
docker exec -it kp-keycloak /opt/keycloak/bin/kc.sh import \
  --file /opt/keycloak/data/import/realm-export.json \
  --override true
```

### 사용자 추가

```bash
# Admin API로 사용자 생성
curl -X POST "http://localhost:8180/admin/realms/hybrid-rag/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "enabled": true,
    "credentials": [{
      "type": "password",
      "value": "password123",
      "temporary": false
    }]
  }'
```

---

## 문제 해결

### 1. Realm을 찾을 수 없음 (404)

**증상**: `/realms/hybrid-rag/.well-known/openid-configuration` 접속 시 404

**원인**:
- realm-export.json이 import되지 않음
- 볼륨 마운트 경로 오류

**해결**:
```bash
# 마운트 확인
docker inspect kp-keycloak | grep -A5 Mounts

# 올바른 경로: /opt/keycloak/data/import/realm-export.json
```

### 2. 401 Unauthorized (토큰 인증 실패)

**증상**: API 호출 시 401 오류

**원인**:
- 토큰 만료
- 잘못된 realm/client 설정
- JWT 서명 검증 실패

**해결**:
```bash
# 토큰 디코딩으로 확인
echo $TOKEN | cut -d'.' -f2 | base64 -d | jq

# issuer, audience 확인
```

### 3. 로그인 후 리다이렉트 실패

**증상**: 로그인 성공 후 "Invalid redirect_uri" 오류

**원인**: realm-export.json의 redirectUris 설정 누락

**해결**:
```json
// realm-export.json에 추가
"redirectUris": [
  "http://localhost/*",
  "http://localhost:3000/*"
],
"webOrigins": [
  "http://localhost",
  "http://localhost:3000"
]
```

### 4. Password Grant 실패

**증상**: `grant_type=password`로 토큰 요청 시 실패

**원인**:
- `directAccessGrantsEnabled: false` 설정
- Public 클라이언트인데 Confidential로 요청

**해결**:
```json
// realm-export.json에서 확인
"directAccessGrantsEnabled": true,
"publicClient": true  // password grant에 secret 불필요
```

---

## 보안 권장사항

### Production 환경

1. **SSL/TLS 활성화**
   ```yaml
   environment:
     - KC_HOSTNAME=auth.your-domain.com
     - KC_HTTPS_CERTIFICATE_FILE=/certs/tls.crt
     - KC_HTTPS_CERTIFICATE_KEY_FILE=/certs/tls.key
   ```

2. **start-dev → start 변경**
   ```yaml
   command: start --optimized
   ```

3. **관리자 비밀번호 강화**
   - 최소 16자 이상
   - 특수문자 포함

4. **Brute Force 보호 활성화**
   ```json
   "bruteForceProtected": true,
   "permanentLockout": false,
   "maxFailureWaitSeconds": 900,
   "failureFactor": 5
   ```

5. **불필요한 grant type 비활성화**
   - Production에서 password grant 비활성화 권장

---

## 참고 자료

- [Keycloak 공식 문서](https://www.keycloak.org/documentation)
- [Keycloak Docker 이미지](https://quay.io/repository/keycloak/keycloak)
- [Keycloak Import/Export](https://www.keycloak.org/server/importExport)
- [Keycloak REST API](https://www.keycloak.org/docs-api/23.0.0/rest-api/index.html)

---

## 변경 이력

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|----------|
| 1.0 | 2026-01-30 | Infra Agent | 초기 작성 |
