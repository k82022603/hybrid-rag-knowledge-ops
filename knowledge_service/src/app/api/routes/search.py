"""
검색 API 엔드포인트

Hybrid 검색 및 대화형 검색 (Chat) 제공
- /hybrid: Vector + Keyword + Graph 통합 검색
- /semantic: 시맨틱 벡터 검색
- /keyword: 키워드 BM25 검색
- /chat: RAG 기반 대화형 검색
- /chat/stream: SSE 스트리밍 대화형 검색
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.services.rag_pipeline import get_rag_pipeline
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


class ChatRequest(BaseModel):
    """대화형 검색 요청 모델"""

    query: str = Field(min_length=1, max_length=2000, description="사용자 질문")
    conversation_id: Optional[str] = Field(default=None, description="대화 ID (선택)")
    top_k: int = Field(default=5, ge=1, le=20, description="검색 결과 수")
    use_reasoner: bool = Field(default=False, description="Reasoner 모델 사용 여부")


class ChatResponse(BaseModel):
    """대화형 검색 응답 모델"""

    answer: str = Field(description="생성된 답변")
    sources: List[Dict[str, Any]] = Field(description="출처 정보")
    conversation_id: Optional[str] = Field(description="대화 ID")
    latency_ms: Optional[float] = Field(default=None, description="처리 소요 시간 (ms)")


class SemanticSearchRequest(BaseModel):
    """시맨틱 검색 요청 모델"""

    query: str = Field(min_length=1, max_length=1000, description="검색 질의")
    top_k: int = Field(default=10, ge=1, le=100, description="반환할 결과 수")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="필터 조건")


# ---------------------------------------------------------------------------
# Hybrid Search
# ---------------------------------------------------------------------------


@router.post(
    "/hybrid",
    response_model=SearchResponse,
    summary="Hybrid 검색",
    description="Vector + Keyword + Graph 결합 검색 수행 (RRF 융합)",
)
async def hybrid_search(request: SearchRequest) -> SearchResponse:
    """
    Hybrid 검색 수행

    Vector Search (Elasticsearch kNN), Keyword Search (BM25),
    Graph Search (Neo4j)를 병렬 실행 후 RRF 알고리즘으로 융합합니다.

    Args:
        request: 검색 요청

    Returns:
        RRF 융합된 검색 결과 목록
    """
    logger.info(f"Hybrid search - Query: {request.query[:50]}...")

    try:
        service = get_search_service()
        result = await service.hybrid_search(
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
            search_type="hybrid",
            latency_ms=result.get("latency_ms"),
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
async def semantic_search(request: SemanticSearchRequest) -> SearchResponse:
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
async def keyword_search(request: SearchRequest) -> SearchResponse:
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
# Chat Search (RAG)
# ---------------------------------------------------------------------------


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="대화형 검색",
    description="검색 + RAG 답변 합성을 포함한 대화형 검색",
)
async def chat_search(request: ChatRequest) -> ChatResponse:
    """
    대화형 검색 (RAG)

    1. Hybrid 검색으로 관련 문서 청크를 가져옴
    2. RAG 파이프라인으로 컨텍스트 구성 + LLM 답변 생성

    Args:
        request: 대화형 검색 요청

    Returns:
        생성된 답변 및 출처 정보
    """
    logger.info(f"Chat search - Query: {request.query[:50]}...")

    try:
        # 1. Hybrid 검색
        search_service = get_search_service()
        search_result = await search_service.hybrid_search(
            query=request.query,
            top_k=request.top_k,
        )

        search_results = search_result.get("results", [])

        # 2. RAG 파이프라인
        rag_pipeline = get_rag_pipeline()
        rag_response = await rag_pipeline.process_query(
            query=request.query,
            search_results=search_results,
            use_reasoner=request.use_reasoner,
        )

        return ChatResponse(
            answer=rag_response.answer,
            sources=rag_response.sources,
            conversation_id=request.conversation_id,
            latency_ms=rag_response.latency_ms,
        )

    except Exception as e:
        logger.exception(f"Chat search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"검색 처리 중 오류가 발생했습니다: {str(e)}",
        )


# ---------------------------------------------------------------------------
# Streaming Chat Search
# ---------------------------------------------------------------------------


@router.post(
    "/chat/stream",
    summary="스트리밍 대화형 검색",
    description="SSE 스트리밍 방식의 대화형 검색",
)
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """
    스트리밍 대화형 검색

    Server-Sent Events (SSE)를 통해 실시간으로 답변을 스트리밍합니다.

    이벤트 유형:
    - start: 검색 시작 (출처 정보 포함)
    - chunk: 답변 텍스트 청크
    - error: 오류 발생
    - end: 스트리밍 종료

    Args:
        request: 대화형 검색 요청

    Returns:
        SSE 스트리밍 응답
    """
    logger.info(f"Chat stream - Query: {request.query[:50]}...")

    async def generate():
        """SSE 이벤트 생성기"""
        try:
            # 1. Hybrid 검색
            search_service = get_search_service()
            search_result = await search_service.hybrid_search(
                query=request.query,
                top_k=request.top_k,
            )

            search_results = search_result.get("results", [])

            # 2. RAG 스트리밍
            rag_pipeline = get_rag_pipeline()
            async for event in rag_pipeline.generate_stream(
                query=request.query,
                search_results=search_results,
            ):
                yield event

        except Exception as e:
            import json
            error_event = json.dumps({
                "type": "error",
                "message": f"스트리밍 검색 실패: {str(e)}",
            }, ensure_ascii=False)
            yield f"data: {error_event}\n\n"

            end_event = json.dumps({"type": "end"})
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
