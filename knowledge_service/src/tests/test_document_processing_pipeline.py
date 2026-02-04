"""
Document Processing Pipeline 단위 테스트

문서 처리 파이프라인의 각 단계를 테스트합니다.
"""

import asyncio
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

# 환경변수 설정
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("ELASTICSEARCH_HOST", "localhost")
os.environ.setdefault("ELASTICSEARCH_PORT", "9200")
os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("REDIS_HOST", "localhost")

from app.models.document import DocumentFormat, DocumentStatus
from app.services.document_processing_pipeline import (
    DocumentProcessingPipeline,
    DocumentRepository,
    FileStorage,
    ProcessingResult,
    ProcessingStatus,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def document_store() -> Dict[UUID, Dict[str, Any]]:
    """테스트용 In-memory 문서 저장소"""
    return {}


@pytest.fixture
def sample_markdown_content() -> str:
    """테스트용 Markdown 문서 내용"""
    return """# Test Document

## Introduction

This is a test document for the processing pipeline.
It contains sample content for testing chunking and embedding.

## Section 1

Some content in section 1.
Machine learning and artificial intelligence are key technologies.

## Section 2

More content in section 2.
Knowledge graphs help represent relationships between entities.

## Conclusion

This concludes the test document.
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


# ---------------------------------------------------------------------------
# DocumentRepository Tests
# ---------------------------------------------------------------------------


class TestDocumentRepository:
    """DocumentRepository 테스트"""

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


# ---------------------------------------------------------------------------
# FileStorage Tests
# ---------------------------------------------------------------------------


class TestFileStorage:
    """FileStorage 테스트"""

    @pytest.mark.asyncio
    async def test_download_local_file(
        self,
        sample_markdown_content: str,
    ):
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
        with pytest.raises(FileNotFoundError):
            await FileStorage.download_file("/nonexistent/path/file.txt")


# ---------------------------------------------------------------------------
# DocumentProcessingPipeline Tests
# ---------------------------------------------------------------------------


class TestDocumentProcessingPipeline:
    """DocumentProcessingPipeline 테스트"""

    @pytest.mark.asyncio
    async def test_process_document_parsing(
        self,
        document_store: Dict[UUID, Dict[str, Any]],
        sample_document: Dict[str, Any],
    ):
        """문서 파싱 테스트 (Mock 사용)"""
        pipeline = DocumentProcessingPipeline(
            document_store=document_store,
            enable_neo4j=False,
            enable_entity_extraction=False,
        )

        doc_id = sample_document["document_id"]

        # Elasticsearch를 Mock으로 대체
        with patch.object(
            pipeline,
            "_ensure_services",
        ):
            # EmbeddingService Mock - 동적으로 청크 수에 맞게 반환
            mock_embedding = MagicMock()
            mock_embedding.aembed_batch = AsyncMock(
                side_effect=lambda texts: [[0.1] * 1024 for _ in range(len(texts))]
            )
            pipeline.embedding_service = mock_embedding

            # ES Storage Mock
            mock_es = MagicMock()
            mock_es.index_chunks = AsyncMock(
                return_value={"indexed": 4, "errors": 0}
            )
            pipeline.es_storage = mock_es

            # 문서 처리
            result = await pipeline.process_document(doc_id)

            # 검증
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
            "storage_path": None,  # 경로 없음
        }

        pipeline = DocumentProcessingPipeline(
            document_store=document_store,
            enable_neo4j=False,
            enable_entity_extraction=False,
        )

        result = await pipeline.process_document(doc_id)

        assert result.success is False
        assert "스토리지 경로" in result.error_message

    @pytest.mark.asyncio
    async def test_process_pending_documents(
        self,
        document_store: Dict[UUID, Dict[str, Any]],
        sample_markdown_content: str,
    ):
        """대기 문서 일괄 처리 테스트"""
        # 여러 문서 생성
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

        # Mock 설정
        with patch.object(
            pipeline,
            "_ensure_services",
        ):
            mock_embedding = MagicMock()
            mock_embedding.aembed_batch = AsyncMock(
                return_value=[[0.1] * 1024 for _ in range(5)]
            )
            pipeline.embedding_service = mock_embedding

            mock_es = MagicMock()
            mock_es.index_chunks = AsyncMock(
                return_value={"indexed": 5, "errors": 0}
            )
            pipeline.es_storage = mock_es

            # 대기 문서 처리
            results = await pipeline.process_pending_documents(batch_size=2)

            # 첫 2개만 처리되어야 함
            assert len(results) == 2

        # 정리
        for doc in document_store.values():
            try:
                os.unlink(doc.get("storage_path", ""))
            except Exception:
                pass


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
        assert result.chunk_count == 10
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
        # 이 테스트는 실제 Elasticsearch 연결이 필요합니다.
        pytest.skip("Requires Elasticsearch connection")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
