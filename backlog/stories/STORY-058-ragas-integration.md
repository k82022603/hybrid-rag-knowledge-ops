# STORY-058: RAGAS 평가 프레임워크 통합

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-48 |
| **Epic** | EPIC-002 |
| **Status** | Done |
| **Priority** | High |
| **Story Points** | 5 |
| **Assignee** | RAG |
| **Sprint** | 4 |

---

## User Story

**As a** RAG 시스템 품질 관리자,
**I want** 자체 구현한 faithfulness/relevance 평가를 RAGAS 표준 프레임워크로 교체,
**So that** 업계 표준 메트릭으로 RAG 품질을 측정하고 다른 시스템과 비교 가능한 벤치마크를 확보할 수 있음.

---

## Acceptance Criteria

- [ ] **Given** RAG 파이프라인 실행 결과(query, context, answer), **When** RAGAS 평가 실행, **Then** faithfulness 점수가 0~1 범위로 산출
- [ ] **Given** RAG 파이프라인 실행 결과, **When** RAGAS 평가 실행, **Then** answer_relevancy 점수가 0~1 범위로 산출
- [ ] **Given** 테스트 데이터셋(50개 이상 QA 쌍), **When** 배치 평가 실행, **Then** 전체 메트릭 요약 리포트 생성 (평균, 중위값, 분포)
- [ ] **Given** 자체 구현한 faithfulness/relevance 코드, **When** RAGAS 통합 완료, **Then** 자체 구현 코드 제거 또는 비활성화
- [ ] **Given** RAGAS 평가 실행, **When** 프로젝트 품질 목표 확인, **Then** Faithfulness > 0.9, Relevancy > 0.85 목표 대비 현재 수치 확인 가능

---

## Tasks

- [ ] RAGAS 라이브러리 설치 및 의존성 추가 (ragas >= 0.1.x)
- [ ] 테스트 데이터셋 준비 (query, ground_truth, context, answer)
- [ ] RAGAS faithfulness 메트릭 통합 (Claim decomposition 기반)
- [ ] RAGAS answer_relevancy 메트릭 통합 (Embedding similarity 기반)
- [ ] RAGAS context_precision, context_recall 메트릭 추가 (선택)
- [ ] 자체 구현 평가 코드와 RAGAS 결과 비교 분석
- [ ] 배치 평가 스크립트 작성 (전체 데이터셋 한 번에 평가)
- [ ] 평가 결과 리포트 템플릿 작성 (HTML 또는 Markdown)
- [ ] CI 파이프라인에 RAGAS 평가 단계 추가 (선택)

---

## 기술 노트

### 문제점 (Sprint 03 리뷰에서 도출)

Sprint 03에서 자체 구현한 RAG 평가 로직에 한계가 발견됨:

1. **비표준 메트릭** - 자체 구현한 faithfulness/relevance가 RAGAS 등 업계 표준과 방법론이 다름
2. **단순한 평가 방식** - 키워드 매칭 또는 코사인 유사도만 사용, claim decomposition 등 정교한 방법 부재
3. **벤치마크 불가** - 다른 RAG 시스템과 동일 기준으로 비교 불가능

### RAGAS 메트릭 설명

```
┌─────────────────────────────────────────────────────┐
│ RAGAS 핵심 메트릭                                     │
├─────────────────────────────────────────────────────┤
│ Faithfulness (충실도)                                 │
│   - 답변의 각 문장(claim)이 제공된 context에서        │
│     실제로 뒷받침되는지 검증                           │
│   - 방법: Claim decomposition → NLI 검증              │
│   - 목표: > 0.9                                      │
├─────────────────────────────────────────────────────┤
│ Answer Relevancy (답변 관련성)                         │
│   - 답변이 질문에 얼마나 관련있는지                    │
│   - 방법: 답변에서 질문 역생성 → 원래 질문과 유사도    │
│   - 목표: > 0.85                                     │
├─────────────────────────────────────────────────────┤
│ Context Precision (맥락 정밀도)                        │
│   - 검색된 문서 중 실제 관련 문서 비율                 │
├─────────────────────────────────────────────────────┤
│ Context Recall (맥락 재현율)                           │
│   - 필요한 정보가 검색된 문서에 포함된 비율            │
└─────────────────────────────────────────────────────┘
```

### 통합 코드 방향

```python
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy
from datasets import Dataset

# 평가 데이터셋 구성
eval_data = {
    "question": questions,
    "answer": answers,
    "contexts": contexts,
    "ground_truth": ground_truths,
}
dataset = Dataset.from_dict(eval_data)

# RAGAS 평가 실행
result = evaluate(
    dataset,
    metrics=[faithfulness, answer_relevancy],
    llm=get_eval_llm(),  # 평가용 LLM (DeepSeek 또는 GPT-4)
)

print(result)
# {'faithfulness': 0.92, 'answer_relevancy': 0.87}
```

### 영향 범위

- `knowledge_service/src/app/evaluation/` - RAGAS 평가 모듈 신규
- `knowledge_service/requirements.txt` - ragas 의존성 추가
- `knowledge_service/tests/evaluation/` - 평가 테스트
- `scripts/evaluate_rag.py` - 배치 평가 스크립트

---

## 테스트 계획

- [ ] Unit Test: RAGAS faithfulness 메트릭 정상 동작
- [ ] Unit Test: RAGAS answer_relevancy 메트릭 정상 동작
- [ ] Integration Test: 전체 데이터셋 배치 평가 실행
- [ ] Benchmark Test: 자체 구현 vs RAGAS 결과 비교
- [ ] Report Test: 평가 리포트 정상 생성 확인

---

## 참고 자료

- Sprint 03 완료 리뷰에서 도출 - 자체 평가 메트릭 한계
- [RAGAS Documentation](https://docs.ragas.io/)
- [RAGAS GitHub](https://github.com/explodinggradients/ragas)
- 프로젝트 품질 목표: Faithfulness > 0.9, Relevancy > 0.85
