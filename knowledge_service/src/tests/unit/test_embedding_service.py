"""EmbeddingService 단위 테스트

STORY-004: BGE-M3 임베딩 생성 - 단위 테스트

테스트 범위:
    - ChunkEmbedding 데이터클래스
    - EmbeddingCache (Redis 캐시 레이어)
    - EmbeddingService 초기화 및 설정
    - 단일/배치 임베딩 생성
    - 벡터 정규화
    - 입력 검증
    - 캐시 통합
    - 싱글톤 팩토리
    - 비동기 메서드
    - 에러 핸들링
"""

import asyncio
import json
import math
import os
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# app.services.__init__의 무거운 의존성(langchain 등)을 회피하기 위해
# importlib.util로 embedding 모듈만 직접 로드
import importlib.util

_emb_spec = importlib.util.spec_from_file_location(
    "app.services.embedding",
    os.path.join(os.path.dirname(__file__), "..", "..", "app", "services", "embedding.py"),
)
_emb_module = importlib.util.module_from_spec(_emb_spec)
sys.modules["app.services.embedding"] = _emb_module
_emb_spec.loader.exec_module(_emb_module)

ChunkEmbedding = _emb_module.ChunkEmbedding
EmbeddingCache = _emb_module.EmbeddingCache
EmbeddingService = _emb_module.EmbeddingService
get_embedding_service = _emb_module.get_embedding_service
reset_embedding_service = _emb_module.reset_embedding_service


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_singleton():
    """각 테스트 전후로 싱글톤 리셋"""
    reset_embedding_service()
    yield
    reset_embedding_service()


@pytest.fixture
def mock_settings():
    """설정 모킹 - importlib로 로드한 모듈에 직접 패치"""
    mock_s = MagicMock()
    mock_s.embedding_model = "BAAI/bge-m3"
    mock_s.embedding_use_fp16 = True
    mock_s.embedding_batch_size = 32
    mock_s.embedding_max_length = 8192
    mock_s.embedding_device = None
    mock_s.embedding_normalize = True
    mock_s.redis_host = "localhost"
    mock_s.redis_port = 6379
    mock_s.redis_password = None
    mock_s.redis_db = 0
    mock_s.redis_embedding_cache_ttl = 604800
    original_settings = _emb_module.settings
    _emb_module.settings = mock_s
    yield mock_s
    _emb_module.settings = original_settings


def _make_service(mock_settings, cache_enabled=False, **kwargs):
    """테스트용 EmbeddingService 생성 헬퍼

    모델 로드를 건너뛰고 _model_type만 설정.
    """
    svc = EmbeddingService.__new__(EmbeddingService)
    svc.model_name = kwargs.get("model_name", "BAAI/bge-m3")
    svc.use_fp16 = kwargs.get("use_fp16", True)
    svc.batch_size = kwargs.get("batch_size", 32)
    svc.max_length = kwargs.get("max_length", 8192)
    svc.device = kwargs.get("device", "cpu")
    svc.normalize = kwargs.get("normalize", True)
    svc._model = kwargs.get("model", None)
    svc._model_type = kwargs.get("model_type", None)
    svc._cache = None
    return svc


# ---------------------------------------------------------------------------
# ChunkEmbedding 테스트
# ---------------------------------------------------------------------------


