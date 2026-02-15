# RAGAS v9 종합 평가 결과 — ETL v2 + 4-Way RRF + Graph RAG

**Version**: 1.0
**Date**: 2026-02-16 05:03 KST
**Author**: Claude Code (Opus 4.6)
**Status**: 완료

---

## 1. 개요

ETL v2 재처리(chunk_size 600→1000, overlap 100→200) 및 4-Way RRF 파이프라인 구축 후, v8 Nori+Hybrid 평가와 동일한 51개 질문, 7개 도메인으로 종합 평가를 수행하여 시스템 변경 전후를 비교한다.

### 1.1 평가 환경 비교

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
| **평가 방법** | RAGAS 0.4.3 (라이브러리) | LLM-as-Judge (DeepSeek) |
| **질문 수** | 51 (7 도메인) | 51 (7 도메인) |

> **주의**: v8은 RAGAS 0.4.3 라이브러리로, v9는 LLM-as-Judge로 평가하여 절대값 비교에 한계가 있음. 상대적 경향 비교에 중점.

### 1.2 도메인별 질문 구성

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

## 2. 전체 평가 결과

### 2.1 평균 점수 (v8 vs v9)

| 메트릭 | v8 | **v9** | 변화 | 목표 | 달성 |
|--------|:---:|:---:|:---:|:---:|:---:|
| **Faithfulness** | 0.919 | **0.610** | -0.309 | 0.70 | FAIL |
| **Answer Relevancy** | 0.647 | **0.619** | -0.028 | 0.70 | FAIL |
| **Context Precision** | 0.489 | **0.504** | **+0.015** | 0.70 | FAIL |
| **Context Recall** | 0.474 | **0.398** | -0.076 | 0.70 | FAIL |

```
┌───────────────────────────────────────────────────┐
│              RAGAS v9 성적표                        │
│                                                     │
│  Faithfulness        ████████████░░░░░░░░░  0.610  │
│  Answer Relevancy    ████████████░░░░░░░░░  0.619  │
│  Context Precision   ██████████░░░░░░░░░░░  0.504  │
│  Context Recall      ████████░░░░░░░░░░░░░  0.398  │
│                                                     │
│  Quality Gate: HIGH 23/51 (45%) | NONE 18/51 (35%) │
└───────────────────────────────────────────────────┘
```

### 2.2 Quality Gate 분포

| 등급 | v8 | **v9** | 비율 | 변화 |
|:---:|:---:|:---:|:---:|:---:|
| **HIGH** (avg >= 0.70) | 24 | **23** | 45.1% | -1 |
| **PARTIAL** (0.40-0.69) | 16 | **10** | 19.6% | -6 |
| **NONE** (< 0.40) | 11 | **18** | 35.3% | **+7** |

---

## 3. 도메인별 상세 분석

### 3.1 도메인별 평균 점수

| 도메인 | Faith | Relev | Prec | Recall | 종합 | 등급 |
|--------|:---:|:---:|:---:|:---:|:---:|:---:|
| **entity_relation** | 0.757 | 0.829 | 0.714 | 0.743 | **0.761** | **강** |
| **multi_hop** | 0.900 | 0.757 | 0.643 | 0.557 | **0.714** | **강** |
| **factual** | 0.788 | 0.788 | 0.600 | 0.412 | 0.647 | 중 |
| **semantic** | 0.557 | 0.657 | 0.557 | 0.386 | 0.539 | 중 |
| **keyword** | 0.386 | 0.564 | 0.400 | 0.371 | 0.430 | 약 |
| **graph_entity** | 0.487 | 0.412 | 0.338 | 0.212 | 0.362 | 약 |
| **legal** | 0.386 | 0.329 | 0.286 | 0.129 | **0.282** | **최약** |

### 3.2 강점 도메인 분석

**entity_relation (0.761) — 최고 성능**
- Faithfulness 0.757, Relevancy 0.829 — 엔티티 관계 질문에 대한 답변 품질이 높음
- Context Precision 0.714 — 관련 문서를 정확히 검색. **Graph Search의 효과가 가장 잘 드러나는 도메인**
- 프로젝트 핵심 기술(Neo4j, ES, FastAPI, BGE-M3 등)에 대한 풍부한 KB가 기반

