# STORY-114: Init-DB depends_on service_healthy 전면 적용

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | - |
| **Epic** | 인프라 안정성 |
| **Status** | To Do |
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

- [ ] `docker-compose.yml`의 init-db 서비스에 `condition: service_healthy` 적용
- [ ] PostgreSQL, Neo4j, Elasticsearch health check 조건 명시
- [ ] `docker-compose up` 시 init-db가 DB 준비 완료 후 실행 확인
- [ ] 재시작 시나리오 테스트 통과

---

## Tasks

- [ ] `docker-compose.yml` init-db depends_on 수정
- [ ] PostgreSQL healthcheck 설정 확인/추가
- [ ] Neo4j healthcheck 설정 확인/추가
- [ ] Elasticsearch healthcheck 설정 확인/추가
- [ ] `docker-compose up --force-recreate` 재시작 테스트

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
