"""
엔티티 추출 API 엔드포인트

문서에서 엔티티/관계/메타데이터 추출
- /entities: Gleaning 기반 엔티티 + 관계 추출
- /metadata: LLM 기반 메타데이터 자동 추출
- /full: 엔티티 + 관계 + 메타데이터 통합 추출
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.agents.state import (
    CategoryMetadata,
    DocumentMetadata,
    Entity,
    ExtractionResult,
    Relationship,
)
from app.core.logging import get_logger
from app.services.entity_extraction import get_entity_extraction_service

logger = get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------


class ExtractEntitiesRequest(BaseModel):
    """엔티티 추출 요청 모델"""

    text: str = Field(min_length=10, max_length=50000, description="추출 대상 텍스트")
    enable_gleaning: bool = Field(default=True, description="Gleaning 활성화 여부")
    document_id: Optional[str] = Field(default=None, description="문서 ID (선택)")


class ExtractEntitiesResponse(BaseModel):
    """엔티티 추출 응답 모델"""

    entities: List[Entity] = Field(description="추출된 엔티티 목록")
    relationships: List[Relationship] = Field(description="추출된 관계 목록")
    gleaning_passes: int = Field(description="Gleaning 수행 횟수")
    entity_count: int = Field(description="추출된 엔티티 수")
    relationship_count: int = Field(description="추출된 관계 수")


class ExtractMetadataRequest(BaseModel):
    """메타데이터 추출 요청 모델"""

    text: str = Field(min_length=10, max_length=50000, description="추출 대상 텍스트")
    filename: Optional[str] = Field(default=None, description="원본 파일명 (힌트용)")


class ExtractMetadataResponse(BaseModel):
    """메타데이터 추출 응답 모델"""

    metadata: DocumentMetadata = Field(description="추출된 메타데이터")


class FullExtractionRequest(BaseModel):
    """통합 추출 요청 모델"""

    text: str = Field(min_length=10, max_length=50000, description="추출 대상 텍스트")
    enable_gleaning: bool = Field(default=True, description="Gleaning 활성화 여부")
    filename: Optional[str] = Field(default=None, description="원본 파일명")
    document_id: Optional[str] = Field(default=None, description="문서 ID (선택)")


class FullExtractionResponse(BaseModel):
    """통합 추출 응답 모델"""

    entities: List[Entity] = Field(description="추출된 엔티티 목록")
    relationships: List[Relationship] = Field(description="추출된 관계 목록")
    metadata: Optional[DocumentMetadata] = Field(description="추출된 메타데이터")
    entity_count: int = Field(description="추출된 엔티티 수")
    relationship_count: int = Field(description="추출된 관계 수")


# ---------------------------------------------------------------------------
# Entity Extraction
# ---------------------------------------------------------------------------


@router.post(
    "/entities",
    response_model=ExtractEntitiesResponse,
    summary="엔티티 추출",
    description="문서에서 엔티티 및 관계 추출 (Gleaning 지원)",
)
async def extract_entities(request: ExtractEntitiesRequest) -> ExtractEntitiesResponse:
    """
    엔티티 및 관계 추출

    LLM을 활용하여 문서에서 엔티티와 관계를 추출합니다.
    Gleaning 기법을 통해 추출 품질을 향상시킵니다 (+33% Recall).

    Pipeline:
        1. 1차 엔티티 추출 (LLM)
        2. Gleaning: 누락 엔티티 보완 (LLM 재질문)
        3. 관계 추출 (LLM)
        4. 결과 통합 및 중복 제거

    Args:
        request: 엔티티 추출 요청

    Returns:
        추출된 엔티티 및 관계
    """
    logger.info(
        f"Entity extraction - Text length: {len(request.text)}, "
        f"Gleaning: {request.enable_gleaning}"
    )

    try:
        service = get_entity_extraction_service()

        # 엔티티 추출 (Gleaning 포함)
        entities = await service.extract_entities(
            text=request.text,
            enable_gleaning=request.enable_gleaning,
        )

        # 관계 추출
        relationships = await service.extract_relationships(
            text=request.text,
            entities=entities,
        )

        return ExtractEntitiesResponse(
            entities=entities,
            relationships=relationships,
            gleaning_passes=service.max_gleanings if request.enable_gleaning else 0,
            entity_count=len(entities),
            relationship_count=len(relationships),
        )

    except Exception as e:
        logger.exception(f"Entity extraction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"엔티티 추출 중 오류가 발생했습니다: {str(e)}",
        )


# ---------------------------------------------------------------------------
# Metadata Extraction
# ---------------------------------------------------------------------------


@router.post(
    "/metadata",
    response_model=ExtractMetadataResponse,
    summary="메타데이터 추출",
    description="문서 유형, 카테고리, 요약 등 메타데이터 자동 추출",
)
async def extract_metadata(request: ExtractMetadataRequest) -> ExtractMetadataResponse:
    """
    문서 메타데이터 추출

    LLM을 활용하여 문서의 메타데이터를 자동으로 추출합니다.
    - 문서 유형 (기술문서, 제안서, 회의록 등)
    - 프로젝트명
    - 유효 기간
    - 계층적 카테고리 (3단계)
    - 핵심 요약

    Args:
        request: 메타데이터 추출 요청

    Returns:
        추출된 메타데이터
    """
    logger.info(f"Metadata extraction - Text length: {len(request.text)}")

    try:
        service = get_entity_extraction_service()

        metadata = await service.extract_metadata(
            text=request.text,
            filename=request.filename,
        )

        return ExtractMetadataResponse(metadata=metadata)

    except Exception as e:
        logger.exception(f"Metadata extraction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"메타데이터 추출 중 오류가 발생했습니다: {str(e)}",
        )


# ---------------------------------------------------------------------------
# Full Extraction (Entities + Relationships + Metadata)
# ---------------------------------------------------------------------------


@router.post(
    "/full",
    response_model=FullExtractionResponse,
    summary="통합 추출",
    description="엔티티 + 관계 + 메타데이터 통합 추출",
)
async def extract_full(request: FullExtractionRequest) -> FullExtractionResponse:
    """
    엔티티 + 관계 + 메타데이터 통합 추출

    한 번의 요청으로 문서에서 모든 구조화된 정보를 추출합니다.

    Args:
        request: 통합 추출 요청

    Returns:
        추출된 엔티티, 관계, 메타데이터
    """
    logger.info(
        f"Full extraction - Text length: {len(request.text)}, "
        f"Gleaning: {request.enable_gleaning}"
    )

    try:
        service = get_entity_extraction_service()

        # 엔티티 + 관계 추출
        result = await service.extract_full(
            text=request.text,
            enable_gleaning=request.enable_gleaning,
        )

        # 메타데이터 추출
        metadata = await service.extract_metadata(
            text=request.text,
            filename=request.filename,
        )

        return FullExtractionResponse(
            entities=result.entities,
            relationships=result.relationships,
            metadata=metadata,
            entity_count=len(result.entities),
            relationship_count=len(result.relationships),
        )

    except Exception as e:
        logger.exception(f"Full extraction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"통합 추출 중 오류가 발생했습니다: {str(e)}",
        )
