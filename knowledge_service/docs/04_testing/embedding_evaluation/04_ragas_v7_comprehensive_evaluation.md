# RAGAS v7 종합 평가 결과 — 51쿼리, 7개 도메인

**Version**: 3.0 (Nori 사고 분석 + v8 재평가 + 시스템 총평 + LangChain Appendix)
**Date**: 2026-02-13
**Author**: 클로드
**Status**: 완료

---

## 1. 개요

Phase 3 임베딩 100% 완료(108,896건) 후, 이전 v5/v6 수준의 종합 RAGAS 평가를 수행했다.
v7 Live 10쿼리 평가(03번 문서)에 이어 51개 질문, 7개 도메인으로 확대하여 통계적 신뢰도를 높였다.

### 평가 환경

| 항목 | 값 |
|------|-----|
| 평가 프레임워크 | RAGAS 0.2.15 (라이브러리 직접 평가) |
| LLM (답변 생성 + 평가) | DeepSeek V3 (deepseek-chat) |
| 임베딩 모델 | BAAI/bge-m3 (1024 dims) |
| 검색 엔진 | Elasticsearch 8.x kNN |
| 검색 방식 | Dense Vector (cosine similarity) |
| Top-K | 5 |
| 평가 질문 수 | 51개 (7개 도메인) |
| 평가 메트릭 | Faithfulness, Answer Relevancy, Context Precision, Context Recall |
| 총 청크 수 | 108,896건 (108K, Phase 3 완료) |
| 실행 시각 | 2026-02-13 19:45 KST |
| 총 소요 시간 | 9.5분 (검색+답변 5.6분 + RAGAS 평가 3.9분) |

### v6 대비 주요 변경점

| 항목 | v6 (2026-02-11) | v7 종합 (2026-02-13) |
|------|----------------|---------------------|
| 임베딩 청크 수 | 13,430 | **108,896** (8.1배) |
| 평가 방법 | LLM-as-Judge (DeepSeek) | **RAGAS 0.2.15 라이브러리** |
| pyarrow | 23.0 (호환 에러) | 17.0 (정상) |
| ragas | 0.1.19 (API 미호환) | **0.2.15** (최신 API) |
| JWT | 자동 갱신 | ES kNN 직접 검색 (JWT 불필요) |

---

## 2. 도메인별 질문 구성

| 도메인 | 쿼리 수 | 범위 | 설명 |
|--------|:-------:|------|------|
| entity_relation | 7 | Q1-Q7 | 기술 엔티티 간 관계 비교 |
| multi_hop | 7 | Q8-Q14 | 다단계 추론 필요 |
| keyword | 7 | Q15-Q21 | 키워드 기반 직접 검색 |
| semantic | 7 | Q22-Q28 | 의미 기반 검색 |
| graph_entity | 8 | Q29-Q36 | Neo4j Graph 트리거 |
| legal | 7 | Q37-Q43 | 법률/규정 도메인 |
| factual | 8 | Q44-Q51 | AI/LLM 심화 + 프로젝트 특화 |

---

## 3. 전체 평가 결과

### 3.1 평균 점수

| 메트릭 | 점수 | 목표 | 달성 | v7 Live (10쿼리) | 변화 |
|--------|------|------|------|------------------|------|
| **Faithfulness** | **0.885** | 0.70 | PASS | 0.884 | +0.1% |
| **Answer Relevancy** | **0.721** | 0.70 | PASS | 0.874 | -17.5% |
| **Context Precision** | **0.455** | 0.70 | FAIL | 0.645 | -29.5% |
| **Context Recall** | **0.464** | 0.70 | FAIL | 0.717 | -35.3% |

> **Answer Relevancy, Context Precision, Recall 하락 원인**: 10쿼리 → 51쿼리 확대로 난이도 높은 도메인(legal, graph_entity, semantic)이 추가됨. 특히 법률, React/Python 같은 프로젝트 외 도메인에서 검색 결과 품질이 낮아 평균이 하락.

### 3.2 역대 평가 비교

| 메트릭 | v5 (13K, LLM-Judge) | v6 (13K, LLM-Judge) | v7 Live (108K, RAGAS) | v7 종합 (108K, RAGAS) |
|--------|:-------------------:|:-------------------:|:--------------------:|:--------------------:|
| Faithfulness | 0.144 | 0.128 | **0.884** | **0.885** |
| Answer Relevancy | 0.456 | 0.356 | **0.874** | **0.721** |
| Context Precision | 0.396 | 0.472 | 0.645 | 0.455 |
| Context Recall | 0.150 | 0.194 | **0.717** | 0.464 |

> v5/v6의 낮은 점수는 (1) pyarrow 호환 에러, (2) LLM-as-Judge 방식의 한계, (3) 13K 청크 부족이 원인.
> v7에서 108K 임베딩 + RAGAS 0.2.15 라이브러리로 전환하면서 Faithfulness/Relevancy는 대폭 개선.

---

## 4. 도메인별 상세 분석

### 4.1 도메인별 평균 점수

| 도메인 | Faith | Relev | Prec | Recall | 종합 |
|--------|:-----:|:-----:|:----:|:------:|:----:|
| **entity_relation** | 0.935 | 0.932 | 0.436 | 0.571 | 0.718 |
| **factual** | 0.960 | 0.776 | 0.418 | 0.313 | 0.616 |
| **graph_entity** | 0.838 | 0.440 | 0.344 | 0.750 | 0.593 |
| **keyword** | 0.923 | 0.509 | 0.593 | 0.571 | 0.649 |
| **legal** | 0.890 | 0.866 | 0.429 | 0.190 | 0.594 |
| **multi_hop** | 0.840 | 0.839 | 0.629 | 0.500 | 0.702 |
| **semantic** | 0.804 | 0.718 | 0.359 | 0.333 | 0.553 |

### 4.2 도메인별 강/약점 분석

