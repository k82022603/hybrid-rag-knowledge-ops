# RAGAS 평가 파이프라인 가이드

**버전**: 2.0
**최종 수정**: 2026-02-04

---

## 개요

RAGAS(Retrieval Augmented Generation Assessment)는 RAG 시스템의 품질을 측정하는 프레임워크입니다. 이 문서는 평가 파이프라인 사용법과 Ground Truth 데이터셋 확장 방법을 설명합니다.

## 목차

1. [빠른 시작](#빠른-시작)
2. [평가 메트릭](#평가-메트릭)
3. [평가 모드](#평가-모드)
4. [CLI 사용법](#cli-사용법)
5. [Ground Truth 데이터셋 확장](#ground-truth-데이터셋-확장)
6. [프로그래밍 API](#프로그래밍-api)
7. [리포트 생성](#리포트-생성)
8. [품질 개선 가이드](#품질-개선-가이드)

---

## 빠른 시작

### 기본 평가 실행

```bash
cd knowledge_service

# 기본 테스트 데이터셋으로 평가
python scripts/run_ragas_eval.py

# Mock 모드 (API 키 없이)
python scripts/run_ragas_eval.py --mock

# 상세 결과 출력
python scripts/run_ragas_eval.py --verbose
```

### 리포트 생성

```bash
# Markdown + JSON 리포트 저장
python scripts/run_ragas_eval.py --output-dir ./docs/results/ragas

# 결과 파일:
# - ragas_evaluation_2026-02-04_123456.json
# - ragas_evaluation_2026-02-04_123456.md
```

---

## 평가 메트릭

| 메트릭 | 설명 | 목표 | 의미 |
|--------|------|------|------|
| **Faithfulness** | 컨텍스트 충실도 | 0.9 | 답변이 검색된 컨텍스트에 기반하는지 (환각 방지) |
| **Answer Relevancy** | 답변 관련성 | 0.85 | 답변이 질문과 직접 관련있는지 |
| **Context Precision** | 컨텍스트 정밀도 | 0.8 | 검색된 컨텍스트가 질문과 관련있는지 |
| **Context Recall** | 컨텍스트 재현율 | 0.7 | 필요한 정보가 검색되었는지 (Ground Truth 필요) |

### 메트릭 계산 방식

```
Faithfulness = (컨텍스트에 근거한 문장 수) / (전체 답변 문장 수)
Answer Relevancy = cosine_similarity(answer_embedding, question_embedding)
Context Precision = (관련 컨텍스트 수) / (전체 검색 컨텍스트 수)
Context Recall = (검색된 Ground Truth 정보 수) / (전체 Ground Truth 정보 수)
```

---

## 평가 모드

### 1. 정적 데이터셋 평가 (Static)

미리 준비된 QA 쌍으로 평가합니다. 답변과 컨텍스트가 이미 제공됩니다.

```bash
python scripts/run_ragas_eval.py --dataset test_dataset.json
```

**데이터셋 형식:**
```json
[
  {
    "question": "LangGraph란 무엇인가요?",
    "answer": "LangGraph는 상태 기반 에이전트 프레임워크입니다.",
    "contexts": [
      "LangGraph는 LangChain 기반의 상태 기반 에이전트 프레임워크입니다."
    ],
    "ground_truth": "LangGraph는 상태 기반 에이전트를 구축하는 프레임워크입니다."
  }
]
```

### 2. Live 평가 (Live)

실제 RAG 파이프라인을 실행하여 평가합니다. 시스템의 실제 성능을 측정합니다.

```bash
# Live 평가 (서비스 실행 필요)
python scripts/run_ragas_eval.py --live --questions questions.json --output-dir ./reports
```

**질문 파일 형식:**
```json
[
  {"question": "RAG란 무엇인가요?", "ground_truth": "RAG는 검색 기반 생성입니다"},
  {"question": "LangGraph란?", "ground_truth": "상태 기반 프레임워크입니다"}
]
```

또는 간단한 형식:
```json
["RAG란 무엇인가요?", "LangGraph란?"]
```

---

## CLI 사용법

### 기본 명령어

```bash
python scripts/run_ragas_eval.py [OPTIONS]
```

### 주요 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--dataset` | 정적 데이터셋 경로 | `src/tests/evaluation/test_dataset.json` |
| `--metrics` | 평가 메트릭 (쉼표 구분) | `faithfulness,answer_relevancy,context_precision` |
| `--output` | JSON 결과 파일 경로 | None |
| `--output-dir` | 리포트 출력 디렉토리 | None |
| `--live` | Live 모드 활성화 | False |
| `--questions` | Live 모드 질문 파일 | None |
| `--top-k` | Live 모드 검색 결과 수 | 5 |
| `--mock` | Mock 평가 (API 키 불필요) | False |
| `--verbose`, `-v` | 상세 출력 | False |

### 목표 점수 옵션

| 옵션 | 기본값 |
|------|--------|
| `--faithfulness-target` | 0.9 |
| `--relevancy-target` | 0.85 |
| `--precision-target` | 0.8 |
| `--recall-target` | 0.7 |

### 사용 예시

```bash
# 전체 메트릭 평가 + 리포트 저장
python scripts/run_ragas_eval.py \
  --metrics faithfulness,answer_relevancy,context_precision,context_recall \
  --output-dir ./docs/results/ragas \
  --verbose

# 커스텀 목표 점수로 평가
python scripts/run_ragas_eval.py \
  --faithfulness-target 0.85 \
  --relevancy-target 0.80 \
  --output results.json

# Live 평가 (RAG 서비스 필요)
python scripts/run_ragas_eval.py \
  --live \
  --questions qa_samples.json \
  --top-k 10 \
  --output-dir ./live_results
```

---

## Ground Truth 데이터셋 확장

### 현재 데이터셋

위치: `src/tests/evaluation/test_dataset.json`
- 24개 QA 샘플
- 기술 도메인 (RAG, LangGraph, Elasticsearch 등)

### 확장 가이드라인

#### 1. 새 도메인 샘플 추가

```json
{
  "question": "Circuit Breaker 패턴의 상태 전이는 어떻게 되나요?",
  "answer": "Circuit Breaker는 Closed -> Open -> Half-Open 상태로 전이됩니다. Closed에서 실패율이 임계값을 초과하면 Open으로 전환되고, 일정 시간 후 Half-Open에서 성공 여부를 확인합니다.",
  "contexts": [
    "Circuit Breaker는 Closed, Open, Half-Open 세 가지 상태를 가집니다.",
    "Closed 상태에서 실패율이 임계값(예: 50%)을 초과하면 Open 상태로 전환됩니다.",
    "Open 상태에서 일정 시간(cooldown)이 지나면 Half-Open 상태가 됩니다."
  ],
  "ground_truth": "Circuit Breaker는 Closed(정상) -> Open(차단) -> Half-Open(테스트) 상태로 전이되며, 실패율에 따라 상태가 변경됩니다."
}
```

#### 2. 샘플 품질 기준

| 기준 | 설명 |
|------|------|
| **질문 명확성** | 단일 주제에 대한 명확한 질문 |
| **답변 정확성** | 컨텍스트에 근거한 정확한 답변 |
| **컨텍스트 관련성** | 질문과 직접 관련된 컨텍스트 2-4개 |
| **Ground Truth** | 핵심 내용을 포함한 간결한 정답 |

#### 3. 확장 시나리오

**A. 다양한 질문 유형**
```json
// 정의형 질문
{"question": "Gleaning 기법이란 무엇인가요?", ...}

// 비교형 질문
{"question": "GraphRAG와 일반 RAG의 차이점은?", ...}

// 방법형 질문
{"question": "JWT 토큰은 어떻게 검증하나요?", ...}

// 목록형 질문
{"question": "RAGAS 평가 메트릭에는 어떤 것들이 있나요?", ...}
```

**B. 복잡도 레벨**
```
Level 1: 단순 정의/설명 (1-hop)
Level 2: 관계/비교 (2-hop)
Level 3: 다중 개념 통합 (multi-hop)
```

**C. 도메인별 분류**
```
- rag/: RAG 관련 샘플
- infra/: 인프라/DevOps 샘플
- backend/: 백엔드 기술 샘플
- frontend/: 프론트엔드 기술 샘플
```

#### 4. 데이터셋 파일 구조

```
src/tests/evaluation/
├── test_dataset.json          # 기본 통합 테스트셋 (24개)
├── extended/
│   ├── rag_advanced.json      # RAG 심화 샘플
│   ├── domain_specific.json   # 도메인 특화 샘플
│   └── edge_cases.json        # 엣지 케이스 샘플
└── questions/
    ├── live_eval_basic.json   # Live 평가용 기본 질문
    └── live_eval_advanced.json # Live 평가용 심화 질문
```

#### 5. 샘플 생성 도구

**자동 생성 프롬프트:**
```
다음 문서 내용을 기반으로 RAGAS 평가용 QA 샘플을 생성해주세요:

[문서 내용]
...

출력 형식:
{
  "question": "...",
  "answer": "...",
  "contexts": ["...", "..."],
  "ground_truth": "..."
}

규칙:
1. 질문은 명확하고 구체적이어야 합니다
2. 답변은 컨텍스트에만 근거해야 합니다
3. 컨텍스트는 2-4개가 적절합니다
4. Ground Truth는 핵심 내용만 포함합니다
```

---

## 프로그래밍 API

### RagasEvaluator (정적 평가)

```python
from app.evaluation import RagasEvaluator, EvaluationSample

# 초기화
evaluator = RagasEvaluator(
    targets={
        "faithfulness": 0.9,
        "answer_relevancy": 0.85,
    }
)

# 샘플 생성
samples = [
    EvaluationSample(
        question="RAG란 무엇인가요?",
        answer="RAG는 검색 기반 생성입니다.",
        contexts=["RAG(Retrieval-Augmented Generation)는..."],
        ground_truth="RAG는 검색 증강 생성입니다.",
    )
]

# 평가 실행
response = await evaluator.evaluate(
    samples=samples,
    metrics=["faithfulness", "answer_relevancy"],
)

print(f"Faithfulness: {response.aggregate_scores.faithfulness}")
print(f"Pass Rate: {response.pass_rate:.1%}")
```

### LiveRagasEvaluator (Live 평가)

```python
from app.evaluation import LiveRagasEvaluator

# 초기화
evaluator = LiveRagasEvaluator()

# 질문으로 Live 평가
questions = ["RAG란?", "LangGraph란?"]
ground_truths = ["검색 기반 생성", "상태 기반 프레임워크"]

response, rag_responses = await evaluator.evaluate_live(
    questions=questions,
    ground_truths=ground_truths,
    top_k=5,
    metrics=["faithfulness", "answer_relevancy"],
)

# RAG 응답 확인
for r in rag_responses:
    print(f"Q: {r['question'][:50]}")
    print(f"A: {r['answer'][:100]}...")
    print(f"Latency: {r['latency_ms']:.1f}ms")
```

### RagasReportGenerator (리포트)

```python
from app.evaluation import RagasReportGenerator

generator = RagasReportGenerator(
    project_name="Hybrid RAG Platform",
    include_details=True,
)

# Markdown 리포트 생성
md_report = generator.generate_markdown(response)

# 파일 저장
saved = generator.save_reports(
    response=response,
    output_dir="./reports",
)
print(f"JSON: {saved['json']}")
print(f"Markdown: {saved['markdown']}")
```

---

## 리포트 생성

### Markdown 리포트 예시

```markdown
# RAGAS 평가 리포트

**프로젝트**: Hybrid RAG Knowledge Platform
**평가 시간**: 2026-02-04 12:34:56 UTC
**평가 샘플 수**: 24

## 평가 요약

| 지표 | 점수 | 목표 | 달성 여부 |
|------|------|------|----------|
| Faithfulness (충실도) | 0.8523 | 0.90 | x FAIL |
| Answer Relevancy (답변 관련성) | 0.8745 | 0.85 | v PASS |
| Context Precision (컨텍스트 정밀도) | 0.8012 | 0.80 | v PASS |

### 통과율
- **통과 샘플**: 18 / 24
- **통과율**: 75.0%

> **[FAIL]** 목표 미달 지표: faithfulness

## 개선 권장 사항

- **Faithfulness 개선**: 환각을 줄이기 위해 프롬프트를 강화하세요.
```

---

## 품질 개선 가이드

### Faithfulness 개선

| 문제 | 해결책 |
|------|--------|
| 환각(Hallucination) | 프롬프트에 "컨텍스트에 없으면 모른다고 답변" 추가 |
| 불필요한 추가 정보 | 답변 길이 제한, 간결성 강조 |

### Answer Relevancy 개선

| 문제 | 해결책 |
|------|--------|
| 질문 키워드 누락 | 질문 핵심어를 답변에 포함하도록 유도 |
| 간접적 답변 | 직접적인 답변을 먼저 제시하도록 프롬프트 수정 |

### Context Precision 개선

| 문제 | 해결책 |
|------|--------|
| 관련 없는 컨텍스트 | Reranker 적용 또는 강화 |
| 검색 품질 낮음 | 임베딩 모델 최적화, 청킹 전략 조정 |

### Context Recall 개선

| 문제 | 해결책 |
|------|--------|
| 정보 누락 | top_k 증가, Hybrid Search 활용 |
| 특정 도메인 약함 | 도메인 특화 데이터 추가 인덱싱 |

---

## 참고 자료

- [RAGAS 공식 문서](https://docs.ragas.io/)
- [LangChain Evaluation](https://python.langchain.com/docs/guides/evaluation/)
- [프로젝트 상세 설계서](../02_design/hybrid_rag_platform_detailed_design.md)

---

*Generated by MLRag Agent - 2026-02-04*
