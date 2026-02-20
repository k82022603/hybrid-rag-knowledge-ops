# EPIC-002: Hybrid RAG Search

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-25 |
| **Status** | Closed - Project Completed (2026-02-18) |
| **Priority** | Critical |
| **Owner** | TBD |
| **Target Sprint** | Sprint 3 |
| **Total Story Points** | 34 |

---

## 요약

Elasticsearch Vector Search와 Neo4j Graph Search를 결합한 Hybrid RAG 파이프라인 구현. RRF Fusion 알고리즘과 BGE Reranker를 통해 검색 품질을 극대화하고, LangGraph 기반 워크플로우로 지능형 RAG 응답 생성.

---

## 배경 및 목표

### 배경
- 단일 검색 방식으로는 복잡한 질의에 대한 정확한 답변 어려움
- 벡터 검색의 의미적 유사성 + 그래프 검색의 관계 기반 추론 필요
- 검색 결과의 순위 최적화로 RAG 품질 향상 필요

### 목표
- Hybrid Search로 검색 재현율 30% 향상
- RRF + Reranking으로 Precision@5 > 0.8 달성
- LangGraph 워크플로우로 복잡한 RAG 시나리오 처리

### 성공 지표
- [ ] Hybrid Search Recall@10 >= 0.85
- [ ] Reranking 후 Precision@5 >= 0.8
- [ ] RAG Faithfulness >= 0.9
- [ ] 응답 지연시간 P95 < 3초

---

## User Stories

| ID | Jira | 제목 | Points | Status | Sprint |
|----|------|------|--------|--------|--------|
| STORY-030 | SCRUM-25 | HybridRetriever 구현 | 8 | Review | 3 |
| STORY-031 | SCRUM-26 | RRF Fusion 알고리즘 | 5 | To Do | 3 |
| STORY-032 | SCRUM-27 | BGE Reranker 통합 | 5 | To Do | 3 |
| STORY-033 | SCRUM-28 | LangGraph 워크플로우 | 8 | To Do | 3 |
| STORY-044 | SCRUM-33 | Backend Search Service | 5 | To Do | 3 |
| STORY-045 | SCRUM-34 | 초기 데이터 ETL | 3 | To Do | 3 |

---

## 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Hybrid RAG Pipeline                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────┐     ┌─────────────────────────────────────────┐           │
│  │  Query  │────▶│              Query Router               │           │
│  └─────────┘     └──────────────┬──────────────────────────┘           │
│                                 │                                       │
│                    ┌────────────┼────────────┐                         │
│                    ▼            ▼            ▼                         │
│              ┌──────────┐ ┌──────────┐ ┌──────────┐                    │
│              │   ES     │ │  Neo4j   │ │ Keyword  │                    │
│              │ Vector   │ │  Graph   │ │ Search   │                    │
│              └────┬─────┘ └────┬─────┘ └────┬─────┘                    │
│                   │            │            │                           │
│                   └────────────┼────────────┘                           │
│                                ▼                                        │
│                        ┌─────────────┐                                  │
│                        │ RRF Fusion  │                                  │
│                        └──────┬──────┘                                  │
│                               ▼                                         │
│                        ┌─────────────┐                                  │
│                        │ BGE Reranker│                                  │
│                        └──────┬──────┘                                  │
│                               ▼                                         │
│                        ┌─────────────┐                                  │
│                        │  Generator  │                                  │
│                        │ (DeepSeek)  │                                  │
│                        └──────┬──────┘                                  │
│                               ▼                                         │
│                        ┌─────────────┐                                  │
│                        │  Response   │                                  │
│                        └─────────────┘                                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 기술 요구사항

### 검색 엔진
| 구성요소 | 기술 | 용도 |
|----------|------|------|
| Vector Search | Elasticsearch 8.x (HNSW) | 의미적 유사성 검색 |
| Graph Search | Neo4j 5.x + Cypher | 관계 기반 추론 |
| Embedding | BGE-M3 (1024차원) | 다국어 임베딩 |
| Reranking | BGE-reranker-v2-m3 | 순위 재조정 |

### LangGraph 노드
| 노드 | 역할 |
|------|------|
| Planner | 질의 분석 및 검색 전략 결정 |
| Retriever | Hybrid 검색 실행 |
| Reranker | 결과 순위 최적화 |
| Generator | RAG 응답 생성 |
| Validator | 응답 품질 검증 |

### 성능 요구사항
| 항목 | 목표 |
|------|------|
| 검색 응답시간 | < 1초 |
| RAG 응답시간 | < 3초 (P95) |
| 동시 검색 | 50 QPS |

---

## 선행 조건 (Sprint 2 완료 필요)

- [x] Elasticsearch 벡터 인덱스 생성 (STORY-006) ✅ Review
- [x] Neo4j Knowledge Graph 구축 (STORY-005) ✅ Review
- [x] BGE-M3 임베딩 파이프라인 (STORY-004) ✅ Review (Basic 5/5, Integration 7/7)
- [ ] Backend AI Service 연동 기반 (API Gateway)

---

## 리스크 및 의존성

### 리스크
| 리스크 | 영향 | 대응 |
|--------|------|------|
| Reranker 지연시간 | Medium | 캐싱, 배치 처리 |
| Graph 쿼리 복잡도 | High | 쿼리 최적화, 인덱스 |
| LLM API 비용 | Medium | DeepSeek V3.2 사용 |

### 의존성
- [ ] BGE-M3 모델 다운로드
- [ ] BGE-reranker 모델 다운로드
- [ ] DeepSeek API 키 설정

---

## 참고 자료

- [상세 설계서 v2.4](../../knowledge_service/docs/02_design/01_hybrid_rag_platform_detailed_design.md)
- [API 통합 설계서](../../knowledge_service/docs/02_design/04_api_integration_design.md)
- [LangGraph 공식 문서](https://langchain-ai.github.io/langgraph/)