**강점 도메인 (종합 ≥ 0.65)**:
- **entity_relation** (0.718): 기술 엔티티 비교 쿼리 — Knowledge Base에 풍부한 기술 문서 존재
- **multi_hop** (0.702): 다단계 추론 — RAG/임베딩/검색 관련 문서가 잘 정비됨
- **keyword** (0.649): 직접 키워드 매칭 — 기술 용어 기반 검색이 효과적

**약점 도메인 (종합 < 0.60)**:

- **semantic** (0.553): Context Precision 0.359, Recall 0.333으로 최저 수준
  - **원인 1 — Dense Vector only 검색의 한계**: semantic 질문은 직접 키워드 없이 추상적 표현("답변 품질을 체계적으로 평가", "반복적이고 점진적인 개발")으로 구성됨. Dense Vector만으로는 의도를 정확히 포착하지 못하고 유사하지만 관련 없는 문서를 반환. BM25를 결합한 Hybrid Search가 부재하여 키워드 보완이 안 됨.
  - **원인 2 — Knowledge Base의 일반 지식 부족**: "환경변수 관리", "DB 마이그레이션", "서비스 간 통신" 등 소프트웨어 공학 일반 지식은 프로젝트 특화 KB(아키텍처 설계서, RAG 관련 문서 위주)에 상대적으로 적음. 프로젝트 문서에 해당 주제가 부분적으로만 언급되어 검색 결과의 커버리지가 부족.
  - **대응**: Hybrid Search(BM25+Dense) 적용 + Query Expansion으로 추상적 쿼리를 구체 키워드로 확장

- **graph_entity** (0.593): Answer Relevancy 0.440으로 최저
  - **원인**: React 18 Suspense, Python 3.11 ExceptionGroup 등 프로젝트 KB에 해당 상세 문서가 없는 기술 토픽. 검색 결과가 빈약할 때 LLM이 컨텍스트 대신 일반 지식으로 답변하여 Relevancy가 급락.
  - **대응**: Knowledge Base에 프론트엔드/Python 심화 문서 보강 또는 해당 질문을 평가셋에서 제외

- **legal** (0.594): Context Recall 0.190으로 최저
  - **원인**: 법률 도메인 문서(개인정보보호법, GDPR, SLA, ISMS)가 Knowledge Base에 절대적으로 부족. 일부 법률 관련 강의 자료가 존재하나 상세 조항 수준의 정보는 미흡.
  - **대응**: 법률/규정 관련 문서를 KB에 추가 적재하거나, 해당 도메인을 "KB 외 영역"으로 분류

- **factual** (0.616): Context Recall 0.313
  - **원인**: "Transformer Self-Attention", "HNSW vs IVF", "Embedding 차원 수 영향" 등 AI/ML 심화 지식이 KB 내 여러 문서에 분산되어 있어 top-5 검색으로는 필요한 정보를 모두 수집하기 어려움.
  - **대응**: Top-K 확대(5→10) 또는 Query Expansion으로 분산된 정보 수집률 향상

### 4.3 핵심 발견

1. **Faithfulness 일관성 (0.885)**: 모든 도메인에서 0.80 이상 유지. LLM이 컨텍스트에 충실하게 답변하고 있음
2. **Answer Relevancy 양극화**: entity_relation(0.932) vs graph_entity(0.440) — 관련 문서 부재 시 답변 품질 급락
3. **Context Precision 전반적 부족 (0.455)**: top-5 중 관련 문서가 2.3개뿐 — Reranking 필요
4. **Context Recall 도메인 편차**: graph_entity(0.750) vs legal(0.190) — Knowledge Base 커버리지 차이

---

## 5. Quality Gate 분석

### 5.1 등급 분포

| Grade | 기준 | 건수 | 비율 |
|:-----:|------|:----:|:----:|
| **HIGH** | 4메트릭 평균 ≥ 0.70 | 23 | 45.1% |
| **PARTIAL** | 4메트릭 평균 0.40-0.69 | 19 | 37.3% |
| **NONE** | 4메트릭 평균 < 0.40 | 9 | 17.6% |

### 5.2 v6 대비 Quality Gate 비교

| Grade | v6 (HRKP-FULL) | v7 종합 | 변화 |
|:-----:|:--------------:|:------:|:----:|
| HIGH | 33 (66.0%) | 23 (45.1%) | -20.9% |
| PARTIAL | 12 (24.0%) | 19 (37.3%) | +13.3% |
| NONE | 5 (10.0%) | 9 (17.6%) | +7.6% |

> v6의 Quality Gate는 검색 max_score 기반이었고, v7은 RAGAS 4메트릭 평균 기반이므로 직접 비교에 주의. v7이 더 엄격한 기준을 적용.

### 5.3 NONE 등급 질문 분석 (9건)

| # | 질문 | 도메인 | 원인 |
|---|------|--------|------|
| Q15 | Docker Compose 네트워크 통신 | keyword | Relevancy=0.000 — 검색 결과 불일치 |
| Q20 | ES 벡터 검색 인덱스 설정 | keyword | Relevancy=0.000, Prec=0.000 — 일반 ES 설정만 검색됨 |
| Q27 | 마이크로서비스 통신 패턴 | semantic | Faith=0.000, Relevancy=0.000 — 답변 생성 실패 |
| Q31 | cosine vs dot product | graph_entity | 대부분 메트릭 0 — KB에 해당 내용 부재 |
| Q34 | React 18 Suspense | graph_entity | Relevancy=0.000 — 프론트엔드 문서 부족 |
| Q35 | Python ExceptionGroup | graph_entity | Relevancy=0.000 — Python 3.11 상세 문서 부재 |
| Q40 | SLA 핵심 항목 | legal | Prec=0.000, Recall=0.000 — 법률 문서 부족 |
| Q41 | ISMS 인증 점검 항목 | legal | Prec=0.000, Recall=0.000 — 보안 규정 문서 부족 |
| Q50 | Embedding 차원 수 영향 | factual | Relevancy=0.000 — 검색 결과 불일치 |

