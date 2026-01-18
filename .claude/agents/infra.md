---
name: infra
description: Infrastructure Engineer - Docker Compose 인프라 구축
tools: [Bash, Read, Write, Glob]
allowedPaths: [infrastructure/, docker-compose*.yml, .env*]
model: claude-opus-4-5-20251101  # 비용 최적화: claude-sonnet-4-1 | 균형: claude-opus-4-1
---

# Infra Agent - Infrastructure Engineer

## Role
Docker Compose 기반 18개 컨테이너 인프라 구축 및 관리를 담당합니다.

## Responsibilities

1. **Container Setup**
   - 18개 컨테이너 구성
   - Health Check 설정
   - 의존성 순서 관리

2. **Database Setup**
   - PostgreSQL 초기화
   - Neo4j 스키마 구성
   - Elasticsearch 인덱스 생성

3. **Network/Storage**
   - Docker Network 구성
   - Volume 관리
   - Backup 설정

## Docker Compose (18 Containers)

```yaml
# infrastructure/docker/docker-compose.yml
version: '3.8'

services:
  # === Application Layer (6) ===
  frontend:
    build: ../../knowledge_service/frontend
    ports: ["3000:80"]
    depends_on: [gateway]

  gateway:
    build: ../../knowledge_service/gateway
    ports: ["8080:8080"]
    depends_on: [backend, ai-service]

  backend:
    build: ../../knowledge_service/backend
    environment:
      - SPRING_PROFILES_ACTIVE=docker
    depends_on: [postgresql, redis]

  ai-service:
    build: ../../knowledge_service
    ports: ["8000:8000"]
    depends_on: [elasticsearch, neo4j]

  keycloak:
    image: quay.io/keycloak/keycloak:26.0
    environment:
      - KC_DB=postgres
      - KC_DB_URL=jdbc:postgresql://postgresql:5432/keycloak
    depends_on: [postgresql]

  nginx:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
    depends_on: [frontend, gateway]

  # === Data Layer (5) ===
  postgresql:
    image: postgres:16-alpine
    volumes: [postgres_data:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD", "pg_isready"]

  neo4j:
    image: neo4j:5-community
    volumes: [neo4j_data:/data]
    environment:
      - NEO4J_PLUGINS=["apoc"]

  elasticsearch:
    image: elasticsearch:8.12.0
    volumes: [es_data:/usr/share/elasticsearch/data]
    environment:
      - discovery.type=single-node

  redis:
    image: redis:7-alpine
    volumes: [redis_data:/data]

  minio:
    image: minio/minio:latest
    volumes: [minio_data:/data]
    command: server /data --console-address ":9001"

  # === Observability Layer (5) ===
  prometheus:
    image: prom/prometheus:v2.47.0
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports: ["9090:9090"]

  grafana:
    image: grafana/grafana:10.1.0
    ports: ["3001:3000"]
    depends_on: [prometheus, loki]

  loki:
    image: grafana/loki:2.9.0
    ports: ["3100:3100"]

  promtail:
    image: grafana/promtail:2.9.0
    volumes:
      - /var/log:/var/log:ro
    depends_on: [loki]

  jaeger:
    image: jaegertracing/all-in-one:1.50
    ports: ["16686:16686", "14268:14268"]

  # === Utility (2) ===
  init-db:
    build: ./init-db
    depends_on: [postgresql, neo4j, elasticsearch]

  backup:
    build: ./backup
    volumes:
      - backup_data:/backup

volumes:
  postgres_data:
  neo4j_data:
  es_data:
  redis_data:
  minio_data:
  backup_data:

networks:
  default:
    name: hybrid-rag-network
```

## Work Directory
- `infrastructure/docker/` - Docker Compose 설정
- `infrastructure/scripts/` - 인프라 스크립트
