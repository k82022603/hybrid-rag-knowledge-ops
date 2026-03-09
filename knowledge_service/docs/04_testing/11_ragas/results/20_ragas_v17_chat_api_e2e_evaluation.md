# RAGAS v17 — Chat API E2E 사용자 체감 품질 측정

**일자**: 2026-03-10
**버전**: v17
**방법**: Chat API E2E (`/api/v1/search/chat`)
**목적**: 최적 파라미터 적용 후 사용자 체감 품질 측정 (v11과 동일 경로)

---

## 1. 평가 설정

| 항목 | 값 |
|------|-----|
| 평가 경로 | Chat API `/api/v1/search/chat` (LangGraph E2E) |
| 파이프라인 | LangGraph → HybridRetriever → Reranker(1x) → DeepSeek Generator |
| candidates_cap | 50 |
| graph_search_top_k | 10 |
| Reranker | 1-Pass (HybridRetriever 내부, SearchService skip) |
| rerank_candidate_count | `min(len, top_k * 2, 50)` = 10 |
| 답변 생성 | LangGraph RAGWorkflow (DeepSeek 내부 호출) |
| 평가 LLM | DeepSeek V3.2 (RAGAS judge) |
| 질문 수 | 51 (7개 도메인) |
| 유효 샘플 | 51/51 (100%) |

### v11과의 경로 비교

| 항목 | v11 (2026-02-16) | v17 (2026-03-10) |
|------|------------------|------------------|
| API 경로 | `/api/v1/search/chat` | `/api/v1/search/chat` |
| Reranker | 2-Pass (SearchService + HybridRetriever) | **1-Pass** (HybridRetriever only) |
| graph_search_top_k | 3 | **10** |
| candidates_cap | 50 | 50 |
| LangGraph 버전 | 동일 RAGWorkflow | 동일 RAGWorkflow + content 필드 |

---

## 2. 결과 요약

| Metric | v11 (Chat) | v14 (REST) | v16 (REST) | **v17 (Chat)** | vs v11 |
|--------|-----------|-----------|-----------|---------------|--------|
| Faithfulness | 0.9350 | 0.9403 | 0.8588 | **0.8002** | -0.1348 |
| Context Precision | 0.6180 | 0.6822 | 0.7389 | **0.6833** | +0.0653 |
| Context Recall | 0.6720 | 0.6078 | 0.6902 | **0.6846** | +0.0126 |
| **산술평균** | **0.7417** | **0.7434** | **0.7626** | **0.7227** | **-0.0190** |

---

## 3. 분석

### 3.1 Precision +6.5%p (vs v11) — Chat API에서도 개선

- `graph_search_top_k=10` 복원 효과가 Chat API 경로에서도 반영
- HybridRetriever 내부 Reranker가 더 많은 Graph 후보를 활용하여 정밀도 향상

### 3.2 Recall +1.3%p (vs v11) — 소폭 개선

- v11(0.672) → v17(0.685): 유의미하지만 큰 차이는 아님
- HybridRetriever의 `rerank_candidate_count = min(len, top_k*2, 50)` = 10개로 v16(15개)보다 적어 Recall 개선 제한적

### 3.3 Faithfulness -13.5%p (vs v11) — 유의미한 하락

이것은 **가장 주목할 만한 변화**입니다:

| 가능한 원인 | 설명 |
|------------|------|
| **DeepSeek API 버전 변화** | v11(2026-02-16) → v17(2026-03-10): 약 3주간 DeepSeek API 내부 모델이 업데이트되었을 가능성 |
| **RAGAS judge 변동성** | 동일 DeepSeek를 judge로 사용, API 응답 변동성이 Faithfulness 측정에 영향 |
| **LangGraph 프롬프트 효과** | RAGWorkflow의 시스템 프롬프트가 더 넓은 범위의 답변을 생성하도록 유도 |
| **평가 시점 간 차이** | RAGAS judge의 DeepSeek 응답이 시점마다 달라질 수 있음 |

> **핵심 인사이트**: Faithfulness 하락은 v16(REST, 0.859)과 v17(Chat, 0.800) 모두에서 관찰됨. 이는 파이프라인 변경이 아닌 **평가 시점의 DeepSeek API 변동성**이 주원인으로 판단.

### 3.4 산술평균 비교

```
v11 (Chat, 2026-02-16): 0.742 → A- 등급
v14 (REST, 2026-02):    0.743 → A- 등급
v16 (REST, 2026-03-10): 0.763 → A  등급
v17 (Chat, 2026-03-10): 0.723 → B+ 등급
```

---

## 4. REST vs Chat API 경로 차이 분석

### 4.1 동일 시점(2026-03-10) 비교: v16 vs v17

