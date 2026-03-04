# STORY-117: Prometheus Exporter 활성화 (postgres + redis + nginx)

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | - |
| **Epic** | Observability 강화 |
| **Status** | To Do |
| **Priority** | P1 |
| **Story Points** | 3 |
| **Assignee** | DevOps/Infra |
| **Sprint** | Sprint 09 |

---

## User Story

**As a** DevOps Engineer,
**I want** PostgreSQL, Redis, Nginx 메트릭이 Prometheus에 수집되기를,
**So that** DB/캐시/웹서버 장애를 즉시 감지할 수 있다.

---

## 배경

현재 `prometheus.yml`에서 postgres-exporter, redis-exporter, nginx-exporter가 주석 처리 상태.
`RedisDown`, `PostgreSQLHighConnections` 알림 규칙은 존재하나 메트릭 수집이 안 되어 알림 미동작.

---

## Acceptance Criteria

- [ ] postgres-exporter 컨테이너 추가 및 PG 메트릭 수집 확인
- [ ] redis-exporter 컨테이너 추가 및 Redis 메트릭 수집 확인
- [ ] nginx-exporter (또는 stub_status) 메트릭 수집 확인
- [ ] Prometheus `prometheus.yml` 주석 해제 및 스크래핑 확인
- [ ] 기존 알림 규칙 동작 확인 (RedisDown, PostgreSQLHighConnections)

---

## Tasks

- [ ] `docker-compose.yml` postgres-exporter 서비스 추가
- [ ] `docker-compose.yml` redis-exporter 서비스 추가
- [ ] nginx stub_status 설정 또는 nginx-exporter 추가
- [ ] `prometheus.yml` 라인 116-121, 145-152, 184-191 주석 해제
- [ ] Prometheus UI에서 메트릭 수집 확인
- [ ] 알림 규칙 동작 테스트

---

## 기술 노트

### 영향 범위
- `infrastructure/docker/docker-compose.yml`
- `infrastructure/docker/prometheus/prometheus.yml`

---

## 의존성

- **선행**: STORY-114 (Init-DB service_healthy)
- **후행**: STORY-123 (Alertmanager 채널 분기), STORY-126 (ETL Grafana 대시보드)
