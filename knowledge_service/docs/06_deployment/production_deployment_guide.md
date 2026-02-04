# Production Deployment Guide

**Version**: 1.0.0
**Created**: 2026-02-04
**Status**: Draft

---

## Document Information

| Item | Content |
|------|---------|
| Document | Production Deployment Guide |
| Version | 1.0.0 |
| Created | 2026-02-04 |
| Author | Infra Agent |
| Related Tickets | STORY-073 |

---

## Table of Contents

1. [Overview](#1-overview)
2. [Prerequisites](#2-prerequisites)
3. [Environment Configuration](#3-environment-configuration)
4. [Deployment Steps](#4-deployment-steps)
5. [SSL/TLS Setup](#5-ssltls-setup)
6. [Security Checklist](#6-security-checklist)
7. [Health Verification](#7-health-verification)
8. [Rollback Procedure](#8-rollback-procedure)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Overview

This guide covers the deployment of the Hybrid RAG Knowledge Platform to a production environment using Docker Compose.

### 1.1 Architecture Overview

```
                    Internet
                        |
                   [Nginx:443]
                        |
            +-----------+-----------+
            |           |           |
        [Frontend]  [API Gateway] [Keycloak]
                        |
            +-----------+-----------+
            |                       |
        [Backend]             [AI Service]
            |                       |
    +-------+-------+       +-------+-------+
    |       |       |       |       |       |
  [PG]   [Redis] [MinIO]  [ES]   [Neo4j]  [DeepSeek]
```

### 1.2 Key Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Base configuration (18 containers) |
| `docker-compose.prod.yml` | Production overrides (security, limits) |
| `.env.production` | Production environment variables |
| `nginx/conf.d/ssl.conf.template` | SSL/TLS configuration template |

---

## 2. Prerequisites

### 2.1 Server Requirements

| Specification | Minimum | Recommended |
|---------------|---------|-------------|
| **CPU** | 16 cores | 32 cores |
| **Memory** | 64 GB | 128 GB |
| **Storage (SSD)** | 500 GB | 1 TB |
| **Network** | 1 Gbps | 10 Gbps |
| **OS** | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |

### 2.2 Software Requirements

```bash
# Docker Engine 24.x+
docker --version

# Docker Compose v2+
docker compose version

# OpenSSL (for generating secrets)
openssl version
```

### 2.3 Network Requirements

| Port | Service | Direction | Description |
|------|---------|-----------|-------------|
| 80 | Nginx | Inbound | HTTP redirect |
| 443 | Nginx | Inbound | HTTPS traffic |
| 22 | SSH | Inbound | Admin access |

All other ports are internal Docker network only.

---

## 3. Environment Configuration

### 3.1 Generate Secrets

```bash
# Navigate to docker directory
cd infrastructure/docker

# Generate all required secrets
echo "DB_PASSWORD=$(openssl rand -base64 32)"
echo "NEO4J_PASSWORD=$(openssl rand -base64 32)"
echo "REDIS_PASSWORD=$(openssl rand -base64 32)"
echo "ES_PASSWORD=$(openssl rand -base64 32)"
echo "KEYCLOAK_ADMIN_PASSWORD=$(openssl rand -base64 32)"
echo "KEYCLOAK_DB_PASSWORD=$(openssl rand -base64 32)"
echo "JWT_SECRET=$(openssl rand -base64 64)"
echo "MINIO_ACCESS_KEY=$(openssl rand -base64 24 | tr -dc 'A-Za-z0-9')"
echo "MINIO_SECRET_KEY=$(openssl rand -base64 32)"
echo "GRAFANA_ADMIN_PASSWORD=$(openssl rand -base64 32)"
echo "KIBANA_PASSWORD=$(openssl rand -base64 32)"
```

### 3.2 Configure .env.production

```bash
# Copy template
cp .env.production .env

# Edit with actual values
nano .env

# Verify no placeholders remain
grep -n "__" .env
# Should return empty (no matches)
```

### 3.3 Required Environment Variables Checklist

- [ ] `DOMAIN` - Production domain (e.g., knowledge.company.com)
- [ ] `DB_PASSWORD` - PostgreSQL password
- [ ] `NEO4J_PASSWORD` - Neo4j password
- [ ] `REDIS_PASSWORD` - Redis password
- [ ] `ES_PASSWORD` - Elasticsearch password
- [ ] `KEYCLOAK_ADMIN_PASSWORD` - Keycloak admin password
- [ ] `KEYCLOAK_DB_PASSWORD` - Keycloak DB password
- [ ] `JWT_SECRET` - JWT signing secret (64+ chars)
- [ ] `MINIO_ACCESS_KEY` - MinIO access key
- [ ] `MINIO_SECRET_KEY` - MinIO secret key
- [ ] `DEEPSEEK_API_KEY` - DeepSeek API key
- [ ] `GRAFANA_ADMIN_PASSWORD` - Grafana admin password

---

## 4. Deployment Steps

### 4.1 Pre-Deployment

```bash
# 1. Clone repository (if not exists)
git clone https://github.com/your-org/hybrid-rag-knowledge-ops.git
cd hybrid-rag-knowledge-ops/infrastructure/docker

# 2. Verify configuration
docker compose -f docker-compose.yml -f docker-compose.prod.yml config

# 3. Pull images
docker compose -f docker-compose.yml -f docker-compose.prod.yml pull
```

### 4.2 Initial Deployment

```bash
# 1. Create data directories
sudo mkdir -p /data/{postgresql,neo4j,elasticsearch,minio,redis,prometheus,grafana,loki}

# 2. Set permissions
sudo chown -R 999:999 /data/postgresql
sudo chown -R 1000:1000 /data/elasticsearch
sudo chown -R 7474:7474 /data/neo4j
sudo chown -R 1000:1000 /data/minio
sudo chown -R 999:999 /data/redis
sudo chown -R 65534:65534 /data/prometheus
sudo chown -R 472:472 /data/grafana
sudo chown -R 10001:10001 /data/loki

# 3. Start services
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 4. Wait for services to be healthy (2-5 minutes)
watch docker compose ps

# 5. Initialize databases (first deployment only)
docker compose --profile init up init-db
```

### 4.3 Verify Deployment

```bash
# Check all containers are healthy
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps

# Expected output: All services should show "healthy" status
# NAME                STATUS              HEALTH
# kp-nginx            Up 2 minutes        healthy
# kp-frontend         Up 2 minutes        healthy
# kp-api-gateway      Up 2 minutes        healthy
# kp-backend          Up 2 minutes        healthy
# kp-ai-service       Up 2 minutes        healthy
# ...
```

### 4.4 Update Deployment

```bash
# 1. Pull latest images
docker compose -f docker-compose.yml -f docker-compose.prod.yml pull

# 2. Rolling update (zero-downtime)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps --build backend

# 3. Repeat for other services as needed
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps --build ai-service
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps --build frontend

# 4. Restart nginx to apply changes
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart nginx
```

---

## 5. SSL/TLS Setup

### 5.1 Option A: Let's Encrypt (Recommended)

```bash
# 1. Install Certbot
sudo apt install certbot

# 2. Stop nginx temporarily
docker compose stop nginx

# 3. Obtain certificate
sudo certbot certonly --standalone -d knowledge.company.com

# 4. Copy certificates
sudo cp /etc/letsencrypt/live/knowledge.company.com/fullchain.pem ./nginx/certs/
sudo cp /etc/letsencrypt/live/knowledge.company.com/privkey.pem ./nginx/certs/
sudo cp /etc/letsencrypt/live/knowledge.company.com/chain.pem ./nginx/certs/

# 5. Set permissions
chmod 600 ./nginx/certs/*.pem

# 6. Enable SSL config
cp ./nginx/conf.d/ssl.conf.template ./nginx/conf.d/ssl.conf
sed -i 's/\${DOMAIN}/knowledge.company.com/g' ./nginx/conf.d/ssl.conf

# 7. Restart nginx
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d nginx
```

### 5.2 Option B: Corporate Certificate

```bash
# 1. Place certificates
cp /path/to/company-cert.pem ./nginx/certs/fullchain.pem
cp /path/to/company-key.pem ./nginx/certs/privkey.pem
cp /path/to/company-chain.pem ./nginx/certs/chain.pem

# 2. Enable SSL config (same as above)
cp ./nginx/conf.d/ssl.conf.template ./nginx/conf.d/ssl.conf
sed -i 's/\${DOMAIN}/knowledge.company.com/g' ./nginx/conf.d/ssl.conf

# 3. Restart nginx
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart nginx
```

### 5.3 Certificate Renewal (Let's Encrypt)

```bash
# Add to crontab (runs twice daily)
echo "0 0,12 * * * root certbot renew --quiet && docker compose -C /opt/knowledge-platform restart nginx" | sudo tee /etc/cron.d/certbot-renewal
```

---

## 6. Security Checklist

### 6.1 Pre-Deployment Security

- [ ] All default passwords changed
- [ ] JWT secret is 64+ characters
- [ ] SSL/TLS certificates installed
- [ ] Firewall configured (only 80, 443 open)
- [ ] SSH key-based auth only
- [ ] .env file permissions restricted (chmod 600)

### 6.2 Production Hardening Applied

The `docker-compose.prod.yml` applies these security measures:

| Measure | Description |
|---------|-------------|
| `read_only: true` | Containers have read-only filesystems |
| `cap_drop: ALL` | All Linux capabilities dropped |
| `no-new-privileges` | Prevents privilege escalation |
| `user: "1000:1000"` | Non-root user execution |
| `internal: true` | Database network fully isolated |
| `ports: []` | Internal services have no port exposure |

### 6.3 Post-Deployment Verification

```bash
# Verify no unnecessary ports exposed
docker compose -f docker-compose.yml -f docker-compose.prod.yml port --help

# Check container security settings
docker inspect kp-backend --format '{{json .HostConfig.SecurityOpt}}'

# Verify network isolation
docker network inspect kp-database | grep '"Internal": true'
```

---

## 7. Health Verification

### 7.1 Automated Health Check Script

```bash
#!/bin/bash
# scripts/health-check.sh

echo "=== Production Health Check ==="

# 1. Container Status
echo -e "\n[1] Container Status"
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps --format "table {{.Name}}\t{{.Status}}\t{{.Health}}"

# 2. API Health
echo -e "\n[2] API Health"
curl -s -k https://localhost/api/v1/health | jq .

# 3. Database Connections
echo -e "\n[3] Database Status"
docker exec kp-postgresql pg_isready -q && echo "PostgreSQL: OK" || echo "PostgreSQL: FAILED"
docker exec kp-redis redis-cli ping | grep -q PONG && echo "Redis: OK" || echo "Redis: FAILED"
curl -s http://localhost:9200/_cluster/health | jq -r '.status' | grep -E 'green|yellow' && echo "Elasticsearch: OK" || echo "Elasticsearch: FAILED"

# 4. Memory Usage
echo -e "\n[4] Memory Usage"
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"

echo -e "\n=== Health Check Complete ==="
```

### 7.2 Monitoring Endpoints

| Endpoint | URL | Purpose |
|----------|-----|---------|
| Nginx Health | `https://domain/nginx-health` | Nginx status |
| API Health | `https://domain/api/v1/health` | Backend health |
| Grafana | `https://domain/grafana` | Metrics dashboard |

---

## 8. Rollback Procedure

### 8.1 Quick Rollback

```bash
# 1. Stop current deployment
docker compose -f docker-compose.yml -f docker-compose.prod.yml down

# 2. Switch to previous version
git checkout <previous-tag>

# 3. Restart with previous version
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 8.2 Database Rollback

```bash
# 1. Stop application services
docker compose stop backend ai-service api-gateway

# 2. Restore PostgreSQL
gunzip -c /backup/postgresql_YYYYMMDD.sql.gz | docker exec -i kp-postgresql psql -U knowledge

# 3. Restore Elasticsearch snapshot
curl -X POST "localhost:9200/_snapshot/backup/snapshot_YYYYMMDD/_restore"

# 4. Restart services
docker compose start
```

---

## 9. Troubleshooting

### 9.1 Common Issues

| Issue | Diagnosis | Solution |
|-------|-----------|----------|
| Container won't start | `docker logs <container>` | Check logs for errors |
| Port conflict | `netstat -tlnp` | Stop conflicting service |
| Permission denied | `ls -la /data/*` | Fix ownership/permissions |
| Out of memory | `docker stats` | Increase limits or add RAM |
| SSL certificate error | `openssl s_client -connect domain:443` | Verify cert chain |

### 9.2 Log Locations

```bash
# Application logs
docker compose logs -f backend
docker compose logs -f ai-service

# Nginx access/error logs
docker compose exec nginx tail -f /var/log/nginx/access.log
docker compose exec nginx tail -f /var/log/nginx/error.log

# Aggregated logs (Loki + Grafana)
# Access via: https://domain/grafana -> Explore -> Loki
```

### 9.3 Emergency Procedures

```bash
# Kill and restart all containers
docker compose -f docker-compose.yml -f docker-compose.prod.yml down
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Force recreate specific container
docker compose up -d --force-recreate backend

# Reset to clean state (DATA LOSS!)
docker compose down -v
docker volume prune -f
```

---

## References

| Document | Location |
|----------|----------|
| Infrastructure Design | `docs/02_design/infrastructure_detailed_design.md` |
| Security Guide | `docs/06_deployment/security_env_setup_guide.md` |
| Backup Guide | `docs/07_maintenance/backup_restore_guide.md` |
| Docker Compose Base | `infrastructure/docker/docker-compose.yml` |
| Production Override | `infrastructure/docker/docker-compose.prod.yml` |

---

**Document End**
