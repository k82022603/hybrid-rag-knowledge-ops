# STORY-051: RAG 파이프라인 통합 (ai_service <-> knowledge_service 연결)

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-41 |
| **Epic** | EPIC-002 |
| **Status** | To Do |
| **Priority** | Critical |
| **Story Points** | 8 |
| **Assignee** | RAG |
| **Sprint** | 4 |

---

## User Story

**As a** RAG 시스템 운영자,
**I want** ai_service와 knowledge_service의 이중 파이프라인을 단일 경로로 통합,
**So that** 검색 요청이 LangGraph workflow를 통해 실제 HybridRetriever를 호출하고 일관된 응답을 반환할 수 있음.

---

## Acceptance Criteria

- [ ] **Given** RetrieverNode 실행 시, **When** retrieve_fn이 호출됨, **Then** HybridRetriever.retrieve()가 실제 Elasticsearch + Neo4j에서 문서를 검색
- [ ] **Given** SearchService에 검색 요청 도달, **When** search() 메서드 실행, **Then** LangGraph workflow(Planner -> Retriever -> Reranker -> Generator)를 통해 응답 생성
- [ ] **Given** 통합 완료 후, **When** E2E 검색 요청 전송, **Then** Frontend -> Backend -> AI Service -> Knowledge Service -> DB 전체 경로 동작
- [ ] **Given** 이중 파이프라인(LangGraph vs RAGPipeline) 존재, **When** 통합 완료, **Then** 단일 LangGraph 경로만 활성화되고 레거시 경로는 제거 또는 비활성화
- [ ] **Given** HybridRetriever 부트스트랩 코드, **When** ai_service 시작 시, **Then** knowledge_service의 retriever 인스턴스가 DI로 주입됨

---

## Tasks

- [ ] HybridRetriever 인스턴스를 RetrieverNode.retrieve_fn에 주입하는 부트스트랩 코드 구현
- [ ] ai_service의 SearchService가 LangGraph workflow를 호출하도록 수정
- [ ] knowledge_service의 HybridRetriever HTTP API 또는 직접 임포트 연결
- [ ] 이중 파이프라인 중 레거시 RAGPipeline 경로 비활성화
- [ ] LangGraph State에 retrieval_results 필드 매핑 확인
- [ ] Reranker Node에서 HybridRetriever 결과를 올바르게 처리하도록 수정
- [ ] Generator Node에서 reranked 문서를 프롬프트에 포함하도록 확인
- [ ] 통합 스모크 테스트 작성 (검색 -> 리랭킹 -> 생성 전체 경로)
- [ ] 에러 핸들링: knowledge_service 연결 실패 시 graceful 오류 메시지

---

## 기술 노트

### 문제점 (Sprint 03 리뷰에서 도출)

Sprint 03에서 LangGraph workflow(STORY-033)와 HybridRetriever(STORY-030)를 각각 구현했으나, 두 시스템이 **실제로 연결되지 않은 상태**:

1. **RetrieverNode.retrieve_fn이 mock 데이터 반환** - 실제 HybridRetriever를 호출하지 않음
2. **이중 파이프라인 혼재** - ai_service에 LangGraph workflow와 별도의 RAGPipeline이 공존
3. **SearchService 라우팅 불명확** - 어떤 파이프라인을 사용할지 결정되지 않음

### 해결 아키텍처

```
┌─────────────────────────────────────────────────────┐
│ ai_service (LangGraph Workflow)                      │
│                                                      │
│  PlannerNode -> RetrieverNode -> RerankerNode        │
│                      │               │               │
│                      │ retrieve_fn   │ rerank_fn     │
│                      ▼               ▼               │
│              ┌──────────────┐  ┌──────────┐         │
│              │ HTTP Client  │  │ BGE       │         │
│              │ or Direct    │  │ Reranker  │         │
│              │ Import       │  │           │         │
│              └──────┬───────┘  └──────────┘         │
└─────────────────────┼───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│ knowledge_service                                    │
│                                                      │
│  HybridRetriever                                     │
│    ├── ElasticsearchRetriever (vector + keyword)     │
│    ├── Neo4jRetriever (graph traversal)              │
│    └── RRF Fusion (score merging)                    │
└─────────────────────────────────────────────────────┘
```

### 부트스트랩 코드 방향

```python
# ai_service/bootstrap.py
from knowledge_service.retriever import HybridRetriever
from ai_service.nodes import RetrieverNode

def bootstrap_pipeline():
    """LangGraph 노드에 실제 retriever를 주입"""
    retriever = HybridRetriever(
        es_client=get_es_client(),
        neo4j_driver=get_neo4j_driver(),
    )
    RetrieverNode.retrieve_fn = retriever.retrieve
```

### 영향 범위

- `ai_service/nodes/retriever_node.py` - retrieve_fn 주입 인터페이스
- `ai_service/services/search_service.py` - LangGraph workflow 단일 경로
- `ai_service/bootstrap.py` - 신규: 파이프라인 부트스트랩
- `knowledge_service/retriever/hybrid_retriever.py` - API 또는 직접 연결

---

## 테스트 계획

- [ ] Unit Test: RetrieverNode에 HybridRetriever.retrieve 주입 확인
- [ ] Unit Test: SearchService가 LangGraph workflow 호출 확인
- [ ] Integration Test: HybridRetriever -> Elasticsearch + Neo4j 실제 검색
- [ ] Integration Test: 전체 파이프라인 (Planner -> Retriever -> Reranker -> Generator)
- [ ] E2E Test: Frontend 검색 요청 -> Backend -> AI Service -> Knowledge Service -> 응답

---

## 참고 자료

- Sprint 03 완료 리뷰에서 도출 - 이중 파이프라인 통합 필요
- [STORY-030 HybridRetriever](./STORY-030-hybrid-retriever.md)
- [STORY-033 LangGraph Workflow](./STORY-033-langgraph-workflow.md)
- [상세 설계서 v2.4](../../knowledge_service/docs/02_design/hybrid_rag_platform_detailed_design.md)
