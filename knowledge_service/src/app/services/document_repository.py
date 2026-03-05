"""
PostgreSQL 문서 저장소

In-memory Dict를 대체하는 영구 저장소.
asyncpg를 사용하여 비동기 PostgreSQL 연결.

Dual-write 패턴:
- 인메모리 저장소와 PostgreSQL에 동시 저장
- 조회 시 인메모리 우선, PostgreSQL fallback
- 컨테이너 재시작 후에도 문서 목록 유지
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _naive_utcnow() -> datetime:
    """asyncpg 호환 naive UTC datetime 반환.

    PostgreSQL 'timestamp without time zone' 컬럼에는
    timezone-aware datetime을 넣을 수 없으므로 tzinfo를 제거합니다.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _strip_tz(dt: Optional[datetime]) -> Optional[datetime]:
    """timezone-aware datetime에서 tzinfo를 제거."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt
from uuid import UUID

import asyncpg

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class DocumentRepository:
    """PostgreSQL 기반 문서 저장소

    asyncpg 커넥션 풀을 사용하여 documents 테이블에
    비동기로 CRUD 연산을 수행합니다.

    Attributes:
        _pool: asyncpg 커넥션 풀 (None이면 미초기화 상태)
    """

    def __init__(self, pool: Optional[asyncpg.Pool] = None):
        """DocumentRepository 생성

        Args:
            pool: 기존 asyncpg 풀 (테스트 등에서 주입 가능).
                  None이면 init_pool()에서 새로 생성.
        """
        self._pool = pool

    async def init_pool(self) -> None:
        """커넥션 풀 초기화

        settings에서 PostgreSQL 연결 정보를 읽어
        min_size=2, max_size=10 풀을 생성합니다.
        """
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                host=settings.postgres_host,
                port=settings.postgres_port,
                user=settings.postgres_user,
                password=settings.postgres_password,
                database=settings.postgres_db,
                min_size=2,
                max_size=10,
            )
            logger.info("DocumentRepository PostgreSQL pool initialized")

    async def close(self) -> None:
        """커넥션 풀 종료"""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("DocumentRepository PostgreSQL pool closed")

    async def save(self, doc_record: Dict[str, Any]) -> None:
        """문서 레코드 저장 (INSERT or UPDATE via UPSERT)

        doc_record는 documents.py의 인메모리 딕셔너리 형식입니다.
        PostgreSQL documents 테이블 스키마에 맞게 변환하여 저장합니다.

        Args:
            doc_record: 인메모리 문서 레코드 딕셔너리.
                필수 키: document_id, status
                선택 키: filename, format, size_bytes, storage_path,
                         metadata, created_at, updated_at
        """
        if self._pool is None:
            logger.warning("PostgreSQL pool not initialized - skipping save")
            return

        doc_id = doc_record["document_id"]

        # status enum -> string
        status_val = doc_record["status"]
        if hasattr(status_val, "value"):
            status_val = status_val.value

        # metadata -> JSON string
        metadata_json = None
        if doc_record.get("metadata"):
            meta = doc_record["metadata"]
            if hasattr(meta, "model_dump"):
                metadata_json = json.dumps(meta.model_dump(), default=str)
            elif isinstance(meta, dict):
                metadata_json = json.dumps(meta, default=str)

        # format enum -> string
        format_val = doc_record.get("format")
        if hasattr(format_val, "value"):
            format_val = format_val.value

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO documents (
                    id, title, document_type, file_path, file_name,
                    file_size, file_type, file_hash, processing_status,
                    chunk_count, raw_metadata, created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb, $12, $13)
                ON CONFLICT (id) DO UPDATE SET
                    processing_status = EXCLUDED.processing_status,
                    file_hash = EXCLUDED.file_hash,
                    chunk_count = EXCLUDED.chunk_count,
                    raw_metadata = EXCLUDED.raw_metadata,
                    updated_at = EXCLUDED.updated_at
                """,
                doc_id,
                doc_record.get("filename", "untitled"),
                format_val or "unknown",
                doc_record.get("storage_path", ""),
                doc_record.get("filename", ""),
                doc_record.get("size_bytes", 0),
                format_val,
                doc_record.get("file_hash"),
                status_val,
                doc_record.get("chunk_count", 0),
                metadata_json or "{}",
                _strip_tz(doc_record.get("created_at")) or _naive_utcnow(),
                _strip_tz(doc_record.get("updated_at")) or _naive_utcnow(),
            )

    async def get(self, document_id: UUID) -> Optional[Dict[str, Any]]:
        """문서 조회

        Args:
            document_id: 조회할 문서 UUID

        Returns:
            API 응답용 딕셔너리 또는 None (미존재 시)
        """
        if self._pool is None:
            return None

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM documents WHERE id = $1", document_id
            )
            if row is None:
                return None
            return self._row_to_dict(row)

    async def list_all(
        self,
        status_filter: Optional[str] = None,
        format_filter: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[Dict[str, Any]], int]:
        """문서 목록 조회 (페이지네이션)

        Args:
            status_filter: 처리 상태 필터 (예: "queued", "completed")
            format_filter: 파일 형식 필터 (예: "pdf", "docx")
            page: 페이지 번호 (1부터 시작)
            page_size: 페이지 크기

        Returns:
            (문서 목록, 전체 개수) 튜플
        """
        if self._pool is None:
            return [], 0

        conditions: List[str] = []
        params: List[Any] = []
        param_idx = 1

        if status_filter:
            conditions.append(f"processing_status = ${param_idx}")
            params.append(status_filter)
            param_idx += 1

        if format_filter:
            conditions.append(f"file_type = ${param_idx}")
            params.append(format_filter)
            param_idx += 1

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        async with self._pool.acquire() as conn:
            count = await conn.fetchval(
                f"SELECT COUNT(*) FROM documents WHERE {where_clause}",
                *params,
            )

            offset = (page - 1) * page_size
            rows = await conn.fetch(
                f"""SELECT * FROM documents WHERE {where_clause}
                    ORDER BY created_at DESC
                    LIMIT ${param_idx} OFFSET ${param_idx + 1}""",
                *params,
                page_size,
                offset,
            )

        docs = [self._row_to_dict(row) for row in rows]
        return docs, count

    async def update_status(
        self,
        document_id: UUID,
        status: str,
        error_message: Optional[str] = None,
        progress_percent: int = 0,
        chunk_count: Optional[int] = None,
        entity_count: Optional[int] = None,
        es_synced: Optional[bool] = None,
        neo4j_synced: Optional[bool] = None,
    ) -> None:
        """문서 처리 상태 업데이트

        Args:
            document_id: 문서 UUID
            status: 새 처리 상태 문자열
            error_message: 에러 메시지 (실패 시)
            progress_percent: 진행률 0-100 (STORY-089: ETL Phase별 반영)
            chunk_count: 청크 수 (처리 완료 시)
            entity_count: 엔티티 수 (처리 완료 시)
            es_synced: ES 동기화 완료 여부
            neo4j_synced: Neo4j 동기화 완료 여부
        """
        if self._pool is None:
            return

        now = _naive_utcnow()

        # 동적 SET 절 구성
        set_parts = [
            "processing_status = $2",
            "processing_error = $3",
            "updated_at = $4",
            "progress_percent = $5",  # STORY-089: 진행률 반영
        ]
        params: list = [document_id, status, error_message, now, progress_percent]
        idx = 6

        # 완료 시 processed_at 기록
        if status == "completed":
            set_parts.append(f"processed_at = ${idx}")
            params.append(now)
            idx += 1

        if chunk_count is not None:
            set_parts.append(f"chunk_count = ${idx}")
            params.append(chunk_count)
            idx += 1

        if entity_count is not None:
            set_parts.append(f"entity_count = ${idx}")
            params.append(entity_count)
            idx += 1

        if es_synced is not None:
            set_parts.append(f"es_synced = ${idx}")
            params.append(es_synced)
            idx += 1
            if es_synced:
                set_parts.append(f"es_synced_at = ${idx}")
                params.append(now)
                idx += 1

        if neo4j_synced is not None:
            set_parts.append(f"neo4j_synced = ${idx}")
            params.append(neo4j_synced)
            idx += 1
            if neo4j_synced:
                set_parts.append(f"neo4j_synced_at = ${idx}")
                params.append(now)
                idx += 1

        set_clause = ",\n                    ".join(set_parts)

        async with self._pool.acquire() as conn:
            await conn.execute(
                f"""
                UPDATE documents
                SET {set_clause}
                WHERE id = $1
                """,
                *params,
            )

    def _row_to_dict(self, row: asyncpg.Record) -> Dict[str, Any]:
        """DB row를 API 응답용 dict로 변환

        documents 테이블의 컬럼명을 인메모리 딕셔너리
        키 형식으로 매핑합니다.

        Args:
            row: asyncpg.Record (SELECT 결과)

        Returns:
            인메모리 doc_record와 호환되는 딕셔너리
        """
        raw_metadata = row["raw_metadata"]
        if isinstance(raw_metadata, str):
            parsed_metadata = json.loads(raw_metadata)
        elif isinstance(raw_metadata, dict):
            parsed_metadata = raw_metadata
        else:
            parsed_metadata = None

        return {
            "document_id": row["id"],
            "filename": row["file_name"] or row["title"],
            "original_filename": row["file_name"],
            "format": row["file_type"],
            "size_bytes": row["file_size"] or 0,
            "status": row["processing_status"],
            "progress_percent": 0,
            "error_message": row["processing_error"],
            "storage_path": row["file_path"],
            "metadata": parsed_metadata,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }


# ============================================================================
# Singleton management
# ============================================================================

_document_repo: Optional[DocumentRepository] = None


async def get_document_repository() -> DocumentRepository:
    """DocumentRepository 싱글톤 반환

    초기화되지 않은 경우 자동으로 init_pool()을 호출합니다.

    Returns:
        초기화된 DocumentRepository 인스턴스
    """
    global _document_repo
    if _document_repo is None:
        _document_repo = DocumentRepository()
        await _document_repo.init_pool()
    return _document_repo


async def init_document_repository() -> DocumentRepository:
    """DocumentRepository 초기화 (lifespan에서 호출)

    애플리케이션 시작 시 main.py의 lifespan에서
    명시적으로 호출하여 커넥션 풀을 미리 생성합니다.

    Returns:
        초기화된 DocumentRepository 인스턴스
    """
    global _document_repo
    _document_repo = DocumentRepository()
    await _document_repo.init_pool()
    return _document_repo


async def close_document_repository() -> None:
    """DocumentRepository 종료

    애플리케이션 종료 시 main.py의 lifespan에서
    호출하여 커넥션 풀을 정리합니다.
    """
    global _document_repo
    if _document_repo:
        await _document_repo.close()
        _document_repo = None
