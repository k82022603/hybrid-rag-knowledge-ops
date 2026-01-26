"""EmbeddingService 단위 테스트

STORY-004: BGE-M3 임베딩 생성 - 단위 테스트
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.embedding import ChunkEmbedding, EmbeddingService, get_embedding_service


class TestChunkEmbedding:
    """ChunkEmbedding 데이터클래스 테스트"""

    def test_create_chunk_embedding(self):
        emb = ChunkEmbedding(
            chunk_id="chunk-001",
            dense_vector=[0.1] * 1024,
        )
        assert emb.chunk_id == "chunk-001"
        assert len(emb.dense_vector) == 1024
        assert emb.model_name == "BAAI/bge-m3"
        assert isinstance(emb.created_at, datetime)

    def test_sparse_vector_optional(self):
        emb = ChunkEmbedding(chunk_id="c1", dense_vector=[0.0])
        assert emb.sparse_vector is None

    def test_custom_model_name(self):
        emb = ChunkEmbedding(
            chunk_id="c1",
            dense_vector=[0.0],
            model_name="custom/model",
        )
        assert emb.model_name == "custom/model"


class TestEmbeddingServiceInit:
    """EmbeddingService 초기화 테스트"""

    def test_default_init(self):
        svc = EmbeddingService.__new__(EmbeddingService)
        svc.model_name = "BAAI/bge-m3"
        svc.batch_size = 32
        svc.max_length = 8192
        svc.device = "cpu"
        svc._model = None
        svc._model_type = None
        assert svc.model_name == "BAAI/bge-m3"
        assert svc.batch_size == 32
        assert svc.device == "cpu"

    def test_vector_dimension(self):
        svc = EmbeddingService.__new__(EmbeddingService)
        assert svc.vector_dimension == 1024

    def test_embed_chunks_length_mismatch(self):
        svc = EmbeddingService.__new__(EmbeddingService)
        svc.model_name = "test"
        with pytest.raises(ValueError, match="길이 불일치"):
            svc.embed_chunks(["id1", "id2"], ["text1"])


class TestEmbedBatchEmpty:
    """빈 입력 처리 테스트"""

    def test_empty_texts_returns_empty_list(self):
        svc = EmbeddingService.__new__(EmbeddingService)
        svc._model_type = None
        result = svc.embed_batch([])
        assert result == []

    def test_empty_texts_with_sparse_returns_tuple(self):
        svc = EmbeddingService.__new__(EmbeddingService)
        svc._model_type = None
        result = svc.embed_batch([], return_sparse=True)
        assert result == ([], [])


class TestGetEmbeddingService:
    """싱글톤 팩토리 테스트"""

    def test_singleton(self):
        import app.services.embedding as mod
        mod._embedding_service = None
        with patch.object(EmbeddingService, '__init__', return_value=None):
            svc1 = get_embedding_service()
            svc2 = get_embedding_service()
            assert svc1 is svc2
        mod._embedding_service = None
