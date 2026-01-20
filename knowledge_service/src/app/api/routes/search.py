"""
검색 API 엔드포인트

Hybrid 검색 및 대화형 검색 (Chat) 제공
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agents.vip_agent import get_vip_agent
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


class SearchRequest(BaseModel):
    """검색 요청 모델"""

    query: str = Field(min_length=1, max_length=1000, description="검색 질의")
    top_k: int = Field(default=10, ge=1, le=100, description="반환할 결과 수")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="필터 조건")


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


class ChatRequest(BaseModel):
    """대화형 검색 요청 모델"""

    query: str = Field(min_length=1, max_length=2000, description="사용자 질문")
    conversation_id: Optional[str] = Field(default=None, description="대화 ID (선택)")
    top_k: int = Field(default=5, ge=1, le=20, description="검색 결과 수")


class ChatResponse(BaseModel):
    """대화형 검색 응답 모델"""

    answer: str = Field(description="생성된 답변")
    sources: List[Dict[str, Any]] = Field(description="출처 정보")
    conversation_id: Optional[str] = Field(description="대화 ID")


@router.post(
    "/hybrid",
    response_model=SearchResponse,
    summary="Hybrid 검색",
    description="Vector + Graph 결합 검색 수행",
)
async def hybrid_search(request: SearchRequest) -> SearchResponse:
    """
    Hybrid 검색 수행

    Vector Search (Elasticsearch)와 Graph Search (Neo4j)를 결합하여
    RRF 융합된 검색 결과를 반환합니다.

    Args:
        request: 검색 요청

    Returns:
        검색 결과 목록
    """
    logger.info(f"Hybrid search - Query: {request.query[:50]}...")

    # TODO: 실제 Hybrid 검색 구현
    # retriever = get_hybrid_retriever()
    # results = await retriever.retrieve(request.query, top_k=request.top_k)

    return SearchResponse(
        query=request.query,
        results=[],  # 스켈레톤: 빈 결과
        total=0,
    )


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="대화형 검색",
    description="검색 + 답변 합성을 포함한 대화형 검색",
)
async def chat_search(request: ChatRequest) -> ChatResponse:
    """
    대화형 검색 (RAG)

    VIP 3단계 파이프라인을 통해 검색 및 답변 합성을 수행합니다.

    Args:
        request: 대화형 검색 요청

    Returns:
        생성된 답변 및 출처 정보
    """
    logger.info(f"Chat search - Query: {request.query[:50]}...")

    try:
        agent = get_vip_agent()
        result = await agent.process(query=request.query)

        return ChatResponse(
            answer=result.get("answer", ""),
            sources=result.get("sources", []),
            conversation_id=request.conversation_id,
        )
    except Exception as e:
        logger.exception(f"Chat search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"검색 처리 중 오류가 발생했습니다: {str(e)}",
        )


@router.post(
    "/chat/stream",
    summary="스트리밍 대화형 검색",
    description="SSE 스트리밍 방식의 대화형 검색",
)
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """
    스트리밍 대화형 검색

    Server-Sent Events (SSE)를 통해 실시간으로 답변을 스트리밍합니다.

    Args:
        request: 대화형 검색 요청

    Returns:
        SSE 스트리밍 응답
    """
    logger.info(f"Chat stream - Query: {request.query[:50]}...")

    async def generate():
        """SSE 이벤트 생성기"""
        # TODO: 실제 스트리밍 구현
        yield f"data: {{'type': 'start', 'message': 'Processing...'}}\n\n"
        yield f"data: {{'type': 'chunk', 'content': 'Streaming not implemented yet.'}}\n\n"
        yield f"data: {{'type': 'end'}}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
