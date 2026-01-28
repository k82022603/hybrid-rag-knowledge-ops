"""
Retriever Adapter

KnowledgeServiceClient의 hybrid_search를 RetrieverNode의 retrieve_fn
시그니처에 맞게 어댑트합니다.

RetrieverNode가 요구하는 retrieve_fn 시그니처:
    async def retrieve_fn(query: str, top_k: int, strategy: str) -> List[Dict]

KnowledgeServiceClient가 제공하는 인터페이스:
    async def hybrid_search(query, top_k, strategy, filters, user_id) -> List[Dict]

이 어댑터가 두 인터페이스를 연결합니다.

STORY-051: RAG 파이프라인 통합
"""

import logging
from typing import Any, Callable, Dict, List, Optional

from ai_service.src.adapters.knowledge_service_client import (
    ConnectionMode,
    KnowledgeServiceClient,
)

logger = logging.getLogger(__name__)


class RetrieverAdapter:
    """
    Retriever 어댑터

    KnowledgeServiceClient를 RetrieverNode.retrieve_fn 시그니처에
    맞게 변환합니다. RetrieverNode는 이 어댑터의 retrieve 메서드를
    retrieve_fn으로 사용합니다.

    Args:
        client: KnowledgeServiceClient 인스턴스
        default_top_k: 기본 검색 결과 수
        default_strategy: 기본 검색 전략

    Example:
        >>> client = KnowledgeServiceClient(mode=ConnectionMode.DIRECT, ...)
        >>> adapter = RetrieverAdapter(client=client)
        >>> retriever_node = RetrieverNode(retrieve_fn=adapter.retrieve)
    """

    def __init__(
        self,
        client: KnowledgeServiceClient,
        default_top_k: int = 10,
        default_strategy: str = "hybrid",
    ):
        """
        초기화

        Args:
            client: KnowledgeServiceClient 인스턴스
            default_top_k: 기본 검색 결과 수
            default_strategy: 기본 검색 전략
        """
        self._client = client
        self._default_top_k = default_top_k
        self._default_strategy = default_strategy

        logger.info(
            "RetrieverAdapter initialized - mode=%s, default_top_k=%d, "
            "default_strategy=%s",
            client.mode.value, default_top_k, default_strategy,
        )

    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
        strategy: str = "hybrid",
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """
        검색 수행 (RetrieverNode.retrieve_fn 호환 시그니처)

        RetrieverNode.__call__에서 다음과 같이 호출됩니다:
            documents = await self.retrieve_fn(
                query=query,
                top_k=self.top_k,
                strategy=strategy,
            )

        Args:
            query: 검색 쿼리
            top_k: 반환할 결과 수
            strategy: 검색 전략 (keyword/semantic/hybrid)
            **kwargs: 추가 파라미터 (filters, user_id 등)

        Returns:
            검색 결과 딕셔너리 목록.
            각 항목: {chunk_id, document_id, content, score, source, metadata}
        """
        effective_top_k = top_k or self._default_top_k
        effective_strategy = strategy or self._default_strategy

        logger.debug(
            "RetrieverAdapter.retrieve - query='%s', top_k=%d, strategy=%s",
            query[:50], effective_top_k, effective_strategy,
        )

        results = await self._client.hybrid_search(
            query=query,
            top_k=effective_top_k,
            strategy=effective_strategy,
            filters=kwargs.get("filters"),
            user_id=kwargs.get("user_id"),
        )

        logger.info(
            "RetrieverAdapter.retrieve - results=%d", len(results),
        )

        return results

    def as_retrieve_fn(self) -> Callable:
        """
        RetrieverNode.retrieve_fn으로 사용할 수 있는 callable 반환

        Returns:
            비동기 검색 함수
        """
        return self.retrieve

    def health_check(self) -> Dict[str, Any]:
        """
        어댑터 상태 점검

        Returns:
            상태 정보 딕셔너리
        """
        return {
            "service": "RetrieverAdapter",
            "client_mode": self._client.mode.value,
            "default_top_k": self._default_top_k,
            "default_strategy": self._default_strategy,
            "client_health": self._client.health_check(),
        }
