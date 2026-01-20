"""
LLM 서비스 모듈

DeepSeek API 연동 및 LLM 호출 관리
"""

from typing import Any, Dict, List, Optional

from langchain_openai import ChatOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.exceptions import LLMError, LLMRateLimitError, LLMTimeoutError
from app.core.logging import get_logger

logger = get_logger(__name__)


class LLMService:
    """
    LLM 서비스

    DeepSeek API를 사용한 LLM 호출 관리
    - Chat 모델 (빠른 응답)
    - Reasoner 모델 (복잡한 추론)
    """

    def __init__(self):
        """초기화"""
        self._chat_llm: Optional[ChatOpenAI] = None
        self._reasoner_llm: Optional[ChatOpenAI] = None

    @property
    def chat_llm(self) -> ChatOpenAI:
        """Chat LLM 인스턴스 (lazy loading)"""
        if self._chat_llm is None:
            if not settings.deepseek_api_key:
                raise LLMError("DEEPSEEK_API_KEY가 설정되지 않았습니다")

            self._chat_llm = ChatOpenAI(
                model=settings.deepseek_chat_model,
                base_url=settings.deepseek_base_url,
                api_key=settings.deepseek_api_key,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
                timeout=settings.llm_timeout,
            )
        return self._chat_llm

    @property
    def reasoner_llm(self) -> ChatOpenAI:
        """Reasoner LLM 인스턴스 (lazy loading)"""
        if self._reasoner_llm is None:
            if not settings.deepseek_api_key:
                raise LLMError("DEEPSEEK_API_KEY가 설정되지 않았습니다")

            self._reasoner_llm = ChatOpenAI(
                model=settings.deepseek_reasoner_model,
                base_url=settings.deepseek_base_url,
                api_key=settings.deepseek_api_key,
                temperature=0.0,  # Reasoner는 항상 0
                max_tokens=settings.llm_max_tokens,
                timeout=settings.llm_timeout * 2,  # Reasoner는 더 긴 타임아웃
            )
        return self._reasoner_llm

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def generate(
        self,
        prompt: str,
        use_reasoner: bool = False,
        temperature: Optional[float] = None,
    ) -> str:
        """
        LLM 응답 생성

        Args:
            prompt: 프롬프트
            use_reasoner: Reasoner 모델 사용 여부
            temperature: 온도 (기본값 사용 시 None)

        Returns:
            생성된 텍스트

        Raises:
            LLMError: LLM 호출 실패
            LLMTimeoutError: 타임아웃
            LLMRateLimitError: Rate limit 초과
        """
        llm = self.reasoner_llm if use_reasoner else self.chat_llm

        if temperature is not None:
            llm = llm.with_config({"temperature": temperature})

        logger.info(f"LLM generate - Model: {llm.model_name}, Prompt length: {len(prompt)}")

        try:
            response = await llm.ainvoke(prompt)
            return response.content

        except Exception as e:
            error_msg = str(e).lower()

            if "timeout" in error_msg:
                raise LLMTimeoutError(timeout=settings.llm_timeout)
            elif "rate" in error_msg or "429" in error_msg:
                raise LLMRateLimitError()
            else:
                raise LLMError(f"LLM 호출 실패: {e}")

    async def generate_with_messages(
        self,
        messages: List[Dict[str, str]],
        use_reasoner: bool = False,
    ) -> str:
        """
        메시지 기반 LLM 응답 생성

        Args:
            messages: 메시지 목록 [{"role": "user", "content": "..."}]
            use_reasoner: Reasoner 모델 사용 여부

        Returns:
            생성된 텍스트
        """
        llm = self.reasoner_llm if use_reasoner else self.chat_llm

        logger.info(f"LLM generate with messages - Count: {len(messages)}")

        try:
            response = await llm.ainvoke(messages)
            return response.content

        except Exception as e:
            raise LLMError(f"LLM 호출 실패: {e}")


# 싱글톤 인스턴스
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """LLM 서비스 인스턴스 반환"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
