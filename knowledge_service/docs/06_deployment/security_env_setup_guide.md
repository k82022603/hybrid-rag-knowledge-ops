# 보안 환경변수 설정 가이드

**프로젝트**: Hybrid RAG Knowledge Operations Platform
**버전**: 1.0
**작성일**: 2026-01-28
**작성자**: Backend Developer (STORY-053)
**상태**: Active

---

## 문서 정보

| 항목 | 내용 |
|------|------|
| **문서명** | 보안 환경변수 설정 가이드 |
| **관련 Story** | STORY-053 보안 강화 |
| **대상 독자** | 개발자, 운영팀, DevOps 엔지니어 |
| **적용 환경** | Local Development, Docker, Production |

---

## 1. 개요

본 문서는 Hybrid RAG Knowledge Platform의 보안 관련 환경변수 설정 방법을 안내합니다.
STORY-053 보안 강화 작업의 일환으로 모든 비밀 정보가 환경변수로 관리되도록 변경되었습니다.

### 1.1 변경 배경

Sprint 03 보안 검토에서 다음 취약점이 식별되어 환경변수 기반으로 전환하였습니다:

| 취약점 | 위험도 | 조치 |
|--------|--------|------|
| JWT Secret 하드코딩 | Critical | 환경변수 필수 (기본값 제거) |
| 기본 자격증명 사용 | High | 환경변수 기반 비밀번호 설정 |
| SSE 입력 검증 부재 | Medium | 입력 길이 제한 및 새니타이징 |

---

## 2. 필수 환경변수 목록

### 2.1 인증/보안 (Critical - 반드시 설정)

| 변수명 | 설명 | 최소 요구사항 | 기본값 |
|--------|------|--------------|--------|
| `JWT_SECRET` | JWT 토큰 서명 키 | 32자 이상 (HS256) | 없음 (미설정 시 시작 실패) |

### 2.2 데이터베이스 자격증명 (Required)

| 변수명 | 설명 | 예시 |
|--------|------|------|
| `DB_PASSWORD` | PostgreSQL 메인 DB 비밀번호 | (강력한 비밀번호) |
| `DB_USERNAME` | PostgreSQL DB 사용자명 | `knowledge` |
| `DB_NAME` | PostgreSQL DB 이름 | `knowledge` |
| `NEO4J_PASSWORD` | Neo4j 그래프 DB 비밀번호 | (강력한 비밀번호) |
| `NEO4J_USER` | Neo4j 사용자명 | `neo4j` |
| `REDIS_PASSWORD` | Redis 캐시 비밀번호 | (선택, 빈 값 허용) |
| `ELASTICSEARCH_PASSWORD` | Elasticsearch 비밀번호 | (선택) |

### 2.3 Keycloak OAuth 2.0 (Required)

| 변수명 | 설명 | 예시 |
|--------|------|------|
| `KEYCLOAK_ADMIN` | Keycloak 관리자 계정 | (기본값 admin 사용 금지) |
| `KEYCLOAK_ADMIN_PASSWORD` | Keycloak 관리자 비밀번호 | (강력한 비밀번호) |
| `KEYCLOAK_DB_USER` | Keycloak 전용 DB 사용자 | `keycloak` |
| `KEYCLOAK_DB_PASSWORD` | Keycloak 전용 DB 비밀번호 | (강력한 비밀번호) |
| `KEYCLOAK_REALM` | Keycloak Realm 이름 | `hybrid-rag` |

### 2.4 객체 스토리지 (Required)

| 변수명 | 설명 | 예시 |
|--------|------|------|
| `MINIO_ACCESS_KEY` | MinIO 접근 키 | (최소 8자) |
| `MINIO_SECRET_KEY` | MinIO 비밀 키 | (강력한 비밀번호) |

### 2.5 AI 서비스 API 키 (Required)

| 변수명 | 설명 | 예시 |
|--------|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek LLM API 키 | `sk-...` |
| `DEEPSEEK_BASE_URL` | DeepSeek API 엔드포인트 | `https://api.deepseek.com` |

### 2.6 모니터링 (Required for Production)

| 변수명 | 설명 | 예시 |
|--------|------|------|
| `GRAFANA_ADMIN_USER` | Grafana 관리자 계정 | (기본값 admin 사용 금지) |
| `GRAFANA_ADMIN_PASSWORD` | Grafana 관리자 비밀번호 | (강력한 비밀번호) |

