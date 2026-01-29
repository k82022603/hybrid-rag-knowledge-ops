"""
Circuit Breaker 패턴 구현

AI Service 장애 시 graceful degradation을 위한 Circuit Breaker 패턴입니다.

STORY-061: Circuit Breaker 패턴 구현

Circuit Breaker States:
    - CLOSED: 정상 상태, 요청이 통과됨
    - OPEN: 차단 상태, 즉시 실패 반환 (fallback)
    - HALF_OPEN: 테스트 상태, 제한된 요청만 허용

Features:
    - 실패 임계값 기반 상태 전이
    - 복구 타임아웃 후 자동 테스트
    - Fallback 전략 지원
    - 상태 모니터링 및 메트릭
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, Generic, Optional, TypeVar

from app.core.exceptions import KnowledgeServiceError
from app.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Enums & Types
# ---------------------------------------------------------------------------


class CircuitState(Enum):
    """Circuit Breaker 상태"""

    CLOSED = "closed"  # 정상: 요청 통과
    OPEN = "open"  # 차단: 즉시 실패
    HALF_OPEN = "half_open"  # 테스트: 제한적 요청


T = TypeVar("T")  # 반환 타입


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class CircuitBreakerError(KnowledgeServiceError):
    """Circuit Breaker 관련 예외"""

    def __init__(
        self,
        message: str = "Circuit Breaker가 열려 있습니다",
        service_name: str = "unknown",
        state: CircuitState = CircuitState.OPEN,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="CIRCUIT_BREAKER_OPEN",
            status_code=503,  # Service Unavailable
            details={
                **(details or {}),
                "service": service_name,
                "circuit_state": state.value,
            },
        )


class CircuitBreakerOpenError(CircuitBreakerError):
    """Circuit이 열려서 요청이 차단된 경우"""

    def __init__(
        self,
        service_name: str,
        retry_after_seconds: Optional[int] = None,
    ):
        super().__init__(
            message=f"{service_name} 서비스가 일시적으로 사용 불가합니다. 잠시 후 다시 시도해주세요.",
            service_name=service_name,
            state=CircuitState.OPEN,
            details={"retry_after_seconds": retry_after_seconds},
        )


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class CircuitBreakerConfig:
    """Circuit Breaker 설정"""

    # 실패 임계값 (연속 실패 횟수)
    failure_threshold: int = 5

    # 복구 타임아웃 (초) - OPEN 상태 유지 시간
    recovery_timeout: int = 30

    # HALF_OPEN 상태에서 허용할 최대 호출 수
    half_open_max_calls: int = 3

    # 성공 임계값 (HALF_OPEN에서 CLOSED로 전이 조건)
    success_threshold: int = 2

    # 예외 필터: True를 반환하면 실패로 간주
    failure_predicate: Optional[Callable[[Exception], bool]] = None

    @staticmethod
    def default_failure_predicate(exc: Exception) -> bool:
        """기본 실패 판정: 대부분의 예외를 실패로 간주"""
        # 일부 예외는 실패로 간주하지 않음
        if isinstance(exc, (ValueError, TypeError)):
            return False
        return True


@dataclass
class CircuitBreakerMetrics:
    """Circuit Breaker 메트릭"""

    # 현재 상태
    state: CircuitState = CircuitState.CLOSED

    # 실패 카운터
    failure_count: int = 0

    # 성공 카운터 (HALF_OPEN 상태에서만 사용)
    success_count: int = 0

    # HALF_OPEN에서 진행 중인 호출 수
    half_open_calls: int = 0

    # 마지막 실패 시간
    last_failure_time: Optional[datetime] = None

    # 마지막 상태 변경 시간
    last_state_change: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # 총 호출 수
    total_calls: int = 0

    # 총 성공 수
    total_successes: int = 0

    # 총 실패 수
    total_failures: int = 0

    # Circuit이 OPEN된 총 횟수
    open_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """메트릭을 딕셔너리로 변환"""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "half_open_calls": self.half_open_calls,
            "last_failure_time": (
                self.last_failure_time.isoformat() if self.last_failure_time else None
            ),
            "last_state_change": self.last_state_change.isoformat(),
            "total_calls": self.total_calls,
            "total_successes": self.total_successes,
            "total_failures": self.total_failures,
            "open_count": self.open_count,
            "success_rate": (
                round(self.total_successes / self.total_calls * 100, 2)
                if self.total_calls > 0
                else 0.0
            ),
        }


# ---------------------------------------------------------------------------
# Circuit Breaker 구현
# ---------------------------------------------------------------------------


class CircuitBreaker(Generic[T]):
    """
    비동기 Circuit Breaker 구현

    외부 서비스 호출 시 장애 전파를 방지하고 빠른 실패(fail-fast)를 제공합니다.

    Usage:
        breaker = CircuitBreaker(
            name="llm-service",
            config=CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=30,
            ),
        )

        try:
            result = await breaker.call(my_async_function, arg1, arg2)
        except CircuitBreakerOpenError:
            # Fallback 처리
            result = default_value
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        fallback: Optional[Callable[..., Awaitable[T]]] = None,
    ):
        """
        초기화

        Args:
            name: Circuit Breaker 이름 (서비스 식별용)
            config: 설정 객체
            fallback: 기본 fallback 함수 (OPEN 상태일 때 호출)
        """
        self._name = name
        self._config = config or CircuitBreakerConfig()
        self._fallback = fallback
        self._metrics = CircuitBreakerMetrics()
        self._lock = asyncio.Lock()

    @property
    def name(self) -> str:
        """Circuit Breaker 이름"""
        return self._name

    @property
    def state(self) -> CircuitState:
        """현재 상태"""
        return self._metrics.state

    @property
    def metrics(self) -> CircuitBreakerMetrics:
        """현재 메트릭"""
        return self._metrics

    def get_state(self) -> CircuitState:
        """현재 상태 반환 (호환성)"""
        return self._metrics.state

    async def call(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        fallback: Optional[Callable[..., Awaitable[T]]] = None,
        **kwargs: Any,
    ) -> T:
        """
        Circuit Breaker를 통한 비동기 함수 호출

        Args:
            func: 호출할 비동기 함수
            *args: 함수 인자
            fallback: 이 호출에 대한 커스텀 fallback
            **kwargs: 함수 키워드 인자

        Returns:
            함수 실행 결과 또는 fallback 결과

        Raises:
            CircuitBreakerOpenError: Circuit이 열려있고 fallback이 없는 경우
            Exception: 원본 함수에서 발생한 예외 (실패로 기록)
        """
        async with self._lock:
            await self._check_state_transition()

        self._metrics.total_calls += 1

        # OPEN 상태: 즉시 실패
        if self._metrics.state == CircuitState.OPEN:
            return await self._handle_open_state(func, args, kwargs, fallback)

        # HALF_OPEN 상태: 호출 수 제한
        if self._metrics.state == CircuitState.HALF_OPEN:
            if self._metrics.half_open_calls >= self._config.half_open_max_calls:
                return await self._handle_open_state(func, args, kwargs, fallback)
            self._metrics.half_open_calls += 1

        # CLOSED 또는 HALF_OPEN: 실제 호출 수행
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure(e)
            raise

    async def _check_state_transition(self) -> None:
        """상태 전이 확인 및 수행"""
        now = datetime.now(timezone.utc)

        if self._metrics.state == CircuitState.OPEN:
            # OPEN -> HALF_OPEN: recovery_timeout 경과 시
            if self._metrics.last_failure_time:
                elapsed = (now - self._metrics.last_failure_time).total_seconds()
                if elapsed >= self._config.recovery_timeout:
                    await self._transition_to(CircuitState.HALF_OPEN)

    async def _transition_to(self, new_state: CircuitState) -> None:
        """상태 전이"""
        old_state = self._metrics.state
        if old_state == new_state:
            return

        self._metrics.state = new_state
        self._metrics.last_state_change = datetime.now(timezone.utc)

        if new_state == CircuitState.CLOSED:
            # CLOSED로 전이 시 카운터 리셋
            self._metrics.failure_count = 0
            self._metrics.success_count = 0
        elif new_state == CircuitState.HALF_OPEN:
            # HALF_OPEN으로 전이 시 카운터 리셋
            self._metrics.success_count = 0
            self._metrics.half_open_calls = 0
        elif new_state == CircuitState.OPEN:
            # OPEN으로 전이
            self._metrics.open_count += 1
            self._metrics.success_count = 0

        logger.warning(
            "Circuit Breaker [%s] state changed: %s -> %s",
            self._name,
            old_state.value,
            new_state.value,
        )

    async def _on_success(self) -> None:
        """성공 처리"""
        async with self._lock:
            self._metrics.total_successes += 1
            self._metrics.failure_count = 0  # 연속 실패 리셋

            if self._metrics.state == CircuitState.HALF_OPEN:
                self._metrics.success_count += 1
                # 성공 임계값 도달 시 CLOSED로 전이
                if self._metrics.success_count >= self._config.success_threshold:
                    await self._transition_to(CircuitState.CLOSED)

    async def _on_failure(self, exc: Exception) -> None:
        """실패 처리"""
        # 실패 판정
        predicate = (
            self._config.failure_predicate
            or CircuitBreakerConfig.default_failure_predicate
        )
        if not predicate(exc):
            return  # 실패로 간주하지 않음

        async with self._lock:
            self._metrics.total_failures += 1
            self._metrics.failure_count += 1
            self._metrics.last_failure_time = datetime.now(timezone.utc)

            if self._metrics.state == CircuitState.HALF_OPEN:
                # HALF_OPEN에서 실패 시 즉시 OPEN으로
                await self._transition_to(CircuitState.OPEN)
            elif self._metrics.state == CircuitState.CLOSED:
                # 실패 임계값 도달 시 OPEN으로 전이
                if self._metrics.failure_count >= self._config.failure_threshold:
                    await self._transition_to(CircuitState.OPEN)

            logger.error(
                "Circuit Breaker [%s] recorded failure: %s (count: %d/%d)",
                self._name,
                type(exc).__name__,
                self._metrics.failure_count,
                self._config.failure_threshold,
            )

    async def _handle_open_state(
        self,
        func: Callable[..., Awaitable[T]],
        args: tuple,
        kwargs: dict,
        fallback: Optional[Callable[..., Awaitable[T]]] = None,
    ) -> T:
        """OPEN 상태 처리"""
        effective_fallback = fallback or self._fallback

        if effective_fallback:
            logger.info(
                "Circuit Breaker [%s] is OPEN, executing fallback",
                self._name,
            )
            return await effective_fallback(*args, **kwargs)

        # Fallback 없음: 예외 발생
        retry_after = self._config.recovery_timeout
        if self._metrics.last_failure_time:
            elapsed = (
                datetime.now(timezone.utc) - self._metrics.last_failure_time
            ).total_seconds()
            retry_after = max(0, int(self._config.recovery_timeout - elapsed))

        raise CircuitBreakerOpenError(
            service_name=self._name,
            retry_after_seconds=retry_after,
        )

    def reset(self) -> None:
        """Circuit Breaker 상태 초기화 (테스트용)"""
        self._metrics = CircuitBreakerMetrics()
        logger.info("Circuit Breaker [%s] reset to initial state", self._name)


