# 빠른 시작 가이드 (Quick Start)

## 5분 만에 개발 환경 구축하기

**버전**: 1.0  
**작성일**: 2026-01-20  
**작성자**: TechLead Agent

---

## 사전 준비 체크리스트

실행 전 아래 항목이 설치되어 있는지 확인하세요:

- [ ] Docker Desktop (4.25+) - 실행 중인지 확인
- [ ] Git (2.40+)
- [ ] Node.js (18+) - Frontend 개발 시
- [ ] Java 17 - Backend 개발 시
- [ ] Python 3.11 + Poetry - AI Service 개발 시

```bash
# 설치 확인 명령어
docker --version && git --version && node --version && java -version
```

---

## Step 1: 프로젝트 클론 (30초)

```bash
git clone git@github.com:your-org/hybrid-rag-knowledge-ops.git
cd hybrid-rag-knowledge-ops
```

---

## Step 2: 환경 파일 설정 (1분)

```bash
# Docker 환경 파일 복사
cp infrastructure/docker/.env.example infrastructure/docker/.env

# 필수 값 편집 (에디터로 열기)
vi infrastructure/docker/.env
```

**필수 변경 항목** (.env 파일):

```bash
DB_PASSWORD=MySecurePassword123\!
NEO4J_PASSWORD=MyNeo4jPassword123\!
KEYCLOAK_ADMIN_PASSWORD=MyKeycloakAdmin123\!
KEYCLOAK_DB_PASSWORD=MyKeycloakDB123\!
MINIO_SECRET_KEY=MyMinioSecret123\!
GRAFANA_ADMIN_PASSWORD=MyGrafana123\!
DEEPSEEK_API_KEY=sk-your-deepseek-api-key
```

> 비밀번호 생성: `openssl rand -base64 24`

---

## Step 3: Docker 서비스 실행 (2분)

```bash
cd infrastructure/docker

# 전체 서비스 시작
docker compose up -d

# 서비스 상태 확인
docker compose ps
```

**메모리 제한 환경 (16GB 미만)**:

```bash
# 핵심 서비스만 실행
docker compose up -d postgresql neo4j elasticsearch redis keycloak keycloak-db
```

---

## Step 4: 서비스 확인 (1분)

```bash
# 헬스 체크
curl -s http://localhost:9200/_cluster/health | jq
curl -s http://localhost:8180/health | jq
```

**서비스 접속 URL**:

| 서비스 | URL | 기본 계정 |
|--------|-----|----------|
| Keycloak Admin | http://localhost:8180 | admin / (설정값) |
| Neo4j Browser | http://localhost:7474 | neo4j / (설정값) |
| Grafana | http://localhost:3001 | admin / (설정값) |
| MinIO Console | http://localhost:9001 | minioadmin / (설정값) |

---

## Step 5: DB 초기화 (30초, 최초 1회)

```bash
docker compose --profile init up init-db

# 완료 확인
docker logs kp-init-db
```

---

## 완료\!

개발 환경이 준비되었습니다. 다음 단계:

### Frontend 개발

```bash
cd knowledge_service/frontend
npm install && npm run dev
# http://localhost:3000 접속
```

### Backend 개발

```bash
cd knowledge_service/backend
./gradlew bootRun --args='--spring.profiles.active=local'
```

### AI Service 개발

```bash
cd knowledge_service
poetry install
poetry run uvicorn src.app.main:app --reload --port 8000
```

---

## 트러블슈팅 FAQ

### Q: 컨테이너가 시작되지 않아요

```bash
# 로그 확인
docker compose logs [service_name]

# 메모리 부족 시: Docker Desktop 메모리 12GB+ 설정
```

### Q: 포트 충돌이 발생해요

```bash
# 사용 중인 포트 확인
lsof -i :8080  # Linux/macOS
netstat -ano | findstr :8080  # Windows

# .env에서 포트 변경
GATEWAY_PORT=8081
```

### Q: Elasticsearch가 실패해요

```bash
# Linux
sudo sysctl -w vm.max_map_count=262144

# Windows (WSL2)
wsl -d docker-desktop sysctl -w vm.max_map_count=262144
```

### Q: 모든 것을 초기화하고 싶어요

```bash
# 컨테이너 + 볼륨 삭제
docker compose down -v

# 다시 시작
docker compose up -d
docker compose --profile init up init-db
```

---

## 관련 문서

- [상세 개발 환경 설정](./development_environment_setup.md)
- [개발 컨벤션](./development_conventions.md)
- [개발자 통합 가이드](./developer_integration_guide.md)

---

**문서 버전**: 1.0 | **최종 수정**: 2026-01-20 | **작성자**: TechLead Agent
