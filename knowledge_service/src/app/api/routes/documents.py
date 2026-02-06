"""
문서 업로드 및 관리 API 엔드포인트

문서 업로드, 처리 상태 조회, 문서 목록 관리
"""

import json
import math
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Form, HTTPException, Query, UploadFile, status

from app.core.config import settings
from app.core.logging import get_logger
from app.models.document import (
    DocumentFormat,
    DocumentListItem,
    DocumentListResponse,
    DocumentMetadataInput,
    DocumentResponse,
    DocumentStatus,
    DocumentStatusResponse,
)
from app.services.storage import upload_file

logger = get_logger(__name__)

router = APIRouter()

# ============================================================================
# Constants
# ============================================================================

# 지원 형식별 MIME 타입 매핑
ALLOWED_MIME_TYPES: Dict[str, DocumentFormat] = {
    "application/pdf": DocumentFormat.PDF,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocumentFormat.DOCX,
    "application/haansofthwp": DocumentFormat.HWP,
    "application/x-hwp": DocumentFormat.HWP,
    "application/vnd.hancom.hwp": DocumentFormat.HWP,
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": DocumentFormat.PPTX,
}

# 확장자별 문서 형식 매핑
ALLOWED_EXTENSIONS: Dict[str, DocumentFormat] = {
    ".pdf": DocumentFormat.PDF,
    ".docx": DocumentFormat.DOCX,
    ".hwp": DocumentFormat.HWP,
    ".pptx": DocumentFormat.PPTX,
}

# 형식별 최대 파일 크기 (바이트)
MAX_FILE_SIZES: Dict[DocumentFormat, int] = {
    DocumentFormat.PDF: 100 * 1024 * 1024,   # 100MB
    DocumentFormat.PPTX: 100 * 1024 * 1024,  # 100MB
    DocumentFormat.DOCX: 50 * 1024 * 1024,   # 50MB
    DocumentFormat.HWP: 50 * 1024 * 1024,    # 50MB
}

# 스토리지 버킷명
DOCUMENTS_BUCKET = "documents"

# In-memory 문서 저장소 (PostgreSQL dual-write와 함께 사용)
# 인메모리: 빠른 조회 / PostgreSQL: 영구 저장 (컨테이너 재시작 후 복구)
_document_store: Dict[UUID, Dict[str, Any]] = {}


# ============================================================================
# Utility Functions
# ============================================================================


def _sanitize_filename(filename: str) -> str:
    """
    파일명 보안 처리

    - 경로 순회 방지 (../ 등)
    - 특수문자 제거
    - 한국어 파일명 유지
    - 길이 제한 (255자)

    Args:
        filename: 원본 파일명

    Returns:
        보안 처리된 파일명
    """
    # None/빈 문자열 처리
    if not filename:
        return "unnamed_document"

    # 경로 구분자 제거 (path traversal 방지)
    filename = filename.replace("/", "_").replace("\\", "_")

    # ".." 방지
    filename = filename.replace("..", "_")

    # Unicode 정규화 (NFC - 한국어 자모 조합 유지)
    filename = unicodedata.normalize("NFC", filename)

    # 허용 문자: 알파벳, 숫자, 한글, 일본어, 중국어, 하이픈, 언더스코어, 마침표
    # 그 외 문자는 언더스코어로 치환
    sanitized = re.sub(
        r"[^\w\s\-.\u3131-\u3163\uac00-\ud7a3\u4e00-\u9fff\u3040-\u30ff]",
        "_",
        filename,
    )

    # 연속된 언더스코어 정리
    sanitized = re.sub(r"_{2,}", "_", sanitized)

    # 앞뒤 공백/특수문자 제거
    sanitized = sanitized.strip(" _.")

    # 빈 문자열이면 기본값
    if not sanitized:
        return "unnamed_document"

    # 길이 제한 (확장자 포함 255자)
    if len(sanitized) > 255:
        name_part, _, ext_part = sanitized.rpartition(".")
        if ext_part:
            max_name_len = 255 - len(ext_part) - 1
            sanitized = f"{name_part[:max_name_len]}.{ext_part}"
        else:
            sanitized = sanitized[:255]

    return sanitized


