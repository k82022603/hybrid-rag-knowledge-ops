# 장애 보고서: 컨테이너 재기동 실패

---

## 문서 정보

| 항목 | 내용 |
|------|------|
| **장애 ID** | INC-2026-02-07-001 |
| **발생일시** | 2026-02-07 01:20 ~ 02:30 (KST) |
| **복구일시** | 2026-02-07 02:30 (KST) |
| **영향 시간** | 약 70분 |
| **심각도** | P2 (서비스 부분 장애) |
| **작성자** | TechLead / Infra |
| **상태** | 복구 완료 |

---

## 1. 장애 개요

Docker Compose 환경의 전체 컨테이너 재기동 시, 서비스 간 의존성 순서 문제로 다수 컨테이너가 비정상 상태에 진입했다. 특히 nginx가 restart 루프에 빠져 리버스 프록시 기능이 완전 중단되었고, backend는 PostgreSQL 연결 실패를 56회 반복했다.

---

## 2. 영향 범위

| 서비스 | 영향 | 시간 |
|--------|------|------|
| kp-nginx | Restart 루프 (서비스 불가) | ~70분 |
| kp-api-gateway | Exited(127) 상태 | ~70분 |
| kp-keycloak | 미기동 | ~70분 |
| kp-backend | PG 연결 실패 56회 (자동 복구) | ~28분 |
| kp-ai-service | Unhealthy (Neo4j 의존성 대기) | ~40분 |
| kp-neo4j | Healthcheck 루프 | ~30분 |
| kp-postgresql | Exited → 수동 재시작 | ~20분 |
| kp-elasticsearch | Exited → 수동 재시작 | ~20분 |

---

## 3. 타임라인

| 시각 (KST) | 이벤트 |
|------------|--------|
| 01:20 | Docker Compose `up -d` 실행, 컨테이너 재기동 시작 |
| 01:20 | kp-backend 시작 → PostgreSQL 연결 시도 시작 |
| 01:20 | kp-postgresql, kp-neo4j, kp-elasticsearch Exited(127) 상태 확인 |
| 01:20 | kp-api-gateway Exited(127) 상태, kp-keycloak 미기동 |
| 01:20 | kp-nginx → `api-gateway:8080` upstream 없어 restart 루프 진입 |
| 01:20~01:48 | kp-backend → PostgreSQL `UnknownHostException` 56회 반복 |
| ~01:40 | kp-postgresql, kp-elasticsearch 수동 재시작 (`docker compose up -d`) |
| ~01:45 | kp-neo4j 수동 재시작 (`docker restart kp-neo4j`) |
| 01:48 | kp-backend → PostgreSQL 자동 재연결 성공 |
| ~02:20 | kp-ai-service redis 패키지 누락 발견, pyproject.toml 수정 후 리빌드 |
| 02:26 | kp-ai-service 리빌드 완료, 재시작 → 전 서비스(ES/Neo4j/Redis/PG) 연결 성공 |
| 02:28 | kp-api-gateway, kp-keycloak 수동 재시작 |
| 02:29 | kp-api-gateway healthy → kp-nginx 정상 기동 |
| 02:30 | **전체 15/15 컨테이너 ALL HEALTHY** |

---

## 4. 근본 원인 분석

### 4.1 직접 원인: 컨테이너 비정상 종료 후 의존성 체인 파괴

컨테이너들이 Exited(127) 상태로 종료되었고 (추정: 시스템 재시작 또는 Docker Desktop 재시작), `docker compose up -d` 실행 시 의존성 체인에 따라 순차적으로 올라와야 하지만 일부 서비스가 정상 기동하지 못했다.

### 4.2 의존성 체인 분석

```
nginx ─depends_on→ api-gateway ─depends_on→ keycloak ─depends_on→ keycloak-db
                                             backend ─depends_on→ postgresql, redis
                                                      ai-service ─depends_on→ neo4j, elasticsearch, redis
```

**파괴 지점**:
1. `postgresql`, `neo4j`, `elasticsearch`가 Exited(127)로 먼저 죽음
2. `api-gateway`와 `keycloak`이 의존성 미충족으로 기동 실패
3. `nginx`가 upstream `api-gateway:8080` DNS 해석 실패로 restart 루프
4. `backend`는 기동은 됐으나 PostgreSQL 연결 반복 실패

### 4.3 추가 발견: redis Python 패키지 누락

