"""
문서 처리 파이프라인

STORY: Document Upload 후 자동 처리 파이프라인
- PostgreSQL에서 uploaded 상태 문서 감지
- MinIO에서 파일 다운로드
- 텍스트 추출 및 청킹
- 임베딩 생성
- Elasticsearch 저장 (벡터 검색용)
- Neo4j 저장 (Knowledge Graph)
- PostgreSQL status 업데이트

Pipeline Flow:
    uploaded -> processing -> completed/failed
"""

import asyncio
import os
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.core.config import settings
from app.core.logging import get_logger
from app.etl.chunker import SemanticChunker
from app.etl.parser import DocumentParser
from app.models.chunk import ChunkResult
from app.services.embedding import EmbeddingService, get_embedding_service
from app.services.entity_extraction import (
    EntityExtractionService,
    get_entity_extraction_service,
)
from app.storage.es_storage import (
    ElasticsearchStorageService,
    get_es_storage_service,
)
from app.storage.neo4j_storage import (
    Neo4jStorageService,
    get_neo4j_storage_service,
)

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Processing Status
# ---------------------------------------------------------------------------


class ProcessingStatus:
    """문서 처리 상태 상수"""

    UPLOADED = "uploaded"
    QUEUED = "queued"
    PROCESSING = "processing"
    PARSING = "parsing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    STORING = "storing"
    EXTRACTING = "extracting"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ProcessingResult:
    """파이프라인 처리 결과

    Attributes:
        document_id: 문서 UUID
        success: 성공 여부
        status: 최종 상태
        chunk_count: 생성된 청크 수
        entity_count: 추출된 엔티티 수
        relationship_count: 추출된 관계 수
        processing_time_ms: 처리 시간 (밀리초)
        error_message: 에러 메시지 (실패 시)
    """

    document_id: str
    success: bool
    status: str
    chunk_count: int = 0
    entity_count: int = 0
    relationship_count: int = 0
    processing_time_ms: float = 0.0
    error_message: Optional[str] = None


# ---------------------------------------------------------------------------
# Document Repository Interface
# ---------------------------------------------------------------------------


