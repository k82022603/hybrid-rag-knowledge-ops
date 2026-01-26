"""
청크 데이터 모델

ETL 파이프라인에서 사용하는 청크 모델
- Chunk: 개별 청크 데이터
- ChunkResult: 청킹 결과 집계
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class Chunk(BaseModel):
    """
    청크 데이터 모델

    SemanticChunker가 생성하는 개별 청크 단위.
    원본 문서 내 위치 정보와 메타데이터를 포함한다.

    Attributes:
        id: 청크 고유 ID (UUID)
        content: 청크 텍스트 내용
        document_id: 원본 문서 ID
        chunk_index: 문서 내 순서 (0-based)
        start_char: 원본 텍스트 내 시작 문자 위치
        end_char: 원본 텍스트 내 끝 문자 위치
        token_count: 추정 토큰 수
        heading: 해당 청크가 속한 섹션 헤더
        page_number: 페이지 번호 (있는 경우)
        metadata: 추가 메타데이터
        created_at: 생성 시간
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    content: str = Field(description="청크 텍스트")
    document_id: str = Field(default="", description="원본 문서 ID")
    chunk_index: int = Field(default=0, ge=0, description="문서 내 순서 (0-based)")
    start_char: int = Field(default=0, ge=0, description="시작 문자 위치")
    end_char: int = Field(default=0, ge=0, description="끝 문자 위치")
    token_count: int = Field(default=0, ge=0, description="토큰 수")
    heading: Optional[str] = Field(default=None, description="섹션 헤더")
    page_number: Optional[int] = Field(default=None, description="페이지 번호")
    metadata: Dict = Field(default_factory=dict, description="추가 메타데이터")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="생성 시간")


class ChunkResult(BaseModel):
    """
    청킹 결과 집계 모델

    SemanticChunker의 chunk_document / chunk_text 결과를
    문서 단위로 집계한 모델.

    Attributes:
        document_id: 원본 문서 ID
        chunks: 생성된 청크 목록
        total_chunks: 총 청크 수
        avg_token_count: 평균 토큰 수
        processing_time_ms: 처리 소요 시간 (밀리초)
    """

    document_id: str = Field(default="", description="원본 문서 ID")
    chunks: List[Chunk] = Field(default_factory=list, description="청크 목록")
    total_chunks: int = Field(default=0, ge=0, description="총 청크 수")
    avg_token_count: float = Field(default=0.0, ge=0.0, description="평균 토큰 수")
    processing_time_ms: float = Field(default=0.0, ge=0.0, description="처리 시간 (ms)")
