"""
데이터 모델 모듈

Pydantic 기반 데이터 모델 정의
- 요청/응답 스키마
- 도메인 엔티티
- 문서 파싱 모델
- 문서 업로드 모델
"""

from app.models.document import (
    Chunk,
    Document,
    DocumentCreate,
    DocumentFormat,
    DocumentListItem,
    DocumentListResponse,
    DocumentMetadataInput,
    DocumentResponse,
    DocumentStatus,
    DocumentStatusResponse,
    DocumentUpdate,
)
from app.models.parsed_document import (
    BatchParseResult,
    ImageRef,
    ParsedDocument,
    ParseResult,
    ParseStatus,
    Section,
    Table,
    TableCell,
)
from app.models.parsed_document import DocumentFormat as ParsedDocumentFormat

__all__ = [
    # Document models
    "Document",
    "Chunk",
    "DocumentCreate",
    "DocumentUpdate",
    # Document upload models
    "DocumentFormat",
    "DocumentStatus",
    "DocumentMetadataInput",
    "DocumentResponse",
    "DocumentStatusResponse",
    "DocumentListItem",
    "DocumentListResponse",
    # Parsed document models
    "ParsedDocument",
    "ParsedDocumentFormat",
    "ParseResult",
    "BatchParseResult",
    "ParseStatus",
    "Section",
    "Table",
    "TableCell",
    "ImageRef",
]