def _detect_format(filename: str, content_type: Optional[str]) -> Optional[DocumentFormat]:
    """
    파일 형식 감지 (확장자 + MIME 타입 검증)

    Args:
        filename: 파일명
        content_type: MIME 타입

    Returns:
        DocumentFormat 또는 None (미지원 형식)
    """
    # 확장자 기반 감지
    ext = ""
    if filename:
        dot_idx = filename.rfind(".")
        if dot_idx >= 0:
            ext = filename[dot_idx:].lower()

    format_by_ext = ALLOWED_EXTENSIONS.get(ext)

    # MIME 타입 기반 감지
    format_by_mime = None
    if content_type:
        format_by_mime = ALLOWED_MIME_TYPES.get(content_type)

    # 확장자와 MIME 타입 중 하나라도 유효하면 허용
    # (일부 브라우저/클라이언트가 정확한 MIME을 보내지 않는 경우 대비)
    if format_by_ext is not None:
        return format_by_ext

    if format_by_mime is not None:
        return format_by_mime

    return None


def _get_content_type_for_format(doc_format: DocumentFormat) -> str:
    """
    문서 형식에 대한 MIME 타입 반환

    Args:
        doc_format: 문서 형식

    Returns:
        MIME 타입 문자열
    """
    mime_map = {
        DocumentFormat.PDF: "application/pdf",
        DocumentFormat.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        DocumentFormat.HWP: "application/haansofthwp",
        DocumentFormat.PPTX: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }
    return mime_map.get(doc_format, "application/octet-stream")


# ============================================================================
# API Endpoints
# ============================================================================


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="문서 업로드",
    description="문서 파일을 업로드합니다. 지원 형식: PDF, DOCX, HWP, PPTX",
)
async def upload_document(
    file: UploadFile,
    metadata: Optional[str] = Form(
        default=None,
        description="메타데이터 JSON 문자열 (title, description, tags, project_name)",
    ),
) -> DocumentResponse:
    """
    문서 업로드 API

    파일을 업로드하고 처리 대기열에 추가합니다.

    지원 형식:
    - PDF: 최대 100MB
    - PPTX: 최대 100MB
    - DOCX: 최대 50MB
    - HWP: 최대 50MB

    Args:
        file: 업로드 파일
        metadata: 메타데이터 JSON 문자열 (선택)

    Returns:
        업로드된 문서 정보 (document_id, status_url 포함)

    Raises:
        HTTPException 400: 지원하지 않는 형식 또는 잘못된 메타데이터
        HTTPException 413: 파일 크기 초과
    """
    logger.info(
        "Document upload request - filename: %s, content_type: %s",
        file.filename,
        file.content_type,
    )

    # 1. 파일명 처리 및 보안
    safe_filename = _sanitize_filename(file.filename or "unnamed_document")

    # 2. 파일 형식 검증
    doc_format = _detect_format(file.filename or "", file.content_type)
    if doc_format is None:
        supported = ", ".join(f.value.upper() for f in DocumentFormat)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"지원하지 않는 파일 형식입니다. 지원 형식: {supported}",
        )

    # 3. 파일 데이터 읽기
    try:
        file_data = await file.read()
    except Exception as e:
        logger.error("Failed to read uploaded file: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="파일을 읽을 수 없습니다",
        )
    finally:
        await file.close()

    file_size = len(file_data)

    # 4. 파일 크기 검증
    max_size = MAX_FILE_SIZES.get(doc_format, 50 * 1024 * 1024)
    if file_size > max_size:
        max_mb = max_size / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"파일 크기가 제한을 초과했습니다. "
                f"{doc_format.value.upper()} 최대 크기: {max_mb:.0f}MB, "
                f"업로드 크기: {file_size / (1024 * 1024):.1f}MB"
            ),
        )

    # 5. 빈 파일 검증
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="빈 파일은 업로드할 수 없습니다",
        )

    # 6. 메타데이터 파싱
    parsed_metadata: Optional[DocumentMetadataInput] = None
    if metadata:
        try:
            metadata_dict = json.loads(metadata)
            parsed_metadata = DocumentMetadataInput(**metadata_dict)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="메타데이터 JSON 형식이 올바르지 않습니다",
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"메타데이터 검증 실패: {str(e)}",
            )

    # 7. document_id 생성
    document_id = uuid4()
    now = datetime.now(timezone.utc)

    # 8. 파일 저장
    object_name = f"{document_id}/{safe_filename}"
    content_type = _get_content_type_for_format(doc_format)

    try:
        storage_path = await upload_file(
            file_data=file_data,
            bucket=DOCUMENTS_BUCKET,
            object_name=object_name,
            content_type=content_type,
        )
    except IOError as e:
        logger.error("File storage failed for document %s: %s", document_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="파일 저장에 실패했습니다. 잠시 후 다시 시도해주세요.",
        )

    # 9. 문서 레코드 저장 (In-memory + PostgreSQL dual-write)
    status_url = f"{settings.api_v1_prefix}/documents/{document_id}/status"

    doc_record = {
        "document_id": document_id,
        "filename": safe_filename,
        "original_filename": file.filename,
        "format": doc_format,
        "size_bytes": file_size,
        "status": DocumentStatus.QUEUED,
        "progress_percent": 0,
        "error_message": None,
        "storage_path": storage_path,
        "metadata": parsed_metadata,
        "created_at": now,
        "updated_at": now,
    }
    _document_store[document_id] = doc_record

    # PostgreSQL에도 저장 (dual-write, 영구 저장)
    try:
        from app.services.document_repository import get_document_repository

        repo = await get_document_repository()
        await repo.save(doc_record)
        logger.info("Document saved to PostgreSQL: %s", document_id)
    except Exception as e:
        logger.warning("PostgreSQL save failed (non-critical): %s", e)

    logger.info(
        "Document uploaded successfully - id: %s, filename: %s, format: %s, size: %d bytes",
        document_id,
        safe_filename,
        doc_format.value,
        file_size,
    )

    return DocumentResponse(
        document_id=document_id,
        filename=safe_filename,
        format=doc_format,
        size_bytes=file_size,
        status=DocumentStatus.QUEUED,
        status_url=status_url,
        created_at=now,
        metadata=parsed_metadata,
    )


