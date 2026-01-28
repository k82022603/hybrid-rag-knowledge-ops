"""
LLM Service Adapter 모듈

Adapter 패턴으로 DeepSeek LLM 호출을 래핑
- 비동기 인터페이스: generate(prompt, context, **kwargs) -> str
- 타임아웃 핸들링 (60초)
- 에러 변환 (HTTP 상태 코드 매핑)
- 재시도 로직 (tenacity)
- LangGraph 워크플로우에서 사용

STORY-051: RAG 파이프라인 통합 (Day 2)
"""

import asyncio
import time
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.exceptions import (
    KnowledgeServiceError,
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from app.core.logging import get_logger
from app.services.llm_service import LLMService, get_llm_service

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# 에러 변환 유틸리티
# ---------------------------------------------------------------------------


class ServiceConnectionError(KnowledgeServiceError):
    """외부 서비스 연결 실패 예외 (502 Bad Gateway)"""

    def __init__(
        self,
        service_name: str,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message or f"{service_name} 서비스에 연결할 수 없습니다",
            error_code="SERVICE_CONNECTION_ERROR",
            status_code=502,
            details={**(details or {}), "service": service_name},
        )


class ServiceTimeoutError(KnowledgeServiceError):
    """외부 서비스 타임아웃 예외 (504 Gateway Timeout)"""

    def __init__(
        self,
        service_name: str,
        timeout_seconds: int,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message or f"{service_name} 응답 시간이 초과되었습니다 ({timeout_seconds}초)",
            error_code="SERVICE_TIMEOUT",
            status_code=504,
            details={
                **(details or {}),
                "service": service_name,
                "timeout_seconds": timeout_seconds,
            },
        )


class ServiceRateLimitError(KnowledgeServiceError):
    """외부 서비스 Rate Limit 예외 (429 Too Many Requests)"""

    def __init__(
        self,
        service_name: str,
        retry_after: Optional[int] = None,
        message: Optional[str] = None,
    ):
        super().__init__(
            message=message or f"{service_name} API 호출 한도를 초과했습니다",
            error_code="SERVICE_RATE_LIMIT",
            status_code=429,
            details={
                "service": service_name,
                "retry_after_seconds": retry_after,
            },
        )


class ServiceValidationError(KnowledgeServiceError):
    """입력 검증 실패 예외 (400 Bad Request)"""

    def __init__(
        self,
        message: str = "입력값이 유효하지 않습니다",
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=400,
            details={**(details or {}), "field": field} if field else details,
        )


# ---------------------------------------------------------------------------
# 에러 변환 함수
# ---------------------------------------------------------------------------


def translate_llm_error(error: Exception) -> KnowledgeServiceError:
    """
    LLM 예외를 HTTP 상태 코드에 매핑된 서비스 예외로 변환

    Args:
        error: 원본 예외

    Returns:
        HTTP 상태 코드가 매핑된 KnowledgeServiceError 하위 클래스

    Mapping:
        - LLMTimeoutError -> 504 Gateway Timeout
        - LLMRateLimitError -> 429 Too Many Requests
        - ConnectionError/OSError -> 502 Bad Gateway
        - asyncio.TimeoutError -> 504 Gateway Timeout
        - LLMError -> 502 Bad Gateway
        - Other -> 500 Internal Server Error
    """
    error_msg = str(error).lower()

    # 타임아웃 에러
    if isinstance(error, (LLMTimeoutError, asyncio.TimeoutError)):
        return ServiceTimeoutError(
            service_name="LLM (DeepSeek)",
            timeout_seconds=settings.llm_timeout,
        )

    # Rate Limit 에러
    if isinstance(error, LLMRateLimitError):
        return ServiceRateLimitError(
            service_name="LLM (DeepSeek)",
        )

    # 연결 오류
    if isinstance(error, (ConnectionError, OSError)):
        return ServiceConnectionError(
            service_name="LLM (DeepSeek)",
            message=f"LLM 서비스 연결 실패: {str(error)}",
        )

    # 문자열 패턴 기반 변환
    if "timeout" in error_msg or "timed out" in error_msg:
        return ServiceTimeoutError(
            service_name="LLM (DeepSeek)",
            timeout_seconds=settings.llm_timeout,
        )

    if "rate" in error_msg or "429" in error_msg or "too many" in error_msg:
        return ServiceRateLimitError(
            service_name="LLM (DeepSeek)",
        )

    if "connection" in error_msg or "refused" in error_msg or "unreachable" in error_msg:
        return ServiceConnectionError(
            service_name="LLM (DeepSeek)",
            message=f"LLM 서비스 연결 실패: {str(error)}",
        )

    # 일반 LLM 에러
    if isinstance(error, LLMError):
        return ServiceConnectionError(
            service_name="LLM (DeepSeek)",
            message=f"LLM 호출 실패: {str(error)}",
        )

    # 기타 에러
    return KnowledgeServiceError(
        message=f"LLM 처리 중 예기치 않은 오류: {str(error)}",
        error_code="LLM_UNKNOWN_ERROR",
        status_code=500,
    )


# ---------------------------------------------------------------------------
# LLMAdapter
# ---------------------------------------------------------------------------


class LLMAdapter:
    """
    LLM Service Adapter

    DeepSeek LLM 호출을 래핑하여 통일된 인터페이스를 제공합니다.
    LangGraph 워크플로우의 Generator 노드에서 사용됩니다.

    Features:
        - 비동기 generate() 인터페이스
        - 타임아웃 핸들링 (asyncio.wait_for)
        - 에러 변환 (LLM 예외 -> HTTP 상태 코드)
        - 시스템 프롬프트 관리

    Usage:
        adapter = LLMAdapter()
        answer = await adapter.generate(
            prompt="사용자 질문",
            context="검색된 컨텍스트",
        )
    """

    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        system_prompt: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ):
        """
        초기화

        Args:
            llm_service: LLMService 인스턴스 (None이면 싱글톤 사용)
            system_prompt: 시스템 프롬프트 (None이면 기본 프롬프트)
            timeout_seconds: 타임아웃 (None이면 settings.llm_timeout)
        """
        self._llm_service = llm_service
        self._system_prompt = system_prompt or self._default_system_prompt()
        self._timeout = timeout_seconds or settings.llm_timeout

    @property
    def llm_service(self) -> LLMService:
        """LLMService 지연 초기화"""
        if self._llm_service is None:
            self._llm_service = get_llm_service()
        return self._llm_service

    @staticmethod
    def _default_system_prompt() -> str:
        """기본 시스템 프롬프트"""
        return (
            "당신은 사내 지식 검색 시스템의 AI 어시스턴트입니다.\n"
            "주어진 컨텍스트 정보를 바탕으로 사용자의 질문에 정확하고 "
            "도움이 되는 답변을 제공합니다.\n\n"
            "## 답변 규칙\n"
            "1. 반드시 제공된 컨텍스트 내용에 근거하여 답변합니다.\n"
            "2. 컨텍스트에 없는 내용은 추측하지 않고 "
            '"해당 정보를 찾을 수 없습니다"라고 안내합니다.\n'
            "3. 답변에 사용한 문서의 출처를 [출처N] 형태로 표기합니다.\n"
            "4. 복잡한 답변은 목록, 소제목 등으로 구조화합니다.\n"
            "5. 답변은 한국어로 제공합니다."
        )

    async def generate(
        self,
        prompt: str,
        context: str = "",
        use_reasoner: bool = False,
        **kwargs: Any,
    ) -> str:
        """
        LLM 답변 생성

        컨텍스트와 프롬프트를 조합하여 LLM 호출을 수행합니다.
        타임아웃 및 에러 변환을 포함합니다.

        Args:
            prompt: 사용자 질문 또는 프롬프트
            context: 검색된 컨텍스트 문자열
            use_reasoner: Reasoner 모델 사용 여부
            **kwargs: 추가 파라미터 (temperature 등)

        Returns:
            생성된 답변 문자열

        Raises:
            ServiceTimeoutError: 타임아웃 (504)
            ServiceRateLimitError: Rate Limit 초과 (429)
            ServiceConnectionError: 연결 실패 (502)
            ServiceValidationError: 입력 검증 실패 (400)
        """
        # 입력 검증
        if not prompt or not prompt.strip():
            raise ServiceValidationError(
                message="프롬프트가 비어 있습니다",
                field="prompt",
            )

        start_time = time.monotonic()

        logger.info(
            "LLM Adapter generate - Prompt length: %d, Context length: %d, "
            "Reasoner: %s, Timeout: %ds",
            len(prompt), len(context), use_reasoner, self._timeout,
        )

        # 메시지 구성
        messages = self._build_messages(prompt=prompt, context=context)

        try:
            # 타임아웃 래핑
            answer = await asyncio.wait_for(
                self.llm_service.generate_with_messages(
                    messages=messages,
                    use_reasoner=use_reasoner,
                ),
                timeout=self._timeout,
            )

            latency_ms = (time.monotonic() - start_time) * 1000

            logger.info(
                "LLM Adapter generate complete - "
                "Answer length: %d, Latency: %.1fms",
                len(answer), latency_ms,
            )

            return answer

        except asyncio.TimeoutError:
            latency_ms = (time.monotonic() - start_time) * 1000
            logger.error(
                "LLM Adapter timeout after %.1fms (limit: %ds)",
                latency_ms, self._timeout,
            )
            raise ServiceTimeoutError(
                service_name="LLM (DeepSeek)",
                timeout_seconds=self._timeout,
            )

        except (LLMTimeoutError, LLMRateLimitError, LLMError) as e:
            latency_ms = (time.monotonic() - start_time) * 1000
            logger.error(
                "LLM Adapter error after %.1fms: %s", latency_ms, e,
            )
            raise translate_llm_error(e)

        except Exception as e:
            latency_ms = (time.monotonic() - start_time) * 1000
            logger.exception(
                "LLM Adapter unexpected error after %.1fms: %s",
                latency_ms, e,
            )
            raise translate_llm_error(e)

    async def generate_with_messages(
        self,
        messages: List[Dict[str, str]],
        use_reasoner: bool = False,
    ) -> str:
        """
        메시지 기반 LLM 답변 생성

        사전 구성된 메시지 목록으로 LLM 호출을 수행합니다.

        Args:
            messages: 메시지 목록 [{"role": "...", "content": "..."}]
            use_reasoner: Reasoner 모델 사용 여부

        Returns:
            생성된 답변 문자열

        Raises:
            ServiceTimeoutError: 타임아웃 (504)
            ServiceRateLimitError: Rate Limit 초과 (429)
            ServiceConnectionError: 연결 실패 (502)
        """
        start_time = time.monotonic()

        try:
            answer = await asyncio.wait_for(
                self.llm_service.generate_with_messages(
                    messages=messages,
                    use_reasoner=use_reasoner,
                ),
                timeout=self._timeout,
            )

            latency_ms = (time.monotonic() - start_time) * 1000
            logger.info(
                "LLM Adapter message-based generate - "
                "Answer length: %d, Latency: %.1fms",
                len(answer), latency_ms,
            )
            return answer

        except asyncio.TimeoutError:
            raise ServiceTimeoutError(
                service_name="LLM (DeepSeek)",
                timeout_seconds=self._timeout,
            )

        except Exception as e:
            raise translate_llm_error(e)

    def _build_messages(
        self,
        prompt: str,
        context: str = "",
    ) -> List[Dict[str, str]]:
        """
        LLM 호출용 메시지 구성

        Args:
            prompt: 사용자 질문
            context: 검색된 컨텍스트

        Returns:
            메시지 목록
        """
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": self._system_prompt},
        ]

        if context.strip():
            user_content = (
                f"## 컨텍스트 정보\n\n{context}\n\n---\n\n"
                f"## 사용자 질문\n\n{prompt}\n\n---\n\n"
                "위 컨텍스트를 참고하여 사용자 질문에 답변해주세요.\n"
                "답변에 사용한 출처를 [출처N] 형태로 표기해주세요."
            )
        else:
            user_content = prompt

        messages.append({"role": "user", "content": user_content})

        return messages


# ---------------------------------------------------------------------------
# 싱글톤 인스턴스
# ---------------------------------------------------------------------------

_llm_adapter: Optional[LLMAdapter] = None


def get_llm_adapter() -> LLMAdapter:
    """LLMAdapter 인스턴스 반환 (싱글톤)"""
    global _llm_adapter
    if _llm_adapter is None:
        _llm_adapter = LLMAdapter()
    return _llm_adapter


def reset_llm_adapter() -> None:
    """싱글톤 인스턴스 초기화 (테스트용)"""
    global _llm_adapter
    _llm_adapter = None
