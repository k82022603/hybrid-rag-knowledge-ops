"""
Circuit Breaker 통합 테스트

STORY-061: Circuit Breaker 패턴 구현

테스트 항목:
    - LLM Adapter + Circuit Breaker 통합
    - Health API Circuit Breaker 상태 조회
    - Fallback 전략 검증
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    get_circuit_breaker_registry,
    reset_circuit_breaker_registry,
)
from app.main import app
from app.services.llm_adapter import (
    LLMAdapter,
    ServiceConnectionError,
    ServiceTimeoutError,
    get_llm_adapter,
    reset_llm_adapter,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    """TestClient 생성"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_singletons():
    """테스트 전후 싱글톤 초기화"""
    yield
    reset_circuit_breaker_registry()
    reset_llm_adapter()


@pytest.fixture
def mock_llm_service():
    """Mock LLM Service"""
    mock = MagicMock()
    mock.generate_with_messages = AsyncMock(return_value="Test response")
    return mock


# ---------------------------------------------------------------------------
# LLM Adapter + Circuit Breaker 통합 테스트
# ---------------------------------------------------------------------------


class TestLLMAdapterCircuitBreakerIntegration:
    """LLM Adapter와 Circuit Breaker 통합 테스트"""

    @pytest.mark.asyncio
    async def test_circuit_breaker_enabled_by_default(self, mock_llm_service):
        """Circuit Breaker가 기본으로 활성화되어 있는지 확인"""
        adapter = LLMAdapter(llm_service=mock_llm_service)

        # 첫 번째 호출로 Circuit Breaker 초기화
        await adapter.generate(prompt="test")

        # Circuit Breaker가 생성되었는지 확인
        state = adapter.get_circuit_breaker_state()
        assert state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_breaker_disabled(self, mock_llm_service):
        """Circuit Breaker 비활성화 시 직접 호출"""
        adapter = LLMAdapter(
            llm_service=mock_llm_service,
            enable_circuit_breaker=False,
        )

        result = await adapter.generate(prompt="test")

        assert result == "Test response"
        assert adapter.get_circuit_breaker_state() is None

    @pytest.mark.asyncio
    async def test_circuit_opens_on_repeated_failures(self, mock_llm_service):
        """연속 실패 시 Circuit이 열림"""
        # 실패를 발생시키는 mock
        mock_llm_service.generate_with_messages = AsyncMock(
            side_effect=ConnectionError("Connection refused")
        )

        # 짧은 threshold로 설정된 어댑터
        config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=30)
        breaker = CircuitBreaker(name="test-llm", config=config)

        adapter = LLMAdapter(
            llm_service=mock_llm_service,
            circuit_breaker=breaker,
        )

        # 3번 실패
        for _ in range(3):
            with pytest.raises(ServiceConnectionError):
                await adapter.generate(prompt="test", use_fallback=False)

        # Circuit이 열렸는지 확인
        assert adapter.get_circuit_breaker_state() == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_fallback_when_circuit_open(self, mock_llm_service):
        """Circuit OPEN 시 fallback 메시지 반환"""
        mock_llm_service.generate_with_messages = AsyncMock(
            side_effect=ConnectionError("Connection refused")
        )

        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=30)
        breaker = CircuitBreaker(name="test-llm-fallback", config=config)

        adapter = LLMAdapter(
            llm_service=mock_llm_service,
            circuit_breaker=breaker,
        )

        # Circuit 열기
        for _ in range(2):
            with pytest.raises(ServiceConnectionError):
                await adapter.generate(prompt="test", use_fallback=False)

        assert adapter.get_circuit_breaker_state() == CircuitState.OPEN

        # Fallback 사용
        result = await adapter.generate(prompt="test", use_fallback=True)
        assert result == LLMAdapter.DEFAULT_FALLBACK_MESSAGE

    @pytest.mark.asyncio
    async def test_circuit_half_open_after_timeout(self, mock_llm_service):
        """복구 타임아웃 후 HALF_OPEN 전이"""
        mock_llm_service.generate_with_messages = AsyncMock(
            side_effect=ConnectionError("Connection refused")
        )

        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=1,  # 1초
        )
        breaker = CircuitBreaker(name="test-llm-recovery", config=config)

        adapter = LLMAdapter(
            llm_service=mock_llm_service,
            circuit_breaker=breaker,
        )

        # Circuit 열기
        for _ in range(2):
            with pytest.raises(ServiceConnectionError):
                await adapter.generate(prompt="test", use_fallback=False)

        assert adapter.get_circuit_breaker_state() == CircuitState.OPEN

        # 복구 타임아웃 대기
        await asyncio.sleep(1.1)

        # 성공하는 mock으로 변경
        mock_llm_service.generate_with_messages = AsyncMock(return_value="Success")

        # HALF_OPEN에서 성공
        result = await adapter.generate(prompt="test")
        assert result == "Success"
        assert adapter.get_circuit_breaker_state() == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_circuit_closes_after_success_threshold(self, mock_llm_service):
        """HALF_OPEN에서 성공 임계값 도달 시 CLOSED"""
        mock_llm_service.generate_with_messages = AsyncMock(
            side_effect=ConnectionError("Connection refused")
        )

        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=0,  # 즉시 HALF_OPEN
            success_threshold=2,
        )
        breaker = CircuitBreaker(name="test-llm-close", config=config)

        adapter = LLMAdapter(
            llm_service=mock_llm_service,
            circuit_breaker=breaker,
        )

        # Circuit 열기
        for _ in range(2):
            with pytest.raises(ServiceConnectionError):
                await adapter.generate(prompt="test", use_fallback=False)

        # 성공하는 mock으로 변경
        mock_llm_service.generate_with_messages = AsyncMock(return_value="Success")

        # 2번 성공
        for _ in range(2):
            await adapter.generate(prompt="test")

        assert adapter.get_circuit_breaker_state() == CircuitState.CLOSED