# ---------------------------------------------------------------------------
# Circuit Breaker Registry
# ---------------------------------------------------------------------------


class CircuitBreakerRegistry:
    """
    Circuit Breaker 레지스트리

    여러 서비스의 Circuit Breaker를 관리합니다.
    """

    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        fallback: Optional[Callable[..., Awaitable[Any]]] = None,
    ) -> CircuitBreaker:
        """
        Circuit Breaker 가져오기 또는 생성

        Args:
            name: Circuit Breaker 이름
            config: 설정 (기존에 없을 때만 적용)
            fallback: fallback 함수

        Returns:
            CircuitBreaker 인스턴스
        """
        async with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(
                    name=name,
                    config=config,
                    fallback=fallback,
                )
                logger.info("Created Circuit Breaker: %s", name)
            return self._breakers[name]

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """이름으로 Circuit Breaker 가져오기"""
        return self._breakers.get(name)

    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """모든 Circuit Breaker 메트릭 반환"""
        return {name: cb.metrics.to_dict() for name, cb in self._breakers.items()}

    def reset_all(self) -> None:
        """모든 Circuit Breaker 초기화"""
        for cb in self._breakers.values():
            cb.reset()


# ---------------------------------------------------------------------------
# Global Registry
# ---------------------------------------------------------------------------

_registry: Optional[CircuitBreakerRegistry] = None


def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    """전역 Circuit Breaker 레지스트리 반환"""
    global _registry
    if _registry is None:
        _registry = CircuitBreakerRegistry()
    return _registry


def reset_circuit_breaker_registry() -> None:
    """전역 레지스트리 초기화 (테스트용)"""
    global _registry
    if _registry:
        _registry.reset_all()
    _registry = None
