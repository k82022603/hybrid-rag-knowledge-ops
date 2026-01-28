"""
RAG Workflow

LangGraph StateGraph 기반 RAG 워크플로우입니다.
Planner -> Retriever -> Generator -> Validator 파이프라인을 구현하며,
Validator 실패 시 조건부 재검색(retry)을 지원합니다.

Architecture:
    START -> planner -> retriever -> generator -> validator
                 ^                                    |
                 |         (fail, retry < max)         |
                 +------------------------------------+
                                                      |
                                            (pass or max retry)
                                                      |
                                                     END

STORY-033: LangGraph 기반 RAG 워크플로우 구현
"""

import logging
from typing import Any, AsyncIterator, Callable, Dict, Literal, Optional

from langgraph.graph import END, START, StateGraph

from ai_service.src.workflows.nodes.generator import GeneratorNode
from ai_service.src.workflows.nodes.planner import PlannerNode
from ai_service.src.workflows.nodes.retriever import RetrieverNode
from ai_service.src.workflows.nodes.validator import ValidatorNode
from ai_service.src.workflows.state import RAGState

logger = logging.getLogger(__name__)


def _should_retry(state: RAGState) -> Literal["retriever", "__end__"]:
    """
    Validator 후 조건부 분기 함수

    검증 결과에 따라 재검색을 수행하거나 워크플로우를 종료합니다.

    Decision logic:
    - validation_result.is_valid == True -> END
    - retry_count >= max_retries -> END
    - Otherwise -> retriever (재검색)

    Args:
        state: 현재 RAG 워크플로우 상태

    Returns:
        다음 노드 이름 ("retriever" 또는 "__end__")
    """
    validation = state.get("validation_result")
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)

    if validation and validation.get("is_valid", False):
        logger.info("Workflow routing: validator -> END (validation passed)")
        return "__end__"

    if retry_count >= max_retries:
        logger.warning(
            "Workflow routing: validator -> END (max retries %d reached)",
            max_retries,
        )
        return "__end__"

    logger.info(
        "Workflow routing: validator -> retriever (retry %d/%d)",
        retry_count, max_retries,
    )
    return "retriever"