# ---------------------------------------------------------------------------
# Health API Circuit Breaker 테스트
# ---------------------------------------------------------------------------


class TestHealthAPICircuitBreaker:
    """Health API Circuit Breaker 엔드포인트 테스트"""

    def test_get_all_circuit_breakers_empty(self, client):
        """Circuit Breaker가 없을 때"""
        response = client.get("/api/v1/health/circuit-breaker")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 0
        assert data["healthy_count"] == 0
        assert data["degraded_count"] == 0

    @pytest.mark.asyncio
    async def test_get_all_circuit_breakers_with_data(self, client):
        """Circuit Breaker가 있을 때"""
        registry = get_circuit_breaker_registry()

        # Circuit Breaker 생성
        await registry.get_or_create("service-a")
        await registry.get_or_create("service-b")

        response = client.get("/api/v1/health/circuit-breaker")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 2
        assert data["healthy_count"] == 2  # 모두 CLOSED
        assert "service-a" in data["circuit_breakers"]
        assert "service-b" in data["circuit_breakers"]

    @pytest.mark.asyncio
    async def test_get_specific_circuit_breaker(self, client):
        """특정 Circuit Breaker 상태 조회"""
        registry = get_circuit_breaker_registry()
        breaker = await registry.get_or_create("test-service")

        response = client.get("/api/v1/health/circuit-breaker/test-service")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test-service"
        assert data["state"] == "closed"
        assert data["failure_count"] == 0
        assert data["total_calls"] == 0

    def test_get_nonexistent_circuit_breaker(self, client):
        """존재하지 않는 Circuit Breaker 조회"""
        response = client.get("/api/v1/health/circuit-breaker/nonexistent")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_circuit_breaker_metrics_after_calls(self, client):
        """호출 후 메트릭 확인"""
        registry = get_circuit_breaker_registry()
        breaker = await registry.get_or_create(
            "metrics-test",
            config=CircuitBreakerConfig(failure_threshold=5),
        )

        async def success_func():
            return "success"

        async def failing_func():
            raise RuntimeError("fail")

        # 3번 성공
        for _ in range(3):
            await breaker.call(success_func)

        # 2번 실패
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await breaker.call(failing_func)

        response = client.get("/api/v1/health/circuit-breaker/metrics-test")

        assert response.status_code == 200
        data = response.json()
        assert data["total_calls"] == 5
        assert data["total_successes"] == 3
        assert data["total_failures"] == 2
        assert data["success_rate"] == 60.0  # 3/5 * 100


# ---------------------------------------------------------------------------
# Fallback 전략 테스트
# ---------------------------------------------------------------------------