| 항목 | 내용 |
|------|------|
| **로그** | `WARNING: Redis unavailable for embedding cache: No module named 'redis'` |
| **원인** | `pyproject.toml`에 `redis` 패키지 미포함 |
| **영향** | 임베딩 캐시 비활성화 (기능적 영향 없음, 성능 저하) |
| **조치** | `redis = "^5.0.0"` 추가 후 ai-service 리빌드 |

---

## 5. 조치 사항

### 5.1 즉시 조치 (완료)

| # | 조치 | 상태 |
|---|------|------|
| 1 | PostgreSQL, Neo4j, Elasticsearch 수동 재시작 | 완료 |
| 2 | ai-service 리빌드 (redis 패키지 추가) | 완료 |
| 3 | api-gateway, keycloak 수동 재시작 | 완료 |
| 4 | nginx restart 루프 해소 확인 | 완료 |
| 5 | 전체 15/15 healthy 확인 | 완료 |

### 5.2 재발 방지 (구현 완료)

| # | 조치 | 상태 |
|---|------|------|
| 1 | `docker-start.sh healthcheck` 명령어 추가 (4-Phase 자동 복구) | 완료 |
| 2 | Critical DB 서비스 자동 재시작 로직 (Phase 2) | 완료 |
| 3 | App 서비스 상태 점검 (Phase 3) | 완료 |

### 5.3 권장 조치 (미완료)

| # | 조치 | 우선순위 | 담당 |
|---|------|---------|------|
| 1 | docker-compose.yml: backend depends_on에 `postgresql: condition: service_healthy` 추가 | P2 | Infra |
| 2 | nginx.conf: upstream 불가 시 fallback 설정 (resolver + variable) | P3 | Infra |
| 3 | 스탠드업 미팅 후 자동 healthcheck 실행 프로세스 | P2 | DevOps |
| 4 | Docker Desktop 자동 시작 시 container restart policy 점검 | P3 | Infra |

---

## 6. 컨테이너 최종 상태 (복구 후)

```
NAME               STATUS                    CPU      MEM
kp-ai-service      Up 6min (healthy)         0.15%    381MB/7.6GB
kp-api-gateway     Up 1min (healthy)         0.15%    210MB/1GB
kp-backend         Up 1hr  (healthy)         0.14%    201MB/2GB
kp-elasticsearch   Up 45min (healthy)        0.79%    1.1GB/1.5GB
kp-frontend        Up 1hr  (healthy)         0.00%    15MB/256MB
kp-grafana         Up 1hr  (healthy)         0.06%    83MB/256MB
kp-jaeger          Up 1hr  (healthy)         0.01%    10MB/256MB
kp-keycloak        Up 1min (healthy)         2.92%    333MB/640MB
kp-keycloak-db     Up 1hr  (healthy)         0.03%    36MB/512MB
kp-kibana          Up 1hr  (healthy)         1.15%    463MB/768MB
kp-minio           Up 1hr  (healthy)         0.03%    73MB/1GB
kp-neo4j           Up 44min (healthy)        0.64%    343MB/1GB
kp-nginx           Up 48s  (healthy)         0.00%    20MB/256MB
kp-postgresql      Up 45min (healthy)        0.00%    17MB/1GB
kp-redis           Up 1hr  (healthy)         0.14%    7MB/1GB
```

**총 메모리 사용**: 약 3.3GB / 18.6GB 할당

---

## 7. 교훈

1. **의존성 체인은 가장 약한 고리에서 깨진다**: DB 서비스가 먼저 죽으면 전체 체인이 무너진다. `depends_on: condition: service_healthy`를 모든 의존 서비스에 적용해야 한다.

2. **healthcheck 자동화가 핵심**: 수동으로 하나씩 재시작하면 70분이 걸렸다. `docker-start.sh healthcheck` 명령어로 Phase별 자동 복구가 가능하도록 개선했다.

3. **패키지 누락은 빌드 시 검증해야 한다**: redis 패키지가 pyproject.toml에 없었지만 graceful degradation으로 인해 발견이 늦어졌다. CI에서 import 검증 테스트가 필요하다.

4. **exit code 127은 binary not found**: 시스템 수준 문제로 인한 컨테이너 종료. restart policy `unless-stopped`가 있어도 반복 실패 시 backoff로 인해 즉시 복구가 안 된다.

---

## 8. 관련 문서

- [docker-start.sh healthcheck 명령어](../../../../scripts/docker-start.sh)
- [Docker 트러블슈팅 가이드](./docker_troubleshooting.md)
- [인프라 설계서](../02_design/10_infrastructure_detailed_design.md)
- [이전 장애: ai-service 시작 실패 (2026-02-02)](./incident_report_2026-02-02_ai_service_startup.md)
