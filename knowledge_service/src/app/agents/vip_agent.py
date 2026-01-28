"""
VIP 3단계 LangGraph 에이전트

Value-Intelligent-Planning 아키텍처 기반 RAG 파이프라인

STORY-051 Day 2 업데이트:
- _hybrid_search: SearchService/HybridRetriever 통합
- _rrf_fusion: SearchService._rrf_fusion 위임
- _synthesize_answer: LLMAdapter를 통한 답변 생성
- reranked_results 필드 매핑
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
    Stage 2 (Intelligent): Hybrid 검색 + RRF 융합 + Reranking
    Stage 3 (Planning): 답변 합성

    STORY-051 Day 2: SearchService/LLMAdapter 통합
    """

    def __init__(
        self,
        search_service: Optional[Any] = None,
        hybrid_retriever: Optional[Any] = None,
        llm_adapter: Optional[Any] = None,
    ):
        """
        에이전트 초기화

        Args:
            search_service: SearchService 인스턴스 (hybrid_retriever 없을 때 사용)
            hybrid_retriever: HybridRetriever 인스턴스 (우선 사용)
            llm_adapter: LLMAdapter 인스턴스 (Generator Node에서 사용)
        """
        self._llm: Optional[ChatOpenAI] = None
        self._graph: Optional[StateGraph] = None
        self._search_service = search_service
        self._hybrid_retriever = hybrid_retriever
        self._llm_adapter = llm_adapter

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
        """
        Stage 2: Hybrid 검색 (Vector + Keyword + Graph)

        STORY-051 Day 2: HybridRetriever 또는 SearchService를 통해
        실제 검색을 수행합니다. 검색 실패 시 빈 결과로 graceful 처리.
        """
        logger.info("Stage 2: Hybrid Search")

        query = state.get("query", "")

        try:
            # HybridRetriever 우선 사용
            if self._hybrid_retriever is not None:
                results = await self._hybrid_retriever.retrieve(
                    query=query,
                    top_k=settings.retrieval_top_k * 2,
                    use_reranking=False,  # reranking은 rrf_fusion 후 수행
                )
                state["vector_results"] = [
                    r for r in results if r.source in ("vector", "keyword")
                ]
                state["graph_results"] = [
                    r for r in results if r.source == "graph"
                ]
                # fused_results 는 _rrf_fusion에서 처리
                state["fused_results"] = results
                return state

            # SearchService fallback
            if self._search_service is not None:
                result = await self._search_service.hybrid_search(
                    query=query,
                    top_k=settings.retrieval_top_k * 2,
                )
                all_results = result.get("results", [])
                state["vector_results"] = [
                    r for r in all_results if r.source in ("vector", "keyword")
                ]
                state["graph_results"] = [
                    r for r in all_results if r.source == "graph"
                ]
                state["fused_results"] = all_results
                return state

            # 검색 서비스 없음
            logger.warning("No search service/retriever configured")
            state["vector_results"] = []
            state["graph_results"] = []
            state["fused_results"] = []

        except Exception as e:
            logger.error("Hybrid search failed: %s", e)
            state["vector_results"] = []
            state["graph_results"] = []
            state["fused_results"] = []
            state["error"] = f"검색 실패: {str(e)}"

        return state

    async def _rrf_fusion(self, state: AgentState) -> AgentState:
        """
        RRF (Reciprocal Rank Fusion) 융합 + Reranking

        STORY-051 Day 2: fused_results에서 상위 결과를 선택하고,
        Reranker가 있으면 재순위화합니다.
        reranked_results 필드에 최종 결과를 저장합니다.
        """
        logger.info("Stage 2: RRF Fusion + Reranking")

        fused_results = state.get("fused_results", [])

        if not fused_results:
            state["reranked_results"] = []
            return state

        # 상위 결과 선택
        top_k = settings.retrieval_top_k
        selected = fused_results[:top_k]

        # Reranking 시도 (HybridRetriever에 reranker가 있는 경우)
        if (
            self._hybrid_retriever is not None
            and hasattr(self._hybrid_retriever, "_reranker")
            and self._hybrid_retriever._reranker is not None
        ):
            query = state.get("query", "")
            try:
                reranker = self._hybrid_retriever._reranker
                selected = await reranker.rerank_search_results(
                    query=query,
                    search_results=fused_results[:50],
                    top_k=top_k,
                )
                logger.info(
                    "Reranking applied - input=%d, output=%d",
                    min(len(fused_results), 50), len(selected),
                )
            except Exception as e:
                logger.warning("Reranking failed, using fused results: %s", e)
                selected = fused_results[:top_k]

        state["reranked_results"] = selected

        logger.info(
            "RRF Fusion complete - Fused: %d, Reranked: %d",
            len(fused_results), len(selected),
        )

        return state

    # Stage 3: Planning (답변 합성)
    async def _synthesize_answer(self, state: AgentState) -> AgentState:
        """
        Stage 3: 답변 합성

        STORY-051 Day 2: reranked_results를 컨텍스트로 변환하고
        LLMAdapter를 통해 답변을 생성합니다.
        """
        logger.info("Stage 3: Answer Synthesis")

        query = state.get("query", "")
        reranked_results = state.get("reranked_results", [])

        # 컨텍스트 구성
        from app.agents.rag_workflow import (
            build_context_from_results,
            build_sources_from_results,
        )

        context, selected_results = build_context_from_results(
            search_results=reranked_results,
            max_chunks=10,
            max_length=8000,
        )

        state["context"] = context
        state["sources"] = build_sources_from_results(selected_results)

        # 컨텍스트 없으면 폴백 답변
        if not context.strip():
            state["answer"] = (
                "죄송합니다. 질문과 관련된 정보를 찾을 수 없습니다. "
                "다른 키워드로 검색해 주시거나, 질문을 더 구체적으로 작성해 주세요."
            )
            return state

        # LLMAdapter를 통한 답변 생성
        if self._llm_adapter is not None:
            try:
                answer = await self._llm_adapter.generate(
                    prompt=query,
                    context=context,
                )
                state["answer"] = answer
                return state
            except Exception as e:
                logger.error("LLM generation failed: %s", e)
                state["error"] = f"답변 생성 실패: {str(e)}"

        # LLMAdapter 없으면 폴백
        state["answer"] = (
            "관련 문서를 찾았으나 답변 생성 서비스를 사용할 수 없습니다. "
            f"검색된 문서 수: {len(selected_results)}"
        )

        return state


# 싱글톤 에이전트 인스턴스
_agent: Optional[VIPAgent] = None


def get_vip_agent() -> VIPAgent:
    """VIP 에이전트 인스턴스 반환"""
    global _agent
    if _agent is None:
        _agent = VIPAgent()
    return _agent


def reset_vip_agent() -> None:
    """싱글톤 인스턴스 초기화 (테스트용)"""
    global _agent
    _agent = None
