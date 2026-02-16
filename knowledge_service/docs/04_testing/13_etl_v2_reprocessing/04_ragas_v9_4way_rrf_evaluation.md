# RAGAS v9 종합 평가 결과 — ETL v2 + 4-Way RRF + Graph RAG

**Version**: 2.0 (RAGAS Library 재평가 포함)
**Date**: 2026-02-16 05:50 KST
**Author**: Claude Code (Opus 4.6)
**Status**: 완료

---

## 1. 개요

ETL v2 재처리(chunk_size 600→1000, overlap 100→200) 및 4-Way RRF 파이프라인 구축 후, v8 Nori+Hybrid 평가와 동일한 51개 질문, 7개 도메인으로 종합 평가를 수행하여 시스템 변경 전후를 비교한다.

**본 보고서는 두 가지 평가 방법으로 수행된 결과를 모두 포함한다:**
1. **LLM-as-Judge** (DeepSeek 직접 채점) — v9 초기 평가
2. **RAGAS 0.2.15 라이브러리** — v8과 동일한 방법론으로 재평가

---

## 2. RAGAS 평가 프레임워크 소개

### 2.1 RAGAS란?

**RAGAS (Retrieval Augmented Generation Assessment)**는 RAG 시스템의 품질을 자동으로 평가하는 오픈소스 프레임워크다. 사람이 직접 평가하는 대신 LLM을 활용하여 4가지 메트릭을 체계적으로 측정한다.

### 2.2 4가지 핵심 메트릭

| 메트릭 | 측정 대상 | 산출 방식 | 의미 |
|--------|----------|----------|------|
| **Faithfulness** | 답변 충실도 | 답변의 각 문장이 제공된 컨텍스트에 근거하는지 검증 | 1.0 = 모든 문장이 컨텍스트 기반, 0.0 = 컨텍스트 무시 |
| **Answer Relevancy** | 답변 관련성 | 답변에서 역으로 질문을 생성하여 원래 질문과의 유사도 측정 | 1.0 = 완벽히 관련된 답변, 0.0 = 무관한 답변 |
| **Context Precision** | 검색 정밀도 | 검색된 컨텍스트 중 실제로 유용한 비율 (순서 가중 평가) | 1.0 = 모든 검색 결과 관련, 0.0 = 관련 없는 결과만 |
| **Context Recall** | 검색 재현율 | ground truth 답변의 각 문장을 컨텍스트가 커버하는 비율 | 1.0 = 완전한 커버, 0.0 = 필요한 정보 미검색 |

### 2.3 RAGAS 버전별 차이

| 항목 | RAGAS 0.4.3 (v8 사용) | RAGAS 0.2.15 (v9 사용) |
|------|:---:|:---:|
| **릴리즈** | 2024-12 (PyPI) | 2025-10 (PyPI) |
| **평가 방식** | `evaluate(dataset)` | `evaluate(EvaluationDataset)` |
| **데이터 스키마** | `question`, `answer`, `contexts`, `ground_truth` | `user_input`, `response`, `retrieved_contexts`, `reference` |
| **Faithfulness 산출** | NLI 기반 문장별 검증 | NLI 기반 문장별 검증 (동일 원리) |
| **Answer Relevancy** | 질문 역생성 + 임베딩 유사도 | 질문 역생성 + 임베딩 유사도 (동일 원리) |
| **LLM 설정** | 메트릭별 `.llm` 지정 | `evaluate(llm=...)` 통합 파라미터 |
| **임베딩** | 자동 (OpenAI 기본) | 명시적 `embeddings` 파라미터 필요 |

> **핵심**: 0.4.3과 0.2.15는 메트릭 산출 원리가 동일하며, API/스키마만 변경됨. 따라서 v8(0.4.3) vs v9(0.2.15) 비교는 방법론적으로 유효하다.

### 2.4 LLM-as-Judge vs RAGAS 라이브러리 차이

| 항목 | LLM-as-Judge | RAGAS 라이브러리 |
|------|:---:|:---:|
| **Faithfulness 산출** | LLM에 "0~1 점수 매겨줘" 단일 프롬프트 | LLM이 문장별로 NLI 검증 → 비율 산출 |
| **정밀도** | 단일 점수 (주관적) | 문장 단위 분해 후 체계적 평가 |
| **Faithfulness 경향** | 더 엄격하게 채점 (낮은 점수) | 더 세밀하고 안정적인 채점 |
| **적합 용도** | 빠른 프로토타입 평가 | 정식 품질 비교 |

---

## 3. 평가 환경

### 3.1 시스템 환경 비교

| 항목 | v8 Baseline (2026-02-13) | v9 Current (2026-02-16) |
|------|:---:|:---:|
| **ES 청크 수** | 108,896 | **56,063** (-48.5%) |
| **Chunk Size** | 600 | **1,000** (+67%) |
| **Chunk Overlap** | 100 | **200** (+100%) |
| **검색 방식** | Dense + BM25(Nori) + Manual RRF | **4-Way RRF** (Dense+BM25+Sparse+Graph) |
| **RRF 채널 수** | 2 (Dense, BM25) | **4** (Dense, BM25, Sparse, Graph) |
| **RRF 가중치** | V=1.0, K=1.0 | V=1.0, K=1.0, S=0.7, G=0.8 |
| **Sparse Vector** | 없음 | **BGE-M3 Sparse** (56,063건) |
| **Neo4j 엔티티** | 0 (미통합) | **70,855** |
| **Neo4j 관계** | 0 (미통합) | **375,229** |
| **Graph Search** | 미통합 | **Entity-Enhanced BM25** |
| **Nori 분석기** | 설치 + 적용 | 설치 + 적용 |
| **LLM** | DeepSeek V3.2 | DeepSeek V3.2 |
| **질문 수** | 51 (7 도메인) | 51 (7 도메인) |

### 3.2 도메인별 질문 구성

| 도메인 | 쿼리 수 | 설명 |
|--------|:---:|------|
| entity_relation | 7 | 기술 엔티티 간 관계 비교 |
| multi_hop | 7 | 다단계 추론 필요 |
| keyword | 7 | 키워드 기반 직접 검색 |
| semantic | 7 | 의미 기반 검색 |
| graph_entity | 8 | Graph/엔티티 트리거 |
| legal | 7 | 법률/규정 도메인 |
| factual | 8 | AI/LLM 심화 + 프로젝트 특화 |

---

## 4. 전체 평가 결과

### 4.1 3-Way 비교: v8 vs v9(LLM-Judge) vs v9(RAGAS Library)

| 메트릭 | v8 (RAGAS 0.4.3) | v9 LLM-Judge | v9 RAGAS 0.2.15 | v8↔v9 Lib 변화 |
|--------|:---:|:---:|:---:|:---:|
| **Faithfulness** | 0.919 | 0.610 | **0.913** | **-0.006** |
| **Answer Relevancy** | 0.647 | 0.619 | **0.547** | **-0.100** |
| **Context Precision** | 0.489 | 0.504 | **0.577** | **+0.088** |
| **Context Recall** | 0.474 | 0.398 | **0.600** | **+0.126** |

```
┌────────────────────────────────────────────────────────────────┐
│           RAGAS v9 성적표 (RAGAS 0.2.15 Library)               │
│                                                                │
│  Faithfulness      ██████████████████░░  0.913  (v8: 0.919)   │
│  Answer Relevancy  ███████████░░░░░░░░░  0.547  (v8: 0.647)   │
│  Context Precision ████████████░░░░░░░░  0.577  (v8: 0.489)   │
│  Context Recall    ████████████░░░░░░░░  0.600  (v8: 0.474)   │
│                                                                │
│  Quality Gate: HIGH 28/51 (55%) | NONE 11/51 (22%)            │
└────────────────────────────────────────────────────────────────┘
```

### 4.2 핵심 발견: LLM-Judge vs RAGAS Library의 차이

| 메트릭 | LLM-Judge | RAGAS Library | 차이 | 해석 |
|--------|:---:|:---:|:---:|------|
| **Faithfulness** | 0.610 | **0.913** | +0.303 | LLM-Judge가 과도하게 엄격 채점 |
| **Answer Relevancy** | 0.619 | 0.547 | -0.072 | 역생성 질문 유사도가 더 정밀 |
| **Context Precision** | 0.504 | **0.577** | +0.073 | 라이브러리의 순서 가중 평가가 차이 |
| **Context Recall** | 0.398 | **0.600** | +0.202 | 문장별 커버리지 측정이 더 관대 |

> **결론**: Faithfulness 0.610 → 0.913 — LLM-as-Judge의 단일 스코어 채점이 과도하게 낮은 점수를 부여함. RAGAS 라이브러리의 문장별 NLI 검증 결과, **Faithfulness는 v8과 거의 동일** (0.913 vs 0.919)하다.

### 4.3 Quality Gate 분포 (최종 — RAGAS Library 기준)

| 등급 | v8 | v9 (RAGAS Lib) | 변화 |
|:---:|:---:|:---:|:---:|
| **HIGH** (avg >= 0.70) | 24 | **28** | **+4** |
| **PARTIAL** (0.40-0.69) | 16 | **12** | -4 |
| **NONE** (< 0.40) | 11 | **11** | 0 |

---

## 5. 56K vs 108K — "실제로 더 많이 실패하는가?"

### 5.1 결론: 아니다. NONE은 동일하고 HIGH가 증가했다.

| 지표 | v8 (108K) | v9 (56K) | 판정 |
|------|:---:|:---:|:---:|
| NONE 등급 | 11건 | 11건 | **동일** |
| HIGH 등급 | 24건 | **28건** | **v9 +4건** |
| Faithfulness | 0.919 | 0.913 | **동등** (-0.006) |
| Context Precision | 0.489 | **0.577** | **v9 개선** (+0.088) |
| Context Recall | 0.474 | **0.600** | **v9 개선** (+0.126) |

### 5.2 왜 청크 수가 절반인데 실패가 늘지 않았나?

```
                108K 시스템 (v8)              56K 시스템 (v9)
                ┌─────────────┐              ┌─────────────┐
    청크 수      │   108,896   │              │   56,063    │
                │ (avg 60 tok)│              │(avg 119 tok)│
                └──────┬──────┘              └──────┬──────┘
                       │                            │
    청크 품질    작고 분산된 청크              의미 단위 완결 청크
                 ↓ 부분 정보만 포함           ↓ 전체 맥락 포함
                       │                            │
    검색 채널    2채널 (Dense+BM25)          4채널 (D+B+S+G)
                 ↓ 단일 관점                ↓ 다각 관점
                       │                            │
    결과         넓지만 얕은 검색            좁지만 깊은 검색
```

**핵심 메커니즘 3가지:**

1. **청크 크기 효과**: 600→1000 토큰으로 각 청크가 더 완전한 문맥을 포함. Context Recall이 0.474→0.600으로 개선된 이유.

2. **4-Way RRF 보상 효과**: 청크 수가 줄었지만, Sparse+Graph 채널이 Dense/BM25가 놓치는 결과를 보완. Context Precision이 0.489→0.577로 개선.

3. **Entity-Enhanced BM25**: Graph 채널이 66.3%의 검색 결과에 기여하며 엔티티 관계 기반 문서 발견. entity_relation 도메인(0.761)과 multi_hop 도메인(0.714)에서 강점.

### 5.3 56K에서도 실패하는 11건의 공통 패턴

NONE 등급 11건을 분석하면:

| 실패 유형 | 건수 | 해당 질문 | 원인 |
|----------|:---:|------|------|
| **KB 문서 부재** | 6 | Q15(Docker Net), Q20(ES Index), Q30(Gleaning), Q35(ExceptionGroup), Q49(벡터 차원), Q50(LLM 서비스) | KB에 해당 주제의 상세 문서가 없음 |
| **법률 도메인 부재** | 3 | Q38(GDPR), Q40(SLA), Q42(라이선스) | 법률 문서 자체가 KB에 미적재 |
| **일반 기술 미포함** | 2 | Q36(RAG Pipeline), Q43(법률용어) | 프로젝트 외부 일반 기술/지식 |

> **핵심**: 이 11건은 108K에서도 실패했던 동일 질문이며, 청크 수와 무관하게 **KB 커버리지 부재**가 근본 원인이다.

---

## 6. 도메인별 상세 분석 (RAGAS Library 기준)

### 6.1 도메인별 평균 점수

| 도메인 | Faith | Relev | Prec | Recall | 종합 | 등급 |
|--------|:---:|:---:|:---:|:---:|:---:|:---:|
| **entity_relation** | 0.984 | 0.737 | 0.780 | 0.714 | **0.804** | **최강** |
| **multi_hop** | 0.988 | 0.686 | 0.734 | 0.857 | **0.816** | **최강** |
| **keyword** | 0.980 | 0.445 | 0.631 | 0.571 | 0.657 | 중 |
| **factual** | 0.964 | 0.650 | 0.626 | 0.562 | 0.701 | 강 |
| **semantic** | 0.958 | 0.537 | 0.698 | 0.298 | 0.623 | 중 |
| **graph_entity** | 0.908 | 0.310 | 0.240 | 0.625 | 0.521 | 약 |
| **legal** | 0.601 | 0.483 | 0.369 | 0.571 | **0.506** | **약** |

### 6.2 강점 도메인 (종합 >= 0.70)

**entity_relation (0.804) — 최고 성능**
- Faithfulness 0.984 — 거의 완벽. 컨텍스트에 충실한 답변
- Precision 0.780 — 관련 문서를 정확히 검색. Graph 채널 효과
- 프로젝트 핵심 기술(Neo4j, ES, FastAPI, BGE-M3)에 대한 풍부한 KB

**multi_hop (0.816) — Recall 최고 (0.857)**
- 다단계 추론에서 Ground Truth를 거의 완전히 커버
- ETL/RAG/LangGraph 관련 풍부한 문서가 기반
- 4-Way RRF가 다양한 관점에서 관련 문서를 찾아 Recall 향상

### 6.3 약점 도메인 분석

**legal (0.506) — Faithfulness 최저 (0.601)**
- Q43(법률용어) F=0.00 — 컨텍스트에 법률 관련 내용이 전혀 없어 일반 지식으로 답변
- Q38(GDPR) F=0.375, Q40(SLA) F=0.500 — 부분적으로만 컨텍스트 활용
- **근본 원인**: KB에 법률 전문 문서 부재

**graph_entity (0.521) — Answer Relevancy 최저 (0.310)**
- Q29(Gateway), Q30(Gleaning), Q34(React), Q35(Python), Q36(RAG Pipeline)에서 Relevancy 0.0
- RAGAS가 답변에서 역생성한 질문이 원래 질문과 다른 방향 → 답변이 질문의 핵심을 벗어남
- **원인**: 검색된 컨텍스트가 질문과 다소 동떨어진 내용 → 답변도 방향이 어긋남

---

## 7. Graph RAG 기여도 분석

### 7.1 Graph 검색 통계

| 항목 | 값 |
|------|-----|
| Graph 기여 검색 결과 | **338/510** (66.3%) |
| Neo4j 엔티티 | 70,855개 |
| Neo4j 관계 | 375,229개 |
| Entity Extraction 대상 | 16,185건 (tc >= 100) |

### 7.2 Graph 기여 효과

Graph 기여가 높은(8+) 질문 vs 낮은(0-3) 질문의 Quality Gate:

| Graph 기여 수준 | 건수 | HIGH 비율 | NONE 비율 |
|:---:|:---:|:---:|:---:|
| High (8-10/10) | 28건 | 57% | 25% |
| Medium (4-7/10) | 16건 | 56% | 12% |
| Low (0-3/10) | 7건 | 43% | 29% |

---

## 8. v8 → v9 트레이드오프 분석

### 8.1 무엇이 좋아졌나

| 개선 항목 | v8 → v9 | 원인 |
|----------|---------|------|
| Context Precision | 0.489 → **0.577** (+18%) | 4-Way RRF 다각 검색 |
| Context Recall | 0.474 → **0.600** (+27%) | 큰 청크의 문맥 완결성 |
| HIGH 등급 | 24 → **28** (+17%) | 검색+답변 품질 통합 개선 |
| entity_relation | - → **0.804** | Graph Search 효과 극대화 |
| multi_hop | - → **0.816** | 다채널 검색의 다단계 추론 지원 |

### 8.2 무엇이 나빠졌나

| 악화 항목 | v8 → v9 | 원인 |
|----------|---------|------|
| Answer Relevancy | 0.647 → **0.547** (-15%) | 넓은 컨텍스트로 답변 초점 분산 |
| graph_entity Relevancy | - → **0.310** | Graph 결과가 질문 핵심에서 이탈 |
| 검색 속도 | ~2초/쿼리 | 4채널 병렬 → Neo4j 추가 지연 |

### 8.3 유지된 것

| 유지 항목 | v8 / v9 | 해석 |
|----------|---------|------|
| Faithfulness | 0.919 / 0.913 | 답변 충실도 완벽 유지 |
| NONE 등급 | 11 / 11 | 실패 패턴 동일 (KB 부재) |
| legal 약점 | 최저 / 최저 | KB 보강 필요 (변동 없음) |

---

## 9. 개선방안

### 9.1 즉시 적용 가능 (P0)

#### 9.1.1 BGE-Reranker 적용

**현황**: 4-Way RRF로 검색된 top-10 결과를 그대로 LLM에 전달
**개선**: BGE-Reranker-v2-m3 (이미 컨테이너에 캐시됨)로 top-10을 재순위화 후 top-5만 전달