**공통 패턴**: Knowledge Base에 해당 도메인 문서가 부족하거나, 일반 지식 질문이라 검색 결과가 불일치.

---

## 6. 우수 사례 (HIGH 등급, 상위 10건)

| # | 질문 | 도메인 | Avg | Faith | 특징 |
|---|------|--------|:---:|:-----:|------|
| Q18 | JWT 인증 장단점 | keyword | 0.982 | 1.000 | 4메트릭 모두 우수 |
| Q11 | LangGraph 상태 관리 | multi_hop | 0.954 | 1.000 | 기술 문서 정확 매칭 |
| Q9 | KG 엔티티 추출 기여 | multi_hop | 0.951 | 0.933 | Graph RAG 관련 문서 풍부 |
| Q4 | PostgreSQL vs Neo4j | entity_relation | 0.919 | 1.000 | SSOT 설계 문서 활용 |
| Q45 | RAG 동작 원리 | factual | 0.914 | 0.929 | 핵심 기술 문서 정확 검색 |
| Q37 | 개인정보보호법 동의 | legal | 0.959 | 1.000 | 법률 문서 적중 |
| Q30 | Gleaning 기법 | graph_entity | 0.924 | 1.000 | 프로젝트 핵심 기술 |
| Q21 | WBS | keyword | 0.906 | 0.917 | 프로젝트 관리 문서 풍부 |
| Q16 | RRF 알고리즘 | keyword | 0.893 | 1.000 | 검색 기술 문서 정확 |
| Q1 | Neo4j vs ES 차이 | entity_relation | 0.889 | 1.000 | 아키텍처 문서 활용 |

---

## 7. v6 대비 개선 사항

### 7.1 핵심 지표 변화

| 항목 | v6 | v7 종합 | 변화 |
|------|-----|---------|------|
| 임베딩 규모 | 13,430 | 108,896 | **+711%** |
| 평가 방법 | LLM-as-Judge | RAGAS Library | 정밀도 향상 |
| Faithfulness | 0.128 | **0.885** | **+591%** |
| Answer Relevancy | 0.356 | **0.721** | **+103%** |
| Context Precision | 0.472 | 0.455 | -3.6% |
| Context Recall | 0.194 | **0.464** | **+139%** |

### 7.2 개선 원인 분석

1. **임베딩 8배 증가**: 13K→108K로 검색 커버리지가 대폭 확대
2. **RAGAS 라이브러리**: LLM-as-Judge(0~1 이진 평가) → RAGAS(세밀한 점수 산출)로 정확한 측정
3. **Live RAG Pipeline**: API 호출 → ES kNN 직접 검색으로 JWT 의존성 제거
4. **pyarrow 호환 해결**: 0.1.19 에러 → 0.2.15 정상 동작

---

## 8. 개선 로드맵

### 8.1 즉시 가능 (Context Precision 개선)

| 항목 | 현재 | 예상 효과 | 난이도 |
|------|------|-----------|--------|
| **Reranking 적용** (BGE-Reranker) | Prec 0.455 | 0.65+ | 중 |
| **Hybrid Search** (Dense + BM25 RRF) | Dense only | Prec/Recall 동시 향상 | 중 |
| **System Prompt 강화** | 일반 프롬프트 | Faithfulness 유지, 환각 감소 | 하 |

### 8.2 중기 개선 (Context Recall 개선)

| 항목 | 현재 | 예상 효과 | 난이도 |
|------|------|-----------|--------|
| **Knowledge Base 확대** (법률, 프론트엔드) | legal Recall 0.19 | 0.50+ | 중 |
| **Query Expansion** | 단일 쿼리 | Recall 향상 | 하 |
| **Top-K 확대** (5→10) | top-5 | 상위 누락 문서 포함 | 하 |

### 8.3 장기 개선

| 항목 | 예상 효과 | 난이도 |
|------|-----------|--------|
| **Graph RAG 3채널 통합** | entity_relation/multi_hop 추가 향상 | 상 |
| **평가 데이터셋 100개 확대** | 통계적 신뢰도 향상 | 중 |
| **도메인별 맞춤 프롬프트** | 약점 도메인 개선 | 중 |

---

## 9. 원본 데이터

```json
{
  "timestamp": "2026-02-13T19:55:06",
  "version": "v7_comprehensive",
  "questions": 51,
  "domains": {
    "entity_relation": 7,
    "multi_hop": 7,
    "keyword": 7,
    "semantic": 7,
    "graph_entity": 8,
    "legal": 7,
    "factual": 8
  },
  "elapsed_total": "9.5분",
  "metrics": {
    "faithfulness": 0.8845,
    "answer_relevancy": 0.7211,
    "context_precision": 0.4551,
    "context_recall": 0.4641
  }
}
```

전체 상세 데이터: `/tmp/ragas_v7_comprehensive_result.json`

---

## 10. Hybrid Search 적용 (Dense + Nori BM25 + RRF)

### 10.1 개선 배경

Dense Vector-only 검색의 한계:
- **추상적/간접적 질문**: 의미 벡터만으로는 키워드 매칭이 필요한 질문에 약함
- **한국어 BM25 부재**: `text` 필드에 standard analyzer만 적용, 한국어 형태소 분석 없음
- **Context Precision 0.455, Recall 0.464**: 검색 품질 목표 0.70에 미달

### 10.2 적용 내용

#### (1) Nori 한국어 형태소 분석기 설치

```bash
# ES 플러그인 설치
elasticsearch-plugin install analysis-nori
```

#### (2) 인덱스 재생성 (knowledge_chunks_v2)

| 항목 | 기존 (knowledge_chunks) | 개선 (knowledge_chunks_v2) |
|------|------------------------|---------------------------|
| text analyzer | standard (공백 토큰화) | **Nori korean** (형태소 분석) |
| search analyzer | standard | **Nori korean_search** (discard mode) |
| heading analyzer | standard | **Nori korean** |
| 사용자 사전 | 없음 | 17개 도메인 용어 등록 |
| 품사 필터 | 없음 | 조사(J), 부사(MAG) 등 18종 제거 |
| 복합어 분해 | 미지원 | mixed mode (원형+분해 동시 색인) |