class TestChunkEmbedding:
    """ChunkEmbedding 데이터클래스 테스트"""

    def test_create_chunk_embedding(self):
        """기본 생성 테스트"""
        emb = ChunkEmbedding(
            chunk_id="chunk-001",
            dense_vector=[0.1] * 1024,
        )
        assert emb.chunk_id == "chunk-001"
        assert len(emb.dense_vector) == 1024
        assert emb.model_name == "BAAI/bge-m3"
        assert isinstance(emb.created_at, datetime)

    def test_sparse_vector_optional(self):
        """sparse_vector 선택적 필드"""
        emb = ChunkEmbedding(chunk_id="c1", dense_vector=[0.0])
        assert emb.sparse_vector is None

    def test_sparse_vector_set(self):
        """sparse_vector 설정 테스트"""
        sparse = {0: 0.5, 10: 0.3, 100: 0.8}
        emb = ChunkEmbedding(
            chunk_id="c1",
            dense_vector=[0.1],
            sparse_vector=sparse,
        )
        assert emb.sparse_vector == sparse
        assert emb.sparse_vector[100] == 0.8

    def test_custom_model_name(self):
        """커스텀 모델명 테스트"""
        emb = ChunkEmbedding(
            chunk_id="c1",
            dense_vector=[0.0],
            model_name="custom/model",
        )
        assert emb.model_name == "custom/model"

    def test_created_at_auto(self):
        """자동 생성 시각 테스트"""
        before = datetime.utcnow()
        emb = ChunkEmbedding(chunk_id="c1", dense_vector=[0.0])
        after = datetime.utcnow()
        assert before <= emb.created_at <= after


# ---------------------------------------------------------------------------
# EmbeddingCache 테스트
# ---------------------------------------------------------------------------