---

## 3. 안전한 비밀 값 생성 방법

### 3.1 JWT Secret 생성

```bash
# 방법 1: openssl (권장, 64바이트 Base64 인코딩)
openssl rand -base64 48

# 방법 2: Python
python3 -c "import secrets; print(secrets.token_urlsafe(48))"

# 방법 3: /dev/urandom (Linux/macOS)
head -c 48 /dev/urandom | base64
```

생성 예시 출력:
```
Kx7bN2mQ8pF3vR9wT1yA4zC6eH0jL5nO8qS2uW4xB7dG0iJ3lM6oP9rU1wY
```

### 3.2 데이터베이스 비밀번호 생성

```bash
# 강력한 비밀번호 (영문 대소문자 + 숫자 + 특수문자, 24자)
openssl rand -base64 18

# 또는 Python으로 생성
python3 -c "import secrets, string; chars = string.ascii_letters + string.digits + '!@#$%'; print(''.join(secrets.choice(chars) for _ in range(24)))"
```

### 3.3 비밀번호 강도 요구사항

| 등급 | 조건 | 적용 대상 |
|------|------|----------|
| **Critical** | 48자 이상, Base64 인코딩 | JWT_SECRET |
| **High** | 16자 이상, 대소문자+숫자+특수문자 | DB 비밀번호, Keycloak Admin |
| **Medium** | 12자 이상, 대소문자+숫자 | MinIO, Grafana |
| **API Key** | 제공 업체 규격 준수 | DEEPSEEK_API_KEY |

---

## 4. 환경별 설정 방법

### 4.1 로컬 개발 환경 (.env 파일)

1. `.env.example` 파일을 `.env`로 복사합니다:

```bash
# 프로젝트 루트
cp .env.example .env

# Docker 환경
cp infrastructure/docker/.env.example infrastructure/docker/.env

# Knowledge Service
cp knowledge_service/.env.example knowledge_service/.env
```

2. `.env` 파일을 편집하여 실제 비밀 값을 입력합니다:

```bash
# .env 파일 편집
vi .env

# 또는 자동 생성 스크립트 사용
JWT_SECRET=$(openssl rand -base64 48)
DB_PASSWORD=$(openssl rand -base64 18)
KEYCLOAK_ADMIN_PASSWORD=$(openssl rand -base64 18)
```

3. `.env` 파일 권한을 제한합니다:

```bash
# 소유자만 읽기/쓰기 가능
chmod 600 .env
chmod 600 infrastructure/docker/.env
chmod 600 knowledge_service/.env
```

4. `.gitignore` 확인:

```bash
# .env 파일이 git에 포함되지 않는지 확인
git check-ignore .env
# 출력: .env (정상)
```

### 4.2 Docker Compose 배포

Docker Compose에서 환경변수를 전달하는 방법:

**방법 A: .env 파일 사용 (개발 환경 권장)**

```yaml
# docker-compose.yml
services:
  backend:
    env_file:
      - .env
    environment:
      - JWT_SECRET=${JWT_SECRET}
      - SPRING_DATASOURCE_PASSWORD=${DB_PASSWORD}
```

```bash
# .env 파일 생성 후 Docker Compose 실행
docker compose --env-file infrastructure/docker/.env up -d
```

**방법 B: 환경변수 직접 전달 (CI/CD 권장)**

```bash
# 셸 환경변수 설정 후 실행
export JWT_SECRET=$(openssl rand -base64 48)
export DB_PASSWORD=$(openssl rand -base64 18)
export KEYCLOAK_ADMIN_PASSWORD=$(openssl rand -base64 18)

docker compose up -d
```

**방법 C: Docker Secrets (운영 환경 권장)**

```yaml
# docker-compose.prod.yml
services:
  backend:
    secrets:
      - jwt_secret
      - db_password
    environment:
      - JWT_SECRET_FILE=/run/secrets/jwt_secret
      - DB_PASSWORD_FILE=/run/secrets/db_password

secrets:
  jwt_secret:
    file: ./secrets/jwt_secret.txt
  db_password:
    file: ./secrets/db_password.txt
```

```bash
# secrets 디렉토리 생성 및 비밀 값 저장
mkdir -p secrets
openssl rand -base64 48 > secrets/jwt_secret.txt
openssl rand -base64 18 > secrets/db_password.txt
chmod 600 secrets/*.txt
```

