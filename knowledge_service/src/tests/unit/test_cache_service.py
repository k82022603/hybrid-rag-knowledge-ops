"""
캐시 서비스 단위 테스트 (STORY-060)

검색 결과 캐싱 서비스 테스트:
- 캐시 키 생성
- 캐시 저장/조회
- TTL 기반 만료
- LRU eviction
- 캐시 무효화
- 캐시 통계
"""

import asyncio
import pytest
import time
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.cache_service import (
    CacheStats,
    InMemoryLRUCache,
    LRUCacheEntry,
    SearchCacheService,
    get_cache_service,
    reset_cache_service,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_singleton():
    """테스트 전후 싱글톤 리셋"""
    reset_cache_service()
    yield
    reset_cache_service()


@pytest.fixture
def cache_service() -> SearchCacheService:
    """인메모리 캐시 서비스 생성"""
    return SearchCacheService(
        redis_url=None,
        ttl=60,
        max_size=100,
    )


@pytest.fixture
def small_cache_service() -> SearchCacheService:
    """작은 크기의 캐시 서비스 (LRU eviction 테스트용)"""
    return SearchCacheService(
        redis_url=None,
        ttl=60,
        max_size=3,
    )


@pytest.fixture
def sample_search_result() -> Dict[str, Any]:
    """테스트용 검색 결과 샘플"""
    return {
        "results": [
            {
                "chunk_id": "chunk_001",
                "document_id": "doc_001",
                "content": "테스트 문서 내용입니다.",
                "score": 0.95,
                "source": "vector",
                "metadata": {"title": "테스트 문서"},
            },
            {
                "chunk_id": "chunk_002",
                "document_id": "doc_001",
                "content": "두 번째 청크 내용입니다.",
                "score": 0.87,
                "source": "keyword",
                "metadata": {"title": "테스트 문서"},
            },
        ],
        "total": 2,
        "debug": {
            "vector_count": 5,
            "keyword_count": 5,
            "graph_count": 0,
            "fused_count": 2,
        },
    }


# ---------------------------------------------------------------------------
# CacheStats Tests
# ---------------------------------------------------------------------------


class TestCacheStats:
    """캐시 통계 테스트"""

    def test_initial_state(self):
        """초기 상태 확인"""
        stats = CacheStats()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.total_requests == 0
        assert stats.hit_rate == 0.0
        assert stats.miss_rate == 0.0

    def test_hit_rate_calculation(self):
        """히트율 계산"""
        stats = CacheStats(hits=70, misses=30)
        assert stats.total_requests == 100
        assert stats.hit_rate == 0.7
        assert stats.miss_rate == 0.3

    def test_to_dict(self):
        """딕셔너리 변환"""
        stats = CacheStats(
            hits=80,
            misses=20,
            size=50,
            max_size=100,
            backend="in_memory_lru",
            last_reset="2026-01-29T00:00:00",
        )
        d = stats.to_dict()
        assert d["hits"] == 80
        assert d["misses"] == 20
        assert d["total_requests"] == 100
        assert d["hit_rate"] == 0.8
        assert d["miss_rate"] == 0.2
        assert d["size"] == 50
        assert d["max_size"] == 100
        assert d["backend"] == "in_memory_lru"


# ---------------------------------------------------------------------------
# InMemoryLRUCache Tests
# ---------------------------------------------------------------------------


class TestInMemoryLRUCache:
    """인메모리 LRU 캐시 백엔드 테스트"""

    @pytest.fixture
    def lru_cache(self) -> InMemoryLRUCache:
        """LRU 캐시 생성"""
        return InMemoryLRUCache(max_size=3, default_ttl=60)

    @pytest.mark.asyncio
    async def test_set_and_get(self, lru_cache: InMemoryLRUCache):
        """저장 및 조회"""
        await lru_cache.set("key1", {"data": "value1"})
        result = await lru_cache.get("key1")
        assert result == {"data": "value1"}

    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self, lru_cache: InMemoryLRUCache):
        """존재하지 않는 키 조회"""
        result = await lru_cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_ttl_expiration(self):
        """TTL 만료 테스트"""
        cache = InMemoryLRUCache(max_size=10, default_ttl=1)
        await cache.set("key1", {"data": "value1"})

        # 즉시 조회 - 존재해야 함
        result = await cache.get("key1")
        assert result is not None

        # TTL 만료 후 조회 - 없어야 함
        await asyncio.sleep(1.1)
        result = await cache.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_lru_eviction(self, lru_cache: InMemoryLRUCache):
        """LRU eviction 테스트 (max_size=3)"""
        await lru_cache.set("key1", {"data": "value1"})
        await lru_cache.set("key2", {"data": "value2"})
        await lru_cache.set("key3", {"data": "value3"})

        # 캐시 가득 참
        assert lru_cache.get_size() == 3

        # key1 접근 -> key1이 가장 최근에 사용됨
        await lru_cache.get("key1")

        # 새 항목 추가 -> key2 (LRU) 삭제
        await lru_cache.set("key4", {"data": "value4"})

        # key1, key3, key4 존재, key2 삭제됨
        assert await lru_cache.get("key1") is not None
        assert await lru_cache.get("key2") is None
        assert await lru_cache.get("key3") is not None
        assert await lru_cache.get("key4") is not None

    @pytest.mark.asyncio
    async def test_delete(self, lru_cache: InMemoryLRUCache):
        """삭제 테스트"""
        await lru_cache.set("key1", {"data": "value1"})
        assert await lru_cache.get("key1") is not None

        result = await lru_cache.delete("key1")
        assert result is True
        assert await lru_cache.get("key1") is None

        # 없는 키 삭제
        result = await lru_cache.delete("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_clear(self, lru_cache: InMemoryLRUCache):
        """전체 삭제 테스트"""
        await lru_cache.set("key1", {"data": "value1"})
        await lru_cache.set("key2", {"data": "value2"})

        count = await lru_cache.clear()
        assert count == 2
        assert lru_cache.get_size() == 0

    @pytest.mark.asyncio
    async def test_keys_all(self, lru_cache: InMemoryLRUCache):
        """모든 키 조회"""
        await lru_cache.set("key1", {"data": "value1"})
        await lru_cache.set("key2", {"data": "value2"})

        keys = await lru_cache.keys("*")
        assert "key1" in keys
        assert "key2" in keys

    @pytest.mark.asyncio
    async def test_keys_with_prefix(self, lru_cache: InMemoryLRUCache):
        """접두사 패턴으로 키 조회"""
        await lru_cache.set("search:query1", {"data": "value1"})
        await lru_cache.set("search:query2", {"data": "value2"})
        await lru_cache.set("other:key", {"data": "value3"})

        keys = await lru_cache.keys("search:*")
        assert len(keys) == 2
        assert "search:query1" in keys
        assert "search:query2" in keys
        assert "other:key" not in keys

    def test_get_backend_name(self, lru_cache: InMemoryLRUCache):
        """백엔드 이름"""
        assert lru_cache.get_backend_name() == "in_memory_lru"


# ---------------------------------------------------------------------------
# SearchCacheService Tests
# ---------------------------------------------------------------------------


class TestSearchCacheService:
    """검색 캐시 서비스 테스트"""

    def test_cache_key_generation(self, cache_service: SearchCacheService):
        """캐시 키 생성 - 동일 입력 동일 키"""
        key1 = cache_service.get_cache_key(
            query="테스트 쿼리",
            filters={"project": "test"},
            top_k=10,
            search_type="hybrid",
        )
        key2 = cache_service.get_cache_key(
            query="테스트 쿼리",
            filters={"project": "test"},
            top_k=10,
            search_type="hybrid",
        )
        assert key1 == key2
        assert len(key1) == 64  # SHA256 hex length

    def test_cache_key_different_queries(self, cache_service: SearchCacheService):
        """캐시 키 생성 - 다른 쿼리는 다른 키"""
        key1 = cache_service.get_cache_key(query="쿼리1")
        key2 = cache_service.get_cache_key(query="쿼리2")
        assert key1 != key2

    def test_cache_key_different_filters(self, cache_service: SearchCacheService):
        """캐시 키 생성 - 다른 필터는 다른 키"""
        key1 = cache_service.get_cache_key(
            query="테스트",
            filters={"project": "A"},
        )
        key2 = cache_service.get_cache_key(
            query="테스트",
            filters={"project": "B"},
        )
        assert key1 != key2

    def test_cache_key_different_top_k(self, cache_service: SearchCacheService):
        """캐시 키 생성 - 다른 top_k는 다른 키"""
        key1 = cache_service.get_cache_key(query="테스트", top_k=5)
        key2 = cache_service.get_cache_key(query="테스트", top_k=10)
        assert key1 != key2

    def test_cache_key_normalization(self, cache_service: SearchCacheService):
        """캐시 키 생성 - 정규화 (앞뒤 공백, 대소문자)"""
        key1 = cache_service.get_cache_key(query="  Test Query  ")
        key2 = cache_service.get_cache_key(query="test query")
        assert key1 == key2

    @pytest.mark.asyncio
    async def test_set_and_get(
        self,
        cache_service: SearchCacheService,
        sample_search_result: Dict[str, Any],
    ):
        """캐시 저장 및 조회"""
        key = cache_service.get_cache_key(query="테스트")

        # 저장
        success = await cache_service.set(key, sample_search_result)
        assert success is True

        # 조회
        result = await cache_service.get(key)
        assert result is not None
        assert "results" in result
        assert result["total"] == 2
        # 메타데이터 확인
        assert "_cached_at" in result
        assert "_ttl" in result

    @pytest.mark.asyncio
    async def test_cache_miss(self, cache_service: SearchCacheService):
        """캐시 미스"""
        key = cache_service.get_cache_key(query="존재하지않는쿼리")
        result = await cache_service.get(key)
        assert result is None

    @pytest.mark.asyncio
    async def test_stats_tracking(
        self,
        cache_service: SearchCacheService,
        sample_search_result: Dict[str, Any],
    ):
        """통계 추적"""
        key = cache_service.get_cache_key(query="테스트")

        # 캐시 미스
        await cache_service.get(key)
        stats = cache_service.get_stats()
        assert stats.misses == 1
        assert stats.hits == 0

        # 캐시 저장
        await cache_service.set(key, sample_search_result)

        # 캐시 히트
        await cache_service.get(key)
        stats = cache_service.get_stats()
        assert stats.misses == 1
        assert stats.hits == 1
        assert stats.hit_rate == 0.5

    @pytest.mark.asyncio
    async def test_invalidate_all(
        self,
        cache_service: SearchCacheService,
        sample_search_result: Dict[str, Any],
    ):
        """전체 캐시 무효화"""
        # 여러 항목 저장
        for i in range(5):
            key = cache_service.get_cache_key(query=f"쿼리{i}")
            await cache_service.set(key, sample_search_result)

        # 전체 삭제
        deleted = await cache_service.invalidate(pattern=None)
        assert deleted == 5

        # 확인
        for i in range(5):
            key = cache_service.get_cache_key(query=f"쿼리{i}")
            result = await cache_service.get(key)
            assert result is None

    @pytest.mark.asyncio
    async def test_invalidate_pattern(self, cache_service: SearchCacheService):
        """패턴 기반 캐시 무효화"""
        # 다양한 키로 저장
        await cache_service._backend.set("search:a", {"data": "a"})
        await cache_service._backend.set("search:b", {"data": "b"})
        await cache_service._backend.set("other:c", {"data": "c"})

        # search:* 패턴 삭제
        deleted = await cache_service.invalidate(pattern="search:*")
        assert deleted == 2

        # 확인
        assert await cache_service._backend.get("search:a") is None
        assert await cache_service._backend.get("search:b") is None
        assert await cache_service._backend.get("other:c") is not None

    @pytest.mark.asyncio
    async def test_reset_stats(
        self,
        cache_service: SearchCacheService,
        sample_search_result: Dict[str, Any],
    ):
        """통계 초기화"""
        key = cache_service.get_cache_key(query="테스트")
        await cache_service.get(key)  # miss
        await cache_service.set(key, sample_search_result)
        await cache_service.get(key)  # hit

        stats = cache_service.get_stats()
        assert stats.hits == 1
        assert stats.misses == 1

        # 초기화
        cache_service.reset_stats()

        stats = cache_service.get_stats()
        assert stats.hits == 0
        assert stats.misses == 0

    @pytest.mark.asyncio
    async def test_custom_ttl(
        self,
        sample_search_result: Dict[str, Any],
    ):
        """커스텀 TTL 테스트"""
        cache = SearchCacheService(
            redis_url=None,
            ttl=60,  # 기본 60초
            max_size=100,
        )

        key = cache.get_cache_key(query="테스트")

        # 커스텀 TTL (1초)로 저장
        await cache.set(key, sample_search_result, ttl=1)

        # 즉시 조회 - 있음
        result = await cache.get(key)
        assert result is not None

        # 1초 후 조회 - 없음
        await asyncio.sleep(1.1)
        result = await cache.get(key)
        assert result is None


# ---------------------------------------------------------------------------
# LRU Eviction Tests
# ---------------------------------------------------------------------------


class TestLRUEviction:
    """LRU eviction 상세 테스트"""

    @pytest.mark.asyncio
    async def test_eviction_order(self, small_cache_service: SearchCacheService):
        """LRU eviction 순서 테스트"""
        # max_size=3인 캐시에 4개 저장
        await small_cache_service.set("k1", {"v": 1})
        await small_cache_service.set("k2", {"v": 2})
        await small_cache_service.set("k3", {"v": 3})

        # k1 접근 -> k1이 가장 최근
        await small_cache_service.get("k1")

        # k4 추가 -> k2 (LRU) 삭제
        await small_cache_service.set("k4", {"v": 4})

        # k1, k3, k4 존재
        assert await small_cache_service.get("k1") is not None
        assert await small_cache_service.get("k2") is None
        assert await small_cache_service.get("k3") is not None
        assert await small_cache_service.get("k4") is not None


# ---------------------------------------------------------------------------
# Singleton Tests
# ---------------------------------------------------------------------------


class TestSingleton:
    """싱글톤 패턴 테스트"""

    def test_singleton_instance(self):
        """동일 인스턴스 반환"""
        # settings는 get_cache_service 내부에서 로컬 import 되므로
        # 직접 get_cache_service에 파라미터 전달
        reset_cache_service()

        # 첫 번째 호출
        service1 = get_cache_service(ttl=60, max_size=100)
        # 두 번째 호출 - 같은 인스턴스 반환
        service2 = get_cache_service(ttl=120, max_size=200)  # 파라미터 무시
        assert service1 is service2

    def test_reset_singleton(self):
        """싱글톤 리셋"""
        reset_cache_service()

        service1 = get_cache_service(ttl=60, max_size=100)
        reset_cache_service()
        service2 = get_cache_service(ttl=60, max_size=100)
        assert service1 is not service2


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """엣지 케이스 테스트"""

    @pytest.mark.asyncio
    async def test_empty_query(self, cache_service: SearchCacheService):
        """빈 쿼리 처리"""
        key1 = cache_service.get_cache_key(query="")
        key2 = cache_service.get_cache_key(query="  ")
        assert key1 == key2  # 정규화 후 동일

    @pytest.mark.asyncio
    async def test_none_filters(self, cache_service: SearchCacheService):
        """None 필터 처리"""
        key1 = cache_service.get_cache_key(query="test", filters=None)
        key2 = cache_service.get_cache_key(query="test", filters={})
        assert key1 == key2  # None과 빈 딕셔너리는 동일

    @pytest.mark.asyncio
    async def test_large_value(self, cache_service: SearchCacheService):
        """큰 값 저장"""
        large_results = {
            "results": [{"content": "x" * 10000} for _ in range(100)],
            "total": 100,
        }
        key = cache_service.get_cache_key(query="대용량테스트")

        success = await cache_service.set(key, large_results)
        assert success is True

        result = await cache_service.get(key)
        assert result is not None
        assert len(result["results"]) == 100

    @pytest.mark.asyncio
    async def test_unicode_handling(self, cache_service: SearchCacheService):
        """유니코드 처리"""
        queries = [
            "한글 쿼리",
            "日本語クエリ",
            "🎉 이모지 테스트",
            "mixed 한글 english",
        ]

        for query in queries:
            key = cache_service.get_cache_key(query=query)
            await cache_service.set(key, {"query": query})
            result = await cache_service.get(key)
            assert result is not None
            assert result["query"] == query

    @pytest.mark.asyncio
    async def test_special_characters_in_filters(
        self, cache_service: SearchCacheService
    ):
        """필터 내 특수문자 처리"""
        filters = {
            "path": "/documents/테스트/파일.pdf",
            "tag": "test:value",
            "query": "a=b&c=d",
        }
        key = cache_service.get_cache_key(query="test", filters=filters)

        await cache_service.set(key, {"filters": filters})
        result = await cache_service.get(key)
        assert result is not None
        assert result["filters"] == filters


# ---------------------------------------------------------------------------
# Integration with Search Service
# ---------------------------------------------------------------------------


class TestSearchServiceIntegration:
    """SearchService 통합 테스트"""

    @pytest.mark.asyncio
    async def test_search_uses_cache(self):
        """SearchService가 캐시를 사용하는지 확인"""
        from app.services.search import SearchService

        with patch("app.services.search.settings") as mock_settings:
            mock_settings.search_cache_enabled = True
            mock_settings.search_cache_ttl = 60
            mock_settings.search_cache_max_size = 100
            mock_settings.rrf_k = 60

            # SearchService 생성
            service = SearchService(cache_enabled=True)

            # _get_cache_service 모킹
            with patch("app.services.search._get_cache_service") as mock_get_cache:
                mock_cache = AsyncMock()
                mock_cache.get_cache_key.return_value = "test_key"
                mock_cache.get.return_value = None  # 캐시 미스
                mock_cache.set.return_value = True
                mock_get_cache.return_value = mock_cache

                # 캐시 활성화된 서비스 생성
                service._cache = mock_cache

                # 검색 수행 (실제 ES/Neo4j 없이)
                try:
                    await service.hybrid_search(
                        query="테스트 쿼리",
                        filters=None,
                        top_k=10,
                    )
                except Exception:
                    # 실제 DB 없이 테스트하므로 예외 허용
                    pass

                # 캐시 키 생성 호출 확인
                mock_cache.get_cache_key.assert_called()
