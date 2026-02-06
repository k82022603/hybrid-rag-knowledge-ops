"""
캐시 서비스 단위 테스트 (STORY-060) - Standalone Version

검색 결과 캐싱 서비스 테스트:
- 캐시 키 생성
- 캐시 저장/조회
- TTL 기반 만료
- LRU eviction
- 캐시 무효화
- 캐시 통계
- Redis 백엔드 테스트 (Mocked)
"""

import asyncio
import hashlib
import json
import pytest
import time
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from abc import ABC, abstractmethod


# ---------------------------------------------------------------------------
# Mock logger to avoid app.core.logging dependency
# ---------------------------------------------------------------------------

class MockLogger:
    """Mock logger for standalone tests"""
    def info(self, msg, *args, **kwargs):
        pass
    def debug(self, msg, *args, **kwargs):
        pass
    def warning(self, msg, *args, **kwargs):
        pass
    def error(self, msg, *args, **kwargs):
        pass


# ---------------------------------------------------------------------------
# Copy of CacheStats from cache_service.py
# ---------------------------------------------------------------------------

@dataclass
class CacheStats:
    """캐시 통계 정보"""

    hits: int = 0
    misses: int = 0
    size: int = 0
    max_size: int = 0
    backend: str = "unknown"
    last_reset: str = ""

    @property
    def total_requests(self) -> int:
        """총 요청 수"""
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        """캐시 히트율 (0.0 ~ 1.0)"""
        if self.total_requests == 0:
            return 0.0
        return self.hits / self.total_requests

    @property
    def miss_rate(self) -> float:
        """캐시 미스율 (0.0 ~ 1.0)"""
        if self.total_requests == 0:
            return 0.0
        return self.misses / self.total_requests

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": self.total_requests,
            "hit_rate": round(self.hit_rate, 4),
            "miss_rate": round(self.miss_rate, 4),
            "size": self.size,
            "max_size": self.max_size,
            "backend": self.backend,
            "last_reset": self.last_reset,
        }


# ---------------------------------------------------------------------------
# Copy of CacheBackend Interface
# ---------------------------------------------------------------------------

