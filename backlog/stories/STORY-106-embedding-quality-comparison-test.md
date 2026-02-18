# STORY-106: 임베딩 유무별 검색 품질 비교 테스트

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | - (Jira 이슈 한도 초과) |
| **Epic** | - |
| **Status** | Deferred (Sprint 12 project closure) |
| **Priority** | High |
| **Story Points** | 3 |
| **Assignee** | QA |
| **Sprint** | 08 |
| **Origin** | 스탠드업 액션 아이템 (2026-02-09) |

---

## User Story

**As a** 품질 관리자,
**I want** 임베딩 유무에 따른 검색 품질 차이를 정량적으로 비교할 수 있어,
**So that** 벡터 임베딩의 실제 효과를 데이터로 증명할 수 있다.

---

## Acceptance Criteria

- [ ] **Given** 동일 쿼리셋이 준비되면, **When** 벡터+키워드 검색과 키워드+그래프 검색을 실행하면, **Then** Precision@K, Recall@K, MRR이 비교된다
- [ ] **Given** 비교 결과가 나오면, **When** 리포트를 작성하면, **Then** RAGAS 메트릭 포함 비교표가 생성된다

---

## Tasks

- [ ] 테스트 쿼리셋 구성 (STORY-105 연계)
- [ ] 벡터+키워드 검색 결과 수집
- [ ] 키워드+그래프 검색 결과 수집
- [ ] 비교 리포트 생성

---

## 기술 노트

### 의존성
- STORY-100 (후속 임베딩 배치) 완료 후 실행 가능
- STORY-105 (RAGAS 평가 기준) 확정 후 평가 실행

---

## 참고 자료

- [스탠드업 2026-02-09](../../work_logs/standups/2026/02-February/2026-02-09_11-05.md)
