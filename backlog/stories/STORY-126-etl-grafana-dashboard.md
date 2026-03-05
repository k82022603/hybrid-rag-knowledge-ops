# STORY-126: ETL 파이프라인 전용 Grafana 대시보드

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | - |
| **Epic** | Observability 강화 |
| **Status** | To Do |
| **Priority** | P2 |
| **Story Points** | 3 |
| **Assignee** | DevOps |
| **Sprint** | Sprint 09 |

---

## 배경

ETL Engineer 요청: 현재 ETL 상태는 PG 쿼리 또는 터미널 모니터 스크립트로만 확인 가능.
Grafana에 ETL 전용 대시보드가 없어 운영 가시성 부족.

---

## User Story

**As a** ETL 운영자,
**I want** Grafana에서 ETL 파이프라인 상태를 실시간으로 확인하기를,
**So that** 문서 처리 현황, Phase별 진행률, 에러율을 한눈에 파악할 수 있다.

---

## Acceptance Criteria

- [ ] ETL 전용 Grafana 대시보드 JSON 파일 생성
- [ ] 패널 구성:
  - Phase 1: 총 문서 수 / 처리 완료 / 실패 수
  - Phase 2: 임베딩 pending / 완료 / 오류
  - Phase 3: 엔티티 추출 완료 / Neo4j 저장 수
  - 고아 노드 비율 (목표: 1% 이하)
  - ETL 최근 실행 로그 (Loki 연동)
- [ ] 대시보드 JSON → `infrastructure/grafana/dashboards/etl-pipeline.json` 저장
- [ ] Grafana 프로비저닝 자동 로드 설정

---

## Tasks

- [ ] PG `document_processing_status` 기반 메트릭 쿼리 작성
- [ ] Neo4j 엔티티/고아 노드 수 메트릭 (Cypher → Prometheus Textfile Exporter)
- [ ] Grafana 대시보드 JSON 설계 및 작성
- [ ] `infrastructure/grafana/provisioning/dashboards/` 설정 확인
- [ ] Loki ETL 로그 패널 연동

---

## 기술 노트

### 데이터 소스

| 패널 | 데이터 소스 | 쿼리 |
|------|------------|------|
| Phase 1 현황 | PostgreSQL | `document_processing_status` 집계 |
| Phase 2 임베딩 | Elasticsearch | `embedding_status` aggregation |
| Phase 3 엔티티 | Neo4j → Textfile | Cypher COUNT |
| ETL 로그 | Loki | `{container="kp-ai-service"} |= "ETL"` |

### 파일 위치
- `infrastructure/grafana/dashboards/etl-pipeline.json` (신규)

---

## 의존성

- **선행**: STORY-117 (Prometheus Exporter 활성화 — Textfile Exporter 필요)
- **관련**: STORY-112 (Phase 3 실행 후 실데이터로 대시보드 검증)