class CacheBackend(ABC):
    """캐시 백엔드 추상 인터페이스"""

    @abstractmethod
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """캐시에서 조회"""
        pass

    @abstractmethod
    async def set(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """캐시에 저장"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """캐시에서 삭제"""
        pass

    @abstractmethod
    async def clear(self) -> int:
        """캐시 전체 삭제"""
        pass

    @abstractmethod
    async def keys(self, pattern: str = "*") -> List[str]:
        """패턴에 매칭되는 키 목록 조회"""
        pass

    @abstractmethod
    def get_size(self) -> int:
        """현재 캐시 크기"""
        pass

    @abstractmethod
    def get_max_size(self) -> int:
        """최대 캐시 크기"""
        pass

    @abstractmethod
    def get_backend_name(self) -> str:
        """백엔드 이름"""
        pass


# ---------------------------------------------------------------------------
# Copy of LRUCacheEntry and InMemoryLRUCache
# ---------------------------------------------------------------------------

@dataclass
class LRUCacheEntry:
    """LRU 캐시 엔트리"""

    value: Dict[str, Any]
    expires_at: float  # Unix timestamp
    created_at: float = field(default_factory=time.time)


class InMemoryLRUCache(CacheBackend):
    """
    인메모리 LRU 캐시 백엔드

    Redis가 없을 때 폴백으로 사용되는 LRU (Least Recently Used) 캐시입니다.
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600, logger=None):
        self._cache: OrderedDict[str, LRUCacheEntry] = OrderedDict()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = Lock()
        self._logger = logger or MockLogger()

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                return None

            # 만료 확인
            if time.time() > entry.expires_at:
                del self._cache[key]
                return None

            # LRU: 최근 접근 → 끝으로 이동
            self._cache.move_to_end(key)
            return entry.value

    async def set(
        self,
        key: str,
        value: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> bool:
        effective_ttl = ttl if ttl is not None else self._default_ttl

        with self._lock:
            # 이미 존재하면 삭제 (순서 갱신 위해)
            if key in self._cache:
                del self._cache[key]

            # 용량 초과 시 가장 오래된 항목 제거 (LRU eviction)
            while len(self._cache) >= self._max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                self._logger.debug(f"LRU eviction: {oldest_key[:20]}...")

            # 새 엔트리 추가
            entry = LRUCacheEntry(
                value=value,
                expires_at=time.time() + effective_ttl,
            )
            self._cache[key] = entry
            return True

    async def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear(self) -> int:
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    async def keys(self, pattern: str = "*") -> List[str]:
        with self._lock:
            # 만료된 항목 정리
            now = time.time()
            expired_keys = [k for k, v in self._cache.items() if v.expires_at < now]
            for k in expired_keys:
                del self._cache[k]

            if pattern == "*":
                return list(self._cache.keys())

            # prefix* 패턴 처리
            if pattern.endswith("*"):
                prefix = pattern[:-1]
                return [k for k in self._cache.keys() if k.startswith(prefix)]

            # 정확한 매칭
            if pattern in self._cache:
                return [pattern]
            return []

    def get_size(self) -> int:
        return len(self._cache)

    def get_max_size(self) -> int:
        return self._max_size

    def get_backend_name(self) -> str:
        return "in_memory_lru"


# ---------------------------------------------------------------------------
# Copy of RedisCacheBackend
# ---------------------------------------------------------------------------

class RedisCacheBackend(CacheBackend):
    """
    Redis 캐시 백엔드

    분산 환경에서 공유 캐시를 제공합니다.
    """

    def __init__(
        self,
        redis_url: str,
        prefix: str = "search_cache:",
        default_ttl: int = 3600,
        max_size: int = 10000,
        logger=None,
    ):
        self._redis_url = redis_url
        self._prefix = prefix
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._client = None
        self._logger = logger or MockLogger()

    async def _get_client(self):
        """Redis 클라이언트 lazily 초기화"""
        if self._client is None:
            try:
                import redis.asyncio as aioredis

                self._client = aioredis.from_url(
                    self._redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
                self._logger.info("Redis client connected")
            except Exception as e:
                self._logger.error(f"Redis connection failed: {e}")
                raise
        return self._client

    def _make_key(self, key: str) -> str:
        """접두사가 붙은 전체 키 생성"""
        return f"{self._prefix}{key}"

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        try:
            client = await self._get_client()
            full_key = self._make_key(key)
            data = await client.get(full_key)

            if data is None:
                return None

            return json.loads(data)

        except Exception as e:
            self._logger.warning(f"Redis get failed: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> bool:
        try:
            effective_ttl = ttl if ttl is not None else self._default_ttl
            client = await self._get_client()
            full_key = self._make_key(key)
            data = json.dumps(value, ensure_ascii=False)

            await client.set(full_key, data, ex=effective_ttl)
            return True

        except Exception as e:
            self._logger.warning(f"Redis set failed: {e}")
            return False

    async def delete(self, key: str) -> bool:
        try:
            client = await self._get_client()
            full_key = self._make_key(key)
            result = await client.delete(full_key)
            return result > 0

        except Exception as e:
            self._logger.warning(f"Redis delete failed: {e}")
            return False

    async def clear(self) -> int:
        try:
            client = await self._get_client()
            pattern = self._make_key("*")

            # SCAN으로 키 조회 후 삭제 (KEYS 대신 안전한 방식)
            deleted = 0
            cursor = 0
            while True:
                cursor, keys = await client.scan(cursor, match=pattern, count=100)
                if keys:
                    deleted += await client.delete(*keys)
                if cursor == 0:
                    break

            return deleted

        except Exception as e:
            self._logger.warning(f"Redis clear failed: {e}")
            return 0

    async def keys(self, pattern: str = "*") -> List[str]:
        try:
            client = await self._get_client()
            full_pattern = self._make_key(pattern)

            result = []
            cursor = 0
            while True:
                cursor, keys = await client.scan(cursor, match=full_pattern, count=100)
                for k in keys:
                    # prefix 제거
                    result.append(k[len(self._prefix):])
                if cursor == 0:
                    break

            return result

        except Exception as e:
            self._logger.warning(f"Redis keys failed: {e}")
            return []

    def get_size(self) -> int:
        """현재 캐시 크기 (비동기 호출 불가, 추정치 반환)"""
        return -1

    def get_max_size(self) -> int:
        """최대 캐시 크기 (Redis는 메모리 기반)"""
        return self._max_size

    def get_backend_name(self) -> str:
        """백엔드 이름"""
        return "redis"


# ---------------------------------------------------------------------------
# Copy of SearchCacheService
# ---------------------------------------------------------------------------

class SearchCacheService:
    """
    검색 결과 캐싱 서비스
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        ttl: int = 3600,
        max_size: int = 1000,
        prefix: str = "search_cache:",
        logger=None,
    ):
        self._ttl = ttl
        self._max_size = max_size
        self._prefix = prefix
        self._logger = logger or MockLogger()

        # 통계 초기화
        self._stats = CacheStats(
            max_size=max_size,
            last_reset=datetime.now(timezone.utc).isoformat(),
        )

        # 백엔드 선택
        if redis_url:
            try:
                self._backend = RedisCacheBackend(
                    redis_url=redis_url,
                    prefix=prefix,
                    default_ttl=ttl,
                    max_size=max_size,
                    logger=self._logger,
                )
                self._stats.backend = "redis"
            except Exception as e:
                self._logger.warning(f"Redis init failed, falling back to in-memory: {e}")
                self._backend = InMemoryLRUCache(max_size=max_size, default_ttl=ttl, logger=self._logger)
                self._stats.backend = "in_memory_lru"
        else:
            self._backend = InMemoryLRUCache(max_size=max_size, default_ttl=ttl, logger=self._logger)
            self._stats.backend = "in_memory_lru"

    def get_cache_key(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 10,
        search_type: str = "hybrid",
    ) -> str:
        # 정규화: 앞뒤 공백 제거, 소문자 변환
        normalized_query = query.strip().lower()

        # 필터 정규화: 정렬된 JSON (None은 빈 딕셔너리)
        normalized_filters = json.dumps(
            filters or {},
            sort_keys=True,
            ensure_ascii=False,
        )

        # 캐시 키 구성요소 조합
        key_components = f"{search_type}:{normalized_query}:{normalized_filters}:{top_k}"

        # SHA256 해싱
        cache_key = hashlib.sha256(key_components.encode("utf-8")).hexdigest()
        return cache_key

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        result = await self._backend.get(key)

        if result is not None:
            self._stats.hits += 1
        else:
            self._stats.misses += 1

        return result

    async def set(
        self,
        key: str,
        value: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> bool:
        effective_ttl = ttl if ttl is not None else self._ttl

        # 캐시 저장 시 메타데이터 추가
        cached_value = {
            **value,
            "_cached_at": datetime.now(timezone.utc).isoformat(),
            "_ttl": effective_ttl,
        }

        success = await self._backend.set(key, cached_value, effective_ttl)

        if success:
            self._stats.size = self._backend.get_size()

        return success

    async def invalidate(self, pattern: Optional[str] = None) -> int:
        if pattern is None:
            # 전체 클리어
            deleted = await self._backend.clear()
        else:
            # 패턴 매칭 삭제
            keys = await self._backend.keys(pattern)
            deleted = 0
            for key in keys:
                if await self._backend.delete(key):
                    deleted += 1

        self._stats.size = self._backend.get_size()
        return deleted

    async def delete(self, key: str) -> bool:
        success = await self._backend.delete(key)
        if success:
            self._stats.size = self._backend.get_size()
        return success

    def get_stats(self) -> CacheStats:
        # 현재 크기 갱신
        current_size = self._backend.get_size()
        if current_size >= 0:
            self._stats.size = current_size
        self._stats.max_size = self._backend.get_max_size()
        self._stats.backend = self._backend.get_backend_name()

        return self._stats

    def reset_stats(self) -> None:
        """통계 초기화"""
        self._stats.hits = 0
        self._stats.misses = 0
        self._stats.last_reset = datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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

    def test_zero_total_requests(self):
        """총 요청이 0일 때 히트율/미스율"""
        stats = CacheStats(hits=0, misses=0)
        assert stats.hit_rate == 0.0
        assert stats.miss_rate == 0.0


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

    @pytest.mark.asyncio
    async def test_keys_exact_match(self, lru_cache: InMemoryLRUCache):
        """정확한 키 매칭"""
        await lru_cache.set("exact_key", {"data": "value1"})
        await lru_cache.set("other_key", {"data": "value2"})

        keys = await lru_cache.keys("exact_key")
        assert len(keys) == 1
        assert "exact_key" in keys

    @pytest.mark.asyncio
    async def test_keys_no_match(self, lru_cache: InMemoryLRUCache):
        """매칭되지 않는 키"""
        await lru_cache.set("key1", {"data": "value1"})

        keys = await lru_cache.keys("nonexistent")
        assert len(keys) == 0

    @pytest.mark.asyncio
    async def test_keys_expired_cleanup(self):
        """keys() 호출 시 만료된 항목 정리"""
        cache = InMemoryLRUCache(max_size=10, default_ttl=1)
        await cache.set("key1", {"data": "value1"})
        await cache.set("key2", {"data": "value2"}, ttl=10)  # 더 긴 TTL

        # key1 만료 후 keys() 호출
        await asyncio.sleep(1.1)
        keys = await cache.keys("*")

        # key1은 만료되어 정리됨, key2만 남음
        assert "key1" not in keys
        assert "key2" in keys

    def test_get_backend_name(self, lru_cache: InMemoryLRUCache):
        """백엔드 이름"""
        assert lru_cache.get_backend_name() == "in_memory_lru"

    def test_get_max_size(self, lru_cache: InMemoryLRUCache):
        """최대 크기"""
        assert lru_cache.get_max_size() == 3

    @pytest.mark.asyncio
    async def test_set_with_custom_ttl(self, lru_cache: InMemoryLRUCache):
        """커스텀 TTL로 저장"""
        await lru_cache.set("key1", {"data": "value1"}, ttl=1)

        result = await lru_cache.get("key1")
        assert result is not None

        await asyncio.sleep(1.1)
        result = await lru_cache.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_update_existing(self, lru_cache: InMemoryLRUCache):
        """기존 키 업데이트"""
        await lru_cache.set("key1", {"data": "value1"})
        await lru_cache.set("key1", {"data": "value2"})

        result = await lru_cache.get("key1")
        assert result == {"data": "value2"}
        assert lru_cache.get_size() == 1


# ---------------------------------------------------------------------------
# RedisCacheBackend Tests (Mocked)
# ---------------------------------------------------------------------------

class TestRedisCacheBackend:
    """Redis 캐시 백엔드 테스트 (Mocked)"""

    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis 클라이언트"""
        client = AsyncMock()
        return client

    @pytest.fixture
    def redis_backend(self, mock_redis_client) -> RedisCacheBackend:
        """Redis 백엔드 생성 (Mock)"""
        backend = RedisCacheBackend(
            redis_url="redis://localhost:6379/0",
            prefix="test_cache:",
            default_ttl=60,
            max_size=1000,
        )
        backend._client = mock_redis_client
        return backend

    def test_make_key(self, redis_backend: RedisCacheBackend):
        """키 생성 - prefix 추가"""
        key = redis_backend._make_key("mykey")
        assert key == "test_cache:mykey"

    def test_get_backend_name(self, redis_backend: RedisCacheBackend):
        """백엔드 이름"""
        assert redis_backend.get_backend_name() == "redis"

    def test_get_size(self, redis_backend: RedisCacheBackend):
        """크기 조회 (비동기 불가로 -1 반환)"""
        assert redis_backend.get_size() == -1

    def test_get_max_size(self, redis_backend: RedisCacheBackend):
        """최대 크기"""
        assert redis_backend.get_max_size() == 1000

    @pytest.mark.asyncio
    async def test_get_success(self, redis_backend: RedisCacheBackend, mock_redis_client):
        """Redis get 성공"""
        mock_redis_client.get.return_value = '{"data": "value1"}'

        result = await redis_backend.get("key1")
        assert result == {"data": "value1"}
        mock_redis_client.get.assert_called_once_with("test_cache:key1")

    @pytest.mark.asyncio
    async def test_get_miss(self, redis_backend: RedisCacheBackend, mock_redis_client):
        """Redis get 미스"""
        mock_redis_client.get.return_value = None

        result = await redis_backend.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_exception(self, redis_backend: RedisCacheBackend, mock_redis_client):
        """Redis get 예외"""
        mock_redis_client.get.side_effect = Exception("Connection error")

        result = await redis_backend.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_success(self, redis_backend: RedisCacheBackend, mock_redis_client):
        """Redis set 성공"""
        mock_redis_client.set.return_value = True

        result = await redis_backend.set("key1", {"data": "value1"}, ttl=120)
        assert result is True
        mock_redis_client.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_exception(self, redis_backend: RedisCacheBackend, mock_redis_client):
        """Redis set 예외"""
        mock_redis_client.set.side_effect = Exception("Connection error")

        result = await redis_backend.set("key1", {"data": "value1"})
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_success(self, redis_backend: RedisCacheBackend, mock_redis_client):
        """Redis delete 성공"""
        mock_redis_client.delete.return_value = 1

        result = await redis_backend.delete("key1")
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_not_found(self, redis_backend: RedisCacheBackend, mock_redis_client):
        """Redis delete - 키 없음"""
        mock_redis_client.delete.return_value = 0

        result = await redis_backend.delete("key1")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_exception(self, redis_backend: RedisCacheBackend, mock_redis_client):
        """Redis delete 예외"""
        mock_redis_client.delete.side_effect = Exception("Connection error")

        result = await redis_backend.delete("key1")
        assert result is False

    @pytest.mark.asyncio
    async def test_clear_success(self, redis_backend: RedisCacheBackend, mock_redis_client):
        """Redis clear 성공"""
        # SCAN 결과 시뮬레이션
        mock_redis_client.scan.side_effect = [
            (1, ["test_cache:key1", "test_cache:key2"]),
            (0, ["test_cache:key3"]),
        ]
        mock_redis_client.delete.return_value = 2

        result = await redis_backend.clear()
        assert result == 4  # 2 + 2 (두 번의 delete 호출)

    @pytest.mark.asyncio
    async def test_clear_exception(self, redis_backend: RedisCacheBackend, mock_redis_client):
        """Redis clear 예외"""
        mock_redis_client.scan.side_effect = Exception("Connection error")

        result = await redis_backend.clear()
        assert result == 0

    @pytest.mark.asyncio
    async def test_keys_success(self, redis_backend: RedisCacheBackend, mock_redis_client):
        """Redis keys 성공"""
        mock_redis_client.scan.side_effect = [
            (1, ["test_cache:key1", "test_cache:key2"]),
            (0, ["test_cache:key3"]),
        ]

        result = await redis_backend.keys("*")
        assert len(result) == 3
        assert "key1" in result
        assert "key2" in result
        assert "key3" in result

    @pytest.mark.asyncio
    async def test_keys_exception(self, redis_backend: RedisCacheBackend, mock_redis_client):
        """Redis keys 예외"""
        mock_redis_client.scan.side_effect = Exception("Connection error")

        result = await redis_backend.keys("*")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_client_initialization(self):
        """Redis 클라이언트 초기화"""
        backend = RedisCacheBackend(
            redis_url="redis://localhost:6379/0",
            prefix="test:",
        )
        assert backend._client is None

        # 실제 Redis 없이 테스트 - import만 확인
        with patch("redis.asyncio.from_url") as mock_from_url:
            mock_client = AsyncMock()
            mock_from_url.return_value = mock_client

            client = await backend._get_client()
            assert client is mock_client
            mock_from_url.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_client_connection_failure(self):
        """Redis 클라이언트 연결 실패"""
        backend = RedisCacheBackend(
            redis_url="redis://localhost:6379/0",
            prefix="test:",
        )

        with patch("redis.asyncio.from_url") as mock_from_url:
            mock_from_url.side_effect = Exception("Connection refused")

            with pytest.raises(Exception, match="Connection refused"):
                await backend._get_client()


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

    def test_cache_key_different_search_type(self, cache_service: SearchCacheService):
        """캐시 키 생성 - 다른 search_type은 다른 키"""
        key1 = cache_service.get_cache_key(query="테스트", search_type="hybrid")
        key2 = cache_service.get_cache_key(query="테스트", search_type="semantic")
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
    async def test_delete(
        self,
        cache_service: SearchCacheService,
        sample_search_result: Dict[str, Any],
    ):
        """특정 키 삭제"""
        key = cache_service.get_cache_key(query="테스트")
        await cache_service.set(key, sample_search_result)

        # 삭제
        success = await cache_service.delete(key)
        assert success is True

        # 확인
        result = await cache_service.get(key)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, cache_service: SearchCacheService):
        """존재하지 않는 키 삭제"""
        success = await cache_service.delete("nonexistent_key")
        assert success is False

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
        assert stats.last_reset != ""

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

    def test_init_with_redis_url(self):
        """Redis URL로 초기화"""
        # Mock Redis import
        with patch.dict("sys.modules", {"redis.asyncio": MagicMock()}):
            cache = SearchCacheService(
                redis_url="redis://localhost:6379/0",
                ttl=120,
                max_size=500,
            )
            assert cache._stats.backend == "redis"

    def test_init_without_redis_url(self):
        """Redis URL 없이 초기화 (인메모리 폴백)"""
        cache = SearchCacheService(
            redis_url=None,
            ttl=120,
            max_size=500,
        )
        assert cache._stats.backend == "in_memory_lru"

    def test_get_stats_updates_size(self, cache_service: SearchCacheService):
        """get_stats가 현재 크기를 업데이트하는지 확인"""
        stats = cache_service.get_stats()
        assert stats.size == 0
        assert stats.max_size == 100
        assert stats.backend == "in_memory_lru"


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

    @pytest.mark.asyncio
    async def test_multiple_eviction(self, small_cache_service: SearchCacheService):
        """여러 항목 eviction"""
        await small_cache_service.set("k1", {"v": 1})
        await small_cache_service.set("k2", {"v": 2})
        await small_cache_service.set("k3", {"v": 3})

        # 2개 더 추가 -> k1, k2 삭제
        await small_cache_service.set("k4", {"v": 4})
        await small_cache_service.set("k5", {"v": 5})

        assert await small_cache_service.get("k1") is None
        assert await small_cache_service.get("k2") is None
        assert await small_cache_service.get("k3") is not None
        assert await small_cache_service.get("k4") is not None
        assert await small_cache_service.get("k5") is not None


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

    @pytest.mark.asyncio
    async def test_nested_filters(self, cache_service: SearchCacheService):
        """중첩된 필터 처리"""
        filters = {
            "level1": {
                "level2": {
                    "level3": "value"
                }
            },
            "array": [1, 2, 3],
        }
        key = cache_service.get_cache_key(query="test", filters=filters)

        await cache_service.set(key, {"filters": filters})
        result = await cache_service.get(key)
        assert result is not None
        assert result["filters"] == filters

    @pytest.mark.asyncio
    async def test_filter_order_independence(self, cache_service: SearchCacheService):
        """필터 순서 독립성"""
        filters1 = {"a": 1, "b": 2}
        filters2 = {"b": 2, "a": 1}

        key1 = cache_service.get_cache_key(query="test", filters=filters1)
        key2 = cache_service.get_cache_key(query="test", filters=filters2)

        # 필터가 정렬되어 같은 키 생성
        assert key1 == key2


# ---------------------------------------------------------------------------
# Concurrent Access Tests
# ---------------------------------------------------------------------------

class TestConcurrentAccess:
    """동시 접근 테스트"""

    @pytest.mark.asyncio
    async def test_concurrent_set(self, cache_service: SearchCacheService):
        """동시 set 작업"""
        async def set_item(i):
            key = cache_service.get_cache_key(query=f"query{i}")
            await cache_service.set(key, {"value": i})
            return True

        # 100개 동시 저장
        results = await asyncio.gather(*[set_item(i) for i in range(100)])
        assert all(results)
        assert cache_service.get_stats().size == 100

    @pytest.mark.asyncio
    async def test_concurrent_get(self, cache_service: SearchCacheService):
        """동시 get 작업"""
        # 미리 데이터 저장
        for i in range(10):
            key = cache_service.get_cache_key(query=f"query{i}")
            await cache_service.set(key, {"value": i})

        async def get_item(i):
            key = cache_service.get_cache_key(query=f"query{i}")
            return await cache_service.get(key)

        # 동시 조회
        results = await asyncio.gather(*[get_item(i % 10) for i in range(100)])
        assert all(r is not None for r in results)

    @pytest.mark.asyncio
    async def test_concurrent_set_get(self, cache_service: SearchCacheService):
        """동시 set/get 혼합 작업"""
        async def mixed_operation(i):
            key = cache_service.get_cache_key(query=f"query{i % 10}")
            if i % 2 == 0:
                await cache_service.set(key, {"value": i})
            else:
                await cache_service.get(key)
            return True

        results = await asyncio.gather(*[mixed_operation(i) for i in range(50)])
        assert all(results)


# ---------------------------------------------------------------------------
# Stats Tests
# ---------------------------------------------------------------------------

class TestStatsTracking:
    """통계 추적 상세 테스트"""

    @pytest.mark.asyncio
    async def test_hit_miss_tracking(self, cache_service: SearchCacheService):
        """히트/미스 추적"""
        # 미스 3회
        for i in range(3):
            key = cache_service.get_cache_key(query=f"query{i}")
            await cache_service.get(key)

        stats = cache_service.get_stats()
        assert stats.misses == 3
        assert stats.hits == 0

        # 저장 후 히트 2회
        key = cache_service.get_cache_key(query="query0")
        await cache_service.set(key, {"data": "value"})
        await cache_service.get(key)
        await cache_service.get(key)

        stats = cache_service.get_stats()
        assert stats.misses == 3
        assert stats.hits == 2
        assert stats.hit_rate == 2 / 5

    @pytest.mark.asyncio
    async def test_stats_after_clear(self, cache_service: SearchCacheService):
        """clear 후 통계"""
        # 데이터 저장
        for i in range(5):
            key = cache_service.get_cache_key(query=f"query{i}")
            await cache_service.set(key, {"value": i})

        # 통계 기록
        for i in range(5):
            key = cache_service.get_cache_key(query=f"query{i}")
            await cache_service.get(key)

        stats = cache_service.get_stats()
        assert stats.hits == 5
        assert stats.size == 5

        # clear
        await cache_service.invalidate(pattern=None)

        stats = cache_service.get_stats()
        assert stats.hits == 5  # 통계는 유지
        assert stats.size == 0  # 크기만 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
