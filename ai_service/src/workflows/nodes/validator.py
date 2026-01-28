"""
Validator Node

생성된 답변의 품질을 검증하는 노드입니다.
Faithfulness (충실도)와 Relevance (관련성)을 점수화하여
품질 기준을 만족하는지 확인합니다.

검증 실패 시 재검색(retry)을 트리거하거나, 사용자에게 경고를 반환합니다.

STORY-033: LangGraph 기반 RAG 워크플로우 구현
"""

import json
import logging
from typing import Any, Callable, Dict, Optional

from ai_service.src.workflows.state import RAGState, ValidationResult

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# System Prompt for Validator
# --------------------------------------------------------------------------

VALIDATOR_SYSTEM_PROMPT = """당신은 RAG 시스템의 답변 품질 검증기입니다.
생성된 답변이 제공된 컨텍스트에 충실하고, 사용자의 질문에 적절한지 평가합니다.

평가 기준:
1. Faithfulness (충실도): 답변이 컨텍스트에 기반하고 있는가? (0.0~1.0)
   - 1.0: 모든 내용이 컨텍스트에서 뒷받침됨
   - 0.5: 일부 내용이 컨텍스트에 없음
   - 0.0: 답변이 컨텍스트와 무관함

2. Relevance (관련성): 답변이 질문에 적절히 대응하는가? (0.0~1.0)
   - 1.0: 질문에 완벽하게 대응
   - 0.5: 부분적으로 대응
   - 0.0: 질문과 무관한 답변

다음 JSON 형식으로 응답하세요:
{
    "faithfulness_score": 0.0~1.0,
    "relevance_score": 0.0~1.0,
    "is_valid": true|false,
    "feedback": "검증 결과 피드백 (한국어)"
}

판정 기준:
- faithfulness_score >= 0.7 AND relevance_score >= 0.7 이면 is_valid=true
- 그 외에는 is_valid=false
"""

VALIDATOR_USER_TEMPLATE = """검증 대상:

[질문]
{query}

[컨텍스트]
{context}

[생성된 답변]
{answer}

위 답변의 충실도(Faithfulness)와 관련성(Relevance)을 평가해 주세요."""


