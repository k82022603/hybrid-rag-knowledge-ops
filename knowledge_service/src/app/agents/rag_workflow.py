"""
LangGraph RAG Workflow 모듈

SearchService -> LangGraph Workflow 연결
VIP 3단계 아키텍처 (Value -> Intelligent -> Planning)를 LangGraph로 구현

Pipeline:
    1. Planner Node: 검색 전략 결정 및 엔티티 추출
    2. Retriever Node: Hybrid 검색 수행 (ES Vector + BM25 + Neo4j Graph)
    3. Reranker Node: RRF 융합 결과 재순위화
    4. Generator Node: 컨텍스트 기반 답변 생성

STORY-051: RAG 파이프라인 통합 (Day 2)
STORY-057: 대화이력 + 스트리밍 구현
"""

import re
import time
from typing import Any, Dict, List, Optional

from app.agents.state import AgentState, SearchResult
from app.core.config import settings
from app.core.logging import get_logger
from app.services.llm_adapter import (
    LLMAdapter,
    ServiceConnectionError,
    ServiceTimeoutError,
    ServiceValidationError,
    get_llm_adapter,
    translate_llm_error,
)

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# RAG Workflow Response
# ---------------------------------------------------------------------------


class RAGWorkflowResponse:
    """
    RAG Workflow 응답

    LangGraph 워크플로우 실행 결과를 캡슐화합니다.

    Attributes:
        answer: 생성된 답변
        sources: 출처 정보 목록
        query: 원본 질의
        search_results: 검색 결과 (reranked)
        context_length: 컨텍스트 길이
        latency_ms: 전체 처리 시간 (ms)
        model: 사용된 LLM 모델
        pipeline_stages: 각 단계별 처리 정보
        error: 에러 메시지 (있는 경우)
        conversation_id: 대화 세션 ID (STORY-057)
    """

    def __init__(
        self,
        answer: str,
        sources: Optional[List[Dict[str, Any]]] = None,
        query: str = "",
        search_results: Optional[List[SearchResult]] = None,
        context_length: int = 0,
        latency_ms: float = 0.0,
        model: str = "",
        pipeline_stages: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ):
        self.answer = answer
        self.sources = sources or []
        self.query = query
        self.search_results = search_results or []
        self.context_length = context_length
        self.latency_ms = latency_ms
        self.model = model
        self.pipeline_stages = pipeline_stages or {}
        self.error = error
        self.conversation_id = conversation_id

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "answer": self.answer,
            "sources": self.sources,
            "query": self.query,
            "context_length": self.context_length,
            "latency_ms": round(self.latency_ms, 2),
            "model": self.model,
            "pipeline_stages": self.pipeline_stages,
            "error": self.error,
            "conversation_id": self.conversation_id,
        }


# ---------------------------------------------------------------------------
# Context Builder (공유 유틸리티)
# ---------------------------------------------------------------------------

CONTEXT_CHUNK_TEMPLATE = """### [출처{index}] {title}
- 문서 ID: {document_id}
- 관련성 점수: {score}

{content}
"""


def build_context_from_results(
    search_results: List[SearchResult],
    max_chunks: int = 10,
    max_length: int = 8000,
) -> tuple:
    """
    검색 결과로부터 LLM 컨텍스트 문자열을 구성

    Args:
        search_results: 검색 결과 목록
        max_chunks: 최대 청크 수
        max_length: 최대 문자 수

    Returns:
        (context_string, selected_results) 튜플
    """
    if not search_results:
        return "", []

    context_parts: List[str] = []
    selected: List[SearchResult] = []
    total_length = 0

    for idx, result in enumerate(search_results):
        if idx >= max_chunks:
            break

        chunk_text = CONTEXT_CHUNK_TEMPLATE.format(
            index=idx + 1,
            title=result.metadata.get("title", "문서"),
            document_id=result.document_id[:8] if result.document_id else "N/A",
            score=round(result.score, 4),
            content=result.content,
        )

        if total_length + len(chunk_text) > max_length:
            remaining = max_length - total_length
            if remaining > 200:
                truncated = chunk_text[:remaining] + "\n...(잘림)"
                context_parts.append(truncated)
                selected.append(result)
            break

        context_parts.append(chunk_text)
        selected.append(result)
        total_length += len(chunk_text)

    return "\n".join(context_parts), selected


