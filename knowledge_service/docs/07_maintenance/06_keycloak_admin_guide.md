# Keycloak 관리자 가이드

운영 환경에서의 Keycloak 관리 및 문제 해결 가이드

**Version**: 1.0
**Last Updated**: 2026-01-30
**Author**: Infra Agent

---

## 목차

1. [빠른 시작](#빠른-시작)
2. [일상 운영 작업](#일상-운영-작업)
3. [사용자 관리](#사용자-관리)
4. [클라이언트 관리](#클라이언트-관리)
5. [토큰 관리](#토큰-관리)
6. [모니터링](#모니터링)
7. [문제 해결](#문제-해결)
8. [백업 및 복구](#백업-및-복구)

---

## 빠른 시작

### 접속 정보

| 환경 | URL | 비고 |
|------|-----|------|
| **Admin Console** | http://localhost:8180/admin/ | 관리 UI |
| **Account Console** | http://localhost:8180/realms/hybrid-rag/account/ | 사용자 셀프서비스 |
| **OIDC 설정** | http://localhost:8180/realms/hybrid-rag/.well-known/openid-configuration | Discovery |

### Admin 토큰 발급

```bash
# 환경변수 설정
export KEYCLOAK_URL="http://localhost:8180"
export KEYCLOAK_ADMIN="admin"
export KEYCLOAK_ADMIN_PASSWORD="your-password"

# 토큰 발급
ADMIN_TOKEN=$(curl -s -X POST "$KEYCLOAK_URL/realms/master/protocol/openid-connect/token" \
  -d "grant_type=password" \
  -d "client_id=admin-cli" \
  -d "username=$KEYCLOAK_ADMIN" \
  -d "password=$KEYCLOAK_ADMIN_PASSWORD" | jq -r '.access_token')

echo "Admin Token: ${ADMIN_TOKEN:0:50}..."
```

---

## 일상 운영 작업

### 서비스 상태 확인

```bash
# Health Check
curl -s http://localhost:8180/health/ready | jq

# Realm 확인
curl -s http://localhost:8180/realms/hybrid-rag | jq '.realm, .displayName'

# 컨테이너 로그
docker logs kp-keycloak --tail 100 -f
```

### 서비스 재시작

```bash
# Keycloak만 재시작
docker compose restart keycloak

# 전체 인증 스택 재시작
docker compose restart keycloak keycloak-db
```

### 설정 변경 적용

```bash
# realm-export.json 수정 후
docker compose restart keycloak

# 강제 재import
docker exec -it kp-keycloak /opt/keycloak/bin/kc.sh import \
  --file /opt/keycloak/data/import/realm-export.json \
  --override true
```

---

## 사용자 관리

### 사용자 목록 조회

```bash
curl -s "$KEYCLOAK_URL/admin/realms/hybrid-rag/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.[].username'
```

### 사용자 생성

```bash
curl -X POST "$KEYCLOAK_URL/admin/realms/hybrid-rag/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "newuser@example.com",
    "firstName": "New",
    "lastName": "User",
    "enabled": true,
    "emailVerified": true,
    "credentials": [{
      "type": "password",
      "value": "SecurePassword123!",
      "temporary": false
    }],
    "realmRoles": ["user"]
  }'
```

### 비밀번호 재설정

```bash
# 사용자 ID 조회
USER_ID=$(curl -s "$KEYCLOAK_URL/admin/realms/hybrid-rag/users?username=targetuser" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq -r '.[0].id')

# 비밀번호 재설정
curl -X PUT "$KEYCLOAK_URL/admin/realms/hybrid-rag/users/$USER_ID/reset-password" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "password",
    "value": "NewPassword123!",
    "temporary": true
  }'
```

### 사용자 비활성화

```bash
curl -X PUT "$KEYCLOAK_URL/admin/realms/hybrid-rag/users/$USER_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

### 역할 할당

```bash
# 사용 가능한 역할 조회
curl -s "$KEYCLOAK_URL/admin/realms/hybrid-rag/roles" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.[].name'

# 역할 할당
curl -X POST "$KEYCLOAK_URL/admin/realms/hybrid-rag/users/$USER_ID/role-mappings/realm" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '[{"name": "admin"}]'
```

---

## 클라이언트 관리

### 클라이언트 목록

```bash
curl -s "$KEYCLOAK_URL/admin/realms/hybrid-rag/clients" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.[] | {clientId, enabled, publicClient}'
```

### Client Secret 재생성

```bash
# Client ID 조회
CLIENT_UUID=$(curl -s "$KEYCLOAK_URL/admin/realms/hybrid-rag/clients?clientId=backend" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq -r '.[0].id')

# Secret 재생성
curl -X POST "$KEYCLOAK_URL/admin/realms/hybrid-rag/clients/$CLIENT_UUID/client-secret" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# 새 Secret 조회
curl -s "$KEYCLOAK_URL/admin/realms/hybrid-rag/clients/$CLIENT_UUID/client-secret" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.value'
```

### Redirect URI 추가

```bash
# 현재 설정 조회
curl -s "$KEYCLOAK_URL/admin/realms/hybrid-rag/clients/$CLIENT_UUID" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.redirectUris'

# 업데이트
curl -X PUT "$KEYCLOAK_URL/admin/realms/hybrid-rag/clients/$CLIENT_UUID" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "redirectUris": [
      "http://localhost/*",
      "http://localhost:3000/*",
      "https://your-domain.com/*"
    ]
  }'
```

---

## 토큰 관리

### 토큰 발급 테스트

```bash
# Password Grant (테스트용)
curl -s -X POST "$KEYCLOAK_URL/realms/hybrid-rag/protocol/openid-connect/token" \
  -d "grant_type=password" \
  -d "client_id=frontend" \
  -d "username=test-user" \
  -d "password=test-password" | jq

# Client Credentials (서비스 간 통신)
curl -s -X POST "$KEYCLOAK_URL/realms/hybrid-rag/protocol/openid-connect/token" \
  -d "grant_type=client_credentials" \
  -d "client_id=backend" \
  -d "client_secret=backend-secret-dev" | jq
```

### 토큰 검증

```bash
# 토큰 디코딩
echo $TOKEN | cut -d'.' -f2 | base64 -d 2>/dev/null | jq

# Introspection
curl -s -X POST "$KEYCLOAK_URL/realms/hybrid-rag/protocol/openid-connect/token/introspect" \
  -d "token=$TOKEN" \
  -d "client_id=backend" \
  -d "client_secret=backend-secret-dev" | jq
```

### 세션 관리

```bash
# 활성 세션 조회
curl -s "$KEYCLOAK_URL/admin/realms/hybrid-rag/users/$USER_ID/sessions" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# 특정 사용자 세션 종료
curl -X DELETE "$KEYCLOAK_URL/admin/realms/hybrid-rag/users/$USER_ID/sessions" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# 전체 세션 종료 (주의!)
curl -X POST "$KEYCLOAK_URL/admin/realms/hybrid-rag/logout-all" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## 모니터링

### 메트릭 확인

```bash
# Keycloak 메트릭 (Prometheus 형식)
curl -s http://localhost:8180/metrics

# 활성 사용자 수
curl -s "$KEYCLOAK_URL/admin/realms/hybrid-rag/users/count" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### 이벤트 로그

```bash
# 최근 로그인 이벤트
curl -s "$KEYCLOAK_URL/admin/realms/hybrid-rag/events?type=LOGIN&max=10" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# 실패한 로그인
curl -s "$KEYCLOAK_URL/admin/realms/hybrid-rag/events?type=LOGIN_ERROR&max=10" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.[].details'
```

### Grafana 대시보드 쿼리

```promql
# 로그인 성공률
sum(rate(keycloak_login_attempts_total{realm="hybrid-rag",result="success"}[5m]))
/
sum(rate(keycloak_login_attempts_total{realm="hybrid-rag"}[5m]))

# 활성 세션 수
keycloak_active_sessions{realm="hybrid-rag"}
```

---

## 문제 해결

### 증상별 진단

#### 1. 로그인 실패 (401)

```bash
# 원인 확인
docker logs kp-keycloak 2>&1 | grep -i "invalid\|fail\|error" | tail -20

# 사용자 존재 확인
curl -s "$KEYCLOAK_URL/admin/realms/hybrid-rag/users?username=testuser" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# 사용자 활성화 상태 확인
curl -s "$KEYCLOAK_URL/admin/realms/hybrid-rag/users?username=testuser" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.[0].enabled'
```

#### 2. Realm 없음 (404)

```bash
# Realm 목록 확인
curl -s "$KEYCLOAK_URL/admin/realms" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.[].realm'

# Import 상태 확인
docker logs kp-keycloak 2>&1 | grep -i "import\|realm"
```

#### 3. 토큰 검증 실패

```bash
# JWKS 확인
curl -s "$KEYCLOAK_URL/realms/hybrid-rag/protocol/openid-connect/certs" | jq

# 토큰 issuer 확인
echo $TOKEN | cut -d'.' -f2 | base64 -d 2>/dev/null | jq '.iss'
# 예상값: http://localhost:8180/realms/hybrid-rag
```

#### 4. 메모리 부족

```bash
# 컨테이너 리소스 확인
docker stats kp-keycloak --no-stream

# 힙 메모리 조정
# docker-compose.yml 수정
# environment:
#   - JAVA_OPTS=-Xms512m -Xmx1g
```

### 로그 수준 조정

```bash
# 디버그 모드 활성화
docker exec -it kp-keycloak /opt/keycloak/bin/kc.sh start-dev \
  --log-level=DEBUG

# 특정 카테고리만
docker exec -it kp-keycloak /opt/keycloak/bin/kc.sh start-dev \
  --log-level=org.keycloak.authentication:DEBUG
```

---

## 백업 및 복구

### Realm 백업

```bash
#!/bin/bash
# backup_keycloak.sh

BACKUP_DIR="./backups/keycloak"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Realm export
docker exec kp-keycloak /opt/keycloak/bin/kc.sh export \
  --dir /tmp/export \
  --realm hybrid-rag \
  --users realm_file

# 호스트로 복사
docker cp kp-keycloak:/tmp/export/hybrid-rag-realm.json \
  $BACKUP_DIR/hybrid-rag-realm-$DATE.json

echo "Backup saved: $BACKUP_DIR/hybrid-rag-realm-$DATE.json"
```

### Realm 복구

```bash
#!/bin/bash
# restore_keycloak.sh

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: $0 <backup-file>"
  exit 1
fi

# 파일 복사
docker cp $BACKUP_FILE kp-keycloak:/tmp/restore-realm.json

# Import
docker exec kp-keycloak /opt/keycloak/bin/kc.sh import \
  --file /tmp/restore-realm.json \
  --override true

echo "Realm restored from: $BACKUP_FILE"
```

### 데이터베이스 백업

```bash
# PostgreSQL 백업
docker exec kp-keycloak-db pg_dump -U keycloak keycloak > keycloak_db_backup.sql

# 복구
docker exec -i kp-keycloak-db psql -U keycloak keycloak < keycloak_db_backup.sql
```

---

## 보안 체크리스트

| 항목 | 확인 | 비고 |
|------|:----:|------|
| Admin 비밀번호 강도 | [ ] | 16자 이상, 특수문자 포함 |
| SSL/TLS 활성화 | [ ] | Production 필수 |
| Brute Force 보호 | [x] | realm-export.json에 설정됨 |
| Password Policy | [ ] | 최소 8자, 대소문자+숫자 |
| Session Timeout | [x] | 30분 (SSO Idle) |
| Token Lifespan | [x] | 1시간 (Access Token) |
| 불필요한 Client 제거 | [ ] | 사용하지 않는 client 비활성화 |
| 감사 로그 활성화 | [x] | Admin Events 활성화됨 |

---

## 참고 명령어 모음

```bash
# === 자주 사용하는 명령어 ===

# Admin 토큰 발급
alias kc-token='curl -s -X POST "http://localhost:8180/realms/master/protocol/openid-connect/token" -d "grant_type=password" -d "client_id=admin-cli" -d "username=admin" -d "password=$KEYCLOAK_ADMIN_PASSWORD" | jq -r ".access_token"'

# 사용자 목록
alias kc-users='curl -s "http://localhost:8180/admin/realms/hybrid-rag/users" -H "Authorization: Bearer $(kc-token)" | jq ".[].username"'

# 클라이언트 목록
alias kc-clients='curl -s "http://localhost:8180/admin/realms/hybrid-rag/clients" -H "Authorization: Bearer $(kc-token)" | jq ".[] | {clientId, enabled}"'

# Health Check
alias kc-health='curl -s http://localhost:8180/health/ready | jq'

# 로그 보기
alias kc-logs='docker logs kp-keycloak --tail 100 -f'
```

---

## 관련 문서

- [Keycloak 설정 가이드](../../../infrastructure/docker/keycloak/README.md)
- [인증/인가 상세 설계서](../../02_design/03_authentication_authorization_detailed_design.md)
- [Docker Troubleshooting](./docker_troubleshooting.md)
- [Keycloak 공식 문서](https://www.keycloak.org/documentation)
