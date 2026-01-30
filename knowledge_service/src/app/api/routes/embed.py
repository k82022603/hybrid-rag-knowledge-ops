"""
임베딩 API 엔드포인트

BGE-M3 기반 텍스트 임베딩 생성
"""

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.embedding import get_embedding_service
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


class EmbedRequest(BaseModel):
    """단일 임베딩 요청 모델"""

    text: str = Field(min_length=1, max_length=10000, description="임베딩할 텍스트")


class EmbedResponse(BaseModel):
    """단일 임베딩 응답 모델"""

    embedding: List[float] = Field(description="Dense 임베딩 벡터")
    dimension: int = Field(description="벡터 차원")


class EmbedBatchRequest(BaseModel):
    """배치 임베딩 요청 모델"""

    texts: List[str] = Field(
        min_length=1,
        max_length=100,
        description="임베딩할 텍스트 목록 (최대 100개)",
    )


class EmbedBatchResponse(BaseModel):
    """배치 임베딩 응답 모델"""

    embeddings: List[List[float]] = Field(description="임베딩 벡터 목록")
    dimension: int = Field(description="벡터 차원")
    count: int = Field(description="처리된 텍스트 수")


@router.post(
    "",
    response_model=EmbedResponse,
    summary="단일 임베딩",
    description="단일 텍스트에 대한 임베딩 벡터 생성",
)
async def embed_single(request: EmbedRequest) -> EmbedResponse:
    """
    단일 텍스트 임베딩

    BGE-M3 모델을 사용하여 텍스트의 Dense 벡터를 생성합니다.

    Args:
        request: 임베딩 요청

    Returns:
        임베딩 벡터
    """
    logger.info(f"Single embedding - Text length: {len(request.text)}")

    try:
        service = get_embedding_service()
        vector = await service.aembed(request.text)

        return EmbedResponse(
            embedding=vector,
            dimension=len(vector),
        )
    except Exception as e:
        logger.exception(f"Embedding failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"임베딩 생성 중 오류가 발생했습니다: {str(e)}",
        )


@router.post(
    "/batch",
    response_model=EmbedBatchResponse,
    summary="배치 임베딩",
    description="여러 텍스트에 대한 배치 임베딩 생성",
)
async def embed_batch(request: EmbedBatchRequest) -> EmbedBatchResponse:
    """
    배치 임베딩

    여러 텍스트에 대해 한 번에 임베딩 벡터를 생성합니다.
    배치 처리로 효율성을 높입니다.

    Args:
        request: 배치 임베딩 요청

    Returns:
        임베딩 벡터 목록
    """
    logger.info(f"Batch embedding - Count: {len(request.texts)}")

    try:
        service = get_embedding_service()
        vectors = await service.aembed_batch(request.texts)

        return EmbedBatchResponse(
            embeddings=vectors,
            dimension=service.vector_dimension,
            count=len(vectors),
        )
    except Exception as e:
        logger.exception(f"Batch embedding failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"배치 임베딩 생성 중 오류가 발생했습니다: {str(e)}",
        )