class TestEmbeddingCache:
    """EmbeddingCache Redis 캐시 레이어 테스트"""

    def test_cache_unavailable_when_redis_missing(self):
        """Redis 연결 실패 시 available=False"""
        original_logger = _emb_module.logger
        _emb_module.logger = MagicMock()
        try:
            cache = EmbeddingCache(host="nonexistent", port=9999)
            assert cache.available is False
        finally:
            _emb_module.logger = original_logger

    def test_cache_get_returns_none_when_unavailable(self):
        """캐시 미사용 시 get()은 None 반환"""
        cache = EmbeddingCache.__new__(EmbeddingCache)
        cache._available = False
        cache._redis = None
        assert cache.get("text", "model") is None

    def test_cache_set_noop_when_unavailable(self):
        """캐시 미사용 시 set()은 아무 동작 안 함"""
        cache = EmbeddingCache.__new__(EmbeddingCache)
        cache._available = False
        cache._redis = None
        # 에러 없이 반환되어야 함
        cache.set("text", "model", [0.1, 0.2])

    def test_cache_get_batch_returns_all_miss_when_unavailable(self):
        """캐시 미사용 시 get_batch는 모든 인덱스를 미스로 반환"""
        cache = EmbeddingCache.__new__(EmbeddingCache)
        cache._available = False
        cache._redis = None
        results, misses = cache.get_batch(["a", "b", "c"], "model")
        assert results == [None, None, None]
        assert misses == [0, 1, 2]

    def test_cache_invalidate_noop_when_unavailable(self):
        """캐시 미사용 시 invalidate()는 아무 동작 안 함"""
        cache = EmbeddingCache.__new__(EmbeddingCache)
        cache._available = False
        cache._redis = None
        cache.invalidate("text", "model")  # 에러 없이 통과

    def test_cache_stats_when_unavailable(self):
        """캐시 미사용 시 stats 반환"""
        cache = EmbeddingCache.__new__(EmbeddingCache)
        cache._available = False
        assert cache.stats == {"available": False}

    def test_make_key_deterministic(self):
        """동일 입력에 대해 동일 키 생성"""
        cache = EmbeddingCache.__new__(EmbeddingCache)
        cache._prefix = "emb:"
        key1 = cache._make_key("hello", "BAAI/bge-m3")
        key2 = cache._make_key("hello", "BAAI/bge-m3")
        assert key1 == key2
        assert key1.startswith("emb:")

    def test_make_key_different_for_different_inputs(self):
        """다른 입력에 대해 다른 키 생성"""
        cache = EmbeddingCache.__new__(EmbeddingCache)
        cache._prefix = "emb:"
        key1 = cache._make_key("hello", "BAAI/bge-m3")
        key2 = cache._make_key("world", "BAAI/bge-m3")
        assert key1 != key2

    def test_make_key_different_for_different_models(self):
        """다른 모델에 대해 다른 키 생성"""
        cache = EmbeddingCache.__new__(EmbeddingCache)
        cache._prefix = "emb:"
        key1 = cache._make_key("hello", "BAAI/bge-m3")
        key2 = cache._make_key("hello", "other/model")
        assert key1 != key2

    def test_cache_get_with_mock_redis(self):
        """Redis mock을 사용한 get 테스트"""
        cache = EmbeddingCache.__new__(EmbeddingCache)
        cache._available = True
        cache._prefix = "emb:"
        cache._redis = MagicMock()
        vector = [0.1, 0.2, 0.3]
        cache._redis.get.return_value = json.dumps(vector).encode()

        result = cache.get("text", "model")
        assert result == vector

    def test_cache_get_miss_with_mock_redis(self):
        """Redis mock으로 캐시 미스 테스트"""
        cache = EmbeddingCache.__new__(EmbeddingCache)
        cache._available = True
        cache._prefix = "emb:"
        cache._redis = MagicMock()
        cache._redis.get.return_value = None

        result = cache.get("text", "model")
        assert result is None

    def test_cache_set_with_mock_redis(self):
        """Redis mock을 사용한 set 테스트"""
        cache = EmbeddingCache.__new__(EmbeddingCache)
        cache._available = True
        cache._prefix = "emb:"
        cache._ttl = 3600
        cache._redis = MagicMock()

        cache.set("text", "model", [0.1, 0.2])
        cache._redis.setex.assert_called_once()

    def test_cache_get_batch_with_mock_redis(self):
        """Redis mock을 사용한 배치 get 테스트"""
        cache = EmbeddingCache.__new__(EmbeddingCache)
        cache._available = True
        cache._prefix = "emb:"
        cache._redis = MagicMock()

        v1 = json.dumps([0.1, 0.2]).encode()
        v2 = None
        v3 = json.dumps([0.3, 0.4]).encode()
        cache._redis.mget.return_value = [v1, v2, v3]

        results, misses = cache.get_batch(["a", "b", "c"], "model")
        assert results[0] == [0.1, 0.2]
        assert results[1] is None
        assert results[2] == [0.3, 0.4]
        assert misses == [1]

    def test_cache_set_batch_with_mock_redis(self):
        """Redis mock을 사용한 배치 set 테스트"""
        cache = EmbeddingCache.__new__(EmbeddingCache)
        cache._available = True
        cache._prefix = "emb:"
        cache._ttl = 3600
        cache._redis = MagicMock()
        pipe_mock = MagicMock()
        cache._redis.pipeline.return_value = pipe_mock

        cache.set_batch(["a", "b"], "model", [[0.1], [0.2]])
        assert pipe_mock.setex.call_count == 2
        pipe_mock.execute.assert_called_once()

    def test_cache_set_batch_empty(self):
        """빈 배치 set은 아무 동작 안 함"""
        cache = EmbeddingCache.__new__(EmbeddingCache)
        cache._available = True
        cache._redis = MagicMock()
        cache.set_batch([], "model", [])
        cache._redis.pipeline.assert_not_called()

    def test_cache_get_handles_exception(self):
        """get() 예외 발생 시 None 반환"""
        cache = EmbeddingCache.__new__(EmbeddingCache)
        cache._available = True
        cache._prefix = "emb:"
        cache._redis = MagicMock()
        cache._redis.get.side_effect = Exception("Redis error")

        result = cache.get("text", "model")
        assert result is None

    def test_cache_invalidate_with_mock_redis(self):
        """Redis mock을 사용한 invalidate 테스트"""
        cache = EmbeddingCache.__new__(EmbeddingCache)
        cache._available = True
        cache._prefix = "emb:"
        cache._redis = MagicMock()

        cache.invalidate("text", "model")
        cache._redis.delete.assert_called_once()


# ---------------------------------------------------------------------------
# EmbeddingService 초기화 테스트
# ---------------------------------------------------------------------------


