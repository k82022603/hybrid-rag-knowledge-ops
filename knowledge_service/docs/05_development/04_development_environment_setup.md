# 개발 환경 설정 가이드

## Development Environment Setup Guide

**버전**: 1.0  
**작성일**: 2026-01-20  
**작성자**: TechLead Agent

---

## 1. 서비스 구성 (18 컨테이너)

| 레이어 | 서비스 | 기술 스택 | 포트 |
|--------|--------|----------|------|
| Application | Frontend | React 18 | 80 |
| Application | Gateway | Spring Cloud Gateway | 8080 |
| Application | Backend | Spring Boot 3.2 | 8081 |
| Application | AI Service | FastAPI, LangGraph | 8000 |
| Auth | Keycloak | Keycloak 23.0 | 8180 |
| Data | PostgreSQL | PostgreSQL 16 | 5432 |
| Data | Neo4j | Neo4j 5.15 | 7474/7687 |
| Data | Elasticsearch | ES 8.11 | 9200 |
| Data | Redis | Redis 7.2 | 6379 |
| Data | MinIO | MinIO | 9000/9001 |
| Observability | Prometheus | Prometheus 2.48 | 9090 |
| Observability | Grafana | Grafana 10.2 | 3001 |
| Observability | Jaeger | Jaeger 1.52 | 16686 |

---

## 2. 시스템 요구사항

### 2.1 하드웨어

| 항목 | 최소 | 권장 |
|------|------|------|
| RAM | 16GB | 32GB |
| CPU | 4 Core | 8 Core |
| Storage | 50GB SSD | 100GB SSD |

### 2.2 소프트웨어

| 소프트웨어 | 버전 | 용도 |
|-----------|------|------|
| Docker Desktop | 4.25+ | 컨테이너 실행 |
| Git | 2.40+ | 소스 관리 |
| Node.js | 18.0+ | Frontend 개발 |
| Java | 17 LTS | Backend 개발 |
| Python | 3.11+ | AI Service 개발 |
| Poetry | 1.6+ | Python 의존성 |

### 2.3 Docker 리소스

```
Settings > Resources > Advanced
- CPUs: 4+
- Memory: 12GB+
- Swap: 2GB
```

---

## 3. 필수 도구 설치

### 3.1 Windows

```powershell
choco install -y git docker-desktop nodejs-lts openjdk17 python311
```

### 3.2 macOS

```bash
brew install git node@18 openjdk@17 python@3.11
brew install --cask docker
curl -sSL https://install.python-poetry.org | python3 -
```

### 3.3 Ubuntu

```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs openjdk-17-jdk python3.11
curl -sSL https://install.python-poetry.org | python3 -
curl -fsSL https://get.docker.com | sudo sh
```

---

## 4. 프로젝트 설정

```bash
git clone git@github.com:your-org/hybrid-rag-knowledge-ops.git
cd hybrid-rag-knowledge-ops
cp infrastructure/docker/.env.example infrastructure/docker/.env
cp knowledge_service/.env.example knowledge_service/.env
```

---

## 5. Docker Compose 환경 구축

### 5.1 전체 서비스 실행

```bash
cd infrastructure/docker
docker compose up -d
docker compose ps
```

### 5.2 서비스 그룹별 실행

```bash
# 데이터베이스만
docker compose up -d postgresql neo4j elasticsearch redis

# 전체 인프라
docker compose up -d postgresql neo4j elasticsearch redis minio keycloak keycloak-db
```

### 5.3 DB 초기화

```bash
docker compose --profile init up init-db
```

### 5.4 서비스 URL

| 서비스 | URL |
|--------|-----|
| API Gateway | http://localhost:8080 |
| Keycloak | http://localhost:8180 |
| Neo4j | http://localhost:7474 |
| Elasticsearch | http://localhost:9200 |
| MinIO | http://localhost:9001 |
| Grafana | http://localhost:3001 |

---

## 6. 서비스별 로컬 개발

### 6.1 Frontend

```bash
cd knowledge_service/frontend
npm install && npm run dev
```

### 6.2 Gateway/Backend

```bash
cd knowledge_service/gateway  # 또는 backend
./gradlew bootRun --args='--spring.profiles.active=local'
```

### 6.3 AI Service

```bash
cd knowledge_service
poetry install
poetry run uvicorn src.app.main:app --reload --port 8000
```

---

## 7. 환경 변수 설정

`infrastructure/docker/.env` 파일 편집:

```bash
# 필수 보안 설정
DB_PASSWORD=YourStrongPassword123\!
NEO4J_PASSWORD=YourNeo4jPassword123\!
KEYCLOAK_ADMIN_PASSWORD=YourKeycloakAdminPassword\!
MINIO_SECRET_KEY=YourMinioSecretKey\!
DEEPSEEK_API_KEY=sk-your-api-key
```

---

## 8. 검증 및 테스트

```bash
curl -s http://localhost:8080/actuator/health | jq
curl -s http://localhost:9200/_cluster/health | jq
docker exec -it kp-postgresql psql -U knowledge -c 'SELECT 1;'
```

---

## 9. 트러블슈팅

| 문제 | 해결 |
|------|------|
| 메모리 부족 | Docker 메모리 12GB+ 할당 |
| 포트 충돌 | .env에서 포트 변경 |
| ES 오류 | sudo sysctl -w vm.max_map_count=262144 |

---

## 관련 문서

- [빠른 시작 가이드](./quick_start_guide.md)
- [개발 컨벤션](./development_conventions.md)
- [개발자 통합 가이드](./developer_integration_guide.md)

---

**문서 버전**: 1.0 | **최종 수정**: 2026-01-20 | **작성자**: TechLead Agent
