# Session Log - 2026-03-10

**Session ID**: 2026-03-10_ragas_v15_v17_evaluation
**시작 시간**: 00:30 KST
**종료 시간**: 04:42 KST
**모델**: Claude Opus 4.6 (claude-opus-4-6)

---

## 세션 요약

RAGAS v15~v17 연속 평가로 Reranker 2-Pass 수학적 중복 증명, 최적 파라미터 확정 (v16 Mean 0.763, A등급), Chat API E2E 검증 완료.

---

## 완료된 작업

### 1. RAGAS v15 — Reranker 2-Pass 재검증 (주요)
- Cross-encoder 코드 추적으로 2-Pass 무의미 수학적 증명
- v15 결과: Mean 0.728 (B+), 2-Pass는 레이턴시만 증가

### 2. RAGAS v16 — 최적 파라미터 확정 (주요)
- REST API Same-Pipeline, DeepSeek Direct 답변 생성
- 결과: **Mean 0.763 (A등급, 역대 최고)**
- 파라미터: c=50, g=10, Reranker 1x, pool=min(top_k*3, 50)

### 3. RAGAS v17 — Chat API E2E (주요)
- LangGraph → HybridRetriever → Reranker(1x) → DeepSeek Generator
- 결과: Mean 0.723 (B+), Precision/Recall 개선 확인
- REST vs Chat 차이: rerank 후보 풀 크기 (15 vs 10)

### 4. 코드 변경 (주요)
- search.py: Reranker 2→1 Pass, 후보 풀 최적화
- config.py: graph_search_top_k 3→10
- rag_workflow.py: sources content 필드 추가

### 5. 보고서 4개 작성 (주요)
- 17: v15 2-Pass 평가, 18: v11~v17 종합 (업데이트)
- 19: v16 확정 검증, 20: v17 Chat E2E

---

## 주요 결정사항

| 결정 | 내용 | 근거 |
|------|------|------|
| Reranker 1-Pass 확정 | 2-Pass 제거, 1-Pass 운영 | 수학적 증명 + v15 실험 |
| graph_search_top_k=10 | 그래프 후보 10개 유지 | Precision +12%p 확인 |
| rerank_pool=min(top_k*3, 50) | 15개 후보 풀 유지 | v16 vs v17 비교로 5%p 차이 확인 |

---

## 변경된 파일 목록

```
knowledge_service/
├── src/app/
│   ├── services/search.py           # Reranker 1-Pass 전환
│   ├── core/config.py               # graph_search_top_k=10
│   └── agents/rag_workflow.py       # content 필드 추가
└── docs/04_testing/11_ragas/results/
    ├── 17_ragas_v15_*.md            # v15 보고서
    ├── 18_ragas_v11_v15_*.md        # 종합 보고서 (v17까지 업데이트)
    ├── 19_ragas_v16_*.md            # v16 보고서
    ├── 20_ragas_v17_*.md            # v17 보고서
    ├── ragas_v15_result.json        # v15 결과 JSON
    ├── ragas_v16_result.json        # v16 결과 JSON
    └── ragas_v17_result.json        # v17 결과 JSON
```

---

## 다음 작업 (Action Items)

### P0 (Critical)
1. HybridRetriever rerank_candidate_count → `top_k*3` 통일

### P1 (High)
2. ONNX INT8 Reranker 적용 (CPU 2-4x)
3. Sprint 10 스토리 진행

### P2 (Medium)
4. GPU 서빙 도입 검토

---

## 세션 통계

| 항목 | 값 |
|------|-----|
| 수정된 파일 | 3개 (코드) |
| 신규 생성 파일 | 7개 (보고서 4 + JSON 3) |
| RAGAS 평가 횟수 | 3회 |
| 컨테이너 리빌드 | 2회 |
| 세션 시간 | ~4시간 12분 |

---

*기록자: Claude Code (Opus 4.6)*
*기록 시간: 2026-03-10 04:42 KST*
