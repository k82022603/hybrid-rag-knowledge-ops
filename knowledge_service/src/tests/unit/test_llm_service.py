"""
LLM Service 단위 테스트

DeepSeek API 실제 연결 테스트 포함.
DEEPSEEK_API_KEY 환경변수 필수.

TEST_MODE=docker pytest src/tests/unit/test_llm_service.py -v
"""

import os

import pytest

from app.core.config import settings
from app.core.exceptions import LLMError
from app.services.llm_service import LLMService, get_llm_service


# ---------------------------------------------------------------------------
# Skip 조건
# ---------------------------------------------------------------------------

skip_no_api_key = pytest.mark.skipif(
    not settings.deepseek_api_key,
    reason="DEEPSEEK_API_KEY not set",
)


# ---------------------------------------------------------------------------
# 초기화 테스트
# ---------------------------------------------------------------------------


class TestLLMServiceInit:
    """LLMService 초기화 테스트"""

    def test_init(self):
        svc = LLMService()
        assert svc._chat_llm is None
        assert svc._reasoner_llm is None

    @skip_no_api_key
    def test_chat_llm_lazy_init(self):
        """chat_llm 프로퍼티 접근 시 초기화"""
        svc = LLMService()
        llm = svc.chat_llm
        assert llm is not None
        assert llm.model_name == settings.deepseek_chat_model

    @skip_no_api_key
    def test_reasoner_llm_lazy_init(self):
        """reasoner_llm 프로퍼티 접근 시 초기화"""
        svc = LLMService()
        llm = svc.reasoner_llm
        assert llm is not None
        assert llm.model_name == settings.deepseek_reasoner_model

    def test_chat_llm_no_api_key(self):
        """API 키 없으면 LLMError"""
        svc = LLMService()
        # Temporarily unset key
        original = settings.deepseek_api_key
        try:
            settings.deepseek_api_key = None
            svc._chat_llm = None
            with pytest.raises(LLMError, match="DEEPSEEK_API_KEY"):
                _ = svc.chat_llm
        finally:
            settings.deepseek_api_key = original

    def test_reasoner_llm_no_api_key(self):
        """API 키 없으면 LLMError"""
        svc = LLMService()
        original = settings.deepseek_api_key
        try:
            settings.deepseek_api_key = None
            svc._reasoner_llm = None
            with pytest.raises(LLMError, match="DEEPSEEK_API_KEY"):
                _ = svc.reasoner_llm
        finally:
            settings.deepseek_api_key = original


# ---------------------------------------------------------------------------
# 실제 DeepSeek API 호출 테스트
# ---------------------------------------------------------------------------


class TestLLMGenerate:
    """실제 DeepSeek API 호출 테스트"""

    @skip_no_api_key
    @pytest.mark.asyncio
    async def test_generate_simple(self):
        """간단한 텍스트 생성"""
        svc = LLMService()
        result = await svc.generate("1+1의 결과를 숫자만 답하세요")
        assert result is not None
        assert len(result) > 0
        assert "2" in result

    @skip_no_api_key
    @pytest.mark.asyncio
    async def test_generate_korean(self):
        """한국어 응답 생성"""
        svc = LLMService()
        result = await svc.generate("대한민국의 수도는 어디입니까? 한 단어로만 답하세요")
        assert "서울" in result

    @skip_no_api_key
    @pytest.mark.asyncio
    async def test_generate_with_temperature(self):
        """temperature 파라미터 전달"""
        svc = LLMService()
        result = await svc.generate(
            "1+1의 결과를 숫자만 답하세요",
            temperature=0.0,
        )
        assert "2" in result

    @skip_no_api_key
    @pytest.mark.asyncio
    async def test_generate_with_messages(self):
        """메시지 기반 생성"""
        svc = LLMService()
        messages = [
            {"role": "system", "content": "당신은 수학 도우미입니다."},
            {"role": "user", "content": "3 x 4 = ? 숫자만 답하세요"},
        ]
        result = await svc.generate_with_messages(messages)
        assert "12" in result


# ---------------------------------------------------------------------------
# 싱글톤 테스트
# ---------------------------------------------------------------------------


class TestSingleton:
    """get_llm_service 싱글톤 테스트"""

    def test_singleton(self):
        s1 = get_llm_service()
        s2 = get_llm_service()
        assert s1 is s2

    def test_is_llm_service_instance(self):
        svc = get_llm_service()
        assert isinstance(svc, LLMService)
