"""
Document Processing Pipeline 단위 테스트

문서 처리 파이프라인의 각 단계를 테스트합니다.
- ProcessingStatus: 상태 상수 검증
- ProcessingResult: 결과 dataclass 검증
- DocumentRepository: In-memory / PostgreSQL 저장소
- FileStorage: MinIO / 로컬 파일 다운로드
- DocumentProcessingPipeline: 전체 파이프라인 처리

Coverage Target: 80%+
"""

import asyncio
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

# 환경변수 설정 (임포트 전에 설정)
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("ELASTICSEARCH_HOST", "localhost")
os.environ.setdefault("ELASTICSEARCH_PORT", "9200")
os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("MINIO_ENDPOINT", "localhost:9000")
os.environ.setdefault("MINIO_ACCESS_KEY", "testkey")
os.environ.setdefault("MINIO_SECRET_KEY", "testsecret")

from app.models.document import DocumentFormat, DocumentStatus
from app.services.document_processing_pipeline import (
    DocumentProcessingPipeline,
    DocumentRepository,
    FileStorage,
    ProcessingResult,
    ProcessingStatus,
    get_document_processing_pipeline,
    reset_pipeline,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def document_store() -> Dict[UUID, Dict[str, Any]]:
    """테스트용 In-memory 문서 저장소"""
    return {}


@pytest.fixture(autouse=True)
def mock_notify_status():
    """Status callback을 모킹하여 네트워크 타임아웃 방지 (각 10초 × 9회 = 90초 절약)"""
    with patch(
        "app.services.document_processing_pipeline.notify_status",
        new_callable=AsyncMock,
        return_value=True,
    ):
        yield


@pytest.fixture
def sample_markdown_content() -> str:
    """테스트용 Markdown 문서 내용 (각 섹션 50+ 토큰, ChunkQualityGate 통과)"""
    return """# Test Document for Processing Pipeline

## Introduction

This is a comprehensive test document designed for validating the document processing pipeline.
The pipeline includes multiple stages such as parsing, chunking, embedding generation, and entity extraction.
Each stage must handle various document formats and produce high-quality output for downstream consumers.
The document contains enough content to pass the ChunkQualityGate minimum token count threshold.
Quality filtering ensures that only meaningful and semantically rich chunks are indexed into the knowledge base.
This introduction section provides an overview of the entire document processing workflow and its requirements.

## Section 1: Machine Learning Overview

Machine learning and artificial intelligence are key technologies driving modern software development.
Supervised learning algorithms such as random forests, gradient boosting, and neural networks are widely used
for classification and regression tasks in production environments across many industries worldwide.
Unsupervised learning techniques including clustering, dimensionality reduction, and anomaly detection
help discover hidden patterns in large datasets without requiring labeled training examples.
Deep learning architectures like transformers have revolutionized natural language processing and computer vision,
enabling applications such as machine translation, text summarization, and image recognition at scale.
Reinforcement learning enables agents to learn optimal policies through trial and error interaction with environments.

## Section 2: Knowledge Graph Technologies

Knowledge graphs help represent relationships between entities in a structured and queryable format.
Graph databases like Neo4j provide efficient traversal of complex relationships between millions of nodes
and edges, making them ideal for recommendation engines, fraud detection, and knowledge management systems.
Entity extraction using natural language processing techniques identifies key concepts, people, organizations,
and locations from unstructured text documents and maps them to nodes within the knowledge graph structure.
Relationship extraction determines how entities are connected, creating edges that capture semantic meaning.
Graph neural networks combine the power of deep learning with graph-structured data for advanced reasoning.
Knowledge graph embeddings enable similarity search and link prediction for discovering new connections.

## Conclusion

This concludes the test document which covers machine learning fundamentals and knowledge graph technologies.
The content has been specifically designed to ensure each section exceeds the minimum token count threshold
required by the ChunkQualityGate filter, which validates that chunks contain sufficient semantic information
for meaningful embedding generation and retrieval operations in the hybrid RAG knowledge search system.
Each section contains detailed technical content that represents realistic document processing scenarios.
The pipeline should successfully parse, chunk, embed, and extract entities from this test document.
"""


@pytest.fixture
def sample_document(
    document_store: Dict[UUID, Dict[str, Any]],
    sample_markdown_content: str,
) -> Dict[str, Any]:
    """테스트용 문서 레코드"""
    doc_id = uuid4()

    # 임시 파일 생성
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".md",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write(sample_markdown_content)
        temp_path = f.name

    doc_record = {
        "document_id": doc_id,
        "filename": "test_document.md",
        "format": DocumentFormat.PDF,
        "size_bytes": len(sample_markdown_content),
        "status": DocumentStatus.QUEUED,
        "progress_percent": 0,
        "error_message": None,
        "storage_path": temp_path,
        "metadata": {"title": "Test Document"},
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    document_store[doc_id] = doc_record
    return doc_record


@pytest.fixture
def uploaded_document(
    document_store: Dict[UUID, Dict[str, Any]],
    sample_markdown_content: str,
) -> Dict[str, Any]:
    """uploaded 상태의 테스트 문서"""
    doc_id = uuid4()

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".md",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write(sample_markdown_content)
        temp_path = f.name

    doc_record = {
        "document_id": doc_id,
        "filename": "uploaded_doc.md",
        "format": DocumentFormat.PDF,
        "size_bytes": len(sample_markdown_content),
        "status": ProcessingStatus.UPLOADED,  # uploaded 상태
        "progress_percent": 0,
        "storage_path": temp_path,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    document_store[doc_id] = doc_record
    return doc_record


# ---------------------------------------------------------------------------
# ProcessingStatus Tests
# ---------------------------------------------------------------------------


class TestProcessingStatus:
    """ProcessingStatus 상수 테스트"""

    def test_status_constants(self):
        """모든 상태 상수가 정의되어 있는지 확인"""
        assert ProcessingStatus.UPLOADED == "uploaded"
        assert ProcessingStatus.QUEUED == "queued"
        assert ProcessingStatus.PROCESSING == "processing"
        assert ProcessingStatus.PARSING == "parsing"
        assert ProcessingStatus.CHUNKING == "chunking"
        assert ProcessingStatus.EMBEDDING == "embedding"
        assert ProcessingStatus.STORING == "storing"
        assert ProcessingStatus.EXTRACTING == "extracting"
        assert ProcessingStatus.COMPLETED == "completed"
        assert ProcessingStatus.FAILED == "failed"

    def test_status_values_are_strings(self):
        """모든 상태 값이 문자열인지 확인"""
        statuses = [
            ProcessingStatus.UPLOADED,
            ProcessingStatus.QUEUED,
            ProcessingStatus.PROCESSING,
            ProcessingStatus.PARSING,
            ProcessingStatus.CHUNKING,
            ProcessingStatus.EMBEDDING,
            ProcessingStatus.STORING,
            ProcessingStatus.EXTRACTING,
            ProcessingStatus.COMPLETED,
            ProcessingStatus.FAILED,
        ]
        for status in statuses:
            assert isinstance(status, str)


# ---------------------------------------------------------------------------
# ProcessingResult Tests
# ---------------------------------------------------------------------------


class TestProcessingResult:
    """ProcessingResult 모델 테스트"""

    def test_success_result(self):
        """성공 결과 생성 테스트"""
        result = ProcessingResult(
            document_id="test-123",
            success=True,
            status=ProcessingStatus.COMPLETED,
            chunk_count=10,
            entity_count=5,
            relationship_count=3,
            processing_time_ms=1234.56,
        )

        assert result.success is True
        assert result.document_id == "test-123"
        assert result.status == ProcessingStatus.COMPLETED
        assert result.chunk_count == 10
        assert result.entity_count == 5
        assert result.relationship_count == 3
        assert result.processing_time_ms == 1234.56
        assert result.error_message is None

    def test_failure_result(self):
        """실패 결과 생성 테스트"""
        result = ProcessingResult(
            document_id="test-456",
            success=False,
            status=ProcessingStatus.FAILED,
            error_message="Processing failed",
            processing_time_ms=100.0,
        )

        assert result.success is False
        assert result.error_message == "Processing failed"
        assert result.chunk_count == 0
        assert result.entity_count == 0
        assert result.relationship_count == 0

    def test_default_values(self):
        """기본값 테스트"""
        result = ProcessingResult(
            document_id="test-789",
            success=True,
            status=ProcessingStatus.COMPLETED,
        )

        assert result.chunk_count == 0
        assert result.entity_count == 0
        assert result.relationship_count == 0
        assert result.processing_time_ms == 0.0
        assert result.error_message is None


# ---------------------------------------------------------------------------
# DocumentRepository Tests
# ---------------------------------------------------------------------------


class TestDocumentRepository:
    """DocumentRepository 테스트"""

    @pytest.mark.asyncio
    async def test_initialization_memory_mode(self, document_store):
        """In-memory 모드 초기화 테스트"""
        repo = DocumentRepository(document_store)
        assert repo._use_memory is True
        assert repo._store is document_store

    @pytest.mark.asyncio
    async def test_initialization_postgres_mode(self):
        """PostgreSQL 모드 초기화 테스트 (document_store=None)"""
        repo = DocumentRepository(None)
        assert repo._use_memory is False
        assert repo._store is None

    @pytest.mark.asyncio
    async def test_get_documents_by_status(
        self,
        document_store: Dict[UUID, Dict[str, Any]],
        sample_document: Dict[str, Any],
    ):
        """상태별 문서 조회 테스트"""
        repo = DocumentRepository(document_store)

        # queued 상태 문서 조회
        docs = await repo.get_documents_by_status("queued", limit=10)
        assert len(docs) == 1
        assert docs[0]["document_id"] == sample_document["document_id"]

        # 없는 상태 조회
        docs = await repo.get_documents_by_status("completed", limit=10)
        assert len(docs) == 0

    @pytest.mark.asyncio
    async def test_get_documents_by_status_with_enum(
        self,
        document_store: Dict[UUID, Dict[str, Any]],
        sample_document: Dict[str, Any],
    ):
        """Enum 상태값으로 문서 조회 테스트"""
        # 상태를 Enum으로 설정
        doc_id = sample_document["document_id"]
        document_store[doc_id]["status"] = DocumentStatus.QUEUED

        repo = DocumentRepository(document_store)

        # queued 상태 문서 조회 (Enum value를 처리해야 함)
        docs = await repo.get_documents_by_status("queued", limit=10)
        assert len(docs) == 1

    @pytest.mark.asyncio
    async def test_get_documents_by_status_limit(
        self,
        document_store: Dict[UUID, Dict[str, Any]],
        sample_markdown_content: str,
    ):
        """limit 제한 테스트"""
        # 여러 문서 추가
        for i in range(5):
            doc_id = uuid4()
            document_store[doc_id] = {
                "document_id": doc_id,
                "status": "queued",
            }

        repo = DocumentRepository(document_store)
        docs = await repo.get_documents_by_status("queued", limit=3)
        assert len(docs) == 3

    @pytest.mark.asyncio
    async def test_update_document_status(
        self,
        document_store: Dict[UUID, Dict[str, Any]],
        sample_document: Dict[str, Any],
    ):
        """문서 상태 업데이트 테스트"""
        repo = DocumentRepository(document_store)
        doc_id = sample_document["document_id"]

        # 상태 업데이트
        success = await repo.update_document_status(
            document_id=doc_id,
            status=ProcessingStatus.PROCESSING,
            progress_percent=50,
        )

        assert success is True
        assert document_store[doc_id]["status"] == ProcessingStatus.PROCESSING
        assert document_store[doc_id]["progress_percent"] == 50
        assert "updated_at" in document_store[doc_id]

    @pytest.mark.asyncio
    async def test_update_document_status_with_error(
        self,
        document_store: Dict[UUID, Dict[str, Any]],
        sample_document: Dict[str, Any],
    ):
        """에러 메시지 포함 상태 업데이트 테스트"""
        repo = DocumentRepository(document_store)
        doc_id = sample_document["document_id"]

        success = await repo.update_document_status(
            document_id=doc_id,
            status=ProcessingStatus.FAILED,
            progress_percent=0,
            error_message="Test error message",
        )

        assert success is True
        assert document_store[doc_id]["status"] == ProcessingStatus.FAILED
        assert document_store[doc_id]["error_message"] == "Test error message"

    @pytest.mark.asyncio
    async def test_update_document_status_with_metadata(
        self,
        document_store: Dict[UUID, Dict[str, Any]],
        sample_document: Dict[str, Any],
    ):
        """메타데이터 포함 상태 업데이트 테스트"""
        repo = DocumentRepository(document_store)
        doc_id = sample_document["document_id"]

        # 기존 메타데이터가 없는 경우
        success = await repo.update_document_status(
            document_id=doc_id,
            status=ProcessingStatus.COMPLETED,
            progress_percent=100,
            metadata={
                "chunk_count": 10,
                "entity_count": 5,
            },
        )

        assert success is True
        assert document_store[doc_id]["processing_metadata"]["chunk_count"] == 10
        assert document_store[doc_id]["processing_metadata"]["entity_count"] == 5

    @pytest.mark.asyncio
    async def test_update_document_status_merge_metadata(
        self,
        document_store: Dict[UUID, Dict[str, Any]],
        sample_document: Dict[str, Any],
    ):
        """기존 메타데이터와 병합 테스트"""
        repo = DocumentRepository(document_store)
        doc_id = sample_document["document_id"]

        # 기존 메타데이터 설정
        document_store[doc_id]["processing_metadata"] = {"existing": "value"}

        success = await repo.update_document_status(
            document_id=doc_id,
            status=ProcessingStatus.COMPLETED,
            metadata={"new_key": "new_value"},
        )

        assert success is True
        meta = document_store[doc_id]["processing_metadata"]
        assert meta["existing"] == "value"
        assert meta["new_key"] == "new_value"

    @pytest.mark.asyncio
    async def test_update_nonexistent_document(
        self,
        document_store: Dict[UUID, Dict[str, Any]],
    ):
        """존재하지 않는 문서 업데이트 테스트"""
        repo = DocumentRepository(document_store)

        success = await repo.update_document_status(
            document_id=uuid4(),
            status=ProcessingStatus.COMPLETED,
        )

        assert success is False

    @pytest.mark.asyncio
    async def test_get_document(
        self,
        document_store: Dict[UUID, Dict[str, Any]],
        sample_document: Dict[str, Any],
    ):
        """문서 조회 테스트"""
        repo = DocumentRepository(document_store)

        # 존재하는 문서
        doc = await repo.get_document(sample_document["document_id"])
        assert doc is not None
        assert doc["filename"] == "test_document.md"

        # 존재하지 않는 문서
        doc = await repo.get_document(uuid4())
        assert doc is None

    @pytest.mark.asyncio
    async def test_create_document_memory(
        self,
        document_store: Dict[UUID, Dict[str, Any]],
    ):
        """In-memory 문서 생성 테스트"""
        repo = DocumentRepository(document_store)
        doc_id = uuid4()

        result = await repo.create_document(
            document_id=doc_id,
            filename="new_document.pdf",
            format_type="pdf",
            size_bytes=12345,
            storage_path="/path/to/file.pdf",
            metadata={"title": "New Document", "author": "Test"},
        )

        assert result is not None
        assert result["document_id"] == doc_id
        assert result["filename"] == "new_document.pdf"
        assert result["status"] == ProcessingStatus.UPLOADED
        assert doc_id in document_store

    @pytest.mark.asyncio
    async def test_create_document_without_metadata(
        self,
        document_store: Dict[UUID, Dict[str, Any]],
    ):
        """메타데이터 없이 문서 생성 테스트"""
        repo = DocumentRepository(document_store)
        doc_id = uuid4()

        result = await repo.create_document(
            document_id=doc_id,
            filename="simple.txt",
            format_type="txt",
            size_bytes=100,
            storage_path="/path/to/simple.txt",
        )

        assert result is not None
        assert result["document_id"] == doc_id

    @pytest.mark.asyncio
    async def test_get_documents_by_status_postgres_mode(self):
        """PostgreSQL 모드에서 상태별 문서 조회 (Mock)"""
        repo = DocumentRepository(None)

        # Mock SQLAlchemy and database
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = {"document_id": "test-123", "status": "queued"}
        mock_result.scalars.return_value.all.return_value = [mock_doc]
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.document_processing_pipeline.DocumentRepository") as mock_repo_class:
            # 직접 PostgreSQL 경로를 테스트하기 위해 import mock
            with patch.dict(sys.modules, {"sqlalchemy": MagicMock(), "app.core.database": MagicMock()}):
                # DB import 실패 시 빈 리스트 반환 확인
                docs = await repo.get_documents_by_status("queued", limit=10)
                assert docs == []  # Import 실패로 빈 리스트

    @pytest.mark.asyncio
    async def test_update_document_status_postgres_mode(self):
        """PostgreSQL 모드에서 문서 상태 업데이트 (Mock)"""
        repo = DocumentRepository(None)

        # DB import 실패 시 False 반환 확인
        result = await repo.update_document_status(
            document_id=uuid4(),
            status=ProcessingStatus.COMPLETED,
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_get_document_postgres_mode(self):
        """PostgreSQL 모드에서 문서 조회 (Mock)"""
        repo = DocumentRepository(None)

        # DB import 실패 시 None 반환 확인
        doc = await repo.get_document(uuid4())
        assert doc is None

    @pytest.mark.asyncio
    async def test_create_document_postgres_mode(self):
        """PostgreSQL 모드에서 문서 생성 (Mock)"""
        repo = DocumentRepository(None)

        # DB import 실패 시 None 반환 확인
        result = await repo.create_document(
            document_id=uuid4(),
            filename="test.pdf",
            format_type="pdf",
            size_bytes=1000,
            storage_path="/path/to/test.pdf",
        )
        assert result is None


# ---------------------------------------------------------------------------
# FileStorage Tests
# ---------------------------------------------------------------------------


class TestFileStorage:
    """FileStorage 테스트"""

    @pytest.mark.asyncio
    async def test_download_local_file(self, sample_markdown_content: str):
        """로컬 파일 다운로드 테스트"""
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".md",
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write(sample_markdown_content)
            temp_path = f.name

        try:
            data = await FileStorage.download_file(temp_path)
            assert data.decode("utf-8") == sample_markdown_content
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_download_nonexistent_file(self):
        """존재하지 않는 파일 다운로드 테스트"""
        with pytest.raises(FileNotFoundError) as exc_info:
            await FileStorage.download_file("/nonexistent/path/file.txt")
        assert "찾을 수 없습니다" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_download_minio_invalid_path(self):
        """잘못된 MinIO 경로 테스트"""
        with pytest.raises(ValueError) as exc_info:
            await FileStorage._download_from_minio("minio://invalid_path")
        assert "Invalid MinIO path" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_download_minio_with_valid_path(self):
        """MinIO 다운로드 테스트 (Mock)"""
        # Mock the minio module
        mock_minio_class = MagicMock()
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.read.return_value = b"test content"
        mock_client.get_object.return_value = mock_response
        mock_minio_class.return_value = mock_client

        # Create a mock minio module
        mock_minio_module = MagicMock()
        mock_minio_module.Minio = mock_minio_class

        with patch.dict(sys.modules, {"minio": mock_minio_module}):
            data = await FileStorage._download_from_minio("minio://bucket/object.txt")
            assert data == b"test content"
            mock_response.close.assert_called_once()
            mock_response.release_conn.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_minio_failure(self):
        """MinIO 다운로드 실패 테스트"""
        mock_minio_class = MagicMock()
        mock_client = MagicMock()
        mock_client.get_object.side_effect = Exception("Connection refused")
        mock_minio_class.return_value = mock_client

        mock_minio_module = MagicMock()
        mock_minio_module.Minio = mock_minio_class

        with patch.dict(sys.modules, {"minio": mock_minio_module}):
            with pytest.raises(IOError) as exc_info:
                await FileStorage._download_from_minio("minio://bucket/object.txt")
            assert "MinIO 파일 다운로드 실패" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_download_local_file_read_error(self):
        """로컬 파일 읽기 에러 테스트"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name

        try:
            with patch("pathlib.Path.read_bytes") as mock_read:
                mock_read.side_effect = PermissionError("Permission denied")
                with pytest.raises(IOError) as exc_info:
                    await FileStorage._download_from_local(temp_path)
                assert "로컬 파일 읽기 실패" in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_download_minio_path_routing(self):
        """MinIO 경로 라우팅 테스트"""
        # minio:// 경로가 MinIO 다운로드로 라우팅되는지 확인
        with patch.object(FileStorage, "_download_from_minio") as mock_minio:
            mock_minio.return_value = b"minio content"
            data = await FileStorage.download_file("minio://bucket/path/file.txt")
            mock_minio.assert_called_once_with("minio://bucket/path/file.txt")
            assert data == b"minio content"


# ---------------------------------------------------------------------------
# DocumentProcessingPipeline Tests
# ---------------------------------------------------------------------------


class TestDocumentProcessingPipeline:
    """DocumentProcessingPipeline 테스트"""

    def test_initialization_default(self, document_store: Dict[UUID, Dict[str, Any]]):
        """기본 초기화 테스트"""
        pipeline = DocumentProcessingPipeline(
            document_store=document_store,
        )
        assert pipeline._enable_neo4j is True
        assert pipeline._enable_entity_extraction is True
        assert pipeline.embedding_service is None  # Lazy loading
        assert pipeline.es_storage is None
        assert pipeline.neo4j_storage is None

    def test_initialization_disabled_features(self, document_store: Dict[UUID, Dict[str, Any]]):
        """기능 비활성화 초기화 테스트"""
        pipeline = DocumentProcessingPipeline(
            document_store=document_store,
            enable_neo4j=False,
            enable_entity_extraction=False,
        )
        assert pipeline._enable_neo4j is False
        assert pipeline._enable_entity_extraction is False

    @pytest.mark.asyncio
    async def test_process_document_not_found(
        self,
        document_store: Dict[UUID, Dict[str, Any]],
    ):
        """존재하지 않는 문서 처리 테스트"""
        pipeline = DocumentProcessingPipeline(
            document_store=document_store,
            enable_neo4j=False,
            enable_entity_extraction=False,
        )

        # _ensure_services 모킹하여 torch 임포트 방지
        with patch.object(pipeline, "_ensure_services"):
            result = await pipeline.process_document(uuid4())

            assert result.success is False
            assert result.status == ProcessingStatus.FAILED
            assert "찾을 수 없습니다" in result.error_message

    @pytest.mark.asyncio
    async def test_process_document_no_storage_path(
        self,
        document_store: Dict[UUID, Dict[str, Any]],
    ):
        """스토리지 경로 없는 문서 처리 테스트"""
        doc_id = uuid4()
        document_store[doc_id] = {
            "document_id": doc_id,
            "filename": "test.md",
            "status": DocumentStatus.QUEUED,
            "storage_path": None,
        }

        pipeline = DocumentProcessingPipeline(
            document_store=document_store,
            enable_neo4j=False,
            enable_entity_extraction=False,
        )

        # _ensure_services 모킹하여 torch 임포트 방지
        with patch.object(pipeline, "_ensure_services"):
            result = await pipeline.process_document(doc_id)

            assert result.success is False
            assert "스토리지 경로" in result.error_message

    @pytest.mark.asyncio
    async def test_process_document_empty_storage_path(
        self,
        document_store: Dict[UUID, Dict[str, Any]],
    ):
        """빈 스토리지 경로 처리 테스트"""
        doc_id = uuid4()
        document_store[doc_id] = {
            "document_id": doc_id,
            "filename": "test.md",
            "status": DocumentStatus.QUEUED,
            "storage_path": "",
        }

        pipeline = DocumentProcessingPipeline(
            document_store=document_store,
            enable_neo4j=False,
            enable_entity_extraction=False,
        )

        # _ensure_services 모킹하여 torch 임포트 방지
        with patch.object(pipeline, "_ensure_services"):
            result = await pipeline.process_document(doc_id)

            assert result.success is False
            assert "스토리지 경로" in result.error_message

    @pytest.mark.asyncio
    async def test_process_document_parsing_success(
        self,
        document_store: Dict[UUID, Dict[str, Any]],
        sample_document: Dict[str, Any],
    ):
        """문서 파싱 성공 테스트 (Mock 사용)"""
        pipeline = DocumentProcessingPipeline(
            document_store=document_store,
            enable_neo4j=False,
            enable_entity_extraction=False,
        )

        doc_id = sample_document["document_id"]

        # 서비스 Mock
        with patch.object(pipeline, "_ensure_services"):
            # EmbeddingService Mock
            mock_embedding = MagicMock()
            mock_embedding.aembed_batch = AsyncMock(
                side_effect=lambda texts, **kwargs: ([[0.1] * 1024 for _ in range(len(texts))], [{1: 0.5} for _ in range(len(texts))])
            )
            pipeline.embedding_service = mock_embedding

            # ES Storage Mock
            mock_es = MagicMock()
            mock_es.index_chunks = AsyncMock(
                return_value={"indexed": 4, "errors": 0}
            )
            pipeline.es_storage = mock_es

            result = await pipeline.process_document(doc_id)

            assert result.success is True
            assert result.status == ProcessingStatus.COMPLETED
            assert result.chunk_count > 0
            assert result.processing_time_ms > 0

            # 상태 업데이트 확인
            assert document_store[doc_id]["status"] == ProcessingStatus.COMPLETED
            assert document_store[doc_id]["progress_percent"] == 100

        # 정리
        try:
            os.unlink(sample_document["storage_path"])
        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_process_document_parsing_failure(
        self,
        document_store: Dict[UUID, Dict[str, Any]],
    ):
        """문서 파싱 실패 테스트"""
        doc_id = uuid4()

        # 빈 파일 생성
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".pdf",
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write("")  # 빈 파일
            temp_path = f.name

        document_store[doc_id] = {
            "document_id": doc_id,
            "filename": "empty.pdf",
            "format": DocumentFormat.PDF,
            "status": DocumentStatus.QUEUED,
            "storage_path": temp_path,
        }

        pipeline = DocumentProcessingPipeline(
            document_store=document_store,
            enable_neo4j=False,
            enable_entity_extraction=False,
        )

        with patch.object(pipeline, "_ensure_services"):
            # Parser Mock - 실패 반환
            mock_parse_result = MagicMock()
            mock_parse_result.success = False
            mock_parse_result.message = "Parsing failed"

            with patch.object(
                pipeline.parser, "parse", return_value=mock_parse_result
            ):
                result = await pipeline.process_document(doc_id)

                assert result.success is False
                assert "파싱 실패" in result.error_message

        try:
            os.unlink(temp_path)
        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_process_document_empty_content(
        self,
        document_store: Dict[UUID, Dict[str, Any]],
    ):
        """빈 내용 추출 테스트"""
        doc_id = uuid4()

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".md",
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write("   ")  # 공백만
            temp_path = f.name

        document_store[doc_id] = {
            "document_id": doc_id,
            "filename": "whitespace.md",
            "format": DocumentFormat.PDF,
            "status": DocumentStatus.QUEUED,
            "storage_path": temp_path,
        }

        pipeline = DocumentProcessingPipeline(
            document_store=document_store,
            enable_neo4j=False,
            enable_entity_extraction=False,
        )

        with patch.object(pipeline, "_ensure_services"):
            # Parser Mock - 성공하지만 빈 내용
            mock_doc = MagicMock()
            mock_doc.content = "   "
            mock_doc.sections = []

            mock_parse_result = MagicMock()
            mock_parse_result.success = True
            mock_parse_result.document = mock_doc

            with patch.object(
                pipeline.parser, "parse", return_value=mock_parse_result
            ):
                result = await pipeline.process_document(doc_id)

                assert result.success is False
                assert "텍스트를 추출할 수 없습니다" in result.error_message

        try:
            os.unlink(temp_path)
        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_process_document_empty_chunks(
        self,
        document_store: Dict[UUID, Dict[str, Any]],
    ):
        """청크 생성 실패 테스트"""
        doc_id = uuid4()

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".md",
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write("Short text")
            temp_path = f.name

        document_store[doc_id] = {
            "document_id": doc_id,
            "filename": "short.md",
            "format": DocumentFormat.PDF,
            "status": DocumentStatus.QUEUED,
            "storage_path": temp_path,
        }

        pipeline = DocumentProcessingPipeline(
            document_store=document_store,
            enable_neo4j=False,
            enable_entity_extraction=False,
        )

        with patch.object(pipeline, "_ensure_services"):
            # Chunker Mock - 빈 청크 반환
            mock_chunk_result = MagicMock()
            mock_chunk_result.chunks = []

            with patch.object(
                pipeline.chunker, "chunk_document", return_value=mock_chunk_result
            ):
                result = await pipeline.process_document(doc_id)

                assert result.success is False
                assert "청크를 생성할 수 없습니다" in result.error_message

        try:
            os.unlink(temp_path)
        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_process_document_with_entity_extraction(
        self,
        document_store: Dict[UUID, Dict[str, Any]],
        sample_document: Dict[str, Any],
    ):
        """엔티티 추출 포함 처리 테스트"""
        pipeline = DocumentProcessingPipeline(
            document_store=document_store,
            enable_neo4j=True,
            enable_entity_extraction=True,
        )

        doc_id = sample_document["document_id"]

        with patch.object(pipeline, "_ensure_services"):
            # EmbeddingService Mock
            mock_embedding = MagicMock()
            mock_embedding.aembed_batch = AsyncMock(
                side_effect=lambda texts, **kwargs: ([[0.1] * 1024 for _ in range(len(texts))], [{1: 0.5} for _ in range(len(texts))])
            )
            pipeline.embedding_service = mock_embedding

            # ES Storage Mock
            mock_es = MagicMock()
            mock_es.index_chunks = AsyncMock(
                return_value={"indexed": 4, "errors": 0}
            )
            pipeline.es_storage = mock_es

            # Entity Extractor Mock
            mock_extraction_result = MagicMock()
            mock_extraction_result.entities = [
                MagicMock(id="e1", name="Test Entity", type="Technology")
            ]
            mock_extraction_result.relationships = [
                MagicMock(source="e1", target="e2", type="USES")
            ]

            mock_extractor = MagicMock()
            mock_extractor.extract_full = AsyncMock(
                return_value=mock_extraction_result
            )
            pipeline.entity_extractor = mock_extractor

            # Neo4j Storage Mock
            mock_neo4j = MagicMock()
            mock_neo4j.save_document_graph = AsyncMock(
                return_value={"knowledge": 1, "entities": 1, "relationships": 1}
            )
            mock_neo4j.save_chunks = AsyncMock()
            pipeline.neo4j_storage = mock_neo4j

            result = await pipeline.process_document(doc_id)

            assert result.success is True
            assert result.entity_count == 1
            assert result.relationship_count == 1

        try:
            os.unlink(sample_document["storage_path"])
        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_process_document_entity_extraction_failure(
        self,
        document_store: Dict[UUID, Dict[str, Any]],
        sample_document: Dict[str, Any],
    ):
        """엔티티 추출 실패해도 처리 계속 테스트"""
        pipeline = DocumentProcessingPipeline(
            document_store=document_store,
            enable_neo4j=True,
            enable_entity_extraction=True,
        )

        doc_id = sample_document["document_id"]

        with patch.object(pipeline, "_ensure_services"):
            mock_embedding = MagicMock()
            mock_embedding.aembed_batch = AsyncMock(
                side_effect=lambda texts, **kwargs: ([[0.1] * 1024 for _ in range(len(texts))], [{1: 0.5} for _ in range(len(texts))])
            )
            pipeline.embedding_service = mock_embedding

            mock_es = MagicMock()
            mock_es.index_chunks = AsyncMock(
                return_value={"indexed": 4, "errors": 0}
            )
            pipeline.es_storage = mock_es

            # Entity Extractor Mock - 실패
            mock_extractor = MagicMock()
            mock_extractor.extract_full = AsyncMock(
                side_effect=Exception("Extraction failed")
            )
            pipeline.entity_extractor = mock_extractor

            result = await pipeline.process_document(doc_id)

            # 엔티티 추출 실패해도 전체는 성공
            assert result.success is True
            assert result.entity_count == 0
            assert result.relationship_count == 0

        try:
            os.unlink(sample_document["storage_path"])
        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_process_document_exception_handling(
        self,
        document_store: Dict[UUID, Dict[str, Any]],
        sample_document: Dict[str, Any],
    ):
        """예외 처리 테스트"""
        pipeline = DocumentProcessingPipeline(
            document_store=document_store,
            enable_neo4j=False,
            enable_entity_extraction=False,
        )

        doc_id = sample_document["document_id"]

        with patch.object(pipeline, "_ensure_services"):
            with patch.object(
                FileStorage, "download_file",
                side_effect=Exception("Unexpected error")
            ):
                result = await pipeline.process_document(doc_id)

                assert result.success is False
                assert "Unexpected error" in result.error_message

    @pytest.mark.asyncio
    async def test_handle_failure(
        self,
        document_store: Dict[UUID, Dict[str, Any]],
        sample_document: Dict[str, Any],
    ):
        """_handle_failure 메서드 테스트"""
        pipeline = DocumentProcessingPipeline(
            document_store=document_store,
            enable_neo4j=False,
        )

        doc_id = sample_document["document_id"]
        start_time = 0.0

        result = await pipeline._handle_failure(
            document_id=doc_id,
            error_message="Test error",
            start_time=start_time,
        )

        assert result.success is False
        assert result.status == ProcessingStatus.FAILED
        assert result.error_message == "Test error"
        assert result.processing_time_ms > 0

        # 저장소 상태 확인
        assert document_store[doc_id]["status"] == ProcessingStatus.FAILED

    @pytest.mark.asyncio
    async def test_process_pending_documents(
        self,
        document_store: Dict[UUID, Dict[str, Any]],
        sample_markdown_content: str,
    ):
        """대기 문서 일괄 처리 테스트"""
        # queued 상태 문서 3개 생성
        for i in range(3):
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".md",
                delete=False,
                encoding="utf-8",
            ) as f:
                f.write(sample_markdown_content)
                temp_path = f.name

            doc_id = uuid4()
            document_store[doc_id] = {
                "document_id": doc_id,
                "filename": f"test_{i}.md",
                "format": DocumentFormat.PDF,
                "status": DocumentStatus.QUEUED,
                "storage_path": temp_path,
                "created_at": datetime.now(timezone.utc),
            }

        pipeline = DocumentProcessingPipeline(
            document_store=document_store,
            enable_neo4j=False,
            enable_entity_extraction=False,
        )

        with patch.object(pipeline, "_ensure_services"):
            mock_embedding = MagicMock()
            mock_embedding.aembed_batch = AsyncMock(
                side_effect=lambda texts, **kwargs: ([[0.1] * 1024 for _ in range(len(texts))], [{1: 0.5} for _ in range(len(texts))])
            )
            pipeline.embedding_service = mock_embedding

            mock_es = MagicMock()
            mock_es.index_chunks = AsyncMock(
                return_value={"indexed": 5, "errors": 0}
            )
            pipeline.es_storage = mock_es

            # batch_size=2로 처리
            results = await pipeline.process_pending_documents(batch_size=2)

            # 최대 2개만 처리
            assert len(results) == 2

        # 정리
        for doc in document_store.values():
            try:
                os.unlink(doc.get("storage_path", ""))
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_process_pending_documents_with_uploaded(
        self,
        document_store: Dict[UUID, Dict[str, Any]],
        sample_markdown_content: str,
    ):
        """uploaded 상태 문서도 처리되는지 테스트"""
        # uploaded 상태 문서 1개 생성
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".md",
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write(sample_markdown_content)
            temp_path = f.name

        doc_id = uuid4()
        document_store[doc_id] = {
            "document_id": doc_id,
            "filename": "uploaded.md",
            "format": DocumentFormat.PDF,
            "status": ProcessingStatus.UPLOADED,  # uploaded 상태
            "storage_path": temp_path,
            "created_at": datetime.now(timezone.utc),
        }

        pipeline = DocumentProcessingPipeline(
            document_store=document_store,
            enable_neo4j=False,
            enable_entity_extraction=False,
        )

        with patch.object(pipeline, "_ensure_services"):
            mock_embedding = MagicMock()
            mock_embedding.aembed_batch = AsyncMock(
                side_effect=lambda texts, **kwargs: ([[0.1] * 1024 for _ in range(len(texts))], [{1: 0.5} for _ in range(len(texts))])
            )
            pipeline.embedding_service = mock_embedding

            mock_es = MagicMock()
            mock_es.index_chunks = AsyncMock(
                return_value={"indexed": 5, "errors": 0}
            )
            pipeline.es_storage = mock_es

            results = await pipeline.process_pending_documents(batch_size=5)

            assert len(results) == 1
            assert results[0].success is True

        try:
            os.unlink(temp_path)
        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_process_pending_documents_empty(
        self,
        document_store: Dict[UUID, Dict[str, Any]],
    ):
        """대기 문서 없을 때 테스트"""
        pipeline = DocumentProcessingPipeline(
            document_store=document_store,
            enable_neo4j=False,
        )

        results = await pipeline.process_pending_documents()
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_close(
        self,
        document_store: Dict[UUID, Dict[str, Any]],
    ):
        """리소스 정리 테스트"""
        pipeline = DocumentProcessingPipeline(
            document_store=document_store,
            enable_neo4j=True,
        )

        # Mock 서비스 설정
        mock_es = MagicMock()
        mock_es.close = AsyncMock()
        pipeline.es_storage = mock_es

        mock_neo4j = MagicMock()
        mock_neo4j.close = AsyncMock()
        pipeline.neo4j_storage = mock_neo4j

        await pipeline.close()

        mock_es.close.assert_called_once()
        mock_neo4j.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_without_services(
        self,
        document_store: Dict[UUID, Dict[str, Any]],
    ):
        """서비스 없이 close 호출 테스트"""
        pipeline = DocumentProcessingPipeline(
            document_store=document_store,
            enable_neo4j=False,
        )

        # 서비스가 None인 상태에서 close 호출
        await pipeline.close()  # 에러 없이 완료되어야 함

    def test_ensure_services_with_mocks(
        self,
        document_store: Dict[UUID, Dict[str, Any]],
    ):
        """_ensure_services 테스트 (Mock 사용)"""
        pipeline = DocumentProcessingPipeline(
            document_store=document_store,
            enable_neo4j=True,
            enable_entity_extraction=True,
        )

        # Mock 서비스 팩토리 함수들
        mock_embedding = MagicMock()
        mock_es = MagicMock()
        mock_neo4j = MagicMock()
        mock_extractor = MagicMock()

        with patch(
            "app.services.document_processing_pipeline.get_embedding_service",
            return_value=mock_embedding,
        ), patch(
            "app.services.document_processing_pipeline.get_es_storage_service",
            return_value=mock_es,
        ), patch(
            "app.services.document_processing_pipeline.get_neo4j_storage_service",
            return_value=mock_neo4j,
        ), patch(
            "app.services.document_processing_pipeline.get_entity_extraction_service",
            return_value=mock_extractor,
        ):
            pipeline._ensure_services()

            assert pipeline.embedding_service is mock_embedding
            assert pipeline.es_storage is mock_es
            assert pipeline.neo4j_storage is mock_neo4j
            assert pipeline.entity_extractor is mock_extractor

    def test_ensure_services_neo4j_disabled(
        self,
        document_store: Dict[UUID, Dict[str, Any]],
    ):
        """Neo4j 비활성화 시 _ensure_services 테스트"""
        pipeline = DocumentProcessingPipeline(
            document_store=document_store,
            enable_neo4j=False,
            enable_entity_extraction=False,
        )

        mock_embedding = MagicMock()
        mock_es = MagicMock()

        with patch(
            "app.services.document_processing_pipeline.get_embedding_service",
            return_value=mock_embedding,
        ), patch(
            "app.services.document_processing_pipeline.get_es_storage_service",
            return_value=mock_es,
        ):
            pipeline._ensure_services()

            assert pipeline.embedding_service is mock_embedding
            assert pipeline.es_storage is mock_es
            assert pipeline.neo4j_storage is None
            assert pipeline.entity_extractor is None


# ---------------------------------------------------------------------------
# Singleton Factory Tests
# ---------------------------------------------------------------------------


class TestSingletonFactory:
    """싱글톤 팩토리 테스트"""

    def test_get_document_processing_pipeline(self):
        """싱글톤 반환 테스트"""
        reset_pipeline()  # 초기화

        pipeline1 = get_document_processing_pipeline()
        pipeline2 = get_document_processing_pipeline()

        assert pipeline1 is pipeline2

        reset_pipeline()  # 정리

    def test_get_document_processing_pipeline_with_store(self):
        """커스텀 store로 싱글톤 생성 테스트"""
        reset_pipeline()

        store: Dict[UUID, Dict[str, Any]] = {}
        pipeline = get_document_processing_pipeline(document_store=store)

        assert pipeline.repository._use_memory is True

        reset_pipeline()

    def test_reset_pipeline(self):
        """reset_pipeline 테스트"""
        reset_pipeline()

        pipeline1 = get_document_processing_pipeline()
        reset_pipeline()
        pipeline2 = get_document_processing_pipeline()

        assert pipeline1 is not pipeline2

        reset_pipeline()


# ---------------------------------------------------------------------------
# Document Format Enum Handling Tests
# ---------------------------------------------------------------------------


class TestDocumentFormatHandling:
    """DocumentFormat Enum 처리 테스트"""

    @pytest.mark.asyncio
    async def test_format_enum_value_extraction(
        self,
        document_store: Dict[UUID, Dict[str, Any]],
        sample_markdown_content: str,
    ):
        """format이 Enum일 때 value 추출 테스트"""
        doc_id = uuid4()

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".md",
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write(sample_markdown_content)
            temp_path = f.name

        document_store[doc_id] = {
            "document_id": doc_id,
            "filename": "enum_test.md",
            "format": DocumentFormat.PDF,  # Enum 값
            "status": DocumentStatus.QUEUED,
            "storage_path": temp_path,
        }

        pipeline = DocumentProcessingPipeline(
            document_store=document_store,
            enable_neo4j=False,
            enable_entity_extraction=False,
        )

        with patch.object(pipeline, "_ensure_services"):
            mock_embedding = MagicMock()
            mock_embedding.aembed_batch = AsyncMock(
                side_effect=lambda texts, **kwargs: ([[0.1] * 1024 for _ in range(len(texts))], [{1: 0.5} for _ in range(len(texts))])
            )
            pipeline.embedding_service = mock_embedding

            mock_es = MagicMock()
            mock_es.index_chunks = AsyncMock(
                return_value={"indexed": 4, "errors": 0}
            )
            pipeline.es_storage = mock_es

            result = await pipeline.process_document(doc_id)
            assert result.success is True

        try:
            os.unlink(temp_path)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Integration Tests (require services)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestPipelineIntegration:
    """통합 테스트 (실제 서비스 연결 필요)

    이 테스트는 pytest -m integration으로 실행됩니다.
    """

    @pytest.mark.asyncio
    async def test_full_pipeline_with_elasticsearch(self):
        """Elasticsearch 연동 전체 파이프라인 테스트"""
        pytest.skip("Requires Elasticsearch connection")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
