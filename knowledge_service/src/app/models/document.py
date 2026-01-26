"""
문서 및 청크 데이터 모델

PostgreSQL SSOT 스키마와 매핑되는 도메인 모델
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Enums
# ============================================================================


class DocumentStatus(str, Enum):
    """문서 처리 상태"""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentFormat(str, Enum):
    """지원하는 업로드 문서 형식"""

    PDF = "pdf"
    DOCX = "docx"
    HWP = "hwp"
    PPTX = "pptx"


# ============================================================================
# Core Models
# ============================================================================


class Chunk(BaseModel):
    """문서 청크 모델"""

    id: Optional[UUID] = Field(default=None, description="청크 UUID")
    document_id: UUID = Field(description="문서 UUID")
    chunk_index: int = Field(ge=0, description="청크 순서 인덱스")
    content: str = Field(description="청크 텍스트 내용")
    token_count: int = Field(ge=0, description="토큰 수")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="청크 메타데이터")
    created_at: Optional[datetime] = Field(default=None, description="생성 시간")

    class Config:
        """Pydantic 설정"""

        from_attributes = True


class Document(BaseModel):
    """문서 모델"""

    id: Optional[UUID] = Field(default=None, description="문서 UUID")
    title: str = Field(min_length=1, max_length=500, description="문서 제목")
    file_path: Optional[str] = Field(default=None, description="파일 경로")
    file_type: Optional[str] = Field(default=None, description="파일 유형 (pdf, docx, pptx)")
    document_type: Optional[str] = Field(default=None, description="문서 유형 (기술문서, 제안서 등)")
    project_name: Optional[str] = Field(default=None, description="프로젝트명")
    valid_start_date: Optional[datetime] = Field(default=None, description="유효 시작일")
    valid_end_date: Optional[datetime] = Field(default=None, description="유효 종료일")
    summary: Optional[str] = Field(default=None, description="문서 요약")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="추가 메타데이터")
    chunks: List[Chunk] = Field(default_factory=list, description="청크 목록")
    created_at: Optional[datetime] = Field(default=None, description="생성 시간")
    updated_at: Optional[datetime] = Field(default=None, description="수정 시간")

    class Config:
        """Pydantic 설정"""

        from_attributes = True


# ============================================================================
# Request/Response Models - CRUD
# ============================================================================


class DocumentCreate(BaseModel):
    """문서 생성 요청 모델"""

    title: str = Field(min_length=1, max_length=500, description="문서 제목")
    content: str = Field(min_length=1, description="문서 내용")
    file_type: Optional[str] = Field(default=None, description="파일 유형")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="추가 메타데이터")


class DocumentUpdate(BaseModel):
    """문서 수정 요청 모델"""

    title: Optional[str] = Field(default=None, min_length=1, max_length=500, description="문서 제목")
    document_type: Optional[str] = Field(default=None, description="문서 유형")
    project_name: Optional[str] = Field(default=None, description="프로젝트명")
    summary: Optional[str] = Field(default=None, description="문서 요약")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="추가 메타데이터")


# ============================================================================
# Request/Response Models - Upload API
# ============================================================================


class DocumentMetadataInput(BaseModel):
    """문서 업로드 시 메타데이터 입력 모델"""

    title: Optional[str] = Field(default=None, max_length=500, description="문서 제목")
    description: Optional[str] = Field(default=None, max_length=2000, description="문서 설명")
    tags: List[str] = Field(default_factory=list, description="태그 목록")
    project_name: Optional[str] = Field(default=None, max_length=200, description="프로젝트명")


class DocumentResponse(BaseModel):
    """문서 업로드 응답 모델"""

    document_id: UUID = Field(description="문서 UUID")
    filename: str = Field(description="원본 파일명")
    format: DocumentFormat = Field(description="문서 형식")
    size_bytes: int = Field(ge=0, description="파일 크기 (바이트)")
    status: DocumentStatus = Field(description="처리 상태")
    status_url: str = Field(description="상태 조회 URL")
    created_at: datetime = Field(description="업로드 시간")
    metadata: Optional[DocumentMetadataInput] = Field(default=None, description="메타데이터")

    class Config:
        """Pydantic 설정"""

        from_attributes = True


class DocumentStatusResponse(BaseModel):
    """문서 처리 상태 응답 모델"""

    document_id: UUID = Field(description="문서 UUID")
    status: DocumentStatus = Field(description="처리 상태")
    progress_percent: int = Field(default=0, ge=0, le=100, description="처리 진행률 (%)")
    error_message: Optional[str] = Field(default=None, description="에러 메시지")
    updated_at: datetime = Field(description="마지막 업데이트 시간")

    class Config:
        """Pydantic 설정"""

        from_attributes = True


class DocumentListItem(BaseModel):
    """문서 목록 항목 모델"""

    document_id: UUID = Field(description="문서 UUID")
    filename: str = Field(description="원본 파일명")
    format: DocumentFormat = Field(description="문서 형식")
    size_bytes: int = Field(ge=0, description="파일 크기 (바이트)")
    status: DocumentStatus = Field(description="처리 상태")
    created_at: datetime = Field(description="업로드 시간")

    class Config:
        """Pydantic 설정"""

        from_attributes = True


class DocumentListResponse(BaseModel):
    """문서 목록 응답 모델 (페이지네이션 포함)"""

    documents: List[DocumentListItem] = Field(description="문서 목록")
    total: int = Field(ge=0, description="전체 문서 수")
    page: int = Field(ge=1, description="현재 페이지")
    page_size: int = Field(ge=1, description="페이지 크기")
    total_pages: int = Field(ge=0, description="전체 페이지 수")