### 4.3 운영 환경 (Production)

운영 환경에서는 다음 중 하나의 방법으로 비밀을 관리합니다:

| 방법 | 장점 | 단점 | 권장 |
|------|------|------|------|
| Docker Secrets | 파일 기반, 안전 | Docker Swarm 필요 | Swarm 환경 |
| HashiCorp Vault | 중앙 집중, 감사 로그 | 추가 인프라 필요 | 대규모 환경 |
| AWS SSM / Azure KeyVault | 클라우드 네이티브 | 클라우드 종속 | 클라우드 환경 |
| 환경변수 + .env | 간단 | 파일 관리 필요 | 소규모/초기 |

---

## 5. Keycloak 관리자 자격증명 설정

### 5.1 초기 설정

Keycloak은 최초 실행 시 관리자 계정을 생성합니다:

```bash
# 환경변수로 관리자 계정 설정
KEYCLOAK_ADMIN=kp-admin          # "admin" 사용 금지
KEYCLOAK_ADMIN_PASSWORD=$(openssl rand -base64 18)
```

### 5.2 Realm 및 클라이언트 설정

```bash
# Keycloak Admin CLI를 통한 Realm 생성
docker exec keycloak /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 \
  --realm master \
  --user ${KEYCLOAK_ADMIN} \
  --password ${KEYCLOAK_ADMIN_PASSWORD}

# Realm 생성
docker exec keycloak /opt/keycloak/bin/kcadm.sh create realms \
  -s realm=hybrid-rag \
  -s enabled=true
```

### 5.3 운영 환경 보안 강화

```properties
# Keycloak 보안 설정 (application.yml 또는 환경변수)
KC_HOSTNAME_STRICT=true
KC_HOSTNAME_STRICT_HTTPS=true
KC_HTTP_ENABLED=false                    # HTTPS만 허용
KC_PROXY=edge                            # 리버스 프록시 뒤에서 실행
KC_LOG_LEVEL=INFO                        # 감사 로깅
```

---

## 6. JWT Secret 보안 가이드

### 6.1 설정 검증

애플리케이션 시작 시 JWT_SECRET에 대해 다음 검증이 수행됩니다:

```
1. 환경변수 존재 여부 확인 -> 미설정 시 시작 실패 (IllegalStateException)
2. 최소 길이 확인 (32자 이상) -> 미달 시 시작 실패
3. 기본값/예시값 사용 여부 확인 -> 'CHANGE_ME' 포함 시 경고 로그
```

### 6.2 JWT Secret 로테이션

운영 환경에서는 정기적으로 JWT Secret을 교체해야 합니다:

```bash
# 1. 새 Secret 생성
NEW_JWT_SECRET=$(openssl rand -base64 48)

# 2. 환경변수 업데이트 (무중단 배포)
# - 새 Secret으로 새 인스턴스 시작
# - 기존 인스턴스는 기존 토큰이 만료될 때까지 유지
# - 모든 토큰 만료 후 이전 인스턴스 종료

# 3. 교체 주기: 90일 권장
```

---

## 7. 운영 배포 체크리스트

배포 전 다음 항목을 반드시 확인하세요:

### 7.1 필수 검증 항목

- [ ] **JWT_SECRET**: 환경변수 설정 완료 (32자 이상)
- [ ] **JWT_SECRET**: `CHANGE_ME` 또는 기본 예시값이 아닌 실제 값
- [ ] **DB_PASSWORD**: 기본 비밀번호(password, secret 등)가 아닌 강력한 비밀번호
- [ ] **NEO4J_PASSWORD**: 기본 비밀번호가 아닌 강력한 비밀번호
- [ ] **KEYCLOAK_ADMIN**: `admin`이 아닌 고유 계정명
- [ ] **KEYCLOAK_ADMIN_PASSWORD**: 기본 비밀번호가 아닌 강력한 비밀번호
- [ ] **GRAFANA_ADMIN_USER**: `admin`이 아닌 고유 계정명
- [ ] **GRAFANA_ADMIN_PASSWORD**: 기본 비밀번호가 아닌 강력한 비밀번호
- [ ] **MINIO_ACCESS_KEY / MINIO_SECRET_KEY**: 기본값이 아닌 실제 키
- [ ] **DEEPSEEK_API_KEY**: 유효한 API 키

### 7.2 파일 보안 검증

