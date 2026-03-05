# STORY-120: ETL 실패 재시도 + 고아 노드 자동 정리

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | - |
| **Epic** | ETL 안정화 |
| **Status** | Done |
| **Priority** | P1 |
| **Story Points** | 3 |
| **Assignee** | ETL |
| **Sprint** | Sprint 09 |

---

## User Story

**As a** ETL 운영자,
**I want** 실패한 문서가 자동으로 재처리되고 고아 노드가 자동 정리되기를,
**So that** 수동 개입 없이 ETL 데이터 품질이 유지된다.

---

## Acceptance Criteria

- [x] 지수 백오프 재시도 구현 (max 3회, backoff=2^n초, 최대 30초)
- [x] 실패 문서 목록 PG에 기록 및 재처리 큐 관리
- [x] 고아 노드 자동 감지 배치 (PART_OF 없는 Entity 노드)
- [x] 고아 노드 비율 1% 이하 유지 목표 — 0.000% 달성 (88개 → 0개)
- [x] 정리 작업 로그 기록

---

## Tasks

- [x] ETL 파이프라인 재시도 로직 추가 (지수 백오프) — `batch_entity_extraction.py`, `run_etl_phase2_entities.py`
- [x] PG `document_processing_status` 실패 기록 강화
- [x] Neo4j 고아 노드 감지 Cypher 쿼리 작성
- [x] 자동 정리 배치 스크립트 작성 — `cleanup_orphan_nodes.py` (dry-run 지원, 배치 200)
- [ ] 스케줄러 등록 (일 1회 실행) — 추후 DevOps 연계

> **완료 메모** (2026-03-05): 고아 129,615→129,527개, 고아 88개→0개(0.000%) 달성. MAX_RETRIES=3, 기본 대기 2초, 최대 30초 (환경변수 오버라이드 가능).

---

## 기술 노트

### 고아 노드 감지 Cypher
```cypher
MATCH (e:Entity)
WHERE NOT (e)-[:PART_OF]->()
AND NOT ()-[:MENTIONS]->(e)
RETURN count(e) as orphan_count
```

### 영향 범위
- `knowledge_service/src/app/services/entity_extraction.py`
- `knowledge_service/scripts/cleanup_orphan_nodes.py` (신규)

---

## 의존성

- **선행**: STORY-112 (Phase 3 실행 후 고아 노드 발생 가능)
- **관련**: STORY-089 (문서 동기화와 상태 관리 연계)
