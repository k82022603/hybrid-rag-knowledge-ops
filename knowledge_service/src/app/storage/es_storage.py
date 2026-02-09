"""
Elasticsearch 벡터/키워드 저장 서비스

STORY-006: Neo4j/Elasticsearch 저장 서비스 구현

청크와 임베딩 벡터를 Elasticsearch에 저장하고 검색합니다.
- 인덱스 매핑 자동 생성 (dense_vector 1024차원, nori 분석기)
- 벌크 인덱싱 최적화 (helpers.async_bulk)
- kNN 벡터 유사도 검색 (cosine similarity)
- BM25 키워드 검색
- 비동기 지원 (async/await)
- 싱글톤 패턴 (get_es_storage_service)

인덱스 매핑: infrastructure/database/elasticsearch/mappings.json 참조
"""

import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.exceptions import ElasticsearchError
from app.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Default index mappings
# ---------------------------------------------------------------------------

DEFAULT_INDEX_SETTINGS: Dict[str, Any] = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "index.codec": "best_compression",
        "analysis": {
            "analyzer": {
                "korean_analyzer": {
                    "type": "custom",
                    "tokenizer": "nori_tokenizer",
                    "filter": ["lowercase", "nori_part_of_speech"],
                },
                "text_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "asciifolding"],
                },
            },
            "filter": {
                "nori_part_of_speech": {
                    "type": "nori_part_of_speech",
                    "stoptags": [
                        "E", "IC", "J", "MAG", "MAJ", "MM",
                        "SP", "SSC", "SSO", "SC", "SE",
                        "XPN", "XSA", "XSN", "XSV", "UNA", "NA", "VSV",
                    ],
                },
            },
        },
        "index.knn": True,
    },
    "mappings": {
        "properties": {
            "chunk_id": {"type": "keyword"},
            "document_id": {"type": "keyword"},
            "chunk_index": {"type": "integer"},
            "text": {
                "type": "text",
                "analyzer": "korean_analyzer",
                "search_analyzer": "korean_analyzer",
                "fields": {
                    "standard": {"type": "text", "analyzer": "text_analyzer"},
                    "keyword": {"type": "keyword", "ignore_above": 256},
                },
            },
            "dense_vector": {
                "type": "dense_vector",
                "dims": 1024,
                "index": True,
                "similarity": "cosine",
            },
            "sparse_vector": {"type": "sparse_vector"},
            "heading": {
                "type": "text",
                "analyzer": "korean_analyzer",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "token_count": {"type": "integer"},
            "metadata": {
                "type": "object",
                "enabled": True,
                "properties": {
                    "document_type": {"type": "keyword"},
                    "project_name": {"type": "keyword"},
                    "title": {
                        "type": "text",
                        "analyzer": "korean_analyzer",
                        "fields": {"keyword": {"type": "keyword"}},
                    },
                    "summary": {"type": "text", "analyzer": "korean_analyzer"},
                    "categories": {"type": "keyword"},
                    "keywords": {"type": "keyword"},
                    "tags": {"type": "keyword"},
                    "source": {"type": "keyword"},
                    "page": {"type": "integer"},
                },
            },
            "neo4j_entity_ids": {"type": "keyword"},
            "total_chunks": {"type": "integer"},
            "created_at": {
                "type": "date",
                "format": "yyyy-MM-dd'T'HH:mm:ss.SSSZ||yyyy-MM-dd'T'HH:mm:ssZ||epoch_millis",
            },
            "updated_at": {
                "type": "date",
                "format": "yyyy-MM-dd'T'HH:mm:ss.SSSZ||yyyy-MM-dd'T'HH:mm:ssZ||epoch_millis",
            },
        },
    },
}


# ---------------------------------------------------------------------------
# ElasticsearchStorageService
# ---------------------------------------------------------------------------