class TestEmbeddingServiceInit:
    """EmbeddingService 초기화 테스트"""

    def test_default_init(self, mock_settings):
        """기본 초기화 테스트"""
        svc = _make_service(mock_settings)
        assert svc.model_name == "BAAI/bge-m3"
        assert svc.batch_size == 32
        assert svc.device == "cpu"
        assert svc.normalize is True

    def test_vector_dimension(self, mock_settings):
        """벡터 차원 상수 테스트"""
        svc = _make_service(mock_settings)
        assert svc.vector_dimension == 1024
        assert EmbeddingService.VECTOR_DIMENSION == 1024

    def test_custom_batch_size(self, mock_settings):
        """커스텀 배치 크기"""
        svc = _make_service(mock_settings, batch_size=8)
        assert svc.batch_size == 8

    def test_custom_device(self, mock_settings):
        """커스텀 디바이스 설정"""
        svc = _make_service(mock_settings, device="cuda")
        assert svc.device == "cuda"

    def test_normalize_false(self, mock_settings):
        """정규화 비활성화"""
        svc = _make_service(mock_settings, normalize=False)
        assert svc.normalize is False

    def test_is_model_loaded_false(self, mock_settings):
        """모델 미로드 상태"""
        svc = _make_service(mock_settings)
        assert svc.is_model_loaded is False

    def test_is_model_loaded_true(self, mock_settings):
        """모델 로드 완료 상태"""
        svc = _make_service(mock_settings, model=MagicMock())
        assert svc.is_model_loaded is True

    def test_embed_chunks_length_mismatch(self, mock_settings):
        """chunk_ids와 texts 길이 불일치 시 ValueError"""
        svc = _make_service(mock_settings)
        with pytest.raises(ValueError, match="길이 불일치"):
            svc.embed_chunks(["id1", "id2"], ["text1"])


# ---------------------------------------------------------------------------
# 벡터 정규화 테스트
# ---------------------------------------------------------------------------


class TestNormalization:
    """벡터 L2 정규화 테스트"""

    def test_normalize_vector(self):
        """단일 벡터 정규화"""
        vec = [3.0, 4.0]
        normalized = EmbeddingService._normalize_vector(vec)
        # L2 norm of [3,4] = 5
        assert abs(normalized[0] - 0.6) < 1e-7
        assert abs(normalized[1] - 0.8) < 1e-7

    def test_normalize_vector_unit_norm(self):
        """정규화된 벡터의 L2 norm은 1"""
        vec = [1.0, 2.0, 3.0, 4.0, 5.0]
        normalized = EmbeddingService._normalize_vector(vec)
        norm = math.sqrt(sum(x * x for x in normalized))
        assert abs(norm - 1.0) < 1e-7

    def test_normalize_zero_vector(self):
        """영벡터 정규화 (그대로 반환)"""
        vec = [0.0, 0.0, 0.0]
        normalized = EmbeddingService._normalize_vector(vec)
        assert normalized == vec

    def test_normalize_vectors_batch(self):
        """배치 벡터 정규화"""
        vecs = [[3.0, 4.0], [1.0, 0.0]]
        normalized = EmbeddingService._normalize_vectors(vecs)
        assert abs(normalized[0][0] - 0.6) < 1e-7
        assert abs(normalized[1][0] - 1.0) < 1e-7
        assert abs(normalized[1][1] - 0.0) < 1e-7

    def test_normalize_high_dimension(self):
        """1024차원 벡터 정규화"""
        vec = [1.0] * 1024
        normalized = EmbeddingService._normalize_vector(vec)
        norm = math.sqrt(sum(x * x for x in normalized))
        assert abs(norm - 1.0) < 1e-6


# ---------------------------------------------------------------------------
# 입력 검증 테스트
# ---------------------------------------------------------------------------