class TestFallbackStrategies:
    """Fallback 전략 테스트"""

    @pytest.mark.asyncio
    async def test_default_fallback_message(self, mock_llm_service):
        """기본 fallback 메시지 확인"""
        mock_llm_service.generate_with_messages = AsyncMock(
            side_effect=ConnectionError("fail")
        )

        config = CircuitBreakerConfig(failure_threshold=1)
        breaker = CircuitBreaker(name="fallback-test", config=config)

        adapter = LLMAdapter(
            llm_service=mock_llm_service,
            circuit_breaker=breaker,
        )

        # Circuit 열기
        with pytest.raises(ServiceConnectionError):
            await adapter.generate(prompt="test", use_fallback=False)

        # Fallback 사용
        result = await adapter.generate(prompt="test", use_fallback=True)

        assert "죄송합니다" in result
        assert "일시적으로" in result

    @pytest.mark.asyncio
    async def test_fallback_does_not_affect_metrics(self, mock_llm_service):
        """Fallback 호출은 메트릭에 영향 없음"""
        mock_llm_service.generate_with_messages = AsyncMock(
            side_effect=ConnectionError("fail")
        )

        config = CircuitBreakerConfig(failure_threshold=2)
        breaker = CircuitBreaker(name="fallback-metrics", config=config)

        adapter = LLMAdapter(
            llm_service=mock_llm_service,
            circuit_breaker=breaker,
        )

        # Circuit 열기
        for _ in range(2):
            with pytest.raises(ServiceConnectionError):
                await adapter.generate(prompt="test", use_fallback=False)

        initial_total = breaker.metrics.total_calls

        # Fallback 호출
        await adapter.generate(prompt="test", use_fallback=True)

        # total_calls는 증가하지만 성공/실패 카운터는 변경 없음
        assert breaker.metrics.total_calls == initial_total + 1

    @pytest.mark.asyncio
    async def test_generate_with_messages_fallback(self, mock_llm_service):
        """generate_with_messages에서 fallback 사용"""
        mock_llm_service.generate_with_messages = AsyncMock(
            side_effect=ConnectionError("fail")
        )

        config = CircuitBreakerConfig(failure_threshold=2)
        breaker = CircuitBreaker(name="messages-fallback", config=config)

        adapter = LLMAdapter(
            llm_service=mock_llm_service,
            circuit_breaker=breaker,
        )

        messages = [{"role": "user", "content": "test"}]

        # Circuit 열기
        for _ in range(2):
            with pytest.raises(ServiceConnectionError):
                await adapter.generate_with_messages(
                    messages=messages, use_fallback=False
                )

        # Fallback 사용
        result = await adapter.generate_with_messages(messages=messages, use_fallback=True)
        assert result == LLMAdapter.DEFAULT_FALLBACK_MESSAGE


# ---------------------------------------------------------------------------
# 에러 시나리오 테스트
# ---------------------------------------------------------------------------


class TestErrorScenarios:
    """에러 시나리오 테스트"""

    @pytest.mark.asyncio
    async def test_timeout_triggers_circuit_breaker(self, mock_llm_service):
        """타임아웃이 Circuit Breaker를 트리거"""
        mock_llm_service.generate_with_messages = AsyncMock(
            side_effect=asyncio.TimeoutError()
        )

        config = CircuitBreakerConfig(failure_threshold=2)
        breaker = CircuitBreaker(name="timeout-test", config=config)

        adapter = LLMAdapter(
            llm_service=mock_llm_service,
            circuit_breaker=breaker,
            timeout_seconds=1,
        )

        # 타임아웃 발생
        for _ in range(2):
            with pytest.raises(ServiceTimeoutError):
                await adapter.generate(prompt="test", use_fallback=False)

        assert adapter.get_circuit_breaker_state() == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_connection_error_triggers_circuit_breaker(self, mock_llm_service):
        """연결 에러가 Circuit Breaker를 트리거"""
        mock_llm_service.generate_with_messages = AsyncMock(
            side_effect=ConnectionError("Connection refused")
        )

        config = CircuitBreakerConfig(failure_threshold=2)
        breaker = CircuitBreaker(name="connection-test", config=config)

        adapter = LLMAdapter(
            llm_service=mock_llm_service,
            circuit_breaker=breaker,
        )

        for _ in range(2):
            with pytest.raises(ServiceConnectionError):
                await adapter.generate(prompt="test", use_fallback=False)

        assert adapter.get_circuit_breaker_state() == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_validation_error_does_not_trigger_circuit_breaker(
        self, mock_llm_service
    ):
        """검증 에러는 Circuit Breaker를 트리거하지 않음"""
        config = CircuitBreakerConfig(failure_threshold=2)
        breaker = CircuitBreaker(name="validation-test", config=config)

        adapter = LLMAdapter(
            llm_service=mock_llm_service,
            circuit_breaker=breaker,
        )

        # 빈 프롬프트로 ValidationError 발생
        for _ in range(5):
            with pytest.raises(Exception):  # ServiceValidationError
                await adapter.generate(prompt="")

        # Circuit은 여전히 CLOSED
        assert adapter.get_circuit_breaker_state() == CircuitState.CLOSED
