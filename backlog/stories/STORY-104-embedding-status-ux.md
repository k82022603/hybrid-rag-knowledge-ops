# STORY-104: 검색 결과에 임베딩 상태 표시 UX

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-97 |
| **Epic** | - |
| **Status** | Deferred (Sprint 12 project closure) |
| **Priority** | Medium |
| **Story Points** | 2 |
| **Assignee** | Frontend |
| **Sprint** | 08 |
| **Origin** | 스탠드업 액션 아이템 (2026-02-09) |

---

## User Story

**As a** 검색 사용자,
**I want** 검색 결과에서 벡터 검색 가능 여부가 시각적으로 구분되어,
**So that** 검색 결과의 신뢰도를 직관적으로 파악할 수 있다.

---

## Acceptance Criteria

- [ ] **Given** has_embedding=true인 결과이면, **When** 검색 결과 카드에 표시되면, **Then** 벡터 뱃지가 표시된다
- [ ] **Given** has_embedding=false인 결과이면, **When** 검색 결과 카드에 표시되면, **Then** 키워드 전용 표시가 된다

---

## Tasks

- [ ] 임베딩 상태 뱃지 컴포넌트 구현
- [ ] 검색 결과 카드에 뱃지 통합
- [ ] 검색 품질 인디케이터 추가

---

## 기술 노트

### 의존성
- STORY-103 (Backend 임베딩 플래그 API) 완료 후 진행

---

## 참고 자료

- [스탠드업 2026-02-09](../../work_logs/standups/2026/02-February/2026-02-09_11-05.md)