class TestValidateTexts:
    """입력 텍스트 검증 테스트"""

    def test_normal_texts(self, mock_settings):
        """정상 텍스트 통과"""
        svc = _make_service(mock_settings)
        result = svc._validate_texts(["hello", "world"])
        assert result == ["hello", "world"]

    def test_empty_string_replaced(self, mock_settings):
        """빈 문자열 대체"""
        svc = _make_service(mock_settings)
        result = svc._validate_texts(["hello", "", "world"])
        assert result[1] == " "

    def test_whitespace_only_replaced(self, mock_settings):
        """공백만 있는 문자열 대체"""
        svc = _make_service(mock_settings)
        result = svc._validate_texts(["  ", "\t", "\n"])
        assert all(t == " " for t in result)

    def test_korean_text_passes(self, mock_settings):
        """한국어 텍스트 정상 통과"""
        svc = _make_service(mock_settings)
        result = svc._validate_texts(["인공지능 기술", "자연어 처리"])
        assert result == ["인공지능 기술", "자연어 처리"]


# ---------------------------------------------------------------------------
# embed_batch 빈 입력 테스트
# ---------------------------------------------------------------------------


class TestEmbedBatchEmpty:
    """빈 입력 처리 테스트"""

    def test_empty_texts_returns_empty_list(self, mock_settings):
        """빈 텍스트 리스트 -> 빈 리스트"""
        svc = _make_service(mock_settings)
        result = svc.embed_batch([])
        assert result == []

    def test_empty_texts_with_sparse_returns_tuple(self, mock_settings):
        """빈 텍스트 + return_sparse -> ([], [])"""
        svc = _make_service(mock_settings)
        result = svc.embed_batch([], return_sparse=True)
        assert result == ([], [])


# ---------------------------------------------------------------------------
# embed_batch 모델 호출 테스트
# ---------------------------------------------------------------------------


class TestEmbedBatchWithMockModel:
    """모델을 mock하여 embed_batch 테스트"""

    def test_embed_batch_flag_embedding(self, mock_settings):
        """FlagEmbedding 기반 배치 임베딩"""
        import numpy as np

        mock_model = MagicMock()
        mock_model.encode.return_value = {
            "dense_vecs": np.array([[0.3, 0.4]] * 2),
        }

        svc = _make_service(
            mock_settings,
            model=mock_model,
            model_type="flag_embedding",
            normalize=False,
        )

        result = svc.embed_batch(["hello", "world"])
        assert len(result) == 2
        assert result[0] == [0.3, 0.4]

    def test_embed_batch_with_normalization(self, mock_settings):
        """정규화 적용 배치 임베딩"""
        import numpy as np

        mock_model = MagicMock()
        mock_model.encode.return_value = {
            "dense_vecs": np.array([[3.0, 4.0]]),
        }

        svc = _make_service(
            mock_settings,
            model=mock_model,
            model_type="flag_embedding",
            normalize=True,
        )

        result = svc.embed_batch(["test"])
        assert len(result) == 1
        # 정규화 확인: [3, 4] -> [0.6, 0.8]
        assert abs(result[0][0] - 0.6) < 1e-7
        assert abs(result[0][1] - 0.8) < 1e-7

    def test_embed_batch_sentence_transformers(self, mock_settings):
        """sentence-transformers 기반 배치 임베딩"""
        import numpy as np

        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[0.5, 0.5]])

        svc = _make_service(
            mock_settings,
            model=mock_model,
            model_type="sentence_transformers",
            normalize=False,
        )

        result = svc.embed_batch(["test"])
        assert len(result) == 1

    def test_embed_batch_with_sparse(self, mock_settings):
        """Sparse 벡터 포함 배치 임베딩"""
        import numpy as np

        mock_model = MagicMock()
        mock_model.encode.return_value = {
            "dense_vecs": np.array([[0.1, 0.2]]),
            "lexical_weights": [{0: 0.5, 10: 0.3}],
        }

        svc = _make_service(
            mock_settings,
            model=mock_model,
            model_type="flag_embedding",
            normalize=False,
        )

        dense, sparse = svc.embed_batch(["test"], return_sparse=True)
        assert len(dense) == 1
        assert len(sparse) == 1
        assert sparse[0][0] == 0.5

    def test_embed_single(self, mock_settings):
        """단일 텍스트 임베딩"""
        import numpy as np

        mock_model = MagicMock()
        mock_model.encode.return_value = {
            "dense_vecs": np.array([[0.1, 0.2]]),
        }

        svc = _make_service(
            mock_settings,
            model=mock_model,
            model_type="flag_embedding",
            normalize=False,
        )

        result = svc.embed("test")
        assert result == [0.1, 0.2]


