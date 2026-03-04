# STORY-112: Phase 3 엔티티 추출 배치 실행 (96K 청크)

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | - |
| **Epic** | Graph RAG 고도화 |
| **Status** | To Do |
| **Priority** | P0 |
| **Story Points** | 3 |
| **Assignee** | ETL/RAG |
| **Sprint** | Sprint 09 |

---

## User Story

**As a** 시스템 운영자,
**I want** Neo4j에 엔티티와 관계 데이터가 구축되기를,
**So that** Graph RAG 검색이 실제 데이터 기반으로 동작할 수 있다.

---

## 배경

현재 Neo4j 상태:
- Document 노드: 1,457개 (PART_OF 관계만 존재)
- **Entity 노드: 0개**
- **RELATED_TO 관계: 0개**

Phase 3 (엔티티 추출) 가 한 번도 실행되지 않아 Graph RAG가 사실상 동작하지 않는 상태.

---

## Acceptance Criteria

- [ ] DeepSeek V3.2 기반 엔티티 추출 배치가 1,460개 문서 대상으로 실행 완료
- [ ] Neo4j Entity 노드 10,000개 이상 생성
- [ ] RELATED_TO 관계 생성 확인
- [ ] PG entity_count 필드 업데이트 완료
- [ ] Graph 검색 (`MATCH (e:Entity)`) 에서 결과 반환 확인

---

## Tasks

- [ ] Docker 환경 기동 상태 확인 (Infra 선행)
- [ ] STORY-088 MERGE 이슈 범위 RAG와 사전 확인
- [ ] Phase 3 배치 실행 (100청크/회, 지수 백오프)
- [ ] Neo4j Entity 수 확인 (`MATCH (e:Entity) RETURN count(e)`)
- [ ] PG entity_count 보정 쿼리 실행
- [ ] Graph 검색 동작 확인

---

## 기술 노트

### 구현 방향
- 배치 단위: 100청크/회 (DeepSeek API 비용 관리)
- 실행 위치: kp-ai-service 컨테이너 내 nohup 실행
- 모니터링: etl_phase1_monitor.sh 참고하여 Phase 3 전용 모니터 스크립트 활용

### 영향 범위
- `knowledge_service/src/app/services/entity_extraction.py`
- `infrastructure/docker/init-db/03_neo4j_constraints.cypher`
- Neo4j: Entity, MENTIONS, RELATED_TO

---

## 테스트 계획

- [ ] Neo4j Entity 수 검증 (목표: 10,000+)
- [ ] Graph 검색 쿼리 동작 확인
- [ ] PG-Neo4j entity_count 정합성 확인

---

## 의존성

- **선행**: Docker 환경 Health Check (Infra)
- **후행**: STORY-088 (Entity 라벨 수정), STORY-120 (ETL 재시도)
