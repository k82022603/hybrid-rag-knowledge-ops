# STORY-103: 검색 API 응답에 임베딩 유무 플래그 반영

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-96 |
| **Epic** | - |
| **Status** | Closed - Project Completed (2026-02-18) |
| **Priority** | High |
| **Story Points** | 2 |
| **Assignee** | Backend |
| **Sprint** | 08 |
| **Origin** | 스탠드업 액션 아이템 (2026-02-09) |

---

## User Story

**As a** 프론트엔드 개발자,
**I want** 검색 API 응답에 각 chunk의 임베딩 유무 플래그가 포함되어,
**So that** UI에서 벡터 검색 가능 여부를 사용자에게 표시할 수 있다.

---

## Acceptance Criteria

- [ ] **Given** 검색 API 호출 시, **When** 응답이 반환되면, **Then** 각 chunk에 `has_embedding: boolean` 필드가 포함된다
- [ ] **Given** 벡터 임베딩이 있는 chunk이면, **When** 응답에 포함되면, **Then** `has_embedding: true`로 표시된다

---

## Tasks

- [ ] 검색 API 응답 DTO에 has_embedding 필드 추가
- [ ] ES 쿼리에서 embedding 필드 존재 여부 확인 로직
- [ ] API 문서 업데이트

---

## 참고 자료

- [스탠드업 2026-02-09](../../work_logs/standups/2026/02-February/2026-02-09_11-05.md)