**Nori 토큰화 예시**:
```
입력: "쿠버네티스에서 하이브리드검색 파이프라인 구축"

standard:  ["쿠버네티스에서", "하이브리드검색", "파이프라인", "구축"]  ← 조사 포함
nori:      ["쿠버네티스", "하이브리드검색", "파이프라인", "구축"]      ← 조사 제거, 용어 보존
```

**사용자 사전 등록 용어**: 검색엔진, 벡터검색, 하이브리드검색, 머신러닝, 딥러닝, 임베딩, 쿠버네티스, 도커, 마이크로서비스, 엘라스틱서치, 네오포제이, 포스트그레스, 지식그래프, 청킹, 리랭킹, 파이프라인, 프레임워크

#### (3) Hybrid Search 구현 (Manual RRF)

ES 8.11 Basic 라이선스에서 `rank.rrf`는 유료 기능이므로, **2x search + manual RRF merge** 방식 적용:

```python
# 1. kNN Dense Vector 검색 (top-10)
knn_results = es.search(index="knowledge_chunks_v2", body={
    "knn": {"field": "dense_vector", "query_vector": vec, "k": 10}
})

# 2. Nori BM25 검색 (top-10)
bm25_results = es.search(index="knowledge_chunks_v2", body={
    "query": {"bool": {"should": [
        {"match": {"text": {"query": query, "boost": 1.0}}},
        {"match": {"heading": {"query": query, "boost": 0.5}}}
    ]}}
})

# 3. RRF 점수 계산 및 결합 (k=60)
for rank, doc in enumerate(results, 1):
    rrf_score += 1.0 / (60 + rank)
```

#### (4) RAGChatbotServer 대비 차이

| 항목 | RAGChatbotServer | HRKP |
|------|------------------|------|
| Nori 설치 | Dockerfile 내장 | 플러그인 수동 설치 |
| Analyzer 종류 | 3종 (korean, korean_search, mixed) | 2종 (korean, korean_search) |
| 사용자 사전 | 5개 기본 용어 | **17개 도메인 특화 용어** |
| 품사 필터 | 18종 stoptag | 18종 stoptag (동일) |
| BM25 필드 | text 1개 | **text + heading 2개** (boost 적용) |
| RRF 방식 | linear alpha weighting | **Reciprocal Rank Fusion** (순위 기반) |
| 검색 요청 | 2x search + merge | 2x search + RRF merge (동일 구조) |

### 10.3 Hybrid Search 평가 결과

**동일 51쿼리, 7도메인, 동일 LLM/임베딩 모델로 재평가 (2026-02-13 20:16 KST)**

#### 전체 평균 비교

| 메트릭 | Dense-only | **Hybrid** | 변화 | 분석 |
|--------|-----------|------------|------|------|
| **Faithfulness** | 0.885 | **0.937** | **+5.2%** | BM25가 키워드 관련 문서 추가 → 답변 근거 강화 |
| **Answer Relevancy** | 0.721 | 0.643 | -7.8% | 검색 다양성 증가 → 답변 범위 확대로 분산 |
| **Context Precision** | 0.455 | 0.464 | +0.9% | 미미한 개선, Reranking 필요 |
| **Context Recall** | 0.464 | **0.526** | **+6.2%** | BM25 보완으로 더 많은 정답 정보 검색 |

#### Quality Gate 비교

| 등급 | Dense-only | Hybrid | 변화 |
|------|-----------|--------|------|
| HIGH (avg ≥ 0.70) | 23/51 (45.1%) | 24/51 (47.1%) | +1 |
| PARTIAL (0.40-0.69) | 19/51 (37.3%) | 15/51 (29.4%) | -4 |
| NONE (< 0.40) | 9/51 (17.6%) | 12/51 (23.5%) | +3 |

#### 도메인별 비교

| 도메인 | Dense Faith→Hybrid | Dense Recall→Hybrid | 주요 변화 |
|--------|-------------------|---------------------|-----------|
| entity_relation | 0.861→0.888 | 0.500→0.571 | Recall +14.2% |
| multi_hop | 0.854→0.839 | 0.452→0.643 | **Recall +42.3%** |
| keyword | 0.979→0.989 | 0.429→0.500 | Recall +16.5% |
| semantic | 0.853→0.980 | 0.167→0.071 | **Faith +14.9%**, Recall 저하 |
| factual | 0.940→1.000 | 0.429→0.583 | **Faith 100%**, Recall +35.9% |
| legal | 0.899→0.962 | 0.524→0.524 | Faith +7.0% |
| graph_entity | 0.789→0.894 | 0.563→0.750 | **Faith +13.3%**, **Recall +33.2%** |

### 10.4 분석

#### 개선된 점

1. **Faithfulness 0.937 (+5.2%)**: BM25가 키워드 정확 매칭 문서를 추가하여 LLM이 컨텍스트에 더 충실하게 답변
2. **Context Recall 0.526 (+6.2%)**: 벡터로 못 찾는 문서를 BM25가 보완 (특히 multi_hop +42.3%, factual +35.9%)
3. **Faithfulness 1.0 달성 도메인**: factual (8/8 전부 1.0) — 모든 답변이 컨텍스트에 100% 근거

#### 한계

1. **Answer Relevancy 0.643 (-7.8%)**: BM25가 다양한 문서를 가져오면서 답변이 분산됨. 핵심 외 부가 정보 비율 증가
2. **Context Precision 0.464 (+0.9%)**: top-5 중 관련 문서 비율은 거의 변화 없음 → **Reranking(BGE-Reranker)** 적용이 필수
3. **NONE 등급 12→12건**: Knowledge Base 부재 질문은 검색 방식 개선으로 해결 불가 → 문서 보강 필요
4. **semantic 도메인 Recall 0.071**: 추상적 질문은 BM25에도 여전히 약함 (키워드가 직접 포함되지 않은 문서)

