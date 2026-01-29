"""
Circuit Breaker 단위 테스트

STORY-061: Circuit Breaker 패턴 구현

테스트 항목:
    - 상태 전이 (CLOSED -> OPEN -> HALF_OPEN -> CLOSED)
    - 실패 임계값 도달 시 OPEN 전이
    - 복구 타임아웃 후 HALF_OPEN 전이
    - Fallback 전략
    - 메트릭 수집
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerError,
    CircuitBreakerMetrics,
    CircuitBreakerOpenError,
    CircuitBreakerRegistry,
    CircuitState,
    get_circuit_breaker_registry,
    reset_circuit_breaker_registry,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def default_config() -> CircuitBreakerConfig:
    """기본 Circuit Breaker 설정"""
    return CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=5,
        half_open_max_calls=2,
        success_threshold=2,
    )


@pytest.fixture
def circuit_breaker(default_config: CircuitBreakerConfig) -> CircuitBreaker:
    """테스트용 Circuit Breaker"""
    return CircuitBreaker(name="test-service", config=default_config)


@pytest.fixture(autouse=True)
def reset_registry():
    """각 테스트 후 레지스트리 초기화"""
    yield
    reset_circuit_breaker_registry()


# ---------------------------------------------------------------------------
# CircuitBreakerConfig Tests
# ---------------------------------------------------------------------------


class TestCircuitBreakerConfig:
    """CircuitBreakerConfig 테스트"""

    def test_default_values(self):
        """기본값 확인"""
        config = CircuitBreakerConfig()

        assert config.failure_threshold == 5
        assert config.recovery_timeout == 30
        assert config.half_open_max_calls == 3
        assert config.success_threshold == 2

    def test_custom_values(self):
        """커스텀 값 확인"""
        config = CircuitBreakerConfig(
            failure_threshold=10,
            recovery_timeout=60,
            half_open_max_calls=5,
            success_threshold=3,
        )

        assert config.failure_threshold == 10
        assert config.recovery_timeout == 60
        assert config.half_open_max_calls == 5
        assert config.success_threshold == 3

    def test_default_failure_predicate(self):
        """기본 실패 판정 함수"""
        predicate = CircuitBreakerConfig.default_failure_predicate

        # 실패로 간주
        assert predicate(RuntimeError("error")) is True
        assert predicate(ConnectionError("error")) is True
        assert predicate(TimeoutError("error")) is True

        # 실패로 간주하지 않음
        assert predicate(ValueError("error")) is False
        assert predicate(TypeError("error")) is False


# ---------------------------------------------------------------------------
# CircuitBreakerMetrics Tests
# ---------------------------------------------------------------------------


class TestCircuitBreakerMetrics:
    """CircuitBreakerMetrics 테스트"""

    def test_initial_state(self):
        """초기 상태 확인"""
        metrics = CircuitBreakerMetrics()

        assert metrics.state == CircuitState.CLOSED
        assert metrics.failure_count == 0
        assert metrics.success_count == 0
        assert metrics.total_calls == 0
        assert metrics.total_successes == 0
        assert metrics.total_failures == 0
        assert metrics.open_count == 0

    def test_to_dict(self):
        """딕셔너리 변환"""
        metrics = CircuitBreakerMetrics(
            state=CircuitState.OPEN,
            failure_count=5,
            total_calls=100,
            total_successes=90,
            total_failures=10,
            open_count=2,
        )

        result = metrics.to_dict()

        assert result["state"] == "open"
        assert result["failure_count"] == 5
        assert result["total_calls"] == 100
        assert result["success_rate"] == 90.0  # 90/100 * 100

    def test_success_rate_calculation(self):
        """성공률 계산"""
        # 호출 없음
        metrics = CircuitBreakerMetrics(total_calls=0)
        assert metrics.to_dict()["success_rate"] == 0.0

        # 100% 성공
        metrics = CircuitBreakerMetrics(total_calls=10, total_successes=10)
        assert metrics.to_dict()["success_rate"] == 100.0

        # 50% 성공
        metrics = CircuitBreakerMetrics(total_calls=10, total_successes=5)
        assert metrics.to_dict()["success_rate"] == 50.0


# ---------------------------------------------------------------------------
# CircuitBreaker State Transition Tests
# ---------------------------------------------------------------------------


class TestCircuitBreakerStateTransition:
    """상태 전이 테스트"""

    @pytest.mark.asyncio
    async def test_initial_state_is_closed(self, circuit_breaker: CircuitBreaker):
        """초기 상태는 CLOSED"""
        assert circuit_breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_transition_to_open_on_failure_threshold(
        self, circuit_breaker: CircuitBreaker
    ):
        """실패 임계값 도달 시 OPEN 전이"""
        async def failing_func():
            raise RuntimeError("Service unavailable")

        # failure_threshold(3)번 실패
        for _ in range(3):
            with pytest.raises(RuntimeError):
                await circuit_breaker.call(failing_func)

        # OPEN 상태로 전이
        assert circuit_breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_open_circuit_rejects_immediately(
        self, circuit_breaker: CircuitBreaker
    ):
        """OPEN 상태에서는 즉시 거부"""
        async def failing_func():
            raise RuntimeError("Service unavailable")

        # OPEN 상태로 전이
        for _ in range(3):
            with pytest.raises(RuntimeError):
                await circuit_breaker.call(failing_func)

        assert circuit_breaker.state == CircuitState.OPEN

        # Fallback 없이 호출 시 CircuitBreakerOpenError 발생
        with pytest.raises(CircuitBreakerOpenError):
            await circuit_breaker.call(failing_func)

    @pytest.mark.asyncio
    async def test_transition_to_half_open_after_recovery_timeout(
        self, default_config: CircuitBreakerConfig
    ):
        """복구 타임아웃 후 HALF_OPEN 전이"""
        # 짧은 복구 타임아웃 설정
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=1,  # 1초
            half_open_max_calls=2,
            success_threshold=2,
        )
        breaker = CircuitBreaker(name="test", config=config)

        async def failing_func():
            raise RuntimeError("Service unavailable")

        async def success_func():
            return "success"

        # OPEN 상태로 전이
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

        # 복구 타임아웃 대기
        await asyncio.sleep(1.1)

        # 다음 호출 시 HALF_OPEN으로 전이
        result = await breaker.call(success_func)
        assert result == "success"
        assert breaker.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_transition_to_closed_on_success_threshold(self):
        """HALF_OPEN에서 성공 임계값 도달 시 CLOSED 전이"""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=0,  # 즉시 HALF_OPEN
            half_open_max_calls=3,
            success_threshold=2,
        )
        breaker = CircuitBreaker(name="test", config=config)

        async def failing_func():
            raise RuntimeError("fail")

        async def success_func():
            return "success"

        # OPEN 상태로 전이
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

        # HALF_OPEN으로 전이 후 success_threshold(2)번 성공
        for _ in range(2):
            result = await breaker.call(success_func)
            assert result == "success"

        # CLOSED 상태로 전이
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_transition_to_open_on_half_open_failure(self):
        """HALF_OPEN에서 실패 시 OPEN 전이"""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=0,
            half_open_max_calls=3,
            success_threshold=2,
        )
        breaker = CircuitBreaker(name="test", config=config)

        async def failing_func():
            raise RuntimeError("fail")

        async def success_func():
            return "success"

        # OPEN 상태로 전이
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

        # HALF_OPEN에서 1번 성공
        await breaker.call(success_func)
        assert breaker.state == CircuitState.HALF_OPEN

        # HALF_OPEN에서 실패 -> OPEN
        with pytest.raises(RuntimeError):
            await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN


# ---------------------------------------------------------------------------
# Fallback Tests
# ---------------------------------------------------------------------------


class TestCircuitBreakerFallback:
    """Fallback 전략 테스트"""

    @pytest.mark.asyncio
    async def test_fallback_on_open(self, circuit_breaker: CircuitBreaker):
        """OPEN 상태에서 fallback 호출"""
        async def failing_func():
            raise RuntimeError("fail")

        async def fallback(*args, **kwargs):
            return "fallback_result"

        # OPEN 상태로 전이
        for _ in range(3):
            with pytest.raises(RuntimeError):
                await circuit_breaker.call(failing_func)

        # Fallback 사용
        result = await circuit_breaker.call(failing_func, fallback=fallback)
        assert result == "fallback_result"

    @pytest.mark.asyncio
    async def test_default_fallback(self):
        """기본 fallback 함수 사용"""
        async def default_fallback(*args, **kwargs):
            return "default_fallback"

        breaker = CircuitBreaker(
            name="test",
            config=CircuitBreakerConfig(failure_threshold=2),
            fallback=default_fallback,
        )

        async def failing_func():
            raise RuntimeError("fail")

        # OPEN 상태로 전이
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await breaker.call(failing_func)

        # 기본 fallback 사용
        result = await breaker.call(failing_func)
        assert result == "default_fallback"

    @pytest.mark.asyncio
    async def test_call_specific_fallback_overrides_default(self):
        """호출별 fallback이 기본 fallback보다 우선"""
        async def default_fallback(*args, **kwargs):
            return "default"

        async def specific_fallback(*args, **kwargs):
            return "specific"

        breaker = CircuitBreaker(
            name="test",
            config=CircuitBreakerConfig(failure_threshold=2),
            fallback=default_fallback,
        )

        async def failing_func():
            raise RuntimeError("fail")

        # OPEN 상태로 전이
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await breaker.call(failing_func)

        # 호출별 fallback 사용
        result = await breaker.call(failing_func, fallback=specific_fallback)
        assert result == "specific"


# ---------------------------------------------------------------------------
# Metrics Tests
# ---------------------------------------------------------------------------


class TestCircuitBreakerMetricsCollection:
    """메트릭 수집 테스트"""

    @pytest.mark.asyncio
    async def test_metrics_on_success(self, circuit_breaker: CircuitBreaker):
        """성공 시 메트릭 업데이트"""
        async def success_func():
            return "success"

        await circuit_breaker.call(success_func)

        assert circuit_breaker.metrics.total_calls == 1
        assert circuit_breaker.metrics.total_successes == 1
        assert circuit_breaker.metrics.total_failures == 0
        assert circuit_breaker.metrics.failure_count == 0

    @pytest.mark.asyncio
    async def test_metrics_on_failure(self, circuit_breaker: CircuitBreaker):
        """실패 시 메트릭 업데이트"""
        async def failing_func():
            raise RuntimeError("fail")

        with pytest.raises(RuntimeError):
            await circuit_breaker.call(failing_func)

        assert circuit_breaker.metrics.total_calls == 1
        assert circuit_breaker.metrics.total_successes == 0
        assert circuit_breaker.metrics.total_failures == 1
        assert circuit_breaker.metrics.failure_count == 1

    @pytest.mark.asyncio
    async def test_open_count_increment(self, circuit_breaker: CircuitBreaker):
        """OPEN 전이 횟수 추적"""
        async def failing_func():
            raise RuntimeError("fail")

        # 첫 번째 OPEN
        for _ in range(3):
            with pytest.raises(RuntimeError):
                await circuit_breaker.call(failing_func)

        assert circuit_breaker.metrics.open_count == 1

    @pytest.mark.asyncio
    async def test_last_failure_time_update(self, circuit_breaker: CircuitBreaker):
        """마지막 실패 시간 업데이트"""
        async def failing_func():
            raise RuntimeError("fail")

        before = datetime.now(timezone.utc)
        with pytest.raises(RuntimeError):
            await circuit_breaker.call(failing_func)
        after = datetime.now(timezone.utc)

        assert circuit_breaker.metrics.last_failure_time is not None
        assert before <= circuit_breaker.metrics.last_failure_time <= after


# ---------------------------------------------------------------------------
# Registry Tests
# ---------------------------------------------------------------------------


class TestCircuitBreakerRegistry:
    """Circuit Breaker 레지스트리 테스트"""

    @pytest.mark.asyncio
    async def test_get_or_create(self):
        """Circuit Breaker 생성 및 조회"""
        registry = CircuitBreakerRegistry()

        breaker1 = await registry.get_or_create("service-a")
        breaker2 = await registry.get_or_create("service-a")

        # 같은 인스턴스 반환
        assert breaker1 is breaker2

    @pytest.mark.asyncio
    async def test_get_nonexistent(self):
        """존재하지 않는 Circuit Breaker 조회"""
        registry = CircuitBreakerRegistry()

        result = registry.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_all_metrics(self):
        """모든 메트릭 조회"""
        registry = CircuitBreakerRegistry()

        await registry.get_or_create("service-a")
        await registry.get_or_create("service-b")

        all_metrics = registry.get_all_metrics()

        assert "service-a" in all_metrics
        assert "service-b" in all_metrics
        assert all_metrics["service-a"]["state"] == "closed"

    @pytest.mark.asyncio
    async def test_reset_all(self):
        """모든 Circuit Breaker 초기화"""
        registry = CircuitBreakerRegistry()

        breaker = await registry.get_or_create(
            "test",
            config=CircuitBreakerConfig(failure_threshold=2),
        )

        async def failing_func():
            raise RuntimeError("fail")

        # OPEN 상태로 전이
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

        # 초기화
        registry.reset_all()

        assert breaker.state == CircuitState.CLOSED
        assert breaker.metrics.failure_count == 0

    @pytest.mark.asyncio
    async def test_global_registry(self):
        """전역 레지스트리"""
        registry = get_circuit_breaker_registry()
        breaker = await registry.get_or_create("global-test")

        assert breaker.name == "global-test"

        # 같은 레지스트리 반환
        registry2 = get_circuit_breaker_registry()
        assert registry is registry2


# ---------------------------------------------------------------------------
# CircuitBreakerOpenError Tests
# ---------------------------------------------------------------------------


class TestCircuitBreakerOpenError:
    """CircuitBreakerOpenError 테스트"""

    def test_error_attributes(self):
        """에러 속성 확인"""
        error = CircuitBreakerOpenError(
            service_name="test-service",
            retry_after_seconds=30,
        )

        assert error.status_code == 503
        assert error.error_code == "CIRCUIT_BREAKER_OPEN"
        assert "test-service" in error.message
        assert error.details["service"] == "test-service"
        assert error.details["retry_after_seconds"] == 30

    def test_to_dict(self):
        """딕셔너리 변환"""
        error = CircuitBreakerOpenError(
            service_name="test-service",
            retry_after_seconds=30,
        )

        result = error.to_dict()

        assert result["error_code"] == "CIRCUIT_BREAKER_OPEN"
        assert "test-service" in result["message"]


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestCircuitBreakerEdgeCases:
    """엣지 케이스 테스트"""

    @pytest.mark.asyncio
    async def test_reset(self, circuit_breaker: CircuitBreaker):
        """수동 리셋"""
        async def failing_func():
            raise RuntimeError("fail")

        # OPEN 상태로 전이
        for _ in range(3):
            with pytest.raises(RuntimeError):
                await circuit_breaker.call(failing_func)

        assert circuit_breaker.state == CircuitState.OPEN

        # 리셋
        circuit_breaker.reset()

        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.metrics.failure_count == 0

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self, circuit_breaker: CircuitBreaker):
        """성공 시 연속 실패 카운터 리셋"""
        async def failing_func():
            raise RuntimeError("fail")

        async def success_func():
            return "success"

        # 2번 실패 (threshold=3 미만)
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await circuit_breaker.call(failing_func)

        assert circuit_breaker.metrics.failure_count == 2

        # 1번 성공
        await circuit_breaker.call(success_func)

        # 연속 실패 카운터 리셋
        assert circuit_breaker.metrics.failure_count == 0

    @pytest.mark.asyncio
    async def test_half_open_max_calls_limit(self):
        """HALF_OPEN 상태에서 호출 수 제한"""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=0,
            half_open_max_calls=2,
            success_threshold=3,
        )
        breaker = CircuitBreaker(name="test", config=config)

        async def failing_func():
            raise RuntimeError("fail")

        async def success_func():
            return "success"

        async def fallback():
            return "fallback"

        # OPEN 상태로 전이
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await breaker.call(failing_func)

        # HALF_OPEN에서 max_calls(2)만큼 호출
        await breaker.call(success_func)
        await breaker.call(success_func)

        # 추가 호출은 fallback 또는 거부
        result = await breaker.call(success_func, fallback=fallback)
        assert result == "fallback"

    @pytest.mark.asyncio
    async def test_custom_failure_predicate(self):
        """커스텀 실패 판정"""

        def custom_predicate(exc: Exception) -> bool:
            # ValueError만 실패로 간주
            return isinstance(exc, ValueError)

        config = CircuitBreakerConfig(
            failure_threshold=2,
            failure_predicate=custom_predicate,
        )
        breaker = CircuitBreaker(name="test", config=config)

        async def value_error_func():
            raise ValueError("value error")

        async def runtime_error_func():
            raise RuntimeError("runtime error")

        # RuntimeError는 실패로 간주하지 않음
        for _ in range(5):
            with pytest.raises(RuntimeError):
                await breaker.call(runtime_error_func)

        assert breaker.state == CircuitState.CLOSED  # 여전히 CLOSED

        # ValueError는 실패로 간주
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(value_error_func)

        assert breaker.state == CircuitState.OPEN
