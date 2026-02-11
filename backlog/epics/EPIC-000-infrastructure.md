# EPIC-000: Infrastructure Setup

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-9 |
| **Status** | Done |
| **Priority** | Critical |
| **Owner** | DevOps |
| **Target Sprint** | Sprint 1 |
| **Total Story Points** | 21 |

---

## 요약

Docker Compose 기반 18개 컨테이너 환경 구축. Keycloak 인증, PostgreSQL/Neo4j/Elasticsearch 데이터베이스 초기화, 프로젝트 골격 생성까지 개발 환경 전체 구성.

---

## 배경 및 목표

### 배경
- 문서 처리 파이프라인 개발 전 실행 환경 필요
- 로컬 개발 환경에서 모든 서비스 테스트 가능해야 함
- 인증/인가 체계가 사전에 구축되어야 함

### 목표
- 단일 명령어로 전체 인프라 기동 (`docker-compose up`)
- 모든 데이터베이스 스키마/인덱스 자동 초기화
- 프로젝트 골격이 빌드 가능한 상태로 준비

### 성공 지표
- [ ] Docker 컨테이너 18개 정상 동작
- [ ] Keycloak OAuth 2.0 로그인 성공
- [ ] PostgreSQL 테이블 생성 완료
- [ ] 로컬 개발 환경 기동 가능

---

## User Stories

| ID | Jira | 제목 | Points | Status | Sprint |
|----|------|------|--------|--------|--------|
| STORY-010 | SCRUM-10 | Docker Compose 환경 구성 | 5 | To Do | 1 |
| STORY-011 | SCRUM-11 | 데이터베이스 초기화 | 5 | To Do | 1 |
| STORY-012 | SCRUM-12 | 인증 인프라 (Keycloak) | 5 | To Do | 1 |
| STORY-013 | SCRUM-13 | 프로젝트 골격 생성 | 5 | To Do | 1 |
| STORY-014 | SCRUM-14 | 개발 환경 가이드 | 1 | To Do | 1 |

---

## 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                    Docker Compose Network                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────── Application Layer ──────────────────────┐ │
│  │  nginx    frontend    api-gateway    backend    ai-service │ │
│  │  :80      :3000       :8080          :8081      :8000      │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│  ┌─────────────────── Data Layer ─────────────────────────────┐ │
│  │  postgresql   elasticsearch   neo4j    redis    minio      │ │
│  │  :5432        :9200           :7687    :6379    :9000      │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│  ┌─────────────────── Auth Layer ─────────────────────────────┐ │
│  │  keycloak                                                   │ │
│  │  :8180                                                      │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│  ┌─────────────────── Observability Layer ────────────────────┐ │
│  │  prometheus   grafana   loki   promtail   jaeger           │ │
│  │  :9090        :3001     :3100             :16686           │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 기술 요구사항

### 컨테이너 목록 (18개)

| Layer | 서비스 | 이미지 | 포트 |
|-------|--------|--------|------|
| Application | nginx | nginx:1.25-alpine | 80, 443 |
| Application | frontend | custom | 3000 |
| Application | api-gateway | custom | 8080 |
| Application | backend | custom | 8081 |
| Application | ai-service | custom | 8000 |
| Auth | keycloak | quay.io/keycloak/keycloak:26.0 | 8180 |
| Data | postgresql | postgres:16-alpine | 5432 |
| Data | elasticsearch | elasticsearch:8.12.0 | 9200 |
| Data | neo4j | neo4j:5-community | 7474, 7687 |
| Data | redis | redis:7-alpine | 6379 |
| Data | minio | minio/minio:latest | 9000, 9001 |
| Observability | prometheus | prom/prometheus:v2.48.0 | 9090 |
| Observability | grafana | grafana/grafana:10.2.0 | 3001 |
| Observability | loki | grafana/loki:2.9.0 | 3100 |
| Observability | promtail | grafana/promtail:2.9.0 | - |
| Observability | jaeger | jaegertracing/all-in-one:1.51 | 16686 |

### 데이터베이스 스키마

| DB | 초기화 내용 |
|----|-------------|
| PostgreSQL | knowledge, keycloak 스키마, 기본 테이블 |
| Elasticsearch | knowledge_chunks 인덱스 (벡터 1024차원) |
| Neo4j | Constraints, Indexes (Document, Chunk, Entity) |

---

## 의존성

### 선행 조건
- [x] Docker Desktop 설치
- [x] Docker Compose v2 설치
- [ ] 최소 16GB RAM (권장 32GB)
- [ ] 50GB 디스크 공간

### 환경 변수
```bash
# .env 파일 필요
POSTGRES_PASSWORD=
KEYCLOAK_ADMIN_PASSWORD=
KEYCLOAK_DB_PASSWORD=
NEO4J_PASSWORD=
MINIO_ROOT_USER=
MINIO_ROOT_PASSWORD=
GRAFANA_PASSWORD=
DEEPSEEK_API_KEY=
```

---

## 리스크

| 리스크 | 영향 | 대응 |
|--------|------|------|
| 메모리 부족 | High | Observability 레이어 선택적 기동 |
| 포트 충돌 | Medium | .env에서 포트 커스터마이징 |
| Keycloak 초기 설정 복잡 | Medium | 자동화 스크립트 제공 |

---

## 참고 자료

- [스프린트 실행 계획서](../../docs/02_스프린트_실행_계획서.md)
- [인프라 설계서](../../knowledge_service/docs/02_design/10_infrastructure_detailed_design.md)
- [Docker Compose 공식 문서](https://docs.docker.com/compose/)
