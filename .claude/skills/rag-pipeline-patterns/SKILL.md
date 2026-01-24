# RAG Pipeline Patterns

Hybrid RAG 파이프라인 구현을 위한 베스트 프랙티스와 패턴을 정의합니다.

## Purpose

RAG (Retrieval-Augmented Generation) 파이프라인의 일관된 품질과 성능을 보장합니다.

---

## RAG Architecture (VIP 3단계)

```
┌─────────────────────────────────────────────────────────────┐
│                    Value Layer (가치 계층)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │   Vector    │  │    Graph    │  │   Keyword   │          │
│  │   Search    │  │   Search    │  │   Search    │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                 Intelligent Layer (지능 계층)                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │   Rerank    │  │   Fusion    │  │   Context   │          │
│  │   (Cross)   │  │   (RRF)     │  │   Window    │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                  Planning Layer (계획 계층)                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │   Query     │  │   Response  │  │   Quality   │          │
│  │   Planning  │  │   Synthesis │  │   Check     │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

---

## Retrieval Patterns (검색 패턴)

### 1. Hybrid Search

```python
async def hybrid_search(
    query: str,
    top_k: int = 10,
    vector_weight: float = 0.4,
    graph_weight: float = 0.3,
    keyword_weight: float = 0.3
) -> List[Document]:
    """
    세 가지 검색 방식을 결합한 하이브리드 검색.

    Args:
        query: 검색 쿼리
        top_k: 반환할 문서 수
        vector_weight: 벡터 검색 가중치 (0-1)
        graph_weight: 그래프 검색 가중치 (0-1)
        keyword_weight: 키워드 검색 가중치 (0-1)

    Returns:
        List[Document]: 점수순 정렬된 문서 목록
    """
    # ✅ 병렬 검색 실행
    vector_results, graph_results, keyword_results = await asyncio.gather(
        vector_search(query, top_k * 2),
        graph_search(query, top_k * 2),
        keyword_search(query, top_k * 2)
    )

    # ✅ RRF (Reciprocal Rank Fusion) 적용
    fused_results = reciprocal_rank_fusion(
        [vector_results, graph_results, keyword_results],
        weights=[vector_weight, graph_weight, keyword_weight]
    )

    return fused_results[:top_k]
```

### 2. Reciprocal Rank Fusion (RRF)

```python
def reciprocal_rank_fusion(
    result_lists: List[List[Document]],
    weights: List[float],
    k: int = 60
) -> List[Document]:
    """
    RRF 알고리즘으로 여러 검색 결과를 융합.

    Formula: score = sum(weight * 1 / (k + rank))
    """
    scores = defaultdict(float)

    for results, weight in zip(result_lists, weights):
        for rank, doc in enumerate(results, 1):
            scores[doc.id] += weight * (1 / (k + rank))

    # 점수순 정렬
    sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [get_document(doc_id) for doc_id, _ in sorted_docs]
```

---

## Embedding Patterns (임베딩 패턴)

### Chunking Strategy

```python
# ✅ 권장 청킹 설정
CHUNK_CONFIG = {
    "chunk_size": 512,           # 토큰 기준
    "chunk_overlap": 50,         # 10% 오버랩
    "separator": "\n\n",         # 문단 기준
    "length_function": "tiktoken" # 정확한 토큰 계산
}

# ✅ 문서 타입별 청킹
DOCUMENT_CHUNKING = {
    "pdf": {"chunk_size": 512, "overlap": 50},
    "code": {"chunk_size": 256, "overlap": 30},
    "markdown": {"chunk_size": 1024, "overlap": 100}
}
```

### Embedding Model Selection

| 용도 | 모델 | 차원 |
|------|------|------|
| **한글 문서** | multilingual-e5-large | 1024 |
| **영문 코드** | text-embedding-3-small | 1536 |
| **혼합 문서** | bge-m3 | 1024 |

---

## Generation Patterns (생성 패턴)

### Context Window Management

```python
def build_context(
    documents: List[Document],
    max_tokens: int = 4000
) -> str:
    """
    컨텍스트 윈도우 내에서 최대한 많은 문서 포함.

    ✅ 중요: 토큰 제한 준수
    """
    context_parts = []
    current_tokens = 0

    for doc in documents:
        doc_tokens = count_tokens(doc.content)
        if current_tokens + doc_tokens > max_tokens:
            break
        context_parts.append(format_document(doc))
        current_tokens += doc_tokens

    return "\n\n---\n\n".join(context_parts)
