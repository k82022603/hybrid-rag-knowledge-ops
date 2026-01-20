"""
엔티티 추출 API 엔드포인트

문서에서 엔티티/관계/메타데이터 추출
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.agents.state import CategoryMetadata, DocumentMetadata, Entity, Relationship
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


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


class ExtractMetadataRequest(BaseModel):
    """메타데이터 추출 요청 모델"""

    text: str = Field(min_length=10, max_length=50000, description="추출 대상 텍스트")
    filename: Optional[str] = Field(default=None, description="원본 파일명 (힌트용)")


class ExtractMetadataResponse(BaseModel):
    """메타데이터 추출 응답 모델"""

    metadata: DocumentMetadata = Field(description="추출된 메타데이터")


@router.post(
    "/entities",
    response_model=ExtractEntitiesResponse,
    summary="엔티티 추출",
    description="문서에서 엔티티 및 관계 추출 (Gleaning 지원)",
)
async def extract_entities(request: ExtractEntitiesRequest) -> ExtractEntitiesResponse:
    """
    엔티티 및 관계 추출

    Stage 1 (Value) 파이프라인을 통해 문서에서 엔티티와 관계를 추출합니다.
    Gleaning 기법을 통해 추출 품질을 향상시킵니다.

    Args:
        request: 엔티티 추출 요청

    Returns:
        추출된 엔티티 및 관계
    """
    logger.info(
        f"Entity extraction - Text length: {len(request.text)}, "
        f"Gleaning: {request.enable_gleaning}"
    )

    # TODO: 실제 엔티티 추출 구현
    # from app.agents.vip_agent import get_vip_agent
    # agent = get_vip_agent()
    # result = await agent.extract_entities(request.text, enable_gleaning=request.enable_gleaning)

    return ExtractEntitiesResponse(
        entities=[],  # 스켈레톤: 빈 결과
        relationships=[],
        gleaning_passes=0,
    )


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
    - 계층적 카테고리
    - 핵심 요약

    Args:
        request: 메타데이터 추출 요청

    Returns:
        추출된 메타데이터
    """
    logger.info(f"Metadata extraction - Text length: {len(request.text)}")

    # TODO: 실제 메타데이터 추출 구현
    # 스켈레톤: 기본값 반환
    return ExtractMetadataResponse(
        metadata=DocumentMetadata(
            document_type="unknown",
            project_name="",
            valid_start_date=None,
            valid_end_date=None,
            categories=CategoryMetadata(
                level1="미분류",
                level2="미분류",
                level3=None,
            ),
            summary="메타데이터 추출이 아직 구현되지 않았습니다.",
        )
    )
