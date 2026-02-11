# HRKP v6 Cross-System RAGAS Evaluation Report

**평가 일시**: 2026-02-11 03:29 KST
**평가 방법**: LLM-as-Judge (DeepSeek V3.2)
**테스트 쿼리**: 50개 (7개 도메인)
**스크립트**: `scripts/rcsv_comparison_eval_v4.py`
**변경사항**: JWT 자동 갱신, 데이터 품질 사전 분석

---

## 0. 데이터 품질 사전 분석

| 항목 | 값 |
|------|-----|
| 총 청크 수 | 13,430 |
| GLYPH 아티팩트 | 2 (0.0%) |
| 짧은 청크 (<50자) | -1 |

## 0.5 Reranker 상태

- (상태 정보 미확인)

## 1. 시스템 비교

| 항목 | HRKP-RAW | HRKP-FULL | RCSV |
|------|----------|-----------|------|
| 검색 | BM25+Dense+Graph(RRF) | BM25+Dense+Graph(RRF)+**BGE Reranker** | BM25 only |
| 품질 필터 | 없음 | **Quality Gate v5** | 없음 |
| LLM | DeepSeek (별도 생성) | DeepSeek (파이프라인 내장) | DeepSeek (별도 생성) |

## 2. RAGAS 메트릭 비교

| 메트릭 | v5-RAW baseline | v6-RAW | v6-FULL | v6-RCSV |
|--------|:--------------:|:------:|:-------:|:-------:|
| faithfulness | 0.1440 | 0.1280 | 0.0200 | 0.0960 |
| answer_relevancy | 0.4560 | 0.3560 | 0.1560 | 0.2900 |
| context_precision | 0.3960 | 0.4720 | 0.1600 | 0.2100 |
| context_recall | 0.1500 | 0.1940 | 0.0000 | 0.0860 |

## 3. v6-FULL vs v5 baseline 개선

| 메트릭 | v5-FULL | v6-FULL | 변화량 | 판정 |
|--------|:------:|:-------:|:------:|:----:|
| faithfulness | 0.0000 | 0.0200 | +0.0200 | **UP** |
| answer_relevancy | 0.1340 | 0.1560 | +0.0220 | **UP** |
| context_precision | 0.2480 | 0.1600 | -0.0880 | DOWN |
| context_recall | 0.0150 | 0.0000 | -0.0150 | DOWN |

> **개선된 메트릭**: 2/4 (v5-FULL은 JWT 만료로 Q43-Q50 ERR 포함, 이번은 자동 갱신)

## 4. Quality Gate 분석