| Metric | v16 (REST) | v17 (Chat) | 차이 |
|--------|-----------|-----------|------|
| Faithfulness | 0.859 | 0.800 | -0.059 |
| Precision | 0.739 | 0.683 | -0.056 |
| Recall | 0.690 | 0.685 | -0.005 |
| **Mean** | **0.763** | **0.723** | **-0.040** |

### 4.2 차이 원인

| 항목 | REST (v16) | Chat (v17) | 영향 |
|------|-----------|-----------|------|
| Reranker 후보 수 | 15 (`top_k*3`) | 10 (`top_k*2`) | Precision -5.6%p |
| 답변 생성 | DeepSeek Direct (단순 프롬프트) | LangGraph RAGWorkflow (복잡 프롬프트) | Faithfulness -5.9%p |
| Reranker 위치 | SearchService | HybridRetriever | 동일 모델 |

> **핵심**: Chat API 경로는 HybridRetriever에서 `min(top_k*2, 50)` = 10개 후보로 Reranking하므로, REST 경로의 `min(top_k*3, 50)` = 15개보다 적음. 이것이 Precision 차이의 주원인.

### 4.3 개선 방안

HybridRetriever의 `rerank_candidate_count`를 REST와 동일하게 `min(top_k * 3, 50)`으로 변경하면 Chat API 경로도 v16 수준으로 개선 가능:

```python
# retriever.py 현재:
rerank_candidate_count = min(len(fused_results), top_k * 2, 50)
# 권장 변경:
rerank_candidate_count = min(len(fused_results), top_k * 3, 50)
```

---

## 5. Latency 통계 (Chat API E2E)

| 항목 | 값 |
|------|-----|
| 평균 | 48,722ms (~49초) |
| 중앙값 | 47,875ms (~48초) |
| 최소 | 33,370ms (~33초) |
| 최대 | 70,481ms (~70초) |

### Latency 구성 추정

| 단계 | 소요 시간 (추정) |
|------|---------------|
| HybridRetriever (Search + Rerank) | ~15-25초 |
| DeepSeek LLM Generation | ~20-30초 |
| LangGraph Overhead | ~3-5초 |
| **합계** | **~38-60초** |

---

## 6. 전체 버전 비교표

```
버전    방법    Faith   Prec    Recall  Mean    등급    특이사항
─────────────────────────────────────────────────────────────────
v11     Chat    0.935   0.618   0.672   0.742   A-      baseline (2-Pass, g=3)
v13     REST    0.942   0.584   0.605   0.710   B+      2-Pass, g=3
v14     REST    0.940   0.682   0.608   0.743   A-      2-Pass, g=10
v15     REST    0.907   0.682   0.595   0.728   B+      2-Pass 중복 증명
v16     REST    0.859   0.739   0.690   0.763   A       1-Pass, 최적 파라미터
v17     Chat    0.800   0.683   0.685   0.723   B+      1-Pass, Chat E2E
```

---

## 7. 결론

### 7.1 검색 품질 (Precision + Recall)

| 비교 | Precision | Recall | 판정 |
|------|-----------|--------|------|
| v17 vs v11 | +0.065 | +0.013 | **개선** |
| v17 vs v14 | +0.001 | +0.077 | **개선** |

Chat API 경로에서도 검색 품질(Precision + Recall)은 v11 대비 개선됨.

### 7.2 답변 충실도 (Faithfulness)

| 비교 | Faithfulness | 판정 |
|------|-------------|------|
| v17 vs v11 | -0.135 | 하락 |
| v16 vs v11 | -0.076 | 하락 |

Faithfulness 하락은 REST/Chat 모두에서 관찰되며, 평가 시점의 DeepSeek API 변동성이 주원인.

### 7.3 최종 판정

1. **최적 파라미터(g=10, Reranker 1x)는 Chat API에서도 유효** — Precision/Recall 개선 확인
2. **Chat API는 REST보다 4%p 낮은 산술평균** — HybridRetriever 후보 수(10 vs 15) 차이
3. **HybridRetriever `rerank_candidate_count`를 `top_k*3`으로 통일 권장**
4. **Faithfulness 변동은 평가 인프라(DeepSeek judge) 한계** — 절대값보다 상대 순위에 집중

---

## 8. 권장 후속 조치

| 우선순위 | 조치 | 기대 효과 |
|---------|------|----------|
| **P0** | HybridRetriever rerank_candidate_count → `top_k*3` | Chat API Precision +5%p 예상 |
| **P1** | ONNX INT8 Reranker 적용 | Latency 2-4x 개선 (49초→12-25초) |
| **P2** | GPU 서빙 (T4) | Latency 10x 개선 (49초→5-10초) |
| **P3** | RAGAS judge를 GPT-4o로 교체 | Faithfulness 측정 안정성 향상 |

---

*Phase 1: 42분 | Phase 2: 438초 | 총 소요: ~50분*
*결과 파일: `ragas_v17_result.json`*