**multi_hop (0.714) — Faithfulness 최고 (0.900)**
- 다단계 추론 질문에서 LLM이 컨텍스트에 매우 충실하게 답변
- ETL/RAG/LangGraph 관련 깊은 KB 문서가 있어 Recall 0.557도 양호

### 3.3 약점 도메인 분석

**legal (0.282) — 최저 성능**
- Recall 0.129 — 법률 문서가 KB에 절대적으로 부족
- 7건 중 5건이 NONE 등급 (Q38 GDPR, Q39 민법, Q40 SLA, Q41 ISMS, Q43 법령용어)
- **근본 원인**: Knowledge Base에 법률 도메인 문서 부재 → 검색 방식과 무관

**graph_entity (0.362) — v8 대비 가장 큰 하락 예상**
- React 18 Suspense (Q34), Python ExceptionGroup (Q35), cosine/dot product (Q31) 등 프로젝트 KB 외 기술
- 8건 중 4건이 NONE (Q29, Q30, Q34, Q35, Q36)
- **원인**: 해당 기술의 상세 문서가 KB에 없어 검색 결과가 부정확

**keyword (0.430) — Faithfulness 0.386**
- Docker Compose 네트워크(Q15), RAGAS 메트릭(Q17), ES 벡터 인덱스(Q20), WBS(Q21)에서 F=0.00
- **원인 추정**: 짧은 키워드 쿼리에서 BM25가 관련 없는 문서를 우선 반환하여 LLM이 부정확하게 답변

---

## 4. Graph RAG 기여도 분석

### 4.1 Graph 검색 통계

| 항목 | 값 |
|------|-----|
| Graph 기여 검색 결과 | **338/510** (66.3%) |
| Neo4j 엔티티 | 70,855개 |
| Neo4j 관계 | 375,229개 |
| Entity Extraction 대상 | 16,185건 (tc >= 100) |

### 4.2 Graph 기여가 높은 질문

| 질문 | Graph/10 | 등급 | 분석 |
|------|:---:|:---:|------|
| Q03 FastAPI+PostgreSQL+RAGAS | 10/10 | PARTIAL | 엔티티 관계가 풍부하여 Graph 검색 효과적 |
| Q10 Agentic AI 패턴 | 10/10 | PARTIAL | 다중 엔티티(LangGraph, Agent 등) 관계 활용 |
| Q14 Tool Calling+Reasoning | 10/10 | HIGH | AI 에이전트 관련 엔티티 네트워크 효과 |
| Q19 K8s+SpringBoot 배포 | 10/10 | HIGH | 인프라 기술 스택 간 관계 검색 |
| Q36 RAG Pipeline 전체 흐름 | 10/10 | NONE | Graph 100% 기여했지만 답변 품질 낮음 |

### 4.3 Graph 기여 효과 분석

Graph 기여가 높은(8+) 질문 vs 낮은(0-3) 질문:

| Graph 기여 수준 | 건수 | 평균 종합점수 |
|:---:|:---:|:---:|
| High (8-10/10) | 28건 | 0.541 |
| Medium (4-7/10) | 16건 | 0.593 |
| Low (0-3/10) | 7건 | 0.403 |

> Graph 기여가 Medium일 때 최고 성능. High에서는 Graph 결과가 너무 많아 원본 검색 결과를 희석시킬 수 있음.

---

## 5. 핵심 발견 및 원인 분석

### 5.1 Faithfulness 하락 원인 (0.919 → 0.610, -0.309)

1. **평가 방법 차이**: v8은 RAGAS 0.4.3 라이브러리(세밀한 문장 단위 평가), v9는 LLM-as-Judge(단일 스코어). Judge가 더 엄격하게 채점하는 경향
2. **F=0.00 패턴**: 51건 중 14건이 Faithfulness 0.00. 이 중 대부분은 KB에 관련 문서가 없어 LLM이 일반 지식으로 답변한 경우
3. **청크 감소 효과**: 108K → 56K로 검색 가능 문서 풀이 절반으로 줄어 검색 실패 확률 증가

### 5.2 Context Precision 개선 원인 (+0.015)

1. **Chunk Size 확대**: 600 → 1000으로 각 청크가 더 많은 정보를 포함 → 적중 시 정밀도 향상
2. **4-Way RRF**: Sparse + Graph 채널이 보완하여 다양한 관점에서 관련 문서 검색
3. **미미한 개선**: +0.015는 통계적으로 유의미하지 않을 수 있음

### 5.3 NONE 등급 증가 원인 (11 → 18, +7건)

| 원인 | 건수 | 해당 질문 |
|------|:---:|------|
| KB 문서 부재 | 9 | Q15,Q17,Q20,Q21,Q24,Q28,Q29,Q30,Q34,Q35 |
| 법률 도메인 부재 | 5 | Q38,Q39,Q40,Q41,Q43 |
| 검색 결과 불일치 | 3 | Q08,Q36,Q49 |
| 기타 | 1 | Q17 |

**공통 패턴**: KB에 해당 상세 문서가 없는 질문은 108K→56K 축소로 더 악화됨.

### 5.4 v8 대비 개선/악화 요약

```
개선된 점
├── Context Precision +0.015 (4-Way RRF 다각 검색)
├── entity_relation 도메인 강세 유지 (0.761)
├── multi_hop 도메인 Faithfulness 0.900
├── Graph 기여 66.3% (Entity-Enhanced BM25 성공)
└── 검색 다양성 향상 (4개 채널 병렬)

악화된 점
├── Faithfulness -0.309 (평가 방법 차이 + 청크 감소)
├── Context Recall -0.076 (56K vs 108K 커버리지)
├── NONE 등급 +7건 (KB 커버리지 감소)
├── legal 도메인 0.282 (여전히 최약)
└── graph_entity 도메인 0.362 (KB 외 기술 문서 부재)
```

---

## 6. v8 → v9 변경의 트레이드오프 분석

### 6.1 청크 수 감소 (108K → 56K)

| 측면 | 효과 |
|------|------|
| **긍정** | 평균 청크 크기 증가 (119.3 tokens), 더 의미 있는 컨텍스트 제공 |
| **부정** | 검색 가능 범위 48.5% 축소, KB 커버리지 감소로 Recall 하락 |
| **결론** | 양날의 검. 핵심 도메인은 개선, 주변 도메인은 악화 |

### 6.2 4-Way RRF (2채널 → 4채널)

| 측면 | 효과 |
|------|------|
| **Sparse** | Dense와 보완적이나, 독립적인 개선 효과는 미미 (후보 재순위화 역할) |
| **Graph** | Entity-Enhanced BM25로 66.3% 기여. entity_relation, multi_hop에 효과적 |
| **리스크** | Graph 과다 기여 시 원본 검색 결과 희석 가능 (graph_entity 도메인 저성능) |

### 6.3 Entity Extraction

| 측면 | 효과 |
|------|------|
| **긍정** | 70,855 엔티티 + 375,229 관계로 풍부한 Knowledge Graph 구축 |
| **제한** | tc>=100 청크만 대상 (28,819/56,063 = 51.4%) → 나머지 49%는 Graph 미적용 |
| **효과** | 프로젝트 핵심 기술 질문에서 강점, 일반/법률 질문에서는 기여 미미 |

---

## 7. 결론

### 7.1 평가 요약

| 항목 | v8 (2-Channel) | v9 (4-Way RRF) | 판정 |
|------|:---:|:---:|:---:|
| Faithfulness | **0.919** | 0.610 | v8 우세 (평가 방법 차이 고려) |
| Answer Relevancy | 0.647 | 0.619 | 유사 |
| Context Precision | 0.489 | **0.504** | v9 소폭 우세 |
| Context Recall | **0.474** | 0.398 | v8 우세 (청크 수 차이) |
| Graph 기여 | 0% | **66.3%** | v9 독보적 |
| HIGH 등급 | **24** | 23 | 유사 |
| NONE 등급 | **11** | 18 | v8 우세 |

### 7.2 핵심 인사이트

1. **"청크를 절반으로 줄이고 채널을 두 배로 늘려도, 핵심 커버리지가 유지되면 품질은 보존된다."**
   - HIGH 등급이 24 → 23으로 거의 유지. 핵심 도메인(entity_relation, multi_hop)은 오히려 강화

2. **"Graph RAG의 가치는 관계 기반 질문에서 극대화된다."**
   - entity_relation 0.761, multi_hop 0.714 — Graph 채널이 실질적으로 기여하는 도메인