| Q# | 질문 | 도메인 | Grade | Max Score | Sources | 레이턴시 |
|:--:|------|--------|:-----:|:---------:|:-------:|--------:|
| Q1 | Neo4j와 Elasticsearch의 역할 차이점은?... | entity_relation | HIGH | 0.7967 | 5 | 61.7s |
| Q2 | LangGraph와 LangChain 중 어떤 것을 사용해야 하... | entity_relation | HIGH | 0.9958 | 5 | 30.8s |
| Q3 | FastAPI와 PostgreSQL을 연동하여 RAGAS 평가를... | entity_relation | HIGH | 0.5378 | 5 | 59.2s |
| Q4 | RAG Pipeline에서 BGE-M3 임베딩 모델의 역할은?... | multi_hop | HIGH | 0.7739 | 5 | 44.1s |
| Q5 | Kubernetes에서 Spring Boot 마이크로서비스를 배... | multi_hop | PARTIAL | 0.0111 | 1 | 49.7s |
| Q6 | Agentic AI 에이전트 워크플로우 설계 패턴은 무엇인가요?... | multi_hop | HIGH | 0.9964 | 3 | 47.7s |
| Q7 | Docker Compose 설정 방법은?... | keyword | PARTIAL | 0.0222 | 4 | 26.5s |
| Q8 | RRF 알고리즘이 Hybrid 검색에서 하는 역할은?... | keyword | HIGH | 0.1369 | 2 | 20.2s |
| Q9 | RAGAS 평가 메트릭의 종류와 의미는?... | keyword | PARTIAL | 0.0120 | 3 | 44.0s |
| Q10 | 대규모 문서를 효율적으로 처리하는 방법은?... | semantic | HIGH | 0.3949 | 2 | 33.8s |
| Q11 | 검색 성능을 최적화하려면 어떻게 해야 하나요?... | semantic | HIGH | 0.1508 | 5 | 46.0s |
| Q12 | 환경변수를 안전하게 관리하는 방법은?... | semantic | NONE | 0.0005 | 0 | 25.8s |
| Q13 | Spring Cloud Gateway에서 API 라우팅과 필터를... | graph_entity | PARTIAL | 0.0834 | 2 | 44.7s |
| Q14 | Redis 캐싱을 RAG 시스템에 적용하여 검색 성능을 개선하는... | graph_entity | HIGH | 0.6228 | 5 | 38.3s |
| Q15 | DeepSeek V3.2 모델의 특징과 비용 절감 효과는?... | graph_entity | HIGH | 0.9128 | 5 | 50.7s |
| Q16 | Vault를 사용한 시크릿 관리와 Spring Cloud Con... | graph_entity | NONE | 0.0006 | 0 | 32.9s |
| Q17 | GitHub Actions로 CI/CD 파이프라인을 구성하는 방... | graph_entity | PARTIAL | 0.0150 | 5 | 50.3s |
| Q18 | Eureka 서비스 디스커버리와 Kubernetes DNS 기반... | graph_entity | PARTIAL | 0.0443 | 2 | 59.1s |
| Q19 | React 18에서 Concurrent 렌더링과 Suspense... | graph_entity | PARTIAL | 0.0206 | 1 | 51.8s |
| Q20 | Python 3.11 기반 FastAPI 비동기 처리와 asyn... | graph_entity | HIGH | 0.3415 | 5 | 44.3s |
| Q21 | Strangler Fig 패턴을 활용한 레거시 시스템 점진적 마... | graph_entity | NONE | 0.0031 | 0 | 51.2s |
| Q22 | Gleaning 기법이란 무엇이며 RAG 파이프라인에서 어떻게 ... | graph_entity | PARTIAL | 0.0386 | 3 | 43.0s |
| Q23 | Vector Search와 Graph Search를 결합하면 어... | graph_entity | NONE | 0.0035 | 0 | 36.0s |
| Q24 | SSOT 원칙이란 무엇이며 데이터 아키텍처에서 왜 중요한가요?... | graph_entity | PARTIAL | 0.0488 | 2 | 47.5s |
| Q25 | 하이브리드 검색에서 BM25와 Dense Vector 검색의 가... | graph_entity | HIGH | 0.7425 | 5 | 46.2s |
| Q26 | 마이크로서비스 아키텍처에서 서비스 간 통신 패턴은 어떤 것들이 ... | graph_entity | PARTIAL | 0.0262 | 3 | 41.8s |
| Q27 | Dual-Write 문제란 무엇이며 MSA 환경에서 어떻게 해결... | graph_entity | PARTIAL | 0.0129 | 1 | 34.6s |
| Q28 | AI Service에서 RAG Pipeline의 전체 처리 흐름... | graph_entity | HIGH | 0.1832 | 3 | 51.0s |
| Q29 | 대한민국 헌법에서 국민의 기본권은 어떻게 규정하고 있나요?... | legal | HIGH | 0.8906 | 5 | 43.3s |
| Q30 | 민법에서 계약의 성립 요건은 무엇인가요?... | legal | HIGH | 0.1544 | 5 | 30.3s |
| Q31 | 형법에서 정당방위의 성립 요건은 무엇인가요?... | legal | HIGH | 0.2504 | 4 | 26.9s |
| Q32 | 상법에서 주식회사의 설립 절차는 어떻게 되나요?... | legal | HIGH | 0.8736 | 5 | 42.1s |
| Q33 | 민사소송법에서 소장 제출과 소송 진행 절차는?... | legal | HIGH | 0.8889 | 5 | 38.7s |
| Q34 | 문화재보호법에서 국가지정문화재의 지정 절차는?... | legal | HIGH | 0.9723 | 5 | 40.3s |
| Q35 | 소방시설법에서 특정소방대상물의 소방시설 설치 의무는?... | legal | HIGH | 0.8149 | 5 | 41.8s |
| Q36 | 법령 용어에서 '선의'와 '악의'의 법률적 의미 차이는?... | legal | PARTIAL | 0.0437 | 5 | 51.3s |
| Q37 | AI 에이전트에서 Tool Calling과 Reasoning의 ... | multi_hop | HIGH | 0.9949 | 5 | 41.8s |
| Q38 | Reranking이 RAG 검색 품질을 향상시키는 원리는 무엇인... | factual | HIGH | 0.7184 | 5 | 34.9s |
| Q39 | Agentic Mesh 아키텍처란 무엇이며 미래 AI 에이전트 ... | factual | HIGH | 0.8850 | 5 | 36.8s |
| Q40 | AI 오케스트레이션이란 무엇이며 2025년 주요 트렌드는?... | factual | HIGH | 0.4823 | 5 | 46.7s |
| Q41 | Chain of Thought 추론 방식이 LLM 성능에 미치는... | factual | HIGH | 0.2640 | 3 | 44.8s |
| Q42 | 강화학습(RL)을 활용한 검색 에이전트 학습 방법은 어떤 것이 ... | factual | HIGH | 0.9796 | 4 | 49.1s |
| Q43 | KT DS 아키텍처팀 AI 프로젝트 워크샵의 주요 주제는 무엇이... | factual | HIGH | 0.3834 | 5 | 28.5s |
| Q44 | MSA 차세대 플랫폼 전환 프로젝트에서 사용된 기술 스택은?... | graph_entity | HIGH | 0.4396 | 4 | 44.0s |
| Q45 | SLM(Small Language Model)과 LLM의 차이점... | comparative | HIGH | 0.9987 | 5 | 51.7s |
| Q46 | 비즈니스에 실제 활용 가능한 LLM 서비스를 만들기 위한 핵심 ... | factual | HIGH | 0.8733 | 5 | 35.8s |
| Q47 | 프롬프트 엔지니어링의 핵심 원칙과 효과적인 기법은 무엇인가요?... | semantic | HIGH | 0.9265 | 5 | 29.0s |
| Q48 | 벡터 임베딩의 차원 수가 검색 정확도에 미치는 영향은?... | semantic | NONE | 0.0030 | 0 | 37.8s |
| Q49 | LLM 환각(hallucination)을 줄이기 위한 효과적인 ... | semantic | HIGH | 0.7744 | 5 | 31.5s |
| Q50 | 모놀리식 아키텍처에서 마이크로서비스로 전환할 때 가장 큰 도전 ... | comparative | HIGH | 0.9239 | 5 | 34.8s |

