"""
VIP 3단계 LangGraph 에이전트

Value-Intelligent-Planning 아키텍처 기반 RAG 파이프라인
"""

from typing import Any, Dict, List, Optional

from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from app.agents.state import (
    AgentState,
    DocumentMetadata,
    Entity,
    ExtractionResult,
    Relationship,
    SearchResult,
)
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class VIPAgent:
    """
    VIP 3단계 LangGraph 에이전트

    Stage 1 (Value): 엔티티 추출 + Gleaning
    Stage 2 (Intelligent): Hybrid 검색 + RRF 융합
    Stage 3 (Planning): 답변 합성
    """

    def __init__(self):
        """에이전트 초기화"""
        self._llm: Optional[ChatOpenAI] = None
        self._graph: Optional[StateGraph] = None

    @property
    def llm(self) -> ChatOpenAI:
        """LLM 인스턴스 (lazy loading)"""
        if self._llm is None:
            if not settings.deepseek_api_key:
                raise ValueError("DEEPSEEK_API_KEY가 설정되지 않았습니다")

            self._llm = ChatOpenAI(
                model=settings.deepseek_chat_model,
                base_url=settings.deepseek_base_url,
                api_key=settings.deepseek_api_key,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
                timeout=settings.llm_timeout,
            )
        return self._llm

    def build_graph(self) -> StateGraph:
        """LangGraph 워크플로우 빌드"""
        if self._graph is not None:
            return self._graph

        # 상태 그래프 생성
        workflow = StateGraph(AgentState)

        # 노드 추가
        workflow.add_node("extract_entities", self._extract_entities)
        workflow.add_node("gleaning", self._gleaning)
        workflow.add_node("hybrid_search", self._hybrid_search)
        workflow.add_node("rrf_fusion", self._rrf_fusion)
        workflow.add_node("synthesize_answer", self._synthesize_answer)

        # 엣지 정의
        workflow.set_entry_point("extract_entities")

        # Stage 1 -> Gleaning 또는 Stage 2
        workflow.add_conditional_edges(
            "extract_entities",
            self._should_gleaning,
            {
                "gleaning": "gleaning",
                "search": "hybrid_search",
            },
        )

        # Gleaning -> 다시 확인 또는 Stage 2
        workflow.add_conditional_edges(
            "gleaning",
            self._should_gleaning,
            {
                "gleaning": "gleaning",
                "search": "hybrid_search",
            },
        )

        # Stage 2: 검색 -> 융합
        workflow.add_edge("hybrid_search", "rrf_fusion")

        # Stage 3: 융합 -> 답변 합성 -> 종료
        workflow.add_edge("rrf_fusion", "synthesize_answer")
        workflow.add_edge("synthesize_answer", END)

        self._graph = workflow.compile()
        return self._graph

    async def process(
        self,
        query: str,
        document_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        VIP 파이프라인 실행

        Args:
            query: 사용자 질의
            document_text: 처리할 문서 텍스트 (옵션)

        Returns:
            처리 결과 (answer, sources, metadata)
        """
        graph = self.build_graph()

        initial_state: AgentState = {
            "query": query,
            "document_text": document_text,
            "extracted_entities": [],
            "extracted_relationships": [],
            "document_metadata": None,
            "gleaning_count": 0,
            "search_strategy": "hybrid",
            "vector_results": [],
            "graph_results": [],
            "fused_results": [],
            "reranked_results": [],
            "context": "",
            "answer": "",
            "sources": [],
            "error": None,
            "messages": [],
        }

        logger.info(f"VIP Pipeline started - Query: {query[:100]}...")

        # 그래프 실행
        result = await graph.ainvoke(initial_state)

        logger.info("VIP Pipeline completed")

        return {
            "answer": result.get("answer", ""),
            "sources": result.get("sources", []),
            "entities": result.get("extracted_entities", []),
            "metadata": result.get("document_metadata"),
        }

    # Stage 1: Value (엔티티 추출)
    async def _extract_entities(self, state: AgentState) -> AgentState:
        """Stage 1: 엔티티 및 관계 추출"""
        logger.info("Stage 1: Entity Extraction")

        # TODO: 실제 LLM 호출로 엔티티 추출 구현
        # 현재는 스켈레톤으로 빈 결과 반환

        state["extracted_entities"] = []
        state["extracted_relationships"] = []
        state["gleaning_count"] = 0

        return state

    async def _gleaning(self, state: AgentState) -> AgentState:
        """Gleaning: 누락된 엔티티 추가 추출"""
        logger.info(f"Gleaning pass {state.get('gleaning_count', 0) + 1}")

        # TODO: Gleaning 로직 구현
        # "누락된 엔티티가 있는지" 재질문하여 추가 추출

        state["gleaning_count"] = state.get("gleaning_count", 0) + 1

        return state

    def _should_gleaning(self, state: AgentState) -> str:
        """Gleaning 필요 여부 판단"""
        gleaning_count = state.get("gleaning_count", 0)

        # max_gleanings 미만이고, 문서 텍스트가 있는 경우 Gleaning 수행
        if gleaning_count < settings.max_gleanings and state.get("document_text"):
            return "gleaning"

        return "search"

    # Stage 2: Intelligent (오케스트레이션)
    async def _hybrid_search(self, state: AgentState) -> AgentState:
        """Stage 2: Hybrid 검색 (Vector + Graph)"""
        logger.info("Stage 2: Hybrid Search")

        # TODO: Elasticsearch Vector Search 구현
        # TODO: Neo4j Graph Search 구현
        # 현재는 스켈레톤으로 빈 결과 반환

        state["vector_results"] = []
        state["graph_results"] = []

        return state

    async def _rrf_fusion(self, state: AgentState) -> AgentState:
        """RRF (Reciprocal Rank Fusion) 융합"""
        logger.info("Stage 2: RRF Fusion")

        # TODO: RRF 융합 알고리즘 구현
        # score = sum(1 / (k + rank))

        state["fused_results"] = []

        return state

    # Stage 3: Planning (답변 합성)
    async def _synthesize_answer(self, state: AgentState) -> AgentState:
        """Stage 3: 답변 합성"""
        logger.info("Stage 3: Answer Synthesis")

        # TODO: LLM을 사용한 답변 합성 구현
        # 현재는 스켈레톤으로 기본 응답 반환

        state["answer"] = "답변 합성이 아직 구현되지 않았습니다. (스켈레톤)"
        state["sources"] = []

        return state


# 싱글톤 에이전트 인스턴스
_agent: Optional[VIPAgent] = None


def get_vip_agent() -> VIPAgent:
    """VIP 에이전트 인스턴스 반환"""
    global _agent
    if _agent is None:
        _agent = VIPAgent()
    return _agent
