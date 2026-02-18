# 운영자 매뉴얼

**시스템**: Hybrid RAG Knowledge Platform
**버전**: 1.1
**작성일**: 2026-02-19

---

## 목차

1. [시스템 개요](#1-시스템-개요)
2. [접속 정보](#2-접속-정보)
3. [시스템 시작/종료](#3-시스템-시작종료)
4. [일상 운영](#4-일상-운영)
5. [모니터링](#5-모니터링)
6. [ETL 파이프라인 운영](#6-etl-파이프라인-운영)
7. [장애 대응](#7-장애-대응)
8. [백업/복구](#8-백업복구)
9. [주요 설정 파일](#9-주요-설정-파일)
10. [타임아웃 설정 가이드](#10-타임아웃-설정-가이드)

---

## 1. 시스템 개요

### 1.1 시스템 설명

Hybrid RAG Knowledge Platform은 기업 내부 문서를 자동 처리(파싱, 청킹, 임베딩, 엔티티 추출)하고, 4-Way Hybrid Search(Dense + Sparse + BM25 + Graph)를 RRF로 통합하여 최적의 검색 결과를 제공하는 지능형 지식 검색 시스템입니다.

### 1.2 구성 요소 (18개 컨테이너)

| # | 컨테이너명 | 레이어 | 역할 | 포트 |
|---|-----------|--------|------|------|
| 1 | kp-nginx | Application | 리버스 프록시 (진입점) | 80, 443 |
| 2 | kp-frontend | Application | React 18 프론트엔드 | (nginx 경유) |
| 3 | kp-api-gateway | Application | Spring Cloud Gateway | 8080 |
| 4 | kp-backend | Application | Spring Boot 비즈니스 로직 | 8081 |
| 5 | kp-ai-service | Application | FastAPI AI/RAG 서비스 (핵심) | 8000 |
| 6 | kp-keycloak | Auth | OAuth 2.0 / OIDC 인증 | 8180 |
| 7 | kp-keycloak-db | Auth | Keycloak 전용 PostgreSQL | (내부) |
| 8 | kp-postgresql | Data | 메인 데이터베이스 (SSOT) | 5432 |
| 9 | kp-neo4j | Data | Knowledge Graph (169K 노드, 775K 관계) | 7474, 7687 |
| 10 | kp-elasticsearch | Data | 벡터/전문검색 (42,462 청크) | 9200 |
| 11 | kp-kibana | Data | ES 데이터 시각화 | 5601 |
| 12 | kp-redis | Data | 캐시 서버 | 6379 |
| 13 | kp-minio | Data | 오브젝트 스토리지 (원본 문서) | 9000, 9001 |
| 14 | kp-prometheus | Observability | 메트릭 수집/저장 (TSDB) | 9090 |
| 15 | kp-grafana | Observability | 메트릭 시각화 (4개 대시보드) | 3001 |
| 16 | kp-loki | Observability | 경량 로그 저장 | 3100 |
| 17 | kp-promtail | Observability | 컨테이너 로그 수집 에이전트 | (내부) |
| 18 | kp-jaeger | Observability | 분산 추적 (Tracing) | 16686 |

### 1.3 아키텍처 개요

```
사용자 (브라우저)
    |
    v
[kp-nginx :80] ── Reverse Proxy
    |         \
    v          v
[kp-frontend]  [kp-api-gateway :8080]
                    |           \
                    v            v
            [kp-backend :8081]  [kp-keycloak :8180]
                    |
                    v
            [kp-ai-service :8000]  ── 핵심 AI/RAG 서비스
                /       |       \
               v        v        v
    [kp-elasticsearch] [kp-neo4j] [kp-postgresql]
         :9200          :7687        :5432
```

### 1.4 데이터 현황

| 항목 | 수치 |
|------|------|
| 문서 수 | 1,437개 |
| 청크 수 | 42,462개 |
| 엔티티 노드 | 169,886 (Entity + Technology + Person) |
| 관계 수 | 775,366 (MENTIONS + RELATED_TO + HAS_ENTITY + PART_OF) |
| Dense + Sparse 임베딩 | 100% 완료 |
| Entity Extraction | 100% 완료 |

### 1.5 핵심 서비스 우선순위

장애 복구 시 아래 순서로 복구하면 연쇄 영향을 최소화할 수 있습니다.

```
postgresql > redis > elasticsearch > neo4j > keycloak > ai-service > backend > api-gateway > nginx
```

### 1.6 컨테이너 재시작 순서 (의존성 기준)

컨테이너를 수동으로 개별 재시작해야 하는 경우, 아래 순서를 따릅니다.

```
1. PostgreSQL      (다른 모든 서비스의 SSOT)
2. Elasticsearch   (검색 인덱스, ai-service 의존)
3. Neo4j           (Knowledge Graph, ai-service 의존)
4. Redis           (캐시, Gateway Rate Limiter 의존)
5. AI Service      (RAG 파이프라인 핵심, 위 4개에 의존)
6. Backend         (비즈니스 로직, PostgreSQL/Keycloak 의존)
7. Gateway         (API 라우팅, Backend/AI Service 의존)
8. Nginx           (리버스 프록시, Gateway/Frontend 의존)
9. Frontend        (UI, Nginx 경유 접근)
```

```bash
# 전체 수동 순차 재시작 (필요 시)
docker compose restart postgresql && sleep 10 && \
docker compose restart elasticsearch && sleep 15 && \
docker compose restart neo4j && sleep 15 && \
docker compose restart redis && sleep 5 && \
docker compose restart ai-service && sleep 60 && \
docker compose restart backend && sleep 15 && \
docker compose restart api-gateway && sleep 10 && \
docker compose restart nginx && sleep 5 && \
docker compose restart frontend
```

> `docker compose up -d`는 `depends_on` + `condition: service_healthy` 설정으로 자동 순서 관리를 수행하므로, 전체 시작 시에는 수동 순서를 신경 쓸 필요가 없습니다.

---

## 2. 접속 정보

### 2.1 서비스 URL 및 인증 정보

| 서비스 | URL | ID / Password | 비고 |
|--------|-----|---------------|------|
| **Frontend (브라우저)** | http://localhost | (아래 AI Service 또는 SSO) | 메인 접속 |
| **AI Service Login** | http://localhost:8000/api/v1/auth/login | `admin@example.com` / `admin123!` | JWT 발급 |
| **AI Service Docs** | http://localhost:8000/docs | (인증 불필요) | FastAPI Swagger |
| **Keycloak SSO** | Frontend SSO 버튼 | `admin` / `admin123` | 또는 `test` / `password123` |
| **Keycloak Admin** | http://localhost:8180/admin | `admin` / `keycloak_admin_2026!` | Realm: `hybrid-rag` |
| **Grafana** | http://localhost:3001 | `admin` / `test1234` | 모니터링 대시보드 |
| **Kibana** | http://localhost:5601 | (인증 불필요) | ES 데이터 조회 |
| **Neo4j Browser** | http://localhost:7474 | `neo4j` / `neo4j_dev_2026!` | Knowledge Graph |
| **MinIO Console** | http://localhost:9001 | `minioadmin` / `minio_dev_2026!` | 문서 스토리지 |
| **Prometheus** | http://localhost:9090 | (인증 불필요) | 메트릭 조회 |
| **Jaeger UI** | http://localhost:16686 | (인증 불필요) | 트레이싱 |
| **PostgreSQL** | localhost:5432 | `knowledge` / `knowledge_dev_2026!` | DB: `knowledge` |
| **Redis** | localhost:6379 | (비밀번호 없음) | 캐시 |
| **Gateway Health** | http://localhost:8080/actuator/health | (인증 불필요) | 상태 확인 |
| **Backend Health** | http://localhost:8081/actuator/health | (인증 불필요) | 상태 확인 |
| **Swagger UI** | http://localhost:8080/swagger-ui.html | (인증 불필요) | API 문서 |

### 2.2 주요 DB 접속

```bash
# PostgreSQL
docker exec -it kp-postgresql psql -U knowledge -d knowledge

# Neo4j (Cypher Shell)
docker exec -it kp-neo4j cypher-shell -u neo4j -p 'neo4j_dev_2026!'

# Redis
docker exec -it kp-redis redis-cli

# Elasticsearch
curl http://localhost:9200/_cluster/health?pretty
```

---

## 3. 시스템 시작/종료

### 3.1 전체 시작

```bash
cd infrastructure/docker
docker compose up -d
```

Docker Compose의 `depends_on` + `condition: service_healthy`가 아래 순서를 자동 관리합니다.

| 단계 | 서비스 | 설명 |
|------|--------|------|
| Phase 1 | postgresql, keycloak-db, neo4j, elasticsearch, redis, minio | 데이터 레이어 (의존성 없음) |
| Phase 2 | keycloak, kibana, loki, prometheus, jaeger | 인증 + 모니터링 |
| Phase 3 | promtail, grafana | 로그 수집 |
| Phase 4 | backend, ai-service | 애플리케이션 |
| Phase 5 | frontend, api-gateway | 게이트웨이 + 프론트엔드 |
| Phase 6 | nginx | 리버스 프록시 |

### 3.2 자동 점검 (startup_check.sh)

시스템 기동 후 전체 상태를 자동으로 점검하는 스크립트입니다.

```bash
# 전체 기동 + 점검
bash scripts/startup_check.sh

# 이미 기동된 상태에서 점검만
bash scripts/startup_check.sh --skip-compose

# 상세 로그 출력
bash scripts/startup_check.sh --skip-compose --verbose
```

**5 Phase 점검 항목**:

| Phase | 점검 내용 | 상세 |
|-------|----------|------|
| **Phase 1** | 인프라 기동 + Health Check | Docker 데몬, docker-compose.yml, .env 존재 확인. kp-elasticsearch, kp-postgresql, kp-neo4j, kp-redis 4종 헬스체크. Redis PING/PONG 확인 |
| **Phase 2** | 애플리케이션 서비스 기동 | kp-ai-service 헬스체크. `/api/v1/health` 엔드포인트 호출. ES/Neo4j/PostgreSQL 연결 상태 파싱. 연결 실패 시 ai-service 1회 재시작 시도 |
| **Phase 3** | 검색 API 자동 테스트 | JWT 로그인(admin@example.com). Keyword/Hybrid/Semantic 3종 검색 실행. 검색 실패 시 Redis FLUSHALL + ai-service 재시작 후 재시도 |
| **Phase 4** | Nori Analyzer 검증 | ES `_analyze` API로 한국어 형태소 분석 확인. `"프로젝트관리시스템구축"` 입력 -> 4토큰 분리 검증 |
| **Phase 5** | 최종 리포트 | PASS/FAIL/WARN 집계. 18개 컨테이너 상태 테이블 출력. 전체 판정 (ALL PASS / PARTIAL / CRITICAL) |

**주요 옵션**:

| 옵션 | 설명 |
|------|------|
| `--skip-compose` | docker-compose up 건너뛰기 (이미 기동된 상태에서 점검만) |
| `--verbose` | 상세 디버그 로그 출력 |

**WSL2 환경 자동 감지**: WSL2에서 실행 시 `docker-compose.wsl2.yml` 오버라이드를 자동 적용합니다.

**자동 복구 기능**:
- Phase 2에서 의존성 연결 실패 시 ai-service 자동 재시작 (1회)
- Phase 3에서 검색 0건 반환 시 Redis FLUSHALL + ai-service 재시작 후 재시도

### 3.3 선택적 기동 (WSL2 메모리 제한 시)

전체 18개 컨테이너는 약 15.5GB RAM(reservations)을 요구합니다. WSL2 메모리가 부족할 경우 선택적으로 기동합니다.

```bash
# 핵심 서비스만 (검색 기능)
docker compose up -d postgresql neo4j elasticsearch redis ai-service

# 핵심 + 프론트엔드 (UI 사용)
docker compose up -d postgresql neo4j elasticsearch redis ai-service \
    keycloak keycloak-db backend frontend api-gateway nginx

# 모니터링 추가
docker compose up -d grafana prometheus kibana

# 불필요한 서비스 중지 (메모리 확보)
docker compose stop grafana kibana jaeger promtail loki
```

**서비스별 메모리 사용량 (상위)**:

| 서비스 | Memory Limit | Memory Reservation |
|--------|:-----------:|:------------------:|
| ai-service | 8G | 4G |
| postgresql | 4G | 2G |
| neo4j | 4G | 2G |
| elasticsearch | 4G | 2G |
| backend | 2G | 1G |

### 3.4 종료

```bash
cd infrastructure/docker

# 전체 종료 (데이터 유지)
docker compose down

# 전체 종료 + 볼륨 삭제 (모든 데이터 삭제 - 주의!)
docker compose down -v
```

> `docker compose down`은 의존관계를 고려하여 자동으로 역순 종료합니다.

---

## 4. 일상 운영

### 4.1 Health Check

**AI Service 종합 헬스체크** (가장 중요):

```bash
curl -s http://localhost:8000/api/v1/health | python3 -m json.tool
```

응답에서 각 dependency 상태를 확인합니다:
- `elasticsearch`: connected/disconnected
- `neo4j`: connected/disconnected
- `postgresql`: connected/disconnected
- `deepseek`: API 연결 상태

**전체 컨테이너 상태 확인**:

```bash
# 서비스 단위 상태
docker compose ps

# 포맷 지정 상태
docker ps --format "table {{.Names}}\t{{.Status}}" | grep kp-

# 리소스 사용량 (스냅샷)
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" | grep kp-
```

**개별 서비스 헬스체크**:

```bash
# Application Layer
curl -s http://localhost:8000/api/v1/health    # ai-service
curl -s http://localhost:8081/actuator/health   # backend
curl -s http://localhost:8080/actuator/health   # api-gateway

# Data Layer
docker exec kp-postgresql pg_isready -U knowledge -d knowledge
docker exec kp-redis redis-cli ping
curl -s http://localhost:9200/_cluster/health?pretty   # ES
curl -s http://localhost:7474                           # Neo4j

# Auth Layer
curl -s http://localhost:8180/health/ready     # keycloak

# Observability Layer
curl -s http://localhost:9090/-/healthy        # prometheus
curl -s http://localhost:3001/api/health       # grafana
curl -s http://localhost:3100/ready            # loki
```

### 4.2 로그 확인

```bash
# 특정 서비스 최근 로그
docker compose logs --tail=100 ai-service

# 실시간 로그 스트리밍
docker compose logs -f ai-service

# 특정 시간 이후 로그
docker logs --since="2026-02-18T09:00:00" kp-ai-service

# 에러만 필터링
docker compose logs ai-service 2>&1 | grep -i "error\|exception\|traceback"

# 여러 서비스 동시 확인
docker compose logs -f ai-service backend api-gateway
```

### 4.3 Redis 캐시 관리

#### 4.3.1 CLI 직접 관리

```bash
# Redis 접속
docker exec -it kp-redis redis-cli

# 캐시 키 목록 확인
docker exec kp-redis redis-cli KEYS "*"

# 캐시 항목 수 확인
docker exec kp-redis redis-cli DBSIZE

# 메모리 사용량 확인
docker exec kp-redis redis-cli INFO memory | head -10

# 전체 캐시 플러시 (검색 결과 stale 시 사용)
docker exec kp-redis redis-cli FLUSHALL
```

> 검색 결과가 이상할 때(stale cache), `FLUSHALL` 후 재검색하면 해결되는 경우가 많습니다.

#### 4.3.2 REST API를 통한 캐시 관리

AI Service에서 제공하는 캐시 관리 API를 활용할 수 있습니다.

**캐시 통계 확인**:

```bash
# JWT 토큰 획득 후 실행
curl -s -X GET http://localhost:8000/api/v1/cache/stats \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

**캐시 초기화**:

```bash
curl -s -X DELETE http://localhost:8000/api/v1/cache/clear \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

#### 4.3.3 캐시 TTL 설정

| 캐시 유형 | TTL (초) | TTL (사람 읽기) | 설정 위치 |
|-----------|:--------:|:---------------:|----------|
| **검색 결과 캐시** | 3,600 | 1시간 | `config.py` > `search_cache_ttl` |
| **임베딩 캐시** | 604,800 | 7일 | `config.py` > `redis_embedding_cache_ttl` |

> 검색 캐시 TTL은 데이터 업데이트 빈도에 맞춰 조정하세요. ETL 실행 직후에는 `FLUSHALL` 또는 `/api/v1/cache/clear`로 캐시를 초기화하는 것을 권장합니다.

### 4.4 일일 점검 체크리스트

```
[ ] 전체 컨테이너 상태 확인: docker compose ps
[ ] 비정상 컨테이너 유무 확인 (Restarting, Exit 상태)
[ ] ai-service /api/v1/health 정상 여부
[ ] 로그에서 ERROR/WARN 패턴 점검
[ ] 디스크 사용량 점검: df -h /
```

---

## 5. 모니터링

### 5.1 Grafana (http://localhost:3001)

**로그인**: `admin` / `test1234`

**제공 대시보드 (4개)**:

| 대시보드 | UID | 설명 |
|----------|-----|------|
| Application Metrics | `kp-application-metrics` | HTTP 요청 수, 응답 시간, 에러율 |
| Database Metrics | `kp-database-metrics` | DB 연결 풀, 쿼리 성능 |
| RAG & SLA Dashboard | `kp-rag-sla` | RAG 파이프라인 성능 |
| System Overview | `kp-system-overview` | 전체 시스템 리소스 |

**데이터 소스**: Prometheus (http://prometheus:9090), Loki (http://loki:3100)

**주요 PromQL 쿼리**:

```promql
# HTTP 요청 수 (분당)
sum(rate(http_server_requests_seconds_count[1m])) by (uri, method)

# HTTP 응답 시간 (95th percentile)
histogram_quantile(0.95, sum(rate(http_server_requests_seconds_bucket[5m])) by (le, uri))

# 에러율
sum(rate(http_server_requests_seconds_count{status=~"5.."}[5m]))
/ sum(rate(http_server_requests_seconds_count[5m])) * 100
```

### 5.2 Kibana (http://localhost:5601)

인증 없이 접속 가능합니다.

**주요 사용 메뉴**:
- **Analytics > Discover**: ES 데이터 검색 및 탐색
- **Management > Dev Tools**: ES 쿼리 콘솔

**Dev Tools 필수 쿼리**:

```json
// 클러스터 상태 (single-node: yellow이 정상)
GET _cluster/health

// 인덱스 목록
GET _cat/indices?v&s=index

// knowledge_chunks 인덱스 상태
GET knowledge_chunks/_stats

// 문서 수 확인
GET knowledge_chunks/_count

// Nori 분석기 동작 확인
POST knowledge_chunks/_analyze
{
  "field": "text",
  "text": "프로젝트관리시스템구축"
}
// 기대 결과: 4토큰 (프로젝트, 관리, 시스템, 구축)

// 키워드 검색 테스트
GET knowledge_chunks/_search
{
  "query": { "match": { "text": "프로젝트 관리" } },
  "size": 5
}
```

### 5.3 Prometheus (http://localhost:9090)

인증 없이 접속 가능합니다.

**주요 메뉴**:
- **Status > Targets**: 스크래핑 대상 상태 (UP/DOWN 확인)
- **Graph**: PromQL 쿼리 실행

**현재 Targets 상태**:

| 타겟 | 상태 | 비고 |
|------|------|------|
| prometheus | UP | Self-monitoring |
| api-gateway | UP | Spring Boot Actuator |
| backend | UP | Spring Boot Actuator |
| grafana | UP | |
| loki | UP | |
| jaeger | UP | |

```bash
# Targets API 조회
curl -s http://localhost:9090/api/v1/targets | python3 -m json.tool | head -30

# 메트릭 직접 조회
curl "http://localhost:9090/api/v1/query?query=up"
```

### 5.4 Jaeger (http://localhost:16686)

인증 없이 접속 가능합니다.

**트레이스 검색 방법**:
1. Service 드롭다운에서 서비스 선택
2. Operation 선택 (선택사항)
3. Lookback 시간 범위 설정
4. Find Traces 클릭

```bash
# 서비스 목록 조회
curl -s http://localhost:16686/api/services | python3 -m json.tool
```

---

## 6. ETL 파이프라인 운영

### 6.1 3-Phase 개요

```
Phase 1 (CPU) ──> Phase 2 (GPU) ──> Phase 3 (CPU)
 파싱+청킹           임베딩          엔티티 추출
 ES/PG/Neo4j      Dense+Sparse     Neo4j 관계 구축
```

| Phase | 환경 | 소요시간 | 핵심 작업 | 비용 |
|-------|------|---------|----------|------|
| Phase 1 | CPU (Docker) | ~6시간/1,786파일 | 파싱(Docling) + 청킹(1000/200) -> ES/PG/Neo4j | 0원 |
| Phase 2 | GPU (Colab T4) | 13.5분/53,414청크 | BGE-M3 Dense+Sparse 임베딩 | 0원 (Colab 무료) |
| Phase 3 | CPU (Docker) | ~43시간(3워커) | DeepSeek V3.2 엔티티 추출 -> Neo4j | ~$52 |

### 6.2 Phase 1 실행 (파싱+청킹)

```bash
# 1. ai-service 컨테이너 최신 빌드 (코드 변경 시 필수)
cd infrastructure/docker
docker compose build ai-service
docker compose up -d ai-service

# 2. Phase 1 실행 (nohup 필수 - 세션 종료 후에도 계속 실행)
docker exec kp-ai-service bash -c \
  "nohup python3 /app/scripts/run_etl_phase1_chunks.py > /tmp/etl_phase1.log 2>&1 &"

# 3. 진행 확인
docker exec kp-ai-service tail -20 /tmp/etl_phase1.log

# 4. 완료 확인
docker exec kp-ai-service grep "Phase 1 Completed" /tmp/etl_phase1.log
```

**핵심 파라미터**:
- `chunk_size=1000` (토큰)
- `chunk_overlap=200`
- `batch_size=4` (CPU 최적값, 8은 역효과)
- `enable_embeddings=False` (Phase 2에서 처리)
- `enable_entity_extraction=False` (Phase 3에서 처리)

### 6.3 Phase 2 실행 (GPU 임베딩)

GPU가 없는 환경에서는 Google Colab 무료 T4 GPU를 활용합니다.

```bash
# 1. ES에서 pending 청크 추출 (호스트에서)
python3 knowledge_service/scripts/export_chunks_for_gpu.py

# 2. Colab에서 BGE-M3 임베딩 실행
# -> Dense(1024차원) + Sparse 벡터 생성

# 3. 임베딩 결과 ES로 임포트
python3 knowledge_service/scripts/import_embeddings.py
```

### 6.4 Phase 3 실행 (엔티티 추출)

```bash
# 1. Phase 3 실행 (nohup 필수)
docker exec kp-ai-service bash -c \
  "nohup python3 /app/scripts/run_etl_phase3_entities.py > /tmp/etl_phase3.log 2>&1 &"

# 2. 진행 확인
docker exec kp-ai-service tail -20 /tmp/etl_phase3.log

# 3. Neo4j에서 엔티티 확인
docker exec kp-neo4j cypher-shell -u neo4j -p 'neo4j_dev_2026!' \
  "MATCH (n) RETURN labels(n) AS label, count(n) AS cnt ORDER BY cnt DESC;"
```

**비용**: DeepSeek V3.2 API 호출 약 $52 (23,074건 기준)

### 6.5 모니터링 스크립트

```bash
# Phase 1 모니터 (15분 간격, Slack dev 채널 보고)
nohup bash knowledge_service/scripts/etl_phase1_monitor.sh > /tmp/etl_phase1_monitor.log 2>&1 &

# 임베딩 전용 모니터
nohup bash knowledge_service/scripts/embedding_monitor.sh > /tmp/embedding_monitor.log 2>&1 &

# 모니터 프로세스 확인
ps aux | grep "etl.*monitor\|embedding.*monitor" | grep -v grep

# 모니터 종료
kill <PID>
```

---

## 7. 장애 대응

### 7.1 컨테이너 재시작

```bash
# 특정 서비스 재시작
docker compose restart ai-service

# 재시작 후 헬스체크 확인
docker inspect --format='{{.State.Health.Status}}' kp-ai-service

# 빌드 후 재시작 (코드 변경 반영)
docker compose up -d --build ai-service
```

### 7.2 검색 0건 반환 시

검색 API가 결과 0건을 반환하는 경우의 대응 절차:

```bash
# 1단계: ES에 데이터가 있는지 직접 확인
curl -s "http://localhost:9200/knowledge_chunks/_count" | python3 -m json.tool

# 2단계: ES 직접 검색 테스트
curl -s -X POST "http://localhost:9200/knowledge_chunks/_search" \
  -H "Content-Type: application/json" \
  -d '{"query":{"match":{"text":"프로젝트 관리"}},"size":3}' | python3 -m json.tool

# 3단계: Redis 캐시 플러시
docker exec kp-redis redis-cli FLUSHALL

# 4단계: ai-service 재시작
docker compose restart ai-service

# 5단계: 60초 대기 후 검색 재시도
sleep 60
# JWT 로그인 후 검색 API 호출
```

### 7.3 ES 인덱스 문제

```bash
# 클러스터 상태 확인 (single-node: yellow이 정상)
curl -s http://localhost:9200/_cluster/health?pretty

# 인덱스 목록 및 크기
curl -s "http://localhost:9200/_cat/indices?v&s=index"

# 인덱스 매핑 확인 (text 필드의 analyzer가 korean_analyzer인지)
curl -s "http://localhost:9200/knowledge_chunks/_mapping" | python3 -m json.tool | head -50

# Nori 분석기 동작 확인
curl -s -X POST "http://localhost:9200/knowledge_chunks/_analyze" \
  -H "Content-Type: application/json" \
  -d '{"field":"text","text":"프로젝트관리시스템구축"}' | python3 -m json.tool
# 기대: 4토큰 (프로젝트, 관리, 시스템, 구축)
# 1토큰이면 Nori 미적용 상태 -> Reindex 필요
```

### 7.4 메모리 부족 (WSL2)

```bash
# 1. 시스템 메모리 확인
free -h

# 2. 컨테이너별 메모리 사용량
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}" | grep kp-

# 3. OOM 여부 확인
docker inspect --format='{{.State.OOMKilled}}' kp-ai-service

# 4. 불필요한 서비스 중지 (서비스 운영에 영향 없음)
docker compose stop grafana kibana jaeger promtail loki

# 5. WSL2 메모리 제한 증가 (Windows %USERPROFILE%/.wslconfig)
# [wsl2]
# memory=16GB
# swap=4GB
```

### 7.5 ai-service 모델 로드 실패

BGE-M3 또는 BGE-Reranker 모델 로드 실패 시:

```bash
# 1. 로그에서 에러 확인
docker compose logs --tail=50 ai-service | grep -i "error\|model\|load"

# 2. HuggingFace 캐시 디렉토리 확인
docker exec kp-ai-service ls -la /root/.cache/huggingface/hub/

# 3. 컨테이너 재시작 (모델 재다운로드)
docker compose restart ai-service

# 4. 재시작 후 모델 로드 대기 (2-3분 소요)
sleep 180
curl -s http://localhost:8000/api/v1/health | python3 -m json.tool
```

### 7.6 Exit Code 해석

| Exit Code | 의미 | 대응 |
|:---------:|------|------|
| 0 | 정상 종료 | - |
| 1 | 애플리케이션 에러 | 로그 확인 |
| 127 | Command Not Found | Dockerfile 확인, 재빌드 |
| 137 | OOM Kill | 메모리 증가 (7.4 참조) |
| 143 | SIGTERM | 정상 종료 신호, 재시작 정책 확인 |

---

## 8. 백업/복구

### 8.1 PostgreSQL

```bash
# 백업
docker exec kp-postgresql pg_dump -U knowledge -d knowledge > backup_pg_$(date +%Y%m%d).sql

# 복구
docker exec -i kp-postgresql psql -U knowledge -d knowledge < backup_pg_20260218.sql

# 특정 테이블 백업
docker exec kp-postgresql pg_dump -U knowledge -d knowledge -t documents > backup_documents.sql
```

**주요 백업 대상 테이블**:
- `documents`: 문서 메타데이터 (1,437건)
- `users`: 사용자 정보
- `sessions`: 세션 데이터

### 8.2 Elasticsearch

```bash
# 스냅샷 저장소 등록 (최초 1회)
curl -X PUT "http://localhost:9200/_snapshot/backup_repo" \
  -H "Content-Type: application/json" \
  -d '{"type":"fs","settings":{"location":"/usr/share/elasticsearch/data/backups"}}'

# 스냅샷 생성
curl -X PUT "http://localhost:9200/_snapshot/backup_repo/snapshot_$(date +%Y%m%d)?wait_for_completion=true"

# 스냅샷 목록 확인
curl -s "http://localhost:9200/_snapshot/backup_repo/_all?pretty"

# 스냅샷 복구
curl -X POST "http://localhost:9200/_snapshot/backup_repo/snapshot_20260218/_restore"
```

**대안: 인덱스 데이터 파일 직접 복사**:

```bash
# ES 데이터 볼륨 위치 확인
docker volume inspect kp-elasticsearch-data

# Docker 볼륨 백업
docker run --rm -v kp-elasticsearch-data:/data -v $(pwd):/backup \
  alpine tar czf /backup/es_backup_$(date +%Y%m%d).tar.gz /data
```

### 8.3 Neo4j

```bash
# 데이터베이스 덤프 (컨테이너 중지 후)
docker compose stop neo4j
docker exec kp-neo4j neo4j-admin database dump neo4j --to-path=/tmp/
docker cp kp-neo4j:/tmp/neo4j.dump ./backup_neo4j_$(date +%Y%m%d).dump
docker compose start neo4j

# 복구
docker compose stop neo4j
docker cp backup_neo4j_20260218.dump kp-neo4j:/tmp/neo4j.dump
docker exec kp-neo4j neo4j-admin database load neo4j --from-path=/tmp/ --overwrite-destination=true
docker compose start neo4j
```

### 8.4 중요 볼륨 목록

| 볼륨명 | 설명 | 백업 주기 |
|--------|------|----------|
| `kp-postgresql-data` | 메인 DB (SSOT) | 일일 |
| `kp-elasticsearch-data` | 벡터/텍스트 인덱스 | 주간 |
| `kp-neo4j-data` | Knowledge Graph | 주간 |
| `kp-keycloak-db-data` | Keycloak 인증 DB | 주간 |
| `kp-minio-data` | 업로드된 원본 문서 | 일일 |

> `docker volume prune`은 중지된 컨테이너의 볼륨도 삭제할 수 있습니다. 실행 전 반드시 `docker volume ls`로 대상을 확인하세요.

---

## 9. 주요 설정 파일

### 9.1 파일 목록

| 파일 | 위치 | 설명 |
|------|------|------|
| `docker-compose.yml` | `infrastructure/docker/` | 18개 컨테이너 정의 (메인) |
| `docker-compose.wsl2.yml` | `infrastructure/docker/` | WSL2 오버라이드 |
| `docker-compose.prod.yml` | `infrastructure/docker/` | 프로덕션 오버라이드 |
| `.env` | `infrastructure/docker/` | 환경변수 (비밀번호, 포트, API 키) |
| `nginx.conf` | `infrastructure/docker/nginx/` | Nginx 리버스 프록시 설정 |
| `default.conf` | `infrastructure/docker/nginx/conf.d/` | Nginx 서버 블록 (타임아웃 포함) |
| `prometheus.yml` | `infrastructure/docker/prometheus/` | Prometheus 스크래핑 설정 |
| `config.py` | `knowledge_service/src/app/core/` | AI Service 핵심 설정 |
| `es_storage.py` | `knowledge_service/src/app/services/` | ES 인덱스 매핑 정의 |
| `application.yml` | `knowledge_service/gateway/src/main/resources/` | Spring Cloud Gateway 설정 |

### 9.2 .env 파일 주요 항목

| 변수 | 값 | 설명 |
|------|-----|------|
| `COMPOSE_PROJECT_NAME` | knowledge-platform | Docker Compose 프로젝트명 |
| `DB_NAME` / `DB_USERNAME` / `DB_PASSWORD` | knowledge / knowledge / knowledge_dev_2026! | 메인 PostgreSQL |
| `NEO4J_USER` / `NEO4J_PASSWORD` | neo4j / neo4j_dev_2026! | Neo4j |
| `DEEPSEEK_API_KEY` | sk-7c3024... | DeepSeek LLM API 키 |
| `KEYCLOAK_ADMIN` / `KEYCLOAK_ADMIN_PASSWORD` | admin / keycloak_admin_2026! | Keycloak 관리자 |
| `GRAFANA_ADMIN_PASSWORD` | test1234 | Grafana 관리자 |

### 9.3 Docker 네트워크 구성

| 네트워크 | 연결된 서비스 |
|----------|-------------|
| kp-frontend | nginx, frontend, api-gateway, keycloak, grafana |
| kp-backend | api-gateway, backend, ai-service, prometheus, jaeger |
| kp-database | api-gateway, backend, ai-service, keycloak, keycloak-db, postgresql, neo4j, elasticsearch, kibana, redis, minio |
| kp-monitoring | prometheus, grafana, loki, promtail, jaeger, kibana |

### 9.4 Admin UI "System Settings"와 실제 설정의 관계

> **주의**: Admin 페이지의 System Settings는 실제 AI Service 동작에 영향을 주지 않습니다.

| 구분 | Admin UI (System Settings) | AI Service (실제 동작) |
|------|:--------------------------:|:---------------------:|
| **저장소** | PostgreSQL `system_config` 테이블 | `config.py` + 환경변수 (`.env`) |
| **관리 주체** | Spring Boot Backend | Python FastAPI |
| **설정 변경 방법** | Admin UI에서 Save | `.env` 수정 + 컨테이너 재빌드 |
| **실제 영향** | 없음 (표시용) | 실제 파이프라인에 적용됨 |

**현재 설정값 (config.py 기준)**:

| 항목 | 값 | 설명 |
|------|:--:|------|
| `chunk_size` | 600 | 청크 크기 (토큰) |
| `chunk_overlap` | 100 | 청크 오버랩 (토큰) |
| `embedding_model` | BAAI/bge-m3 | BGE-M3 임베딩 모델 |
| `embedding_dimension` | 1024 | 임베딩 벡터 차원 |
| `elasticsearch_index` | knowledge_chunks | ES 인덱스명 (Nori 적용) |
| `docling_parse_timeout` | 1200.0 | PDF 파싱 타임아웃 (초) |

**설정 변경이 필요한 경우**:

```bash
# 1. .env 또는 config.py 수정
# 2. 컨테이너 재빌드
cd infrastructure/docker
docker compose build --no-cache ai-service
docker compose up -d ai-service

# 3. 60초 대기 후 헬스체크
sleep 60
curl -s http://localhost:8000/api/v1/health | python3 -m json.tool
```

### 9.5 Quick Reference 명령어

```
=======================================================================
  Knowledge Platform - 운영자 Quick Reference
=======================================================================

--- 시작/종료 ---
docker compose up -d                        # 전체 시작
docker compose down                         # 전체 종료
bash scripts/startup_check.sh --skip-compose # 점검만

--- 상태 확인 ---
docker compose ps                           # 서비스 상태
docker stats --no-stream | grep kp-         # 리소스 사용량
curl localhost:8000/api/v1/health           # ai-service 상태

--- 로그 ---
docker compose logs --tail=100 ai-service   # 최근 로그
docker compose logs -f ai-service           # 실시간 로그

--- 긴급 대응 ---
docker compose restart ai-service           # 서비스 재시작
docker exec kp-redis redis-cli FLUSHALL     # 캐시 초기화

--- 캐시 관리 (API) ---
curl -s GET localhost:8000/api/v1/cache/stats -H "Authorization: Bearer $TOKEN"
curl -s -X DELETE localhost:8000/api/v1/cache/clear -H "Authorization: Bearer $TOKEN"

--- 백업 ---
docker exec kp-postgresql pg_dump -U knowledge -d knowledge > backup.sql

--- 디스크 ---
docker system df                            # Docker 디스크 사용량
docker system prune -f                      # 안전한 정리

=======================================================================
  작업 디렉토리: infrastructure/docker/
  환경 변수: infrastructure/docker/.env
=======================================================================
```

---

## 10. 타임아웃 설정 가이드

### 10.1 End-to-End 타임아웃 체인

대용량 PDF 파싱이나 임베딩 등 장시간 요청이 정상 처리되려면, 요청 경로상의 모든 레이어에서 타임아웃이 충분히 설정되어 있어야 합니다.

```
Browser ──> Nginx ──> Spring Cloud Gateway ──> AI Service (FastAPI)
                                                      |
                                                  Docling 파싱
```

### 10.2 현재 타임아웃 설정

| 레이어 | 설정 항목 | 현재 값 | 설정 파일 |
|--------|----------|:-------:|----------|
| **Frontend (Vite dev proxy)** | server.proxy timeout | (Vite 기본값) | `frontend/vite.config.ts` |
| **Nginx** (일반 API) | `proxy_read_timeout` | **1,200초** | `nginx/conf.d/default.conf` |
| **Nginx** (검색) | `proxy_read_timeout` | 120초 | `nginx/conf.d/default.conf` |
| **Nginx** (업로드) | `proxy_read_timeout` | **1,200초** | `nginx/conf.d/default.conf` |
| **Nginx** (WebSocket) | `proxy_read_timeout` | 3,600초 | `nginx/conf.d/default.conf` |
| **Spring Cloud Gateway** | Resilience4j TimeLimiter (AI) | **60초** | `application.yml` |
| **Spring Cloud Gateway** | Resilience4j TimeLimiter (Backend) | 30초 | `application.yml` |
| **AI Service** | `docling_parse_timeout` | **1,200초** | `config.py` |
| **AI Service** | `llm_timeout` | 60초 | `config.py` |

### 10.3 주의: Spring Cloud Gateway 병목

> Spring Cloud Gateway의 Resilience4j TimeLimiter가 AI Service 경유 요청에 대해 **60초**로 설정되어 있습니다. Nginx(1,200초)와 AI Service(1,200초)에 비해 상대적으로 짧아서, 대용량 PDF 업로드 후 파싱 등 장시간 작업에서 Gateway 타임아웃이 먼저 발생할 수 있습니다.

**영향 범위**: 문서 업로드 후 파싱이 60초를 초과하는 경우, Gateway에서 503 응답 반환.

**임시 대응**: 대용량 문서 처리 시 AI Service API(`localhost:8000`)를 직접 호출하여 Gateway를 우회할 수 있습니다.

**영구 해결 (권장)**: `application.yml`에서 AI Service용 TimeLimiter 타임아웃을 증가시킵니다.

```yaml
# application.yml - resilience4j.timelimiter.instances
ai-service-circuit-breaker:
  timeout-duration: 1200s   # 현재 60s -> 1200s 증가 권장
```

### 10.4 타임아웃 수정 방법

```bash
# Nginx 타임아웃 변경
# 1. infrastructure/docker/nginx/conf.d/default.conf 수정
# 2. Nginx 재시작
docker compose restart nginx

# AI Service 타임아웃 변경
# 1. knowledge_service/src/app/core/config.py 수정
# 2. 컨테이너 재빌드
docker compose build --no-cache ai-service
docker compose up -d ai-service

# Gateway 타임아웃 변경
# 1. knowledge_service/gateway/src/main/resources/application.yml 수정
# 2. 컨테이너 재빌드
docker compose build --no-cache api-gateway
docker compose up -d api-gateway
```

---

*작성: Claude Code (Opus 4.6) | 2026-02-19*
