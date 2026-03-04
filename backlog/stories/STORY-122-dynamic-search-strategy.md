# STORY-122: 동적 검색 전략 선택 (rag_workflow.py Plan 단계 구현)

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | - |
| **Epic** | RAG 파이프라인 고도화 |
| **Status** | To Do |
| **Priority** | P2 |
| **Story Points** | 5 |
| **Assignee** | RAG |
| **Sprint** | Sprint 09 |

---

## User Story

**As a** 검색 사용자,
**I want** 질의 유형에 맞는 최적 검색 전략이 자동으로 선택되기를,
**So that** 검색 정확도가 향상되고 불필요한 지연이 줄어든다.

---

## 배경

현재 `rag_workflow.py:682`에 TODO 주석으로 항상 "hybrid" 전략만 반환.
모든 쿼리에 동일한 4-Way 검색 적용 → 단순 쿼리에도 과도한 처리.

---

## Acceptance Criteria

- [ ] 질의 유형 분류기 구현 (사실적/관계형/키워드/복합)
- [ ] 유형별 검색 전략 매핑
  - 사실적 질문 → vector 우선
  - 관계형 질문 → graph 우선
  - 키워드 검색 → BM25 우선
  - 복합 질문 → hybrid
- [ ] 검색 정확도 비교 테스트 (기존 vs 동적 전략)
- [ ] 예상 효과: 검색 정확도 +15~20%, 지연시간 -30%

---

## Tasks

- [ ] `rag_workflow.py:682` Plan 단계 구현
- [ ] 질의 유형 분류 로직 작성 (LLM 기반 or 규칙 기반)
- [ ] 전략별 검색 파라미터 조정
- [ ] A/B 테스트 (기존 항상 hybrid vs 동적 선택)

---

## 기술 노트

### 영향 범위
- `knowledge_service/src/app/agents/rag_workflow.py:682`

---

## 의존성

- **선행**: 없음
- **관련**: STORY-090 (성능 개선 연계), STORY-097 (A/B 평가)
