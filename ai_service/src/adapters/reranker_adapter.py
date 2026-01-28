"""
Reranker Adapter

ai_service의 BGEReranker를 LangGraph 워크플로우에서
사용할 수 있도록 어댑트합니다.

현재 아키텍처에서는 리랭킹이 HybridRetriever.retrieve() 내부에서
자동으로 수행됩니다 (STORY-032에서 통합). 따라서 이 어댑터는
LangGraph 워크플로우에서 별도의 RerankerNode를 추가하고자 할 때
사용합니다.

Architecture:
    Option A (현재): RetrieverNode -> HybridRetriever(내장 reranking)
    Option B (확장): RetrieverNode -> RerankerNode(이 어댑터 사용)

STORY-051: RAG 파이프라인 통합
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class RerankerAdapter:
    """
    Reranker 어댑터

    BGEReranker 또는 KnowledgeServiceClient의 rerank 기능을
    LangGraph 워크플로우에서 사용할 수 있도록 변환합니다.

    Args:
        reranker: BGEReranker 인스턴스 (Direct 모드)
        client: KnowledgeServiceClient 인스턴스 (HTTP 모드)
        default_top_k: 기본 리랭킹 상위 결과 수

    Example:
        >>> adapter = RerankerAdapter(reranker=bge_reranker)
        >>> reranked = await adapter.rerank(
        ...     query="FastAPI 사용법",
        ...     documents=[{"content": "...", "score": 0.9}],
        ...     top_k=5,
        ... )
    """

    def __init__(
        self,
        reranker: Optional[Any] = None,
        client: Optional[Any] = None,
        default_top_k: int = 10,
    ):
        """
        초기화

        Args:
            reranker: BGEReranker 인스턴스 (Direct 모드 우선)
            client: KnowledgeServiceClient 인스턴스 (HTTP 모드 폴백)
            default_top_k: 기본 리랭킹 상위 결과 수
        """
        self._reranker = reranker
        self._client = client
        self._default_top_k = default_top_k

        logger.info(
            "RerankerAdapter initialized - direct_reranker=%s, "
            "http_client=%s, default_top_k=%d",
            reranker is not None,
            client is not None,
            default_top_k,
        )

    async def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        문서 리랭킹 수행

        Direct 모드(BGEReranker)를 우선 시도하고,
        실패 시 HTTP 모드(KnowledgeServiceClient)로 폴백합니다.

        Args:
            query: 검색 쿼리
            documents: 리랭킹 대상 문서 딕셔너리 목록
            top_k: 반환할 상위 결과 수 (None이면 기본값 사용)

        Returns:
            리랭킹된 문서 딕셔너리 목록 (score 업데이트됨)
        """
        if not documents:
            return []

        effective_top_k = top_k or self._default_top_k

        # Direct 모드: BGEReranker 직접 호출
        if self._reranker is not None:
            try:
                return await self._direct_rerank(
                    query=query,
                    documents=documents,
                    top_k=effective_top_k,
                )
            except Exception as e:
                logger.warning(
                    "Direct reranking failed, trying HTTP fallback: %s", e
                )

        # HTTP 모드: KnowledgeServiceClient 호출
        if self._client is not None:
            try:
                return await self._client.rerank(
                    query=query,
                    documents=documents,
                    top_k=effective_top_k,
                )
            except Exception as e:
                logger.warning(
                    "HTTP reranking failed, returning original order: %s", e
                )

        # 모든 방법 실패: 원본 순서 유지
        logger.warning("No reranker available, returning original document order")
        return documents[:effective_top_k]

    async def _direct_rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """
        BGEReranker 직접 리랭킹

        Args:
            query: 검색 쿼리
            documents: 문서 목록
            top_k: 반환할 상위 결과 수

        Returns:
            리랭킹된 문서 딕셔너리 목록
        """
        reranked = await self._reranker.rerank(
            query=query,
            documents=documents,
            top_k=top_k,
        )

        # RerankResult -> Dict 변환
        return [
            {
                "chunk_id": r.doc_id,
                "document_id": doc.get("document_id", ""),
                "content": r.content,
                "score": r.score,
                "original_score": r.original_score,
                "source": doc.get("source", "unknown"),
                "metadata": {
                    **doc.get("metadata", {}),
                    "rerank_score": r.score,
                    "rerank_rank": r.rank,
                    "original_score": r.original_score,
                },
            }
            for r, doc in zip(reranked, documents)
            if r is not None
        ]

    @property
    def is_available(self) -> bool:
        """리랭킹 가능 여부"""
        return self._reranker is not None or self._client is not None

    def health_check(self) -> Dict[str, Any]:
        """
        어댑터 상태 점검

        Returns:
            상태 정보 딕셔너리
        """
        reranker_health: Dict[str, Any] = {}
        if self._reranker is not None and hasattr(self._reranker, "health_check"):
            reranker_health = self._reranker.health_check()

        return {
            "service": "RerankerAdapter",
            "direct_reranker_available": self._reranker is not None,
            "http_client_available": self._client is not None,
            "default_top_k": self._default_top_k,
            "reranker": reranker_health,
        }