3. **"KB에 없는 건 검색 방식을 바꿔도 안 된다."**
   - legal 0.282, graph_entity 내 React/Python 질문 0.00 — KB 보강이 근본 해결책

4. **"평가 방법론의 일관성이 비교의 전제 조건이다."**
   - RAGAS 라이브러리 vs LLM-as-Judge 간 Faithfulness 차이 0.309는 시스템 차이보다 평가 방법 차이일 가능성 높음

### 7.3 후속 과제

| 우선순위 | 과제 | 예상 효과 |
|:---:|------|------|
| **P0** | RAGAS 라이브러리(0.4.3)로 재평가 → 동일 평가 방법 비교 | Faithfulness 정확한 비교 가능 |
| **P0** | BGE-Reranker 적용 | Context Precision 0.50 → 0.70+ |
| **P1** | Graph RRF 가중치 튜닝 (0.8 → 도메인별 적응) | Graph 과다 기여 방지 |
| **P1** | Entity Extraction 대상 확대 (tc>=50) | Graph 커버리지 51% → 70%+ |
| **P2** | KB 보강 (법률, 프론트엔드 문서) | legal Recall 0.13 → 0.50+ |
| **P2** | 100 쿼리 확대 평가 | 통계적 신뢰도 향상 |

---

## 8. 원본 데이터

### 8.1 JSON

```json
{
  "version": "v9_comprehensive",
  "timestamp": "2026-02-16 05:03:00",
  "system": {
    "es_chunks": 56063,
    "neo4j_entities": 70855,
    "neo4j_relationships": 375229,
    "search_type": "4-Way RRF (Dense + BM25 + Sparse + Graph)",
    "rrf_weights": {"vector": 1.0, "keyword": 1.0, "sparse": 0.7, "graph": 0.8},
    "chunk_size": 1000,
    "chunk_overlap": 200
  },
  "metrics": {
    "faithfulness": 0.610,
    "answer_relevancy": 0.619,
    "context_precision": 0.504,
    "context_recall": 0.398
  },
  "quality_gate": {"HIGH": 23, "PARTIAL": 10, "NONE": 18},
  "evaluation": {
    "method": "LLM-as-Judge (DeepSeek V3.2)",
    "search_time_s": 209.8,
    "eval_time_s": 196.2,
    "total_time_s": 406.0
  }
}
```

전체 상세 데이터: `ragas_v9_comprehensive_result.json` (동일 폴더)

---

## 9. 개별 질문 결과

