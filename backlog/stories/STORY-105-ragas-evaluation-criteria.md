# STORY-105: RAGAS 평가 기준 문서 확정

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-98 |
| **Epic** | - |
| **Status** | Closed - Project Completed (2026-02-18) |
| **Priority** | High |
| **Story Points** | 3 |
| **Assignee** | MLRag |
| **Sprint** | 08 |
| **Origin** | 스탠드업 액션 아이템 (2026-02-09) |

---

## User Story

**As a** QA 엔지니어,
**I want** RAGAS 평가 프레임워크의 기준이 문서화되어,
**So that** 일관된 품질 기준으로 검색 품질을 평가할 수 있다.

---

## Acceptance Criteria

- [ ] **Given** RAGAS 평가 문서가 작성되면, **When** 검토하면, **Then** 4가지 메트릭(Faithfulness, Relevancy, Context Recall, Context Precision) 목표값이 정의되어 있다
- [ ] **Given** 테스트 쿼리셋이 정의되면, **When** 확인하면, **Then** 최소 20개 쿼리가 포함되어 있다
- [ ] **Given** 평가 실행 방법이 문서화되면, **When** 따라하면, **Then** 누구나 동일한 방법으로 평가를 실행할 수 있다

---

## Tasks

- [ ] RAGAS 4가지 메트릭 목표값 정의 및 근거 작성
- [ ] 테스트 쿼리셋 (최소 20개) 구성
- [ ] 평가 실행 방법 및 리포팅 형식 문서화
- [ ] TechLead 리뷰

---

## 참고 자료

- [스탠드업 2026-02-09](../../work_logs/standups/2026/02-February/2026-02-09_11-05.md)
- Quality Metrics: Faithfulness > 0.9, Answer Relevancy > 0.85
