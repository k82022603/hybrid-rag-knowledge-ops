# STORY-124: Neo4j 스키마 통합 (v1.0/v2.6 불일치 해소)

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | - |
| **Epic** | Knowledge Graph 고도화 |
| **Status** | To Do |
| **Priority** | P2 |
| **Story Points** | 3 |
| **Assignee** | DB/RAG |
| **Sprint** | Sprint 09 |

---

## 배경

DB Designer 발견: Neo4j 스키마 파일 2개 공존
- `infrastructure/docker/init-db/03_neo4j_constraints.cypher` (v1.0: Entity/Document/TextUnit/Community)
- `infrastructure/database/neo4j/schema.cypher` (v2.6: User/Knowledge/Chunk/Entity)
노드 레이블 불일치로 인한 혼란 가능성.

TechLead 확인: Sprint 12에서 HAS_ENTITY→MENTIONS, RELATED→RELATED_TO 스키마 통일 완료.
init-db 파일이 구버전일 가능성 높음.

---

## Acceptance Criteria

- [ ] 두 스키마 파일 간 불일치 항목 전수 조사
- [ ] 실제 운영 스키마(v2.6 기준) 확정
- [ ] init-db 파일을 v2.6 기준으로 업데이트
- [ ] 마이그레이션 스크립트 작성 (기존 데이터 보존)

---

## 의존성

- **선행**: STORY-112 (Phase 3 실행으로 실제 데이터 확인)
- **후행**: STORY-121 (KG 시각화 UI)
