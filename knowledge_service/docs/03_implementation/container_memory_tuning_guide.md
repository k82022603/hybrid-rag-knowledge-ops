# 컨테이너 메모리 튜닝 가이드

**Version**: 1.1 | **Updated**: 2026-01-21

---

## 목차

1. [현재 메모리 사용 현황](#1-현재-메모리-사용-현황)
2. [서비스별 튜닝 옵션](#2-서비스별-튜닝-옵션)
3. [개발 환경 경량화 프로파일](#3-개발-환경-경량화-프로파일)
4. [튜닝 적용 방법](#4-튜닝-적용-방법)
5. [모니터링 및 검증](#5-모니터링-및-검증)
6. [적용 결과 (2026-01-21)](#6-적용-결과-2026-01-21)

---

## 1. 현재 메모리 사용 현황

### 1.1 전체 현황 (2026-01-21 기준)

**총 사용량**: 4.83GB / 7.42GB (65%)

### 1.2 서비스별 메모리 사용량

| 컨테이너 | 현재 사용 | 제한(limit) | 예약(reservation) | 사용률 | 카테고리 |
|----------|-----------|-------------|-------------------|--------|----------|
| kp-elasticsearch | 2.86GB | 4GB | 2GB | 71.5% | Data Layer |
| kp-neo4j | 757.8MB | 4GB | 2GB | 18.5% | Data Layer |
| kp-kibana | 553.9MB | 1GB | 512MB | 54.0% | Data Layer |
| kp-keycloak | 259.8MB | 1GB | 512MB | 25.4% | Security |
| kp-grafana | 82.15MB | 512MB | 256MB | 16.0% | Observability |
| kp-minio | 79.63MB | 1GB | 512MB | 7.8% | Data Layer |
| kp-prometheus | 67.92MB | 512MB | 256MB | 13.3% | Observability |
| kp-loki | 63.86MB | 512MB | 256MB | 12.5% | Observability |
| kp-postgresql | 38.07MB | 4GB | 2GB | 0.9% | Data Layer |
| kp-keycloak-db | 26.79MB | 512MB | 256MB | 5.2% | Security |
| kp-promtail | 22.74MB | 256MB | 128MB | 8.9% | Observability |
| kp-jaeger | 17MB | 512MB | 256MB | 3.3% | Observability |
| kp-nginx | 12.83MB | 256MB | 128MB | 5.0% | Frontend |
| kp-redis | - | 1GB | 512MB | - | Data Layer |

### 1.3 메모리 소비 Top 5

1. **Elasticsearch** (2.86GB) - JVM 힙 2GB + 오버헤드
2. **Neo4j** (757.8MB) - JVM 힙 + 페이지 캐시
3. **Kibana** (553.9MB) - Node.js 기반
4. **Keycloak** (259.8MB) - JVM 기반 인증 서버
5. **Grafana** (82.15MB) - Go 기반 대시보드

---

## 2. 서비스별 튜닝 옵션

### 2.1 Elasticsearch (가장 큰 절감 가능)

**현재 설정**:
```yaml
environment:
  - "ES_JAVA_OPTS=-Xms2g -Xmx2g"
deploy:
  resources:
    limits:
      memory: 4G
    reservations:
      memory: 2G
```

**개발 환경 튜닝**:
```yaml
environment:
  - "ES_JAVA_OPTS=-Xms512m -Xmx512m"  # 힙 512MB로 축소
  - xpack.ml.enabled=false             # ML 기능 비활성화 (이미 적용됨)
deploy:
  resources:
    limits:
      memory: 1G                       # 4G → 1G
    reservations:
      memory: 512M                     # 2G → 512M
```

**절감 효과**: ~3GB 절감 (4GB → 1GB)

**주의사항**:
- 대용량 인덱싱 시 OOM 가능
- 개발/테스트용으로만 권장
- 프로덕션은 최소 2GB 힙 유지

---

### 2.2 Neo4j

**현재 설정**:
```yaml
environment:
  - NEO4J_dbms_memory_heap_initial__size=1G
  - NEO4J_dbms_memory_heap_max__size=2G
  - NEO4J_dbms_memory_pagecache_size=1G
deploy:
  resources:
    limits:
      memory: 4G
    reservations:
      memory: 2G
```

**개발 환경 튜닝**:
```yaml
environment:
  - NEO4J_dbms_memory_heap_initial__size=256m
  - NEO4J_dbms_memory_heap_max__size=512m
  - NEO4J_dbms_memory_pagecache_size=256m
deploy:
  resources:
    limits:
      memory: 1G                       # 4G → 1G
    reservations:
      memory: 512M                     # 2G → 512M
```

**절감 효과**: ~3GB 절감 (4GB → 1GB)

**주의사항**:
- 그래프 쿼리 성능 저하 가능
- 대규모 트래버설 시 느려질 수 있음

---

### 2.3 Kibana

**현재 설정**:
```yaml
deploy:
  resources:
    limits:
      memory: 1G
    reservations:
      memory: 512M
```

**개발 환경 튜닝**:
```yaml
environment:
  - NODE_OPTIONS=--max-old-space-size=256  # Node.js 힙 제한
deploy:
  resources:
    limits:
      memory: 512M                     # 1G → 512M
    reservations:
      memory: 256M                     # 512M → 256M
```

**절감 효과**: ~500MB 절감 (1GB → 512MB)

---

### 2.4 Keycloak

**현재 설정**:
```yaml
deploy:
  resources:
    limits:
      memory: 1G
    reservations:
      memory: 512M
```

**개발 환경 튜닝**:
```yaml
environment:
  - JAVA_OPTS_APPEND=-Xms128m -Xmx384m  # 힙 제한
deploy:
  resources:
    limits:
      memory: 512M                     # 1G → 512M
    reservations:
      memory: 256M                     # 512M → 256M
```

**절감 효과**: ~500MB 절감 (1GB → 512MB)

**주의사항**:
- 동시 인증 요청이 많으면 성능 저하
- Realm 설정이 복잡하면 시작 시간 증가

---

### 2.5 Observability 스택

#### Prometheus

**현재**: 512MB limit

**개발 환경 튜닝**:
```yaml
deploy:
  resources:
    limits:
      memory: 256M                     # 512M → 256M
    reservations:
      memory: 128M                     # 256M → 128M
```

추가 설정 (prometheus.yml):
```yaml
global:
  scrape_interval: 30s                 # 15s → 30s (수집 빈도 감소)

storage:
  tsdb:
    retention.time: 3d                 # 15d → 3d (보관 기간 단축)
```

#### Grafana

**현재**: 512MB limit

**개발 환경 튜닝**:
```yaml
deploy:
  resources:
    limits:
      memory: 256M                     # 512M → 256M
    reservations:
      memory: 128M                     # 256M → 128M
```

#### Loki

**현재**: 512MB limit

**개발 환경 튜닝**:
```yaml
deploy:
  resources:
    limits:
      memory: 256M                     # 512M → 256M
    reservations:
      memory: 128M                     # 256M → 128M
```

추가 설정:
```yaml
limits_config:
  ingestion_rate_mb: 4                 # 기본값보다 낮게
  ingestion_burst_size_mb: 6
```

#### Jaeger

**현재**: 512MB limit, 메모리 스토리지

**개발 환경 튜닝**:
```yaml
environment:
  - MEMORY_MAX_TRACES=5000             # 10000 → 5000
deploy:
  resources:
    limits:
      memory: 256M                     # 512M → 256M
    reservations:
      memory: 128M                     # 256M → 128M
```

---

## 3. 개발 환경 경량화 프로파일

### 3.1 메모리 절감 요약

| 서비스 | 현재 제한 | 경량화 제한 | 절감량 |
|--------|----------|-------------|--------|
| Elasticsearch | 4GB | 1GB | -3GB |
| Neo4j | 4GB | 1GB | -3GB |
| Kibana | 1GB | 512MB | -512MB |
| Keycloak | 1GB | 512MB | -512MB |
| PostgreSQL | 4GB | 1GB | -3GB |
| Prometheus | 512MB | 256MB | -256MB |
| Grafana | 512MB | 256MB | -256MB |
| Loki | 512MB | 256MB | -256MB |
| Jaeger | 512MB | 256MB | -256MB |
| **총계** | **~17GB** | **~5.5GB** | **~11.5GB** |

### 3.2 docker-compose.override.yml (개발용)

개발 환경에서 메모리를 절감하려면 `docker-compose.override.yml` 파일을 생성합니다:

```yaml
# infrastructure/docker/docker-compose.override.yml
# 개발 환경용 메모리 경량화 설정

version: '3.8'

services:
  # Elasticsearch 경량화
  elasticsearch:
    environment:
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M

  # Neo4j 경량화
  neo4j:
    environment:
      - NEO4J_dbms_memory_heap_initial__size=256m
      - NEO4J_dbms_memory_heap_max__size=512m
      - NEO4J_dbms_memory_pagecache_size=256m
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M

  # Kibana 경량화
  kibana:
    environment:
      - NODE_OPTIONS=--max-old-space-size=256
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M

  # Keycloak 경량화
  keycloak:
    environment:
      - JAVA_OPTS_APPEND=-Xms128m -Xmx384m
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M

  # PostgreSQL 경량화
  postgresql:
    command: >
      postgres
      -c shared_buffers=128MB
      -c effective_cache_size=256MB
      -c work_mem=4MB
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M

  # Prometheus 경량화
  prometheus:
    deploy:
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 128M

  # Grafana 경량화
  grafana:
    deploy:
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 128M

  # Loki 경량화
  loki:
    deploy:
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 128M

  # Jaeger 경량화
  jaeger:
    environment:
      - MEMORY_MAX_TRACES=5000
    deploy:
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 128M
```

---

## 4. 튜닝 적용 방법

### 4.1 Override 파일 사용 (권장)

```bash
cd infrastructure/docker

# 1. override 파일 생성 (위 3.2 내용 복사)
vi docker-compose.override.yml

# 2. 컨테이너 재시작 (자동으로 override 적용)
docker compose down
docker compose up -d
```

### 4.2 직접 수정 (비권장)

`docker-compose.yml` 직접 수정 시 git에서 충돌 가능.
`.gitignore`에 override 파일 추가 권장.

### 4.3 환경별 분리

```bash
# 개발 환경
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# 프로덕션 환경
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## 5. 모니터링 및 검증

### 5.1 메모리 사용량 확인

```bash
# 전체 컨테이너 메모리 사용량
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"

# 특정 컨테이너 상세
docker inspect --format='{{.HostConfig.Memory}}' kp-elasticsearch

# 실시간 모니터링
watch -n 5 'docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}"'
```

### 5.2 OOM 발생 확인

```bash
# OOM 킬 이벤트 확인
dmesg | grep -i "oom\|killed"

# 컨테이너 로그에서 OOM 확인
docker logs kp-elasticsearch 2>&1 | grep -i "outofmemory\|heap"
```

### 5.3 서비스 정상 동작 검증

```bash
# Elasticsearch
curl -s http://localhost:9200/_cluster/health

# Neo4j
curl -s http://localhost:7474

# Keycloak
curl -s http://localhost:8180/health/ready

# Grafana
curl -s http://localhost:3001/api/health

# Prometheus
curl -s http://localhost:9090/-/healthy
```

### 5.4 Grafana 대시보드

Grafana에서 Container Memory 대시보드 생성:
- URL: http://localhost:3001
- Data source: Prometheus
- Query: `container_memory_usage_bytes{name=~"kp-.*"}`

---

## 권장 사항

### 개발 환경

| 항목 | 권장 설정 |
|------|----------|
| 총 메모리 | 8GB 이상 |
| Elasticsearch | 1GB (힙 512MB) |
| Neo4j | 1GB (힙 512MB) |
| Keycloak | 512MB |
| Observability | 각 256MB |

### 프로덕션 환경

| 항목 | 권장 설정 |
|------|----------|
| 총 메모리 | 32GB 이상 |
| Elasticsearch | 8GB (힙 4GB) |
| Neo4j | 8GB (힙 4GB, 페이지캐시 2GB) |
| Keycloak | 2GB |
| Observability | 각 1GB |

---

## 6. 적용 결과 (2026-01-21)

### 6.1 튜닝 전후 비교

#### Before (기본 설정)

| 컨테이너 | 사용량 | 제한 | 사용률 |
|----------|--------|------|--------|
| kp-elasticsearch | 2.86GB | 4GB | 71.5% |
| kp-neo4j | 757.8MB | 4GB | 18.5% |
| kp-kibana | 553.9MB | 1GB | 54.0% |
| kp-keycloak | 259.8MB | 1GB | 25.4% |
| kp-grafana | 82.15MB | 512MB | 16.0% |
| kp-prometheus | 67.92MB | 512MB | 13.3% |
| kp-loki | 63.86MB | 512MB | 12.5% |
| **총 메모리 제한** | - | **~17GB** | - |

#### After (경량화 적용)

| 컨테이너 | 사용량 | 제한 | 사용률 | 상태 |
|----------|--------|------|--------|------|
| kp-elasticsearch | 1.156GB | 1.5GB | 77.1% | ✅ healthy |
| kp-neo4j | 580.9MB | 1GB | 56.7% | ✅ healthy |
| kp-kibana | 618.6MB | 768MB | 80.5% | ✅ healthy |
| kp-keycloak | 335.6MB | 640MB | 52.4% | ✅ healthy |
| kp-grafana | 137.9MB | 256MB | 53.9% | ✅ healthy |
| kp-prometheus | 53.27MB | 256MB | 20.8% | ✅ healthy |
| kp-loki | 56.13MB | 256MB | 21.9% | ✅ healthy |
| kp-postgresql | 20.07MB | 1GB | 2.0% | ✅ healthy |
| **총 메모리 제한** | - | **~7.4GB** | - |

### 6.2 절감 효과

| 항목 | Before | After | 절감량 |
|------|--------|-------|--------|
| 총 메모리 제한 | ~17GB | ~7.4GB | **-9.6GB (56%)** |
| Elasticsearch | 4GB | 1.5GB | -2.5GB |
| Neo4j | 4GB | 1GB | -3GB |
| PostgreSQL | 4GB | 1GB | -3GB |
| Kibana | 1GB | 768MB | -256MB |
| Keycloak | 1GB | 640MB | -384MB |

### 6.3 적용된 최종 설정

**파일**: `infrastructure/docker/docker-compose.override.yml`

| 서비스 | 힙/캐시 설정 | 메모리 제한 |
|--------|-------------|-------------|
| Elasticsearch | ES_JAVA_OPTS=-Xms512m -Xmx512m | 1536MB |
| Neo4j | heap=512m, pagecache=256m | 1GB |
| Kibana | NODE_OPTIONS=--max-old-space-size=384 | 768MB |
| Keycloak | JAVA_OPTS_APPEND=-Xms128m -Xmx384m | 640MB |
| PostgreSQL | shared_buffers=128MB | 1GB |
| Prometheus | (기본) | 256MB |
| Grafana | (기본) | 256MB |
| Loki | (기본) | 256MB |
| Jaeger | MEMORY_MAX_TRACES=5000 | 256MB |
| Promtail | (기본) | 128MB |

### 6.4 트러블슈팅 기록

#### Kibana OOM 이슈

**문제**: 초기 512MB 제한, 256MB 힙 설정 시 OOM 발생
```
FATAL ERROR: Ineffective mark-compacts near heap limit Allocation failed - JavaScript heap out of memory
```

**해결**: 메모리 제한 768MB, 힙 384MB로 상향 조정

#### Elasticsearch 메모리 압박

**문제**: 1GB 제한 시 99.54% 사용률로 OOM 위험

**해결**: 메모리 제한 1.5GB로 상향 (힙 512MB 유지)

### 6.5 주의사항

1. **개발 환경 전용**: 이 설정은 개발/테스트 환경용입니다
2. **대용량 데이터**: 대량 인덱싱이나 복잡한 쿼리 시 성능 저하 가능
3. **프로덕션 금지**: 프로덕션 환경에서는 기본 설정 또는 더 높은 메모리 권장
4. **모니터링 필수**: `docker stats`로 주기적 모니터링 권장

---

## 변경 이력

| 날짜 | 버전 | 변경 내용 |
|------|------|----------|
| 2026-01-21 | 1.1 | 적용 결과 추가 (섹션 6) |
| 2026-01-21 | 1.0 | 초기 문서 작성 (메모리 분석 및 튜닝 가이드) |
