"""
PostgreSQL 적재 모듈

문서 메타데이터를 PostgreSQL(SSOT)에 저장하고,
전체 저장 오케스트레이션(PG -> ES -> Neo4j)을 수행합니다.

Functions:
    store_to_postgresql: PG documents 테이블에 문서 레코드 저장
    update_pg_entity_count: PG entity_count 업데이트
    store_document: 전체 저장 오케스트레이션
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.core.logging import get_logger
from app.services.data_loader.es_loader import store_to_elasticsearch
from app.services.data_loader.graph_loader import store_to_neo4j
from app.services.data_loader.models import FileInfo

logger = get_logger(__name__)


async def store_to_postgresql(
    document_id: str,
    file_info: FileInfo,
    chunks: List[Any],
    metadata: Dict[str, Any],
    file_hash: Optional[str] = None,
) -> Optional[str]:
    """PostgreSQL documents 테이블에 문서 레코드 저장 (SSOT)

    STORY-099: InitialDataLoader에서도 PG에 문서를 등록하여
    ES/Neo4j document_id와 PG id의 정합성을 보장합니다.

    Args:
        document_id: 문서 UUID
        file_info: 파일 정보
        chunks: 청크 리스트 (chunk_count 계산용)
        metadata: 메타데이터 딕셔너리
        file_hash: SHA-256 파일 해시 (STORY-108 dedup용)

    Returns:
        저장된 document_id (성공 시) 또는 None (실패 시)
    """
    try:
        from app.services.document_repository import get_document_repository

        repo = await get_document_repository()

        # document_repository.save()에 맞는 dict 구성
        doc_record = {
            "document_id": document_id,
            "filename": metadata.get("title", file_info.file_name),
            "format": file_info.extension.lstrip(".") if file_info.extension else "unknown",
            "size_bytes": file_info.file_size,
            "storage_path": str(file_info.file_path),
            "status": "completed",
            "metadata": metadata,
            "created_at": file_info.modified_at or datetime.utcnow(),
            "file_hash": file_hash,
            "chunk_count": len(chunks),
        }

        await repo.save(doc_record)

        logger.info(
            "PostgreSQL document saved: doc_id=%s, title=%s",
            document_id[:8],
            doc_record["filename"],
        )
        return document_id

    except ImportError:
        logger.warning(
            "asyncpg not available, skipping PostgreSQL storage for doc_id=%s",
            document_id[:8],
        )
        return None
    except Exception as e:
        logger.warning(
            "PostgreSQL storage failed (non-critical): %s", e
        )
        return None


async def update_pg_entity_count(document_id: str, entity_count: int) -> None:
    """PG documents 테이블의 entity_count 업데이트

    Args:
        document_id: 문서 ID
        entity_count: 엔티티 수
    """
    try:
        from app.services.document_repository import get_document_repository
        repo = await get_document_repository()
        if repo._pool:
            async with repo._pool.acquire() as conn:
                await conn.execute(
                    "UPDATE documents SET entity_count = $1 WHERE id = $2::uuid",
                    entity_count, document_id,
                )
    except Exception as e:
        logger.warning("PG entity_count update failed: %s", e)


async def store_document(
    document_id: str,
    file_info: FileInfo,
    parsed_doc: Any,
    chunks: List[Any],
    embeddings: Optional[List[Any]],
    entities: List[Any],
    metadata: Dict[str, Any],
    file_hash: Optional[str] = None,
    es_client_holder: Any = None,
) -> str:
    """문서 데이터를 저장소에 적재

    PostgreSQL (SSOT) -> Elasticsearch (청크 + 벡터) -> Neo4j (엔티티 + 관계)
    순서로 저장합니다. PG에서 생성된 document_id를 ES/Neo4j에 전달하여
    ID 정합성을 보장합니다. (STORY-099)

    저장소가 사용 불가능한 경우 로깅 후 건너뜁니다.

    Args:
        document_id: 문서 ID (초기 UUID)
        file_info: 파일 정보
        parsed_doc: 파싱된 문서
        chunks: 청크 리스트
        embeddings: 임베딩 리스트 (선택)
        entities: 엔티티 리스트
        metadata: 메타데이터 딕셔너리
        file_hash: SHA-256 파일 해시 (STORY-108 dedup용)
        es_client_holder: ES 클라이언트를 보유한 객체

    Returns:
        실제 저장된 document_id (PG 우선)
    """
    # STORY-099: metadata.title에 실제 파일명 보장
    if not metadata.get("title") or metadata["title"] == "untitled":
        metadata["title"] = file_info.file_name

    # PostgreSQL 저장 (SSOT - 가장 먼저 저장)
    pg_doc_id = await store_to_postgresql(
        document_id=document_id,
        file_info=file_info,
        chunks=chunks,
        metadata=metadata,
        file_hash=file_hash,
    )
    # PG 저장 성공 시 PG ID 사용, 실패 시 원래 UUID 유지
    effective_doc_id = pg_doc_id or document_id

    # Elasticsearch 저장
    await store_to_elasticsearch(
        document_id=effective_doc_id,
        chunks=chunks,
        embeddings=embeddings,
        metadata=metadata,
        es_client_holder=es_client_holder,
    )

    # Neo4j 저장
    await store_to_neo4j(
        document_id=effective_doc_id,
        file_info=file_info,
        chunks=chunks,
        entities=entities,
        metadata=metadata,
    )

    # PG entity_count 업데이트 (엔티티 추출 완료 후)
    if entities and pg_doc_id:
        await update_pg_entity_count(pg_doc_id, len(entities))

    return effective_doc_id