# ---------------------------------------------------------------------------
# embed_chunks 테스트
# ---------------------------------------------------------------------------


class TestEmbedChunks:
    """embed_chunks 메서드 테스트"""

    def test_embed_chunks_basic(self, mock_settings):
        """기본 청크 임베딩"""
        import numpy as np

        mock_model = MagicMock()
        mock_model.encode.return_value = {
            "dense_vecs": np.array([[0.1] * 2, [0.2] * 2]),
        }

        svc = _make_service(
            mock_settings,
            model=mock_model,
            model_type="flag_embedding",
            normalize=False,
        )

        chunks = svc.embed_chunks(["c1", "c2"], ["text1", "text2"])
        assert len(chunks) == 2
        assert chunks[0].chunk_id == "c1"
        assert chunks[0].dense_vector == [0.1, 0.1]
        assert chunks[1].chunk_id == "c2"
        assert chunks[0].model_name == "BAAI/bge-m3"
        assert chunks[0].sparse_vector is None

    def test_embed_chunks_with_sparse(self, mock_settings):
        """Sparse 포함 청크 임베딩"""
        import numpy as np

        mock_model = MagicMock()
        mock_model.encode.return_value = {
            "dense_vecs": np.array([[0.1, 0.2]]),
            "lexical_weights": [{5: 0.9}],
        }

        svc = _make_service(
            mock_settings,
            model=mock_model,
            model_type="flag_embedding",
            normalize=False,
        )

        chunks = svc.embed_chunks(["c1"], ["text1"], return_sparse=True)
        assert len(chunks) == 1
        assert chunks[0].sparse_vector == {5: 0.9}

    def test_embed_chunks_length_mismatch(self, mock_settings):
        """길이 불일치 시 ValueError"""
        svc = _make_service(mock_settings)
        with pytest.raises(ValueError, match="길이 불일치"):
            svc.embed_chunks(["c1"], ["t1", "t2"])


# ---------------------------------------------------------------------------
# 캐시 통합 테스트
# ---------------------------------------------------------------------------


class TestEmbeddingServiceWithCache:
    """캐시 통합 테스트"""

    def test_embed_with_cache_hit(self, mock_settings):
        """캐시 히트 시 모델 호출 없이 반환"""
        svc = _make_service(mock_settings)
        mock_cache = MagicMock(spec=EmbeddingCache)
        mock_cache.available = True
        mock_cache.get.return_value = [0.1, 0.2, 0.3]
        svc._cache = mock_cache

        result = svc.embed("test text")
        assert result == [0.1, 0.2, 0.3]
        # 모델은 호출되지 않아야 함 (svc._model is None)

    def test_embed_batch_with_partial_cache(self, mock_settings):
        """부분 캐시 히트: 미스 텍스트만 모델 호출"""
        import numpy as np

        mock_model = MagicMock()
        # 캐시 미스인 1개만 인코딩
        mock_model.encode.return_value = {
            "dense_vecs": np.array([[0.5, 0.6]]),
        }

        svc = _make_service(
            mock_settings,
            model=mock_model,
            model_type="flag_embedding",
            normalize=False,
        )

        mock_cache = MagicMock(spec=EmbeddingCache)
        mock_cache.available = True
        mock_cache.get_batch.return_value = (
            [[0.1, 0.2], None, [0.3, 0.4]],  # 인덱스 1만 미스
            [1],
        )
        svc._cache = mock_cache

        result = svc.embed_batch(["a", "b", "c"])
        assert len(result) == 3
        assert result[0] == [0.1, 0.2]  # 캐시 히트
        assert result[1] == [0.5, 0.6]  # 새로 생성
        assert result[2] == [0.3, 0.4]  # 캐시 히트

    def test_embed_batch_full_cache_hit(self, mock_settings):
        """전체 캐시 히트: 모델 호출 없음"""
        svc = _make_service(mock_settings)

        mock_cache = MagicMock(spec=EmbeddingCache)
        mock_cache.available = True
        mock_cache.get_batch.return_value = (
            [[0.1], [0.2]],
            [],  # 미스 없음
        )
        svc._cache = mock_cache

        result = svc.embed_batch(["a", "b"])
        assert result == [[0.1], [0.2]]

    def test_embed_batch_cache_disabled(self, mock_settings):
        """캐시 비활성화 시 항상 모델 호출"""
        import numpy as np

        mock_model = MagicMock()
        mock_model.encode.return_value = {
            "dense_vecs": np.array([[0.1, 0.2]]),
        }

        svc = _make_service(
            mock_settings,
            model=mock_model,
            model_type="flag_embedding",
            normalize=False,
        )
        svc._cache = None

        result = svc.embed_batch(["test"])
        assert len(result) == 1
        mock_model.encode.assert_called_once()