def _is_filename(value: str) -> bool:
    """
    값이 파일명 패턴인지 확인

    Args:
        value: 확인할 문자열

    Returns:
        파일명이면 True
    """
    return bool(re.search(r'\.\w{2,5}$', value))


def _extract_entities_from_title(title: str) -> List[str]:
    """
    제목에서 엔티티로 사용할 수 있는 키워드 추출

    파일명(예: "KMS_설계서.pdf")은 제외하고,
    의미 있는 키워드(프로젝트명, 기술명 등)를 추출합니다.

    Args:
        title: 문서 제목

    Returns:
        추출된 키워드 목록
    """
    if not title or _is_filename(title):
        return []

    # 제목 자체가 유의미한 엔티티명일 수 있음
    return [title]


def build_sources_from_results(
    search_results: List[SearchResult],
) -> List[Dict[str, Any]]:
    """
    검색 결과에서 출처 정보 생성

    ISSUE-011: 모든 소스에 graph_context.related_entities를 포함하여
    Graph 패널에서 파일명 대신 실제 엔티티명을 사용하도록 개선.

    Args:
        search_results: 선택된 검색 결과 목록

    Returns:
        출처 정보 딕셔너리 목록
    """
    sources: List[Dict[str, Any]] = []
    seen_doc_ids: set = set()

    for idx, result in enumerate(search_results):
        doc_id = result.document_id

        source_info: Dict[str, Any] = {
            "index": idx + 1,
            "chunk_id": result.chunk_id,
            "document_id": doc_id,
            "title": result.metadata.get("title", "문서"),
            "score": round(result.score, 4),
            "source_type": result.source,
            "snippet": (
                result.content[:200] + "..."
                if len(result.content) > 200
                else result.content
            ),
        }

        # ISSUE-011: 모든 소스에 대해 graph_context 생성
        # Graph 소스: matched_entities 사용 (Neo4j 쿼리에서 추출된 실제 엔티티)
        # Vector/Keyword 소스: 메타데이터의 제목에서 엔티티 추출 (파일명 제외)
        related_entities: List[str] = []

        matched_entities = result.metadata.get("matched_entities", [])
        if matched_entities:
            # 파일명 패턴 필터링
            related_entities = [e for e in matched_entities if e and not _is_filename(e)]

        # matched_entities가 비어 있으면 제목에서 엔티티 후보 추출
        if not related_entities:
            title = result.metadata.get("title", "")
            related_entities = _extract_entities_from_title(title)

        # ISSUE-011 보강: 제목이 파일명이라서 엔티티를 못 찾은 경우
        # content에서 명사구/키워드 후보를 추출 (snippet 기반)
        if not related_entities and result.content:
            content_snippet = result.content[:300]
            # 영문 대문자로 시작하는 단어 (기술명, 고유명사 후보)
            proper_nouns = re.findall(r'\b([A-Z][a-zA-Z]{2,}(?:\s+[A-Z][a-zA-Z]+)*)\b', content_snippet)
            # 한글 키워드 (2-6글자, 한자어/복합어 패턴)
            korean_keywords = re.findall(r'([가-힣]{2,6}(?:\s[가-힣]{2,6})?)', content_snippet)
            candidates = list(dict.fromkeys(proper_nouns[:3] + korean_keywords[:3]))
            related_entities = [c for c in candidates if not _is_filename(c)][:3]

        if related_entities:
            source_info["graph_context"] = {
                "related_entities": related_entities,
            }

        if doc_id not in seen_doc_ids:
            source_info["is_primary"] = True
            seen_doc_ids.add(doc_id)
        else:
            source_info["is_primary"] = False

        sources.append(source_info)

    return sources


# ---------------------------------------------------------------------------
# RAGWorkflow (LangGraph 기반)
# ---------------------------------------------------------------------------