- [ ] `.env` 파일이 `.gitignore`에 포함됨
- [ ] `.env` 파일 권한: `600` (소유자만 읽기/쓰기)
- [ ] `secrets/` 디렉토리 권한: `700` (소유자만 접근)
- [ ] 비밀 값이 로그에 출력되지 않음

### 7.3 네트워크 보안 검증

- [ ] Keycloak 관리 콘솔: 내부 네트워크에서만 접근 가능
- [ ] 데이터베이스 포트: 외부 노출 차단 (Docker internal network)
- [ ] Redis: 비밀번호 설정 완료 (운영 환경)
- [ ] Grafana/Prometheus: 인증 필수

---

## 8. 문제 해결 (Troubleshooting)

### 8.1 애플리케이션 시작 실패

```
Error: JWT_SECRET 환경변수가 설정되지 않았습니다.
```

**해결 방법**:
```bash
# 환경변수 확인
echo $JWT_SECRET

# 설정되지 않은 경우 생성
export JWT_SECRET=$(openssl rand -base64 48)

# Docker Compose 사용 시 .env 파일 확인
cat infrastructure/docker/.env | grep JWT_SECRET
```

### 8.2 JWT Secret 길이 부족

```
Error: JWT_SECRET은 최소 32자 이상이어야 합니다.
```

**해결 방법**:
```bash
# 현재 길이 확인
echo -n "$JWT_SECRET" | wc -c

# 48바이트 Base64 (64자 출력) 재생성
export JWT_SECRET=$(openssl rand -base64 48)
```

### 8.3 Keycloak 로그인 실패

```
Error: Invalid credentials
```

**해결 방법**:
```bash
# 환경변수 확인
echo $KEYCLOAK_ADMIN
echo $KEYCLOAK_ADMIN_PASSWORD

# Keycloak 컨테이너 로그 확인
docker logs kp-keycloak 2>&1 | tail -20
```

### 8.4 데이터베이스 연결 실패

```
Error: FATAL: password authentication failed for user "knowledge"
```

**해결 방법**:
```bash
# Docker Compose .env와 application.yml 비밀번호 일치 확인
grep DB_PASSWORD infrastructure/docker/.env
grep SPRING_DATASOURCE_PASSWORD infrastructure/docker/.env

# PostgreSQL 컨테이너 내부에서 확인
docker exec -it kp-postgresql psql -U knowledge -d knowledge
```

---

## 9. 보안 모범 사례

### 9.1 하지 말아야 할 것 (Do NOT)

```bash
# 1. 비밀 값을 코드에 하드코딩하지 마세요
jwt_secret = "my-secret-key"  # WRONG

# 2. 비밀 값을 커밋하지 마세요
git add .env  # WRONG

# 3. 기본 비밀번호를 사용하지 마세요
KEYCLOAK_ADMIN_PASSWORD=admin  # WRONG

# 4. 비밀 값을 로그로 출력하지 마세요
logger.info(f"JWT Secret: {jwt_secret}")  # WRONG

# 5. 비밀 값을 URL 쿼리 파라미터로 전달하지 마세요
/api/login?password=secret123  # WRONG
```

### 9.2 해야 할 것 (DO)

```bash
# 1. 환경변수로 비밀 값을 관리하세요
jwt_secret = os.getenv("JWT_SECRET")  # CORRECT

# 2. .env.example만 커밋하세요 (실제 값 없이)
git add .env.example  # CORRECT

# 3. 자동 생성된 강력한 비밀번호를 사용하세요
openssl rand -base64 48  # CORRECT

# 4. 비밀 값은 마스킹하여 로그에 출력하세요
logger.info(f"JWT Secret: {jwt_secret[:4]}***")  # CORRECT

# 5. 정기적으로 비밀 값을 교체하세요 (90일 주기)
```

---

## 10. 참고 자료

- [OWASP Top 10 - Sensitive Data Exposure](https://owasp.org/Top10/A02_2021-Cryptographic_Failures/)
- [Docker Secrets Documentation](https://docs.docker.com/engine/swarm/secrets/)
- [Spring Boot Externalized Configuration](https://docs.spring.io/spring-boot/reference/features/external-config.html)
- [Keycloak Administration Guide](https://www.keycloak.org/docs/latest/server_admin/)
- [STORY-053 보안 강화](../../../backlog/stories/STORY-053-security-hardening.md)
