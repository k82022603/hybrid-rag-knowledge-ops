"""
캐시 관리 API 엔드포인트 (STORY-060)

검색 캐시 통계 조회 및 관리 API
- GET /stats: 캐시 통계 조회
- DELETE /clear: 캐시 전체 삭제
- DELETE /invalidate: 패턴 기반 캐시 무효화
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.routes.auth import get_current_user
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------


class CacheStatsResponse(BaseModel):
    """캐시 통계 응답 모델"""

    hits: int = Field(description="캐시 히트 수")
    misses: int = Field(description="캐시 미스 수")
    total_requests: int = Field(description="총 요청 수")
    hit_rate: float = Field(description="캐시 히트율 (0.0 ~ 1.0)")
    miss_rate: float = Field(description="캐시 미스율 (0.0 ~ 1.0)")
    size: int = Field(description="현재 캐시 크기 (-1: 측정 불가)")
    max_size: int = Field(description="최대 캐시 크기")
    backend: str = Field(description="캐시 백엔드 유형")
    last_reset: str = Field(description="마지막 통계 초기화 시간")
    enabled: bool = Field(description="캐시 활성화 여부")
    ttl_seconds: int = Field(description="기본 TTL (초)")


class CacheInvalidateRequest(BaseModel):
    """캐시 무효화 요청 모델"""

    pattern: Optional[str] = Field(
        default=None,
        description="삭제할 키 패턴 (예: 'prefix*'), None이면 전체 삭제",
    )


class CacheInvalidateResponse(BaseModel):
    """캐시 무효화 응답 모델"""

    deleted_count: int = Field(description="삭제된 캐시 엔트리 수")
    pattern: Optional[str] = Field(description="적용된 패턴")
    message: str = Field(description="결과 메시지")


class CacheClearResponse(BaseModel):
    """캐시 전체 삭제 응답 모델"""

    deleted_count: int = Field(description="삭제된 캐시 엔트리 수")
    message: str = Field(description="결과 메시지")


class CacheStatusResponse(BaseModel):
    """캐시 상태 응답 모델"""

    enabled: bool = Field(description="캐시 활성화 여부")
    backend: str = Field(description="캐시 백엔드 유형")
    status: str = Field(description="상태 (available/disabled/error)")
    message: str = Field(description="상태 메시지")


# ---------------------------------------------------------------------------
# Cache Stats
# ---------------------------------------------------------------------------


@router.get(
    "/stats",
    response_model=CacheStatsResponse,
    summary="캐시 통계 조회",
    description="검색 캐시 히트/미스율, 크기 등 통계 정보 조회 (STORY-060)",
)
async def get_cache_stats(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> CacheStatsResponse:
    """
    캐시 통계 조회

    캐시 히트율, 미스율, 현재 크기 등의 통계 정보를 반환합니다.

    Returns:
        캐시 통계 정보
    """
    logger.info("Cache stats requested")

    if not settings.search_cache_enabled:
        return CacheStatsResponse(
            hits=0,
            misses=0,
            total_requests=0,
            hit_rate=0.0,
            miss_rate=0.0,
            size=0,
            max_size=0,
            backend="none",
            last_reset="",
            enabled=False,
            ttl_seconds=0,
        )

    try:
        from app.services.cache_service import get_cache_service

        cache_service = get_cache_service()
        stats = await cache_service.get_stats()

        return CacheStatsResponse(
            hits=stats.hits,
            misses=stats.misses,
            total_requests=stats.total_requests,
            hit_rate=round(stats.hit_rate, 4),
            miss_rate=round(stats.miss_rate, 4),
            size=stats.size,
            max_size=stats.max_size,
            backend=stats.backend,
            last_reset=stats.last_reset,
            enabled=True,
            ttl_seconds=settings.search_cache_ttl,
        )

    except Exception as e:
        logger.exception(f"Failed to get cache stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"캐시 통계 조회 실패: {str(e)}",
        )


# ---------------------------------------------------------------------------
# Cache Clear
# ---------------------------------------------------------------------------


@router.delete(
    "/clear",
    response_model=CacheClearResponse,
    summary="캐시 전체 삭제",
    description="모든 검색 캐시를 삭제합니다. 주의: 되돌릴 수 없습니다.",
)
async def clear_cache(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> CacheClearResponse:
    """
    캐시 전체 삭제

    모든 검색 캐시 엔트리를 삭제합니다.

    Returns:
        삭제 결과
    """
    logger.info(f"Cache clear requested by user: {current_user.get('sub')}")

    if not settings.search_cache_enabled:
        return CacheClearResponse(
            deleted_count=0,
            message="캐시가 비활성화되어 있습니다",
        )

    try:
        from app.services.cache_service import get_cache_service

        cache_service = get_cache_service()
        deleted_count = await cache_service.invalidate(pattern=None)

        logger.info(f"Cache cleared: {deleted_count} entries deleted")

        return CacheClearResponse(
            deleted_count=deleted_count,
            message=f"캐시가 성공적으로 삭제되었습니다: {deleted_count}개 엔트리",
        )

    except Exception as e:
        logger.exception(f"Failed to clear cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"캐시 삭제 실패: {str(e)}",
        )


# ---------------------------------------------------------------------------
# Cache Invalidate
# ---------------------------------------------------------------------------


@router.delete(
    "/invalidate",
    response_model=CacheInvalidateResponse,
    summary="캐시 무효화",
    description="패턴에 매칭되는 캐시 엔트리를 삭제합니다",
)
async def invalidate_cache(
    pattern: Optional[str] = Query(
        default=None,
        description="삭제할 키 패턴 (예: 'prefix*')",
    ),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> CacheInvalidateResponse:
    """
    캐시 무효화

    패턴에 매칭되는 캐시 엔트리를 삭제합니다.
    패턴이 없으면 전체 삭제와 동일합니다.

    Args:
        pattern: 삭제할 키 패턴

    Returns:
        삭제 결과
    """
    logger.info(f"Cache invalidate requested - pattern: {pattern}")

    if not settings.search_cache_enabled:
        return CacheInvalidateResponse(
            deleted_count=0,
            pattern=pattern,
            message="캐시가 비활성화되어 있습니다",
        )

    try:
        from app.services.cache_service import get_cache_service

        cache_service = get_cache_service()
        deleted_count = await cache_service.invalidate(pattern=pattern)

        logger.info(f"Cache invalidated: {deleted_count} entries deleted for pattern '{pattern}'")

        return CacheInvalidateResponse(
            deleted_count=deleted_count,
            pattern=pattern,
            message=f"캐시 무효화 완료: {deleted_count}개 엔트리 삭제",
        )

    except Exception as e:
        logger.exception(f"Failed to invalidate cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"캐시 무효화 실패: {str(e)}",
        )


# ---------------------------------------------------------------------------
# Cache Status
# ---------------------------------------------------------------------------


@router.get(
    "/status",
    response_model=CacheStatusResponse,
    summary="캐시 상태 확인",
    description="캐시 서비스 상태 및 백엔드 정보 조회",
)
async def get_cache_status(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> CacheStatusResponse:
    """
    캐시 상태 확인

    캐시 서비스 활성화 여부 및 백엔드 상태를 확인합니다.

    Returns:
        캐시 상태 정보
    """
    if not settings.search_cache_enabled:
        return CacheStatusResponse(
            enabled=False,
            backend="none",
            status="disabled",
            message="캐시가 설정에서 비활성화되어 있습니다",
        )

    try:
        from app.services.cache_service import get_cache_service

        cache_service = get_cache_service()
        stats = await cache_service.get_stats()

        return CacheStatusResponse(
            enabled=True,
            backend=stats.backend,
            status="available",
            message=f"캐시 서비스 정상 작동 중 ({stats.backend})",
        )

    except Exception as e:
        logger.warning(f"Cache status check failed: {e}")
        return CacheStatusResponse(
            enabled=True,
            backend="unknown",
            status="error",
            message=f"캐시 서비스 오류: {str(e)}",
        )


# ---------------------------------------------------------------------------
# Reset Stats
# ---------------------------------------------------------------------------


@router.post(
    "/stats/reset",
    summary="캐시 통계 초기화",
    description="캐시 통계 (히트/미스 카운터)를 초기화합니다",
)
async def reset_cache_stats(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    캐시 통계 초기화

    히트/미스 카운터를 0으로 초기화합니다.
    캐시 데이터는 삭제되지 않습니다.

    Returns:
        초기화 결과
    """
    logger.info(f"Cache stats reset requested by user: {current_user.get('sub')}")

    if not settings.search_cache_enabled:
        return {
            "success": False,
            "message": "캐시가 비활성화되어 있습니다",
        }

    try:
        from app.services.cache_service import get_cache_service

        cache_service = get_cache_service()
        cache_service.reset_stats()

        return {
            "success": True,
            "message": "캐시 통계가 초기화되었습니다",
        }

    except Exception as e:
        logger.exception(f"Failed to reset cache stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"캐시 통계 초기화 실패: {str(e)}",
        )