@router.get(
    "/{document_id}/status",
    response_model=DocumentStatusResponse,
    summary="문서 처리 상태 조회",
    description="업로드된 문서의 처리 상태를 조회합니다",
)
async def get_document_status(document_id: UUID) -> DocumentStatusResponse:
    """
    문서 처리 상태 조회

    Args:
        document_id: 문서 UUID

    Returns:
        문서 처리 상태 정보

    Raises:
        HTTPException 404: 문서를 찾을 수 없음
    """
    doc_record = _document_store.get(document_id)

    # PostgreSQL fallback (인메모리에 없을 때, 예: 컨테이너 재시작 후)
    if doc_record is None:
        try:
            from app.services.document_repository import get_document_repository

            repo = await get_document_repository()
            doc_record = await repo.get(document_id)
        except Exception as e:
            logger.warning("PostgreSQL query failed: %s", e)

    if doc_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"문서를 찾을 수 없습니다: {document_id}",
        )

    return DocumentStatusResponse(
        document_id=doc_record["document_id"],
        status=doc_record["status"],
        progress_percent=doc_record.get("progress_percent", 0),
        error_message=doc_record.get("error_message"),
        updated_at=doc_record["updated_at"],
    )


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="문서 목록 조회",
    description="업로드된 문서 목록을 페이지네이션으로 조회합니다",
)
async def list_documents(
    page: int = Query(default=1, ge=1, description="페이지 번호"),
    page_size: int = Query(default=20, ge=1, le=100, description="페이지 크기"),
    status_filter: Optional[DocumentStatus] = Query(
        default=None,
        alias="status",
        description="상태 필터 (queued, processing, completed, failed)",
    ),
    format_filter: Optional[DocumentFormat] = Query(
        default=None,
        alias="format",
        description="형식 필터 (pdf, docx, hwp, pptx)",
    ),
) -> DocumentListResponse:
    """
    문서 목록 조회 (페이지네이션)

    Args:
        page: 페이지 번호 (1부터 시작)
        page_size: 페이지 크기 (기본 20, 최대 100)
        status_filter: 상태 필터 (선택)
        format_filter: 형식 필터 (선택)

    Returns:
        문서 목록 및 페이지네이션 정보
    """
    # 전체 목록에서 필터링
    all_docs = list(_document_store.values())

    # 인메모리가 비어있으면 PostgreSQL에서 조회 (컨테이너 재시작 후 fallback)
    if not all_docs:
        try:
            from app.services.document_repository import get_document_repository

            repo = await get_document_repository()
            status_val = status_filter.value if status_filter else None
            format_val = format_filter.value if format_filter else None
            pg_docs, pg_total = await repo.list_all(
                status_filter=status_val,
                format_filter=format_val,
                page=page,
                page_size=page_size,
            )
            if pg_docs:
                items = [
                    DocumentListItem(
                        document_id=d["document_id"],
                        filename=d["filename"],
                        format=d.get("format") or "unknown",
                        size_bytes=d["size_bytes"],
                        status=d["status"],
                        created_at=d["created_at"],
                    )
                    for d in pg_docs
                ]
                total_pages = max(1, math.ceil(pg_total / page_size))
                return DocumentListResponse(
                    documents=items,
                    total=pg_total,
                    page=page,
                    page_size=page_size,
                    total_pages=total_pages,
                )
        except Exception as e:
            logger.warning("PostgreSQL list failed: %s", e)

    if status_filter is not None:
        all_docs = [d for d in all_docs if d["status"] == status_filter]

    if format_filter is not None:
        all_docs = [d for d in all_docs if d["format"] == format_filter]

    # 최신 순 정렬
    all_docs.sort(key=lambda d: d["created_at"], reverse=True)

    total = len(all_docs)
    total_pages = max(1, math.ceil(total / page_size))

    # 페이지 슬라이싱
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_docs = all_docs[start_idx:end_idx]

    items = [
        DocumentListItem(
            document_id=d["document_id"],
            filename=d["filename"],
            format=d["format"],
            size_bytes=d["size_bytes"],
            status=d["status"],
            created_at=d["created_at"],
        )
        for d in page_docs
    ]

    return DocumentListResponse(
        documents=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# ============================================================================
# Processing Endpoints
# ============================================================================


@router.post(
    "/{document_id}/process",
    summary="문서 처리 트리거",
    description="업로드된 문서의 처리(파싱, 청킹, 임베딩, 저장)를 수동으로 트리거합니다",
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_document_processing(document_id: UUID) -> Dict[str, Any]:
    """
    문서 처리 트리거 API

    업로드된 문서의 자동 처리 파이프라인을 수동으로 시작합니다.
    처리는 비동기로 진행되며, /status 엔드포인트로 진행 상황을 확인할 수 있습니다.

    Args:
        document_id: 문서 UUID

    Returns:
        처리 시작 응답 (status, message, status_url)

    Raises:
        HTTPException 404: 문서를 찾을 수 없음
        HTTPException 409: 이미 처리 중이거나 완료됨
    """
    from app.services.document_processing_pipeline import (
        DocumentProcessingPipeline,
        ProcessingStatus,
    )
    import asyncio

    doc_record = _document_store.get(document_id)

    if doc_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"문서를 찾을 수 없습니다: {document_id}",
        )

    current_status = doc_record.get("status")
    status_value = current_status.value if hasattr(current_status, "value") else str(current_status)

    # 이미 처리 중인 경우
    if status_value in (ProcessingStatus.PROCESSING, ProcessingStatus.PARSING,
                        ProcessingStatus.CHUNKING, ProcessingStatus.EMBEDDING,
                        ProcessingStatus.STORING, ProcessingStatus.EXTRACTING):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"문서가 이미 처리 중입니다. 현재 상태: {status_value}",
        )

    # 이미 완료된 경우 (재처리 허용 가능하도록 주석 처리)
    # if status_value == ProcessingStatus.COMPLETED:
    #     raise HTTPException(
    #         status_code=status.HTTP_409_CONFLICT,
    #         detail="문서 처리가 이미 완료되었습니다",
    #     )

    # 파이프라인 생성 및 비동기 처리 시작
    pipeline = DocumentProcessingPipeline(
        document_store=_document_store,
        enable_neo4j=True,
        enable_entity_extraction=True,
    )

    # 백그라운드에서 처리 시작
    async def run_processing():
        try:
            result = await pipeline.process_document(document_id)
            logger.info(
                f"Document processing finished: {document_id}, "
                f"success={result.success}, "
                f"chunks={result.chunk_count}"
            )
        except Exception as e:
            logger.exception(f"Background processing failed: {document_id}")

    # 비동기 태스크로 실행
    asyncio.create_task(run_processing())

    logger.info(f"Document processing triggered: {document_id}")

    return {
        "document_id": str(document_id),
        "status": "accepted",
        "message": "문서 처리가 시작되었습니다",
        "status_url": f"{settings.api_v1_prefix}/documents/{document_id}/status",
    }


