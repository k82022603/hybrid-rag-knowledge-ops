"""
검색 서비스 모듈

Hybrid 검색 (Dense + Sparse + Graph) 통합 서비스
- Elasticsearch kNN Vector Search
- Elasticsearch BM25 Keyword Search
- Neo4j Graph Search
- RRF (Reciprocal Rank Fusion) 융합
- 검색 필터링 및 이력 관리
- 검색 결과 캐싱 (STORY-060)
"""

import asyncio
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.agents.state import SearchResult
from app.core.config import settings
from app.core.exceptions import ElasticsearchError, Neo4jError, SearchError
from app.core.logging import get_logger
from app.services.embedding import get_embedding_service

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Cache Integration (STORY-060)
# ---------------------------------------------------------------------------

def _get_cache_service():
    """캐시 서비스 lazy import (순환 참조 방지)"""
    if not settings.search_cache_enabled:
        return None
    try:
        from app.services.cache_service import get_cache_service
        return get_cache_service(
            ttl=settings.search_cache_ttl,
            max_size=settings.search_cache_max_size,
        )
    except Exception as e:
        logger.warning(f"Cache service unavailable: {e}")
        return None


# ---------------------------------------------------------------------------
# 검색 필터 모델
# ---------------------------------------------------------------------------

class SearchFilters:
    """검색 필터 조건"""

    def __init__(
        self,
        project_name: Optional[str] = None,
        document_type: Optional[str] = None,
        category: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        file_types: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ):
        self.project_name = project_name
        self.document_type = document_type
        self.category = category
        self.date_from = date_from
        self.date_to = date_to
        self.file_types = file_types or []
        self.tags = tags or []

    def to_es_filter(self) -> List[Dict[str, Any]]:
        """Elasticsearch filter 쿼리로 변환"""
        filters: List[Dict[str, Any]] = []

        if self.project_name:
            filters.append({"term": {"metadata.project_name": self.project_name}})

        if self.document_type:
            filters.append({"term": {"metadata.document_type": self.document_type}})

        if self.category:
            filters.append({"term": {"metadata.category": self.category}})

        if self.date_from or self.date_to:
            date_range: Dict[str, str] = {}
            if self.date_from:
                date_range["gte"] = self.date_from
            if self.date_to:
                date_range["lte"] = self.date_to
            filters.append({"range": {"metadata.created_at": date_range}})

        if self.file_types:
            filters.append({"terms": {"metadata.file_type": self.file_types}})

        if self.tags:
            filters.append({"terms": {"metadata.tags": self.tags}})

        return filters

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "SearchFilters":
        """딕셔너리에서 SearchFilters 생성"""
        if data is None:
            return cls()
        return cls(
            project_name=data.get("project_name"),
            document_type=data.get("document_type"),
            category=data.get("category"),
            date_from=data.get("date_from"),
            date_to=data.get("date_to"),
            file_types=data.get("file_types"),
            tags=data.get("tags"),
        )


# ---------------------------------------------------------------------------
# 검색 이력 저장소 (인메모리, 추후 PostgreSQL로 교체)
# ---------------------------------------------------------------------------