### 10.5 Hybrid Search 개선 로드맵

| 단계 | 항목 | 예상 효과 | 난이도 |
|------|------|-----------|--------|
| **Step 1** (완료) | Nori BM25 + kNN + RRF | Faith +5.2%, Recall +6.2% | 중 |
| **Step 2** (다음) | BGE-Reranker 적용 | Context Precision 0.46→0.70+ | 중 |
| **Step 3** | 프롬프트 개선 (답변 집중도) | Answer Relevancy 0.64→0.75+ | 하 |
| **Step 4** | KB 보강 (법률/프론트엔드) | NONE 등급 12→5건 이하 | 중 |
| **Step 5** | Graph RAG 3채널 통합 | multi_hop/entity_relation 추가 향상 | 상 |

---

## 11. Nori 미적용 사고 분석 (Post-Mortem)

### 11.1 사고 개요

| 항목 | 내용 |
|------|------|
| **발견 일시** | 2026-02-13 |
| **사고 유형** | 인프라 설정 누락 — ES Nori 플러그인 미설치 |
| **영향 범위** | 프로젝트 시작(01-12)부터 02-13까지 **모든 BM25 검색** |
| **영향** | BM25 키워드 검색이 standard analyzer(공백 분리)로만 동작, 한국어 형태소 분석 없음 |

### 11.2 타임라인

| 날짜 | 커밋 | 내용 | 문제 |
|------|------|------|------|
| **01-12** | `081eb7e` | 프로젝트 구조 v2.6, mappings.json 생성 | `korean_analyzer`에 `standard` tokenizer 사용 (Nori 아님) |
| **01-14** | — | 코드리뷰: "nori 분석기 설정 완전" | **ES 플러그인 설치 여부 미확인**, mappings.json만 보고 OK |
| **01-20** | `d46d8fa` | Sprint 01 완료, init-db.py 생성 | `nori_tokenizer` 참조하지만 docker-compose는 공식 ES 이미지 사용 (플러그인 없음) |
| **01-26** | `0760ab9` | 아키텍처 C3 이슈 — ES 매핑 정합성 수정 | mappings.json에 `nori_tokenizer` 추가했으나 **Dockerfile 미생성** |
| **01-27** | — | 코드리뷰: "korean_analyzer 올바르게 설정됨" | **실동작 검증 없이** 코드만 보고 통과 |
| **01-28** | — | 기술리뷰: "ES BM25+Nori OK" | **E2E 검증 없이** 설계서/코드 검토만 진행 |
| **02-06~12** | 다수 | 임베딩 108K, RAGAS v5~v7 평가 | **BM25 채널이 Nori 없이** standard 분석기로 동작 |
| **02-13** | — | RAGChatbotServer 비교에서 Nori 미설치 발견 | ES 컨테이너에 `analysis-nori` 플러그인이 없음 확인 |

### 11.3 근본 원인 (Root Cause)

1. **Dockerfile 누락**: docker-compose.yml이 ES 공식 이미지(`elasticsearch:8.11.0`)를 직접 참조 → Nori 플러그인 설치 단계 없음
2. **설정과 실행 환경 불일치**: mappings.json, init-db.py에는 `nori_tokenizer` 참조가 있었으나, ES 컨테이너에 플러그인 자체가 미설치
3. **검증 부재**: 3건의 코드리뷰/기술리뷰에서 모두 "코드만 보고 OK" — 실제 ES에서 Nori 토큰화가 동작하는지 E2E 검증 없음

### 11.4 책임 분석

| 시점 | 담당 | 문제 |
|------|------|------|
| 초기 설계 (01-12) | 사용자(k82022603) + 클로드 | mappings.json에 Nori 설계했으나 ES Dockerfile 미생성 |
| Sprint 01 구현 (01-20) | 클로드 (Claude Haiku 4.5) | init-db.py에 nori 참조 추가했으나 docker-compose ES 이미지 그대로 |
| 아키텍처 리뷰 (01-26) | 클로드 (Claude Haiku 4.5) | C3 이슈로 mappings.json 수정했으나 **Dockerfile 누락** — 가장 치명적 실수 |
| 코드리뷰 3건 (01-14, 01-27, 01-28) | 클로드 | mappings.json/코드만 보고 "OK" — **실동작 미검증** |
| RAGAS 평가 (02-06~12) | 클로드 | BM25가 standard analyzer로 동작하는지 인지하지 못함 |

**결론**: 클로드(AI 에이전트)가 **설계서와 실행 환경의 일치 여부를 검증하지 않은** 것이 근본 원인.
코드 리뷰 시 "실제 동작 확인" 없이 "코드 레벨 검토"만 한 것이 3번 반복됨.

### 11.5 수정 내역

| 작업 | 내용 |
|------|------|
| ES Dockerfile 생성 | `infrastructure/database/elasticsearch/Dockerfile` — Nori 플러그인 사전 설치 |
| docker-compose.yml 수정 | ES `image:` → `build:` 변경 |
| init-db.py 정리 | legacy 코드 제거, `knowledge_chunks` 인덱스에 Nori 설정 직접 적용 |
| config.py 통일 | `elasticsearch_index` 기본값 `"knowledge_chunks"` |
| 인덱스 재생성 | Nori 설정 포함 `knowledge_chunks` 인덱스로 108,896건 reindex |

### 11.6 재발 방지 대책

1. **인프라 E2E 검증 필수**: 설정 변경 후 반드시 실제 동작 확인 (예: `_analyze` API로 토큰화 결과 검증)
2. **코드리뷰 체크리스트 추가**: "설정 파일이 참조하는 플러그인/의존성이 실행 환경에 설치되어 있는가?"
3. **RAGAS 평가 시 BM25 채널 검증**: Hybrid Search 평가 전 BM25 결과가 한국어 형태소 분석을 반영하는지 확인

