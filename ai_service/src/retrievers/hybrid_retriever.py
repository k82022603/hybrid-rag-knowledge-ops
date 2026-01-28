"""
Hybrid Retriever with Reranking Support

기존 knowledge_service의 HybridRetriever를 확장하여
BGE Reranker 통합을 제공하는 래퍼 모듈입니다.

Architecture:
    HybridRetriever.retrieve()
        -> SearchService.hybrid_search() (Vector + Keyword + Graph)
        -> RRF Fusion
        -> BGE Reranker (optional, use_reranking=True)
        -> Top-K 반환

STORY-032: BGE Reranker 통합 구현
"""

import logging
import time
from typing import Any, Dict, List, Optional

from ai_service.src.reranking.bge_reranker import BGEReranker, RerankResult

logger = logging.getLogger(__name__)


class HybridRetrieverWithReranking:
    """
    Reranking이 통합된 Hybrid Retriever

    기존 HybridRetriever의 검색 결과에 BGE Reranker를 적용하여
    정밀한 관련성 기반 재순위화를 수행합니다.

    Args:
        hybrid_retriever: 기존 HybridRetriever 인스턴스
        reranker: BGEReranker 인스턴스 (None이면 리랭킹 비활성화)
        rerank_top_n: 리랭킹에 사용할 상위 문서 수 (기본: 50)

    Attributes:
        hybrid_retriever: 기존 HybridRetriever 인스턴스
        reranker: BGEReranker 인스턴스
        rerank_top_n: 리랭킹 대상 문서 수
    """

    def __init__(
        self,
        hybrid_retriever: Any,
        reranker: Optional[BGEReranker] = None,
        rerank_top_n: int = 50,
    ):
        """
        초기화

        Args:
            hybrid_retriever: 기존 HybridRetriever 인스턴스
            reranker: BGEReranker 인스턴스
            rerank_top_n: 리랭킹에 사용할 상위 문서 수
        """
        self.hybrid_retriever = hybrid_retriever
        self.reranker = reranker
        self.rerank_top_n = rerank_top_n

    async def retrieve(
        self,
        query: str,
        entities: Optional[List[Dict[str, Any]]] = None,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        use_reranking: bool = True,
    ) -> List[Any]:
        """
        Hybrid 검색 + Reranking 수행

        1. HybridRetriever로 RRF 융합된 검색 결과 획득
        2. (선택) BGE Reranker로 상위 N개 문서 재순위화
        3. 상위 top_k개 반환

        Args:
            query: 검색 쿼리
            entities: 추출된 엔티티 목록
            top_k: 최종 반환할 결과 수
            filters: 검색 필터
            user_id: 사용자 ID
            use_reranking: 리랭킹 활성화 여부

        Returns:
            SearchResult 리스트 (리랭킹 적용 시 rerank_score 메타데이터 포함)
        """
        start_time = time.monotonic()

        # 1. 기존 HybridRetriever로 검색 (RRF 융합까지)
        # 리랭킹이 활성화된 경우, 더 많은 결과를 요청
        fetch_k = self.rerank_top_n if (use_reranking and self.reranker) else top_k

        fused_results = await self.hybrid_retriever.retrieve(
            query=query,
            entities=entities,
            top_k=fetch_k,
            filters=filters,
            user_id=user_id,
        )

        # 2. Reranking 적용
        if use_reranking and self.reranker and len(fused_results) > top_k:
            logger.info(
                "Applying reranking - query='%s', fused=%d, target_top_k=%d",
                query[:50], len(fused_results), top_k,
            )

            reranked_results = await self.reranker.rerank_search_results(
                query=query,
                search_results=fused_results[:self.rerank_top_n],
                top_k=top_k,
            )

            elapsed_ms = (time.monotonic() - start_time) * 1000
            logger.info(
                "Retrieve + Rerank complete - "
                "fused=%d, reranked=%d, latency=%.1fms",
                len(fused_results), len(reranked_results), elapsed_ms,
            )

            return reranked_results

        elapsed_ms = (time.monotonic() - start_time) * 1000
        logger.info(
            "Retrieve complete (no reranking) - results=%d, latency=%.1fms",
            len(fused_results), elapsed_ms,
        )

        return fused_results[:top_k]

    def health_check(self) -> Dict[str, Any]:
        """상태 점검"""
        base_health = {}
        if hasattr(self.hybrid_retriever, "health_check"):
            base_health = self.hybrid_retriever.health_check()

        reranker_health = {}
        if self.reranker:
            reranker_health = self.reranker.health_check()

        return {
            "service": "HybridRetrieverWithReranking",
            "hybrid_retriever": base_health,
            "reranker": reranker_health,
            "rerank_top_n": self.rerank_top_n,
            "reranking_enabled": self.reranker is not None,
        }
