"""
Hybrid Retriever

Elasticsearch Vector Search + Neo4j Graph Search를 결합한 Hybrid 검색
RRF (Reciprocal Rank Fusion) 기반 결과 융합
"""

import asyncio
from typing import Any, Dict, List, Optional

from app.agents.state import SearchResult
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class HybridRetriever:
    """
    Hybrid Retriever

    Vector Search (Elasticsearch kNN)와 Graph Search (Neo4j Cypher)를
    병렬로 실행하고 RRF로 결과를 융합합니다.
    """

    def __init__(
        self,
        es_client: Optional[Any] = None,
        neo4j_driver: Optional[Any] = None,
    ):
        """
        초기화

        Args:
            es_client: Elasticsearch 클라이언트
            neo4j_driver: Neo4j 드라이버
        """
        self.es_client = es_client
        self.neo4j_driver = neo4j_driver

    async def retrieve(
        self,
        query: str,
        entities: Optional[List[Dict[str, Any]]] = None,
        top_k: int = 10,
    ) -> List[SearchResult]:
        """
        Hybrid 검색 수행

        Args:
            query: 검색 질의
            entities: 추출된 엔티티 목록 (Graph Search 활용)
            top_k: 반환할 결과 수

        Returns:
            융합된 검색 결과 목록
        """
        logger.info(f"Hybrid retrieval - Query: {query[:50]}..., top_k={top_k}")

        # 1. 병렬 검색 실행
        es_results, neo_results = await asyncio.gather(
            self._vector_search(query, top_k=top_k * 2),
            self._graph_search(query, entities, top_k=top_k * 2),
        )

        logger.info(
            f"Search results - Vector: {len(es_results)}, Graph: {len(neo_results)}"
        )

        # 2. RRF 융합
        fused = self._rrf_fusion(es_results, neo_results, k=settings.rrf_k)

        # 3. Reranking (옵션)
        # TODO: Cross-encoder reranking 구현

        return fused[:top_k]

    async def _vector_search(
        self,
        query: str,
        top_k: int = 20,
    ) -> List[SearchResult]:
        """
        Elasticsearch kNN Vector Search

        Args:
            query: 검색 질의
            top_k: 반환할 결과 수

        Returns:
            Vector Search 결과 목록
        """
        if self.es_client is None:
            logger.warning("Elasticsearch client not initialized")
            return []

        # TODO: 실제 Elasticsearch kNN 검색 구현
        # query_vector = await self._get_embedding(query)
        # results = await self.es_client.search(
        #     index=settings.elasticsearch_index,
        #     knn={
        #         "field": "embedding",
        #         "query_vector": query_vector,
        #         "k": top_k,
        #         "num_candidates": top_k * 10,
        #     },
        # )

        return []

    async def _graph_search(
        self,
        query: str,
        entities: Optional[List[Dict[str, Any]]] = None,
        top_k: int = 20,
    ) -> List[SearchResult]:
        """
        Neo4j Graph Search

        Args:
            query: 검색 질의
            entities: 추출된 엔티티 목록
            top_k: 반환할 결과 수

        Returns:
            Graph Search 결과 목록
        """
        if self.neo4j_driver is None:
            logger.warning("Neo4j driver not initialized")
            return []

        # TODO: 실제 Neo4j Cypher 검색 구현
        # entity_names = [e["name"] for e in (entities or [])]
        # cypher = """
        # MATCH (d:Document)-[:CONTAINS]->(c:Chunk)
        # WHERE any(name IN $entity_names WHERE c.content CONTAINS name)
        # RETURN c.id AS chunk_id, c.content AS content, d.id AS document_id
        # LIMIT $top_k
        # """

        return []

    def _rrf_fusion(
        self,
        vector_results: List[SearchResult],
        graph_results: List[SearchResult],
        k: int = 60,
    ) -> List[SearchResult]:
        """
        RRF (Reciprocal Rank Fusion) 융합

        Args:
            vector_results: Vector Search 결과
            graph_results: Graph Search 결과
            k: RRF 파라미터 (기본값 60)

        Returns:
            융합된 결과 목록
        """
        scores: Dict[str, float] = {}
        results_map: Dict[str, SearchResult] = {}

        # Vector 결과 스코어 계산
        for rank, result in enumerate(vector_results):
            chunk_id = result.chunk_id
            scores[chunk_id] = scores.get(chunk_id, 0) + 1.0 / (k + rank + 1)
            results_map[chunk_id] = result

        # Graph 결과 스코어 계산
        for rank, result in enumerate(graph_results):
            chunk_id = result.chunk_id
            scores[chunk_id] = scores.get(chunk_id, 0) + 1.0 / (k + rank + 1)
            if chunk_id not in results_map:
                results_map[chunk_id] = result

        # 스코어 기준 정렬
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        # 결과 반환
        fused_results = []
        for chunk_id in sorted_ids:
            result = results_map[chunk_id]
            result.score = scores[chunk_id]
            fused_results.append(result)

        return fused_results


# 싱글톤 인스턴스
_retriever: Optional[HybridRetriever] = None


def get_hybrid_retriever() -> HybridRetriever:
    """Hybrid Retriever 인스턴스 반환"""
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever
