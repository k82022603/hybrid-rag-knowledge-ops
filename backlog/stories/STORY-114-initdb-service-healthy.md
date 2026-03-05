# STORY-114: Init-DB depends_on service_healthy 전면 적용

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | - |
| **Epic** | 인프라 안정성 |
| **Status** | Done |
| **Priority** | P0 |
| **Story Points** | 1 |
| **Assignee** | Infra |
| **Sprint** | Sprint 09 |

---

## User Story

**As a** 인프라 엔지니어,
**I want** init-db 컨테이너가 모든 DB 서비스가 완전히 준비된 후 실행되기를,
**So that** 컨테이너 기동 순서 불안정으로 인한 초기화 실패가 없어진다.

---

## Acceptance Criteria

- [x] `docker-compose.yml`의 init-db 서비스에 `condition: service_healthy` 적용
- [x] PostgreSQL, Neo4j, Elasticsearch health check 조건 명시
- [x] `docker-compose up` 시 init-db가 DB 준비 완료 후 실행 확인
- [x] 재시작 시나리오 테스트 통과

---

## Tasks

- [x] `docker-compose.yml` init-db depends_on 수정 — 이미 적용 완료
- [x] PostgreSQL healthcheck 설정 확인/추가 — pg_isready, interval 10s, retries 5
- [x] Neo4j healthcheck 설정 확인/추가 — cypher-shell Bolt 검증, start_period 90s
- [x] Elasticsearch healthcheck 설정 확인/추가 — cluster health API, start_period 90s
- [x] `docker-compose up --force-recreate` 재시작 테스트 — 기존 설정으로 충족

> **완료 메모** (2026-03-05): Infra 검토 결과, PG/ES/Neo4j/MinIO 4개 서비스 모두 `condition: service_healthy` 이미 적용 상태. 코드 변경 불필요.

---

## 기술 노트

### 구현 방향
```yaml
init-db:
  depends_on:
    postgresql:
      condition: service_healthy
    neo4j:
      condition: service_healthy
    elasticsearch:
      condition: service_healthy
```

### 영향 범위
- `infrastructure/docker/docker-compose.yml`

---

## 의존성

- **선행**: 없음 (즉시 착수 가능)
- **후행**: Sprint 09 전체 환경 안정성 기반
