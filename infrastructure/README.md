# Infrastructure Configuration

Hybrid RAG Knowledge Platform - Docker Compose 기반 인프라 구성

**Version**: 2.0 | **Updated**: 2026-01-20

---

## 18 Containers Overview

| Layer | Container | Image | Port | Description |
|-------|-----------|-------|------|-------------|
| **Application** | nginx | nginx:1.25-alpine | 80, 443 | Reverse Proxy |
| | frontend | custom | - | React SPA |
| | api-gateway | custom | 8080 | Spring Cloud Gateway |
| | backend | custom | 8081 | Spring Boot API |
| | ai-service | custom | 8000 | FastAPI AI Service |
| **Auth** | keycloak | keycloak:23.0 | 8180 | OAuth 2.0 / OIDC |
| | keycloak-db | postgres:16-alpine | - | Keycloak Database |
| **Data** | postgresql | postgres:16-alpine | 5432 | Main DB (SSOT) |
| | neo4j | neo4j:5.15-community | 7474, 7687 | Knowledge Graph |
| | elasticsearch | elasticsearch:8.11.0 | 9200 | Vector Search |
| | redis | redis:7.2-alpine | 6379 | Cache |
| | minio | minio:latest | 9000, 9001 | Object Storage |
| **Observability** | prometheus | prom/prometheus:v2.48.0 | 9090 | Metrics |
| | grafana | grafana/grafana:10.2.0 | 3001 | Dashboard |
| | loki | grafana/loki:2.9.0 | 3100 | Log Aggregation |
| | promtail | grafana/promtail:2.9.0 | - | Log Collection |
| | jaeger | jaegertracing/all-in-one:1.52 | 16686 | Distributed Tracing |
| **Utility** | init-db | python:3.11-slim | - | DB Initialization |

---

## Folder Structure

```
infrastructure/
├── docker/
│   ├── docker-compose.yml        # Main compose file (18 containers)
│   ├── .env.example              # Environment template
│   ├── nginx/
│   │   ├── nginx.conf            # Main nginx config
│   │   ├── conf.d/default.conf   # Server blocks
│   │   └── certs/                # SSL certificates
│   ├── keycloak/
│   │   └── realm-export.json     # Keycloak realm config
│   ├── prometheus/
│   │   ├── prometheus.yml        # Scrape config
│   │   └── rules/alerts.yml      # Alert rules
│   ├── grafana/
│   │   ├── provisioning/
│   │   │   ├── datasources/      # Auto-configure datasources
│   │   │   └── dashboards/       # Dashboard provisioning
│   │   └── dashboards/           # Dashboard JSON files
│   ├── loki/
│   │   └── loki-config.yml       # Loki configuration
│   ├── promtail/
│   │   └── promtail-config.yml   # Log collection config
│   └── scripts/
│       ├── init-postgresql.sql   # PostgreSQL init
│       ├── init-db.py            # ES/Neo4j/MinIO init
│       └── requirements-init.txt # Python dependencies
├── database/
│   ├── postgres/schema.sql       # PostgreSQL schema
│   ├── neo4j/schema.cypher       # Neo4j constraints
│   └── elasticsearch/mappings.json # ES index mappings
└── README.md
```

---

## Quick Start

### 1. Configure Environment

```bash
cd infrastructure/docker
cp .env.example .env
# Edit .env with your credentials
```

### 2. Start Core Services (Data Layer)

```bash
docker compose up -d postgresql keycloak-db neo4j elasticsearch redis minio
```

### 3. Start All Services

```bash
docker compose up -d
```

### 4. Initialize Databases (First Time Only)

```bash
docker compose --profile init up init-db
```

### 5. Check Status

```bash
docker compose ps
docker compose logs -f
```

---

## Service URLs

| Service | URL | Default Credentials |
|---------|-----|---------------------|
| Frontend | http://localhost | - |
| API Gateway | http://localhost:8080 | - |
| Keycloak Admin | http://localhost:8180 | admin / (see .env) |
| Neo4j Browser | http://localhost:7474 | neo4j / (see .env) |
| Grafana | http://localhost:3001 | admin / (see .env) |
| Prometheus | http://localhost:9090 | - |
| Jaeger UI | http://localhost:16686 | - |
| MinIO Console | http://localhost:9001 | (see .env) |

---

## Resource Requirements

### Minimum (Development)

| Resource | Requirement |
|----------|-------------|
| CPU | 8 cores |
| RAM | 16 GB |
| Storage | 100 GB SSD |

### Memory Allocation (16GB RAM)

| Container | Memory Limit | Memory Reserved |
|-----------|--------------|-----------------|
| nginx | 256 MB | 128 MB |
| frontend | 256 MB | 128 MB |
| api-gateway | 1 GB | 512 MB |
| backend | 2 GB | 1 GB |
| ai-service | 8 GB | 4 GB |
| keycloak | 1 GB | 512 MB |
| keycloak-db | 512 MB | 256 MB |
| postgresql | 4 GB | 2 GB |
| neo4j | 4 GB | 2 GB |
| elasticsearch | 4 GB | 2 GB |
| redis | 1 GB | 512 MB |
| minio | 1 GB | 512 MB |
| prometheus | 512 MB | 256 MB |
| grafana | 512 MB | 256 MB |
| loki | 512 MB | 256 MB |
| promtail | 256 MB | 128 MB |
| jaeger | 512 MB | 256 MB |
| **Total** | **~29 GB** | **~15 GB** |

---

## Common Commands

### Container Management

```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# Restart specific service
docker compose restart backend

# View logs
docker compose logs -f ai-service

# Check status
docker compose ps
```

### Database Operations

```bash
# PostgreSQL shell
docker exec -it kp-postgresql psql -U knowledge -d knowledge

# Neo4j shell
docker exec -it kp-neo4j cypher-shell -u neo4j -p <password>

# Redis CLI
docker exec -it kp-redis redis-cli

# Elasticsearch health
curl http://localhost:9200/_cluster/health?pretty
```

### Cleanup

```bash
# Remove containers and networks
docker compose down

# Remove with volumes (DATA LOSS!)
docker compose down -v

# Prune unused images
docker image prune -f
```

---

## Health Checks

All services include health checks:

```bash
# Check all service health
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Health}}"

# Individual health endpoints
curl http://localhost:8080/actuator/health  # API Gateway
curl http://localhost:8081/actuator/health  # Backend
curl http://localhost:8000/health           # AI Service
curl http://localhost:9200/_cluster/health  # Elasticsearch
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Container won't start | Check logs: `docker compose logs <service>` |
| Port conflict | Change port in `.env` file |
| Memory issues | Reduce limits or increase host RAM |
| ES bootstrap error | Run: `sudo sysctl -w vm.max_map_count=262144` |
| Neo4j plugin error | Check APOC plugin installation |

---

## Security Notes

- Never commit `.env` file to version control
- Change all default passwords before production
- Enable SSL/TLS for production deployments
- Review Keycloak security settings
- Configure proper network isolation

---

## Related Documents

- [Infrastructure Detailed Design](../knowledge_service/docs/02_design/infrastructure_detailed_design.md)
- [API Integration Design](../knowledge_service/docs/02_design/api_integration_design.md)
- [Database Schema](./database/postgres/schema.sql)

---

**Last Updated**: 2026-01-20 | **Author**: Infra Agent (Claude)