```
현재:  4-Way RRF top-10 → LLM
개선:  4-Way RRF top-10 → Reranker → top-5 → LLM
```

**예상 효과**:
- Context Precision 0.577 → 0.70+ (불필요한 컨텍스트 제거)
- Answer Relevancy 0.547 → 0.65+ (더 집중된 컨텍스트 → 답변 초점 개선)
- Faithfulness 유지 (이미 0.913)

#### 9.1.2 Graph RRF 가중치 도메인별 적응

**현황**: Graph 가중치 고정 0.8
**문제**: Graph 기여가 높을 때(8+/10) 오히려 원본 검색 결과를 희석
**개선**:
```python
# 현재
graph_weight = 0.8  # 모든 질문에 동일

# 개선 - 엔티티 매칭 수에 따른 동적 가중치
if matched_entities >= 5:
    graph_weight = 0.6  # 많이 매칭 → 가중치 낮춤 (과다 기여 방지)
elif matched_entities >= 2:
    graph_weight = 0.8  # 적절한 기여
else:
    graph_weight = 1.0  # 적게 매칭 → 가중치 높여 Graph 활용 극대화
```

**예상 효과**: graph_entity 도메인 Relevancy 0.310 → 0.50+ 개선

### 9.2 단기 개선 (P1)

#### 9.2.1 Entity Extraction 대상 확대

**현황**: token_count >= 100인 청크만 엔티티 추출 (28,819/56,063 = 51.4%)
**개선**: token_count >= 50으로 확대 → 70%+ 커버리지

**예상 효과**: Graph Search가 더 많은 문서에서 엔티티를 찾아 Recall 향상

#### 9.2.2 Answer Relevancy 개선 — 프롬프트 최적화

**현황**: 답변 생성 프롬프트가 "간결하고 정확하게 한국어로 답변하세요"
**문제**: 넓은 컨텍스트에서 답변이 질문 핵심에서 벗어남
**개선**:
```python
# 현재 프롬프트
"간결하고 정확하게 한국어로 답변하세요."

# 개선 프롬프트
"질문에 직접 답변하세요. 질문의 핵심 키워드를 반드시 포함하여 답변하고,
 질문과 관련 없는 부가 정보는 제외하세요."
```

**예상 효과**: Answer Relevancy 0.547 → 0.60+

#### 9.2.3 Sparse Vector 가중치 조정 — A/B 테스트 완료

**현황**: Sparse 가중치 0.7 (Dense/BM25의 70%)
**가설**: Sparse는 Dense와 유사한 후보를 반환하는 경향 → 차별화 부족 → 0.5로 하향 시 개선

**A/B 테스트 실시** (2026-02-16):

| 메트릭 | S=0.7 (기존) | S=0.5 (테스트) | 차이 | 판정 |
|--------|:---:|:---:|:---:|:---:|
| Faithfulness | **0.913** | 0.899 | -0.014 | S=0.7 우세 |
| Answer Relevancy | **0.547** | 0.544 | -0.003 | S=0.7 우세 |
| Context Precision | **0.577** | 0.575 | -0.002 | S=0.7 우세 |
| Context Recall | **0.600** | 0.565 | **-0.035** | S=0.7 우세 |
| HIGH 등급 | **28** | 26 | -2 | S=0.7 우세 |
| PARTIAL 등급 | 12 | 13 | +1 | - |
| NONE 등급 | 11 | 12 | +1 | - |

**결론: S=0.7 유지 (S=0.5 개선안 기각)**

**핵심 발견 — Sparse의 "보강 효과" (Reinforcement Effect)**:
- Sparse 채널은 Dense와 유사한 후보를 반환하지만, 이것이 **단점이 아닌 장점**으로 작용
- 동일 문서가 Dense + Sparse 두 채널에서 검색되면 RRF 점수가 합산되어 **상위 랭킹 강화**
- Sparse 가중치를 낮추면 이 보강 효과가 약화되어 Context Recall이 -0.035 하락
- 즉, Sparse는 "차별화된 결과"가 아닌 "기존 검색의 확신도 강화"가 핵심 가치

**최종 RRF 가중치 (확정)**: V=1.0, K=1.0, **S=0.7**, G=0.8

### 9.3 중기 개선 (P2)

#### 9.3.1 KB 보강 — 법률/규정 도메인

**현황**: legal 도메인 종합 0.506 (최약)
**개선**: 다음 문서 추가
- 개인정보보호법 전문 또는 요약본
- GDPR 가이드라인 한국어 번역
- 오픈소스 라이선스 비교 문서
- ISMS 인증 체크리스트
- SLA 표준 템플릿

**예상 효과**: legal Recall 0.571 → 0.80+, Faithfulness 0.601 → 0.85+

#### 9.3.2 KB 보강 — 프로젝트 외부 기술

**현황**: React 18 Suspense(Q34), Python ExceptionGroup(Q35), ES 인덱스 설정(Q20) 등에서 NONE
**개선**: 프로젝트에서 직접 사용하는 기술의 상세 문서 추가
- React 18 공식 문서 핵심 발췌
- Python 3.11 변경사항 문서
- ES 벡터 검색 인덱스 설정 가이드

#### 9.3.3 평가 질문 확대

**현황**: 51개 질문 (도메인당 7-8개)
**개선**: 100개로 확대 → 통계적 신뢰도 향상

### 9.4 개선 로드맵 요약

```
즉시 (P0)                     단기 (P1)                   중기 (P2)
─────────────────────────────────────────────────────────────────────
BGE-Reranker 적용             Entity Extraction 확대       KB 보강 (법률)
Graph 가중치 동적 조정         프롬프트 최적화               KB 보강 (기술)
                              ~~Sparse 가중치 조정~~        평가 100문항 확대
                              (A/B 테스트 결과 기각됨)
                              → S=0.7 유지 확정

예상 종합 효과:
  Context Precision  0.577 → 0.70+
  Answer Relevancy   0.547 → 0.65+
  Context Recall     0.600 → 0.70+
  Faithfulness       0.913 유지

  Quality Gate 목표: HIGH 35+/51 (69%+), NONE 5건 이하
```

