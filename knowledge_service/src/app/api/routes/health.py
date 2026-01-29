"""
Health Check 엔드포인트

시스템 상태 확인 및 의존성 체크
Circuit Breaker 상태 모니터링 (STORY-061)
"""

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from app.core.circuit_breaker import get_circuit_breaker_registry
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


# ---------------------------------------------------------------------------
# Circuit Breaker 모니터링 (STORY-061)
# ---------------------------------------------------------------------------


class CircuitBreakerStatusResponse(BaseModel):
    """Circuit Breaker 상태 응답 모델"""

    name: str = Field(description="Circuit Breaker 이름")
    state: str = Field(description="현재 상태 (closed, open, half_open)")
    failure_count: int = Field(description="현재 연속 실패 횟수")
    success_count: int = Field(description="HALF_OPEN 상태에서 성공 횟수")
    total_calls: int = Field(description="총 호출 횟수")
    total_successes: int = Field(description="총 성공 횟수")
    total_failures: int = Field(description="총 실패 횟수")
    success_rate: float = Field(description="성공률 (%)")
    last_failure_time: Optional[str] = Field(
        default=None, description="마지막 실패 시간 (ISO 8601)"
    )
    last_state_change: str = Field(description="마지막 상태 변경 시간 (ISO 8601)")
    open_count: int = Field(description="Circuit이 OPEN된 총 횟수")


class CircuitBreakerAllStatusResponse(BaseModel):
    """모든 Circuit Breaker 상태 응답 모델"""

    circuit_breakers: Dict[str, Dict[str, Any]] = Field(
        description="모든 Circuit Breaker 메트릭"
    )
    total_count: int = Field(description="등록된 Circuit Breaker 수")
    healthy_count: int = Field(description="CLOSED 상태인 Circuit Breaker 수")
    degraded_count: int = Field(description="OPEN/HALF_OPEN 상태인 Circuit Breaker 수")


@router.get(
    "/circuit-breaker",
    response_model=CircuitBreakerAllStatusResponse,
    summary="모든 Circuit Breaker 상태",
    description="등록된 모든 Circuit Breaker의 상태를 조회합니다.",
)
async def get_all_circuit_breaker_status() -> CircuitBreakerAllStatusResponse:
    """
    모든 Circuit Breaker 상태 조회

    Returns:
        모든 Circuit Breaker의 현재 상태 및 메트릭
    """
    registry = get_circuit_breaker_registry()
    all_metrics = registry.get_all_metrics()

    healthy_count = sum(
        1 for m in all_metrics.values() if m.get("state") == "closed"
    )
    degraded_count = len(all_metrics) - healthy_count

    return CircuitBreakerAllStatusResponse(
        circuit_breakers=all_metrics,
        total_count=len(all_metrics),
        healthy_count=healthy_count,
        degraded_count=degraded_count,
    )


@router.get(
    "/circuit-breaker/{name}",
    response_model=CircuitBreakerStatusResponse,
    summary="특정 Circuit Breaker 상태",
    description="특정 Circuit Breaker의 상세 상태를 조회합니다.",
    responses={
        404: {"description": "Circuit Breaker를 찾을 수 없음"},
    },
)
async def get_circuit_breaker_status(name: str) -> CircuitBreakerStatusResponse:
    """
    특정 Circuit Breaker 상태 조회

    Args:
        name: Circuit Breaker 이름

    Returns:
        해당 Circuit Breaker의 현재 상태 및 메트릭
    """
    from fastapi import HTTPException

    registry = get_circuit_breaker_registry()
    breaker = registry.get(name)

    if breaker is None:
        raise HTTPException(
            status_code=404,
            detail=f"Circuit Breaker '{name}'을(를) 찾을 수 없습니다",
        )

    metrics = breaker.metrics.to_dict()

    return CircuitBreakerStatusResponse(
        name=name,
        state=metrics["state"],
        failure_count=metrics["failure_count"],
        success_count=metrics["success_count"],
        total_calls=metrics["total_calls"],
        total_successes=metrics["total_successes"],
        total_failures=metrics["total_failures"],
        success_rate=metrics["success_rate"],
        last_failure_time=metrics["last_failure_time"],
        last_state_change=metrics["last_state_change"],
        open_count=metrics["open_count"],
    )