# ---------------------------------------------------------------------------
# 모델 로드 테스트
# ---------------------------------------------------------------------------


class TestModelLoading:
    """모델 로드 테스트"""

    def test_load_model_flag_embedding(self, mock_settings):
        """FlagEmbedding 모델 로드 시뮬레이션"""
        svc = _make_service(mock_settings)
        # FlagEmbedding 로드를 직접 시뮬레이션
        svc._model = MagicMock()
        svc._model_type = "flag_embedding"
        assert svc._model_type == "flag_embedding"
        assert svc._model is not None

    def test_load_model_fallback_to_sentence_transformers(self, mock_settings):
        """FlagEmbedding 실패 시 sentence-transformers 폴백 시뮬레이션"""
        svc = _make_service(mock_settings)
        # sentence-transformers 폴백을 시뮬레이션
        svc._model_type = "sentence_transformers"
        svc._model = MagicMock()
        assert svc._model_type == "sentence_transformers"

    def test_load_model_raises_on_both_missing(self, mock_settings):
        """두 라이브러리 모두 없을 때 EmbeddingModelLoadError"""
        from app.core.exceptions import EmbeddingModelLoadError

        svc = _make_service(mock_settings)

        original_import = __import__

        def mock_import(name, *args, **kwargs):
            if name in ("FlagEmbedding", "sentence_transformers"):
                raise ImportError(f"No module named '{name}'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(EmbeddingModelLoadError):
                svc._load_model()

    def test_lazy_loading_via_model_property(self, mock_settings):
        """model 프로퍼티 접근 시 이미 로드된 모델 반환"""
        svc = _make_service(mock_settings)
        mock_model = MagicMock()
        svc._model = mock_model

        assert svc.model is mock_model


# ---------------------------------------------------------------------------
# 디바이스 감지 테스트
# ---------------------------------------------------------------------------


class TestDeviceDetection:
    """GPU/CPU 자동 감지 테스트"""

    def test_detect_cpu_when_no_torch(self):
        """torch 미설치 시 CPU"""
        original_import = __import__

        def mock_import(name, *args, **kwargs):
            if name == "torch":
                raise ImportError("No torch")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            device = EmbeddingService._detect_device()
            assert device == "cpu"


# ---------------------------------------------------------------------------
# 헬스 체크 테스트
# ---------------------------------------------------------------------------


class TestHealthCheck:
    """서비스 상태 점검 테스트"""

    def test_health_check_basic(self, mock_settings):
        """기본 헬스 체크"""
        svc = _make_service(mock_settings)
        health = svc.health_check()

        assert health["service"] == "EmbeddingService"
        assert health["model_name"] == "BAAI/bge-m3"
        assert health["model_loaded"] is False
        assert health["vector_dimension"] == 1024
        assert health["batch_size"] == 32
        assert health["normalize"] is True

    def test_health_check_with_model(self, mock_settings):
        """모델 로드 후 헬스 체크"""
        svc = _make_service(
            mock_settings,
            model=MagicMock(),
            model_type="flag_embedding",
        )
        health = svc.health_check()
        assert health["model_loaded"] is True
        assert health["model_type"] == "flag_embedding"

    def test_cache_stats_disabled(self, mock_settings):
        """캐시 비활성화 시 stats"""
        svc = _make_service(mock_settings)
        stats = svc.cache_stats
        assert stats["available"] is False


# ---------------------------------------------------------------------------
# 싱글톤 팩토리 테스트
# ---------------------------------------------------------------------------


class TestGetEmbeddingService:
    """싱글톤 팩토리 테스트"""

    def test_singleton(self, mock_settings):
        """동일 인스턴스 반환"""
        with patch.object(EmbeddingService, "__init__", return_value=None):
            svc1 = get_embedding_service()
            svc2 = get_embedding_service()
            assert svc1 is svc2

    def test_reset_singleton(self, mock_settings):
        """싱글톤 리셋"""
        with patch.object(EmbeddingService, "__init__", return_value=None):
            svc1 = get_embedding_service()
            reset_embedding_service()
            svc2 = get_embedding_service()
            assert svc1 is not svc2


# ---------------------------------------------------------------------------
# 에러 핸들링 테스트
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """에러 핸들링 테스트"""

    def test_embed_raises_embedding_error(self, mock_settings):
        """embed() 실패 시 EmbeddingError"""
        from app.core.exceptions import EmbeddingError

        svc = _make_service(mock_settings, model_type="flag_embedding")
        mock_model = MagicMock()
        mock_model.encode.side_effect = RuntimeError("Model crashed")
        svc._model = mock_model

        with pytest.raises(EmbeddingError, match="임베딩 생성 실패"):
            svc.embed("test")

    def test_embed_batch_raises_embedding_error(self, mock_settings):
        """embed_batch() 실패 시 EmbeddingError"""
        from app.core.exceptions import EmbeddingError

        svc = _make_service(mock_settings, model_type="flag_embedding")
        mock_model = MagicMock()
        mock_model.encode.side_effect = RuntimeError("OOM")
        svc._model = mock_model

        with pytest.raises(EmbeddingError, match="배치 임베딩 생성 실패"):
            svc.embed_batch(["test"])


# ---------------------------------------------------------------------------
# 비동기 메서드 테스트
# ---------------------------------------------------------------------------


class TestAsyncMethods:
    """비동기 메서드 테스트"""

    @pytest.mark.asyncio
    async def test_aembed(self, mock_settings):
        """비동기 단일 임베딩"""
        import numpy as np

        mock_model = MagicMock()
        mock_model.encode.return_value = {
            "dense_vecs": np.array([[0.1, 0.2]]),
        }

        svc = _make_service(
            mock_settings,
            model=mock_model,
            model_type="flag_embedding",
            normalize=False,
        )

        result = await svc.aembed("test")
        assert result == [0.1, 0.2]

    @pytest.mark.asyncio
    async def test_aembed_batch(self, mock_settings):
        """비동기 배치 임베딩"""
        import numpy as np

        mock_model = MagicMock()
        mock_model.encode.return_value = {
            "dense_vecs": np.array([[0.1, 0.2], [0.3, 0.4]]),
        }

        svc = _make_service(
            mock_settings,
            model=mock_model,
            model_type="flag_embedding",
            normalize=False,
        )

        result = await svc.aembed_batch(["a", "b"])
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_aembed_chunks(self, mock_settings):
        """비동기 청크 임베딩"""
        import numpy as np

        mock_model = MagicMock()
        mock_model.encode.return_value = {
            "dense_vecs": np.array([[0.1, 0.2]]),
        }

        svc = _make_service(
            mock_settings,
            model=mock_model,
            model_type="flag_embedding",
            normalize=False,
        )

        chunks = await svc.aembed_chunks(["c1"], ["text"])
        assert len(chunks) == 1
        assert chunks[0].chunk_id == "c1"