class SearchHistoryStore:
    """검색 이력 저장소 (인메모리 구현)"""

    def __init__(self, max_entries: int = 10000):
        self._history: List[Dict[str, Any]] = []
        self._max_entries = max_entries

    def record(
        self,
        query: str,
        search_type: str,
        result_count: int,
        latency_ms: float,
        user_id: Optional[str] = None,
    ) -> None:
        """검색 이력 기록"""
        entry = {
            "id": str(uuid4()),
            "query": query,
            "search_type": search_type,
            "result_count": result_count,
            "latency_ms": round(latency_ms, 2),
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._history.append(entry)

        # 최대 크기 초과 시 오래된 항목 제거
        if len(self._history) > self._max_entries:
            self._history = self._history[-self._max_entries:]

    def get_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        """최근 검색 이력 조회"""
        return list(reversed(self._history[-limit:]))


# ---------------------------------------------------------------------------
# SearchService
# ---------------------------------------------------------------------------

class SearchService:
    """
    통합 검색 서비스

    Hybrid Search (Vector + Keyword + Graph)를 제공하며,
    RRF 기반 결과 융합과 필터링을 수행합니다.

    Attributes:
        es_client: Elasticsearch 클라이언트 (Optional)
        neo4j_driver: Neo4j 드라이버 (Optional)
        history_store: 검색 이력 저장소
    """

    def __init__(
        self,
        es_client: Optional[Any] = None,
        neo4j_driver: Optional[Any] = None,
        cache_enabled: bool = True,
    ):
        """
        초기화

        Args:
            es_client: Elasticsearch 클라이언트 (None이면 연결 없이 동작)
            neo4j_driver: Neo4j 드라이버 (None이면 연결 없이 동작)
            cache_enabled: 캐시 활성화 여부 (STORY-060)
        """
        self.es_client = es_client
        self.neo4j_driver = neo4j_driver
        self.history_store = SearchHistoryStore()
        self._embedding_service = get_embedding_service()
        self._cache_enabled = cache_enabled and settings.search_cache_enabled
        self._cache = _get_cache_service() if self._cache_enabled else None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def hybrid_search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 10,
        user_id: Optional[str] = None,
        use_cache: bool = True,
        use_graph: bool = True,
        use_vector: bool = True,
    ) -> Dict[str, Any]:
        """
        Hybrid 검색 수행

        Vector Search, Keyword Search, Graph Search를 병렬로 실행하고
        RRF 알고리즘으로 결과를 융합합니다.

        STORY-060: 캐싱 적용으로 반복 쿼리 성능 향상

        Args:
            query: 검색 질의
            filters: 필터 조건 딕셔너리
            top_k: 반환할 결과 수
            user_id: 사용자 ID (이력 기록용)
            use_cache: 캐시 사용 여부 (기본 True)
            use_graph: Graph 검색 사용 여부 (기본 True)
            use_vector: Vector 검색 사용 여부 (기본 True)

        Returns:
            검색 결과 딕셔너리
            {
                "results": List[SearchResult],
                "total": int,
                "search_type": "hybrid",
                "latency_ms": float,
                "from_cache": bool,
                "debug": { ... }
            }

        Raises:
            SearchError: 검색 처리 실패
        """
        start_time = time.monotonic()
        search_filters = SearchFilters.from_dict(filters)
        from_cache = False

        logger.info(
            f"Hybrid search - Query: '{query[:80]}...', "
            f"top_k={top_k}, has_filters={filters is not None}, "
            f"use_vector={use_vector}, use_graph={use_graph}, "
            f"cache={use_cache and self._cache is not None}"
        )

        try:
            # STORY-060: 캐시 조회
            cache_key = None
            if use_cache and self._cache is not None:
                cache_key = self._cache.get_cache_key(
                    query=query,
                    filters=filters,
                    top_k=top_k,
                    search_type="hybrid",
                )
                cached_result = await self._cache.get(cache_key)
                if cached_result is not None:
                    # 캐시 히트 - SearchResult 객체로 복원
                    cached_results_data = cached_result.get("results", [])
                    results = [
                        SearchResult(
                            chunk_id=r.get("chunk_id", ""),
                            document_id=r.get("document_id", ""),
                            content=r.get("content", ""),
                            score=r.get("score", 0.0),
                            source=r.get("source", "cached"),
                            metadata=r.get("metadata", {}),
                        )
                        for r in cached_results_data
                    ]
                    latency_ms = (time.monotonic() - start_time) * 1000

                    # 검색 이력 기록 (캐시 히트)
                    self.history_store.record(
                        query=query,
                        search_type="hybrid_cached",
                        result_count=len(results),
                        latency_ms=latency_ms,
                        user_id=user_id,
                    )

                    logger.info(
                        f"Hybrid search CACHE HIT - "
                        f"Results: {len(results)}, "
                        f"Latency: {latency_ms:.1f}ms"
                    )

                    return {
                        "results": results,
                        "total": len(results),
                        "search_type": "hybrid",
                        "latency_ms": round(latency_ms, 2),
                        "from_cache": True,
                        "debug": cached_result.get("debug", {}),
                    }

            # 1. 병렬 검색 실행 (조건부: Vector + Keyword + Graph)
            tasks = []
            task_names = []

            # Vector/Semantic 검색 (use_vector=True 일 때)
            if use_vector:
                tasks.append(self.semantic_search(
                    query=query, filters=filters, top_k=top_k * 2
                ))
                task_names.append("vector")

            # Keyword 검색 (항상 실행 - BM25 기본)
            tasks.append(self.keyword_search(
                query=query, filters=filters, top_k=top_k * 2
            ))
            task_names.append("keyword")

            # Graph 검색 (use_graph=True 일 때)
            if use_graph:
                tasks.append(self._graph_search(
                    query=query, top_k=top_k * 2
                ))
                task_names.append("graph")

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 결과 매핑
            vector_results: List[SearchResult] = []
            keyword_results: List[SearchResult] = []
            graph_results: List[SearchResult] = []

            for i, task_name in enumerate(task_names):
                result = results[i]
                if task_name == "vector":
                    if isinstance(result, dict):
                        vector_results = result.get("results", [])
                    elif isinstance(result, Exception):
                        logger.warning(f"Vector search failed: {result}")
                elif task_name == "keyword":
                    if isinstance(result, dict):
                        keyword_results = result.get("results", [])
                    elif isinstance(result, Exception):
                        logger.warning(f"Keyword search failed: {result}")
                elif task_name == "graph":
                    if isinstance(result, list):
                        graph_results = result
                    elif isinstance(result, Exception):
                        logger.warning(f"Graph search failed: {result}")

            # 2. RRF 융합 (활성화된 소스만)
            result_lists = []
            source_names = []

            if use_vector and vector_results:
                result_lists.append(vector_results)
                source_names.append("vector")

            if keyword_results:
                result_lists.append(keyword_results)
                source_names.append("keyword")

            if use_graph and graph_results:
                result_lists.append(graph_results)
                source_names.append("graph")

            fused_results = self._rrf_fusion(
                result_lists=result_lists,
                source_names=source_names,
                k=settings.rrf_k,
            )

            # 3. 상위 top_k 반환
            final_results = fused_results[:top_k]

            latency_ms = (time.monotonic() - start_time) * 1000

            debug_info = {
                "vector_count": len(vector_results),
                "keyword_count": len(keyword_results),
                "graph_count": len(graph_results),
                "fused_count": len(fused_results),
            }

            # STORY-060: 캐시 저장
            if cache_key is not None and self._cache is not None:
                # SearchResult 객체를 직렬화 가능한 딕셔너리로 변환
                serializable_results = [
                    {
                        "chunk_id": r.chunk_id,
                        "document_id": r.document_id,
                        "content": r.content,
                        "score": r.score,
                        "source": r.source,
                        "metadata": r.metadata,
                    }
                    for r in final_results
                ]
                await self._cache.set(
                    key=cache_key,
                    value={
                        "results": serializable_results,
                        "total": len(final_results),
                        "debug": debug_info,
                    },
                )

            # 4. 검색 이력 기록
            self.history_store.record(
                query=query,
                search_type="hybrid",
                result_count=len(final_results),
                latency_ms=latency_ms,
                user_id=user_id,
            )

            logger.info(
                f"Hybrid search complete - "
                f"Vector: {len(vector_results)}, "
                f"Keyword: {len(keyword_results)}, "
                f"Graph: {len(graph_results)}, "
                f"Fused: {len(final_results)}, "
                f"Latency: {latency_ms:.1f}ms"
            )

            return {
                "results": final_results,
                "total": len(final_results),
                "search_type": "hybrid",
                "latency_ms": round(latency_ms, 2),
                "from_cache": False,
                "debug": debug_info,
            }

        except Exception as e:
            latency_ms = (time.monotonic() - start_time) * 1000
            logger.exception(f"Hybrid search failed: {e}")
            raise SearchError(
                message=f"Hybrid 검색 실패: {str(e)}",
                details={"query": query[:200], "latency_ms": round(latency_ms, 2)},
            )

    async def semantic_search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 10,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        시맨틱 벡터 검색

        BGE-M3 임베딩을 사용하여 Elasticsearch kNN 검색을 수행합니다.

        Args:
            query: 검색 질의
            filters: 필터 조건 딕셔너리
            top_k: 반환할 결과 수
            user_id: 사용자 ID (이력 기록용)

        Returns:
            검색 결과 딕셔너리

        Raises:
            ElasticsearchError: Elasticsearch 검색 실패
        """
        start_time = time.monotonic()
        search_filters = SearchFilters.from_dict(filters)

        logger.info(f"Semantic search - Query: '{query[:80]}...', top_k={top_k}")

        try:
            # 1. 쿼리 임베딩 생성
            query_vector = await self._embedding_service.aembed(query)

            results: List[SearchResult] = []

            if self.es_client is not None:
                # 2. Elasticsearch kNN 검색
                knn_query: Dict[str, Any] = {
                    "field": "embedding",
                    "query_vector": query_vector,  # EmbeddingService returns List[float]
                    "k": top_k,
                    "num_candidates": top_k * 10,
                }

                # 필터 적용
                es_filters = search_filters.to_es_filter()
                if es_filters:
                    knn_query["filter"] = {"bool": {"must": es_filters}}

                response = await self._es_search(
                    body={"knn": knn_query, "size": top_k},
                    index=settings.elasticsearch_index,
                )

                results = self._parse_es_results(response, source="vector")
            else:
                logger.debug("Elasticsearch client not available - returning empty results")

            latency_ms = (time.monotonic() - start_time) * 1000

            # 검색 이력 기록
            if user_id:
                self.history_store.record(
                    query=query,
                    search_type="semantic",
                    result_count=len(results),
                    latency_ms=latency_ms,
                    user_id=user_id,
                )

            logger.info(
                f"Semantic search complete - Results: {len(results)}, "
                f"Latency: {latency_ms:.1f}ms"
            )

            return {
                "results": results,
                "total": len(results),
                "search_type": "semantic",
                "latency_ms": round(latency_ms, 2),
            }

        except Exception as e:
            latency_ms = (time.monotonic() - start_time) * 1000
            logger.exception(f"Semantic search failed: {e}")
            raise ElasticsearchError(
                message=f"시맨틱 검색 실패: {str(e)}",
                details={"query": query[:200], "latency_ms": round(latency_ms, 2)},
            )

    async def keyword_search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 10,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        키워드 기반 BM25 검색

        Elasticsearch BM25 알고리즘을 사용한 텍스트 매칭 검색을 수행합니다.

        Args:
            query: 검색 질의
            filters: 필터 조건 딕셔너리
            top_k: 반환할 결과 수
            user_id: 사용자 ID (이력 기록용)

        Returns:
            검색 결과 딕셔너리

        Raises:
            ElasticsearchError: Elasticsearch 검색 실패
        """
        start_time = time.monotonic()
        search_filters = SearchFilters.from_dict(filters)

        logger.info(f"Keyword search - Query: '{query[:80]}...', top_k={top_k}")

        try:
            results: List[SearchResult] = []

            if self.es_client is not None:
                # BM25 검색 쿼리 구성
                must_query: Dict[str, Any] = {
                    "multi_match": {
                        "query": query,
                        "fields": [
                            "content^3",
                            "content.nori^2",
                            "metadata.title^2",
                            "metadata.summary",
                        ],
                        "type": "best_fields",
                        "fuzziness": "AUTO",
                    }
                }

                bool_query: Dict[str, Any] = {"must": [must_query]}

                # 필터 적용
                es_filters = search_filters.to_es_filter()
                if es_filters:
                    bool_query["filter"] = es_filters

                body: Dict[str, Any] = {
                    "query": {"bool": bool_query},
                    "size": top_k,
                    "highlight": {
                        "fields": {
                            "content": {
                                "fragment_size": 200,
                                "number_of_fragments": 3,
                            }
                        }
                    },
                }

                response = await self._es_search(
                    body=body,
                    index=settings.elasticsearch_index,
                )

                results = self._parse_es_results(response, source="keyword")
            else:
                logger.debug("Elasticsearch client not available - returning empty results")

            latency_ms = (time.monotonic() - start_time) * 1000

            if user_id:
                self.history_store.record(
                    query=query,
                    search_type="keyword",
                    result_count=len(results),
                    latency_ms=latency_ms,
                    user_id=user_id,
                )

            logger.info(
                f"Keyword search complete - Results: {len(results)}, "
                f"Latency: {latency_ms:.1f}ms"
            )

            return {
                "results": results,
                "total": len(results),
                "search_type": "keyword",
                "latency_ms": round(latency_ms, 2),
            }

        except Exception as e:
            latency_ms = (time.monotonic() - start_time) * 1000
            logger.exception(f"Keyword search failed: {e}")
            raise ElasticsearchError(
                message=f"키워드 검색 실패: {str(e)}",
                details={"query": query[:200], "latency_ms": round(latency_ms, 2)},
            )

    # ------------------------------------------------------------------
    # Internal methods
    # ------------------------------------------------------------------

    async def _graph_search(
        self,
        query: str,
        entities: Optional[List[Dict[str, Any]]] = None,
        top_k: int = 20,
    ) -> List[SearchResult]:
        """
        Neo4j Graph Search

        엔티티 기반으로 Knowledge Graph를 탐색하여 관련 청크를 검색합니다.

        Args:
            query: 검색 질의
            entities: 추출된 엔티티 목록
            top_k: 반환할 결과 수

        Returns:
            Graph Search 결과 목록
        """
        if self.neo4j_driver is None:
            logger.debug("Neo4j driver not available - returning empty results")
            return []

        try:
            # Neo4j Cypher 기반 검색
            entity_names = [e.get("name", "") for e in (entities or [])]

            # 엔티티가 있으면 엔티티 기반 검색
            if entity_names:
                cypher = """
                MATCH (e:Entity)-[:MENTIONED_IN]->(c:Chunk)-[:BELONGS_TO]->(d:Document)
                WHERE e.name IN $entity_names
                WITH c, d, count(e) AS entity_match_count
                ORDER BY entity_match_count DESC
                LIMIT $top_k
                RETURN c.id AS chunk_id, c.content AS content,
                       d.id AS document_id, d.title AS title,
                       entity_match_count AS score
                """
                params = {"entity_names": entity_names, "top_k": top_k}
            else:
                # 키워드 기반 전문 검색 (fulltext index)
                cypher = """
                CALL db.index.fulltext.queryNodes('chunk_content', $query)
                YIELD node AS c, score
                MATCH (c)-[:BELONGS_TO]->(d:Document)
                RETURN c.id AS chunk_id, c.content AS content,
                       d.id AS document_id, d.title AS title,
                       score
                ORDER BY score DESC
                LIMIT $top_k
                """
                params = {"query": query, "top_k": top_k}

            records = await self._neo4j_query(cypher, params)

            results = [
                SearchResult(
                    chunk_id=str(record.get("chunk_id", str(uuid4()))),
                    document_id=str(record.get("document_id", "")),
                    content=str(record.get("content", "")),
                    score=float(record.get("score", 0.0)),
                    source="graph",
                    metadata={
                        "title": record.get("title", ""),
                        "search_source": "neo4j_graph",
                    },
                )
                for record in records
            ]

            logger.info(f"Graph search complete - Results: {len(results)}")
            return results

        except Exception as e:
            logger.warning(f"Graph search failed (non-critical): {e}")
            return []

    def _rrf_fusion(
        self,
        result_lists: List[List[SearchResult]],
        source_names: Optional[List[str]] = None,
        k: int = 60,
    ) -> List[SearchResult]:
        """
        RRF (Reciprocal Rank Fusion) 융합

        여러 검색 소스의 결과를 RRF 알고리즘으로 융합합니다.
        score = sum(1 / (k + rank_i)) for each source i

        Args:
            result_lists: 각 소스의 검색 결과 리스트
            source_names: 소스 이름 리스트 (디버깅용)
            k: RRF 파라미터 (기본값 60, 높을수록 하위 순위 영향 감소)

        Returns:
            RRF 점수 기준 정렬된 통합 결과 리스트
        """
        scores: Dict[str, float] = {}
        results_map: Dict[str, SearchResult] = {}
        source_ranks: Dict[str, Dict[str, int]] = {}  # chunk_id -> {source: rank}

        names = source_names or [f"source_{i}" for i in range(len(result_lists))]

        for source_idx, result_list in enumerate(result_lists):
            source_name = names[source_idx] if source_idx < len(names) else f"source_{source_idx}"

            for rank, result in enumerate(result_list):
                chunk_id = result.chunk_id
                rrf_score = 1.0 / (k + rank + 1)

                scores[chunk_id] = scores.get(chunk_id, 0.0) + rrf_score

                if chunk_id not in results_map:
                    results_map[chunk_id] = result

                # 소스별 순위 기록
                if chunk_id not in source_ranks:
                    source_ranks[chunk_id] = {}
                source_ranks[chunk_id][source_name] = rank + 1

        # 점수 기준 정렬
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        fused_results: List[SearchResult] = []
        for chunk_id in sorted_ids:
            result = results_map[chunk_id]
            # RRF 점수로 업데이트
            result.score = round(scores[chunk_id], 6)
            result.metadata["rrf_score"] = result.score
            result.metadata["source_ranks"] = source_ranks.get(chunk_id, {})
            fused_results.append(result)

        logger.debug(
            f"RRF fusion - Input sources: {len(result_lists)}, "
            f"Unique results: {len(fused_results)}"
        )

        return fused_results

    async def _es_search(
        self,
        body: Dict[str, Any],
        index: str,
    ) -> Dict[str, Any]:
        """
        Elasticsearch 검색 실행

        Args:
            body: 검색 쿼리 본문
            index: 인덱스명

        Returns:
            Elasticsearch 응답

        Raises:
            ElasticsearchError: 검색 실패
        """
        if self.es_client is None:
            return {"hits": {"hits": [], "total": {"value": 0}}}

        try:
            # Elasticsearch 비동기 검색
            if hasattr(self.es_client, "search"):
                response = await self.es_client.search(index=index, body=body)
                return response
            else:
                logger.warning("ES client does not support search method")
                return {"hits": {"hits": [], "total": {"value": 0}}}

        except Exception as e:
            raise ElasticsearchError(
                message=f"Elasticsearch 검색 실패: {str(e)}",
                details={"index": index},
            )

    async def _neo4j_query(
        self,
        cypher: str,
        params: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Neo4j Cypher 쿼리 실행

        Args:
            cypher: Cypher 쿼리
            params: 파라미터

        Returns:
            쿼리 결과 레코드 리스트

        Raises:
            Neo4jError: 쿼리 실패
        """
        if self.neo4j_driver is None:
            return []

        try:
            async with self.neo4j_driver.session() as session:
                result = await session.run(cypher, params)
                records = [dict(record) async for record in result]
                return records

        except Exception as e:
            raise Neo4jError(
                message=f"Neo4j 쿼리 실패: {str(e)}",
                details={"cypher": cypher[:200]},
            )

    def _parse_es_results(
        self,
        response: Dict[str, Any],
        source: str = "vector",
    ) -> List[SearchResult]:
        """
        Elasticsearch 응답을 SearchResult 리스트로 변환

        Args:
            response: Elasticsearch 응답
            source: 검색 소스 식별자

        Returns:
            SearchResult 리스트
        """
        results: List[SearchResult] = []
        hits = response.get("hits", {}).get("hits", [])

        for hit in hits:
            src = hit.get("_source", {})
            metadata = src.get("metadata", {})
            metadata["search_source"] = source

            # 하이라이트 결과 포함
            highlight = hit.get("highlight", {})
            if highlight:
                metadata["highlight"] = highlight

            result = SearchResult(
                chunk_id=hit.get("_id", str(uuid4())),
                document_id=str(metadata.get("document_id", "")),
                content=src.get("content", ""),
                score=float(hit.get("_score", 0.0)),
                source=source,
                metadata=metadata,
            )
            results.append(result)

        return results


# ---------------------------------------------------------------------------
# 싱글톤 인스턴스
# ---------------------------------------------------------------------------

_search_service: Optional[SearchService] = None


def init_search_service(
    es_client: Optional[Any] = None,
    neo4j_driver: Optional[Any] = None,
) -> SearchService:
    """SearchService 싱글톤 초기화 (lifespan에서 호출)

    Args:
        es_client: Elasticsearch AsyncElasticsearch 클라이언트
        neo4j_driver: Neo4j AsyncGraphDatabase 드라이버

    Returns:
        초기화된 SearchService 인스턴스
    """
    global _search_service
    _search_service = SearchService(
        es_client=es_client,
        neo4j_driver=neo4j_driver,
    )
    logger.info(
        f"SearchService initialized - "
        f"ES: {'connected' if es_client else 'none'}, "
        f"Neo4j: {'connected' if neo4j_driver else 'none'}"
    )
    return _search_service


def get_search_service() -> SearchService:
    """SearchService 인스턴스 반환 (싱글톤)

    init_search_service()로 초기화되지 않은 경우 기본값으로 생성합니다.
    """
    global _search_service
    if _search_service is None:
        logger.warning("SearchService not initialized via init_search_service() - creating with defaults")
        _search_service = SearchService()
    return _search_service
