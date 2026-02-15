"""
LLM Adapter 단위 테스트

에러 변환, 메시지 구성, Circuit Breaker 연동 등 순수 로직 테스트.
실제 DeepSeek API 호출은 통합 테스트에서 수행.

TEST_MODE=docker pytest src/tests/unit/test_llm_adapter.py -v
"""

import asyncio

import pytest

from app.core.exceptions import (
    KnowledgeServiceError,
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from app.services.llm_adapter import (
    LLMAdapter,
    ServiceConnectionError,
    ServiceRateLimitError,
    ServiceTimeoutError,
    ServiceValidationError,
    translate_llm_error,
    reset_llm_adapter,
)


# ---------------------------------------------------------------------------
# translate_llm_error 테스트
# ---------------------------------------------------------------------------


class TestTranslateLLMError:
    """LLM 예외 -> 서비스 예외 변환 테스트"""

    def test_timeout_error(self):
        err = translate_llm_error(LLMTimeoutError())
        assert isinstance(err, ServiceTimeoutError)
        assert err.status_code == 504

    def test_asyncio_timeout(self):
        err = translate_llm_error(asyncio.TimeoutError())
        assert isinstance(err, ServiceTimeoutError)
        assert err.status_code == 504

    def test_rate_limit_error(self):
        err = translate_llm_error(LLMRateLimitError())
        assert isinstance(err, ServiceRateLimitError)
        assert err.status_code == 429

    def test_connection_error(self):
        err = translate_llm_error(ConnectionError("refused"))
        assert isinstance(err, ServiceConnectionError)
        assert err.status_code == 502

    def test_os_error(self):
        err = translate_llm_error(OSError("network unreachable"))
        assert isinstance(err, ServiceConnectionError)
        assert err.status_code == 502

    def test_generic_llm_error(self):
        err = translate_llm_error(LLMError("something failed"))
        assert isinstance(err, ServiceConnectionError)
        assert err.status_code == 502

    def test_unknown_error(self):
        err = translate_llm_error(RuntimeError("unexpected"))
        assert isinstance(err, KnowledgeServiceError)
        assert err.status_code == 500

    def test_timeout_string_pattern(self):
        """문자열에 'timeout' 포함 시 504"""
        err = translate_llm_error(Exception("connection timed out"))
        assert isinstance(err, ServiceTimeoutError)

    def test_rate_string_pattern(self):
        """문자열에 '429' 포함 시 429"""
        err = translate_llm_error(Exception("HTTP 429 too many requests"))
        assert isinstance(err, ServiceRateLimitError)

    def test_connection_string_pattern(self):
        """문자열에 'connection refused' 포함 시 502"""
        err = translate_llm_error(Exception("connection refused"))
        assert isinstance(err, ServiceConnectionError)


# ---------------------------------------------------------------------------
# ServiceError 클래스 테스트
# ---------------------------------------------------------------------------


class TestServiceErrors:
    """서비스 예외 클래스 테스트"""

    def test_service_connection_error(self):
        err = ServiceConnectionError(service_name="TestService")
        assert "TestService" in err.message
        assert err.status_code == 502
        assert err.error_code == "SERVICE_CONNECTION_ERROR"

    def test_service_timeout_error(self):
        err = ServiceTimeoutError(service_name="LLM", timeout_seconds=60)
        assert "60" in err.message
        assert err.status_code == 504
        assert err.details["timeout_seconds"] == 60

    def test_service_rate_limit_error(self):
        err = ServiceRateLimitError(service_name="DeepSeek", retry_after=30)
        assert err.status_code == 429
        assert err.details["retry_after_seconds"] == 30

    def test_service_validation_error(self):
        err = ServiceValidationError(message="Invalid input", field="query")
        assert err.status_code == 400
        assert err.error_code == "VALIDATION_ERROR"

    def test_service_validation_error_no_field(self):
        err = ServiceValidationError()
        assert err.status_code == 400


# ---------------------------------------------------------------------------
# LLMAdapter 메시지 구성 테스트
# ---------------------------------------------------------------------------


class TestBuildMessages:
    """_build_messages() 테스트"""

    def test_with_context(self):
        adapter = LLMAdapter(enable_circuit_breaker=False)
        messages = adapter._build_messages(
            prompt="사용자 질문",
            context="검색 컨텍스트",
        )
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "검색 컨텍스트" in messages[1]["content"]
        assert "사용자 질문" in messages[1]["content"]
        assert "[출처N]" in messages[1]["content"]

    def test_without_context(self):
        adapter = LLMAdapter(enable_circuit_breaker=False)
        messages = adapter._build_messages(
            prompt="단순 질문",
            context="",
        )
        assert len(messages) == 2
        assert messages[1]["content"] == "단순 질문"

    def test_whitespace_only_context(self):
        adapter = LLMAdapter(enable_circuit_breaker=False)
        messages = adapter._build_messages(
            prompt="질문",
            context="   \n  ",
        )
        # 공백만 있는 context는 context 없는 것으로 처리
        assert messages[1]["content"] == "질문"

    def test_custom_system_prompt(self):
        adapter = LLMAdapter(
            system_prompt="You are a test assistant.",
            enable_circuit_breaker=False,
        )
        messages = adapter._build_messages(prompt="hello")
        assert messages[0]["content"] == "You are a test assistant."


# ---------------------------------------------------------------------------
# LLMAdapter 초기화 테스트
# ---------------------------------------------------------------------------


class TestLLMAdapterInit:
    """LLMAdapter 초기화 테스트"""

    def test_default_init(self):
        adapter = LLMAdapter(enable_circuit_breaker=False)
        assert adapter._system_prompt is not None
        assert adapter._timeout > 0

    def test_custom_timeout(self):
        adapter = LLMAdapter(timeout_seconds=120, enable_circuit_breaker=False)
        assert adapter._timeout == 120

    def test_circuit_breaker_disabled(self):
        adapter = LLMAdapter(enable_circuit_breaker=False)
        assert adapter._enable_circuit_breaker is False
        state = adapter.get_circuit_breaker_state()
        assert state is None

    def test_default_system_prompt(self):
        prompt = LLMAdapter._default_system_prompt()
        assert "지식 검색 시스템" in prompt
        assert "한국어" in prompt

    def test_default_fallback_message(self):
        assert "일시적으로" in LLMAdapter.DEFAULT_FALLBACK_MESSAGE


# ---------------------------------------------------------------------------
# LLMAdapter.generate() 입력 검증
# ---------------------------------------------------------------------------


class TestGenerateValidation:
    """generate() 입력 검증 테스트"""

    @pytest.mark.asyncio
    async def test_empty_prompt_raises(self):
        adapter = LLMAdapter(enable_circuit_breaker=False)
        with pytest.raises(ServiceValidationError, match="비어 있습니다"):
            await adapter.generate(prompt="")

    @pytest.mark.asyncio
    async def test_whitespace_prompt_raises(self):
        adapter = LLMAdapter(enable_circuit_breaker=False)
        with pytest.raises(ServiceValidationError):
            await adapter.generate(prompt="   ")


# ---------------------------------------------------------------------------
# 싱글톤 테스트
# ---------------------------------------------------------------------------


class TestSingleton:
    """reset_llm_adapter 테스트"""

    def test_reset(self):
        reset_llm_adapter()
        # After reset, next call should create new instance
        from app.services.llm_adapter import _llm_adapter
        assert _llm_adapter is None