class ValidatorNode:
    """
    응답 품질 검증 노드

    생성된 답변의 Faithfulness(충실도)와 Relevance(관련성)를
    평가하여 품질 기준을 만족하는지 확인합니다.

    검증 실패 시:
    - retry_count < max_retries: 재검색 트리거
    - retry_count >= max_retries: 경고와 함께 답변 반환

    Args:
        llm_call: LLM 호출 함수 (async callable).
            입력: system_prompt (str), user_message (str)
            출력: str (검증 결과 JSON)
        faithfulness_threshold: Faithfulness 최소 기준 (기본: 0.7)
        relevance_threshold: Relevance 최소 기준 (기본: 0.7)

    Example:
        >>> async def my_llm(system_prompt, user_message):
        ...     return '{"faithfulness_score": 0.9, "relevance_score": 0.85, ...}'
        >>> validator = ValidatorNode(llm_call=my_llm)
        >>> state = await validator({
        ...     "query": "...", "context": "...", "answer": "...",
        ...     "steps": [], "retry_count": 0, "max_retries": 2,
        ... })
    """

    def __init__(
        self,
        llm_call: Optional[Callable] = None,
        faithfulness_threshold: float = 0.7,
        relevance_threshold: float = 0.7,
    ):
        """
        초기화

        Args:
            llm_call: LLM 호출 비동기 함수
            faithfulness_threshold: Faithfulness 최소 기준
            relevance_threshold: Relevance 최소 기준
        """
        self.llm_call = llm_call
        self.faithfulness_threshold = faithfulness_threshold
        self.relevance_threshold = relevance_threshold

    async def __call__(self, state: RAGState) -> Dict[str, Any]:
        """
        Validator 노드 실행

        답변의 품질을 검증하고 결과를 상태에 반영합니다.

        Args:
            state: 현재 RAG 워크플로우 상태

        Returns:
            업데이트할 상태 딕셔너리:
                - validation_result: 검증 결과
                - retry_count: 업데이트된 재시도 횟수
                - steps: 실행 단계 기록 추가
                - error: 에러 발생 시 메시지
        """
        query = state.get("query", "")
        context = state.get("context", "")
        answer = state.get("answer", "")
        steps = list(state.get("steps", []))
        retry_count = state.get("retry_count", 0)

        logger.info(
            "ValidatorNode - Query: '%s', Answer length: %d, Retry: %d",
            query[:80], len(answer), retry_count,
        )

        # 답변이 없으면 검증 불가
        if not answer or not answer.strip():
            logger.warning("ValidatorNode - Empty answer")
            validation: ValidationResult = {
                "is_valid": False,
                "faithfulness_score": 0.0,
                "relevance_score": 0.0,
                "feedback": "답변이 비어 있습니다.",
            }
            steps.append("validator:fail:empty_answer")
            return {
                "validation_result": validation,
                "retry_count": retry_count + 1,
                "steps": steps,
            }

        try:
            if self.llm_call is not None:
                user_message = VALIDATOR_USER_TEMPLATE.format(
                    query=query,
                    context=context[:4000],  # 컨텍스트 길이 제한
                    answer=answer[:2000],
                )
                response_text = await self.llm_call(
                    VALIDATOR_SYSTEM_PROMPT,
                    user_message,
                )
                validation = self._parse_validation_response(response_text)
            else:
                # LLM 미설정 시 규칙 기반 검증
                validation = self._rule_based_validation(
                    query, context, answer
                )

            # 임계값 기반 최종 판정
            is_valid = (
                validation.get("faithfulness_score", 0.0) >= self.faithfulness_threshold
                and validation.get("relevance_score", 0.0) >= self.relevance_threshold
            )
            validation["is_valid"] = is_valid

            if is_valid:
                steps.append(
                    f"validator:pass:f={validation.get('faithfulness_score', 0):.2f},"
                    f"r={validation.get('relevance_score', 0):.2f}"
                )
                logger.info(
                    "ValidatorNode - PASS: Faithfulness=%.2f, Relevance=%.2f",
                    validation.get("faithfulness_score", 0),
                    validation.get("relevance_score", 0),
                )
            else:
                steps.append(
                    f"validator:fail:f={validation.get('faithfulness_score', 0):.2f},"
                    f"r={validation.get('relevance_score', 0):.2f}"
                )
                logger.warning(
                    "ValidatorNode - FAIL: Faithfulness=%.2f, Relevance=%.2f, "
                    "Feedback: %s",
                    validation.get("faithfulness_score", 0),
                    validation.get("relevance_score", 0),
                    validation.get("feedback", ""),
                )

            result: Dict[str, Any] = {
                "validation_result": validation,
                "steps": steps,
            }

            if not is_valid:
                result["retry_count"] = retry_count + 1

            return result

        except Exception as e:
            logger.error("ValidatorNode - Error: %s", e)
            steps.append(f"validator:error:{type(e).__name__}")
            validation = {
                "is_valid": False,
                "faithfulness_score": 0.0,
                "relevance_score": 0.0,
                "feedback": f"Validation error: {e}",
            }
            return {
                "validation_result": validation,
                "retry_count": retry_count + 1,
                "steps": steps,
                "error": f"Validation error: {e}",
            }

    def _parse_validation_response(
        self, response_text: str
    ) -> ValidationResult:
        """
        LLM 검증 응답을 파싱

        Args:
            response_text: LLM 응답 원문

        Returns:
            ValidationResult 딕셔너리

        Raises:
            ValueError: JSON 파싱 실패
        """
        text = response_text.strip()

        # 코드 펜스 제거
        if "```json" in text:
            text = text.split("```json", 1)[1]
            if "```" in text:
                text = text.split("```", 1)[0]
        elif "```" in text:
            text = text.split("```", 1)[1]
            if "```" in text:
                text = text.split("```", 1)[0]

        text = text.strip()

        # JSON 객체 추출
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            text = text[start:end]

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning("ValidatorNode - JSON parse failed: %s", e)
            raise ValueError(
                f"Failed to parse validation response: {e}"
            ) from e

        # 값 검증 및 정규화
        faithfulness = max(0.0, min(1.0, float(
            parsed.get("faithfulness_score", 0.0)
        )))
        relevance = max(0.0, min(1.0, float(
            parsed.get("relevance_score", 0.0)
        )))

        return {
            "faithfulness_score": faithfulness,
            "relevance_score": relevance,
            "is_valid": parsed.get("is_valid", False),
            "feedback": parsed.get("feedback", ""),
        }

    def _rule_based_validation(
        self, query: str, context: str, answer: str
    ) -> ValidationResult:
        """
        규칙 기반 답변 검증 (LLM 미사용 시 폴백)

        간단한 휴리스틱으로 답변의 품질을 평가합니다.

        Args:
            query: 사용자 쿼리
            context: 컨텍스트 문자열
            answer: 생성된 답변

        Returns:
            ValidationResult 딕셔너리
        """
        # Faithfulness: 답변 내 단어가 컨텍스트에 얼마나 포함되는지
        answer_words = set(answer.lower().split())
        context_words = set(context.lower().split())

        if answer_words:
            overlap = len(answer_words & context_words)
            faithfulness = min(1.0, overlap / max(len(answer_words), 1))
        else:
            faithfulness = 0.0

        # Relevance: 쿼리 키워드가 답변에 포함되는지
        query_words = set(query.lower().split())
        if query_words:
            query_overlap = len(query_words & answer_words)
            relevance = min(1.0, query_overlap / max(len(query_words), 1))
        else:
            relevance = 0.0

        is_valid = (
            faithfulness >= self.faithfulness_threshold
            and relevance >= self.relevance_threshold
        )

        feedback_parts = []
        if faithfulness < self.faithfulness_threshold:
            feedback_parts.append(
                f"충실도 부족 ({faithfulness:.2f} < {self.faithfulness_threshold})"
            )
        if relevance < self.relevance_threshold:
            feedback_parts.append(
                f"관련성 부족 ({relevance:.2f} < {self.relevance_threshold})"
            )
        if is_valid:
            feedback_parts.append("검증 통과")

        return {
            "faithfulness_score": round(faithfulness, 4),
            "relevance_score": round(relevance, 4),
            "is_valid": is_valid,
            "feedback": "; ".join(feedback_parts) if feedback_parts else "검증 완료",
        }