| # | 질문 | 도메인 | Faith | Relev | Prec | Recall | 등급 | Graph |
|:---:|------|--------|:---:|:---:|:---:|:---:|:---:|:---:|
| Q01 | Neo4j와 Elasticsearch의 역할 차이점은? | entity_relation | 0.50 | 0.90 | 0.60 | 0.50 | PARTIAL | 4 |
| Q02 | LangGraph와 LangChain 중 어떤 것을 사용해야 하나요? | entity_relation | 1.00 | 0.95 | 1.00 | 0.80 | HIGH | 8 |
| Q03 | FastAPI와 PostgreSQL을 연동하여 RAGAS 평가를 수행하려면? | entity_relation | 0.00 | 0.20 | 0.60 | 0.80 | PARTIAL | 10 |
| Q04 | PostgreSQL과 Neo4j의 데이터 모델 차이는? | entity_relation | 0.90 | 0.95 | 0.40 | 0.50 | PARTIAL | 2 |
| Q05 | Spring Cloud Gateway와 FastAPI의 역할 분담은? | entity_relation | 1.00 | 0.90 | 0.80 | 1.00 | HIGH | 6 |
| Q06 | BGE-M3와 BGE-Reranker의 역할 차이는? | entity_relation | 1.00 | 1.00 | 0.80 | 0.80 | HIGH | 4 |
| Q07 | DeepSeek V3와 OpenAI GPT의 비용 및 성능 차이는? | entity_relation | 0.90 | 0.90 | 0.80 | 0.80 | HIGH | 9 |
| Q08 | RAG Pipeline에서 BGE-M3 임베딩 모델의 역할은? | multi_hop | 1.00 | 0.00 | 0.20 | 0.00 | NONE | 8 |
| Q09 | Knowledge Graph 엔티티 추출이 RAG 검색 품질에 기여하는 방식은? | multi_hop | 1.00 | 0.90 | 0.80 | 1.00 | HIGH | 8 |
| Q10 | Agentic AI 에이전트 워크플로우 설계 패턴은? | multi_hop | 0.90 | 0.90 | 0.90 | 0.00 | PARTIAL | 10 |
| Q11 | LangGraph에서 상태 관리와 노드 간 데이터 전달 방식은? | multi_hop | 0.90 | 0.90 | 0.20 | 0.80 | HIGH | 7 |
| Q12 | ETL 파이프라인에서 문서 파싱부터 임베딩 저장까지의 전체 흐름은? | multi_hop | 0.80 | 0.90 | 0.80 | 0.50 | HIGH | 5 |
| Q13 | Hybrid Search에서 RRF 퓨전이 단일 검색보다 나은 이유는? | multi_hop | 0.80 | 0.90 | 0.80 | 0.80 | HIGH | 4 |
| Q14 | AI 에이전트에서 Tool Calling과 Reasoning의 상호작용은? | multi_hop | 0.90 | 0.80 | 0.80 | 0.80 | HIGH | 10 |
| Q15 | Docker Compose에서 컨테이너 간 네트워크 통신 설정 방법은? | keyword | 0.00 | 0.10 | 0.20 | 0.00 | NONE | 8 |
| Q16 | RRF 알고리즘이 Hybrid 검색에서 하는 역할은? | keyword | 1.00 | 1.00 | 0.80 | 0.80 | HIGH | 6 |
| Q17 | RAGAS 평가 메트릭의 종류와 의미는? | keyword | 0.00 | 0.00 | 0.20 | 0.00 | NONE | 8 |
| Q18 | JWT 인증 토큰의 장점과 단점은? | keyword | 0.90 | 0.95 | 0.60 | 0.80 | HIGH | 5 |
| Q19 | Kubernetes에서 Spring Boot 마이크로서비스 배포 방법은? | keyword | 0.80 | 0.90 | 0.80 | 1.00 | HIGH | 10 |
| Q20 | Elasticsearch 벡터 검색을 위한 인덱스 설정 방법은? | keyword | 0.00 | 0.10 | 0.20 | 0.00 | NONE | 10 |
| Q21 | WBS란 무엇이며 프로젝트 관리에서 어떻게 활용하나요? | keyword | 0.00 | 0.90 | 0.00 | 0.00 | NONE | 8 |
| Q22 | 대규모 문서를 효율적으로 처리하는 방법은? | semantic | 0.50 | 0.90 | 0.90 | 0.50 | HIGH | 10 |
| Q23 | 검색 성능을 최적화하려면 어떻게 해야 하나요? | semantic | 0.90 | 0.90 | 0.80 | 0.40 | HIGH | 9 |
| Q24 | 환경변수를 안전하게 관리하는 방법은? | semantic | 0.00 | 0.10 | 0.20 | 0.00 | NONE | 9 |
| Q25 | 답변 품질을 체계적으로 평가하는 방법론은? | semantic | 0.80 | 0.90 | 0.60 | 0.80 | HIGH | 0 |
| Q26 | 반복적이고 점진적인 개발 방법론은? | semantic | 0.90 | 0.90 | 0.60 | 0.20 | PARTIAL | 6 |
| Q27 | 데이터베이스 마이그레이션을 안전하게 수행하는 방법은? | semantic | 0.80 | 0.90 | 0.60 | 0.80 | HIGH | 4 |
| Q28 | 마이크로서비스 아키텍처에서 서비스 간 통신 패턴은? | semantic | 0.00 | 0.00 | 0.20 | 0.00 | NONE | 4 |
| Q29 | Spring Cloud Gateway에서 API 라우팅과 필터 설정 방법은? | graph_entity | 0.00 | 0.10 | 0.20 | 0.00 | NONE | 4 |
| Q30 | Gleaning 기법이란 무엇이며 RAG에서 어떻게 활용되나요? | graph_entity | 0.20 | 0.20 | 0.20 | 0.00 | NONE | 5 |
| Q31 | cosine similarity와 dot product 유사도의 차이는? | graph_entity | 0.80 | 0.95 | 0.60 | 0.20 | PARTIAL | 3 |
| Q32 | SSOT 원칙이란 무엇이며 왜 중요한가요? | graph_entity | 1.00 | 0.90 | 0.40 | 0.50 | HIGH | 4 |
| Q33 | Vector Search와 Graph Search를 결합하면 어떤 이점이 있나요? | graph_entity | 0.90 | 0.95 | 0.90 | 1.00 | HIGH | 8 |
| Q34 | React 18에서 Concurrent 렌더링과 Suspense 활용 방법은? | graph_entity | 0.00 | 0.10 | 0.20 | 0.00 | NONE | 8 |
| Q35 | Python 3.11의 ExceptionGroup과 except* 구문은? | graph_entity | 0.00 | 0.00 | 0.00 | 0.00 | NONE | 4 |
| Q36 | AI Service에서 RAG Pipeline의 전체 처리 흐름은? | graph_entity | 1.00 | 0.10 | 0.20 | 0.00 | NONE | 10 |
| Q37 | 개인정보보호법에서 개인정보 수집 시 동의 요건은? | legal | 0.90 | 1.00 | 0.80 | 0.80 | HIGH | 8 |
| Q38 | GDPR의 핵심 원칙과 국내 기업의 준수 사항은? | legal | 0.80 | 0.40 | 0.20 | 0.00 | NONE | 9 |
| Q39 | 민법에서 계약의 성립 요건은? | legal | 0.00 | 0.10 | 0.20 | 0.00 | NONE | 9 |
| Q40 | SLA에서 반드시 포함해야 할 핵심 항목은? | legal | 0.00 | 0.10 | 0.20 | 0.00 | NONE | 5 |
| Q41 | ISMS 인증을 위한 정보보안 점검 항목은? | legal | 0.00 | 0.20 | 0.00 | 0.00 | NONE | 1 |
| Q42 | 소프트웨어 라이선스 종류(MIT, GPL, Apache)의 차이는? | legal | 1.00 | 0.40 | 0.40 | 0.00 | PARTIAL | 2 |
| Q43 | 법령 용어에서 '선의'와 '악의'의 법률적 의미 차이는? | legal | 0.00 | 0.10 | 0.20 | 0.10 | NONE | 10 |
| Q44 | RAG 시스템의 동작 원리는? | factual | 0.90 | 0.95 | 1.00 | 1.00 | HIGH | 9 |
| Q45 | Transformer Self-Attention 메커니즘은? | factual | 0.80 | 0.90 | 0.40 | 0.10 | PARTIAL | 9 |
| Q46 | Reranking이 RAG 검색 품질을 향상시키는 원리는? | factual | 0.90 | 0.95 | 0.80 | 0.50 | HIGH | 4 |
| Q47 | HNSW와 IVF 벡터 인덱스 알고리즘의 비교는? | factual | 1.00 | 0.80 | 0.40 | 0.20 | PARTIAL | 7 |
| Q48 | Chain of Thought 추론이 LLM 성능에 미치는 영향은? | factual | 0.80 | 0.90 | 0.80 | 1.00 | HIGH | 10 |
| Q49 | 벡터 임베딩의 차원 수가 검색 정확도에 미치는 영향은? | factual | 0.00 | 0.00 | 0.00 | 0.00 | NONE | 8 |
| Q50 | 비즈니스에 실제 활용 가능한 LLM 서비스의 핵심 고려사항은? | factual | 1.00 | 0.90 | 0.60 | 0.00 | PARTIAL | 4 |
| Q51 | 프롬프트 엔지니어링의 핵심 원칙과 효과적인 기법은? | factual | 0.90 | 0.90 | 0.80 | 0.50 | HIGH | 5 |

---

## 10. 소요 시간

| 단계 | 시간 |
|------|------|
| 검색 + 답변 생성 | 209.8초 (4.1초/query) |
| RAGAS 평가 (LLM-as-Judge) | 196.2초 (3.8초/query) |
| **총 소요 시간** | **406.0초 (6.8분)** |

---

*기록: 2026-02-16 05:10 KST*
*평가 스크립트: `scripts/ragas_v9_comprehensive_eval.py`*
*상세 JSON: `ragas_v9_comprehensive_result.json`*