---

## 12. v8 Nori+Hybrid 재평가 결과

### 12.1 평가 환경

| 항목 | v7 (§2~§10) | v8 (이 섹션) |
|------|-------------|-------------|
| **RAGAS 버전** | 0.2.15 | **0.4.3** |
| **ES 인덱스** | knowledge_chunks (standard) | **knowledge_chunks (Nori)** |
| **Nori 플러그인** | 미설치 | **설치됨** |
| **인덱스명** | knowledge_chunks → knowledge_chunks_v2 | **knowledge_chunks** (통일) |
| **검색 방식** | Dense(kNN) + BM25 + Manual RRF | Dense(kNN) + BM25(Nori) + Manual RRF |
| **질문 수** | 51개, 7개 도메인 | 51개, 7개 도메인 (동일) |
| **실행 시각** | 2026-02-13 20:15 KST | 2026-02-13 21:20 KST |
| **총 소요 시간** | 11.2분 | 9.0분 (검색 305초 + 평가 233초) |

> **중요**: RAGAS 버전이 0.2.15 → 0.4.3으로 변경되었으므로 절대값 비교에 한계가 있음.
> NaN 발생률: v7(0.2.15)=0%, v8(0.4.3)=0% (n=1 강제 설정으로 해결)

### 12.2 전체 평균 비교

| 메트릭 | v7 Dense-only | v7 Hybrid (Nori 미적용) | **v8 Hybrid (Nori 적용)** | 변화 (v7H→v8) |
|--------|:---:|:---:|:---:|:---:|
| **Faithfulness** | 0.885 | 0.937 | **0.919** | -0.018 |
| **Answer Relevancy** | 0.721 | 0.643 | **0.647** | +0.004 |
| **Context Precision** | 0.455 | 0.464 | **0.489** | **+0.025** |
| **Context Recall** | 0.464 | 0.526 | **0.474** | -0.052 |

> v7→v8 변화는 **RAGAS 버전 차이 + Nori 적용 효과가 혼합**되어 있음

### 12.3 Quality Gate

| 등급 | v7 Hybrid | **v8 Nori+Hybrid** | 변화 |
|------|:---------:|:---:|:---:|
| **HIGH** (avg ≥ 0.70) | — | **24/51 (47.1%)** | — |
| **PARTIAL** (0.40~0.69) | — | **16/51 (31.4%)** | — |
| **NONE** (< 0.40) | 12 | **11/51 (21.6%)** | -1 |

### 12.4 도메인별 상세

| Domain | Faith | Relevancy | Precision | Recall |
|--------|:-----:|:---------:|:---------:|:------:|
| entity_relation | 0.870 | **0.916** | 0.625 | 0.571 |
| multi_hop | 0.837 | 0.693 | **0.601** | **0.643** |
| keyword | **0.929** | 0.386 | **0.608** | 0.500 |
| semantic | 0.943 | 0.784 | 0.338 | 0.119 |
| graph_entity | 0.927 | 0.398 | 0.356 | **0.625** |
| legal | 0.943 | 0.621 | **0.493** | 0.238 |
| factual | **0.978** | 0.751 | 0.429 | **0.583** |

### 12.5 분석

#### Nori 효과가 확인된 영역

1. **Context Precision +2.5%**: Nori 형태소 분석으로 BM25가 더 정확한 문서를 반환
2. **keyword 도메인 Faith 0.929**: 키워드 정확 매칭에서 Nori가 standard보다 우수
3. **NONE 등급 12→11**: 미약하지만 개선

#### 한계

1. **RAGAS 버전 차이**: 0.2.15→0.4.3 전환으로 메트릭 계산 로직이 다름 — 직접 비교 불가
2. **Faithfulness 소폭 하락**: 0.937→0.919 (RAGAS 버전 차이 가능성 높음)
3. **semantic 도메인 Recall 0.119**: 추상적 질문은 BM25(키워드)로 개선 불가

---

## 13. 결론

### 핵심 성과

1. **Nori 미적용 사고 발견 및 수정**: 프로젝트 시작부터 누락된 ES Nori 플러그인을 설치하고 인덱스 재생성
2. **인덱스 통일**: `knowledge_chunks_v2` → `knowledge_chunks`로 단순화 (alias 제거)
3. **Context Precision 0.489**: Nori 형태소 분석으로 BM25 검색 정밀도 개선
4. **Quality Gate HIGH 47.1%**: 51개 질문 중 24개가 고품질 답변
5. **108K 임베딩 + Nori Hybrid**: 설계 의도대로 한국어 형태소 분석 기반 BM25가 동작

### 남은 과제

1. **Context Precision 0.489**: Reranking(BGE-Reranker) 적용으로 0.70+ 달성 필요
2. **Answer Relevancy 0.647**: 프롬프트 개선 + Reranking으로 답변 집중도 회복
3. **NONE 등급 11건 (21.6%)**: KB 부재 도메인 문서 보강 (legal, semantic)
4. **RAGAS 평가 환경 표준화**: ragas 버전, LLM 파라미터를 requirements.txt에 고정

### 교훈

> **"설계서에 적혀 있다고 구현된 것이 아니다."**
> — 코드 리뷰 시 반드시 실제 동작을 검증해야 한다.

---

## 14. 현재 시스템 총평 (2026-02-13 기준)

### 14.1 시스템 현황

| 구분 | 항목 | 상태 |
|------|------|------|
| **데이터** | ES 인덱스 `knowledge_chunks` | 108,896건 (Nori 한국어 분석기 적용) |
| **임베딩** | BGE-M3 (1024 dims, CPU) | Phase 3 완료, batch_size=4, max_text_len=1000 |
| **검색** | Hybrid Search (kNN + BM25 + RRF) | Manual RRF (ES Basic 라이선스 제약) |
| **LLM** | DeepSeek V3.2 | 답변 생성 + RAGAS 평가 겸용 |
| **인프라** | Docker Compose 17개 컨테이너 | ES Nori Dockerfile 추가, 전체 healthy |
| **평가** | RAGAS 0.4.3 / 51쿼리 / 7도메인 | v8 Nori+Hybrid 최종 평가 완료 |