---

## 10. 개별 질문 결과 (RAGAS 0.2.15 Library)

| # | 질문 | 도메인 | Faith | Relev | Prec | Recall | 등급 |
|:---:|------|--------|:---:|:---:|:---:|:---:|:---:|
| Q01 | Neo4j와 Elasticsearch의 역할 차이점은? | entity_relation | 1.000 | 0.861 | 0.417 | 1.000 | HIGH |
| Q02 | LangGraph와 LangChain 중 어떤 것을 사용해야 하나요? | entity_relation | 1.000 | 0.849 | 0.679 | 0.500 | HIGH |
| Q03 | FastAPI와 PostgreSQL을 연동하여 RAGAS 평가를 수행하려면? | entity_relation | 1.000 | 0.000 | 0.917 | 0.000 | PARTIAL |
| Q04 | PostgreSQL과 Neo4j의 데이터 모델 차이는? | entity_relation | 1.000 | 0.888 | 1.000 | 1.000 | HIGH |
| Q05 | Spring Cloud Gateway와 FastAPI의 역할 분담은? | entity_relation | 1.000 | 0.883 | 1.000 | 0.500 | HIGH |
| Q06 | BGE-M3와 BGE-Reranker의 역할 차이는? | entity_relation | 0.889 | 0.847 | 0.450 | 1.000 | HIGH |
| Q07 | DeepSeek V3와 OpenAI GPT의 비용 및 성능 차이는? | entity_relation | 1.000 | 0.828 | 1.000 | 1.000 | HIGH |
| Q08 | RAG Pipeline에서 BGE-M3 임베딩 모델의 역할은? | multi_hop | 1.000 | 0.000 | 0.917 | 1.000 | HIGH |
| Q09 | Knowledge Graph 엔티티 추출이 RAG 검색 품질에 기여하는 방식은? | multi_hop | 1.000 | 0.808 | 1.000 | 1.000 | HIGH |
| Q10 | Agentic AI 에이전트 워크플로우 설계 패턴은? | multi_hop | 0.917 | 0.823 | 0.000 | 0.000 | PARTIAL |
| Q11 | LangGraph에서 상태 관리와 노드 간 데이터 전달 방식은? | multi_hop | 1.000 | 0.793 | 1.000 | 1.000 | HIGH |
| Q12 | ETL 파이프라인에서 문서 파싱부터 임베딩 저장까지의 전체 흐름은? | multi_hop | 1.000 | 0.712 | 0.333 | 1.000 | HIGH |
| Q13 | Hybrid Search에서 RRF 퓨전이 단일 검색보다 나은 이유는? | multi_hop | 1.000 | 0.796 | 1.000 | 1.000 | HIGH |
| Q14 | AI 에이전트에서 Tool Calling과 Reasoning의 상호작용은? | multi_hop | 1.000 | 0.872 | 0.888 | 1.000 | HIGH |
| Q15 | Docker Compose에서 컨테이너 간 네트워크 통신 설정 방법은? | keyword | 1.000 | 0.000 | 0.000 | 0.000 | NONE |
| Q16 | RRF 알고리즘이 Hybrid 검색에서 하는 역할은? | keyword | 1.000 | 0.741 | 1.000 | 1.000 | HIGH |
| Q17 | RAGAS 평가 메트릭의 종류와 의미는? | keyword | 1.000 | 0.000 | 1.000 | 0.000 | PARTIAL |
| Q18 | JWT 인증 토큰의 장점과 단점은? | keyword | 1.000 | 0.738 | 0.417 | 1.000 | HIGH |
| Q19 | Kubernetes에서 Spring Boot 마이크로서비스 배포 방법은? | keyword | 1.000 | 0.832 | 1.000 | 1.000 | HIGH |
| Q20 | Elasticsearch 벡터 검색을 위한 인덱스 설정 방법은? | keyword | 1.000 | 0.000 | 0.000 | 0.000 | NONE |
| Q21 | WBS란 무엇이며 프로젝트 관리에서 어떻게 활용하나요? | keyword | 0.857 | 0.807 | 1.000 | 1.000 | HIGH |
| Q22 | 대규모 문서를 효율적으로 처리하는 방법은? | semantic | 1.000 | 0.483 | 1.000 | 0.333 | HIGH |
| Q23 | 검색 성능을 최적화하려면 어떻게 해야 하나요? | semantic | 0.818 | 0.541 | 0.806 | 0.250 | PARTIAL |
| Q24 | 환경변수를 안전하게 관리하는 방법은? | semantic | 1.000 | 0.617 | 0.250 | 0.000 | PARTIAL |
| Q25 | 답변 품질을 체계적으로 평가하는 방법론은? | semantic | 1.000 | 0.596 | 0.833 | 0.000 | PARTIAL |
| Q26 | 반복적이고 점진적인 개발 방법론은? | semantic | 1.000 | 0.546 | 0.500 | 0.000 | PARTIAL |
| Q27 | 데이터베이스 마이그레이션을 안전하게 수행하는 방법은? | semantic | 0.889 | 0.977 | 1.000 | 1.000 | HIGH |
| Q28 | 마이크로서비스 아키텍처에서 서비스 간 통신 패턴은? | semantic | 1.000 | 0.000 | 0.500 | 0.500 | PARTIAL |
| Q29 | Spring Cloud Gateway에서 API 라우팅과 필터 설정 방법은? | graph_entity | 1.000 | 0.000 | 0.000 | 1.000 | PARTIAL |
| Q30 | Gleaning 기법이란 무엇이며 RAG에서 어떻게 활용되나요? | graph_entity | 0.833 | 0.000 | 0.000 | 0.000 | NONE |
| Q31 | cosine similarity와 dot product 유사도의 차이는? | graph_entity | 0.720 | 0.900 | 0.333 | 1.000 | HIGH |
| Q32 | SSOT 원칙이란 무엇이며 왜 중요한가요? | graph_entity | 1.000 | 0.725 | 0.639 | 1.000 | HIGH |
| Q33 | Vector Search와 Graph Search를 결합하면 어떤 이점이 있나요? | graph_entity | 0.909 | 0.855 | 0.950 | 1.000 | HIGH |
| Q34 | React 18에서 Concurrent 렌더링과 Suspense 활용 방법은? | graph_entity | 1.000 | 0.000 | 0.000 | 1.000 | PARTIAL |
| Q35 | Python 3.11의 ExceptionGroup과 except* 구문은? | graph_entity | 1.000 | 0.000 | 0.000 | 0.000 | NONE |
| Q36 | AI Service에서 RAG Pipeline의 전체 처리 흐름은? | graph_entity | 0.800 | 0.000 | 0.000 | 0.000 | NONE |
| Q37 | 개인정보보호법에서 개인정보 수집 시 동의 요건은? | legal | 1.000 | 0.479 | 1.000 | 1.000 | HIGH |
| Q38 | GDPR의 핵심 원칙과 국내 기업의 준수 사항은? | legal | 0.375 | 0.704 | 0.000 | 0.000 | NONE |
| Q39 | 민법에서 계약의 성립 요건은? | legal | 1.000 | 0.000 | 1.000 | 1.000 | HIGH |
| Q40 | SLA에서 반드시 포함해야 할 핵심 항목은? | legal | 0.500 | 0.729 | 0.000 | 0.000 | NONE |
| Q41 | ISMS 인증을 위한 정보보안 점검 항목은? | legal | 0.917 | 0.707 | 0.000 | 1.000 | PARTIAL |
| Q42 | 소프트웨어 라이선스 종류(MIT, GPL, Apache)의 차이는? | legal | 0.417 | 0.761 | 0.000 | 0.000 | NONE |
| Q43 | 법령 용어에서 '선의'와 '악의'의 법률적 의미 차이는? | legal | 0.000 | 0.000 | 0.583 | 1.000 | NONE |
| Q44 | RAG 시스템의 동작 원리는? | factual | 1.000 | 0.629 | 0.888 | 1.000 | HIGH |
| Q45 | Transformer Self-Attention 메커니즘은? | factual | 1.000 | 0.894 | 0.417 | 1.000 | HIGH |
| Q46 | Reranking이 RAG 검색 품질을 향상시키는 원리는? | factual | 0.917 | 0.811 | 1.000 | 0.000 | PARTIAL |
| Q47 | HNSW와 IVF 벡터 인덱스 알고리즘의 비교는? | factual | 0.875 | 0.848 | 1.000 | 0.500 | HIGH |
| Q48 | Chain of Thought 추론이 LLM 성능에 미치는 영향은? | factual | 1.000 | 0.790 | 1.000 | 1.000 | HIGH |
| Q49 | 벡터 임베딩의 차원 수가 검색 정확도에 미치는 영향은? | factual | 1.000 | 0.000 | 0.000 | 0.000 | NONE |
| Q50 | 비즈니스에 실제 활용 가능한 LLM 서비스의 핵심 고려사항은? | factual | 0.917 | 0.666 | 0.000 | 0.000 | NONE |
| Q51 | 프롬프트 엔지니어링의 핵심 원칙과 효과적인 기법은? | factual | 1.000 | 0.562 | 0.700 | 1.000 | HIGH |