### Grade 분포

| Grade | 건수 | 비율 |
|:-----:|:----:|:----:|
| **HIGH** | 33 | 66.0% |
| **PARTIAL** | 12 | 24.0% |
| **NONE** | 5 | 10.0% |

## 5. 도메인별 성능

| 도메인 | 쿼리 | HIGH | NONE | ERR | HIGH% | 평균 max_score |
|--------|:----:|:----:|:----:|:---:|:-----:|:--------------:|
| entity_relation | 3 | 3 | 0 | 0 | 100.0% | 0.777 |
| factual | 7 | 7 | 0 | 0 | 100.0% | 0.655 |
| comparative | 2 | 2 | 0 | 0 | 100.0% | 0.961 |
| legal | 8 | 7 | 0 | 0 | 87.5% | 0.611 |
| multi_hop | 4 | 3 | 0 | 0 | 75.0% | 0.694 |
| semantic | 6 | 4 | 2 | 0 | 66.7% | 0.375 |
| graph_entity | 17 | 6 | 3 | 0 | 35.3% | 0.208 |
| keyword | 3 | 1 | 0 | 0 | 33.3% | 0.057 |

## 6. 레이턴시

| 시스템 | 평균 레이턴시 |
|--------|:-----------:|
| HRKP-RAW | 6ms |
| HRKP-FULL | 41498ms |
| RCSV | 9ms |

## 7. 결론

- **개선된 메트릭**: 2/4 (vs v5-FULL)
- **JWT 만료 이슈**: 자동 갱신으로 해결 (15쿼리마다 재로그인)
- **데이터 품질**: GLYPH 아티팩트 2개 (0.0%)

---
*Generated: 2026-02-11 03:29 KST*
*Script: rcsv_comparison_eval_v4.py*