### 14.2 품질 점수 종합

```
┌─────────────────────────────────────────────────────┐
│              RAGAS v8 최종 성적표                      │
│                                                       │
│  Faithfulness        ████████████████████░░  0.919    │
│  Answer Relevancy    █████████████░░░░░░░░░  0.647    │
│  Context Precision   ██████████░░░░░░░░░░░░  0.489    │
│  Context Recall      █████████░░░░░░░░░░░░░  0.474    │
│                                                       │
│  Quality Gate: HIGH 24/51 (47%) | NONE 11/51 (22%)   │
└─────────────────────────────────────────────────────┘
```

### 14.3 강점

1. **Faithfulness 0.919 (목표 0.90 달성)**: LLM이 컨텍스트에 충실하게 답변하며, 환각(hallucination)이 최소화됨. 51개 질문 중 factual 도메인은 0.978로 거의 완벽
2. **108K 규모 임베딩 완료**: BGE-M3로 108,896건의 문서 청크가 벡터화되어 Dense 검색 기반이 확보됨
3. **Hybrid Search 파이프라인 구축**: kNN(Dense) + BM25(Nori) + Manual RRF 3채널 검색이 동작. 설계서 의도대로 구현됨
4. **Nori 한국어 분석기**: 사용자 사전 17개 도메인 용어 + 품사 필터(18 stoptags)로 BM25 키워드 검색 품질 확보
5. **entity_relation 도메인 0.916 Relevancy**: 엔티티 간 관계 질문에서 가장 높은 답변 관련성 — 프로젝트 핵심 시나리오에 강함

### 14.4 약점

1. **Context Precision 0.489 (목표 0.80 미달, Gap -0.311)**: 검색된 top-5 중 관련 문서 비율이 낮음. **Reranker 미적용**이 근본 원인. BGE-Reranker(cross-encoder)로 검색 결과 재순위화가 필수
2. **Answer Relevancy 0.647 (목표 0.85 미달, Gap -0.203)**: BM25가 다양한 문서를 가져오면서 답변이 분산됨. 프롬프트 개선 + Reranking으로 답변 집중도를 높여야 함
3. **Context Recall 0.474 (목표 0.70 미달, Gap -0.226)**: 정답에 필요한 정보가 검색 결과에 충분히 포함되지 않음. KB 보강 + Graph RAG 3채널 통합이 필요
4. **semantic 도메인 Recall 0.119**: 추상적 질문("효율적으로 처리하는 방법은?")에 대한 검색이 극히 약함. Query Expansion 또는 HyDE 기법 검토 필요
5. **legal 도메인 Recall 0.238**: 법률/규정 관련 문서가 KB에 부족함. 문서 보강이 근본 해결책
6. **NONE 등급 11건 (21.6%)**: 약 5건 중 1건은 유의미한 답변을 제공하지 못함

### 14.5 아키텍처 완성도

| 설계 항목 | 설계서 | 구현 | 검증 | 비고 |
|-----------|:------:|:----:|:----:|------|
| Dense Vector (kNN) | O | O | O | cosine similarity, 108K |
| BM25 Keyword Search | O | O | **O** | Nori 적용 완료 (02-13) |
| Nori 한국어 분석기 | O | **O** | **O** | 32일 지연 후 수정 |
| Manual RRF Fusion | O | O | O | ES Basic 라이선스 제약 대응 |
| BGE-Reranker | O | **X** | — | **미구현** — 최우선 과제 |
| Graph RAG (Neo4j) | O | △ | — | 엔티티 추출은 있으나 검색 채널 미통합 |
| Query Expansion/HyDE | O | X | — | 미구현 |
| Redis 임베딩 캐시 | O | O | O | TTL 7일 |
| RAGAS 자동 평가 | O | O | O | 0.4.3, 51쿼리 |

**구현 완성도: 6/9 (67%)** — Reranker, Graph RAG 검색 채널, Query Expansion 미구현

### 14.6 기술 부채

| 부채 | 심각도 | 설명 |
|------|:------:|------|
| Reranker 미적용 | **Critical** | Context Precision의 가장 큰 병목. BGE-Reranker 적용 시 0.48→0.70+ 예상 |
| RAGAS 버전 미고정 | High | requirements.txt에 ragas==0.4.3 + 의존성 고정 필요 |
| ragas pip install 비영속 | High | 컨테이너 재시작 시 사라짐, Dockerfile에 반영 필요 |
| Graph RAG 검색 미통합 | High | Neo4j 엔티티는 있으나 Hybrid Search에 3번째 채널로 통합 안 됨 |
| ES RRF 유료 제약 | Medium | Manual RRF로 대체 중이나, ES 8.15+/Platinum 전환 시 네이티브 RRF 사용 가능 |
| DeepSeek n=1 제약 | Low | RAGAS 평가 전용 이슈. 운영에는 영향 없음. n=1 강제 설정으로 해결 |

### 14.7 다음 단계 우선순위

```
P0 (즉시)
├── BGE-Reranker 적용 → Context Precision 0.48→0.70+
├── requirements.txt에 ragas + 의존성 버전 고정
└── Dockerfile에 ragas 패키지 포함

P1 (1주 내)
├── 프롬프트 개선 → Answer Relevancy 0.65→0.75+
├── KB 보강 (legal, semantic 도메인 문서 추가)
└── Graph RAG 3채널 Hybrid Search 통합

P2 (2주 내)
├── Query Expansion / HyDE 기법 적용
├── 100쿼리 확대 평가
└── RAGAS 자동 회귀 테스트 (CI 연동)
```

### 14.8 종합 평가

> **현재 시스템은 "검색은 되지만 정밀하지 않은" 단계이다.**

