"""
Planner Node

사용자 쿼리를 분석하여 최적의 검색 전략을 결정합니다.
LLM을 활용하여 쿼리를 정제하고, keyword/semantic/hybrid 중
가장 적합한 검색 방법을 선택합니다.

STORY-033: LangGraph 기반 RAG 워크플로우 구현
"""

import json
import logging
from typing import Any, Callable, Dict, Optional

from ai_service.src.workflows.state import RAGState

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# System Prompt for Planner
# --------------------------------------------------------------------------

PLANNER_SYSTEM_PROMPT = """당신은 RAG 시스템의 쿼리 플래너입니다.
사용자의 질문을 분석하여 최적의 검색 전략을 결정합니다.

검색 전략 유형:
- "keyword": 정확한 키워드/용어/코드명 검색 (예: 특정 API명, 에러 코드, 파일명)
- "semantic": 의미 기반 검색 (예: 개념 설명, 방법론 질문, 비교 분석)
- "hybrid": 키워드 + 의미 결합 검색 (대부분의 기술 질문에 권장)

다음 JSON 형식으로 응답하세요:
{
    "search_strategy": "keyword" | "semantic" | "hybrid",
    "refined_query": "검색에 최적화된 쿼리 문자열",
    "reasoning": "전략 선택 이유 (한국어)"
}

규칙:
1. 특정 용어/코드가 포함된 질문은 "keyword" 또는 "hybrid"를 선택합니다.
2. 개념적/추상적 질문은 "semantic"을 선택합니다.
3. 대부분의 기술 질문은 "hybrid"가 가장 효과적입니다.
4. refined_query에서 불필요한 조사/접속사를 제거하고 핵심 키워드를 강조합니다.
5. 반드시 유효한 JSON만 출력하세요. 다른 텍스트는 포함하지 마세요.
"""

PLANNER_USER_TEMPLATE = """사용자 질문: {query}

위 질문에 대한 최적의 검색 전략을 결정해 주세요."""


class PlannerNode:
    """
    쿼리 분석 및 검색 전략 결정 노드

    LLM을 사용하여 사용자 쿼리를 분석하고, 최적의 검색 전략
    (keyword/semantic/hybrid)을 결정합니다. 또한 검색에 최적화된
    정제 쿼리(refined_query)를 생성합니다.

    Args:
        llm_call: LLM 호출 함수 (async callable).
            입력: system_prompt (str), user_message (str)
            출력: str (LLM 응답 텍스트)
        default_strategy: LLM 호출 실패 시 기본 검색 전략

    Example:
        >>> async def my_llm(system_prompt, user_message):
        ...     return '{"search_strategy": "hybrid", "refined_query": "...", "reasoning": "..."}'
        >>> planner = PlannerNode(llm_call=my_llm)
        >>> state = await planner({"query": "FastAPI 사용법", "steps": []})
    """

    def __init__(
        self,
        llm_call: Optional[Callable] = None,
        default_strategy: str = "hybrid",
    ):
        """
        초기화

        Args:
            llm_call: LLM 호출 비동기 함수
            default_strategy: 기본 검색 전략
        """
        self.llm_call = llm_call
        self.default_strategy = default_strategy

    async def __call__(self, state: RAGState) -> Dict[str, Any]:
        """
        Planner 노드 실행

        사용자 쿼리를 분석하여 검색 전략과 정제 쿼리를 결정합니다.

        Args:
            state: 현재 RAG 워크플로우 상태

        Returns:
            업데이트할 상태 딕셔너리:
                - search_strategy: 결정된 검색 전략
                - refined_query: 정제된 쿼리
                - steps: 실행 단계 기록 추가
                - error: 에러 발생 시 메시지
        """
        query = state.get("query", "")
        steps = list(state.get("steps", []))

        logger.info("PlannerNode - Analyzing query: '%s'", query[:80])

        if not query or not query.strip():
            logger.warning("PlannerNode - Empty query received")
            steps.append("planner:error:empty_query")
            return {
                "search_strategy": self.default_strategy,
                "refined_query": "",
                "steps": steps,
                "error": "Empty query provided",
            }

        try:
            if self.llm_call is not None:
                response_text = await self.llm_call(
                    PLANNER_SYSTEM_PROMPT,
                    PLANNER_USER_TEMPLATE.format(query=query),
                )
                parsed = self._parse_llm_response(response_text)
            else:
                # LLM 미설정 시 규칙 기반 분석
                parsed = self._rule_based_analysis(query)

            strategy = parsed.get("search_strategy", self.default_strategy)
            refined = parsed.get("refined_query", query)
            reasoning = parsed.get("reasoning", "")

            # 유효한 전략인지 검증
            if strategy not in ("keyword", "semantic", "hybrid"):
                logger.warning(
                    "PlannerNode - Invalid strategy '%s', using default", strategy
                )
                strategy = self.default_strategy

            steps.append(f"planner:strategy={strategy}")
            logger.info(
                "PlannerNode - Strategy: %s, Refined: '%s', Reason: %s",
                strategy, refined[:80], reasoning[:100],
            )

            return {
                "search_strategy": strategy,
                "refined_query": refined,
                "steps": steps,
            }

        except Exception as e:
            logger.error("PlannerNode - Error: %s", e)
            steps.append(f"planner:error:{type(e).__name__}")
            return {
                "search_strategy": self.default_strategy,
                "refined_query": query,
                "steps": steps,
                "error": f"Planner error: {e}",
            }

    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """
        LLM 응답을 JSON으로 파싱

        JSON 블록이 코드 펜스로 감싸져 있거나 추가 텍스트가 있는
        경우에도 안전하게 파싱합니다.

        Args:
            response_text: LLM 응답 원문

        Returns:
            파싱된 딕셔너리

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
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning("PlannerNode - JSON parse failed: %s", e)
            raise ValueError(f"Failed to parse planner response: {e}") from e

    def _rule_based_analysis(self, query: str) -> Dict[str, Any]:
        """
        규칙 기반 쿼리 분석 (LLM 미사용 시 폴백)

        간단한 휴리스틱으로 검색 전략을 결정합니다.

        Args:
            query: 사용자 쿼리

        Returns:
            분석 결과 딕셔너리
        """
        query_lower = query.lower()

        # 키워드 검색 패턴
        keyword_patterns = [
            "에러", "error", "exception", "코드", "code",
            "api", "함수", "function", "class", "파일",
            "버전", "version", "설정", "config",
        ]

        # 의미 검색 패턴
        semantic_patterns = [
            "설명", "explain", "이란", "무엇", "what",
            "어떻게", "how", "왜", "why", "비교",
            "차이", "장단점", "방법", "개념",
        ]

        keyword_score = sum(
            1 for p in keyword_patterns if p in query_lower
        )
        semantic_score = sum(
            1 for p in semantic_patterns if p in query_lower
        )

        if keyword_score > 0 and semantic_score > 0:
            strategy = "hybrid"
            reasoning = "키워드와 의미 패턴 모두 감지"
        elif keyword_score > semantic_score:
            strategy = "keyword"
            reasoning = "키워드 패턴 우세"
        elif semantic_score > keyword_score:
            strategy = "semantic"
            reasoning = "의미 패턴 우세"
        else:
            strategy = "hybrid"
            reasoning = "기본 하이브리드 전략"

        return {
            "search_strategy": strategy,
            "refined_query": query.strip(),
            "reasoning": reasoning,
        }