class ElasticsearchStorageService:
    """
    Elasticsearch 벡터/키워드 저장 서비스

    청크와 임베딩 벡터를 Elasticsearch에 인덱싱하고,
    kNN 벡터 유사도 검색과 BM25 키워드 검색을 제공합니다.

    Attributes:
        _client: Elasticsearch 비동기 클라이언트
        _index_name: 기본 인덱스 이름
    """

    def __init__(
        self,
        hosts: Optional[List[str]] = None,
        index_name: Optional[str] = None,
        basic_auth: Optional[tuple] = None,
    ):
        """ElasticsearchStorageService 초기화

        클라이언트를 즉시 생성하지 않고, 첫 사용 시 지연 연결합니다.

        Args:
            hosts: Elasticsearch 호스트 목록 (기본: 설정값)
            index_name: 기본 인덱스 이름 (기본: 설정값)
            basic_auth: 기본 인증 (user, password) 튜플
        """
        if hosts:
            self._hosts = hosts
        else:
            self._hosts = [settings.elasticsearch_url]

        self._index_name = index_name or settings.elasticsearch_index
        self._basic_auth = basic_auth
        self._client: Optional[Any] = None

        # 인증 정보 설정
        if not self._basic_auth:
            if settings.elasticsearch_user and settings.elasticsearch_password:
                self._basic_auth = (
                    settings.elasticsearch_user,
                    settings.elasticsearch_password,
                )

        logger.info(
            "ElasticsearchStorageService initialized: hosts=%s, index=%s",
            self._hosts,
            self._index_name,
        )

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def _ensure_client(self) -> Any:
        """Elasticsearch 클라이언트 지연 초기화

        Returns:
            AsyncElasticsearch 클라이언트

        Raises:
            ElasticsearchError: 클라이언트 생성 실패 시
        """
        if self._client is not None:
            return self._client

        try:
            from elasticsearch import AsyncElasticsearch

            kwargs: Dict[str, Any] = {
                "hosts": self._hosts,
                "request_timeout": 30,
                "max_retries": 3,
                "retry_on_timeout": True,
            }

            if self._basic_auth:
                kwargs["basic_auth"] = self._basic_auth

            # HTTP 연결 (xpack.security.enabled=false)
            kwargs["verify_certs"] = False

            self._client = AsyncElasticsearch(**kwargs)
            logger.info("Elasticsearch client connected: hosts=%s", self._hosts)
            return self._client

        except ImportError:
            raise ElasticsearchError(
                message=(
                    "elasticsearch 패키지가 설치되지 않았습니다. "
                    "pip install elasticsearch[async]"
                ),
                details={"package": "elasticsearch[async]"},
            )
        except Exception as e:
            raise ElasticsearchError(
                message=f"Elasticsearch 클라이언트 생성 실패: {e}",
                details={"hosts": self._hosts},
            )

    async def close(self) -> None:
        """클라이언트 연결 종료"""
        if self._client is not None:
            await self._client.close()
            self._client = None
            logger.info("Elasticsearch client closed")

    async def verify_connectivity(self) -> bool:
        """Elasticsearch 연결 상태 확인

        Returns:
            연결 성공 여부
        """
        try:
            client = self._ensure_client()
            info = await client.info()
            logger.debug("Elasticsearch info: %s", info.get("version", {}).get("number"))
            return True
        except Exception as e:
            logger.warning("Elasticsearch connectivity check failed: %s", e)
            return False

    # ------------------------------------------------------------------
    # Index management
    # ------------------------------------------------------------------

    async def create_index(
        self,
        index_name: Optional[str] = None,
        settings_override: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """인덱스 매핑을 생성 (이미 존재하면 건너뜀)

        Args:
            index_name: 생성할 인덱스 이름 (기본: 설정값)
            settings_override: 인덱스 설정 덮어쓰기 (기본: DEFAULT_INDEX_SETTINGS)

        Returns:
            인덱스 생성 성공 여부 (이미 존재하면 True)

        Raises:
            ElasticsearchError: 인덱스 생성 실패 시
        """
        client = self._ensure_client()
        idx = index_name or self._index_name
        body = settings_override or DEFAULT_INDEX_SETTINGS

        try:
            exists = await client.indices.exists(index=idx)
            if exists:
                logger.info("Index already exists: %s", idx)
                return True

            await client.indices.create(index=idx, body=body)
            logger.info("Index created: %s", idx)
            return True

        except Exception as e:
            # "resource_already_exists_exception" 은 무시
            error_str = str(e)
            if "resource_already_exists_exception" in error_str:
                logger.info("Index already exists (concurrent): %s", idx)
                return True

            raise ElasticsearchError(
                message=f"인덱스 생성 실패: {e}",
                details={"index": idx},
            )

    async def delete_index(self, index_name: Optional[str] = None) -> bool:
        """인덱스 삭제

        Args:
            index_name: 삭제할 인덱스 이름 (기본: 설정값)

        Returns:
            삭제 성공 여부

        Raises:
            ElasticsearchError: 삭제 실패 시
        """
        client = self._ensure_client()
        idx = index_name or self._index_name

        try:
            exists = await client.indices.exists(index=idx)
            if not exists:
                logger.info("Index does not exist: %s", idx)
                return True

            await client.indices.delete(index=idx)
            logger.info("Index deleted: %s", idx)
            return True

        except Exception as e:
            raise ElasticsearchError(
                message=f"인덱스 삭제 실패: {e}",
                details={"index": idx},
            )

    # ------------------------------------------------------------------
    # Indexing (write)
    # ------------------------------------------------------------------

    async def index_chunks(
        self,
        chunks: List[Dict[str, Any]],
        index_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """청크 + 벡터를 벌크 인덱싱

        각 청크 딕셔너리에는 다음 필드가 포함되어야 합니다:
            - chunk_id: str (필수)
            - document_id: str (필수)
            - content: str (text 필드로 매핑)
            - dense_vector: List[float] (1024차원)
            - chunk_index: int (선택)
            - metadata: dict (선택)

        Args:
            chunks: 인덱싱할 청크 딕셔너리 리스트
            index_name: 인덱스 이름 (기본: 설정값)

        Returns:
            인덱싱 결과 통계 {"indexed": n, "errors": m, "latency_ms": float}

        Raises:
            ElasticsearchError: 인덱싱 실패 시
        """
        if not chunks:
            return {"indexed": 0, "errors": 0, "latency_ms": 0.0}

        start_time = time.monotonic()
        client = self._ensure_client()
        idx = index_name or self._index_name
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

        # 인덱스 자동 생성
        await self.create_index(index_name=idx)

        try:
            from elasticsearch.helpers import async_bulk

            actions = []
            for chunk in chunks:
                chunk_id = chunk.get("chunk_id", chunk.get("id", ""))
                doc: Dict[str, Any] = {
                    "chunk_id": chunk_id,
                    "document_id": chunk.get("document_id", ""),
                    "text": chunk.get("content", chunk.get("text", "")),
                    "chunk_index": chunk.get("chunk_index", 0),
                    "token_count": chunk.get("token_count", 0),
                    "heading": chunk.get("heading", ""),
                    "metadata": chunk.get("metadata", {}),
                    "created_at": now_iso,
                    "updated_at": now_iso,
                }

                # 벡터 필드
                dense_vector = chunk.get("dense_vector", chunk.get("embedding"))
                if dense_vector is not None:
                    doc["dense_vector"] = dense_vector

                sparse_vector = chunk.get("sparse_vector")
                if sparse_vector is not None:
                    doc["sparse_vector"] = sparse_vector

                # Neo4j 연결 정보 (선택)
                entity_ids = chunk.get("neo4j_entity_ids")
                if entity_ids:
                    doc["neo4j_entity_ids"] = entity_ids

                total_chunks = chunk.get("total_chunks")
                if total_chunks is not None:
                    doc["total_chunks"] = total_chunks

                actions.append({
                    "_index": idx,
                    "_id": chunk_id,
                    "_source": doc,
                })

            success_count, errors = await async_bulk(
                client,
                actions,
                raise_on_error=False,
                chunk_size=500,
                max_retries=3,
            )

            error_count = len(errors) if isinstance(errors, list) else 0
            latency_ms = (time.monotonic() - start_time) * 1000

            logger.info(
                "Chunks indexed: index=%s, success=%d, errors=%d, latency=%.1fms",
                idx,
                success_count,
                error_count,
                latency_ms,
            )

            return {
                "indexed": success_count,
                "errors": error_count,
                "latency_ms": round(latency_ms, 2),
            }

        except ImportError:
            raise ElasticsearchError(
                message="elasticsearch.helpers 모듈을 찾을 수 없습니다",
            )
        except ElasticsearchError:
            raise
        except Exception as e:
            raise ElasticsearchError(
                message=f"청크 인덱싱 실패: {e}",
                details={"chunk_count": len(chunks), "index": idx},
            )

    async def index_single(
        self,
        chunk: Dict[str, Any],
        index_name: Optional[str] = None,
    ) -> bool:
        """단일 청크 인덱싱

        Args:
            chunk: 인덱싱할 청크 딕셔너리
            index_name: 인덱스 이름

        Returns:
            인덱싱 성공 여부
        """
        result = await self.index_chunks([chunk], index_name=index_name)
        return result["indexed"] == 1

    # ------------------------------------------------------------------
    # Search (read)
    # ------------------------------------------------------------------

    async def search_vectors(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        index_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """kNN 벡터 유사도 검색

        cosine similarity 기반으로 유사 벡터를 검색합니다.

        Args:
            query_vector: 쿼리 벡터 (1024차원)
            top_k: 반환할 결과 수
            filters: Elasticsearch 필터 쿼리 (선택)
            index_name: 검색할 인덱스 이름

        Returns:
            검색 결과 리스트 [{"chunk_id", "document_id", "text", "score", "metadata"}]

        Raises:
            ElasticsearchError: 검색 실패 시
        """
        client = self._ensure_client()
        idx = index_name or self._index_name

        try:
            knn_query: Dict[str, Any] = {
                "field": "dense_vector",
                "query_vector": query_vector,
                "k": top_k,
                "num_candidates": top_k * 10,
            }

            if filters:
                knn_query["filter"] = filters

            body: Dict[str, Any] = {
                "knn": knn_query,
                "size": top_k,
                "_source": {
                    "excludes": ["dense_vector", "sparse_vector"],
                },
            }

            response = await client.search(index=idx, body=body)

            return self._parse_hits(response)

        except Exception as e:
            raise ElasticsearchError(
                message=f"벡터 검색 실패: {e}",
                details={"index": idx, "top_k": top_k},
            )

    async def search_keyword(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        index_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """BM25 키워드 검색

        Args:
            query: 검색 질의 텍스트
            top_k: 반환할 결과 수
            filters: Elasticsearch 필터 쿼리 (선택)
            index_name: 검색할 인덱스 이름

        Returns:
            검색 결과 리스트 [{"chunk_id", "document_id", "text", "score", "metadata"}]

        Raises:
            ElasticsearchError: 검색 실패 시
        """
        client = self._ensure_client()
        idx = index_name or self._index_name

        try:
            must_query: Dict[str, Any] = {
                "multi_match": {
                    "query": query,
                    "fields": [
                        "text^3",
                        "text.standard^2",
                        "heading^2",
                        "metadata.title^2",
                        "metadata.summary",
                    ],
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                },
            }

            bool_query: Dict[str, Any] = {"must": [must_query]}

            if filters:
                if isinstance(filters, list):
                    bool_query["filter"] = filters
                else:
                    bool_query["filter"] = [filters]

            body: Dict[str, Any] = {
                "query": {"bool": bool_query},
                "size": top_k,
                "_source": {
                    "excludes": ["dense_vector", "sparse_vector"],
                },
                "highlight": {
                    "fields": {
                        "text": {
                            "fragment_size": 200,
                            "number_of_fragments": 3,
                        },
                    },
                },
            }

            response = await client.search(index=idx, body=body)

            return self._parse_hits(response)

        except Exception as e:
            raise ElasticsearchError(
                message=f"키워드 검색 실패: {e}",
                details={"index": idx, "query": query[:200]},
            )

    # ------------------------------------------------------------------
    # Delete operations (rollback support)
    # ------------------------------------------------------------------

    async def delete_by_document_id(
        self,
        document_id: str,
        index_name: Optional[str] = None,
    ) -> int:
        """문서 ID로 모든 청크 삭제 (롤백용)

        Args:
            document_id: 삭제할 문서 ID
            index_name: 인덱스 이름

        Returns:
            삭제된 문서 수

        Raises:
            ElasticsearchError: 삭제 실패 시
        """
        client = self._ensure_client()
        idx = index_name or self._index_name

        try:
            response = await client.delete_by_query(
                index=idx,
                body={
                    "query": {
                        "term": {"document_id": document_id},
                    },
                },
                refresh=True,
            )

            deleted = response.get("deleted", 0)
            logger.info(
                "Chunks deleted by document_id: index=%s, doc_id=%s, count=%d",
                idx,
                document_id,
                deleted,
            )
            return deleted

        except Exception as e:
            raise ElasticsearchError(
                message=f"문서 청크 삭제 실패: {e}",
                details={"document_id": document_id, "index": idx},
            )

    async def delete_by_chunk_id(
        self,
        chunk_id: str,
        index_name: Optional[str] = None,
    ) -> bool:
        """청크 ID로 단일 문서 삭제

        Args:
            chunk_id: 삭제할 청크 ID
            index_name: 인덱스 이름

        Returns:
            삭제 성공 여부
        """
        client = self._ensure_client()
        idx = index_name or self._index_name

        try:
            await client.delete(index=idx, id=chunk_id, refresh=True)
            return True
        except Exception as e:
            logger.warning("Chunk delete failed: id=%s, error=%s", chunk_id, e)
            return False

    # ------------------------------------------------------------------
    # Health & stats
    # ------------------------------------------------------------------

    async def health_check(self) -> Dict[str, Any]:
        """서비스 상태 점검

        Returns:
            상태 정보 딕셔너리
        """
        connected = await self.verify_connectivity()

        result: Dict[str, Any] = {
            "service": "ElasticsearchStorageService",
            "connected": connected,
            "hosts": self._hosts,
            "index": self._index_name,
        }

        if connected:
            try:
                client = self._ensure_client()
                # 인덱스 통계
                idx_exists = await client.indices.exists(index=self._index_name)
                result["index_exists"] = idx_exists

                if idx_exists:
                    stats = await client.indices.stats(index=self._index_name)
                    primaries = stats.get("_all", {}).get("primaries", {})
                    result["doc_count"] = primaries.get("docs", {}).get("count", 0)
                    result["store_size"] = primaries.get("store", {}).get(
                        "size_in_bytes", 0
                    )
            except Exception as e:
                result["stats_error"] = str(e)

        return result

    async def get_document_count(
        self, index_name: Optional[str] = None,
    ) -> int:
        """인덱스의 문서 수 조회

        Args:
            index_name: 인덱스 이름

        Returns:
            문서 수
        """
        client = self._ensure_client()
        idx = index_name or self._index_name

        try:
            response = await client.count(index=idx)
            return response.get("count", 0)
        except Exception:
            return 0

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_hits(response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Elasticsearch 응답의 hits를 파싱

        Args:
            response: Elasticsearch 검색 응답

        Returns:
            파싱된 결과 리스트
        """
        results: List[Dict[str, Any]] = []
        hits = response.get("hits", {}).get("hits", [])

        for hit in hits:
            source = hit.get("_source", {})
            # ES 문서의 content 필드명은 "text"(정상) 또는 "content"(InitialDataLoader 경유)
            # 두 가지가 공존하므로 둘 다 확인하여 누락 방지
            chunk_text = source.get("text", "") or source.get("content", "")
            result: Dict[str, Any] = {
                "chunk_id": hit.get("_id", ""),
                "document_id": source.get("document_id", ""),
                "text": chunk_text,
                "score": float(hit.get("_score", 0.0)),
                "chunk_index": source.get("chunk_index", 0),
                "heading": source.get("heading", ""),
                "token_count": source.get("token_count", 0),
                "metadata": source.get("metadata", {}),
            }

            # 하이라이트 포함
            highlight = hit.get("highlight", {})
            if highlight:
                result["highlight"] = highlight

            results.append(result)

        return results


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------

_es_storage_service: Optional[ElasticsearchStorageService] = None


def get_es_storage_service(**kwargs: Any) -> ElasticsearchStorageService:
    """ElasticsearchStorageService 싱글톤 팩토리

    처음 호출 시 인스턴스를 생성하고, 이후에는 동일 인스턴스를 반환합니다.

    Args:
        **kwargs: ElasticsearchStorageService 생성자 인자

    Returns:
        ElasticsearchStorageService 인스턴스 (싱글톤)
    """
    global _es_storage_service
    if _es_storage_service is None:
        _es_storage_service = ElasticsearchStorageService(**kwargs)
    return _es_storage_service


def reset_es_storage_service() -> None:
    """싱글톤 인스턴스 초기화 (테스트용)"""
    global _es_storage_service
    _es_storage_service = None
