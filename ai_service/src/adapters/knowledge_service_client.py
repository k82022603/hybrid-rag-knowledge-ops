"""
Knowledge Service HTTP Client

ai_service에서 knowledge_service의 검색/리랭킹 엔드포인트를
호출하기 위한 HTTP 클라이언트입니다.

두 가지 통신 모드를 지원합니다:
1. Direct Import (동일 프로세스): knowledge_service 모듈을 직접 임포트
2. HTTP REST (별도 프로세스): httpx를 통한 HTTP 통신

Architecture:
    ai_service (RetrieverNode)
        -> KnowledgeServiceClient
            -> [Direct] HybridRetriever.retrieve()
            -> [HTTP]   POST /api/v1/search/hybrid

STORY-051: RAG 파이프라인 통합
"""

import logging
import time
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ConnectionMode(str, Enum):
    """knowledge_service 연결 모드"""
    DIRECT = "direct"   # 동일 프로세스 내 직접 임포트
    HTTP = "http"       # HTTP REST API 호출


class KnowledgeServiceClient:
    """
    Knowledge Service 클라이언트

    ai_service에서 knowledge_service의 HybridRetriever와 SearchService에
    접근하기 위한 통합 클라이언트입니다.

    Direct 모드:
        - 동일 프로세스 내에서 knowledge_service 모듈을 직접 임포트
        - 네트워크 오버헤드 없음, 가장 효율적
        - 개발/테스트 환경에 적합

    HTTP 모드:
        - knowledge_service가 별도 프로세스로 실행될 때 사용
        - httpx 비동기 클라이언트로 REST API 호출
        - 프로덕션 마이크로서비스 환경에 적합

    Args:
        mode: 연결 모드 (direct 또는 http)
        base_url: HTTP 모드에서 knowledge_service URL
        timeout: HTTP 요청 타임아웃 (초)
        hybrid_retriever: Direct 모드에서 주입할 HybridRetriever 인스턴스
        search_service: Direct 모드에서 주입할 SearchService 인스턴스

    Example:
        >>> # Direct mode
        >>> client = KnowledgeServiceClient(
        ...     mode=ConnectionMode.DIRECT,
        ...     hybrid_retriever=retriever_instance,
        ... )
        >>> results = await client.hybrid_search("FastAPI 사용법")

        >>> # HTTP mode
        >>> client = KnowledgeServiceClient(
        ...     mode=ConnectionMode.HTTP,
        ...     base_url="http://localhost:8000",
        ... )
        >>> results = await client.hybrid_search("FastAPI 사용법")
    """

    def __init__(
        self,
        mode: ConnectionMode = ConnectionMode.DIRECT,
        base_url: str = "http://localhost:8000",
        timeout: float = 30.0,
        hybrid_retriever: Optional[Any] = None,
        search_service: Optional[Any] = None,
    ):
        """
        초기화

        Args:
            mode: 연결 모드
            base_url: HTTP 모드 base URL
            timeout: HTTP 타임아웃 (초)
            hybrid_retriever: Direct 모드 HybridRetriever 인스턴스
            search_service: Direct 모드 SearchService 인스턴스
        """
        self._mode = mode
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._hybrid_retriever = hybrid_retriever
        self._search_service = search_service
        self._http_client: Optional[Any] = None

        logger.info(
            "KnowledgeServiceClient initialized - mode=%s, base_url=%s",
            mode.value, base_url,
        )

    @property
    def mode(self) -> ConnectionMode:
        """현재 연결 모드"""
        return self._mode

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        strategy: str = "hybrid",
        filters: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Hybrid 검색 수행

        연결 모드에 따라 Direct 또는 HTTP 방식으로
        knowledge_service의 HybridRetriever를 호출합니다.

        Args:
            query: 검색 쿼리
            top_k: 반환할 결과 수
            strategy: 검색 전략 (keyword/semantic/hybrid)
            filters: 검색 필터
            user_id: 사용자 ID

        Returns:
            검색 결과 딕셔너리 목록
            각 항목: {chunk_id, document_id, content, score, source, metadata}
        """
        start_time = time.monotonic()

        try:
            if self._mode == ConnectionMode.DIRECT:
                results = await self._direct_hybrid_search(
                    query=query,
                    top_k=top_k,
                    strategy=strategy,
                    filters=filters,
                    user_id=user_id,
                )
            else:
                results = await self._http_hybrid_search(
                    query=query,
                    top_k=top_k,
                    strategy=strategy,
                    filters=filters,
                    user_id=user_id,
                )

            latency_ms = (time.monotonic() - start_time) * 1000
            logger.info(
                "KSClient hybrid_search - mode=%s, query='%s', "
                "results=%d, latency=%.1fms",
                self._mode.value, query[:50],
                len(results), latency_ms,
            )

            return results

        except Exception as e:
            latency_ms = (time.monotonic() - start_time) * 1000
            logger.error(
                "KSClient hybrid_search failed - mode=%s, "
                "query='%s', latency=%.1fms, error=%s",
                self._mode.value, query[:50], latency_ms, e,
            )
            return []

    async def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        리랭킹 수행

        Args:
            query: 검색 쿼리
            documents: 리랭킹 대상 문서 목록
            top_k: 반환할 상위 결과 수

        Returns:
            리랭킹된 문서 딕셔너리 목록
        """
        start_time = time.monotonic()

        try:
            if self._mode == ConnectionMode.DIRECT:
                results = await self._direct_rerank(
                    query=query,
                    documents=documents,
                    top_k=top_k,
                )
            else:
                results = await self._http_rerank(
                    query=query,
                    documents=documents,
                    top_k=top_k,
                )

            latency_ms = (time.monotonic() - start_time) * 1000
            logger.info(
                "KSClient rerank - mode=%s, input=%d, output=%d, latency=%.1fms",
                self._mode.value, len(documents),
                len(results), latency_ms,
            )

            return results

        except Exception as e:
            latency_ms = (time.monotonic() - start_time) * 1000
            logger.error(
                "KSClient rerank failed - mode=%s, latency=%.1fms, error=%s",
                self._mode.value, latency_ms, e,
            )
            # 리랭킹 실패 시 원본 반환
            return documents[:top_k]

    # ------------------------------------------------------------------
    # Direct Mode Implementation
    # ------------------------------------------------------------------

    async def _direct_hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        strategy: str = "hybrid",
        filters: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Direct 모드: HybridRetriever.retrieve() 직접 호출

        Args:
            query: 검색 쿼리
            top_k: 반환할 결과 수
            strategy: 검색 전략
            filters: 검색 필터
            user_id: 사용자 ID

        Returns:
            검색 결과 딕셔너리 목록
        """
        retriever = self._get_hybrid_retriever()

        if strategy == "keyword":
            results = await retriever.retrieve_by_source(
                query=query,
                source="keyword",
                top_k=top_k,
                filters=filters,
            )
        elif strategy == "semantic":
            results = await retriever.retrieve_by_source(
                query=query,
                source="vector",
                top_k=top_k,
                filters=filters,
            )
        else:
            # hybrid (기본값)
            results = await retriever.retrieve(
                query=query,
                top_k=top_k,
                filters=filters,
                user_id=user_id,
            )

        # SearchResult -> Dict 변환
        return [self._search_result_to_dict(r) for r in results]

    async def _direct_rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Direct 모드: BGEReranker.rerank() 직접 호출

        Args:
            query: 검색 쿼리
            documents: 문서 딕셔너리 목록
            top_k: 반환할 상위 결과 수

        Returns:
            리랭킹된 문서 딕셔너리 목록
        """
        retriever = self._get_hybrid_retriever()

        if retriever._reranker is not None:
            reranked = await retriever._reranker.rerank(
                query=query,
                documents=documents,
                top_k=top_k,
            )
            # RerankResult -> Dict 변환
            return [
                {
                    "chunk_id": r.doc_id,
                    "content": r.content,
                    "score": r.score,
                    "original_score": r.original_score,
                    "metadata": r.metadata,
                }
                for r in reranked
            ]

        # Reranker 미설정 시 원본 반환
        return documents[:top_k]

    def _get_hybrid_retriever(self) -> Any:
        """
        HybridRetriever 인스턴스 획득

        Returns:
            HybridRetriever 인스턴스

        Raises:
            RuntimeError: retriever가 설정되지 않은 경우
        """
        if self._hybrid_retriever is not None:
            return self._hybrid_retriever

        # 지연 임포트로 싱글톤 인스턴스 획득 시도
        try:
            from app.rag.retriever import get_hybrid_retriever
            self._hybrid_retriever = get_hybrid_retriever()
            return self._hybrid_retriever
        except ImportError:
            pass

        raise RuntimeError(
            "HybridRetriever not available. "
            "Provide hybrid_retriever in constructor or ensure "
            "knowledge_service is importable."
        )

    # ------------------------------------------------------------------
    # HTTP Mode Implementation
    # ------------------------------------------------------------------

    async def _http_hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        strategy: str = "hybrid",
        filters: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        HTTP 모드: knowledge_service REST API 호출

        Args:
            query: 검색 쿼리
            top_k: 반환할 결과 수
            strategy: 검색 전략
            filters: 검색 필터
            user_id: 사용자 ID

        Returns:
            검색 결과 딕셔너리 목록
        """
        client = await self._get_http_client()

        payload: Dict[str, Any] = {
            "query": query,
            "top_k": top_k,
            "search_type": strategy,
        }
        if filters:
            payload["filters"] = filters
        if user_id:
            payload["user_id"] = user_id

        response = await client.post(
            f"{self._base_url}/api/v1/search/hybrid",
            json=payload,
            timeout=self._timeout,
        )
        response.raise_for_status()

        data = response.json()
        results = data.get("results", [])

        return results

    async def _http_rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        HTTP 모드: knowledge_service 리랭킹 API 호출

        Args:
            query: 검색 쿼리
            documents: 문서 목록
            top_k: 반환할 상위 결과 수

        Returns:
            리랭킹된 문서 목록
        """
        client = await self._get_http_client()

        payload: Dict[str, Any] = {
            "query": query,
            "documents": documents,
            "top_k": top_k,
        }

        response = await client.post(
            f"{self._base_url}/api/v1/search/rerank",
            json=payload,
            timeout=self._timeout,
        )
        response.raise_for_status()

        data = response.json()
        return data.get("results", documents[:top_k])

    async def _get_http_client(self) -> Any:
        """
        httpx AsyncClient 획득 (지연 초기화)

        Returns:
            httpx.AsyncClient 인스턴스
        """
        if self._http_client is None:
            try:
                import httpx
                self._http_client = httpx.AsyncClient(
                    timeout=httpx.Timeout(self._timeout),
                    headers={"Content-Type": "application/json"},
                )
            except ImportError:
                raise RuntimeError(
                    "httpx is required for HTTP mode. "
                    "Install with: pip install httpx"
                )
        return self._http_client

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _search_result_to_dict(result: Any) -> Dict[str, Any]:
        """
        SearchResult(Pydantic) -> Dict 변환

        Args:
            result: SearchResult 인스턴스

        Returns:
            딕셔너리 표현
        """
        if isinstance(result, dict):
            return result

        return {
            "chunk_id": getattr(result, "chunk_id", ""),
            "document_id": getattr(result, "document_id", ""),
            "content": getattr(result, "content", ""),
            "score": float(getattr(result, "score", 0.0)),
            "source": getattr(result, "source", "unknown"),
            "metadata": dict(getattr(result, "metadata", {})),
        }

    async def close(self) -> None:
        """HTTP 클라이언트 종료"""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None
            logger.info("KnowledgeServiceClient HTTP client closed")

    def health_check(self) -> Dict[str, Any]:
        """
        클라이언트 상태 점검

        Returns:
            상태 정보 딕셔너리
        """
        return {
            "service": "KnowledgeServiceClient",
            "mode": self._mode.value,
            "base_url": self._base_url if self._mode == ConnectionMode.HTTP else "N/A",
            "retriever_available": self._hybrid_retriever is not None,
            "http_client_active": self._http_client is not None,
        }
