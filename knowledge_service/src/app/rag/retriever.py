"""
Hybrid Retriever

Elasticsearch Vector Search + Neo4j Graph Search를 결합한 Hybrid 검색
SearchService 위임 구조로 중복 제거 (ADR-001)

Architecture:
    - ElasticsearchRetriever: ES kNN 벡터 + BM25 키워드 검색 래퍼
    - Neo4jRetriever: Neo4j 그래프 탐색 래퍼
    - HybridRetriever: 3-source 통합 + RRF Fusion (SearchService 위임)

Usage:
    RAG 워크플로우에서 HybridRetriever를 사용하여 검색을 수행합니다.
    REST API에서는 SearchService를 직접 사용합니다.
    둘 다 내부적으로 같은 검색 로직을 공유합니다.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional

from app.agents.state import SearchResult
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ElasticsearchRetriever:
    """
    Elasticsearch 검색 래퍼

    SearchService의 semantic_search 및 keyword_search를 위임하여
    ES kNN 벡터 검색과 BM25 키워드 검색을 수행합니다.

    Attributes:
        _search_service: SearchService 인스턴스 (지연 초기화)
    """

    def __init__(
        self,
        es_client: Optional[Any] = None,
        search_service: Optional[Any] = None,
    ):
        """
        초기화

        Args:
            es_client: Elasticsearch 클라이언트 (SearchService 생성 시 사용)
            search_service: 기존 SearchService 인스턴스 (직접 주입)
        """
        self._es_client = es_client
        self._search_service = search_service

    @property
    def search_service(self) -> Any:
        """SearchService 지연 초기화"""
        if self._search_service is None:
            from app.services.search import SearchService
            self._search_service = SearchService(es_client=self._es_client)
        return self._search_service

    async def search(
        self,
        query: str,
        top_k: int = 20,
        filters: Optional[Dict[str, Any]] = None,
        search_type: str = "vector",
    ) -> List[SearchResult]:
        """
        Elasticsearch 검색 수행

        Args:
            query: 검색 질의
            top_k: 반환할 결과 수
            filters: 필터 조건 딕셔너리
            search_type: 검색 유형 ('vector' 또는 'keyword')

        Returns:
            SearchResult 목록
        """
        try:
            if search_type == "keyword":
                result = await self.search_service.keyword_search(
                    query=query, filters=filters, top_k=top_k
                )
            else:
                result = await self.search_service.semantic_search(
                    query=query, filters=filters, top_k=top_k
                )

            results = result.get("results", [])
            logger.debug(
                "ES %s search - Query: '%s', Results: %d",
                search_type, query[:50], len(results),
            )
            return results

        except Exception as e:
            logger.warning("ES %s search failed: %s", search_type, e)
            return []

    async def vector_search(
        self,
        query: str,
        top_k: int = 20,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        벡터 유사도 검색 (kNN)

        Args:
            query: 검색 질의
            top_k: 반환할 결과 수
            filters: 필터 조건

        Returns:
            Vector Search 결과 목록
        """
        return await self.search(
            query=query, top_k=top_k, filters=filters, search_type="vector"
        )

    async def keyword_search(
        self,
        query: str,
        top_k: int = 20,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        키워드 검색 (BM25)

        Args:
            query: 검색 질의
            top_k: 반환할 결과 수
            filters: 필터 조건

        Returns:
            Keyword Search 결과 목록
        """
        return await self.search(
            query=query, top_k=top_k, filters=filters, search_type="keyword"
        )


class Neo4jRetriever:
    """
    Neo4j Graph 검색 래퍼

    SearchService의 _graph_search를 위임하여 Knowledge Graph 탐색을 수행합니다.

    Attributes:
        _search_service: SearchService 인스턴스 (지연 초기화)
    """

    def __init__(
        self,
        neo4j_driver: Optional[Any] = None,
        search_service: Optional[Any] = None,
    ):
        """
        초기화

        Args:
            neo4j_driver: Neo4j 드라이버 (SearchService 생성 시 사용)
            search_service: 기존 SearchService 인스턴스 (직접 주입)
        """
        self._neo4j_driver = neo4j_driver
        self._search_service = search_service

    @property
    def search_service(self) -> Any:
        """SearchService 지연 초기화"""
        if self._search_service is None:
            from app.services.search import SearchService
            self._search_service = SearchService(neo4j_driver=self._neo4j_driver)
        return self._search_service

    async def search(
        self,
        query: str,
        entities: Optional[List[Dict[str, Any]]] = None,
        top_k: int = 20,
    ) -> List[SearchResult]:
        """
        Graph 검색 수행

        엔티티 기반으로 Knowledge Graph를 탐색하여 관련 청크를 검색합니다.

        Args:
            query: 검색 질의
            entities: 추출된 엔티티 목록
            top_k: 반환할 결과 수

        Returns:
            Graph Search 결과 목록
        """
        try:
            results = await self.search_service._graph_search(
                query=query, entities=entities, top_k=top_k
            )
            logger.debug(
                "Graph search - Query: '%s', Entities: %d, Results: %d",
                query[:50],
                len(entities or []),
                len(results),
            )
            return results

        except Exception as e:
            logger.warning("Graph search failed: %s", e)
            return []


class HybridRetriever:
    """
    Hybrid Retriever

    Vector Search (Elasticsearch kNN + BM25)와 Graph Search (Neo4j Cypher)를
    병렬로 실행하고 RRF로 결과를 융합합니다.

    ADR-001 결정에 따라 SearchService에 위임하여 중복 로직을 제거합니다.
    - HybridRetriever: RAG 워크플로우 인터페이스
    - SearchService: REST API 인터페이스
    - 둘 다 동일한 검색/융합 로직 공유

    Attributes:
        _search_service: SearchService 인스턴스
        _es_retriever: Elasticsearch 검색 래퍼
        _neo4j_retriever: Neo4j 검색 래퍼
    """

    def __init__(
        self,
        es_client: Optional[Any] = None,
        neo4j_driver: Optional[Any] = None,
        search_service: Optional[Any] = None,
        reranker: Optional[Any] = None,
    ):
        """
        초기화

        SearchService 인스턴스를 직접 주입하거나, es_client/neo4j_driver로
        새 인스턴스를 생성합니다.

        Args:
            es_client: Elasticsearch 클라이언트
            neo4j_driver: Neo4j 드라이버
            search_service: 기존 SearchService 인스턴스 (직접 주입, 우선)
            reranker: BGEReranker 인스턴스 (STORY-032, None이면 리랭킹 비활성화)
        """
        self._es_client = es_client
        self._neo4j_driver = neo4j_driver
        self._injected_search_service = search_service
        self._search_service: Optional[Any] = None
        self._reranker = reranker

        # 개별 Retriever (SearchService 공유)
        self._es_retriever: Optional[ElasticsearchRetriever] = None
        self._neo4j_retriever: Optional[Neo4jRetriever] = None

    @property
    def search_service(self) -> Any:
        """SearchService 지연 초기화 (싱글톤)"""
        if self._search_service is None:
            if self._injected_search_service is not None:
                self._search_service = self._injected_search_service
            else:
                from app.services.search import SearchService
                self._search_service = SearchService(
                    es_client=self._es_client,
                    neo4j_driver=self._neo4j_driver,
                )
        return self._search_service

    @property
    def es_retriever(self) -> ElasticsearchRetriever:
        """ElasticsearchRetriever 지연 초기화"""
        if self._es_retriever is None:
            self._es_retriever = ElasticsearchRetriever(
                search_service=self.search_service
            )
        return self._es_retriever

    @property
    def neo4j_retriever(self) -> Neo4jRetriever:
        """Neo4jRetriever 지연 초기화"""
        if self._neo4j_retriever is None:
            self._neo4j_retriever = Neo4jRetriever(
                search_service=self.search_service
            )
        return self._neo4j_retriever

    async def retrieve(
        self,
        query: str,
        entities: Optional[List[Dict[str, Any]]] = None,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        use_reranking: bool = True,
    ) -> List[SearchResult]:
        """
        Hybrid 검색 수행

        SearchService.hybrid_search()에 위임하여 Vector + Keyword + Graph
        3-source 병렬 검색 후 RRF 융합 결과를 반환합니다.
        Reranker가 설정된 경우, RRF 융합 후 BGE Reranker로 재순위화합니다.

        Args:
            query: 검색 질의
            entities: 추출된 엔티티 목록 (Graph Search 활용)
            top_k: 반환할 결과 수
            filters: 필터 조건 딕셔너리
            user_id: 사용자 ID (이력 기록용)
            use_reranking: Reranker 사용 여부 (STORY-032)

        Returns:
            RRF 융합 (및 선택적 리랭킹) 검색 결과 목록 (상위 top_k개)
        """
        start_time = time.monotonic()

        # P0-2: Reranking 활성화 시 후보 수를 top_k*3 또는 최대 25건으로 제한 (50→25)
        fetch_k = min(top_k * 3, 25) if (use_reranking and self._reranker) else top_k

        logger.info(
            "Hybrid retrieval - Query: '%s', top_k=%d, fetch_k=%d, "
            "entities=%d, reranking=%s",
            query[:80], top_k, fetch_k, len(entities or []),
            use_reranking and self._reranker is not None,
        )

        try:
            # P0-1: SearchService에 위임하여 hybrid search 수행
            # skip_reranking=True로 SearchService 내부 reranking을 건너뛰고
            # HybridRetriever에서 자체 reranking만 수행 (이중 실행 방지)
            result = await self.search_service.hybrid_search(
                query=query,
                filters=filters,
                top_k=fetch_k,
                user_id=user_id,
                skip_reranking=True,
            )

            fused_results = result.get("results", [])
            debug_info = result.get("debug", {})

            # STORY-032: Reranking 적용
            # P0-2: 후보 수를 top_k*2 또는 최대 15건으로 제한 (50→15, CPU 추론 부하 경감)
            if (
                use_reranking
                and self._reranker is not None
                and len(fused_results) > top_k
            ):
                rerank_start = time.monotonic()
                rerank_candidate_count = min(len(fused_results), top_k * 2, 50)
                rerank_input_count = rerank_candidate_count
                before_max_score = max((r.score for r in fused_results), default=0.0)
                try:
                    fused_results = await self._reranker.rerank_search_results(
                        query=query,
                        search_results=fused_results[:rerank_candidate_count],
                        top_k=top_k,
                    )
                    rerank_ms = (time.monotonic() - rerank_start) * 1000
                    after_max_score = max((r.score for r in fused_results), default=0.0)
                    logger.info(
                        "Reranking applied - input=%d, output=%d, "
                        "before_max_score=%.4f, after_max_score=%.4f, "
                        "rerank_latency=%.1fms",
                        rerank_input_count,
                        len(fused_results),
                        before_max_score,
                        after_max_score,
                        rerank_ms,
                    )
                except Exception as rerank_err:
                    logger.warning(
                        "Reranking failed, using RRF results: %s", rerank_err
                    )
                    fused_results = fused_results[:top_k]
            else:
                if use_reranking and self._reranker is not None:
                    logger.debug(
                        "Reranking skipped - fused_results(%d) <= top_k(%d)",
                        len(fused_results), top_k,
                    )
                fused_results = fused_results[:top_k]

            latency_ms = (time.monotonic() - start_time) * 1000

            logger.info(
                "Hybrid retrieval complete - "
                "Vector: %d, Keyword: %d, Graph: %d, "
                "Fused: %d, Latency: %.1fms",
                debug_info.get("vector_count", 0),
                debug_info.get("keyword_count", 0),
                debug_info.get("graph_count", 0),
                len(fused_results),
                latency_ms,
            )

            return fused_results

        except Exception as e:
            latency_ms = (time.monotonic() - start_time) * 1000
            logger.error(
                "Hybrid retrieval failed (%.1fms): %s", latency_ms, e
            )
            # Fallback: 개별 Retriever로 부분 검색 시도
            return await self._fallback_retrieve(
                query=query, entities=entities, top_k=top_k, filters=filters
            )

    async def aretrieve(
        self,
        query: str,
        entities: Optional[List[Dict[str, Any]]] = None,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        use_reranking: bool = True,
    ) -> List[SearchResult]:
        """
        비동기 Hybrid 검색 (retrieve의 별칭)

        LangChain/LangGraph 호환성을 위한 비동기 인터페이스입니다.

        Args:
            query: 검색 질의
            entities: 추출된 엔티티 목록
            top_k: 반환할 결과 수
            filters: 필터 조건 딕셔너리
            user_id: 사용자 ID
            use_reranking: Reranker 사용 여부 (STORY-032)

        Returns:
            RRF 융합 (및 선택적 리랭킹) 검색 결과 목록
        """
        return await self.retrieve(
            query=query,
            entities=entities,
            top_k=top_k,
            filters=filters,
            user_id=user_id,
            use_reranking=use_reranking,
        )

    async def retrieve_by_source(
        self,
        query: str,
        source: str = "vector",
        entities: Optional[List[Dict[str, Any]]] = None,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        특정 소스로 검색

        Args:
            query: 검색 질의
            source: 검색 소스 ('vector', 'keyword', 'graph')
            entities: 추출된 엔티티 목록
            top_k: 반환할 결과 수
            filters: 필터 조건

        Returns:
            검색 결과 목록
        """
        if source == "graph":
            return await self.neo4j_retriever.search(
                query=query, entities=entities, top_k=top_k
            )
        elif source == "keyword":
            return await self.es_retriever.keyword_search(
                query=query, top_k=top_k, filters=filters
            )
        else:
            return await self.es_retriever.vector_search(
                query=query, top_k=top_k, filters=filters
            )

    async def _fallback_retrieve(
        self,
        query: str,
        entities: Optional[List[Dict[str, Any]]] = None,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        Fallback 검색: 개별 소스 병렬 검색 + RRF 융합

        hybrid_search 전체가 실패한 경우, 개별 Retriever로
        부분 검색을 시도하고 가용한 결과를 RRF 융합합니다.

        Args:
            query: 검색 질의
            entities: 추출된 엔티티 목록
            top_k: 반환할 결과 수
            filters: 필터 조건

        Returns:
            가용한 검색 결과 목록 (부분 결과 가능)
        """
        logger.warning("Falling back to individual source retrieval")

        # 병렬 검색 (return_exceptions로 부분 실패 허용)
        vector_task = self.es_retriever.vector_search(
            query=query, top_k=top_k * 2, filters=filters
        )
        keyword_task = self.es_retriever.keyword_search(
            query=query, top_k=top_k * 2, filters=filters
        )
        graph_task = self.neo4j_retriever.search(
            query=query, entities=entities, top_k=top_k * 2
        )

        results = await asyncio.gather(
            vector_task, keyword_task, graph_task,
            return_exceptions=True,
        )

        # 성공한 결과만 수집
        result_lists: List[List[SearchResult]] = []
        source_names: List[str] = []

        for i, (name, res) in enumerate(
            zip(["vector", "keyword", "graph"], results)
        ):
            if isinstance(res, Exception):
                logger.warning("Fallback %s search failed: %s", name, res)
            elif isinstance(res, list):
                result_lists.append(res)
                source_names.append(name)

        if not result_lists:
            logger.error("All fallback searches failed")
            return []

        # RRF 융합 (SearchService의 메서드 사용)
        fused = self.search_service._rrf_fusion(
            result_lists=result_lists,
            source_names=source_names,
            k=settings.rrf_k,
        )

        logger.info(
            "Fallback retrieval - Sources: %s, Fused: %d",
            source_names, len(fused),
        )

        return fused[:top_k]

    def health_check(self) -> Dict[str, Any]:
        """
        Retriever 상태 점검

        Returns:
            상태 정보 딕셔너리
        """
        health = {
            "service": "HybridRetriever",
            "es_client": self._es_client is not None or (
                self._injected_search_service is not None
                and getattr(self._injected_search_service, "es_client", None) is not None
            ),
            "neo4j_driver": self._neo4j_driver is not None or (
                self._injected_search_service is not None
                and getattr(self._injected_search_service, "neo4j_driver", None) is not None
            ),
            "search_service_initialized": self._search_service is not None,
            "rrf_k": settings.rrf_k,
            "retrieval_top_k": settings.retrieval_top_k,
            "reranker_enabled": self._reranker is not None,
        }

        # STORY-032: Reranker 상태 포함
        if self._reranker is not None and hasattr(self._reranker, "health_check"):
            health["reranker"] = self._reranker.health_check()

        return health


# ---------------------------------------------------------------------------
# Singleton instance
# ---------------------------------------------------------------------------

_retriever: Optional[HybridRetriever] = None


def get_hybrid_retriever(
    es_client: Optional[Any] = None,
    neo4j_driver: Optional[Any] = None,
    search_service: Optional[Any] = None,
    reranker: Optional[Any] = None,
) -> HybridRetriever:
    """
    HybridRetriever 인스턴스 반환 (싱글톤)

    Args:
        es_client: Elasticsearch 클라이언트
        neo4j_driver: Neo4j 드라이버
        search_service: SearchService 인스턴스
        reranker: BGEReranker 인스턴스 (STORY-032)

    Returns:
        HybridRetriever 싱글톤 인스턴스
    """
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever(
            es_client=es_client,
            neo4j_driver=neo4j_driver,
            search_service=search_service,
            reranker=reranker,
        )
    else:
        # SCRUM-103: 싱글톤에 reranker가 누락된 경우 업데이트
        if reranker is not None and _retriever._reranker is None:
            _retriever._reranker = reranker
            logger.info("HybridRetriever singleton updated with reranker")
    return _retriever


def reset_hybrid_retriever() -> None:
    """싱글톤 인스턴스 초기화 (테스트용)"""
    global _retriever
    _retriever = None
