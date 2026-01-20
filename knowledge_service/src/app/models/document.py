"""
문서 및 청크 데이터 모델

PostgreSQL SSOT 스키마와 매핑되는 도메인 모델
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


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