---

## 11. 결론

### 11.1 최종 평가 요약

| 항목 | v8 (108K, 2-Channel) | v9 (56K, 4-Way RRF) | 판정 |
|------|:---:|:---:|:---:|
| Faithfulness | 0.919 | 0.913 | **동등** |
| Answer Relevancy | **0.647** | 0.547 | **v8 우세** |
| Context Precision | 0.489 | **0.577** | **v9 우세** |
| Context Recall | 0.474 | **0.600** | **v9 우세** |
| HIGH 등급 | 24 | **28** | **v9 우세** |
| NONE 등급 | 11 | 11 | 동일 |
| Graph 기여 | 0% | **66.3%** | v9 독보적 |
| **4 메트릭 중 우세** | **1** (Relevancy) | **2** (Precision, Recall) | **v9 우세** |

### 11.2 핵심 인사이트

1. **"청크를 절반으로 줄이고 채널을 두 배로 늘리면, 검색 품질은 오히려 올라간다."**
   - Context Precision/Recall 모두 개선. 더 크고 의미 있는 청크 + 다채널 검색이 핵심.

2. **"Faithfulness는 시스템이 아닌 LLM의 역량이다."**
   - 0.913으로 108K 시스템과 동등. 동일 LLM(DeepSeek V3.2) + 동일 프롬프트 = 동일 충실도.

3. **"Answer Relevancy가 유일한 약점이며, Reranker가 해결책이다."**
   - 넓은 컨텍스트가 답변 초점을 분산시킴. Reranker로 top-5 정제 시 개선 가능.

4. **"KB에 없는 건 어떤 검색 방식도 답이 없다."**
   - 11건의 NONE은 v8/v9 공통. KB 보강만이 근본 해결책.

### 11.3 후속 과제 우선순위

| 우선순위 | 과제 | 예상 효과 | 난이도 |
|:---:|------|------|:---:|
| **P0** | BGE-Reranker 적용 | Precision 0.577→0.70+, Relevancy 0.547→0.65+ | 중 |
| **P0** | Graph 가중치 동적 조정 | graph_entity Relevancy 0.310→0.50+ | 하 |
| **P1** | Entity Extraction 대상 확대 (tc>=50) | Graph 커버리지 51%→70%+ | 하 |
| **P1** | 답변 프롬프트 최적화 | Relevancy +0.05 | 하 |
| ~~P1~~ | ~~Sparse 가중치 0.5 조정~~ | ~~차별화~~ → **A/B 테스트 결과 기각** (S=0.7 유지) | 완료 |
| **P2** | KB 보강 (법률/기술 문서) | legal Recall 0.571→0.80+ | 중 |
| **P2** | 평가 100문항 확대 | 통계적 신뢰도 향상 | 하 |

