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
import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from app.agents.state import SearchResult
from app.core.config import settings
from app.core.exceptions import ElasticsearchError, Neo4jError, SearchError
from app.core.logging import get_logger
from app.rag.bge_reranker import get_reranker
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
                    use_graph=use_graph,
                    use_vector=use_vector,
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
                            has_embedding=r.get("has_embedding"),
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

            # 0. Dense + Sparse 임베딩 동시 생성 (1회 모델 호출)
            query_dense: Optional[List[float]] = None
            query_sparse: Optional[Dict[str, float]] = None

            if use_vector or settings.sparse_search_enabled:
                try:
                    dense_list, sparse_list = await self._embedding_service.aembed_batch(
                        [query], return_sparse=True
                    )
                    query_dense = dense_list[0] if dense_list else None
                    query_sparse = sparse_list[0] if sparse_list else None
                except Exception as e:
                    logger.warning(f"Dense+Sparse embedding failed: {e}")

            # 1. 병렬 검색 실행 (조건부: Vector + Keyword + Graph)
            tasks = []
            task_names = []

            # Vector/Semantic 검색 (use_vector=True 일 때)
            if use_vector:
                tasks.append(self.semantic_search(
                    query=query, filters=filters, top_k=top_k * 2,
                    query_vector=query_dense,
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

            # 1.5 Sparse 검색 (2-Phase: 후보 청크의 stored sparse로 dot-product)
            sparse_results: List[SearchResult] = []
            if settings.sparse_search_enabled and query_sparse and self.es_client:
                # 후보 chunk_ids 수집 (vector + keyword 결과의 합집합)
                candidate_ids = set()
                candidate_map: Dict[str, SearchResult] = {}
                for r in vector_results + keyword_results:
                    candidate_ids.add(r.chunk_id)
                    if r.chunk_id not in candidate_map:
                        candidate_map[r.chunk_id] = r

                if candidate_ids:
                    try:
                        sparse_results = await self._sparse_search(
                            query_sparse=query_sparse,
                            candidate_ids=list(candidate_ids),
                            candidate_map=candidate_map,
                        )
                    except Exception as e:
                        logger.warning(f"Sparse search failed: {e}")

            # 2. RRF 융합 (활성화된 소스만, 채널별 가중치 적용)
            result_lists = []
            source_names = []
            source_weights = []

            if use_vector and vector_results:
                result_lists.append(vector_results)
                source_names.append("vector")
                source_weights.append(settings.rrf_weight_vector)

            if keyword_results:
                result_lists.append(keyword_results)
                source_names.append("keyword")
                source_weights.append(settings.rrf_weight_keyword)

            if sparse_results:
                result_lists.append(sparse_results)
                source_names.append("sparse")
                source_weights.append(settings.rrf_weight_sparse)

            if use_graph and graph_results:
                result_lists.append(graph_results)
                source_names.append("graph")
                source_weights.append(settings.rrf_weight_graph)

            fused_results = self._rrf_fusion(
                result_lists=result_lists,
                source_names=source_names,
                weights=source_weights,
                k=settings.rrf_k,
            )

            # 2.5 Reranker 적용 (Post-RRF, STORY-032)
            # RRF 융합 결과를 BGE Reranker로 재순위화하여 Context Precision 개선
            reranker_used = False
            try:
                reranker = get_reranker()
                if not reranker.is_loaded:
                    await reranker.load_model()
                rerank_candidates = fused_results[:top_k * 2]  # 상위 2배를 rerank 대상
                reranked = await reranker.arerank_with_timeout(
                    query=query,
                    documents=[
                        {
                            "doc_id": r.chunk_id,
                            "content": r.content,
                            "score": r.score,
                            "metadata": r.metadata,
                        }
                        for r in rerank_candidates
                    ],
                    top_k=top_k,
                    timeout=30.0,
                )
                # rerank 결과를 SearchResult로 매핑
                result_map = {r.chunk_id: r for r in rerank_candidates}
                reranked_results: List[SearchResult] = []
                for rr in reranked:
                    original = result_map.get(rr.doc_id)
                    if original is not None:
                        original.metadata["rerank_score"] = round(rr.score, 6)
                        original.metadata["original_rrf_score"] = original.score
                        original.score = round(rr.score, 6)
                        reranked_results.append(original)
                fused_results = reranked_results if reranked_results else fused_results
                reranker_used = bool(reranked_results)
                if reranker_used:
                    logger.info(
                        f"Reranker applied - top_score={reranked[0].score:.4f}, "
                        f"candidates={len(rerank_candidates)}, output={len(reranked_results)}"
                    )
            except Exception as e:
                logger.warning(f"Reranker failed (non-critical, using RRF order): {e}")

            # 2.6 청크별 Neo4j 엔티티 직접 조회 (Phase 2)
            # post-RRF 결과의 chunk_id로 Neo4j MENTIONS 관계를 직접 조회하여
            # 각 청크에 실제 연결된 엔티티만 할당 (글로벌 엔티티 리스트 제거)
            # 3. 상위 top_k 반환
            final_results = fused_results[:top_k]

            if use_graph:
                chunk_ids = [
                    r.metadata.get("chunk_id") or r.chunk_id
                    for r in final_results
                    if r.metadata.get("chunk_id") or r.chunk_id
                ]
                if chunk_ids:
                    chunk_entity_map = await self._get_chunk_entities(chunk_ids)
                    for r in final_results:
                        cid = r.metadata.get("chunk_id") or r.chunk_id
                        if cid and cid in chunk_entity_map:
                            r.metadata["matched_entities"] = chunk_entity_map[cid]
                        # chunk_id가 없거나 엔티티가 없으면 matched_entities 미할당 → Graph 버튼 미표시

            latency_ms = (time.monotonic() - start_time) * 1000

            debug_info = {
                "vector_count": len(vector_results),
                "keyword_count": len(keyword_results),
                "sparse_count": len(sparse_results),
                "graph_count": len(graph_results),
                "fused_count": len(fused_results),
                "reranker_used": reranker_used,
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
                        "has_embedding": r.has_embedding,
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
                f"Sparse: {len(sparse_results)}, "
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
        query_vector: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """
        시맨틱 벡터 검색

        BGE-M3 임베딩을 사용하여 Elasticsearch kNN 검색을 수행합니다.

        Args:
            query: 검색 질의
            filters: 필터 조건 딕셔너리
            top_k: 반환할 결과 수
            user_id: 사용자 ID (이력 기록용)
            query_vector: 사전 계산된 Dense 벡터 (None이면 내부 생성)

        Returns:
            검색 결과 딕셔너리

        Raises:
            ElasticsearchError: Elasticsearch 검색 실패
        """
        start_time = time.monotonic()
        search_filters = SearchFilters.from_dict(filters)

        logger.info(f"Semantic search - Query: '{query[:80]}...', top_k={top_k}")

        try:
            # 1. 쿼리 임베딩 생성 (사전 계산된 벡터가 없으면 생성)
            if query_vector is None:
                query_vector = await self._embedding_service.aembed(query)

            results: List[SearchResult] = []

            if self.es_client is not None:
                # 2. Elasticsearch kNN 검색
                knn_query: Dict[str, Any] = {
                    "field": "dense_vector",
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
                            "text^3",
                            "heading^2",
                            "metadata.title^2",
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
                            "text": {
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

    async def _get_chunk_entities(self, chunk_ids: List[str]) -> Dict[str, List[str]]:
        """각 청크의 고유 엔티티를 Neo4j에서 직접 조회 (Phase 2)

        post-RRF 결과의 chunk_id로 Neo4j MENTIONS 관계를 조회하여
        각 청크에 실제 연결된 엔티티만 반환합니다.

        Args:
            chunk_ids: 조회할 청크 ID 리스트

        Returns:
            {chunk_id: [entity_name, ...]} 매핑
        """
        cypher = """
        UNWIND $chunk_ids AS cid
        MATCH (c:Chunk {id: cid})-[:MENTIONS]->(e:Entity)
        WHERE NOT e.name STARTS WITH '/' AND NOT e.name STARTS WITH '.'
          AND size(e.name) >= 2
          AND NOT e.name CONTAINS '.py' AND NOT e.name CONTAINS '.ts'
          AND NOT e.name CONTAINS '.js' AND NOT e.name CONTAINS '.json'
          AND NOT e.name CONTAINS '//' AND NOT e.name CONTAINS '()'
          AND NOT e.name CONTAINS '{}' AND NOT e.name CONTAINS '*'
        RETURN cid, collect(DISTINCT e.name)[0..5] AS entities
        """
        try:
            records = await self._neo4j_query(cypher, {"chunk_ids": chunk_ids})
            return {
                str(r.get("cid", "")): r.get("entities", [])
                for r in records
                if r.get("entities")
            }
        except Exception as e:
            logger.warning(f"Chunk entity lookup failed: {e}")
            return {}

    async def _sparse_search(
        self,
        query_sparse: Dict[str, float],
        candidate_ids: List[str],
        candidate_map: Dict[str, "SearchResult"],
    ) -> List["SearchResult"]:
        """Application-level Sparse 검색 (2-Phase, ADR-002)

        ES kNN+BM25로 선별한 후보 청크에 대해 저장된 sparse_vector_json을
        파싱하여 query sparse 벡터와 dot-product 스코어를 계산합니다.

        Args:
            query_sparse: 쿼리의 Sparse 벡터 {token: weight}
            candidate_ids: 후보 청크 ID 리스트
            candidate_map: chunk_id -> SearchResult 매핑

        Returns:
            Sparse 점수 기준 내림차순 정렬된 SearchResult 리스트
        """
        if not candidate_ids or not query_sparse:
            return []

        start_time = time.monotonic()

        # 쿼리 sparse 프루닝 (top_tokens + min_weight)
        pruned_query = {
            token: weight
            for token, weight in query_sparse.items()
            if weight >= settings.sparse_min_weight
        }
        if pruned_query:
            sorted_tokens = sorted(
                pruned_query.items(), key=lambda x: x[1], reverse=True
            )
            pruned_query = dict(sorted_tokens[: settings.sparse_top_tokens])

        if not pruned_query:
            return []

        # ES mget으로 후보 청크의 sparse_vector_json 조회
        try:
            mget_body = {"ids": candidate_ids}
            response = await self.es_client.mget(
                index=settings.elasticsearch_index,
                body=mget_body,
                _source=["sparse_vector_json"],
            )
        except Exception as e:
            logger.warning(f"Sparse mget failed: {e}")
            return []

        # Dot-product 스코어 계산
        scored: List[Tuple[str, float]] = []
        for doc in response.get("docs", []):
            if not doc.get("found"):
                continue
            chunk_id = doc["_id"]
            source = doc.get("_source", {})
            sparse_json_str = source.get("sparse_vector_json")
            if not sparse_json_str:
                continue
            try:
                doc_sparse = json.loads(sparse_json_str)
            except (json.JSONDecodeError, TypeError):
                continue

            # dot-product: query_sparse · doc_sparse
            score = sum(
                pruned_query.get(token, 0.0) * weight
                for token, weight in doc_sparse.items()
            )
            if score > 0:
                scored.append((chunk_id, score))

        # 스코어 기준 정렬
        scored.sort(key=lambda x: x[1], reverse=True)

        # SearchResult 리스트 생성
        sparse_results: List[SearchResult] = []
        for chunk_id, score in scored:
            if chunk_id in candidate_map:
                original = candidate_map[chunk_id]
                sparse_result = SearchResult(
                    chunk_id=original.chunk_id,
                    document_id=original.document_id,
                    content=original.content,
                    score=score,
                    source="sparse",
                    metadata={**original.metadata, "search_source": "sparse"},
                    has_embedding=original.has_embedding,
                )
                sparse_results.append(sparse_result)

        elapsed_ms = (time.monotonic() - start_time) * 1000
        logger.info(
            f"Sparse search - candidates={len(candidate_ids)}, "
            f"scored={len(scored)}, query_tokens={len(pruned_query)}, "
            f"latency={elapsed_ms:.1f}ms"
        )

        return sparse_results

    async def _graph_search(
        self,
        query: str,
        entities: Optional[List[Dict[str, Any]]] = None,
        top_k: int = 20,
    ) -> List[SearchResult]:
        """
        Neo4j Graph Search (Entity-Enhanced BM25)

        Knowledge Graph에서 쿼리 관련 엔티티를 추출한 뒤, 엔티티명으로
        ES를 검색합니다. 이 방식으로 chunk_id가 Vector/Keyword와 겹쳐
        RRF 부스트가 가능합니다.

        전략:
        1. Neo4j에서 쿼리와 관련된 엔티티 매칭 + RELATED 1-hop 확장
        2. 상위 엔티티명을 expanded query로 구성
        3. ES에서 expanded query로 BM25 검색
        → chunk_id가 Vector/Keyword 결과와 동일하여 RRF 융합 시 부스트
        → Graph 고유 문서도 entity context 포함하여 반환

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
            entity_names = [e.get("name", "") for e in (entities or [])]

            # Step 1: Neo4j에서 관련 엔티티 추출
            if entity_names:
                cypher = """
                MATCH (e:Entity)
                WHERE e.name IN $entity_names
                OPTIONAL MATCH (e)-[:RELATED]-(related:Entity)
                WHERE related.name IS NOT NULL AND related.name <> 'None'
                WITH collect(DISTINCT e.name) + collect(DISTINCT related.name) AS all_names
                UNWIND all_names AS name
                WITH DISTINCT name
                WHERE name IS NOT NULL AND name <> 'None' AND size(name) >= 2
                RETURN name
                LIMIT 20
                """
                params: Dict[str, Any] = {"entity_names": entity_names}
            else:
                query_lower = query.lower()
                # 한국어 조사 + 구두점 제거 후 query_words 생성
                import re as _re
                _punct = _re.compile(r'[?!.。,;:]+$')
                _particles = _re.compile(r'[은는이가을를의와과에서로도만으로부터까지에게]+$')
                raw_words = [w for w in query.split() if len(w) >= 2]
                query_words = []
                for w in raw_words:
                    cleaned = _punct.sub('', w)
                    stripped = _particles.sub('', cleaned)
                    if stripped and len(stripped) >= 2 and stripped not in query_words:
                        query_words.append(stripped)
                    if cleaned and len(cleaned) >= 2 and cleaned not in query_words:
                        query_words.append(cleaned)
                if not query_words:
                    query_words = [query]

                # 2단계 Cypher: 정확 매칭 우선 + 부분 매칭 보조
                _ef = (
                    "e.name IS NOT NULL AND size(e.name) >= 2"
                    " AND NOT e.name STARTS WITH '/'"
                    " AND NOT e.name STARTS WITH '.'"
                    " AND NOT e.name CONTAINS '.py' AND NOT e.name CONTAINS '.ts'"
                    " AND NOT e.name CONTAINS '.js' AND NOT e.name CONTAINS '.json'"
                    " AND NOT e.name CONTAINS '.md' AND NOT e.name CONTAINS '.yml'"
                    " AND NOT e.name CONTAINS '.yaml'"
                    " AND NOT e.name CONTAINS '//'"
                    " AND NOT e.name CONTAINS '()' AND NOT e.name CONTAINS '{}'"
                    " AND NOT e.name CONTAINS '*'"
                )
                cypher = f"""
                MATCH (e:Entity) WHERE {_ef}
                AND any(word IN $query_words WHERE toLower(word) = toLower(e.name))
                WITH collect(DISTINCT e) AS exact

                OPTIONAL MATCH (e2:Entity)
                WHERE {_ef.replace('e.name', 'e2.name')}
                AND any(word IN $query_words WHERE
                    toLower(e2.name) CONTAINS toLower(word) AND size(word) >= 2)
                AND NOT any(word IN $query_words WHERE toLower(word) = toLower(e2.name))
                WITH exact, collect(DISTINCT e2)[0..15] AS partial

                WITH exact + partial AS all_e
                UNWIND all_e AS e
                WITH DISTINCT e LIMIT 20

                OPTIONAL MATCH (e)-[r:RELATED]-(rel:Entity)
                WHERE rel.name IS NOT NULL AND rel.name <> 'None'
                  AND NOT rel.name STARTS WITH '/' AND NOT rel.name STARTS WITH '.'
                  AND size(rel.name) >= 2
                WITH e, rel, COALESCE(r.weight, 1.0) AS w
                ORDER BY w DESC
                WITH e, collect(rel.name)[0..3] AS rn
                WITH collect(e.name) + reduce(a=[], n IN collect(rn) | a + n) AS names
                UNWIND names AS name
                WITH DISTINCT name
                WHERE name IS NOT NULL AND name <> 'None' AND size(name) >= 2
                  AND NOT name STARTS WITH '/' AND NOT name STARTS WITH '.'
                RETURN name LIMIT 20
                """
                params = {
                    "query_str": query_lower,
                    "query_words": query_words,
                }

            entity_records = await self._neo4j_query(cypher, params)

            if not entity_records:
                logger.info("Graph search: no matching entities found")
                return []

            # Step 2: 엔티티명으로 enhanced query 구성
            # 경로/코드/파일 패턴 필터 (Neo4j에 잘못 저장된 엔티티 제외)
            _junk_patterns = ('/', '//', '()', '{}', '*', '.py', '.ts', '.js', '.json', '.md', '.yml', '.yaml')
            graph_entities = [
                str(r.get("name", ""))
                for r in entity_records
                if r.get("name")
                and not str(r.get("name", "")).startswith(("/", "."))
                and not any(p in str(r.get("name", "")) for p in _junk_patterns)
            ]

            logger.debug(
                f"Graph search - Entities: {graph_entities[:5]}"
            )

            # Step 3: keyword search와 동일한 multi_match + 엔티티 부스트
            # must: keyword search와 동일한 multi_match 쿼리 (동일한 청크 풀)
            # should: 엔티티명으로 부스트 (entity 관련 청크 우선)
            # → keyword와 동일 chunk_id를 찾아 RRF에서 부스트
            results: List[SearchResult] = []

            if self.es_client is not None:
                should_clauses = [
                    {"match": {"text": {"query": ent, "boost": 1.5}}}
                    for ent in graph_entities[:10]
                ]

                es_query: Dict[str, Any] = {
                    "bool": {
                        "must": [
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": [
                                        "text^3",
                                        "heading^2",
                                        "metadata.title^2",
                                    ],
                                    "type": "best_fields",
                                    "fuzziness": "AUTO",
                                }
                            },
                        ],
                        "should": should_clauses,
                    }
                }

                response = await self._es_search(
                    body={"query": es_query, "size": top_k},
                    index=settings.elasticsearch_index,
                )

                # _parse_es_results로 파싱 (keyword와 동일한 chunk_id 생성)
                results = self._parse_es_results(response, source="graph")
                # Phase 2: matched_entities는 post-RRF에서 Neo4j MENTIONS 직접 조회로 할당
                # _graph_search에서는 ES 검색 결과만 반환

            # Debug: 매칭 통계
            matched_count = sum(1 for r in results if r.metadata.get("matched_entities"))
            logger.info(
                f"Graph search complete - "
                f"Entities: {len(graph_entities)}, Results: {len(results)}, "
                f"WithMatchedEntities: {matched_count}, "
                f"AllEntities: {graph_entities}"
            )
            return results

        except Exception as e:
            logger.warning(f"Graph search failed (non-critical): {e}")
            return []

    def _rrf_fusion(
        self,
        result_lists: List[List[SearchResult]],
        source_names: Optional[List[str]] = None,
        weights: Optional[List[float]] = None,
        k: int = 60,
    ) -> List[SearchResult]:
        """
        RRF (Reciprocal Rank Fusion) 융합

        여러 검색 소스의 결과를 RRF 알고리즘으로 융합합니다.
        score = sum(weight_i / (k + rank_i)) for each source i

        Args:
            result_lists: 각 소스의 검색 결과 리스트
            source_names: 소스 이름 리스트 (디버깅용)
            weights: 소스별 가중치 리스트 (None이면 모두 1.0)
            k: RRF 파라미터 (기본값 60, 높을수록 하위 순위 영향 감소)

        Returns:
            RRF 점수 기준 정렬된 통합 결과 리스트
        """
        scores: Dict[str, float] = {}
        results_map: Dict[str, SearchResult] = {}
        source_ranks: Dict[str, Dict[str, int]] = {}  # chunk_id -> {source: rank}

        names = source_names or [f"source_{i}" for i in range(len(result_lists))]
        effective_weights = weights or [1.0] * len(result_lists)

        for source_idx, result_list in enumerate(result_lists):
            source_name = names[source_idx] if source_idx < len(names) else f"source_{source_idx}"
            weight = effective_weights[source_idx] if source_idx < len(effective_weights) else 1.0

            for rank, result in enumerate(result_list):
                chunk_id = result.chunk_id
                rrf_score = weight * (1.0 / (k + rank + 1))

                scores[chunk_id] = scores.get(chunk_id, 0.0) + rrf_score

                if chunk_id not in results_map:
                    results_map[chunk_id] = result
                else:
                    # ISSUE-011: 중복 chunk에서 graph 소스의 matched_entities 머지
                    # vector 결과가 먼저 저장되면 graph의 matched_entities가 유실되므로
                    # 나중에 등장하는 소스에 matched_entities가 있으면 기존 결과에 병합
                    existing = results_map[chunk_id]
                    new_entities = result.metadata.get("matched_entities", [])
                    if new_entities and not existing.metadata.get("matched_entities"):
                        existing.metadata["matched_entities"] = new_entities

                # 소스별 순위 기록
                if chunk_id not in source_ranks:
                    source_ranks[chunk_id] = {}
                source_ranks[chunk_id][source_name] = rank + 1

        # 점수 기준 정렬
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        # 소스별 가중치 점수 추적용
        source_weighted_scores: Dict[str, Dict[str, float]] = {}
        for source_idx, result_list in enumerate(result_lists):
            source_name = names[source_idx] if source_idx < len(names) else f"source_{source_idx}"
            w = effective_weights[source_idx] if source_idx < len(effective_weights) else 1.0
            for rank, result in enumerate(result_list):
                cid = result.chunk_id
                if cid not in source_weighted_scores:
                    source_weighted_scores[cid] = {}
                source_weighted_scores[cid][source_name] = w * (1.0 / (k + rank + 1))

        fused_results: List[SearchResult] = []
        for chunk_id in sorted_ids:
            result = results_map[chunk_id]
            # RRF 점수로 업데이트
            result.score = round(scores[chunk_id], 6)
            result.metadata["rrf_score"] = result.score
            ranks = source_ranks.get(chunk_id, {})
            result.metadata["source_ranks"] = ranks

            # Primary source: 가중치 적용된 RRF 점수가 가장 높은 소스로 결정
            chunk_src_scores = source_weighted_scores.get(chunk_id, {})
            if chunk_src_scores:
                primary_source = max(chunk_src_scores, key=chunk_src_scores.get)
                result.source = primary_source
                result.metadata["search_source"] = primary_source
                result.metadata["source_scores"] = {
                    s: round(v, 6) for s, v in chunk_src_scores.items()
                }
                # SCRUM-101: 기여한 전체 소스 목록 추적 (graph 태깅용)
                result.metadata["contributing_sources"] = list(chunk_src_scores.keys())

            fused_results.append(result)

        logger.debug(
            f"RRF fusion - Input sources: {len(result_lists)}, "
            f"Unique results: {len(fused_results)}, "
            f"weights: {dict(zip(names, effective_weights))}"
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

            # ES 문서의 content 필드명은 "text"(ElasticsearchStorageService 경유)
            # 또는 "content"(InitialDataLoader 직접 인덱싱) 두 가지가 공존.
            # 둘 다 확인하여 누락 방지.
            chunk_content = src.get("text", "") or src.get("content", "")

            # SCRUM-96: dense_vector 존재 여부 체크
            has_embedding = "dense_vector" in src

            result = SearchResult(
                chunk_id=hit.get("_id", str(uuid4())),
                document_id=str(src.get("document_id", "") or metadata.get("document_id", "")),
                content=chunk_content,
                score=float(hit.get("_score", 0.0)),
                source=source,
                metadata=metadata,
                has_embedding=has_embedding,
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
