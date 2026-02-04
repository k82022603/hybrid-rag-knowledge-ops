# Observability 운영자 매뉴얼

**Version**: 1.0 | **Created**: 2026-02-04 | **Author**: DevOps Team

---

## 목차

1. [개요](#1-개요)
2. [아키텍처](#2-아키텍처)
3. [접속 정보](#3-접속-정보)
4. [Grafana 운영](#4-grafana-운영)
5. [Prometheus 운영](#5-prometheus-운영)
6. [Kibana & Elasticsearch 운영](#6-kibana--elasticsearch-운영)
7. [Jaeger 운영](#7-jaeger-운영)
8. [Loki & Promtail 운영](#8-loki--promtail-운영)
9. [알림 설정](#9-알림-설정)
10. [일상 운영 체크리스트](#10-일상-운영-체크리스트)
11. [장애 대응 가이드](#11-장애-대응-가이드)
12. [트러블슈팅](#12-트러블슈팅)

---

## 1. 개요

### 1.1 Observability란?

Observability(관측 가능성)는 시스템의 내부 상태를 외부에서 측정 가능한 출력을 통해 이해하는 능력입니다.

**3대 핵심 요소 (Three Pillars):**

| 요소 | 설명 | 도구 |
|------|------|------|
| **Metrics** | 숫자 기반 측정값 (CPU, Memory, Request Rate) | Prometheus + Grafana |
| **Logs** | 이벤트 기록 (에러, 경고, 정보) | Loki/Elasticsearch + Kibana |
| **Traces** | 분산 요청 추적 (서비스 간 호출 경로) | Jaeger |

### 1.2 시스템 구성

```
Knowledge Platform Observability Stack
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌─────────────────────────────────────────────────────────┐
│                    Visualization Layer                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │   Grafana   │  │   Kibana    │  │   Jaeger    │     │
│  │  (Metrics)  │  │   (Logs)    │  │  (Traces)   │     │
│  │  :3001      │  │   :5601     │  │  :16686     │     │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘     │
└─────────┼────────────────┼────────────────┼─────────────┘
          │                │                │
┌─────────┼────────────────┼────────────────┼─────────────┐
│         │     Storage & Query Layer       │             │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐     │
│  │ Prometheus  │  │Elasticsearch│  │   Jaeger    │     │
│  │  (TSDB)     │  │  (Index)    │  │  (Storage)  │     │
│  │  :9090      │  │   :9200     │  │  (in-mem)   │     │
│  └──────┬──────┘  └──────┬──────┘  └─────────────┘     │
│         │                │                              │
│  ┌──────▼──────┐  ┌──────▼──────┐                      │
│  │    Loki     │  │  Promtail   │                      │
│  │ (Log Store) │  │(Log Shipper)│                      │
│  │  :3100      │  │             │                      │
│  └─────────────┘  └─────────────┘                      │
└─────────────────────────────────────────────────────────┘
          ▲                ▲                ▲
          │                │                │
┌─────────┼────────────────┼────────────────┼─────────────┐
│         │     Data Collection Layer       │             │
│  ┌──────┴──────────────────────────────────┴──────┐     │
│  │              Application Services               │     │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐          │     │
│  │  │ Backend │ │ Gateway │ │AI Service│          │     │
│  │  │ /metrics│ │ /metrics│ │ /metrics │          │     │
│  │  └─────────┘ └─────────┘ └─────────┘          │     │
│  └────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────┘
```

---

## 2. 아키텍처

### 2.1 컴포넌트 역할

| 컴포넌트 | 역할 | 데이터 유형 | 보존 기간 |
|----------|------|------------|----------|
| **Prometheus** | 메트릭 수집 및 저장 | Time-series | 15일 (기본) |
| **Grafana** | 메트릭 시각화 | - | - |
| **Elasticsearch** | 로그 저장 및 검색 | 문서 (JSON) | 30일 |
| **Kibana** | 로그 시각화 및 분석 | - | - |
| **Loki** | 경량 로그 저장 | 로그 스트림 | 7일 |
| **Promtail** | 컨테이너 로그 수집 | - | - |
| **Jaeger** | 분산 추적 저장 | Trace/Span | In-memory |

### 2.2 데이터 흐름

```
[Application] ──metrics──▶ [Prometheus] ──query──▶ [Grafana]
      │
      ├──────logs───────▶ [Promtail] ──push──▶ [Loki] ──query──▶ [Grafana]
      │
      ├──────logs───────▶ [Filebeat] ──push──▶ [Elasticsearch] ──query──▶ [Kibana]
      │
      └──────traces─────▶ [Jaeger Agent] ──report──▶ [Jaeger Collector] ──query──▶ [Jaeger UI]
```

---

## 3. 접속 정보

### 3.1 URL 및 포트

| 서비스 | 내부 URL | 외부 URL | 포트 |
|--------|----------|----------|------|
| **Grafana** | http://grafana:3000 | http://localhost:3001 | 3001 |
| **Prometheus** | http://prometheus:9090 | http://localhost:9090 | 9090 |
| **Kibana** | http://kibana:5601 | http://localhost:5601 | 5601 |
| **Elasticsearch** | http://elasticsearch:9200 | http://localhost:9200 | 9200 |
| **Jaeger** | http://jaeger:16686 | http://localhost:16686 | 16686 |
| **Loki** | http://loki:3100 | http://localhost:3100 | 3100 |

### 3.2 인증 정보

| 서비스 | Username | Password | 비고 |
|--------|----------|----------|------|
| **Grafana** | admin | `grafana_dev_2026!` | 환경변수 설정 |
| **Kibana** | - | - | 인증 없음 (개발) |
| **Prometheus** | - | - | 인증 없음 |
| **Jaeger** | - | - | 인증 없음 |

### 3.3 컨테이너 정보

| 컨테이너명 | 이미지 | 헬스체크 |
|-----------|--------|----------|
| kp-grafana | grafana/grafana:10.2.0 | HTTP /api/health |
| kp-prometheus | prom/prometheus:v2.48.0 | HTTP /-/healthy |
| kp-kibana | kibana:8.11.0 | HTTP /api/status |
| kp-elasticsearch | elasticsearch:8.11.0 | HTTP /_cluster/health |
| kp-jaeger | jaegertracing/all-in-one:1.52 | HTTP /health |
| kp-loki | grafana/loki:2.9.2 | HTTP /ready |
| kp-promtail | grafana/promtail:2.9.2 | - |

---

## 4. Grafana 운영

### 4.1 접속 및 로그인

```bash
# 브라우저 접속
http://localhost:3001

# 로그인
Username: admin
Password: grafana_dev_2026!
```

### 4.2 대시보드 메뉴 구조

```
Grafana
├── Home                    # 홈 대시보드
├── Dashboards             # 대시보드 목록
│   ├── General            # 일반 대시보드
│   └── [Custom Folders]   # 사용자 정의 폴더
├── Explore                # 임시 쿼리 및 탐색
├── Alerting               # 알림 관리
│   ├── Alert rules        # 알림 규칙
│   ├── Contact points     # 알림 수신자
│   └── Notification policies
├── Connections            # 데이터 소스 연결
│   └── Data sources       # Prometheus, Loki 등
└── Administration         # 관리 설정
    ├── Users              # 사용자 관리
    └── Settings           # 시스템 설정
```

### 4.3 데이터 소스 설정

#### Prometheus 데이터 소스 추가

1. **Connections** → **Data sources** → **Add data source**
2. **Prometheus** 선택
3. 설정:
   ```
   Name: Prometheus
   URL: http://prometheus:9090
   Access: Server (default)
   ```
4. **Save & test** 클릭

#### Loki 데이터 소스 추가

1. **Connections** → **Data sources** → **Add data source**
2. **Loki** 선택
3. 설정:
   ```
   Name: Loki
   URL: http://loki:3100
   ```
4. **Save & test** 클릭

### 4.4 주요 쿼리 예제

#### CPU 사용률

```promql
100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
```

#### 메모리 사용률

```promql
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100
```

#### HTTP 요청 수 (분당)

```promql
sum(rate(http_server_requests_seconds_count[1m])) by (uri, method)
```

#### HTTP 응답 시간 (95th percentile)

```promql
histogram_quantile(0.95, sum(rate(http_server_requests_seconds_bucket[5m])) by (le, uri))
```

#### 에러율

```promql
sum(rate(http_server_requests_seconds_count{status=~"5.."}[5m]))
/ sum(rate(http_server_requests_seconds_count[5m])) * 100
```

### 4.5 대시보드 생성

#### 새 대시보드 생성

1. **Dashboards** → **New** → **New Dashboard**
2. **Add visualization** 클릭
3. 데이터 소스 선택 (Prometheus)
4. 쿼리 입력
5. 패널 제목 설정
6. **Apply** → **Save dashboard**

#### 대시보드 내보내기/가져오기

**내보내기:**
1. 대시보드 열기
2. **Share** (상단) → **Export**
3. **Save to file** 클릭

**가져오기:**
1. **Dashboards** → **Import**
2. JSON 파일 업로드 또는 대시보드 ID 입력

### 4.6 운영 명령어

```bash
# Grafana 컨테이너 상태 확인
docker ps --filter name=kp-grafana

# Grafana 로그 확인
docker logs kp-grafana --tail 100

# Grafana 재시작
docker compose restart grafana

# Grafana 설정 확인
docker exec kp-grafana cat /etc/grafana/grafana.ini

# 데이터 소스 API 조회
curl -u admin:grafana_dev_2026! http://localhost:3001/api/datasources
```

---

## 5. Prometheus 운영

### 5.1 접속

```bash
# 브라우저 접속
http://localhost:9090
```

### 5.2 메뉴 구조

```
Prometheus
├── Graph          # 쿼리 실행 및 그래프
├── Alerts         # 알림 규칙 상태
├── Status
│   ├── Runtime & Build Information
│   ├── Command-Line Flags
│   ├── Configuration
│   ├── Rules       # 알림/레코딩 규칙
│   ├── Targets     # 스크래핑 대상 ⭐
│   ├── Service Discovery
│   └── TSDB Status # 저장소 상태
└── Help
```

### 5.3 Targets 확인 (중요)

**Status** → **Targets** 메뉴에서 스크래핑 대상 확인

| 상태 | 의미 | 조치 |
|------|------|------|
| **UP** (녹색) | 정상 수집 중 | 없음 |
| **DOWN** (빨강) | 수집 실패 | 대상 서비스 확인 |
| **UNKNOWN** | 아직 수집 안됨 | 대기 |

### 5.4 주요 내장 메트릭

```promql
# Prometheus 자체 상태
prometheus_build_info                    # 버전 정보
prometheus_tsdb_head_samples_appended_total  # 수집된 샘플 수
prometheus_target_scrape_pool_targets    # 스크래핑 대상 수

# 타겟 상태
up                                       # 타겟 상태 (1=UP, 0=DOWN)
scrape_duration_seconds                  # 스크래핑 소요 시간
scrape_samples_scraped                   # 스크래핑된 샘플 수
```

### 5.5 설정 파일 구조

```yaml
# /etc/prometheus/prometheus.yml
global:
  scrape_interval: 15s      # 기본 수집 주기
  evaluation_interval: 15s  # 규칙 평가 주기

alerting:
  alertmanagers:
    - static_configs:
        - targets: []

rule_files:
  - /etc/prometheus/rules/*.yml

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'backend'
    metrics_path: /actuator/prometheus
    static_configs:
      - targets: ['backend:8081']

  - job_name: 'api-gateway'
    metrics_path: /actuator/prometheus
    static_configs:
      - targets: ['api-gateway:8080']
```

### 5.6 운영 명령어

```bash
# Prometheus 상태 확인
docker ps --filter name=kp-prometheus

# 설정 파일 확인
docker exec kp-prometheus cat /etc/prometheus/prometheus.yml

# 설정 리로드 (SIGHUP)
docker exec kp-prometheus kill -HUP 1

# 메트릭 직접 조회
curl http://localhost:9090/api/v1/query?query=up

# 타겟 상태 조회
curl http://localhost:9090/api/v1/targets

# TSDB 상태 확인
curl http://localhost:9090/api/v1/status/tsdb
```

### 5.7 PromQL 쿼리 팁

```promql
# 기본 조회
metric_name

# 레이블 필터
metric_name{label="value"}
metric_name{label=~"regex.*"}    # 정규식 매칭
metric_name{label!="value"}      # 불일치

# 시간 범위
metric_name[5m]                   # 최근 5분
metric_name[1h]                   # 최근 1시간

# 집계 함수
sum(metric_name)                  # 합계
avg(metric_name)                  # 평균
max(metric_name)                  # 최대
min(metric_name)                  # 최소
count(metric_name)                # 개수

# rate 함수 (카운터용)
rate(metric_name[5m])             # 초당 증가율
irate(metric_name[5m])            # 순간 증가율

# by 절 (그룹핑)
sum(metric_name) by (label)
avg(rate(http_requests_total[5m])) by (status)
```

---

## 6. Kibana & Elasticsearch 운영

### 6.1 접속

```bash
# Kibana
http://localhost:5601

# Elasticsearch (API)
http://localhost:9200
```

### 6.2 Kibana 메뉴 구조

```
Kibana
├── Analytics
│   ├── Discover       # 로그 검색 및 탐색 ⭐
│   ├── Dashboard      # 대시보드
│   └── Canvas         # 시각화 캔버스
├── Management
│   ├── Dev Tools      # ES 쿼리 콘솔 ⭐
│   ├── Stack Monitoring
│   └── Stack Management
│       ├── Index Management  # 인덱스 관리
│       ├── Data Views       # 인덱스 패턴
│       └── Saved Objects    # 저장된 객체
└── Observability
    ├── Logs
    └── APM
```

### 6.3 Dev Tools 필수 쿼리

#### 클러스터 상태

```json
GET _cluster/health

# 응답 예시
{
  "cluster_name": "docker-cluster",
  "status": "yellow",        // green/yellow/red
  "number_of_nodes": 1,
  "active_primary_shards": 5
}
```

| 상태 | 의미 | 조치 |
|------|------|------|
| **green** | 모든 샤드 정상 | 없음 |
| **yellow** | 프라이머리 정상, 레플리카 없음 | 단일 노드에서 정상 |
| **red** | 일부 샤드 손실 | 즉시 조치 필요 |

#### 인덱스 목록

```json
GET _cat/indices?v&s=index

# 출력
health status index             docs.count store.size
yellow open   knowledge-chunks  1000       5.2mb
yellow open   logs-2026.02.04   50000      25mb
```

#### 인덱스 상세 정보

```json
GET knowledge-chunks/_stats
GET knowledge-chunks/_mapping
GET knowledge-chunks/_settings
```

#### 문서 검색

```json
# 전체 검색 (최근 10개)
GET knowledge-chunks/_search
{
  "query": { "match_all": {} },
  "size": 10,
  "sort": [{ "@timestamp": "desc" }]
}

# 키워드 검색
GET knowledge-chunks/_search
{
  "query": {
    "match": {
      "content": "로깅 표준"
    }
  }
}

# 복합 쿼리
GET knowledge-chunks/_search
{
  "query": {
    "bool": {
      "must": [
        { "match": { "content": "로깅" } }
      ],
      "filter": [
        { "range": { "@timestamp": { "gte": "now-1d" } } }
      ]
    }
  }
}
```

#### 인덱스 관리

```json
# 인덱스 생성
PUT my-index
{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0
  }
}

# 인덱스 삭제 (주의!)
DELETE my-index

# 오래된 인덱스 삭제 (예: 30일 이전)
DELETE logs-2026.01.*
```

### 6.4 Discover 사용법

1. **메뉴** → **Analytics** → **Discover**
2. **Data View** 선택 (인덱스 패턴)
3. **시간 범위** 설정 (우측 상단)
4. **검색어** 입력 (KQL 문법)

#### KQL (Kibana Query Language) 예제

```
# 필드 값 일치
status: 500
level: error

# 와일드카드
message: *error*
service: backend*

# 범위
response_time > 1000
@timestamp >= "2026-02-04"

# 논리 연산
level: error AND service: backend
level: error OR level: warning
NOT status: 200

# 존재 여부
_exists_: error_message
```

### 6.5 Data View (인덱스 패턴) 생성

1. **Stack Management** → **Data Views**
2. **Create data view**
3. 설정:
   ```
   Name: logs-*
   Index pattern: logs-*
   Timestamp field: @timestamp
   ```
4. **Save data view**

### 6.6 운영 명령어

```bash
# Elasticsearch 상태 확인
curl http://localhost:9200/_cluster/health?pretty

# 노드 정보
curl http://localhost:9200/_nodes/stats?pretty

# 인덱스 목록
curl http://localhost:9200/_cat/indices?v

# 디스크 사용량
curl http://localhost:9200/_cat/allocation?v

# Kibana 상태
curl http://localhost:5601/api/status

# 컨테이너 로그
docker logs kp-elasticsearch --tail 50
docker logs kp-kibana --tail 50
```

---

## 7. Jaeger 운영

### 7.1 접속

```bash
# Jaeger UI
http://localhost:16686
```

### 7.2 UI 구조

```
Jaeger UI
├── Search           # 트레이스 검색 ⭐
│   ├── Service      # 서비스 선택
│   ├── Operation    # 작업/엔드포인트
│   ├── Tags         # 태그 필터
│   └── Lookback     # 시간 범위
├── Compare          # 트레이스 비교
├── Dependencies     # 서비스 의존성 그래프
└── System Architecture  # 시스템 아키텍처
```

### 7.3 트레이스 검색

1. **Service** 드롭다운에서 서비스 선택
2. **Operation** 선택 (선택사항)
3. **Lookback** 시간 범위 설정
4. **Find Traces** 클릭

#### 검색 필터 예제

| 필터 | 값 예시 | 설명 |
|------|---------|------|
| Service | backend | 서비스명 |
| Operation | GET /api/v1/documents | HTTP 메서드 + 경로 |
| Tags | http.status_code=500 | 태그 필터 |
| Min Duration | 1s | 최소 소요 시간 |
| Max Duration | 10s | 최대 소요 시간 |
| Limit Results | 20 | 결과 개수 |

### 7.4 트레이스 분석

#### 트레이스 뷰 구성

```
Trace Timeline
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[nginx]          |████|
[api-gateway]         |████████████|
  └─[backend]              |████████|
      └─[postgresql]            |██|
      └─[redis]                 |█|
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
0ms            100ms           200ms          300ms
```

#### Span 상세 정보

- **Service**: 서비스명
- **Operation**: 작업명
- **Duration**: 소요 시간
- **Tags**: 메타데이터 (http.method, http.url, http.status_code 등)
- **Logs**: 스팬 내 로그 이벤트
- **Process**: 프로세스 정보

### 7.5 Dependencies 뷰

서비스 간 의존성을 시각화:

```
[nginx] ──▶ [api-gateway] ──▶ [backend] ──▶ [postgresql]
                   │                │
                   │                └──▶ [redis]
                   │
                   └──▶ [ai-service] ──▶ [elasticsearch]
```

### 7.6 운영 명령어

```bash
# Jaeger 상태 확인
curl http://localhost:16686/api/services

# 서비스 목록 조회
curl http://localhost:16686/api/services | jq

# 특정 서비스의 작업 목록
curl "http://localhost:16686/api/operations?service=backend" | jq

# 트레이스 조회
curl "http://localhost:16686/api/traces?service=backend&limit=10" | jq

# 컨테이너 로그
docker logs kp-jaeger --tail 50
```

---

## 8. Loki & Promtail 운영

### 8.1 개요

| 컴포넌트 | 역할 | 포트 |
|----------|------|------|
| **Loki** | 로그 저장 및 쿼리 서버 | 3100 |
| **Promtail** | 컨테이너 로그 수집 에이전트 | - |

### 8.2 Loki 상태 확인

```bash
# Ready 상태
curl http://localhost:3100/ready

# 메트릭
curl http://localhost:3100/metrics

# 레이블 목록
curl http://localhost:3100/loki/api/v1/labels

# 레이블 값 조회
curl "http://localhost:3100/loki/api/v1/label/container/values"
```

### 8.3 LogQL (Loki 쿼리 언어)

Grafana **Explore**에서 Loki 데이터 소스 선택 후 사용:

#### 기본 쿼리

```logql
# 컨테이너별 로그
{container="kp-backend"}

# 여러 조건
{container="kp-backend", level="error"}

# 정규식 매칭
{container=~"kp-.*"}
```

#### 필터링

```logql
# 텍스트 포함
{container="kp-backend"} |= "error"

# 텍스트 미포함
{container="kp-backend"} != "health"

# 정규식 필터
{container="kp-backend"} |~ "ERROR|WARN"
```

#### 파싱 및 집계

```logql
# JSON 파싱
{container="kp-backend"} | json

# 특정 필드 추출
{container="kp-backend"} | json | level="error"

# 로그 카운트 (1분 단위)
count_over_time({container="kp-backend"} |= "error" [1m])

# 로그 발생률
rate({container="kp-backend"}[5m])
```

### 8.4 Promtail 설정

```yaml
# /etc/promtail/config.yml
server:
  http_listen_port: 9080

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: containers
    static_configs:
      - targets:
          - localhost
        labels:
          job: containerlogs
          __path__: /var/lib/docker/containers/*/*log
    pipeline_stages:
      - json:
          expressions:
            log: log
            stream: stream
            time: time
      - labels:
          stream:
      - output:
          source: log
```

### 8.5 운영 명령어

```bash
# Loki 상태
docker logs kp-loki --tail 50

# Promtail 상태
docker logs kp-promtail --tail 50

# Loki 저장소 크기
docker exec kp-loki du -sh /loki

# 레이블 확인
curl http://localhost:3100/loki/api/v1/labels | jq
```

---

## 9. 알림 설정

### 9.1 Grafana 알림 설정

#### Contact Points 설정

1. **Alerting** → **Contact points**
2. **Add contact point**
3. Integration 선택:
   - **Slack**: Webhook URL 입력
   - **Email**: SMTP 설정 필요
   - **Webhook**: 커스텀 URL

#### Slack 연동 예시

```
Name: Slack-Alerts
Integration: Slack
Webhook URL: https://hooks.slack.com/services/T00/B00/XXX
```

#### 알림 규칙 생성

1. **Alerting** → **Alert rules** → **New alert rule**
2. 쿼리 설정:
   ```promql
   sum(rate(http_server_requests_seconds_count{status=~"5.."}[5m])) > 0.1
   ```
3. 조건 설정:
   - Threshold: > 0.1
   - For: 5m (5분 지속 시)
4. 알림 메시지 설정
5. Contact point 선택
6. **Save rule**

### 9.2 권장 알림 규칙

| 알림명 | 조건 | 심각도 |
|--------|------|--------|
| High Error Rate | 5xx 에러 > 1% | Critical |
| High Latency | P95 > 2s | Warning |
| Service Down | up == 0 | Critical |
| High Memory | Memory > 80% | Warning |
| Disk Full | Disk > 85% | Warning |

---

## 10. 일상 운영 체크리스트

### 10.1 일일 점검 (Daily)

```
□ 모든 컨테이너 상태 확인
  $ docker compose ps

□ Prometheus Targets 상태 확인
  URL: http://localhost:9090/targets
  - 모든 타겟 UP 상태 확인

□ Grafana 대시보드 확인
  - 에러율 확인
  - 응답 시간 확인
  - 리소스 사용량 확인

□ 알림 확인
  - 발생한 알림 검토
  - 해결되지 않은 알림 조치

□ 로그 이상 확인 (Kibana)
  - ERROR 레벨 로그 검색
  - 비정상 패턴 확인
```

### 10.2 주간 점검 (Weekly)

```
□ 디스크 사용량 확인
  $ docker exec kp-prometheus du -sh /prometheus
  $ docker exec kp-elasticsearch du -sh /usr/share/elasticsearch/data

□ 오래된 데이터 정리
  - 30일 이상 로그 인덱스 삭제
  - 불필요한 메트릭 확인

□ 대시보드 업데이트 검토
  - 새로운 메트릭 추가 필요 여부
  - 알림 규칙 조정 필요 여부

□ 백업 상태 확인
  - Grafana 대시보드 백업
  - 알림 규칙 백업
```

### 10.3 월간 점검 (Monthly)

```
□ 용량 계획 검토
  - 데이터 증가 추세 분석
  - 스토리지 확장 필요 여부

□ 성능 최적화
  - 쿼리 성능 분석
  - 인덱스 최적화

□ 보안 업데이트 확인
  - 이미지 버전 업데이트
  - 취약점 패치
```

---

## 11. 장애 대응 가이드

### 11.1 서비스 다운 대응

```bash
# 1. 컨테이너 상태 확인
docker compose ps

# 2. 다운된 서비스 로그 확인
docker logs <container_name> --tail 100

# 3. 서비스 재시작
docker compose restart <service_name>

# 4. 헬스체크 확인
docker inspect --format='{{.State.Health.Status}}' <container_name>
```

### 11.2 고부하 대응

```bash
# 1. 리소스 사용량 확인
docker stats

# 2. Prometheus에서 메트릭 확인
# - CPU, Memory, Request Rate

# 3. 로그에서 원인 파악
# - 대량 요청, 느린 쿼리 등

# 4. 필요시 스케일 아웃 또는 리소스 증설
```

### 11.3 디스크 부족 대응

```bash
# 1. 디스크 사용량 확인
df -h

# 2. 컨테이너별 사용량
docker system df -v

# 3. 오래된 데이터 삭제
# Elasticsearch 오래된 인덱스 삭제
curl -X DELETE "http://localhost:9200/logs-2026.01.*"

# Docker 정리
docker system prune -f

# 4. 보존 정책 조정
```

---

## 12. 트러블슈팅

### 12.1 Prometheus

| 증상 | 원인 | 해결 |
|------|------|------|
| Target DOWN | 서비스 다운 또는 네트워크 문제 | 서비스 상태 확인, 방화벽 확인 |
| Scrape 실패 | metrics 엔드포인트 오류 | /actuator/prometheus 접근 확인 |
| 데이터 누락 | TSDB 손상 | 데이터 디렉토리 백업 후 재시작 |

### 12.2 Grafana

| 증상 | 원인 | 해결 |
|------|------|------|
| 로그인 실패 | 비밀번호 오류 | 환경변수 확인, 비밀번호 리셋 |
| 데이터 소스 연결 실패 | URL 오류 또는 네트워크 | 내부 Docker 네트워크 URL 확인 |
| 대시보드 로딩 느림 | 쿼리 비효율 | 쿼리 최적화, 시간 범위 축소 |

### 12.3 Elasticsearch

| 증상 | 원인 | 해결 |
|------|------|------|
| Cluster RED | 샤드 손실 | 샤드 할당 상태 확인, 복구 |
| 인덱싱 느림 | 리소스 부족 | 힙 메모리 증설, 벌크 크기 조정 |
| 검색 타임아웃 | 쿼리 비효율 | 쿼리 최적화, 인덱스 튜닝 |

### 12.4 Jaeger

| 증상 | 원인 | 해결 |
|------|------|------|
| 서비스 목록 비어있음 | 트레이싱 미설정 | 애플리케이션 트레이싱 설정 확인 |
| 트레이스 없음 | 에이전트 연결 실패 | Jaeger Agent 포트 확인 |
| UI 느림 | 데이터 과다 | Lookback 시간 축소, Limit 설정 |

### 12.5 Loki

| 증상 | 원인 | 해결 |
|------|------|------|
| 로그 수집 안됨 | Promtail 설정 오류 | 설정 파일 및 경로 확인 |
| 쿼리 느림 | 레이블 카디널리티 높음 | 레이블 설계 검토 |
| 저장 공간 부족 | 보존 기간 설정 | retention_period 조정 |

---

## 부록

### A. 유용한 명령어 모음

```bash
# 전체 상태 확인
docker compose ps | grep -E "grafana|prometheus|kibana|elastic|jaeger|loki"

# 모든 observability 서비스 재시작
docker compose restart grafana prometheus kibana elasticsearch jaeger loki promtail

# 로그 통합 확인
docker compose logs --tail 50 grafana prometheus kibana

# 리소스 사용량
docker stats --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep kp-
```

### B. 참고 문서

- [Grafana Documentation](https://grafana.com/docs/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Elasticsearch Guide](https://www.elastic.co/guide/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [Loki Documentation](https://grafana.com/docs/loki/)

### C. 버전 정보

| 컴포넌트 | 버전 | 릴리스 노트 |
|----------|------|-------------|
| Grafana | 10.2.0 | 2023-10 |
| Prometheus | 2.48.0 | 2023-11 |
| Elasticsearch | 8.11.0 | 2023-11 |
| Kibana | 8.11.0 | 2023-11 |
| Jaeger | 1.52 | 2023-12 |
| Loki | 2.9.2 | 2023-10 |

---

*Document Version: 1.0*
*Last Updated: 2026-02-04*
*Maintainer: DevOps Team*