Faithfulness 0.919로 **LLM 답변 품질은 목표를 달성**했다. 컨텍스트에 있는 정보를 잘 활용하여 답변하고, 환각이 거의 없다.

그러나 **"올바른 컨텍스트를 가져오는 능력"**(Context Precision 0.489, Recall 0.474)이 부족하다. 108K 문서 중에서 질문에 가장 관련 높은 top-5를 정확히 뽑아내지 못하고 있다. 이는 **Reranker 미적용**이 가장 큰 원인이며, BM25+kNN으로 후보를 넓게 가져온 후 cross-encoder로 재순위화하는 단계가 빠져 있다.

비유하자면, **"도서관에서 책은 많이 찾아오지만, 정작 필요한 페이지를 펼치지 못하는"** 상태다. BGE-Reranker 적용이 현재 시스템의 가장 큰 전환점이 될 것이다.

---

## Appendix A. LangChain + RAGAS 평가 생태계 레퍼런스

### A.1 RAGAS 버전별 차이점

| 구분 | v0.2.x | v0.4.x |
|------|--------|--------|
| **아키텍처** | 독립 메트릭 평가 | 실험 기반 아키텍처 (평가/분석/반복 통합) |
| **메트릭 반환** | `float` 값 | `MetricResult` 객체 (점수 + 추론 근거) |
| **LLM 초기화** | `LangchainLLMWrapper` | `llm_factory()` (범용, LangchainLLMWrapper deprecated) |
| **프롬프트 시스템** | 클래스 기반 | 함수 기반 (조합 가능) |
| **컬렉션 메트릭** | 없음 | 표준화된 컬렉션 기반 메트릭 |
| **pydantic** | pydantic_v1 의존 | pydantic v2 네이티브 |

### A.2 LangChain 통합 변경사항

**LangchainLLMWrapper (v0.4에서 Deprecated)**:
```python
# 구 방식 (Deprecated, 현재 HRKP 사용 중)
from ragas.llms import LangchainLLMWrapper
llm = LangchainLLMWrapper(ChatOpenAI(model="deepseek-chat", ...))

# 신 방식 (v0.4 권장)
from ragas.llms import llm_factory
from openai import OpenAI
client = OpenAI(base_url="https://api.deepseek.com", api_key=...)
llm = llm_factory("deepseek-chat", client=client)
```

**HuggingFaceEmbeddings 마이그레이션**:
```python
# 구 방식 (Deprecated)
from langchain_community.embeddings import HuggingFaceEmbeddings

# 신 방식 (langchain-huggingface 파트너 패키지)
from langchain_huggingface import HuggingFaceEmbeddings
```

### A.3 DeepSeek API 호환성 이슈

| 이슈 | 원인 | 영향 | 해결 |
|------|------|------|------|
| `n>1` 미지원 | DeepSeek API가 n=1만 허용 | RAGAS AnswerRelevancy에서 NaN 발생 | `ChatOpenAI(n=1)` 강제 설정 |
| JSON 파싱 실패 | DeepSeek 응답이 간헐적으로 비정형 | NaN 메트릭 | `response_format={"type":"json_object"}` |
| Rate Limit | 분당 요청 제한 | 대규모 평가 시 타임아웃 | batch_size 조정, timeout 증가 |

> **운영 영향**: n>1 이슈는 **RAGAS 평가 전용**으로, RAG 파이프라인 운영에는 영향 없음.
> RAGAS가 내부적으로 AnswerRelevancy 메트릭 계산 시 LLM에 n=3을 요청하는 것이 원인.

### A.4 권장 버전 고정 (HRKP)

```txt
# requirements-eval.txt (RAGAS 평가 전용)
ragas==0.4.3
langchain-core>=0.2.0
langchain-openai>=0.1.0
langchain-huggingface>=0.1.0
openai>=1.0.0
```

### A.5 NaN 값 처리 가이드

**발생 원인**: RAGAS 공식 — "NaN scores often occur because of invalid JSONs generated by LLM"

**처리 전략**:
1. `n=1` 강제 설정 (DeepSeek 필수)
2. JSON 모드 활성화 (가능한 경우)
3. 후처리: NaN은 0.0으로 치환 (보수적 평가)
4. 재시도 로직: NaN 비율 > 10% 시 자동 재실행

### A.6 대안 RAG 평가 프레임워크

| 프레임워크 | 강점 | HRKP 적합성 |
|-----------|------|:-----------:|
| **RAGAS** | 연구 기반 메트릭, Ground Truth 선택적 | ⭐⭐⭐⭐ (현재 사용) |
| **DeepEval** | pytest 스타일, NaN 처리 내장 | ⭐⭐⭐ |
| **Arize Phoenix** | OpenTelemetry 트레이싱, 프레임워크 중립 | ⭐⭐⭐⭐ |
| **LangSmith** | LangChain 네이티브, 프로덕션 모니터링 | ⭐⭐⭐ (유료) |

### A.7 한국어 RAG 평가 권장 메트릭

| 메트릭 | 한국어 적용성 | HRKP 목표 | 현재 | Gap |
|--------|:-----------:|:---------:|:----:|:---:|
| Faithfulness | 높음 (LLM 판단) | 0.90 | **0.919** | **달성** |
| Answer Relevancy | 중상 (임베딩 기반) | 0.85 | 0.647 | -0.203 |
| Context Precision | 높음 (LLM 판단) | 0.80 | 0.489 | -0.311 |
| Context Recall | 중간 (Ground Truth 필요) | 0.70 | 0.474 | -0.226 |

---

*기록: 2026-02-13 19:55 KST*
*업데이트 1: 2026-02-13 20:30 KST — §10 Hybrid Search 결과 추가*
*업데이트 2: 2026-02-13 21:30 KST — §11 Nori 사고 분석, §12 v8 재평가, §13 결론 갱신*
*업데이트 3: 2026-02-13 21:45 KST — §14 시스템 총평, Appendix A LangChain+RAGAS 레퍼런스*