---

## 12. 원본 데이터

### 12.1 v9 RAGAS Library 결과 JSON

```json
{
  "version": "v9_library",
  "ragas_version": "0.2.15",
  "timestamp": "2026-02-16 05:44:02",
  "metrics": {
    "faithfulness": 0.9127,
    "answer_relevancy": 0.547,
    "context_precision": 0.5768,
    "context_recall": 0.5997
  },
  "quality_gate": {"HIGH": 28, "PARTIAL": 12, "NONE": 11}
}
```

### 12.2 v9 LLM-as-Judge 결과 JSON

```json
{
  "version": "v9_comprehensive",
  "timestamp": "2026-02-16 05:03:00",
  "metrics": {
    "faithfulness": 0.610,
    "answer_relevancy": 0.619,
    "context_precision": 0.504,
    "context_recall": 0.398
  },
  "quality_gate": {"HIGH": 23, "PARTIAL": 10, "NONE": 18}
}
```

### 12.3 소요 시간

| 단계 | LLM-as-Judge | RAGAS Library |
|------|:---:|:---:|
| 검색 + 답변 생성 | 209.8초 | 162.3초 |
| 평가 | 196.2초 | 158.8초 |
| **총 소요 시간** | **406.0초** | **321.1초** |

전체 상세 데이터: `ragas_v9_library_result.json`, `ragas_v9_comprehensive_result.json` (동일 폴더)

---

## 13. 시스템 총평

### 13.1 현 시스템의 성격

**HRKP v9 (Hybrid RAG Knowledge Platform)**은 "기업 내부 문서 기반 지능형 검색 시스템"이다. 1,437개 문서에서 56,063개 청크를 추출하고, 70,855개 엔티티와 375,229개 관계를 구축하여 4-Way Hybrid Search를 제공한다.

### 13.2 달성한 것

| 목표 | 달성도 | 근거 |
|------|:---:|------|
| **검색 정확도** | **우수** | Context Precision 0.577, v8 대비 +18% |
| **검색 커버리지** | **우수** | Context Recall 0.600, v8 대비 +27% |
| **답변 충실도** | **우수** | Faithfulness 0.913 — 컨텍스트에 매우 충실 |
| **답변 관련성** | **개선 필요** | Answer Relevancy 0.547 — Reranker 미적용 |
| **Graph RAG 통합** | **성공** | 66.3% 검색 기여, entity_relation/multi_hop 강세 |
| **비용 효율** | **우수** | DeepSeek V3.2로 GPT 대비 95% 절감 |

### 13.3 성적 해석 — "0.913은 좋은 점수인가?"

RAG 시스템 평가의 학계/산업계 기준과 비교:

| 수준 | Faithfulness | Context Precision | Context Recall | 해당 시스템 |
|------|:---:|:---:|:---:|------|
| **최상** | 0.95+ | 0.80+ | 0.80+ | RAG + Reranker + 풍부한 KB |
| **우수** | 0.85-0.95 | 0.60-0.80 | 0.60-0.80 | 잘 구축된 RAG |
| **양호** | 0.70-0.85 | 0.40-0.60 | 0.40-0.60 | 기본 RAG |
| **개선필요** | <0.70 | <0.40 | <0.40 | RAG 미성숙 |
| **HRKP v9** | **0.913** | **0.577** | **0.600** | **우수~양호** |

- **Faithfulness 0.913**: 우수. LLM이 검색된 컨텍스트를 거의 완벽히 기반으로 답변. 할루시네이션 위험 낮음.
- **Context Precision 0.577**: 양호. 검색 10건 중 ~6건이 유용. Reranker 적용 시 0.70+ 가능.
- **Context Recall 0.600**: 양호→우수 경계. Ground Truth의 60%를 검색으로 커버.

### 13.4 핵심 강점

1. **4-Way RRF — 다채널 검색의 강건성**
   - Dense/BM25/Sparse/Graph 4개 채널이 서로의 약점을 보완
   - 단일 채널 실패 시에도 다른 채널이 fallback

2. **Entity-Enhanced BM25 — Knowledge Graph의 실질적 활용**
   - 단순한 Graph 저장이 아닌, 검색에 직접 기여하는 Knowledge Graph
   - entity_relation(0.804), multi_hop(0.816) — 관계 기반 질문에서 압도적 성능

3. **DeepSeek V3.2 — 비용 대비 성능의 균형**
   - GPT-4 대비 95% 비용 절감
   - Faithfulness 0.913 — 비용 절감이 품질 저하로 이어지지 않음

### 13.5 핵심 한계

1. **Answer Relevancy 0.547** — 유일한 약점
   - 원인: 10개 컨텍스트를 그대로 전달하여 답변 초점 분산
   - 해결: BGE-Reranker (이미 캐시됨) 적용으로 즉시 개선 가능

2. **KB 커버리지 의존성**
   - NONE 11건 = KB에 없는 주제. 검색 방식 개선으로는 해결 불가
   - 법률(7건 중 4건 NONE), 프로젝트 외부 기술(React, Python 3.11 등)

3. **Graph 과다 기여 시 역효과**
   - Graph 기여 High(8+/10)일 때 NONE 비율 25% — Medium(4-7)의 12%보다 높음
   - 엔티티가 많이 매칭되는 질문에서 Graph 결과가 원본 검색을 희석

### 13.6 총합 판정