@router.post(
    "/process-pending",
    summary="대기 문서 일괄 처리",
    description="업로드 후 대기 중인 모든 문서를 일괄 처리합니다",
    status_code=status.HTTP_202_ACCEPTED,
)
async def process_pending_documents(
    batch_size: int = Query(default=5, ge=1, le=20, description="한 번에 처리할 문서 수"),
) -> Dict[str, Any]:
    """
    대기 중인 문서 일괄 처리 API

    queued 또는 uploaded 상태의 문서들을 일괄 처리합니다.

    Args:
        batch_size: 한 번에 처리할 문서 수 (기본 5, 최대 20)

    Returns:
        처리 시작 응답 (count, status)
    """
    from app.services.document_processing_pipeline import (
        DocumentProcessingPipeline,
        ProcessingStatus,
    )
    import asyncio

    # 대기 중인 문서 조회
    pending_docs = [
        doc for doc in _document_store.values()
        if (hasattr(doc.get("status"), "value") and
            doc.get("status").value in ("queued", "uploaded")) or
           (doc.get("status") in ("queued", "uploaded"))
    ][:batch_size]

    if not pending_docs:
        return {
            "count": 0,
            "status": "no_pending",
            "message": "처리할 대기 문서가 없습니다",
        }

    # 파이프라인 생성
    pipeline = DocumentProcessingPipeline(
        document_store=_document_store,
        enable_neo4j=True,
        enable_entity_extraction=True,
    )

    # 백그라운드에서 일괄 처리
    async def run_batch_processing():
        for doc in pending_docs:
            doc_id = doc.get("document_id")
            if doc_id:
                try:
                    result = await pipeline.process_document(doc_id)
                    logger.info(
                        f"Batch processing result: {doc_id}, success={result.success}"
                    )
                except Exception as e:
                    logger.exception(f"Batch processing failed for {doc_id}")

    asyncio.create_task(run_batch_processing())

    logger.info(f"Batch processing triggered for {len(pending_docs)} documents")

    return {
        "count": len(pending_docs),
        "status": "accepted",
        "message": f"{len(pending_docs)}개 문서 처리가 시작되었습니다",
        "document_ids": [str(doc.get("document_id")) for doc in pending_docs],
    }


# ============================================================================
# Internal helper (for testing)
# ============================================================================


def _clear_document_store() -> None:
    """
    문서 저장소 초기화 (테스트용)

    WARNING: 테스트 환경에서만 사용하세요.
    """
    _document_store.clear()


def _get_document_store() -> Dict[UUID, Dict[str, Any]]:
    """
    문서 저장소 참조 반환 (파이프라인 연동용)

    Returns:
        In-memory 문서 저장소 딕셔너리
    """
    return _document_store
