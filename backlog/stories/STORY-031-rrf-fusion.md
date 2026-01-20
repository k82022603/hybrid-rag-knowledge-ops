# STORY-031: RRF Fusion 알고리즘

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-31 |
| **Epic** | EPIC-002 |
| **Status** | To Do |
| **Priority** | High |
| **Story Points** | 5 |
| **Assignee** | MLRag |
| **Sprint** | 3 |

---

## User Story

**As a** 검색 시스템 개발자,
**I want** RRF(Reciprocal Rank Fusion) 알고리즘으로 다중 검색 결과를 융합,
**So that** 각 검색 엔진의 순위를 공정하게 반영한 최종 순위를 생성함.

---

## Acceptance Criteria

- [ ] **Given** ES 결과 20개 + Neo4j 결과 20개, **When** RRF Fusion 적용, **Then** 통합 순위 결과 반환
- [ ] **Given** 동일 문서가 양쪽에 존재, **When** 융합 시, **Then** 양쪽 순위 점수 합산
- [ ] **Given** 가중치 (es=0.6, neo4j=0.4), **When** 융합 시, **Then** 가중치 반영된 점수 계산
- [ ] **Given** k 파라미터 = 60, **When** 순위 점수 계산, **Then** RRF 공식 1/(k+rank) 적용
- [ ] **Given** 결과 목록, **When** 융합 완료, **Then** 정렬된 결과 반환

---

## Tasks

- [ ] RRF Fusion 알고리즘 구현
- [ ] 가중치 파라미터 지원
- [ ] k 파라미터 튜닝
- [ ] HybridRetriever와 통합
- [ ] 단위 테스트 작성
- [ ] 품질 벤치마크 (Precision/Recall)

---

## 기술 노트

### RRF 알고리즘

```python
# ai_service/src/retrievers/rrf_fusion.py
from collections import defaultdict
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class RRFResult:
    doc_id: str
    content: str
    metadata: dict
    rrf_score: float
    source_scores: Dict[str, float]  # {'es': 0.xx, 'neo4j': 0.xx}


class RRFFusion:
    """
    Reciprocal Rank Fusion (RRF) 알고리즘

    공식: RRF(d) = sum(1 / (k + r_i(d)))
    - k: 순위 안정화 상수 (기본값 60)
    - r_i(d): i번째 검색 엔진에서 문서 d의 순위
    """

    def __init__(self, k: int = 60):
        self.k = k

    def fuse(
        self,
        result_lists: List[List[Document]],
        weights: Optional[List[float]] = None,
        source_names: Optional[List[str]] = None
    ) -> List[RRFResult]:
        """
        다중 검색 결과 융합

        Args:
            result_lists: 검색 결과 리스트들 [[ES결과], [Neo4j결과], ...]
            weights: 각 검색 엔진의 가중치 [0.6, 0.4, ...]
            source_names: 소스 이름 ['es', 'neo4j', ...]

        Returns:
            RRF 점수로 정렬된 결과 리스트
        """
        if weights is None:
            weights = [1.0] * len(result_lists)

        if source_names is None:
            source_names = [f"source_{i}" for i in range(len(result_lists))]

        # 문서별 RRF 점수 및 메타 정보 수집
        scores: Dict[str, float] = defaultdict(float)
        source_scores: Dict[str, Dict[str, float]] = defaultdict(dict)
        doc_map: Dict[str, Document] = {}

        for source_idx, (results, weight, source_name) in enumerate(
            zip(result_lists, weights, source_names)
        ):
            for rank, doc in enumerate(results):
                # RRF 점수 계산: weight * 1/(k + rank + 1)
                rrf_score = weight / (self.k + rank + 1)
                scores[doc.id] += rrf_score
                source_scores[doc.id][source_name] = rrf_score

                # 문서 정보 저장 (첫 번째 등장 기준)
                if doc.id not in doc_map:
                    doc_map[doc.id] = doc

        # 정렬 및 결과 생성
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        return [
            RRFResult(
                doc_id=doc_id,
                content=doc_map[doc_id].content,
                metadata=doc_map[doc_id].metadata,
                rrf_score=scores[doc_id],
                source_scores=dict(source_scores[doc_id])
            )
            for doc_id in sorted_ids
        ]

    def fuse_with_explanation(
        self,
        result_lists: List[List[Document]],
        weights: List[float],
        source_names: List[str]
    ) -> Dict:
        """융합 과정 설명 포함"""
        results = self.fuse(result_lists, weights, source_names)

        return {
            "results": results,
            "fusion_params": {
                "k": self.k,
                "weights": dict(zip(source_names, weights)),
                "num_sources": len(result_lists)
            },
            "statistics": {
                "total_unique_docs": len(results),
                "max_rrf_score": results[0].rrf_score if results else 0,
                "min_rrf_score": results[-1].rrf_score if results else 0
            }
        }
```

### HybridRetriever 통합

```python
# hybrid_retriever.py 업데이트
class HybridRetriever:
    def __init__(self, ..., rrf_fusion: RRFFusion):
        self.rrf_fusion = rrf_fusion

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        es_weight: float = 0.5,
        neo4j_weight: float = 0.5
    ) -> List[Document]:
        # ... 검색 실행 ...

        # RRF Fusion 적용
        fused = self.rrf_fusion.fuse(
            result_lists=[es_results, neo4j_results],
            weights=[es_weight, neo4j_weight],
            source_names=["elasticsearch", "neo4j"]
        )

        return [
            Document(
                id=r.doc_id,
                content=r.content,
                metadata=r.metadata,
                score=r.rrf_score
            )
            for r in fused[:top_k]
        ]
```

### 영향 범위
- `ai_service/src/retrievers/rrf_fusion.py` (신규)
- `ai_service/src/retrievers/hybrid_retriever.py` (수정)

---

## 테스트 계획

- [ ] Unit Test: RRF 점수 계산 정확성
- [ ] Unit Test: 가중치 적용 검증
- [ ] Unit Test: 중복 문서 처리
- [ ] Integration Test: HybridRetriever 연동
- [ ] Quality Test: Precision@5 측정

---

## 참고 자료

- [RRF 논문](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
- [상세 설계서 v2.4](../../knowledge_service/docs/02_design/hybrid_rag_platform_detailed_design.md)