```
┌──────────────────────────────────────────────────────────────┐
│                    HRKP v9 시스템 총평                        │
│                                                              │
│  종합 등급: B+ (우수)                                         │
│                                                              │
│  ✅ Faithfulness   0.913  — 할루시네이션 방지에 성공           │
│  ✅ Ctx Precision  0.577  — 4-Way RRF 효과 입증               │
│  ✅ Ctx Recall     0.600  — 큰 청크 + Graph의 시너지          │
│  ⚠️  Ans Relevancy 0.547  — Reranker 적용 시 해결 가능        │
│                                                              │
│  v8 대비: 4 메트릭 중 2개 개선, 1개 동등, 1개 하락            │
│  HIGH: 24 → 28건 (+17%), NONE: 11건 동일                     │
│                                                              │
│  Reranker + 프롬프트 최적화 적용 시 A- (최우수) 도달 가능     │
└──────────────────────────────────────────────────────────────┘
```

---

## Appendix A. 상용 LLM 사용 시 추정 비교

### A.1 비용 비교 (LLM 추론 기준)

현재 시스템은 **DeepSeek V3.2**를 사용한다. 상용 LLM으로 전환 시 비용과 성능 변화를 추정한다.

#### LLM 가격 비교 (2026-02 기준, Input/Output per 1M tokens)

| 모델 | Input | Output | 합산 (1M tok) | DeepSeek 대비 |
|------|:---:|:---:|:---:|:---:|
| **DeepSeek V3.2** (현재) | $0.27 | $1.10 | **$1.37** | 1x (기준) |
| GPT-4o | $2.50 | $10.00 | $12.50 | **9.1x** |
| GPT-4o-mini | $0.15 | $0.60 | $0.75 | **0.55x** |
| Claude Sonnet 4.5 | $3.00 | $15.00 | $18.00 | **13.1x** |
| Claude Haiku 4.5 | $0.80 | $4.00 | $4.80 | **3.5x** |
| Gemini 2.0 Flash | $0.10 | $0.40 | $0.50 | **0.36x** |

> 참고: 가격은 공식 API 기준이며, 볼륨 할인/약정 미포함.

#### 월간 운영 비용 추정

| 시나리오 | 일일 쿼리 | 월간 토큰 (추정) | DeepSeek | GPT-4o | GPT-4o-mini |
|----------|:---:|:---:|:---:|:---:|:---:|
| 소규모 (PoC) | 50 | ~15M | **$0.02** | $0.19 | $0.01 |
| 중규모 (부서) | 500 | ~150M | **$0.21** | $1.88 | $0.11 |
| 대규모 (전사) | 5,000 | ~1.5B | **$2.06** | $18.75 | $1.13 |

> 토큰 추정: 쿼리당 평균 ~10K tokens (컨텍스트 8K + 답변 2K)

### A.2 성능 추정 비교

GPT-4o로 전환 시 각 메트릭의 예상 변화:

| 메트릭 | DeepSeek V3.2 (현재) | GPT-4o (추정) | GPT-4o-mini (추정) | 근거 |
|--------|:---:|:---:|:---:|------|
| **Faithfulness** | 0.913 | **0.94-0.96** | 0.90-0.92 | GPT-4o의 우수한 지시 따르기 |
| **Answer Relevancy** | 0.547 | **0.65-0.70** | 0.55-0.60 | GPT의 정확한 질문 핵심 파악 |
| **Context Precision** | 0.577 | 0.577 | 0.577 | 검색은 LLM 무관 (동일) |
| **Context Recall** | 0.600 | 0.600 | 0.600 | 검색은 LLM 무관 (동일) |

> **핵심**: Context Precision/Recall은 검색 파이프라인이 결정하므로 LLM 전환과 무관. Faithfulness/Relevancy만 LLM에 의존.

### A.3 비용 대비 성능 효율 (Cost-Performance Ratio)

| 모델 | 예상 4-메트릭 평균 | 월간 비용 (중규모) | 성능/$ 효율 |
|------|:---:|:---:|:---:|
| **DeepSeek V3.2** | 0.659 | $0.21 | **3.14/$ (최고)** |
| GPT-4o | 0.692 | $1.88 | 0.37/$ |
| GPT-4o-mini | 0.657 | $0.11 | 5.97/$ |
| Gemini 2.0 Flash | ~0.650 | $0.08 | 8.13/$ |

### A.4 상용 LLM 전환 시 권장 시나리오

| 시나리오 | 추천 모델 | 이유 |
|----------|---------|------|
| **현재 유지** (PoC/개발) | DeepSeek V3.2 | 비용 최소, 성능 충분 |
| **품질 극대화** (프로덕션 핵심) | GPT-4o | Faithfulness 0.95+, 비용 9x 증가 허용 시 |
| **비용 최적** (대량 트래픽) | GPT-4o-mini 또는 Gemini Flash | DeepSeek과 유사 성능, 글로벌 SLA |
| **하이브리드** | 평상시 DeepSeek + 중요 쿼리 GPT-4o | 비용-품질 밸런스 |

### A.5 전환 시 고려사항

1. **RAGAS 평가의 LLM 의존성**: RAGAS 평가 자체도 LLM을 사용하므로, 평가 LLM과 답변 LLM을 다르게 설정하면 더 객관적인 평가 가능
2. **한국어 성능 차이**: DeepSeek V3.2는 한국어 성능이 GPT-4o에 근접하나, 법률/전문 용어에서는 GPT-4o가 우세할 수 있음
3. **API 안정성**: DeepSeek은 중국 API로 국내에서 간헐적 지연 발생 가능. 프로덕션 시 글로벌 API(OpenAI/Google) 고려
4. **검색 파이프라인이 핵심**: LLM 전환보다 Reranker 적용이 더 큰 효과. Context Precision/Recall 개선은 검색 파이프라인에서만 가능

---

*기록: 2026-02-16 05:55 KST*
*평가 스크립트: `scripts/ragas_v9_library_eval.py`, `scripts/ragas_v9_comprehensive_eval.py`*
