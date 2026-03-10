"""
문서 로딩/파싱 모듈

문서 파싱, 시맨틱 청킹, 메타데이터 추출, 문서 유형 분류를 담당합니다.

Functions:
    parse_file: DocumentParser를 사용한 파일 파싱
    chunk_document: SemanticChunker를 사용한 문서 청킹
    extract_metadata: 파일/문서 메타데이터 추출
    classify_doc_type: 문서 유형 분류
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger
from app.services.data_loader.models import DocType, FileInfo

logger = get_logger(__name__)


def parse_file(parser: Any, file_info: FileInfo) -> Optional[Any]:
    """파일 파싱

    DocumentParser를 사용하여 파일을 파싱합니다.

    Args:
        parser: DocumentParser 인스턴스
        file_info: 파일 정보

    Returns:
        ParsedDocument 또는 None (파싱 실패 시)
    """
    try:
        parse_result = parser.parse(file_info.file_path)

        if not parse_result.success:
            logger.warning(
                "Parse failed for %s: %s",
                file_info.file_name,
                parse_result.message,
            )
            return None

        parsed_doc = parse_result.document

        # 빈 문서 체크
        if not parsed_doc.content or not parsed_doc.content.strip():
            logger.warning("Empty content after parsing: %s", file_info.file_name)
            return None

        logger.debug(
            "Parsed %s: content_length=%d, sections=%d",
            file_info.file_name,
            len(parsed_doc.content),
            len(parsed_doc.sections) if parsed_doc.sections else 0,
        )

        return parsed_doc

    except Exception as e:
        logger.error("Parse error for %s: %s", file_info.file_name, e)
        raise


def chunk_document(chunker: Any, parsed_doc: Any) -> List[Any]:
    """문서 청킹

    SemanticChunker를 사용하여 문서를 청크로 분할합니다.

    Args:
        chunker: SemanticChunker 인스턴스
        parsed_doc: 파싱된 문서

    Returns:
        Chunk 객체 리스트
    """
    try:
        chunk_result = chunker.chunk_document(parsed_doc)
        chunks = chunk_result.chunks

        logger.debug(
            "Chunked document: total_chunks=%d, avg_tokens=%.1f",
            chunk_result.total_chunks,
            chunk_result.avg_token_count,
        )

        return chunks

    except Exception as e:
        logger.error("Chunking error: %s", e)
        raise


def extract_metadata(
    file_info: FileInfo,
    parsed_doc: Any,
) -> Dict[str, Any]:
    """파일 및 문서에서 메타데이터 추출

    파일 경로, 확장자, 문서 내용 등에서 메타데이터를 추출합니다.

    Args:
        file_info: 파일 정보
        parsed_doc: 파싱된 문서

    Returns:
        메타데이터 딕셔너리
    """
    metadata: Dict[str, Any] = {
        "source_name": file_info.source_name,
        "doc_type": classify_doc_type(file_info, parsed_doc),
        "file_name": file_info.file_name,
        "file_path": str(file_info.file_path),
        "file_size": file_info.file_size,
        "extension": file_info.extension,
        "modified_at": file_info.modified_at.isoformat() if file_info.modified_at else None,
        "content_length": len(parsed_doc.content) if parsed_doc.content else 0,
        "title": getattr(parsed_doc, "title", None) or file_info.file_name,
    }

    # 섹션 정보 추가
    if hasattr(parsed_doc, "sections") and parsed_doc.sections:
        metadata["section_count"] = len(parsed_doc.sections)
        metadata["section_titles"] = [
            s.title for s in parsed_doc.sections if s.title
        ][:10]  # 최대 10개 섹션 제목

    # 표/이미지 정보
    if hasattr(parsed_doc, "tables") and parsed_doc.tables:
        metadata["table_count"] = len(parsed_doc.tables)
    if hasattr(parsed_doc, "images") and parsed_doc.images:
        metadata["image_count"] = len(parsed_doc.images)

    return metadata


def classify_doc_type(
    file_info: FileInfo,
    parsed_doc: Any,
) -> str:
    """문서 유형 분류

    파일 경로와 내용을 기반으로 문서 유형을 분류합니다.

    Args:
        file_info: 파일 정보
        parsed_doc: 파싱된 문서

    Returns:
        문서 유형 문자열
    """
    # 데이터 소스에서 지정한 유형이 있으면 사용
    if file_info.doc_type != DocType.UNKNOWN:
        return file_info.doc_type.value

    # 파일 경로 기반 분류
    path_str = str(file_info.file_path).lower()

    path_type_map = {
        "design": "technical",
        "planning": "technical",
        "implementation": "technical",
        "testing": "technical",
        "development": "guide",
        "deployment": "guide",
        "maintenance": "guide",
        "guide": "guide",
        "manual": "guide",
        "presentation": "presentation",
        "policy": "policy",
        "standard": "standard",
        "report": "report",
    }

    for keyword, doc_type in path_type_map.items():
        if keyword in path_str:
            return doc_type

    # 내용 기반 분류 (간단한 규칙)
    if parsed_doc and parsed_doc.content:
        content_preview = parsed_doc.content[:2000].lower()

        if any(kw in content_preview for kw in ["설계", "아키텍처", "스키마", "api"]):
            return "technical"
        if any(kw in content_preview for kw in ["가이드", "매뉴얼", "사용법", "설치"]):
            return "guide"
        if any(kw in content_preview for kw in ["보고", "결과", "분석"]):
            return "report"

    return "unknown"