class DocumentRepository:
    """
    문서 저장소 인터페이스

    PostgreSQL 연동과 In-memory 저장소를 모두 지원합니다.
    - document_store가 None이면 PostgreSQL 사용
    - document_store가 제공되면 In-memory 사용 (테스트용)

    PostgreSQL 연동:
        SQLAlchemy async 세션을 사용하여 documents 테이블과 상호작용.
    """

    def __init__(self, document_store: Optional[Dict[UUID, Dict[str, Any]]] = None):
        """
        초기화

        Args:
            document_store: In-memory 문서 저장소 (None이면 PostgreSQL 사용)
        """
        self._store = document_store
        self._use_memory = document_store is not None

        if not self._use_memory:
            logger.info("DocumentRepository initialized with PostgreSQL backend")
        else:
            logger.info("DocumentRepository initialized with in-memory backend (testing)")

    async def get_documents_by_status(
        self,
        status: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        특정 상태의 문서 목록 조회

        Args:
            status: 문서 상태 (uploaded, queued, processing 등)
            limit: 최대 조회 개수

        Returns:
            문서 딕셔너리 리스트
        """
        if self._use_memory:
            results = []
            for doc in self._store.values():
                doc_status = doc.get("status")
                # Enum 또는 문자열 처리
                if hasattr(doc_status, "value"):
                    doc_status = doc_status.value
                if doc_status == status:
                    results.append(doc)
                    if len(results) >= limit:
                        break
            return results

        # PostgreSQL 연동
        try:
            from sqlalchemy import select
            from app.core.database import DocumentModel, get_async_session

            async with get_async_session() as session:
                query = (
                    select(DocumentModel)
                    .where(DocumentModel.status == status)
                    .order_by(DocumentModel.created_at.asc())
                    .limit(limit)
                )
                result = await session.execute(query)
                documents = result.scalars().all()

                return [doc.to_dict() for doc in documents]

        except Exception as e:
            logger.error(f"PostgreSQL query failed: {e}")
            return []

    async def update_document_status(
        self,
        document_id: UUID,
        status: str,
        progress_percent: int = 0,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        문서 상태 업데이트

        Args:
            document_id: 문서 UUID
            status: 새 상태
            progress_percent: 진행률 (0-100)
            error_message: 에러 메시지 (실패 시)
            metadata: 추가 메타데이터

        Returns:
            업데이트 성공 여부
        """
        if self._use_memory:
            if document_id not in self._store:
                logger.warning(f"Document not found: {document_id}")
                return False

            self._store[document_id]["status"] = status
            self._store[document_id]["progress_percent"] = progress_percent
            self._store[document_id]["updated_at"] = datetime.now(timezone.utc)

            if error_message is not None:
                self._store[document_id]["error_message"] = error_message

            if metadata:
                existing_meta = self._store[document_id].get("processing_metadata", {})
                existing_meta.update(metadata)
                self._store[document_id]["processing_metadata"] = existing_meta

            logger.debug(
                f"Document status updated: {document_id} -> {status} ({progress_percent}%)"
            )
            return True

        # PostgreSQL 연동
        try:
            from sqlalchemy import update
            from app.core.database import DocumentModel, get_async_session

            async with get_async_session() as session:
                # 업데이트할 값 준비
                update_values = {
                    "status": status,
                    "progress_percent": progress_percent,
                }

                if error_message is not None:
                    update_values["error_message"] = error_message

                # metadata에서 처리 결과 추출
                if metadata:
                    if "chunk_count" in metadata:
                        update_values["chunk_count"] = metadata["chunk_count"]
                    if "entity_count" in metadata:
                        update_values["entity_count"] = metadata["entity_count"]
                    if "relationship_count" in metadata:
                        update_values["relationship_count"] = metadata["relationship_count"]

                query = (
                    update(DocumentModel)
                    .where(DocumentModel.id == str(document_id))
                    .values(**update_values)
                )
                result = await session.execute(query)

                if result.rowcount > 0:
                    logger.debug(
                        f"Document status updated: {document_id} -> {status} ({progress_percent}%)"
                    )
                    return True
                else:
                    logger.warning(f"Document not found for update: {document_id}")
                    return False

        except Exception as e:
            logger.error(f"PostgreSQL update failed: {e}")
            return False

    async def get_document(self, document_id: UUID) -> Optional[Dict[str, Any]]:
        """
        문서 조회

        Args:
            document_id: 문서 UUID

        Returns:
            문서 딕셔너리 또는 None
        """
        if self._use_memory:
            return self._store.get(document_id)

        # PostgreSQL 연동
        try:
            from sqlalchemy import select
            from app.core.database import DocumentModel, get_async_session

            async with get_async_session() as session:
                query = select(DocumentModel).where(DocumentModel.id == str(document_id))
                result = await session.execute(query)
                document = result.scalar_one_or_none()

                if document:
                    return document.to_dict()
                return None

        except Exception as e:
            logger.error(f"PostgreSQL query failed: {e}")
            return None

    async def create_document(
        self,
        document_id: UUID,
        filename: str,
        format_type: str,
        size_bytes: int,
        storage_path: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        새 문서 생성

        Args:
            document_id: 문서 UUID
            filename: 파일명
            format_type: 문서 형식 (pdf, docx, hwp, pptx)
            size_bytes: 파일 크기 (바이트)
            storage_path: 스토리지 경로
            metadata: 추가 메타데이터

        Returns:
            생성된 문서 딕셔너리 또는 None
        """
        if self._use_memory:
            doc = {
                "document_id": document_id,
                "filename": filename,
                "format": format_type,
                "size_bytes": size_bytes,
                "storage_path": storage_path,
                "status": ProcessingStatus.UPLOADED,
                "progress_percent": 0,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
            if metadata:
                doc.update(metadata)
            self._store[document_id] = doc
            return doc

        # PostgreSQL 연동
        try:
            from app.core.database import DocumentModel, get_async_session

            async with get_async_session() as session:
                new_doc = DocumentModel(
                    id=str(document_id),
                    filename=filename,
                    format=format_type,
                    size_bytes=size_bytes,
                    storage_path=storage_path,
                    status=ProcessingStatus.UPLOADED,
                    title=metadata.get("title") if metadata else None,
                    description=metadata.get("description") if metadata else None,
                    project_name=metadata.get("project_name") if metadata else None,
                )
                session.add(new_doc)
                await session.flush()

                return new_doc.to_dict()

        except Exception as e:
            logger.error(f"PostgreSQL insert failed: {e}")
            return None


# ---------------------------------------------------------------------------
# File Storage Interface
# ---------------------------------------------------------------------------


class FileStorage:
    """
    파일 스토리지 인터페이스

    MinIO 또는 로컬 파일시스템에서 파일을 다운로드합니다.
    """

    @staticmethod
    async def download_file(storage_path: str) -> bytes:
        """
        스토리지에서 파일 다운로드

        Args:
            storage_path: 스토리지 경로 (minio://bucket/path 또는 로컬 경로)

        Returns:
            파일 바이너리 데이터

        Raises:
            FileNotFoundError: 파일을 찾을 수 없는 경우
            IOError: 다운로드 실패
        """
        if storage_path.startswith("minio://"):
            return await FileStorage._download_from_minio(storage_path)
        else:
            return await FileStorage._download_from_local(storage_path)

    @staticmethod
    async def _download_from_minio(storage_path: str) -> bytes:
        """MinIO에서 파일 다운로드"""
        # minio://bucket/object_name 파싱
        path_parts = storage_path.replace("minio://", "").split("/", 1)
        if len(path_parts) != 2:
            raise ValueError(f"Invalid MinIO path: {storage_path}")

        bucket, object_name = path_parts

        try:
            from minio import Minio
            import io

            endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
            access_key = os.getenv("MINIO_ACCESS_KEY", "")
            secret_key = os.getenv("MINIO_SECRET_KEY", "")
            secure = os.getenv("MINIO_SECURE", "false").lower() == "true"

            client = Minio(
                endpoint=endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=secure,
            )

            response = await asyncio.to_thread(
                client.get_object, bucket, object_name
            )
            data = response.read()
            response.close()
            response.release_conn()

            logger.info(f"Downloaded from MinIO: {storage_path} ({len(data)} bytes)")
            return data

        except Exception as e:
            logger.error(f"MinIO download failed: {e}")
            raise IOError(f"MinIO 파일 다운로드 실패: {e}") from e

    @staticmethod
    async def _download_from_local(storage_path: str) -> bytes:
        """로컬 파일시스템에서 파일 다운로드"""
        try:
            path = Path(storage_path)
            if not path.exists():
                raise FileNotFoundError(f"파일을 찾을 수 없습니다: {storage_path}")

            data = await asyncio.to_thread(path.read_bytes)
            logger.info(f"Downloaded from local: {storage_path} ({len(data)} bytes)")
            return data

        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Local file read failed: {e}")
            raise IOError(f"로컬 파일 읽기 실패: {e}") from e


# ---------------------------------------------------------------------------
# Document Processing Pipeline
# ---------------------------------------------------------------------------


class DocumentProcessingPipeline:
    """
    문서 처리 파이프라인

    업로드된 문서를 자동으로 처리하여 검색 가능한 형태로 변환합니다.

    Pipeline Stages:
        1. 파일 다운로드 (MinIO/로컬)
        2. 텍스트 추출 (Docling/네이티브 파서)
        3. 청킹 (SemanticChunker)
        4. 임베딩 생성 (BGE-M3)
        5. Elasticsearch 저장 (벡터 검색)
        6. Neo4j 저장 (Knowledge Graph)
        7. 상태 업데이트 (PostgreSQL)

    Attributes:
        repository: 문서 저장소
        parser: 문서 파서
        chunker: 시맨틱 청커
        embedding_service: 임베딩 서비스
        es_storage: Elasticsearch 저장소
        neo4j_storage: Neo4j 저장소
        entity_extractor: 엔티티 추출 서비스
    """

    def __init__(
        self,
        document_store: Optional[Dict[UUID, Dict[str, Any]]] = None,
        enable_neo4j: bool = True,
        enable_entity_extraction: bool = True,
    ):
        """
        초기화

        Args:
            document_store: In-memory 문서 저장소 (None이면 PostgreSQL 사용)
            enable_neo4j: Neo4j 저장 활성화 여부
            enable_entity_extraction: 엔티티/관계 추출 활성화 여부
        """
        self.repository = DocumentRepository(document_store)
        self.parser = DocumentParser()
        self.chunker = SemanticChunker(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        self.embedding_service: Optional[EmbeddingService] = None
        self.es_storage: Optional[ElasticsearchStorageService] = None
        self.neo4j_storage: Optional[Neo4jStorageService] = None
        self.entity_extractor: Optional[EntityExtractionService] = None

        self._enable_neo4j = enable_neo4j
        self._enable_entity_extraction = enable_entity_extraction

        logger.info(
            "DocumentProcessingPipeline initialized: "
            f"neo4j={enable_neo4j}, entity_extraction={enable_entity_extraction}"
        )

    def _ensure_services(self) -> None:
        """서비스 지연 초기화"""
        if self.embedding_service is None:
            self.embedding_service = get_embedding_service()

        if self.es_storage is None:
            self.es_storage = get_es_storage_service()

        if self._enable_neo4j and self.neo4j_storage is None:
            self.neo4j_storage = get_neo4j_storage_service()

        if self._enable_entity_extraction and self.entity_extractor is None:
            self.entity_extractor = get_entity_extraction_service()

    async def process_document(
        self,
        document_id: UUID,
    ) -> ProcessingResult:
        """
        단일 문서 처리

        Args:
            document_id: 문서 UUID

        Returns:
            ProcessingResult 객체
        """
        start_time = time.monotonic()
        doc_id_str = str(document_id)

        logger.info(f"Processing document: {document_id}")

        try:
            # 서비스 초기화
            self._ensure_services()

            # 문서 조회
            document = await self.repository.get_document(document_id)
            if document is None:
                return ProcessingResult(
                    document_id=doc_id_str,
                    success=False,
                    status=ProcessingStatus.FAILED,
                    error_message=f"문서를 찾을 수 없습니다: {document_id}",
                )

            storage_path = document.get("storage_path")
            if not storage_path:
                return ProcessingResult(
                    document_id=doc_id_str,
                    success=False,
                    status=ProcessingStatus.FAILED,
                    error_message="스토리지 경로가 없습니다",
                )

            # 상태 업데이트: processing
            await self.repository.update_document_status(
                document_id=document_id,
                status=ProcessingStatus.PROCESSING,
                progress_percent=5,
            )

            # 1. 파일 다운로드
            await self.repository.update_document_status(
                document_id=document_id,
                status=ProcessingStatus.PARSING,
                progress_percent=10,
            )

            file_data = await FileStorage.download_file(storage_path)

            # 임시 파일로 저장 (파서가 파일 경로 필요)
            filename = document.get("filename", "document")
            with tempfile.NamedTemporaryFile(
                suffix=Path(filename).suffix, delete=False
            ) as tmp_file:
                tmp_file.write(file_data)
                tmp_path = tmp_file.name

            try:
                # 2. 텍스트 추출
                parse_result = self.parser.parse(tmp_path)

                if not parse_result.success:
                    return await self._handle_failure(
                        document_id=document_id,
                        error_message=f"문서 파싱 실패: {parse_result.message}",
                        start_time=start_time,
                    )

                parsed_doc = parse_result.document
                content = parsed_doc.content

                if not content or not content.strip():
                    return await self._handle_failure(
                        document_id=document_id,
                        error_message="문서에서 텍스트를 추출할 수 없습니다",
                        start_time=start_time,
                    )

                logger.info(
                    f"Document parsed: {document_id}, "
                    f"content_length={len(content)}, "
                    f"sections={len(parsed_doc.sections)}"
                )

                # 3. 청킹
                await self.repository.update_document_status(
                    document_id=document_id,
                    status=ProcessingStatus.CHUNKING,
                    progress_percent=30,
                )

                chunk_result = self.chunker.chunk_document(parsed_doc)
                chunks = chunk_result.chunks

                if not chunks:
                    return await self._handle_failure(
                        document_id=document_id,
                        error_message="청크를 생성할 수 없습니다",
                        start_time=start_time,
                    )

                logger.info(
                    f"Document chunked: {document_id}, "
                    f"chunks={len(chunks)}, "
                    f"avg_tokens={chunk_result.avg_token_count:.1f}"
                )

                # 4. 임베딩 생성
                await self.repository.update_document_status(
                    document_id=document_id,
                    status=ProcessingStatus.EMBEDDING,
                    progress_percent=50,
                )

                chunk_texts = [c.content for c in chunks]
                chunk_ids = [c.id for c in chunks]

                embeddings = await self.embedding_service.aembed_batch(chunk_texts)

                logger.info(
                    f"Embeddings generated: {document_id}, count={len(embeddings)}"
                )

                # 5. Elasticsearch 저장
                await self.repository.update_document_status(
                    document_id=document_id,
                    status=ProcessingStatus.STORING,
                    progress_percent=70,
                )

                # 문서 메타데이터
                doc_metadata = {
                    "title": document.get("filename", ""),
                    "document_type": document.get("format", {}).value
                    if hasattr(document.get("format", {}), "value")
                    else str(document.get("format", "")),
                    "project_name": "",
                }

                # 청크 데이터 준비
                es_chunks = []
                for i, chunk in enumerate(chunks):
                    es_chunk = {
                        "chunk_id": chunk.id,
                        "document_id": doc_id_str,
                        "content": chunk.content,
                        "dense_vector": embeddings[i],
                        "chunk_index": chunk.chunk_index,
                        "token_count": chunk.token_count,
                        "heading": chunk.heading or "",
                        "metadata": doc_metadata,
                        "total_chunks": len(chunks),
                    }
                    es_chunks.append(es_chunk)

                es_result = await self.es_storage.index_chunks(es_chunks)

                logger.info(
                    f"Elasticsearch indexed: {document_id}, "
                    f"indexed={es_result.get('indexed', 0)}, "
                    f"errors={es_result.get('errors', 0)}"
                )

                # 6. 엔티티/관계 추출 및 Neo4j 저장 (옵션)
                entity_count = 0
                relationship_count = 0

                if self._enable_entity_extraction and self._enable_neo4j:
                    await self.repository.update_document_status(
                        document_id=document_id,
                        status=ProcessingStatus.EXTRACTING,
                        progress_percent=85,
                    )

                    try:
                        extraction_result = await self.entity_extractor.extract_full(
                            text=content,
                            enable_gleaning=True,
                        )

                        entities = extraction_result.entities
                        relationships = extraction_result.relationships

                        entity_count = len(entities)
                        relationship_count = len(relationships)

                        logger.info(
                            f"Entities extracted: {document_id}, "
                            f"entities={entity_count}, "
                            f"relationships={relationship_count}"
                        )

                        # Neo4j 저장
                        if self.neo4j_storage:
                            neo4j_result = await self.neo4j_storage.save_document_graph(
                                document_id=doc_id_str,
                                title=document.get("filename", ""),
                                entities=entities,
                                relationships=relationships,
                                metadata=doc_metadata,
                            )

                            # 청크도 Neo4j에 저장
                            await self.neo4j_storage.save_chunks(
                                knowledge_id=doc_id_str,
                                chunks=es_chunks,
                            )

                            logger.info(
                                f"Neo4j saved: {document_id}, "
                                f"knowledge={neo4j_result.get('knowledge', 0)}, "
                                f"entities={neo4j_result.get('entities', 0)}, "
                                f"relationships={neo4j_result.get('relationships', 0)}"
                            )

                    except Exception as e:
                        # 엔티티 추출 실패는 경고만 하고 진행
                        logger.warning(
                            f"Entity extraction failed for {document_id}: {e}"
                        )

                # 7. 완료 상태 업데이트
                processing_time_ms = (time.monotonic() - start_time) * 1000

                await self.repository.update_document_status(
                    document_id=document_id,
                    status=ProcessingStatus.COMPLETED,
                    progress_percent=100,
                    metadata={
                        "chunk_count": len(chunks),
                        "entity_count": entity_count,
                        "relationship_count": relationship_count,
                        "processing_time_ms": processing_time_ms,
                    },
                )

                logger.info(
                    f"Document processing completed: {document_id}, "
                    f"chunks={len(chunks)}, "
                    f"entities={entity_count}, "
                    f"relationships={relationship_count}, "
                    f"time={processing_time_ms:.1f}ms"
                )

                return ProcessingResult(
                    document_id=doc_id_str,
                    success=True,
                    status=ProcessingStatus.COMPLETED,
                    chunk_count=len(chunks),
                    entity_count=entity_count,
                    relationship_count=relationship_count,
                    processing_time_ms=processing_time_ms,
                )

            finally:
                # 임시 파일 삭제
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

        except Exception as e:
            logger.exception(f"Document processing failed: {document_id}")
            return await self._handle_failure(
                document_id=document_id,
                error_message=str(e),
                start_time=start_time,
            )

    async def _handle_failure(
        self,
        document_id: UUID,
        error_message: str,
        start_time: float,
    ) -> ProcessingResult:
        """
        처리 실패 핸들링

        Args:
            document_id: 문서 UUID
            error_message: 에러 메시지
            start_time: 시작 시간

        Returns:
            ProcessingResult (실패)
        """
        processing_time_ms = (time.monotonic() - start_time) * 1000

        await self.repository.update_document_status(
            document_id=document_id,
            status=ProcessingStatus.FAILED,
            progress_percent=0,
            error_message=error_message,
        )

        logger.error(f"Document processing failed: {document_id} - {error_message}")

        return ProcessingResult(
            document_id=str(document_id),
            success=False,
            status=ProcessingStatus.FAILED,
            processing_time_ms=processing_time_ms,
            error_message=error_message,
        )

    async def process_pending_documents(
        self,
        batch_size: int = 5,
    ) -> List[ProcessingResult]:
        """
        대기 중인 문서 일괄 처리

        Args:
            batch_size: 한 번에 처리할 문서 수

        Returns:
            ProcessingResult 리스트
        """
        # uploaded 또는 queued 상태의 문서 조회
        pending_docs = await self.repository.get_documents_by_status(
            status=ProcessingStatus.QUEUED,
            limit=batch_size,
        )

        # uploaded 상태도 조회
        uploaded_docs = await self.repository.get_documents_by_status(
            status=ProcessingStatus.UPLOADED,
            limit=batch_size - len(pending_docs),
        )

        all_pending = pending_docs + uploaded_docs

        if not all_pending:
            logger.debug("No pending documents to process")
            return []

        logger.info(f"Processing {len(all_pending)} pending documents")

        results = []
        for doc in all_pending:
            doc_id = doc.get("document_id")
            if doc_id:
                result = await self.process_document(doc_id)
                results.append(result)

        return results

    async def close(self) -> None:
        """리소스 정리"""
        if self.es_storage:
            await self.es_storage.close()

        if self.neo4j_storage:
            await self.neo4j_storage.close()

        logger.info("DocumentProcessingPipeline closed")


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------

_pipeline: Optional[DocumentProcessingPipeline] = None


def get_document_processing_pipeline(
    document_store: Optional[Dict[UUID, Dict[str, Any]]] = None,
    **kwargs: Any,
) -> DocumentProcessingPipeline:
    """
    DocumentProcessingPipeline 싱글톤 팩토리

    Args:
        document_store: In-memory 문서 저장소 (테스트용)
        **kwargs: 추가 설정

    Returns:
        DocumentProcessingPipeline 인스턴스
    """
    global _pipeline
    if _pipeline is None:
        _pipeline = DocumentProcessingPipeline(
            document_store=document_store,
            **kwargs,
        )
    return _pipeline


def reset_pipeline() -> None:
    """싱글톤 인스턴스 초기화 (테스트용)"""
    global _pipeline
    _pipeline = None
