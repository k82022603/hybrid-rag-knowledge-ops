"""
검색 결과 캐싱 서비스 모듈 (STORY-060)

검색 결과 캐싱으로 응답 속도 향상 및 LLM 비용 절감을 제공합니다.

기능:
- Redis 연결 시: redis-py 기반 분산 캐시
- Redis 없음 시: cachetools LRU 캐시로 폴백
- 캐시 키 생성: SHA256 해싱 (query + filters)
- TTL 기반 자동 만료
- 캐시 무효화 (패턴 기반, 전체 클리어)
- 캐시 통계 (히트/미스율, 크기)
"""

import asyncio
import hashlib
import json
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, List, Optional, Union

from app.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Cache Statistics
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
# Cache Backend Interface
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
# LRU In-Memory Cache Backend
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

    Attributes:
        max_size: 최대 캐시 엔트리 수
        default_ttl: 기본 TTL (초)
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """
        초기화

        Args:
            max_size: 최대 캐시 엔트리 수 (기본 1000)
            default_ttl: 기본 TTL (초, 기본 1시간)
        """
        self._cache: OrderedDict[str, LRUCacheEntry] = OrderedDict()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = Lock()

        logger.info(f"InMemoryLRUCache initialized - max_size={max_size}, ttl={default_ttl}s")

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        캐시에서 조회

        Args:
            key: 캐시 키

        Returns:
            캐시된 값 또는 None (만료/미존재)
        """
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
        """
        캐시에 저장

        Args:
            key: 캐시 키
            value: 저장할 값
            ttl: TTL (초), None이면 기본값 사용

        Returns:
            저장 성공 여부
        """
        effective_ttl = ttl if ttl is not None else self._default_ttl

        with self._lock:
            # 이미 존재하면 삭제 (순서 갱신 위해)
            if key in self._cache:
                del self._cache[key]

            # 용량 초과 시 가장 오래된 항목 제거 (LRU eviction)
            while len(self._cache) >= self._max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                logger.debug(f"LRU eviction: {oldest_key[:20]}...")

            # 새 엔트리 추가
            entry = LRUCacheEntry(
                value=value,
                expires_at=time.time() + effective_ttl,
            )
            self._cache[key] = entry
            return True

    async def delete(self, key: str) -> bool:
        """
        캐시에서 삭제

        Args:
            key: 캐시 키

        Returns:
            삭제 성공 여부 (키 존재 시 True)
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear(self) -> int:
        """
        캐시 전체 삭제

        Returns:
            삭제된 항목 수
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    async def keys(self, pattern: str = "*") -> List[str]:
        """
        패턴에 매칭되는 키 목록 조회

        단순 와일드카드 패턴만 지원 (*, prefix*)

        Args:
            pattern: 검색 패턴

        Returns:
            매칭되는 키 목록
        """
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
        """현재 캐시 크기"""
        return len(self._cache)

    def get_max_size(self) -> int:
        """최대 캐시 크기"""
        return self._max_size

    def get_backend_name(self) -> str:
        """백엔드 이름"""
        return "in_memory_lru"


# ---------------------------------------------------------------------------
# Redis Cache Backend
# ---------------------------------------------------------------------------


class RedisCacheBackend(CacheBackend):
    """
    Redis 캐시 백엔드

    분산 환경에서 공유 캐시를 제공합니다.

    Attributes:
        redis_url: Redis 연결 URL
        prefix: 캐시 키 접두사
        default_ttl: 기본 TTL (초)
    """

    def __init__(
        self,
        redis_url: str,
        prefix: str = "search_cache:",
        default_ttl: int = 3600,
        max_size: int = 10000,
    ):
        """
        초기화

        Args:
            redis_url: Redis 연결 URL
            prefix: 캐시 키 접두사
            default_ttl: 기본 TTL (초)
            max_size: 최대 캐시 크기 (참조용, Redis는 자체 메모리 관리)
        """
        self._redis_url = redis_url
        self._prefix = prefix
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._client = None

        logger.info(f"RedisCacheBackend initialized - url={redis_url[:30]}..., prefix={prefix}")

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
                logger.info("Redis client connected")
            except Exception as e:
                logger.error(f"Redis connection failed: {e}")
                raise
        return self._client

    def _make_key(self, key: str) -> str:
        """접두사가 붙은 전체 키 생성"""
        return f"{self._prefix}{key}"

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        캐시에서 조회

        Args:
            key: 캐시 키

        Returns:
            캐시된 값 또는 None
        """
        try:
            client = await self._get_client()
            full_key = self._make_key(key)
            data = await client.get(full_key)

            if data is None:
                return None

            return json.loads(data)

        except Exception as e:
            logger.warning(f"Redis get failed: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> bool:
        """
        캐시에 저장

        Args:
            key: 캐시 키
            value: 저장할 값
            ttl: TTL (초)

        Returns:
            저장 성공 여부
        """
        try:
            effective_ttl = ttl if ttl is not None else self._default_ttl
            client = await self._get_client()
            full_key = self._make_key(key)
            data = json.dumps(value, ensure_ascii=False)

            await client.set(full_key, data, ex=effective_ttl)
            return True

        except Exception as e:
            logger.warning(f"Redis set failed: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        캐시에서 삭제

        Args:
            key: 캐시 키

        Returns:
            삭제 성공 여부
        """
        try:
            client = await self._get_client()
            full_key = self._make_key(key)
            result = await client.delete(full_key)
            return result > 0

        except Exception as e:
            logger.warning(f"Redis delete failed: {e}")
            return False

    async def clear(self) -> int:
        """
        캐시 전체 삭제 (prefix 범위 내)

        Returns:
            삭제된 항목 수
        """
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
            logger.warning(f"Redis clear failed: {e}")
            return 0

    async def keys(self, pattern: str = "*") -> List[str]:
        """
        패턴에 매칭되는 키 목록 조회

        Args:
            pattern: 검색 패턴

        Returns:
            매칭되는 키 목록 (prefix 제외)
        """
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
            logger.warning(f"Redis keys failed: {e}")
            return []

    def get_size(self) -> int:
        """현재 캐시 크기 (비동기 호출 불가, 추정치 반환)"""
        # 동기 컨텍스트에서 호출될 수 있으므로 -1 반환
        return -1

    def get_max_size(self) -> int:
        """최대 캐시 크기 (Redis는 메모리 기반)"""
        return self._max_size

    def get_backend_name(self) -> str:
        """백엔드 이름"""
        return "redis"


# ---------------------------------------------------------------------------
# SearchCacheService
# ---------------------------------------------------------------------------


class SearchCacheService:
    """
    검색 결과 캐싱 서비스

    Hybrid Search 결과를 캐싱하여 응답 속도를 향상하고 LLM 비용을 절감합니다.

    Features:
        - Redis/인메모리 자동 폴백
        - 쿼리 + 필터 기반 캐시 키 생성 (SHA256)
        - TTL 기반 자동 만료
        - 패턴 기반 캐시 무효화
        - 캐시 통계 (히트/미스율)

    Attributes:
        backend: 캐시 백엔드 (Redis 또는 InMemory)
        ttl: 기본 TTL (초)
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        ttl: int = 3600,
        max_size: int = 1000,
        prefix: str = "search_cache:",
    ):
        """
        초기화

        Args:
            redis_url: Redis 연결 URL (None이면 인메모리 캐시)
            ttl: 기본 캐시 TTL (초, 기본 1시간)
            max_size: 최대 캐시 엔트리 수 (인메모리 기준)
            prefix: Redis 키 접두사
        """
        self._ttl = ttl
        self._max_size = max_size
        self._prefix = prefix

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
                )
                self._stats.backend = "redis"
                logger.info(f"SearchCacheService using Redis backend")
            except Exception as e:
                logger.warning(f"Redis init failed, falling back to in-memory: {e}")
                self._backend = InMemoryLRUCache(max_size=max_size, default_ttl=ttl)
                self._stats.backend = "in_memory_lru"
        else:
            self._backend = InMemoryLRUCache(max_size=max_size, default_ttl=ttl)
            self._stats.backend = "in_memory_lru"
            logger.info("SearchCacheService using in-memory LRU backend")

    def get_cache_key(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 10,
        search_type: str = "hybrid",
        use_graph: bool = True,
        use_vector: bool = True,
    ) -> str:
        """
        검색 쿼리를 캐시 키로 변환

        쿼리, 필터, top_k, 검색 타입, use_graph/use_vector를
        조합하여 SHA256 해시 생성

        Args:
            query: 검색 쿼리
            filters: 필터 조건
            top_k: 반환 결과 수
            search_type: 검색 유형 (hybrid, semantic, keyword)
            use_graph: Graph 검색 사용 여부
            use_vector: Vector 검색 사용 여부

        Returns:
            캐시 키 (SHA256 해시)
        """
        # 정규화: 앞뒤 공백 제거, 소문자 변환
        normalized_query = query.strip().lower()

        # 필터 정규화: 정렬된 JSON (None은 빈 딕셔너리)
        normalized_filters = json.dumps(
            filters or {},
            sort_keys=True,
            ensure_ascii=False,
        )

        # 캐시 키 구성요소 조합 (use_graph/use_vector 포함)
        key_components = (
            f"{search_type}:{normalized_query}:{normalized_filters}"
            f":{top_k}:g={use_graph}:v={use_vector}"
        )

        # SHA256 해싱
        cache_key = hashlib.sha256(key_components.encode("utf-8")).hexdigest()

        logger.debug(f"Cache key generated: {cache_key[:16]}... for query: '{query[:30]}...'")
        return cache_key

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        캐시에서 조회

        Args:
            key: 캐시 키

        Returns:
            캐시된 검색 결과 또는 None
        """
        result = await self._backend.get(key)

        if result is not None:
            self._stats.hits += 1
            logger.debug(f"Cache HIT: {key[:16]}...")
        else:
            self._stats.misses += 1
            logger.debug(f"Cache MISS: {key[:16]}...")

        return result

    async def set(
        self,
        key: str,
        value: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> bool:
        """
        캐시에 저장

        Args:
            key: 캐시 키
            value: 저장할 검색 결과
            ttl: TTL (초), None이면 기본값 사용

        Returns:
            저장 성공 여부
        """
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
            logger.debug(f"Cache SET: {key[:16]}..., ttl={effective_ttl}s")
        else:
            logger.warning(f"Cache SET failed: {key[:16]}...")

        return success

    async def invalidate(self, pattern: Optional[str] = None) -> int:
        """
        캐시 무효화

        Args:
            pattern: 삭제할 키 패턴 (None이면 전체 삭제)

        Returns:
            삭제된 항목 수
        """
        if pattern is None:
            # 전체 클리어
            deleted = await self._backend.clear()
            logger.info(f"Cache cleared: {deleted} entries")
        else:
            # 패턴 매칭 삭제
            keys = await self._backend.keys(pattern)
            deleted = 0
            for key in keys:
                if await self._backend.delete(key):
                    deleted += 1
            logger.info(f"Cache invalidated: {deleted} entries matching '{pattern}'")

        self._stats.size = self._backend.get_size()
        return deleted

    async def delete(self, key: str) -> bool:
        """
        특정 키 삭제

        Args:
            key: 캐시 키

        Returns:
            삭제 성공 여부
        """
        success = await self._backend.delete(key)
        if success:
            self._stats.size = self._backend.get_size()
            logger.debug(f"Cache DELETE: {key[:16]}...")
        return success

    def get_stats(self) -> CacheStats:
        """
        캐시 통계 조회

        Returns:
            CacheStats 객체
        """
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
        logger.info("Cache stats reset")


# ---------------------------------------------------------------------------
# 싱글톤 인스턴스
# ---------------------------------------------------------------------------

_cache_service: Optional[SearchCacheService] = None


def get_cache_service(
    redis_url: Optional[str] = None,
    ttl: int = 3600,
    max_size: int = 1000,
) -> SearchCacheService:
    """
    SearchCacheService 인스턴스 반환 (싱글톤)

    Args:
        redis_url: Redis 연결 URL (처음 호출 시에만 적용)
        ttl: 캐시 TTL (초)
        max_size: 최대 캐시 크기

    Returns:
        SearchCacheService 인스턴스
    """
    global _cache_service
    if _cache_service is None:
        # 환경변수에서 Redis URL 확인
        from app.core.config import settings

        effective_redis_url = redis_url
        if effective_redis_url is None and settings.redis_host:
            # Redis 설정이 있으면 URL 구성
            password_part = f":{settings.redis_password}@" if settings.redis_password else ""
            effective_redis_url = (
                f"redis://{password_part}{settings.redis_host}:{settings.redis_port}"
                f"/{settings.redis_db}"
            )
            logger.info(f"Using Redis from settings: {settings.redis_host}:{settings.redis_port}")

        _cache_service = SearchCacheService(
            redis_url=effective_redis_url,
            ttl=ttl,
            max_size=max_size,
        )

    return _cache_service


def reset_cache_service() -> None:
    """캐시 서비스 인스턴스 리셋 (테스트용)"""
    global _cache_service
    _cache_service = None
    logger.info("Cache service instance reset")
