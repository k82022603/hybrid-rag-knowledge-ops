# STORY-032: BGE Reranker 통합

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-27 |
| **Epic** | EPIC-002 |
| **Status** | To Do |
| **Priority** | High |
| **Story Points** | 5 |
| **Assignee** | MLRag |
| **Sprint** | 3 |

---

## User Story

**As a** 검색 시스템 개발자,
**I want** BGE Reranker로 검색 결과 순위를 재조정,
**So that** 쿼리와 문서 간의 관련성을 더 정확하게 반영한 최종 순위를 제공함.

---

## Acceptance Criteria

- [ ] **Given** RRF 융합 결과 50개, **When** Reranker 적용, **Then** 재순위화된 결과 반환
- [ ] **Given** 쿼리와 문서 쌍, **When** Reranker 점수 계산, **Then** 0~1 범위의 관련성 점수 반환
- [ ] **Given** top_k=5, **When** Reranking 완료, **Then** 상위 5개 문서 반환
- [ ] **Given** Reranker 실행, **When** 응답 시간 측정, **Then** 50개 문서 기준 500ms 이내
- [ ] **Given** GPU 없는 환경, **When** Reranker 실행, **Then** CPU에서 정상 동작

---

## Tasks

- [ ] BGE-reranker-v2-m3 모델 로드
- [ ] Reranker 클래스 구현
- [ ] 배치 처리 최적화
- [ ] HybridRetriever와 통합
- [ ] CPU/GPU 환경 지원
- [ ] 캐싱 전략 구현
- [ ] 단위 테스트 작성
- [ ] 성능 벤치마크

---

## 기술 노트

### BGE Reranker

```python
# ai_service/src/reranking/bge_reranker.py
from typing import List, Tuple
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch

class BGEReranker:
    """
    BGE Reranker v2 M3
    - 모델: BAAI/bge-reranker-v2-m3
    - 크로스 인코더 기반 관련성 점수 계산
    - 다국어 지원 (한국어 포함)
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-v2-m3",
        device: str = None,
        batch_size: int = 32
    ):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.batch_size = batch_size

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.model.to(self.device)
        self.model.eval()

    @torch.no_grad()
    async def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: int = 5
    ) -> List[Document]:
        """
        문서 재순위화

        Args:
            query: 검색 쿼리
            documents: 재순위화할 문서 리스트
            top_k: 반환할 상위 문서 수

        Returns:
            재순위화된 문서 리스트
        """
        if not documents:
            return []

        # 쿼리-문서 쌍 생성
        pairs = [[query, doc.content] for doc in documents]

        # 배치 처리
        scores = []
        for i in range(0, len(pairs), self.batch_size):
            batch = pairs[i:i + self.batch_size]
            batch_scores = self._compute_scores(batch)
            scores.extend(batch_scores)

        # 점수와 문서 결합 후 정렬
        scored_docs = list(zip(documents, scores))
        scored_docs.sort(key=lambda x: x[1], reverse=True)

        # 점수 업데이트 및 반환
        return [
            Document(
                id=doc.id,
                content=doc.content,
                metadata={**doc.metadata, "rerank_score": score},
                score=score
            )
            for doc, score in scored_docs[:top_k]
        ]

    def _compute_scores(self, pairs: List[List[str]]) -> List[float]:
        """배치 점수 계산"""
        inputs = self.tokenizer(
            pairs,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt"
        ).to(self.device)

        outputs = self.model(**inputs)
        # Sigmoid로 0~1 정규화
        scores = torch.sigmoid(outputs.logits.squeeze(-1))
        return scores.cpu().tolist()

    async def rerank_with_scores(
        self,
        query: str,
        documents: List[Document]
    ) -> List[Tuple[Document, float]]:
        """점수와 함께 반환"""
        reranked = await self.rerank(query, documents, top_k=len(documents))
        return [(doc, doc.score) for doc in reranked]
```

### HybridRetriever 통합

```python
# hybrid_retriever.py 업데이트
class HybridRetriever:
    def __init__(
        self,
        es_retriever: ElasticsearchRetriever,
        neo4j_retriever: Neo4jRetriever,
        embedder: BGEEmbedder,
        rrf_fusion: RRFFusion,
        reranker: BGEReranker  # 추가
    ):
        self.reranker = reranker
        # ...

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        use_reranking: bool = True
    ) -> List[Document]:
        # ... 검색 및 RRF 융합 ...

        if use_reranking and len(fused) > top_k:
            # Reranking (상위 50개만)
            reranked = await self.reranker.rerank(
                query=query,
                documents=fused[:50],
                top_k=top_k
            )
            return reranked

        return fused[:top_k]
```

### 영향 범위
- `ai_service/src/reranking/bge_reranker.py` (신규)
- `ai_service/src/retrievers/hybrid_retriever.py` (수정)
- `ai_service/pyproject.toml` (transformers 의존성)

---

## 테스트 계획

- [ ] Unit Test: Reranker 점수 계산
- [ ] Unit Test: 배치 처리 동작
- [ ] Unit Test: 정렬 정확성
- [ ] Integration Test: HybridRetriever 연동
- [ ] Performance Test: 50개 문서 < 500ms

---

## 참고 자료

- [BGE Reranker HuggingFace](https://huggingface.co/BAAI/bge-reranker-v2-m3)
- [상세 설계서 v2.4](../../knowledge_service/docs/02_design/hybrid_rag_platform_detailed_design.md)
