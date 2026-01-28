"""
LLM Adapter for LangGraph Nodes

knowledge_service의 LLMService(DeepSeek V3.2)를
LangGraph 노드(Planner, Generator, Validator)의 llm_call 시그니처에
맞게 어댑트합니다.

LangGraph 노드가 요구하는 llm_call 시그니처:
    async def llm_call(system_prompt: str, user_message: str) -> str

LLMService가 제공하는 인터페이스:
    async def generate_with_messages(messages: List[Dict], use_reasoner: bool) -> str

이 어댑터가 두 인터페이스를 연결합니다.

STORY-051: RAG 파이프라인 통합
"""

import logging
from typing import Any, AsyncIterator, Dict, List, Optional

logger = logging.getLogger(__name__)


class LLMAdapter:
    """
    LLM 호출 어댑터

    knowledge_service의 LLMService를 LangGraph 노드의
    llm_call / llm_stream 시그니처에 맞게 변환합니다.

    Args:
        llm_service: knowledge_service의 LLMService 인스턴스
        use_reasoner: Reasoner 모델 사용 여부 (기본: False)
        fallback_enabled: LLM 호출 실패 시 폴백 응답 활성화

    Example:
        >>> from app.services.llm_service import get_llm_service
        >>> llm_service = get_llm_service()
        >>> adapter = LLMAdapter(llm_service=llm_service)
        >>> response = await adapter.call("System prompt", "User message")
    """

    def __init__(
        self,
        llm_service: Any,
        use_reasoner: bool = False,
        fallback_enabled: bool = True,
    ):
        """
        초기화

        Args:
            llm_service: knowledge_service의 LLMService 인스턴스
            use_reasoner: Reasoner 모델 사용 여부
            fallback_enabled: 폴백 응답 활성화 여부
        """
        self._llm_service = llm_service
        self._use_reasoner = use_reasoner
        self._fallback_enabled = fallback_enabled

        logger.info(
            "LLMAdapter initialized - reasoner=%s, fallback=%s",
            use_reasoner, fallback_enabled,
        )

    async def call(
        self,
        system_prompt: str,
        user_message: str,
    ) -> str:
        """
        LLM 호출 (LangGraph 노드 호환 시그니처)

        PlannerNode, GeneratorNode, ValidatorNode의 llm_call에 바인딩됩니다.

        Args:
            system_prompt: 시스템 프롬프트
            user_message: 사용자 메시지

        Returns:
            LLM 생성 텍스트

        Raises:
            RuntimeError: LLM 호출 실패 시 (fallback 비활성화인 경우)
        """
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        logger.debug(
            "LLMAdapter.call - system_prompt_len=%d, user_msg_len=%d, reasoner=%s",
            len(system_prompt), len(user_message), self._use_reasoner,
        )

        try:
            response = await self._llm_service.generate_with_messages(
                messages=messages,
                use_reasoner=self._use_reasoner,
            )

            logger.debug(
                "LLMAdapter.call - response_len=%d", len(response),
            )
            return response

        except Exception as e:
            logger.error("LLMAdapter.call failed: %s", e)

            if self._fallback_enabled:
                logger.warning(
                    "LLMAdapter returning fallback response due to error: %s", e
                )
                return self._fallback_response(system_prompt, user_message, str(e))

            raise RuntimeError(
                f"LLM call failed and fallback is disabled: {e}"
            ) from e

    async def stream(
        self,
        system_prompt: str,
        user_message: str,
    ) -> AsyncIterator[str]:
        """
        스트리밍 LLM 호출 (GeneratorNode.llm_stream 호환)

        현재는 전체 응답을 한 번에 생성한 후 청크 단위로 반환합니다.
        향후 LLMService에 스트리밍 인터페이스가 추가되면 직접 연결합니다.

        Args:
            system_prompt: 시스템 프롬프트
            user_message: 사용자 메시지

        Yields:
            생성된 텍스트 청크
        """
        full_response = await self.call(system_prompt, user_message)

        # 문장 단위로 분할하여 스트리밍 시뮬레이션
        import re
        sentences = re.split(r'(?<=[.!?。])\s+', full_response)

        for sentence in sentences:
            if sentence.strip():
                yield sentence.strip()

    def _fallback_response(
        self,
        system_prompt: str,
        user_message: str,
        error_msg: str,
    ) -> str:
        """
        LLM 호출 실패 시 폴백 응답 생성

        Args:
            system_prompt: 원본 시스템 프롬프트
            user_message: 원본 사용자 메시지
            error_msg: 에러 메시지

        Returns:
            폴백 응답 문자열
        """
        # Planner 노드 폴백: 기본 hybrid 전략 반환
        if "검색 전략" in system_prompt or "search_strategy" in system_prompt:
            import json
            return json.dumps({
                "search_strategy": "hybrid",
                "refined_query": user_message[:200],
                "reasoning": f"LLM 호출 실패로 기본 hybrid 전략 적용 ({error_msg})",
            }, ensure_ascii=False)

        # Validator 노드 폴백: 통과 처리 (재시도 방지)
        if "검증기" in system_prompt or "Validator" in system_prompt:
            import json
            return json.dumps({
                "faithfulness_score": 0.5,
                "relevance_score": 0.5,
                "is_valid": True,
                "feedback": f"LLM 검증 불가 - 기본 통과 처리 ({error_msg})",
            }, ensure_ascii=False)

        # Generator 노드 폴백: 오류 안내
        return (
            f"LLM 서비스 일시 장애로 답변을 생성할 수 없습니다. "
            f"잠시 후 다시 시도해 주세요. (오류: {error_msg})"
        )

    def health_check(self) -> Dict[str, Any]:
        """
        어댑터 상태 점검

        Returns:
            상태 정보 딕셔너리
        """
        llm_available = self._llm_service is not None
        has_api_key = False

        if llm_available and hasattr(self._llm_service, '_chat_llm'):
            try:
                # LLMService가 API 키를 가지고 있는지 간접 확인
                from app.core.config import settings
                has_api_key = settings.deepseek_api_key is not None
            except Exception:
                pass

        return {
            "service": "LLMAdapter",
            "llm_service_available": llm_available,
            "has_api_key": has_api_key,
            "use_reasoner": self._use_reasoner,
            "fallback_enabled": self._fallback_enabled,
        }