class RAGWorkflow:
    """
    LangGraph RAG Workflow

    SearchService가 이 워크플로우를 호출하여 전체 RAG 파이프라인을 실행합니다.

    Pipeline Stages:
        1. plan() - 검색 전략 결정
        2. retrieve() - Hybrid 검색 (SearchService 위임)
        3. rerank() - 결과 재순위화 (Reranker 사용)
        4. generate() - 컨텍스트 기반 답변 생성 (LLM Adapter)

    Usage:
        workflow = RAGWorkflow(search_service=svc)
        response = await workflow.run(query="질문", top_k=5)
    """

    def __init__(
        self,
        search_service: Optional[Any] = None,
        hybrid_retriever: Optional[Any] = None,
        llm_adapter: Optional[LLMAdapter] = None,
        conversation_history_service: Optional[Any] = None,
        max_context_chunks: int = 10,
        max_context_length: int = 8000,
        max_conversation_turns: int = 5,
    ):
        """
        초기화

        Args:
            search_service: SearchService 인스턴스
            hybrid_retriever: HybridRetriever 인스턴스 (우선 사용)
            llm_adapter: LLMAdapter 인스턴스 (None이면 싱글톤)
            conversation_history_service: ConversationHistoryService 인스턴스 (STORY-057)
            max_context_chunks: 컨텍스트 최대 청크 수
            max_context_length: 컨텍스트 최대 문자 수
            max_conversation_turns: 대화 이력 최대 턴 수 (STORY-057)
        """
        self._search_service = search_service
        self._hybrid_retriever = hybrid_retriever
        self._llm_adapter = llm_adapter
        self._conversation_history_service = conversation_history_service
        self._max_context_chunks = max_context_chunks
        self._max_context_length = max_context_length
        self._max_conversation_turns = max_conversation_turns

    @property
    def llm_adapter(self) -> LLMAdapter:
        """LLMAdapter 지연 초기화"""
        if self._llm_adapter is None:
            self._llm_adapter = get_llm_adapter()
        return self._llm_adapter

    @property
    def conversation_history_service(self) -> Any:
        """ConversationHistoryService 지연 초기화 (STORY-057)"""
        if self._conversation_history_service is None:
            from app.services.conversation_history import (
                get_conversation_history_service,
            )
            self._conversation_history_service = get_conversation_history_service()
        return self._conversation_history_service

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def run(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        use_reasoner: bool = False,
        use_reranking: bool = True,
        conversation_id: Optional[str] = None,
    ) -> RAGWorkflowResponse:
        """
        RAG 워크플로우 실행

        Planner -> Retriever -> Reranker -> Generator 순서로 처리합니다.

        Args:
            query: 사용자 질의
            top_k: 반환할 결과 수
            filters: 검색 필터 조건
            user_id: 사용자 ID
            use_reasoner: Reasoner 모델 사용 여부
            use_reranking: Reranker 사용 여부
            conversation_id: 대화 세션 ID (STORY-057)

        Returns:
            RAGWorkflowResponse

        Raises:
            ServiceValidationError: 입력 검증 실패 (400)
            ServiceConnectionError: 서비스 연결 실패 (502)
            ServiceTimeoutError: 타임아웃 (504)
            ServiceRateLimitError: Rate Limit (429)
        """
        # 입력 검증
        if not query or not query.strip():
            raise ServiceValidationError(
                message="검색 질의가 비어 있습니다",
                field="query",
            )

        start_time = time.monotonic()
        pipeline_stages: Dict[str, Any] = {}

        # 대화 이력 컨텍스트 조회 (STORY-057)
        conversation_context = ""
        if conversation_id:
            conversation_context = self.conversation_history_service.get_conversation_context(
                session_id=conversation_id,
                max_turns=self._max_conversation_turns,
            )
            if conversation_context:
                logger.debug(
                    "Conversation context loaded - Session: %s, Length: %d",
                    conversation_id, len(conversation_context),
                )

        logger.info(
            "RAG Workflow started - Query: '%s', top_k=%d, "
            "reasoner=%s, reranking=%s, conversation_id=%s",
            query[:80], top_k, use_reasoner, use_reranking, conversation_id,
        )

        # ------------------------------------------------------------------
        # Stage 1: Plan (검색 전략 결정)
        # ------------------------------------------------------------------
        plan_start = time.monotonic()
        search_strategy = self._plan(query)
        pipeline_stages["plan"] = {
            "strategy": search_strategy,
            "latency_ms": round((time.monotonic() - plan_start) * 1000, 2),
        }

        # ------------------------------------------------------------------
        # Stage 2: Retrieve (Hybrid 검색)
        # ------------------------------------------------------------------
        retrieve_start = time.monotonic()
        try:
            search_results = await self._retrieve(
                query=query,
                top_k=top_k,
                filters=filters,
                user_id=user_id,
                use_reranking=use_reranking,
            )
        except Exception as e:
            logger.error("Retrieval failed: %s", e)
            search_results = []
            pipeline_stages["retrieve"] = {
                "error": str(e),
                "latency_ms": round((time.monotonic() - retrieve_start) * 1000, 2),
            }

        retrieve_latency = (time.monotonic() - retrieve_start) * 1000
        pipeline_stages["retrieve"] = pipeline_stages.get("retrieve", {
            "result_count": len(search_results),
            "latency_ms": round(retrieve_latency, 2),
        })

        # ------------------------------------------------------------------
        # Stage 3: Generate (답변 합성)
        # ------------------------------------------------------------------
        generate_start = time.monotonic()
        try:
            answer, context, selected_results = await self._generate(
                query=query,
                search_results=search_results,
                use_reasoner=use_reasoner,
                conversation_context=conversation_context,
            )
        except Exception as e:
            logger.error("Generation failed: %s", e)
            # 검색 결과는 있지만 생성 실패 시 -> 검색 결과만 반환
            answer = self._fallback_answer(search_results)
            context = ""
            selected_results = search_results

            pipeline_stages["generate"] = {
                "error": str(e),
                "latency_ms": round((time.monotonic() - generate_start) * 1000, 2),
            }

        generate_latency = (time.monotonic() - generate_start) * 1000
        if "generate" not in pipeline_stages:
            pipeline_stages["generate"] = {
                "answer_length": len(answer),
                "context_length": len(context),
                "latency_ms": round(generate_latency, 2),
            }

        # ------------------------------------------------------------------
        # 응답 구성
        # ------------------------------------------------------------------
        sources = build_sources_from_results(selected_results)
        total_latency = (time.monotonic() - start_time) * 1000

        # 대화 이력에 턴 추가 (STORY-057)
        if conversation_id:
            try:
                self.conversation_history_service.add_turn(
                    session_id=conversation_id,
                    query=query,
                    answer=answer,
                    sources=sources,
                    latency_ms=total_latency,
                    metadata={"pipeline_stages": pipeline_stages},
                )
                logger.debug(
                    "Conversation turn added - Session: %s", conversation_id,
                )
            except Exception as e:
                logger.warning(
                    "Failed to save conversation turn: %s", e,
                )

        logger.info(
            "RAG Workflow complete - "
            "Answer length: %d, Sources: %d, "
            "Total latency: %.1fms",
            len(answer), len(sources), total_latency,
        )

        return RAGWorkflowResponse(
            answer=answer,
            sources=sources,
            query=query,
            search_results=selected_results,
            context_length=len(context),
            latency_ms=total_latency,
            model=settings.deepseek_chat_model,
            pipeline_stages=pipeline_stages,
            conversation_id=conversation_id,
        )

    # ------------------------------------------------------------------
    # Pipeline Stages
    # ------------------------------------------------------------------

    def _plan(self, query: str) -> str:
        """
        Stage 1: 검색 전략 결정

        현재는 항상 hybrid 전략을 사용합니다.
        향후 질의 분석 기반 동적 전략 선택을 구현합니다.

        Args:
            query: 사용자 질의

        Returns:
            검색 전략 ("hybrid", "vector", "keyword", "graph")
        """
        # TODO: 질의 분석 기반 동적 전략 선택
        # 현재는 항상 hybrid
        logger.debug("Plan stage - Strategy: hybrid (default)")
        return "hybrid"

    async def _retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        use_reranking: bool = True,
    ) -> List[SearchResult]:
        """
        Stage 2: Hybrid 검색 수행

        HybridRetriever 또는 SearchService를 사용하여 검색합니다.
        HybridRetriever가 있으면 우선 사용 (reranking 포함).

        Args:
            query: 검색 질의
            top_k: 반환할 결과 수
            filters: 필터 조건
            user_id: 사용자 ID
            use_reranking: Reranker 사용 여부

        Returns:
            검색 결과 목록 (reranked 또는 fused)
        """
        # HybridRetriever 우선 사용 (Reranking 지원)
        if self._hybrid_retriever is not None:
            logger.debug("Retrieve stage - Using HybridRetriever")
            return await self._hybrid_retriever.retrieve(
                query=query,
                top_k=top_k,
                filters=filters,
                user_id=user_id,
                use_reranking=use_reranking,
            )

        # SearchService fallback
        if self._search_service is not None:
            logger.debug("Retrieve stage - Using SearchService")
            result = await self._search_service.hybrid_search(
                query=query,
                filters=filters,
                top_k=top_k,
                user_id=user_id,
            )
            return result.get("results", [])

        logger.warning("Retrieve stage - No retriever or search service available")
        return []

    async def _generate(
        self,
        query: str,
        search_results: List[SearchResult],
        use_reasoner: bool = False,
        conversation_context: str = "",
    ) -> tuple:
        """
        Stage 3: 답변 합성

        Reranked 검색 결과를 컨텍스트로 변환하고 LLM으로 답변을 생성합니다.

        Args:
            query: 사용자 질의
            search_results: (reranked) 검색 결과 목록
            use_reasoner: Reasoner 모델 사용 여부
            conversation_context: 대화 이력 컨텍스트 (STORY-057)

        Returns:
            (answer, context, selected_results) 튜플
        """
        # 컨텍스트 구성
        context, selected_results = build_context_from_results(
            search_results=search_results,
            max_chunks=self._max_context_chunks,
            max_length=self._max_context_length,
        )

        # 대화 이력 컨텍스트 통합 (STORY-057)
        if conversation_context:
            # 대화 이력을 검색 컨텍스트 앞에 추가
            context = f"{conversation_context}\n\n---\n\n{context}" if context else conversation_context

        # 컨텍스트 없으면 폴백
        if not context.strip():
            logger.warning("Generate stage - No context, returning fallback")
            return (
                "죄송합니다. 질문과 관련된 정보를 찾을 수 없습니다. "
                "다른 키워드로 검색해 주시거나, 질문을 더 구체적으로 작성해 주세요.",
                "",
                [],
            )

        # LLM 호출 (Adapter 사용)
        answer = await self.llm_adapter.generate(
            prompt=query,
            context=context,
            use_reasoner=use_reasoner,
        )

        return answer, context, selected_results

    @staticmethod
    def _fallback_answer(search_results: List[SearchResult]) -> str:
        """
        LLM 실패 시 폴백 답변 생성

        검색 결과가 있으면 결과 요약을 반환합니다.

        Args:
            search_results: 검색 결과 목록

        Returns:
            폴백 답변 문자열
        """
        if not search_results:
            return (
                "죄송합니다. 질문과 관련된 정보를 찾을 수 없습니다. "
                "다른 키워드로 검색해 주시거나, 질문을 더 구체적으로 작성해 주세요."
            )

        # 검색 결과 상위 항목 요약
        summary_parts = ["관련 문서를 찾았으나 답변 생성에 실패했습니다. 검색된 문서:"]
        for idx, result in enumerate(search_results[:5]):
            title = result.metadata.get("title", "문서")
            snippet = (
                result.content[:150] + "..."
                if len(result.content) > 150
                else result.content
            )
            summary_parts.append(f"\n{idx + 1}. [{title}] {snippet}")

        return "\n".join(summary_parts)


# ---------------------------------------------------------------------------
# 싱글톤 인스턴스
# ---------------------------------------------------------------------------

_workflow: Optional[RAGWorkflow] = None


def get_rag_workflow(
    search_service: Optional[Any] = None,
    hybrid_retriever: Optional[Any] = None,
    llm_adapter: Optional[LLMAdapter] = None,
    conversation_history_service: Optional[Any] = None,
) -> RAGWorkflow:
    """
    RAGWorkflow 인스턴스 반환 (싱글톤)

    Args:
        search_service: SearchService 인스턴스
        hybrid_retriever: HybridRetriever 인스턴스
        llm_adapter: LLMAdapter 인스턴스
        conversation_history_service: ConversationHistoryService 인스턴스 (STORY-057)

    Returns:
        RAGWorkflow 싱글톤 인스턴스
    """
    global _workflow
    if _workflow is None:
        _workflow = RAGWorkflow(
            search_service=search_service,
            hybrid_retriever=hybrid_retriever,
            llm_adapter=llm_adapter,
            conversation_history_service=conversation_history_service,
        )
    return _workflow


def reset_rag_workflow() -> None:
    """싱글톤 인스턴스 초기화 (테스트용)"""
    global _workflow
    _workflow = None
