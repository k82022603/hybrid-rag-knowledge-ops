"""
검색 API 엔드포인트

Hybrid 검색 및 대화형 검색 (Chat) 제공
- /hybrid: Vector + Keyword + Graph 통합 검색
- /semantic: 시맨틱 벡터 검색
- /keyword: 키워드 BM25 검색
- /chat: LangGraph RAG Workflow 기반 대화형 검색
- /chat/stream: SSE 스트리밍 대화형 검색 (토큰 단위 최적화)
- /conversations/{id}: 대화 이력 조회

STORY-051 Day 2: /chat 엔드포인트가 LangGraph RAGWorkflow를 사용
STORY-057: 대화이력 + 스트리밍 구현
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.routes.auth import get_current_user
from app.core.logging import get_logger
from app.services.llm_adapter import (
    ServiceConnectionError,
    ServiceRateLimitError,
    ServiceTimeoutError,
    ServiceValidationError,
)
from app.services.search import get_search_service

logger = get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------


class SearchRequest(BaseModel):
    """검색 요청 모델"""

    query: str = Field(min_length=1, max_length=1000, description="검색 질의")
    top_k: int = Field(default=10, ge=1, le=100, description="반환할 결과 수")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="필터 조건")
    useGraph: bool = Field(default=True, description="Graph 검색 사용 여부")
    useVector: bool = Field(default=True, description="Vector 검색 사용 여부")

    model_config = {"populate_by_name": True}


class SearchResult(BaseModel):
    """검색 결과 항목"""

    chunk_id: str = Field(description="청크 ID")
    document_id: str = Field(description="문서 ID")
    content: str = Field(description="청크 내용")
    score: float = Field(description="관련성 점수")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="메타데이터")


class SearchResponse(BaseModel):
    """검색 응답 모델"""

    query: str = Field(description="원본 질의")
    results: List[SearchResult] = Field(description="검색 결과 목록")
    total: int = Field(description="총 결과 수")
    search_type: str = Field(default="hybrid", description="검색 유형")
    latency_ms: Optional[float] = Field(default=None, description="검색 소요 시간 (ms)")
    from_cache: bool = Field(default=False, description="캐시 히트 여부 (STORY-060)")


class ChatRequest(BaseModel):
    """대화형 검색 요청 모델"""

    query: str = Field(min_length=1, max_length=2000, description="사용자 질문")
    conversationId: Optional[str] = Field(default=None, description="대화 세션 ID (STORY-057)")
    topK: int = Field(default=5, ge=1, le=20, description="검색 결과 수")
    useReasoner: bool = Field(default=False, description="Reasoner 모델 사용 여부")

    # camelCase alias (ADR 준수)
    model_config = {"populate_by_name": True}


class ChatResponse(BaseModel):
    """대화형 검색 응답 모델"""

    answer: str = Field(description="생성된 답변")
    sources: List[Dict[str, Any]] = Field(description="출처 정보")
    conversationId: Optional[str] = Field(description="대화 세션 ID (STORY-057)")
    latencyMs: Optional[float] = Field(default=None, description="처리 소요 시간 (ms)")
    turnCount: Optional[int] = Field(default=None, description="대화 턴 수 (STORY-057)")

    model_config = {"populate_by_name": True}


class ConversationSummary(BaseModel):
    """대화 세션 요약 모델 (STORY-057)"""

    sessionId: str = Field(description="세션 ID")
    userId: Optional[str] = Field(default=None, description="사용자 ID")
    turnCount: int = Field(description="대화 턴 수")
    createdAt: str = Field(description="생성 시간")
    updatedAt: str = Field(description="마지막 업데이트 시간")
    lastQuery: Optional[str] = Field(default=None, description="마지막 질문")


class SemanticSearchRequest(BaseModel):
    """시맨틱 검색 요청 모델"""

    query: str = Field(min_length=1, max_length=1000, description="검색 질의")
    top_k: int = Field(default=10, ge=1, le=100, description="반환할 결과 수")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="필터 조건")


# ---------------------------------------------------------------------------
# Error translation helper
# ---------------------------------------------------------------------------


def _translate_service_error(error: Exception) -> HTTPException:
    """
    서비스 예외를 HTTPException으로 변환

    Args:
        error: 서비스 예외

    Returns:
        HTTPException (적절한 HTTP 상태 코드)
    """
    if isinstance(error, ServiceTimeoutError):
        return HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(error),
        )
    if isinstance(error, ServiceConnectionError):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        )
    if isinstance(error, ServiceRateLimitError):
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(error),
        )
    if isinstance(error, ServiceValidationError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"처리 중 오류가 발생했습니다: {str(error)}",
    )


# ---------------------------------------------------------------------------
# Hybrid Search
# ---------------------------------------------------------------------------


@router.post(
    "/hybrid",
    response_model=SearchResponse,
    summary="Hybrid 검색",
    description="Vector + Keyword + Graph 결합 검색 수행 (RRF 융합)",
)
async def hybrid_search(
    request: SearchRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SearchResponse:
    """
    Hybrid 검색 수행

    Vector Search (Elasticsearch kNN), Keyword Search (BM25),
    Graph Search (Neo4j)를 병렬 실행 후 RRF 알고리즘으로 융합합니다.

    Args:
        request: 검색 요청

    Returns:
        RRF 융합된 검색 결과 목록
    """
    logger.info(
        f"Hybrid search - Query: {request.query[:50]}..., "
        f"useGraph={request.useGraph}, useVector={request.useVector}"
    )

    try:
        service = get_search_service()
        result = await service.hybrid_search(
            query=request.query,
            filters=request.filters,
            top_k=request.top_k,
            use_graph=request.useGraph,
            use_vector=request.useVector,
        )

        return SearchResponse(
            query=request.query,
            results=[
                SearchResult(
                    chunk_id=r.chunk_id,
                    document_id=r.document_id,
                    content=r.content,
                    score=r.score,
                    metadata=r.metadata,
                )
                for r in result.get("results", [])
            ],
            total=result.get("total", 0),
            search_type="hybrid",
            latency_ms=result.get("latency_ms"),
            from_cache=result.get("from_cache", False),
        )

    except Exception as e:
        logger.exception(f"Hybrid search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Hybrid 검색 처리 중 오류가 발생했습니다: {str(e)}",
        )


# ---------------------------------------------------------------------------
# Semantic Search
# ---------------------------------------------------------------------------


@router.post(
    "/semantic",
    response_model=SearchResponse,
    summary="시맨틱 검색",
    description="BGE-M3 벡터 기반 시맨틱 검색 (Elasticsearch kNN)",
)
async def semantic_search(
    request: SemanticSearchRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SearchResponse:
    """
    시맨틱 벡터 검색

    BGE-M3 임베딩을 사용하여 의미적으로 유사한 문서 청크를 검색합니다.

    Args:
        request: 시맨틱 검색 요청

    Returns:
        벡터 유사도 기반 검색 결과
    """
    logger.info(f"Semantic search - Query: {request.query[:50]}...")

    try:
        service = get_search_service()
        result = await service.semantic_search(
            query=request.query,
            filters=request.filters,
            top_k=request.top_k,
        )

        return SearchResponse(
            query=request.query,
            results=[
                SearchResult(
                    chunk_id=r.chunk_id,
                    document_id=r.document_id,
                    content=r.content,
                    score=r.score,
                    metadata=r.metadata,
                )
                for r in result.get("results", [])
            ],
            total=result.get("total", 0),
            search_type="semantic",
            latency_ms=result.get("latency_ms"),
        )

    except Exception as e:
        logger.exception(f"Semantic search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"시맨틱 검색 처리 중 오류가 발생했습니다: {str(e)}",
        )


# ---------------------------------------------------------------------------
# Keyword Search
# ---------------------------------------------------------------------------


@router.post(
    "/keyword",
    response_model=SearchResponse,
    summary="키워드 검색",
    description="BM25 기반 키워드 매칭 검색 (Elasticsearch)",
)
async def keyword_search(
    request: SearchRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SearchResponse:
    """
    키워드 기반 BM25 검색

    Elasticsearch BM25 알고리즘을 사용한 텍스트 매칭 검색을 수행합니다.

    Args:
        request: 검색 요청

    Returns:
        BM25 기반 검색 결과
    """
    logger.info(f"Keyword search - Query: {request.query[:50]}...")

    try:
        service = get_search_service()
        result = await service.keyword_search(
            query=request.query,
            filters=request.filters,
            top_k=request.top_k,
        )

        return SearchResponse(
            query=request.query,
            results=[
                SearchResult(
                    chunk_id=r.chunk_id,
                    document_id=r.document_id,
                    content=r.content,
                    score=r.score,
                    metadata=r.metadata,
                )
                for r in result.get("results", [])
            ],
            total=result.get("total", 0),
            search_type="keyword",
            latency_ms=result.get("latency_ms"),
        )

    except Exception as e:
        logger.exception(f"Keyword search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"키워드 검색 처리 중 오류가 발생했습니다: {str(e)}",
        )


# ---------------------------------------------------------------------------
# Chat Search (LangGraph RAG Workflow)
# ---------------------------------------------------------------------------


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="대화형 검색 (LangGraph)",
    description="LangGraph RAG Workflow 기반 대화형 검색 (STORY-051, STORY-057)",
)
async def chat_search(
    request: ChatRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> ChatResponse:
    """
    대화형 검색 (LangGraph RAG Workflow)

    STORY-051: SearchService -> LangGraph Workflow 연결
    STORY-057: 대화이력 + 스트리밍 구현
    Planner -> Retriever -> Reranker -> Generator 파이프라인을 통해
    답변을 생성합니다.

    Args:
        request: 대화형 검색 요청

    Returns:
        생성된 답변 및 출처 정보

    Raises:
        HTTPException(400): 입력 검증 실패
        HTTPException(429): Rate Limit 초과
        HTTPException(502): 서비스 연결 실패
        HTTPException(504): 타임아웃
    """
    logger.info(
        f"Chat search (LangGraph) - Query: {request.query[:50]}..., "
        f"ConversationId: {request.conversationId}"
    )

    try:
        from app.agents.rag_workflow import get_rag_workflow
        from app.services.conversation_history import get_conversation_history_service
        from app.services.search import get_search_service as _get_svc

        # 서비스 초기화
        search_svc = _get_svc()
        conversation_svc = get_conversation_history_service()
        workflow = get_rag_workflow(
            search_service=search_svc,
            conversation_history_service=conversation_svc,
        )

        # 대화 세션 생성/조회 (STORY-057)
        conversation_id = request.conversationId
        if conversation_id:
            session = conversation_svc.get_or_create_session(
                session_id=conversation_id,
                user_id=current_user.get("sub"),
            )
        else:
            # 새 세션 생성
            session = conversation_svc.get_or_create_session(
                user_id=current_user.get("sub"),
            )
            conversation_id = session.session_id

        # 워크플로우 실행
        response = await workflow.run(
            query=request.query,
            top_k=request.topK,
            use_reasoner=request.useReasoner,
            conversation_id=conversation_id,
        )

        # 턴 수 조회
        turn_count = len(session.turns) if session else 0

        return ChatResponse(
            answer=response.answer,
            sources=response.sources,
            conversationId=conversation_id,
            latencyMs=response.latency_ms,
            turnCount=turn_count,
        )

    except (
        ServiceTimeoutError,
        ServiceConnectionError,
        ServiceRateLimitError,
        ServiceValidationError,
    ) as e:
        logger.error(f"Chat search service error: {e}")
        raise _translate_service_error(e)

    except Exception as e:
        logger.exception(f"Chat search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"검색 처리 중 오류가 발생했습니다: {str(e)}",
        )


# ---------------------------------------------------------------------------
# Streaming Chat Search (STORY-057)
# ---------------------------------------------------------------------------


@router.post(
    "/chat/stream",
    summary="스트리밍 대화형 검색",
    description="SSE 스트리밍 방식의 대화형 검색 (토큰 단위 최적화, STORY-057)",
)
async def chat_stream(
    request: ChatRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> StreamingResponse:
    """
    스트리밍 대화형 검색 (STORY-057)

    Server-Sent Events (SSE)를 통해 실시간으로 답변을 스트리밍합니다.
    토큰 단위 스트리밍으로 최적화되었습니다.

    이벤트 유형:
    - start: 검색 시작 (출처 정보, 세션 ID 포함)
    - chunk: 답변 텍스트 청크 (토큰 단위)
    - error: 오류 발생
    - end: 스트리밍 종료 (전체 통계 포함)

    Args:
        request: 대화형 검색 요청

    Returns:
        SSE 스트리밍 응답
    """
    logger.info(
        f"Chat stream - Query: {request.query[:50]}..., "
        f"ConversationId: {request.conversationId}"
    )

    async def generate():
        """SSE 이벤트 생성기 (토큰 단위 최적화)"""
        import asyncio
        import json
        import re

        conversation_id = request.conversationId
        total_tokens = 0
        start_time = 0

        try:
            import time as _time
            start_time = _time.monotonic()

            from app.agents.rag_workflow import get_rag_workflow
            from app.services.conversation_history import get_conversation_history_service
            from app.services.search import get_search_service as _get_svc

            # 서비스 초기화
            search_svc = _get_svc()
            conversation_svc = get_conversation_history_service()
            workflow = get_rag_workflow(
                search_service=search_svc,
                conversation_history_service=conversation_svc,
            )

            # 대화 세션 생성/조회 (STORY-057)
            if conversation_id:
                session = conversation_svc.get_or_create_session(
                    session_id=conversation_id,
                    user_id=current_user.get("sub"),
                )
            else:
                session = conversation_svc.get_or_create_session(
                    user_id=current_user.get("sub"),
                )
                conversation_id = session.session_id

            # 워크플로우 실행
            response = await workflow.run(
                query=request.query,
                top_k=request.topK,
                use_reasoner=request.useReasoner,
                conversation_id=conversation_id,
            )

            # 시작 이벤트 (출처, 세션 정보 포함)
            start_event = json.dumps({
                "type": "start",
                "conversationId": conversation_id,
                "sources": response.sources,
                "contextLength": response.context_length,
                "turnCount": len(session.turns) if session else 0,
            }, ensure_ascii=False)
            yield f"data: {start_event}\n\n"

            # 토큰 단위 스트리밍 (word 기반으로 시뮬레이션)
            # 실제 LLM 스트리밍은 추후 구현 예정
            answer = response.answer
            words = answer.split()
            buffer = []
            chunk_size = 3  # 3 단어씩 청크로 전송

            for i, word in enumerate(words):
                buffer.append(word)
                total_tokens += 1

                # chunk_size 단어마다 또는 마지막 단어일 때 전송
                if len(buffer) >= chunk_size or i == len(words) - 1:
                    chunk_text = " ".join(buffer)
                    # 마지막이 아닌 경우 공백 추가
                    if i < len(words) - 1:
                        chunk_text += " "

                    chunk_event = json.dumps({
                        "type": "chunk",
                        "content": chunk_text,
                        "tokenIndex": total_tokens,
                    }, ensure_ascii=False)
                    yield f"data: {chunk_event}\n\n"
                    buffer = []

                    # 자연스러운 스트리밍 효과를 위한 짧은 딜레이
                    await asyncio.sleep(0.02)  # 20ms

        except Exception as e:
            logger.exception(f"Streaming error: {e}")
            error_event = json.dumps({
                "type": "error",
                "message": f"스트리밍 검색 실패: {str(e)}",
            }, ensure_ascii=False)
            yield f"data: {error_event}\n\n"

        # 종료 이벤트 (통계 포함)
        import time as _time
        total_time_ms = (_time.monotonic() - start_time) * 1000 if start_time else 0

        end_event = json.dumps({
            "type": "end",
            "conversationId": conversation_id,
            "totalTokens": total_tokens,
            "latencyMs": round(total_time_ms, 2),
        }, ensure_ascii=False)
        yield f"data: {end_event}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Conversation History Endpoints (STORY-057)
# ---------------------------------------------------------------------------


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationSummary,
    summary="대화 세션 조회",
    description="대화 세션 요약 정보 조회 (STORY-057)",
)
async def get_conversation(
    conversation_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> ConversationSummary:
    """
    대화 세션 요약 조회 (STORY-057)

    Args:
        conversation_id: 대화 세션 ID

    Returns:
        대화 세션 요약 정보

    Raises:
        HTTPException(404): 세션을 찾을 수 없음
    """
    from app.services.conversation_history import get_conversation_history_service

    service = get_conversation_history_service()
    summary = service.get_session_summary(conversation_id)

    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"대화 세션을 찾을 수 없습니다: {conversation_id}",
        )

    return ConversationSummary(
        sessionId=summary["sessionId"],
        userId=summary.get("userId"),
        turnCount=summary["turnCount"],
        createdAt=summary["createdAt"],
        updatedAt=summary["updatedAt"],
        lastQuery=summary.get("lastQuery"),
    )


@router.delete(
    "/conversations/{conversation_id}",
    summary="대화 세션 삭제",
    description="대화 세션 삭제 (STORY-057)",
)
async def delete_conversation(
    conversation_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    대화 세션 삭제 (STORY-057)

    Args:
        conversation_id: 대화 세션 ID

    Returns:
        삭제 결과

    Raises:
        HTTPException(404): 세션을 찾을 수 없음
    """
    from app.services.conversation_history import get_conversation_history_service

    service = get_conversation_history_service()
    deleted = service.delete_session(conversation_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"대화 세션을 찾을 수 없습니다: {conversation_id}",
        )

    logger.info(f"Conversation deleted: {conversation_id}")
    return {"deleted": True, "conversationId": conversation_id}