```

### Prompt Template

```python
RAG_PROMPT_TEMPLATE = """
다음 컨텍스트를 기반으로 질문에 답변하세요.

## 컨텍스트
{context}

## 질문
{question}

## 답변 지침
1. 컨텍스트에 있는 정보만 사용하세요
2. 컨텍스트에 없으면 "정보를 찾을 수 없습니다"라고 답하세요
3. 출처를 명시하세요 (예: [문서명])
4. 한국어로 답변하세요

## 답변
"""
```

---

## Quality Patterns (품질 패턴)

### RAGAS Metrics

```python
# ✅ 필수 평가 메트릭
RAGAS_THRESHOLDS = {
    "faithfulness": 0.85,      # 답변이 컨텍스트에 기반하는가
    "answer_relevancy": 0.80,  # 답변이 질문과 관련있는가
    "context_precision": 0.75, # 검색된 컨텍스트가 정확한가
    "context_recall": 0.70     # 필요한 정보가 모두 검색되었는가
}

async def evaluate_response(
    question: str,
    answer: str,
    contexts: List[str],
    ground_truth: str = None
) -> Dict[str, float]:
    """RAGAS 메트릭으로 응답 품질 평가"""
    return await ragas.evaluate(
        question=question,
        answer=answer,
        contexts=contexts,
        ground_truth=ground_truth
    )
```

### Hallucination Prevention

```python
# ✅ 환각 방지 체크리스트
def check_hallucination(answer: str, contexts: List[str]) -> bool:
    """
    답변이 컨텍스트에 기반하는지 검증.

    Returns:
        True if no hallucination detected
    """
    # 1. 답변의 핵심 클레임 추출
    claims = extract_claims(answer)

    # 2. 각 클레임이 컨텍스트에서 지원되는지 확인
    for claim in claims:
        if not any(supports_claim(ctx, claim) for ctx in contexts):
            return False

    return True
```

---

## Anti-Patterns (안티패턴)

### 🚫 피해야 할 패턴

| 안티패턴 | 문제점 | 올바른 방식 |
|----------|--------|------------|
| 단일 검색만 사용 | 낮은 재현율 | Hybrid Search 사용 |
| 고정 청크 크기 | 문서 타입별 최적화 불가 | 문서 타입별 청킹 |
| 컨텍스트 무제한 | 토큰 초과, 비용 증가 | 토큰 제한 관리 |
| Rerank 미적용 | 관련성 낮은 문서 포함 | Cross-encoder Rerank |
| 품질 검증 없음 | 환각 위험 | RAGAS 평가 적용 |

---

## Integration with LangGraph

```python
from langgraph.graph import StateGraph

# ✅ RAG 워크플로우 정의
rag_workflow = StateGraph(RAGState)

rag_workflow.add_node("retrieve", retrieve_documents)
rag_workflow.add_node("rerank", rerank_documents)
rag_workflow.add_node("generate", generate_response)
rag_workflow.add_node("evaluate", evaluate_quality)

rag_workflow.add_edge("retrieve", "rerank")
rag_workflow.add_edge("rerank", "generate")
rag_workflow.add_edge("generate", "evaluate")

rag_workflow.set_entry_point("retrieve")
rag_workflow.set_finish_point("evaluate")
```

---

## Configuration Template

```yaml
# rag_config.yaml
retrieval:
  vector:
    model: "multilingual-e5-large"
    top_k: 20
    weight: 0.4
  graph:
    depth: 2
    top_k: 10
    weight: 0.3
  keyword:
    analyzer: "korean"
    top_k: 10
    weight: 0.3

reranking:
  model: "bge-reranker-v2-m3"
  top_k: 5

generation:
  model: "deepseek-chat"
  max_tokens: 2000
  temperature: 0.1

quality:
  min_faithfulness: 0.85
  min_relevancy: 0.80
```

---

**Version**: 1.0.0
**Last Updated**: 2026-01-24