class RAGWorkflow:
    """
    LangGraph 기반 RAG 워크플로우

    Planner -> Retriever -> Generator -> Validator 파이프라인을
    StateGraph로 구현합니다. Validator 실패 시 조건부 재검색을
    최대 max_retries 회 수행합니다.

    Args:
        planner: PlannerNode 인스턴스
        retriever: RetrieverNode 인스턴스
        generator: GeneratorNode 인스턴스
        validator: ValidatorNode 인스턴스
        max_retries: 최대 재시도 횟수 (기본: 2)

    Example:
        >>> workflow = RAGWorkflow(
        ...     planner=PlannerNode(llm_call=my_llm),
        ...     retriever=RetrieverNode(retrieve_fn=my_search),
        ...     generator=GeneratorNode(llm_call=my_llm),
        ...     validator=ValidatorNode(llm_call=my_llm),
        ... )
        >>> result = await workflow.invoke("FastAPI 사용법은?")
        >>> print(result["answer"])

    Attributes:
        planner: PlannerNode
        retriever: RetrieverNode
        generator: GeneratorNode
        validator: ValidatorNode
        max_retries: 최대 재시도 횟수
        graph: 컴파일된 StateGraph
    """

    def __init__(
        self,
        planner: Optional[PlannerNode] = None,
        retriever: Optional[RetrieverNode] = None,
        generator: Optional[GeneratorNode] = None,
        validator: Optional[ValidatorNode] = None,
        max_retries: int = 2,
    ):
        """
        초기화

        Args:
            planner: PlannerNode 인스턴스 (None이면 기본 생성)
            retriever: RetrieverNode 인스턴스 (None이면 기본 생성)
            generator: GeneratorNode 인스턴스 (None이면 기본 생성)
            validator: ValidatorNode 인스턴스 (None이면 기본 생성)
            max_retries: 최대 재시도 횟수
        """
        self.planner = planner or PlannerNode()
        self.retriever = retriever or RetrieverNode()
        self.generator = generator or GeneratorNode()
        self.validator = validator or ValidatorNode()
        self.max_retries = max_retries

        self.graph = self._build_graph()

    def _build_graph(self) -> Any:
        """
        StateGraph 구성 및 컴파일

        노드와 엣지를 설정하여 RAG 파이프라인 그래프를 만듭니다.

        Returns:
            컴파일된 StateGraph 인스턴스
        """
        builder = StateGraph(RAGState)

        # 노드 등록
        builder.add_node("planner", self.planner)
        builder.add_node("retriever", self.retriever)
        builder.add_node("generator", self.generator)
        builder.add_node("validator", self.validator)

        # 엣지 설정
        builder.add_edge(START, "planner")
        builder.add_edge("planner", "retriever")
        builder.add_edge("retriever", "generator")
        builder.add_edge("generator", "validator")

        # 조건부 엣지: Validator 결과에 따라 분기
        builder.add_conditional_edges(
            "validator",
            _should_retry,
            {
                "retriever": "retriever",
                "__end__": END,
            },
        )

        return builder.compile()

    async def invoke(
        self,
        query: str,
        conversation_history: Optional[list] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> RAGState:
        """
        RAG 워크플로우 실행

        쿼리를 입력받아 전체 파이프라인을 실행하고 결과를 반환합니다.

        Args:
            query: 사용자 질문
            conversation_history: 대화 이력 (멀티턴)
            config: LangGraph 실행 설정

        Returns:
            완료된 RAGState 딕셔너리

        Raises:
            ValueError: 빈 쿼리
        """
        if not query or not query.strip():
            raise ValueError("Query must not be empty")

        initial_state: RAGState = {
            "query": query,
            "conversation_history": conversation_history or [],
            "search_strategy": "hybrid",
            "refined_query": "",
            "documents": [],
            "context": "",
            "answer": "",
            "sources": [],
            "steps": [],
            "error": None,
            "validation_result": None,
            "retry_count": 0,
            "max_retries": self.max_retries,
        }

        logger.info("RAGWorkflow.invoke - Query: '%s'", query[:80])

        result = await self.graph.ainvoke(initial_state, config=config)

        logger.info(
            "RAGWorkflow complete - Steps: %s, Retries: %d, Valid: %s",
            len(result.get("steps", [])),
            result.get("retry_count", 0),
            result.get("validation_result", {}).get("is_valid", "N/A")
            if result.get("validation_result") else "N/A",
        )

        return result

    async def astream(
        self,
        query: str,
        conversation_history: Optional[list] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        RAG 워크플로우 스트리밍 실행

        각 노드의 실행 결과를 순차적으로 스트리밍합니다.

        Args:
            query: 사용자 질문
            conversation_history: 대화 이력
            config: LangGraph 실행 설정

        Yields:
            Dict[str, Any]: 각 노드의 출력 상태 업데이트

        Raises:
            ValueError: 빈 쿼리
        """
        if not query or not query.strip():
            raise ValueError("Query must not be empty")

        initial_state: RAGState = {
            "query": query,
            "conversation_history": conversation_history or [],
            "search_strategy": "hybrid",
            "refined_query": "",
            "documents": [],
            "context": "",
            "answer": "",
            "sources": [],
            "steps": [],
            "error": None,
            "validation_result": None,
            "retry_count": 0,
            "max_retries": self.max_retries,
        }

        logger.info("RAGWorkflow.astream - Query: '%s'", query[:80])

        async for event in self.graph.astream(initial_state, config=config):
            yield event

    def get_graph_info(self) -> Dict[str, Any]:
        """
        워크플로우 그래프 정보 반환

        Returns:
            그래프 메타 정보 딕셔너리
        """
        return {
            "name": "RAGWorkflow",
            "nodes": ["planner", "retriever", "generator", "validator"],
            "edges": [
                ("START", "planner"),
                ("planner", "retriever"),
                ("retriever", "generator"),
                ("generator", "validator"),
                ("validator", "retriever (conditional: retry)"),
                ("validator", "END (conditional: pass/max_retry)"),
            ],
            "max_retries": self.max_retries,
        }
