# STORY-108: InitialDataLoader 중복 방지 구현 (file_hash 기반)

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | - (Jira 이슈 한도 초과) |
| **Epic** | - |
| **Status** | Done |
| **Priority** | High |
| **Story Points** | 3 |
| **Assignee** | Data |
| **Sprint** | 08 |
| **Origin** | 스탠드업 액션 아이템 (2026-02-09) |

---

## User Story

**As a** 데이터 엔지니어,
**I want** InitialDataLoader가 파일 해시 기반으로 중복을 감지하여,
**So that** 동일 파일이 중복 적재되지 않고 데이터 정합성이 보장된다.

---

## Acceptance Criteria

- [x] **Given** 이미 적재된 파일과 동일한 파일이 업로드되면, **When** InitialDataLoader가 처리하면, **Then** 중복으로 감지하여 스킵한다
- [x] **Given** file_hash가 계산되면, **When** PG에 저장되면, **Then** SHA-256 해시값이 정확히 저장된다
- [ ] **Given** 기존 PG 중복 4건이 있으면, **When** 정리 스크립트를 실행하면, **Then** 중복이 제거되고 정합성이 검증된다

---

## Tasks

- [x] file_hash (SHA-256) 계산 로직 구현 (`_compute_file_hash()`)
- [x] PG documents 테이블에 file_hash 컬럼 - 이미 존재 (schema.sql L157)
- [x] 업로드 시 중복 체크 로직 (`_check_duplicate()` → PG 조회)
- [x] `document_repository.py` save()에 file_hash INSERT/UPSERT 추가
- [ ] 기존 PG 중복 4건 정리 마이그레이션 스크립트 (Phase 2)
- [ ] ES/Neo4j 정합성 검증 쿼리 (Phase 2)

---

## 기술 노트

### 배경
- PG 44행 중 4건 중복/변형 데이터 존재 (이전 수동 업로드 잔재)
- 3중 저장소(PG/ES/Neo4j) 정합성 유지 필수

---

## 참고 자료

- [스탠드업 2026-02-09](../../work_logs/standups/2026/02-February/2026-02-09_11-05.md)
