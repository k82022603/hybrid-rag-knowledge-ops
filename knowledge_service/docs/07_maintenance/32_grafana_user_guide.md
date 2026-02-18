# Grafana 사용자 가이드

**Version**: 1.0 | **Updated**: 2026-02-18

---

## 목차

1. [개요](#1-개요)
2. [접속 및 초기 설정](#2-접속-및-초기-설정)
3. [대시보드 개요](#3-대시보드-개요)
4. [System Overview 대시보드](#4-system-overview-대시보드)
5. [Application Metrics 대시보드](#5-application-metrics-대시보드)
6. [Database Metrics 대시보드](#6-database-metrics-대시보드)
7. [RAG & SLA Dashboard](#7-rag--sla-dashboard)
8. [데이터소스 구성](#8-데이터소스-구성)
9. [자주 쓰는 기능](#9-자주-쓰는-기능)
10. [트러블슈팅](#10-트러블슈팅)
11. [참고](#11-참고)

---

## 1. 개요

### 1.1 Grafana란?

Grafana는 여러 데이터소스의 메트릭을 통합 시각화하고 모니터링하는 오픈소스 대시보드 도구입니다.

### 1.2 프로젝트 내 역할

| 용도 | 설명 |
|------|------|
| 통합 모니터링 | Prometheus, Loki, Jaeger, Elasticsearch 데이터를 단일 UI로 통합 |
| 메트릭 시각화 | 시계열 그래프, 게이지, 상태 패널로 시스템 상태 파악 |
| SLA 관리 | 가용성, 응답 시간, 에러 버짓 추적 |
| 알림 관리 | 임계값 기반 알림 및 AlertManager 연동 |

### 1.3 기술 스택

| 항목 | 값 |
|------|---|
| Grafana | 10.2.0 |
| 컨테이너명 | kp-grafana |
| 외부 포트 | 3001 |
| 내부 포트 | 3000 |
| 설치 플러그인 | grafana-clock-panel, grafana-simple-json-datasource |

### 1.4 Grafana vs Kibana

프로젝트에서 Grafana와 Kibana는 서로 다른 목적으로 사용됩니다.

| 기능 | Grafana | Kibana |
|------|---------|--------|
| **주요 용도** | 통합 모니터링 대시보드 | Elasticsearch 데이터 탐색 |
| **데이터소스** | Prometheus, Loki, Jaeger, ES 등 다수 | Elasticsearch 전용 |
| **적합한 작업** | SLA 추적, 리소스 모니터링, 알림 | 벡터 검색 디버깅, 인덱스 매핑 확인 |
| **쿼리 언어** | PromQL, LogQL | ES DSL, KQL |
| **접속 URL** | http://localhost:3001 | http://localhost:5601 |

---

## 2. 접속 및 초기 설정

### 2.1 Grafana 접속

**URL**: http://localhost:3001

**계정 정보**:

| 항목 | 값 |
|------|---|
| 사용자명 | admin |
| 비밀번호 | test1234 |

### 2.2 컨테이너 상태 확인

```bash
# 컨테이너 상태 확인
docker ps --filter name=kp-grafana --format "table {{.Names}}\t{{.Status}}"

# 헬스체크 상태
docker inspect --format='{{.State.Health.Status}}' kp-grafana

# 로그 확인
docker logs kp-grafana --tail 20
```

### 2.3 API를 통한 상태 확인

```bash
# Grafana Health
curl -s http://localhost:3001/api/health

# 대시보드 목록
curl -s -u admin:test1234 http://localhost:3001/api/search?type=dash-db | python3 -m json.tool

# 데이터소스 목록
curl -s -u admin:test1234 http://localhost:3001/api/datasources | python3 -m json.tool
```

---

## 3. 대시보드 개요

프로젝트에는 4개의 프로비저닝된 대시보드가 포함되어 있습니다. 대시보드 파일은 `infrastructure/docker/grafana/dashboards/` 에 JSON 형태로 관리됩니다.

| UID | 대시보드명 | 주요 모니터링 대상 | 용도 |
|-----|----------|------------------|------|
| `kp-system-overview` | System Overview | 전체 서비스 상태, 리소스 사용량 | 시스템 전반 건강 상태 한눈에 확인 |
| `kp-application-metrics` | Application Metrics | 요청률, 에러율, 지연 시간, JVM | 애플리케이션 성능 상세 분석 |
| `kp-database-metrics` | Database Metrics | PG, ES, Neo4j, Redis | 데이터베이스 성능 및 상태 |
| `kp-rag-sla` | RAG & SLA Dashboard | SLA, RAG 파이프라인, LLM, 검색 품질 | RAG 서비스 품질 및 SLA 준수 여부 |

### 대시보드 접근 경로

1. 좌측 메뉴에서 **Dashboards** 클릭
2. **Knowledge Platform** 폴더 선택
3. 원하는 대시보드 클릭

또는 직접 URL로 접근:
```
http://localhost:3001/d/kp-system-overview
http://localhost:3001/d/kp-application-metrics
http://localhost:3001/d/kp-database-metrics
http://localhost:3001/d/kp-rag-sla
```

---

## 4. System Overview 대시보드

**URL**: http://localhost:3001/d/kp-system-overview

전체 시스템 상태를 한눈에 파악하기 위한 최상위 대시보드입니다. 매일 아침 점검 시 가장 먼저 확인합니다.

### 4.1 Service Health Status (Row)

7개 서비스의 UP/DOWN 상태를 Stat 패널로 표시합니다.

| 패널명 | 메트릭 | 설명 |
|--------|--------|------|
| Backend | `up{job="backend"}` | SpringBoot 백엔드 서비스 |
| AI Service | `up{job="ai-service"}` | FastAPI AI/RAG 서비스 |
| API Gateway | `up{job="api-gateway"}` | Spring Cloud Gateway |
| PostgreSQL | `up{job="postgresql"}` | 메인 RDBMS |
| Elasticsearch | `up{job="elasticsearch"}` | 벡터/키워드 검색 엔진 |
| Neo4j | `up{job="neo4j"}` | 지식 그래프 DB |
| Keycloak | `up{job="keycloak"}` | 인증/인가 서버 |
| Total Up | `count(up == 1)` | 전체 정상 서비스 수 |

**해석 방법**:
- 값이 **1**: 정상 (녹색)
- 값이 **0**: 비정상 (적색)
- **Total Up**: 전체 대상 중 몇 개가 정상인지 요약

### 4.2 Resource Usage (Row)

| 패널명 | 타입 | 메트릭 |
|--------|------|--------|
| CPU Usage by Service (%) | timeseries | `rate(process_cpu_seconds_total{job=~"backend\|ai-service\|api-gateway"}[5m]) * 100` |
| Memory Usage by Service | timeseries | `process_resident_memory_bytes{job=~"backend\|ai-service\|api-gateway"}` |

**확인 시점**: CPU가 지속적으로 80% 이상이거나, 메모리가 컨테이너 제한에 근접할 때 조치 필요.

### 4.3 Container Metrics (Row)

| 패널명 | 타입 | 메트릭 |
|--------|------|--------|
| Container Memory Usage | timeseries | `container_memory_usage_bytes{name=~"kp-.*"}` |
| Container Network I/O | timeseries | `rate(container_network_receive_bytes_total{name=~"kp-.*"}[5m])` (수신), `rate(container_network_transmit_bytes_total{name=~"kp-.*"}[5m])` (송신) |

**확인 시점**: `kp-` 접두사가 붙은 모든 컨테이너의 메모리 및 네트워크 트래픽 추이를 봅니다. 특정 컨테이너의 메모리가 급증하면 OOM 가능성을 점검합니다.

### 4.4 Active Alerts (Row)

| 패널명 | 타입 | 설명 |
|--------|------|------|
| Active Alerts | alertlist | 현재 발생 중인 알림 목록 표시 |

**확인 시점**: 알림이 있으면 심각도(Critical/Warning)를 확인하고 대응합니다.

---

## 5. Application Metrics 대시보드

**URL**: http://localhost:3001/d/kp-application-metrics

애플리케이션 계층의 성능을 상세 분석하는 대시보드입니다. API 성능 이슈 진단 시 사용합니다.

### 5.1 Request Metrics (Row)

| 패널명 | 타입 | 메트릭 | 설명 |
|--------|------|--------|------|
| Request Rate by Service | timeseries | `sum(rate(http_server_requests_seconds_count{job=~"backend\|ai-service\|api-gateway"}[1m])) by (job)` | 서비스별 초당 요청 수 |
| Backend Error Rate | stat | `(sum(rate(...{status=~"5..", job="backend"}[5m])) / sum(rate(...{job="backend"}[5m]))) * 100` | Backend 5xx 에러율 (%) |
| AI Service Error Rate | stat | 위와 동일 (job="ai-service") | AI Service 5xx 에러율 (%) |
| Backend P95 Latency | stat | `histogram_quantile(0.95, rate(...{job="backend"}[5m])) * 1000` | Backend P95 지연 시간 (ms) |
| AI Service P95 Latency | stat | 위와 동일 (job="ai-service") | AI Service P95 지연 시간 (ms) |

**해석 방법**:
- Error Rate가 1% 이상이면 주의, 5% 이상이면 즉시 조사
- P95 Latency가 500ms를 초과하면 성능 병목 확인

### 5.2 Latency Distribution (Row)

| 패널명 | 타입 | 설명 |
|--------|------|------|
| Backend Latency Percentiles | timeseries | P50, P95, P99 세 가지 라인으로 시간 추이 표시 |
| AI Service Latency Percentiles | timeseries | P50, P95, P99 세 가지 라인으로 시간 추이 표시 |

**해석 방법**:
- P50 (중간값): 일반적인 응답 시간
- P95: 95%의 요청이 이 시간 이내에 완료
- P99: 꼬리 지연 시간 (tail latency)
- P99가 P50의 10배 이상이면 간헐적 지연 원인 조사 필요

### 5.3 Circuit Breaker Status (Row)

Backend에서 AI Service 호출 시 사용하는 Resilience4j Circuit Breaker 상태를 모니터링합니다.

| 패널명 | 타입 | 메트릭 | 설명 |
|--------|------|--------|------|
| AI Service Circuit Breaker | stat | `resilience4j_circuitbreaker_state{name="aiService"}` | 현재 CB 상태 |
| CB Failure Rate | stat | `resilience4j_circuitbreaker_failure_rate{name="aiService"}` | 실패율 (%) |
| Circuit Breaker Calls | timeseries | `rate(resilience4j_circuitbreaker_calls_total{name="aiService", kind="successful\|failed"}[5m])` | 성공/실패 호출률 |

**Circuit Breaker 상태값**:

| 값 | 상태 | 의미 |
|----|------|------|
| 0 | CLOSED | 정상 (모든 요청 통과) |
| 1 | OPEN | 차단 (Fallback 응답 중, AI Service 장애) |
| 2 | HALF_OPEN | 복구 시도 중 (일부 요청만 통과) |

**확인 시점**: CB가 OPEN 상태이면 AI Service 장애를 의미합니다. AI Service 컨테이너 상태와 로그를 즉시 확인해야 합니다.

### 5.4 HTTP Status Distribution (Row)

| 패널명 | 타입 | 설명 |
|--------|------|------|
| HTTP Status Code Distribution | timeseries | 2xx, 3xx, 4xx, 5xx 상태 코드별 요청률 |

**해석 방법**:
- 2xx가 대부분이어야 정상
- 4xx 급증: 클라이언트 측 잘못된 요청 (API 변경, 인증 만료 등)
- 5xx 급증: 서버 내부 오류 (즉시 조사 필요)

### 5.5 JVM Metrics - Backend (Row)

| 패널명 | 타입 | 메트릭 | 설명 |
|--------|------|--------|------|
| JVM Heap Memory | timeseries | `jvm_memory_used_bytes` / `jvm_memory_max_bytes` (area="heap") | 힙 메모리 사용량 vs 최대값 |
| JVM Threads | timeseries | `jvm_threads_live_threads`, `daemon_threads`, `peak_threads` | 스레드 상태 추이 |

**확인 시점**:
- Used가 Max에 근접하면 GC 부하 증가, OOM 위험
- Thread peak가 지속적으로 상승하면 스레드 누수 의심

---

## 6. Database Metrics 대시보드

**URL**: http://localhost:3001/d/kp-database-metrics

4개 데이터베이스(PostgreSQL, Elasticsearch, Neo4j, Redis)의 상태와 성능을 모니터링합니다.

### 6.1 Database Health Overview (Row)

| 패널명 | 메트릭 | 설명 |
|--------|--------|------|
| PostgreSQL | `up{job="postgresql"}` | PG 연결 상태 |
| Elasticsearch | `up{job="elasticsearch"}` | ES 연결 상태 |
| Neo4j | `up{job="neo4j"}` | Neo4j 연결 상태 |
| Redis | `up{job="redis"}` | Redis 연결 상태 |

### 6.2 Elasticsearch Metrics (Row)

| 패널명 | 타입 | 메트릭 | 설명 |
|--------|------|--------|------|
| ES Cluster Health | stat | `elasticsearch_cluster_health_status` | 클러스터 상태 (green/yellow/red) |
| ES Total Documents | stat | `elasticsearch_indices_docs_total` | 전체 문서 수 |
| ES Store Size | stat | `elasticsearch_indices_store_size_bytes_total` | 인덱스 저장 크기 |
| ES Query Rate | timeseries | `rate(elasticsearch_indices_search_query_total[5m])`, `rate(elasticsearch_indices_indexing_index_total[5m])` | 검색/인덱싱 요청률 |
| ES JVM Memory | timeseries | `elasticsearch_jvm_memory_used_bytes`, `elasticsearch_jvm_memory_max_bytes` | ES JVM 메모리 |

**해석 방법**:
- Cluster Health가 **red**이면 샤드 할당 실패, 즉시 확인
- **yellow**은 단일 노드 환경에서는 정상 (replica 없음)
- Store Size가 급증하면 디스크 용량 점검

### 6.3 Redis Metrics (Row)

| 패널명 | 타입 | 메트릭 | 설명 |
|--------|------|--------|------|
| Redis Memory Usage | stat | `(redis_memory_used_bytes / redis_memory_max_bytes) * 100` | 메모리 사용률 (%) |
| Redis Connected Clients | stat | `redis_connected_clients` | 연결된 클라이언트 수 |
| Redis Keys | stat | `redis_db_keys` | 저장된 키 수 |
| Redis Commands Rate | timeseries | `rate(redis_commands_processed_total[5m])` | 초당 명령 처리율 |
| Redis Cache Hit Rate | timeseries | `(hits / (hits + misses)) * 100` | 캐시 적중률 (%) |

**해석 방법**:
- Cache Hit Rate가 80% 미만이면 캐시 키 설계 검토 필요
- Memory Usage가 90% 이상이면 eviction 발생 가능

### 6.4 Neo4j Metrics (Row)

| 패널명 | 타입 | 메트릭 | 설명 |
|--------|------|--------|------|
| Neo4j Graph Size | timeseries | `neo4j_database_count_node`, `neo4j_database_count_relationship` | 노드/관계 수 추이 |
| Neo4j Memory | timeseries | `neo4j_dbms_vm_heap_used`, `neo4j_dbms_page_cache_bytes_used` | 힙 및 페이지 캐시 사용량 |

**확인 시점**: ETL 이후 Graph Size가 예상대로 증가했는지 확인합니다.

---

## 7. RAG & SLA Dashboard

**URL**: http://localhost:3001/d/kp-rag-sla

RAG 파이프라인 성능과 SLA 준수 여부를 추적하는 핵심 대시보드입니다.

### 7.1 SLA Overview (Row)

| 패널명 | 타입 | 메트릭 | 설명 |
|--------|------|--------|------|
| Availability (24h) | stat | `(1 - (5xx / total)) * 100` [24h] | 최근 24시간 가용성 (%) |
| Availability (7d) | stat | 위와 동일 [7d] | 최근 7일 가용성 (%) |
| Error Budget (30d) | stat | `100 - (error_ratio / 0.001 * 100)` [30d] | 30일 에러 버짓 잔여량 (%) |
| Search Latency P95 | stat | `histogram_quantile(0.95, ...{uri=~"/api/v1/search.*"}[5m]) * 1000` | 검색 API P95 지연 (ms) |

**SLA 기준**:

| 지표 | 목표 | 임계값 |
|------|------|--------|
| 가용성 | 99.9% (월간) | 99.5% 미만 시 Critical |
| 검색 P95 | < 500ms | 1000ms 초과 시 Warning |
| 에러 버짓 | > 20% 잔여 | 20% 미만 시 Warning |

**해석 방법**:
- Error Budget이 0% 이하면 SLA를 이미 위반한 상태
- Availability가 99.9% 미만이면 근본 원인 분석 필요

### 7.2 SLA Trends (Row)

| 패널명 | 타입 | 설명 |
|--------|------|------|
| Availability Over Time (5m rolling) | timeseries | 5분 롤링 가용성 추이 |
| Search API Latency | timeseries | 검색 API P50/P95/P99 추이 |

**확인 시점**: 특정 시간대에 가용성 하락이 반복되면 해당 시간대 로그를 Loki에서 확인합니다.

### 7.3 RAG Pipeline Metrics (Row)

| 패널명 | 타입 | 메트릭 | 설명 |
|--------|------|--------|------|
| Search Requests by Type | timeseries | `sum(rate(ai_search_requests_total[5m])) by (search_type)` | 검색 유형별 요청률 (vector/graph/hybrid) |
| RAG Component Latency P95 | timeseries | embedding, vector_search, graph_search 각각의 `histogram_quantile(0.95, ...)` | RAG 컴포넌트별 P95 지연 시간 |
| Document Processing Queue | timeseries | `ai_active_processing_jobs` | 현재 문서 처리 대기열 크기 |

**해석 방법**:
- Component Latency에서 어느 컴포넌트가 병목인지 파악
  - embedding P95 높음: 임베딩 모델 또는 GPU 이슈
  - vector_search P95 높음: ES 검색 성능 이슈
  - graph_search P95 높음: Neo4j 쿼리 최적화 필요
- Processing Queue가 100건 이상이면 처리 지연 알림 발생

### 7.4 LLM Metrics (Row)

| 패널명 | 타입 | 메트릭 | 설명 |
|--------|------|--------|------|
| LLM Tokens (24h) | stat | `sum(increase(ai_llm_tokens_total[24h]))` | 24시간 토큰 사용량 |
| LLM Cost (24h) | stat | `sum(increase(ai_llm_cost_dollars[24h]))` | 24시간 API 비용 ($) |
| LLM Fallback Rate | stat | `(fallback / total) * 100` | Fallback 모델 사용 비율 (%) |
| LLM Latency P95 | stat | `histogram_quantile(0.95, rate(ai_llm_request_duration_seconds_bucket[5m]))` | LLM 호출 P95 (초) |
| Token Usage by Model | timeseries | input/output 토큰을 모델별로 분리 | 모델별 토큰 사용 추이 |
| LLM Response Time Distribution | timeseries | P50/P95/P99 | LLM 응답 시간 분포 |

**해석 방법**:
- Fallback Rate가 5% 이상이면 주 LLM(DeepSeek) 장애 가능성
- Cost가 예상보다 높으면 불필요한 호출이나 프롬프트 길이 점검
- Latency P95가 5초 이상이면 LLM API 서버 상태 확인

### 7.5 Search Quality (Row)

| 패널명 | 타입 | 메트릭 | 설명 |
|--------|------|--------|------|
| Search Relevance Score Distribution | histogram | `sum(rate(ai_search_relevance_score_bucket[1h])) by (le)` | 검색 결과 관련도 점수 분포 |
| Search Relevance Over Time | timeseries | P50, P10 | 관련도 점수 추이 |

**해석 방법**:
- P50 관련도가 0.7 이상이면 양호
- P10이 0.3 미만이면 검색 품질 개선 필요 (임베딩 재학습 또는 인덱스 튜닝)

---

## 8. 데이터소스 구성

프로비저닝을 통해 4개의 데이터소스가 자동으로 설정되어 있습니다.

### 8.1 데이터소스 목록

| ID | 이름 | 타입 | URL | 기본값 | 용도 |
|----|------|------|-----|--------|------|
| 1 | Prometheus | prometheus | http://prometheus:9090 | Yes | 메트릭 쿼리 (PromQL) |
| 2 | Loki | loki | http://loki:3100 | No | 로그 쿼리 (LogQL) |
| 3 | Jaeger | jaeger | http://jaeger:16686 | No | 분산 트레이싱 조회 |
| 4 | Elasticsearch | elasticsearch | http://elasticsearch:9200 | No | ES 데이터 분석 |

### 8.2 데이터소스별 용도

**Prometheus** (기본 데이터소스):
- 4개 대시보드 모두에서 사용
- 시스템 메트릭, 애플리케이션 메트릭, 비즈니스 메트릭 수집
- 15초 간격 스크래핑, POST 방식

**Loki**:
- 로그 탐색 (Explore 메뉴)
- LogQL 쿼리로 에러 로그 검색
- max_lines: 1000

**Jaeger**:
- 분산 트레이싱 조회 (Explore 메뉴)
- 서비스 간 요청 흐름 추적
- 병목 구간 식별

**Elasticsearch**:
- ES 8.11.0 설정
- @timestamp 기반 시간 필터링
- level/message 필드 매핑

### 8.3 프로비저닝 파일 위치

```
infrastructure/docker/grafana/
  provisioning/
    datasources/datasources.yml    # 데이터소스 정의
    dashboards/dashboards.yml      # 대시보드 프로비저닝
  dashboards/
    system-overview.json           # System Overview
    application-metrics.json       # Application Metrics
    database-metrics.json          # Database Metrics
    rag-sla-dashboard.json         # RAG & SLA
```

---

## 9. 자주 쓰는 기능

### 9.1 시간 범위 변경

대시보드 우측 상단의 시간 선택기를 사용합니다.

- **Quick ranges**: Last 5 minutes, Last 15 minutes, Last 1 hour, Last 6 hours, Last 24 hours
- **Custom range**: From/To 날짜/시간 직접 입력
- **실시간 모드**: 우측 상단 새로고침 아이콘 옆 드롭다운에서 `30s` 등 자동 새로고침 간격 설정

**자주 사용하는 범위**:
- 장애 진단: Last 1 hour
- 일일 점검: Last 24 hours
- SLA 리뷰: Last 7 days / Last 30 days

### 9.2 패널 확대 (Panel Zoom)

특정 패널을 자세히 보려면:
1. 패널 제목 클릭
2. **View** 선택 (또는 패널 제목 옆 확대 아이콘)
3. 전체 화면으로 패널 확대
4. ESC 키로 원래 대시보드로 복귀

### 9.3 쿼리 검사 (Inspect)

패널의 원본 데이터를 확인하려면:
1. 패널 제목 클릭
2. **Inspect** > **Data** 선택
3. 테이블 형태로 원본 시계열 데이터 확인
4. **Query** 탭에서 실제 실행된 PromQL 확인
5. CSV 다운로드 가능

### 9.4 Explore (데이터 탐색)

좌측 메뉴의 **Explore** 를 통해 자유로운 쿼리를 실행할 수 있습니다.

**PromQL 예시**:
```promql
# 서비스별 요청률 (최근 5분)
sum(rate(http_server_requests_seconds_count[5m])) by (job)

# 검색 API P95 응답 시간
histogram_quantile(0.95, rate(http_server_requests_seconds_bucket{uri=~"/api/v1/search.*"}[5m]))

# 현재 UP 상태인 서비스 수
count(up == 1)
```

**LogQL 예시** (데이터소스를 Loki로 변경):
```logql
# 최근 에러 로그
{service="backend", level="ERROR"} | json

# 특정 TraceId 추적
{service=~"backend|ai-service"} | json | traceId="<trace-id>"
```

### 9.5 Row 접기/펼치기

각 대시보드의 섹션(Row)은 접기/펼치기가 가능합니다:
- Row 헤더 좌측의 화살표를 클릭하여 토글
- 관심 없는 섹션을 접어두면 화면을 효율적으로 사용 가능

### 9.6 변수 필터링

일부 쿼리에서 `job` 레이블을 사용합니다. Explore에서 특정 서비스만 필터링하려면:
```promql
# backend만
http_server_requests_seconds_count{job="backend"}

# ai-service만
http_server_requests_seconds_count{job="ai-service"}
```

---

## 10. 트러블슈팅

### 10.1 "No Data" 표시

**증상**: 패널에 "No data" 또는 빈 그래프가 표시됨

**확인 순서**:

1. **시간 범위 확인**: 데이터가 있는 시간대인지 확인 (우측 상단 시간 선택기)
2. **Prometheus 타겟 확인**:
   ```bash
   curl -s http://localhost:9090/api/v1/targets | python3 -c "
   import sys,json
   data=json.load(sys.stdin)
   for t in data.get('data',{}).get('activeTargets',[]):
     print(f'{t[\"labels\"].get(\"job\",\"?\")}: {t[\"health\"]}')
   "
   ```
3. **서비스 상태 확인**: 해당 서비스 컨테이너가 실행 중인지 확인
   ```bash
   docker ps --filter name=kp- --format "table {{.Names}}\t{{.Status}}"
   ```
4. **Inspect 확인**: 패널 > Inspect > Query에서 에러 메시지 확인

**주요 원인별 대응**:

| 원인 | 해결 |
|------|------|
| 서비스가 DOWN | `docker compose up -d <service>` 로 컨테이너 시작 |
| Prometheus 타겟 DOWN | 서비스의 메트릭 엔드포인트 정상 여부 확인 |
| 메트릭 경로 불일치 | prometheus.yml의 `metrics_path` 확인 |
| 시간 범위 너무 짧음 | Last 1 hour 이상으로 범위 확대 |

### 10.2 Prometheus 타겟 DOWN 시 대응

**현재 타겟 상태 확인**:
- Prometheus UI: http://localhost:9090/targets
- 또는 위의 API 명령어 사용

**DOWN 상태 서비스 복구 절차**:

```bash
# 1. 컨테이너 상태 확인
docker ps -a --filter name=kp-<service>

# 2. 중지된 컨테이너 시작
cd /mnt/d/Users/KTDS/Documents/06.과제/hybrid-rag-knowledge-ops/infrastructure/docker
docker compose up -d <service>

# 3. 메트릭 엔드포인트 직접 확인
# Backend (Spring Actuator)
curl -s http://localhost:8081/actuator/prometheus | head -5

# AI Service (FastAPI)
curl -s http://localhost:8000/metrics | head -5

# 4. Prometheus 타겟 재확인 (1-2분 대기 후)
curl -s http://localhost:9090/api/v1/targets/metadata?match_target={job="<job_name>"} | head
```

### 10.3 데이터소스 연결 실패

**증상**: 대시보드에서 "Datasource error" 또는 "Bad gateway"

**확인 순서**:

1. **데이터소스 연결 테스트**:
   - Grafana > Configuration > Data Sources > 해당 데이터소스 > **Test** 버튼
2. **네트워크 확인**:
   ```bash
   # Grafana 컨테이너에서 데이터소스로 연결 가능한지
   docker exec kp-grafana wget -qO- http://prometheus:9090/-/healthy 2>&1
   docker exec kp-grafana wget -qO- http://loki:3100/ready 2>&1
   ```
3. **Docker 네트워크 확인**:
   ```bash
   docker network inspect docker_monitoring
   ```

### 10.4 대시보드 변경 사항이 저장되지 않음

프로비저닝된 대시보드는 `allowUiUpdates: true`로 설정되어 있어 UI에서 수정 가능하지만, 컨테이너 재시작 시 JSON 파일 기준으로 초기화됩니다.

**영구 변경이 필요한 경우**:
1. Grafana UI에서 수정 후 대시보드 JSON을 Export (Share > Export > Save to file)
2. 해당 JSON을 `infrastructure/docker/grafana/dashboards/` 에 덮어쓰기
3. 컨테이너 재시작 시에도 변경 사항이 유지됨

### 10.5 Grafana 접속 불가

**증상**: http://localhost:3001 접속 시 연결 거부

**진단 및 해결**:
```bash
# 컨테이너 상태
docker ps --filter name=kp-grafana

# 포트 확인
docker port kp-grafana

# 로그 확인 (권한 이슈가 잦음)
docker logs kp-grafana --tail 50

# 재시작
cd /mnt/d/Users/KTDS/Documents/06.과제/hybrid-rag-knowledge-ops/infrastructure/docker
docker compose restart grafana
```

### 10.6 비밀번호 분실

```bash
# Grafana admin 비밀번호 리셋
docker exec kp-grafana grafana-cli admin reset-admin-password <new-password>
```

---

## 11. 참고

### 11.1 Prometheus 타겟 현황

현재 Prometheus에 등록된 스크래핑 타겟 목록입니다 (prometheus.yml 기준).

| Job | 대상 | 메트릭 경로 | 간격 | 레이어 |
|-----|------|------------|------|--------|
| prometheus | localhost:9090 | /metrics | 15s | monitoring |
| alertmanager | alertmanager:9093 | /metrics | 15s | monitoring |
| api-gateway | api-gateway:8080 | /actuator/prometheus | 15s | application |
| backend | backend:8081 | /actuator/prometheus | 15s | application |
| ai-service | ai-service:8000 | /metrics | 15s | application |
| frontend | frontend:80 | /stub_status | 30s | application |
| keycloak | keycloak:8080 | /metrics | 30s | auth |
| elasticsearch | elasticsearch:9200 | /_prometheus/metrics | 30s | database |
| neo4j | neo4j:2004 | /metrics | 30s | database |
| loki | loki:3100 | /metrics | 15s | monitoring |
| jaeger | jaeger:14269 | /metrics | 15s | monitoring |
| grafana | grafana:3000 | /metrics | 15s | monitoring |

> **참고**: PostgreSQL exporter, Redis exporter, Nginx exporter는 현재 비활성화(주석 처리) 상태입니다. 해당 exporter 컨테이너 추가 시 prometheus.yml에서 주석을 해제하면 됩니다.

### 11.2 관련 파일

| 파일 | 설명 |
|------|------|
| `infrastructure/docker/docker-compose.yml` | Grafana 컨테이너 설정 |
| `infrastructure/docker/.env` | GRAFANA_PORT, GRAFANA_ADMIN_PASSWORD 환경 변수 |
| `infrastructure/docker/grafana/provisioning/datasources/datasources.yml` | 데이터소스 프로비저닝 |
| `infrastructure/docker/grafana/provisioning/dashboards/dashboards.yml` | 대시보드 프로비저닝 |
| `infrastructure/docker/grafana/dashboards/*.json` | 대시보드 JSON 파일 (4개) |
| `infrastructure/docker/prometheus/prometheus.yml` | Prometheus 스크래핑 설정 |
| `infrastructure/docker/prometheus/rules/alert-rules.yml` | 알림 규칙 |

### 11.3 관련 문서

| 문서 | 위치 |
|------|------|
| Observability 상세 설계서 | `docs/02_design/14_observability_detailed_design.md` |
| Kibana 사용자 가이드 | `docs/07_maintenance/02_kibana_user_guide.md` |
| 인프라 설계서 | `docs/02_design/10_infrastructure_detailed_design.md` |
| 에러 코드 표준 | `docs/02_design/error_code_standards.md` |

### 11.4 참고 링크

- [Grafana 공식 문서](https://grafana.com/docs/grafana/latest/)
- [PromQL 문서](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [LogQL 문서](https://grafana.com/docs/loki/latest/logql/)
- [Grafana Provisioning 가이드](https://grafana.com/docs/grafana/latest/administration/provisioning/)

---

## 변경 이력

| 날짜 | 버전 | 변경 내용 |
|------|------|----------|
| 2026-02-18 | 1.0 | 초기 문서 작성 (4개 대시보드 상세, 데이터소스, 트러블슈팅) |
