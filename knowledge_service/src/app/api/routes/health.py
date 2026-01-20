"""
Health Check 엔드포인트

시스템 상태 확인 및 의존성 체크
"""

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


class HealthResponse(BaseModel):
    """Health Check 응답 모델"""

    status: str = Field(description="서비스 상태 (healthy, degraded, unhealthy)")
    version: str = Field(description="서비스 버전")
    environment: str = Field(description="실행 환경")
    timestamp: str = Field(description="체크 시간 (ISO 8601)")
    dependencies: Dict[str, str] = Field(description="의존성 상태")


class ReadinessResponse(BaseModel):
    """Readiness Check 응답 모델"""

    ready: bool = Field(description="서비스 준비 상태")
    checks: Dict[str, bool] = Field(description="개별 체크 결과")


@router.get(
    "",
    response_model=HealthResponse,
    summary="Health Check",
    description="서비스 기본 상태 확인",
)
async def health_check() -> HealthResponse:
    """
    서비스 Health Check

    Returns:
        서비스 상태 정보
    """
    dependencies = await _check_dependencies()

    # 상태 결정
    if all(v == "healthy" for v in dependencies.values()):
        status_value = "healthy"
    elif any(v == "unhealthy" for v in dependencies.values()):
        status_value = "degraded"
    else:
        status_value = "healthy"

    return HealthResponse(
        status=status_value,
        version=settings.app_version,
        environment=settings.environment,
        timestamp=datetime.utcnow().isoformat() + "Z",
        dependencies=dependencies,
    )


@router.get(
    "/live",
    status_code=status.HTTP_200_OK,
    summary="Liveness Probe",
    description="Kubernetes Liveness Probe용 엔드포인트",
)
async def liveness() -> Dict[str, str]:
    """
    Liveness Probe

    서비스가 살아있는지 확인 (Kubernetes용)
    """
    return {"status": "alive"}


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness Probe",
    description="Kubernetes Readiness Probe용 엔드포인트",
)
async def readiness() -> ReadinessResponse:
    """
    Readiness Probe

    서비스가 트래픽을 받을 준비가 되었는지 확인 (Kubernetes용)
    """
    checks = {
        "config_loaded": True,
        "llm_api_key_set": settings.deepseek_api_key is not None,
    }

    # TODO: 실제 DB 연결 체크 추가
    # checks["elasticsearch"] = await _check_elasticsearch()
    # checks["neo4j"] = await _check_neo4j()

    return ReadinessResponse(
        ready=all(checks.values()),
        checks=checks,
    )


async def _check_dependencies() -> Dict[str, str]:
    """
    의존성 상태 체크

    Returns:
        의존성별 상태 (healthy, unhealthy, unknown)
    """
    results: Dict[str, str] = {}

    # LLM API 키 확인
    results["deepseek_api"] = (
        "healthy" if settings.deepseek_api_key else "unhealthy"
    )

    # TODO: 실제 연결 체크 구현
    # Elasticsearch
    results["elasticsearch"] = "unknown"  # 연결 미구현

    # Neo4j
    results["neo4j"] = "unknown"  # 연결 미구현

    # PostgreSQL
    results["postgresql"] = "unknown"  # 연결 미구현

    return results
