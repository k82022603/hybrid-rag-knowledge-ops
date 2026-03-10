"""
BGE-M3 임베딩 서비스

STORY-004: BGE-M3 임베딩 생성
- Dense 임베딩 (1024차원)
- Sparse 임베딩 (Hybrid 검색용)
- 배치 처리 지원 (설정 가능한 batch_size)
- 한국어/영어 다국어 임베딩 지원
- Redis 캐시 레이어
- 벡터 정규화
- CPU/GPU 자동 감지
- BGE-M3 / sentence-transformers 자동 폴백
"""

import asyncio
import hashlib
import json
import math
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

from app.core.config import settings
from app.core.exceptions import EmbeddingError, EmbeddingModelLoadError
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ChunkEmbedding:
    """청크 임베딩 결과

    Attributes:
        chunk_id: 청크 고유 식별자
        dense_vector: 1024차원 Dense 벡터
        sparse_vector: Sparse 벡터 (Hybrid 검색용, 선택)
        model_name: 사용된 임베딩 모델명
        created_at: 생성 시각 (UTC)
    """

    chunk_id: str
    dense_vector: List[float]
    sparse_vector: Optional[Dict[str, float]] = None
    model_name: str = "BAAI/bge-m3"
    created_at: datetime = field(default_factory=datetime.utcnow)


class EmbeddingCache:
    """Redis 기반 임베딩 캐시 레이어

    동일 텍스트에 대한 반복 임베딩 요청을 캐시하여 성능 향상.
    Redis 연결 실패 시 캐시 미스로 처리 (서비스 중단 방지).

    Attributes:
        _redis: Redis 클라이언트 인스턴스
        _ttl: 캐시 TTL (초)
        _prefix: Redis 키 접두사
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        password: Optional[str] = None,
        db: int = 0,
        ttl: int = 86400 * 7,
        prefix: str = "emb:",
    ):
        """Redis 캐시 초기화

        Args:
            host: Redis 호스트
            port: Redis 포트
            password: Redis 비밀번호
            db: Redis DB 번호
            ttl: 캐시 유효 기간 (초, 기본 7일)
            prefix: Redis 키 접두사
        """
        self._redis = None
        self._ttl = ttl
        self._prefix = prefix
        self._host = host
        self._port = port
        self._password = password
        self._db = db
        self._available = False
        self._connect()

    def _connect(self) -> None:
        """Redis 연결 시도 (실패 시 캐시 비활성화)"""
        try:
            import redis

            self._redis = redis.Redis(
                host=self._host,
                port=self._port,
                password=self._password,
                db=self._db,
                decode_responses=False,
                socket_connect_timeout=3,
                socket_timeout=3,
            )
            self._redis.ping()
            self._available = True
            logger.info(
                "Embedding cache connected: host=%s, port=%d, ttl=%ds",
                self._host,
                self._port,
                self._ttl,
            )
        except Exception as e:
            self._available = False
            logger.warning(
                "Redis unavailable for embedding cache, running without cache: %s", e
            )

    @property
    def available(self) -> bool:
        """캐시 사용 가능 여부"""
        return self._available

    def _make_key(self, text: str, model_name: str, sparse: bool = False) -> str:
        """캐시 키 생성 (텍스트 + 모델명 + sparse 여부 해시)

        Args:
            text: 임베딩 대상 텍스트
            model_name: 모델명
            sparse: Sparse 벡터 포함 키 여부

        Returns:
            Redis 키 문자열
        """
        sparse_tag = "sparse:" if sparse else ""
        content = f"{model_name}:{sparse_tag}{text}"
        text_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
        return f"{self._prefix}{text_hash}"

    def get(self, text: str, model_name: str) -> Optional[List[float]]:
        """캐시에서 Dense 임베딩 벡터 조회

        Args:
            text: 임베딩 대상 텍스트
            model_name: 모델명

        Returns:
            캐시된 벡터 또는 None (미스 시)
        """
        if not self._available:
            return None
        try:
            key = self._make_key(text, model_name)
            data = self._redis.get(key)
            if data is not None:
                return json.loads(data)
            return None
        except Exception as e:
            logger.debug("Cache get failed: %s", e)
            return None

    def get_with_sparse(
        self, text: str, model_name: str
    ) -> Optional[Tuple[List[float], Dict[str, float]]]:
        """캐시에서 Dense + Sparse 임베딩 벡터 조회

        Args:
            text: 임베딩 대상 텍스트
            model_name: 모델명

        Returns:
            (dense_vector, sparse_vector) 튜플 또는 None (미스 시)
        """
        if not self._available:
            return None
        try:
            key = self._make_key(text, model_name, sparse=True)
            data = self._redis.get(key)
            if data is not None:
                cached = json.loads(data)
                return cached["dense"], cached["sparse"]
            return None
        except Exception as e:
            logger.debug("Cache get_with_sparse failed: %s", e)
            return None

    def get_batch(
        self, texts: List[str], model_name: str
    ) -> Tuple[List[Optional[List[float]]], List[int]]:
        """배치 캐시 조회 (Dense only)

        Args:
            texts: 텍스트 리스트
            model_name: 모델명

        Returns:
            (결과 리스트, 캐시 미스 인덱스 리스트) 튜플.
            결과 리스트의 캐시 미스 위치는 None.
        """
        if not self._available or not texts:
            return [None] * len(texts), list(range(len(texts)))

        try:
            keys = [self._make_key(t, model_name) for t in texts]
            values = self._redis.mget(keys)

            results: List[Optional[List[float]]] = []
            miss_indices: List[int] = []

            for i, val in enumerate(values):
                if val is not None:
                    results.append(json.loads(val))
                else:
                    results.append(None)
                    miss_indices.append(i)

            return results, miss_indices
        except Exception as e:
            logger.debug("Cache batch get failed: %s", e)
            return [None] * len(texts), list(range(len(texts)))

    def get_batch_with_sparse(
        self, texts: List[str], model_name: str
    ) -> Tuple[
        List[Optional[Tuple[List[float], Dict[str, float]]]],
        List[int],
    ]:
        """배치 캐시 조회 (Dense + Sparse)

        Args:
            texts: 텍스트 리스트
            model_name: 모델명

        Returns:
            (결과 리스트, 캐시 미스 인덱스 리스트) 튜플.
            결과 리스트의 캐시 미스 위치는 None.
            각 히트 항목은 (dense_vector, sparse_vector) 튜플.
        """
        if not self._available or not texts:
            return [None] * len(texts), list(range(len(texts)))

        try:
            keys = [self._make_key(t, model_name, sparse=True) for t in texts]
            values = self._redis.mget(keys)

            results: List[Optional[Tuple[List[float], Dict[str, float]]]] = []
            miss_indices: List[int] = []

            for i, val in enumerate(values):
                if val is not None:
                    cached = json.loads(val)
                    results.append((cached["dense"], cached["sparse"]))
                else:
                    results.append(None)
                    miss_indices.append(i)

            return results, miss_indices
        except Exception as e:
            logger.debug("Cache batch get_with_sparse failed: %s", e)
            return [None] * len(texts), list(range(len(texts)))

    def set(self, text: str, model_name: str, vector: List[float]) -> None:
        """Dense 임베딩 벡터를 캐시에 저장

        Args:
            text: 임베딩 대상 텍스트
            model_name: 모델명
            vector: 임베딩 벡터
        """
        if not self._available:
            return
        try:
            key = self._make_key(text, model_name)
            self._redis.setex(key, self._ttl, json.dumps(vector))
        except Exception as e:
            logger.debug("Cache set failed: %s", e)

    def set_with_sparse(
        self,
        text: str,
        model_name: str,
        dense_vector: List[float],
        sparse_vector: Dict[str, float],
    ) -> None:
        """Dense + Sparse 임베딩 벡터를 캐시에 저장

        Args:
            text: 임베딩 대상 텍스트
            model_name: 모델명
            dense_vector: Dense 임베딩 벡터
            sparse_vector: Sparse 임베딩 벡터
        """
        if not self._available:
            return
        try:
            key = self._make_key(text, model_name, sparse=True)
            payload = {"dense": dense_vector, "sparse": sparse_vector}
            self._redis.setex(key, self._ttl, json.dumps(payload))
        except Exception as e:
            logger.debug("Cache set_with_sparse failed: %s", e)

    def set_batch(
        self, texts: List[str], model_name: str, vectors: List[List[float]]
    ) -> None:
        """배치 캐시 저장 (Dense only)

        Args:
            texts: 텍스트 리스트
            model_name: 모델명
            vectors: 벡터 리스트
        """
        if not self._available or not texts:
            return
        try:
            pipe = self._redis.pipeline()
            for text, vector in zip(texts, vectors):
                key = self._make_key(text, model_name)
                pipe.setex(key, self._ttl, json.dumps(vector))
            pipe.execute()
        except Exception as e:
            logger.debug("Cache batch set failed: %s", e)

    def set_batch_with_sparse(
        self,
        texts: List[str],
        model_name: str,
        dense_vectors: List[List[float]],
        sparse_vectors: List[Dict[str, float]],
    ) -> None:
        """배치 캐시 저장 (Dense + Sparse)

        Args:
            texts: 텍스트 리스트
            model_name: 모델명
            dense_vectors: Dense 벡터 리스트
            sparse_vectors: Sparse 벡터 리스트
        """
        if not self._available or not texts:
            return
        try:
            pipe = self._redis.pipeline()
            for text, dense, sparse in zip(texts, dense_vectors, sparse_vectors):
                key = self._make_key(text, model_name, sparse=True)
                payload = {"dense": dense, "sparse": sparse}
                pipe.setex(key, self._ttl, json.dumps(payload))
            pipe.execute()
        except Exception as e:
            logger.debug("Cache batch set_with_sparse failed: %s", e)

    def invalidate(self, text: str, model_name: str) -> None:
        """특정 텍스트의 캐시 무효화 (Dense + Sparse 모두)

        Args:
            text: 대상 텍스트
            model_name: 모델명
        """
        if not self._available:
            return
        try:
            dense_key = self._make_key(text, model_name)
            sparse_key = self._make_key(text, model_name, sparse=True)
            self._redis.delete(dense_key, sparse_key)
        except Exception as e:
            logger.debug("Cache invalidate failed: %s", e)

    @property
    def stats(self) -> Dict[str, Any]:
        """캐시 통계 정보

        Returns:
            캐시 상태 정보 딕셔너리
        """
        if not self._available:
            return {"available": False}
        try:
            info = self._redis.info("memory")
            db_info = self._redis.info("keyspace")
            return {
                "available": True,
                "used_memory_human": info.get("used_memory_human", "N/A"),
                "keyspace": db_info,
            }
        except Exception:
            return {"available": True, "error": "stats unavailable"}


class EmbeddingService:
    """BGE-M3 기반 임베딩 서비스

    한국어/영어 다국어 임베딩을 지원하며, Dense(1024차원) 및
    Sparse 임베딩을 생성합니다. Redis 캐시를 통한 중복 요청 최적화,
    벡터 정규화, 배치 처리를 지원합니다.

    Features:
        - Dense 임베딩 (1024차원)
        - Sparse 임베딩 (Hybrid 검색용)
        - 배치 처리 지원 (설정 가능한 batch_size)
        - 한국어/영어 다국어 임베딩 지원
        - Redis 캐시 레이어 (결정적 결과 보장)
        - 벡터 L2 정규화
        - CPU/GPU 자동 감지
        - BGE-M3 / sentence-transformers 자동 폴백

    Attributes:
        model_name: 임베딩 모델명
        batch_size: 배치 처리 크기
        max_length: 최대 토큰 길이
        device: 연산 디바이스 (cpu/cuda)
        normalize: 벡터 정규화 여부
    """

    VECTOR_DIMENSION: int = 1024

    def __init__(
        self,
        model_name: Optional[str] = None,
        use_fp16: Optional[bool] = None,
        device: Optional[str] = None,
        batch_size: Optional[int] = None,
        max_length: Optional[int] = None,
        normalize: Optional[bool] = None,
        cache_enabled: bool = True,
    ):
        """EmbeddingService 초기화

        Args:
            model_name: 임베딩 모델명 (기본: 환경설정)
            use_fp16: FP16 사용 여부 (기본: 환경설정)
            device: 연산 디바이스 ('cpu', 'cuda', None=자동)
            batch_size: 배치 크기 (기본: 환경설정)
            max_length: 최대 토큰 길이 (기본: 환경설정)
            normalize: 벡터 정규화 여부 (기본: 환경설정)
            cache_enabled: Redis 캐시 사용 여부

        Raises:
            EmbeddingError: 초기화 실패 시
        """
        self.model_name = model_name or settings.embedding_model
        self.use_fp16 = use_fp16 if use_fp16 is not None else settings.embedding_use_fp16
        self.batch_size = batch_size or settings.embedding_batch_size
        self.max_length = max_length or settings.embedding_max_length
        self.normalize = normalize if normalize is not None else settings.embedding_normalize
        self._model = None
        self._model_type: Optional[str] = None

        # 디바이스 설정
        if device is not None:
            self.device = device
        elif settings.embedding_device is not None:
            self.device = settings.embedding_device
        else:
            self.device = self._detect_device()

        # 캐시 초기화
        self._cache: Optional[EmbeddingCache] = None
        if cache_enabled:
            self._cache = EmbeddingCache(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password,
                db=settings.redis_db,
                ttl=settings.redis_embedding_cache_ttl,
            )

        logger.info(
            "EmbeddingService initialized: model=%s, device=%s, fp16=%s, "
            "batch_size=%d, normalize=%s, cache=%s",
            self.model_name,
            self.device,
            self.use_fp16,
            self.batch_size,
            self.normalize,
            "enabled" if self._cache and self._cache.available else "disabled",
        )

    @staticmethod
    def _detect_device() -> str:
        """GPU 사용 가능 여부를 자동 감지

        Returns:
            'cuda' 또는 'cpu'
        """
        try:
            import torch

            if torch.cuda.is_available():
                device_name = torch.cuda.get_device_name(0)
                logger.info("CUDA device detected: %s", device_name)
                return "cuda"
        except ImportError:
            pass
        return "cpu"

    @property
    def model(self) -> Any:
        """모델 지연 로딩 (Lazy Loading)

        Returns:
            로드된 임베딩 모델 인스턴스

        Raises:
            EmbeddingModelLoadError: 모델 로드 실패 시
        """
        if self._model is None:
            self._load_model()
        return self._model

    def _load_model(self) -> None:
        """BGE-M3 모델 로드 (FlagEmbedding -> sentence-transformers 폴백)

        Raises:
            EmbeddingModelLoadError: 모든 로드 방법이 실패할 경우
        """
        load_start = time.time()

        # 1차 시도: FlagEmbedding (BGE-M3 네이티브)
        try:
            from FlagEmbedding import BGEM3FlagModel

            self._model = BGEM3FlagModel(
                self.model_name,
                use_fp16=self.use_fp16 and self.device != "cpu",
                device=self.device,
            )
            self._model_type = "flag_embedding"
            elapsed = time.time() - load_start
            logger.info(
                "BGE-M3 model loaded via FlagEmbedding on %s (%.2fs)",
                self.device,
                elapsed,
            )
            return
        except ImportError:
            logger.warning("FlagEmbedding not available, trying sentence-transformers")
        except Exception as e:
            logger.warning("FlagEmbedding load failed: %s, trying fallback", e)

        # 2차 시도: sentence-transformers
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name, device=self.device)
            self._model_type = "sentence_transformers"
            elapsed = time.time() - load_start
            logger.info(
                "Model loaded via sentence-transformers: %s (%.2fs)",
                self.model_name,
                elapsed,
            )
            return
        except ImportError:
            pass
        except Exception as e:
            logger.error("sentence-transformers load failed: %s", e)

        raise EmbeddingModelLoadError(
            model_name=self.model_name,
            message=(
                f"임베딩 모델 '{self.model_name}'을 로드할 수 없습니다. "
                "FlagEmbedding 또는 sentence-transformers를 설치하세요. "
                "pip install FlagEmbedding 또는 pip install sentence-transformers"
            ),
        )

    @staticmethod
    def _normalize_vector(vector: List[float]) -> List[float]:
        """L2 정규화 (단위 벡터로 변환) — numpy 가속

        Args:
            vector: 정규화할 벡터

        Returns:
            L2 정규화된 벡터. 영벡터인 경우 그대로 반환.
        """
        arr = np.array(vector, dtype=np.float32)
        norm = np.linalg.norm(arr)
        if norm == 0.0:
            return vector
        return (arr / norm).tolist()

    @staticmethod
    def _normalize_vectors(vectors: List[List[float]]) -> List[List[float]]:
        """벡터 리스트 L2 정규화 — numpy 배치 가속

        Args:
            vectors: 정규화할 벡터 리스트

        Returns:
            L2 정규화된 벡터 리스트
        """
        arr = np.array(vectors, dtype=np.float32)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms = np.where(norms == 0.0, 1.0, norms)
        return (arr / norms).tolist()

    def _validate_texts(self, texts: List[str]) -> List[str]:
        """입력 텍스트 전처리 및 검증

        빈 문자열은 공백으로 대체하여 모델 오류 방지.

        Args:
            texts: 입력 텍스트 리스트

        Returns:
            전처리된 텍스트 리스트
        """
        processed = []
        for i, text in enumerate(texts):
            if not text or not text.strip():
                logger.warning("Empty text at index %d, replacing with space", i)
                processed.append(" ")
            else:
                processed.append(text)
        return processed

    def embed(self, text: str) -> List[float]:
        """단일 텍스트 Dense 임베딩

        캐시 히트 시 캐시된 결과를 반환합니다.

        Args:
            text: 임베딩할 텍스트

        Returns:
            1024차원 float 벡터 (정규화 설정에 따라 정규화됨)

        Raises:
            EmbeddingError: 임베딩 생성 실패 시
        """
        # 캐시 조회
        if self._cache:
            cached = self._cache.get(text, self.model_name)
            if cached is not None:
                logger.debug("Cache hit for single embed")
                return cached

        try:
            results = self.embed_batch([text])
            return results[0]
        except Exception as e:
            raise EmbeddingError(
                message=f"텍스트 임베딩 생성 실패: {e}",
                details={"text_length": len(text)},
            )

    def embed_batch(
        self,
        texts: List[str],
        return_sparse: bool = False,
    ) -> Union[List[List[float]], Tuple[List[List[float]], List[Dict[str, float]]]]:
        """배치 텍스트 임베딩 생성

        대량 텍스트를 효율적으로 임베딩합니다. Redis 캐시를 활용하여
        이미 임베딩된 텍스트는 재계산하지 않습니다.

        Args:
            texts: 임베딩할 텍스트 리스트
            return_sparse: True이면 (dense, sparse) 튜플 반환

        Returns:
            Dense 벡터 리스트, 또는 (dense, sparse) 튜플

        Raises:
            EmbeddingError: 임베딩 생성 실패 시
        """
        if not texts:
            return ([], []) if return_sparse else []

        start_time = time.time()
        texts = self._validate_texts(texts)

        # 캐시 배치 조회
        miss_indices: List[int] = list(range(len(texts)))

        # Sparse 요청 시: Dense + Sparse 함께 캐시 조회
        cache_results_sparse: Optional[
            List[Optional[Tuple[List[float], Dict[str, float]]]]
        ] = None
        # Dense-only 요청 시: Dense만 캐시 조회
        cache_results_dense: Optional[List[Optional[List[float]]]] = None

        if self._cache and return_sparse:
            cache_results_sparse, miss_indices = self._cache.get_batch_with_sparse(
                texts, self.model_name
            )
            if not miss_indices:
                # 전체 캐시 히트 — Dense + Sparse 분리 반환
                cached_dense = [r[0] for r in cache_results_sparse]  # type: ignore[index]
                cached_sparse = [r[1] for r in cache_results_sparse]  # type: ignore[index]
                logger.debug(
                    "Full cache hit (sparse) for batch of %d texts (%.3fs)",
                    len(texts),
                    time.time() - start_time,
                )
                return cached_dense, cached_sparse
        elif self._cache and not return_sparse:
            cache_results_dense, miss_indices = self._cache.get_batch(
                texts, self.model_name
            )
            if not miss_indices:
                logger.debug(
                    "Full cache hit for batch of %d texts (%.3fs)",
                    len(texts),
                    time.time() - start_time,
                )
                return cache_results_dense  # type: ignore[return-value]

        # 캐시 미스 텍스트만 임베딩 생성
        miss_texts = [texts[i] for i in miss_indices]

        try:
            dense_vectors, sparse_vectors = self._encode_texts(
                miss_texts, return_sparse=return_sparse
            )
        except Exception as e:
            raise EmbeddingError(
                message=f"배치 임베딩 생성 실패: {e}",
                details={"batch_size": len(texts), "miss_count": len(miss_indices)},
            )

        # 정규화
        if self.normalize:
            dense_vectors = self._normalize_vectors(dense_vectors)

        # 캐시 저장
        if self._cache and miss_texts:
            if return_sparse:
                self._cache.set_batch_with_sparse(
                    miss_texts, self.model_name, dense_vectors, sparse_vectors
                )
            else:
                self._cache.set_batch(miss_texts, self.model_name, dense_vectors)

        # 결과 조합 (캐시 히트 + 새 결과)
        if return_sparse and cache_results_sparse is not None:
            final_dense: List[List[float]] = []
            final_sparse: List[Dict[str, float]] = []
            new_idx = 0
            for i in range(len(texts)):
                if cache_results_sparse[i] is not None:
                    final_dense.append(cache_results_sparse[i][0])  # type: ignore[index]
                    final_sparse.append(cache_results_sparse[i][1])  # type: ignore[index]
                else:
                    final_dense.append(dense_vectors[new_idx])
                    final_sparse.append(sparse_vectors[new_idx])
                    new_idx += 1
            dense_vectors = final_dense
            sparse_vectors = final_sparse
        elif not return_sparse and cache_results_dense is not None:
            final_dense_only: List[List[float]] = []
            new_idx = 0
            for i in range(len(texts)):
                if cache_results_dense[i] is not None:
                    final_dense_only.append(cache_results_dense[i])  # type: ignore[arg-type]
                else:
                    final_dense_only.append(dense_vectors[new_idx])
                    new_idx += 1
            dense_vectors = final_dense_only

        elapsed = time.time() - start_time
        has_cache = cache_results_sparse is not None or cache_results_dense is not None
        cache_hits = len(texts) - len(miss_indices) if has_cache else 0
        logger.info(
            "Batch embed completed: total=%d, cache_hits=%d, computed=%d, "
            "sparse=%s, elapsed=%.3fs, rate=%.1f texts/s",
            len(texts),
            cache_hits,
            len(miss_indices),
            return_sparse,
            elapsed,
            len(texts) / elapsed if elapsed > 0 else 0,
        )

        if return_sparse:
            return dense_vectors, sparse_vectors
        return dense_vectors

    def _encode_texts(
        self,
        texts: List[str],
        return_sparse: bool = False,
    ) -> Tuple[List[List[float]], List[Dict[str, float]]]:
        """실제 모델 호출로 텍스트 인코딩

        내부적으로 batch_size 단위로 분할하여 처리합니다.

        Args:
            texts: 인코딩할 텍스트 리스트
            return_sparse: Sparse 벡터 반환 여부

        Returns:
            (dense_vectors, sparse_vectors) 튜플
        """
        if self._model_type == "flag_embedding" or self._model_type is None:
            try:
                return self._encode_flag_embedding(texts, return_sparse)
            except Exception as e:
                if self._model_type == "flag_embedding":
                    raise
                logger.debug("FlagEmbedding encode failed: %s", e)

        # sentence-transformers 폴백
        return self._encode_sentence_transformers(texts, return_sparse)

    def _encode_flag_embedding(
        self,
        texts: List[str],
        return_sparse: bool = False,
    ) -> Tuple[List[List[float]], List[Dict[str, float]]]:
        """FlagEmbedding 기반 인코딩

        Args:
            texts: 텍스트 리스트
            return_sparse: Sparse 벡터 반환 여부

        Returns:
            (dense_vectors, sparse_vectors) 튜플
        """
        result = self.model.encode(
            texts,
            batch_size=self.batch_size,
            max_length=self.max_length,
            return_dense=True,
            return_sparse=return_sparse,
            return_colbert_vecs=False,
        )
        dense = result["dense_vecs"].tolist()
        sparse = []
        if return_sparse:
            sparse = result.get("lexical_weights", [{} for _ in texts])
        return dense, sparse

    def _encode_sentence_transformers(
        self,
        texts: List[str],
        return_sparse: bool = False,
    ) -> Tuple[List[List[float]], List[Dict[str, float]]]:
        """sentence-transformers 기반 인코딩 (폴백)

        Args:
            texts: 텍스트 리스트
            return_sparse: Sparse 벡터 반환 여부 (미지원, 빈 dict 반환)

        Returns:
            (dense_vectors, sparse_vectors) 튜플
        """
        # normalize_embeddings=False: embed_batch에서 numpy로 일괄 정규화하므로
        # 여기서 중복 정규화하지 않음 (이중 정규화 방지)
        embeddings = self.model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=False,
            normalize_embeddings=False,
        )
        dense = embeddings.tolist()
        sparse = [{} for _ in texts] if return_sparse else []
        return dense, sparse

    def embed_chunks(
        self,
        chunk_ids: List[str],
        texts: List[str],
        return_sparse: bool = False,
    ) -> List[ChunkEmbedding]:
        """청크 리스트에 대한 임베딩 생성

        Args:
            chunk_ids: 청크 ID 리스트
            texts: 청크 텍스트 리스트
            return_sparse: Sparse 벡터 포함 여부

        Returns:
            ChunkEmbedding 리스트

        Raises:
            ValueError: chunk_ids와 texts 길이가 다를 경우
            EmbeddingError: 임베딩 생성 실패 시
        """
        if len(chunk_ids) != len(texts):
            raise ValueError(
                f"chunk_ids({len(chunk_ids)})와 texts({len(texts)}) 길이 불일치"
            )

        if return_sparse:
            dense_vectors, sparse_vectors = self.embed_batch(
                texts, return_sparse=True
            )
        else:
            dense_vectors = self.embed_batch(texts, return_sparse=False)
            sparse_vectors = [None] * len(texts)

        return [
            ChunkEmbedding(
                chunk_id=cid,
                dense_vector=vec,
                sparse_vector=svec,
                model_name=self.model_name,
            )
            for cid, vec, svec in zip(chunk_ids, dense_vectors, sparse_vectors)
        ]

    async def aembed(self, text: str) -> List[float]:
        """단일 텍스트 비동기 Dense 임베딩

        Args:
            text: 임베딩할 텍스트

        Returns:
            1024차원 float 벡터
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.embed, text)

    async def aembed_batch(
        self,
        texts: List[str],
        return_sparse: bool = False,
    ) -> Union[List[List[float]], Tuple[List[List[float]], List[Dict[str, float]]]]:
        """배치 텍스트 비동기 임베딩 생성

        Args:
            texts: 임베딩할 텍스트 리스트
            return_sparse: True이면 (dense, sparse) 튜플 반환

        Returns:
            Dense 벡터 리스트, 또는 (dense, sparse) 튜플
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self.embed_batch(texts, return_sparse=return_sparse)
        )

    async def aembed_chunks(
        self,
        chunk_ids: List[str],
        texts: List[str],
        return_sparse: bool = False,
    ) -> List[ChunkEmbedding]:
        """청크 리스트에 대한 비동기 임베딩 생성

        Args:
            chunk_ids: 청크 ID 리스트
            texts: 청크 텍스트 리스트
            return_sparse: Sparse 벡터 포함 여부

        Returns:
            ChunkEmbedding 리스트
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.embed_chunks(chunk_ids, texts, return_sparse=return_sparse),
        )

    @property
    def vector_dimension(self) -> int:
        """임베딩 벡터 차원 수 (BGE-M3: 1024)"""
        return self.VECTOR_DIMENSION

    @property
    def is_model_loaded(self) -> bool:
        """모델 로드 여부"""
        return self._model is not None

    @property
    def cache_stats(self) -> Dict[str, Any]:
        """캐시 통계 정보

        Returns:
            캐시 상태 딕셔너리
        """
        if self._cache:
            return self._cache.stats
        return {"available": False, "reason": "cache disabled"}

    def health_check(self) -> Dict[str, Any]:
        """서비스 상태 점검

        Returns:
            상태 정보 딕셔너리
        """
        return {
            "service": "EmbeddingService",
            "model_name": self.model_name,
            "model_loaded": self.is_model_loaded,
            "model_type": self._model_type,
            "device": self.device,
            "vector_dimension": self.vector_dimension,
            "batch_size": self.batch_size,
            "normalize": self.normalize,
            "cache": self.cache_stats,
        }


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------

_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service(**kwargs: Any) -> EmbeddingService:
    """EmbeddingService 싱글톤 팩토리

    처음 호출 시 인스턴스를 생성하고, 이후에는 동일 인스턴스를 반환합니다.

    Args:
        **kwargs: EmbeddingService 생성자 인자

    Returns:
        EmbeddingService 인스턴스 (싱글톤)
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService(**kwargs)
    return _embedding_service


def reset_embedding_service() -> None:
    """싱글톤 인스턴스 초기화 (테스트용)"""
    global _embedding_service
    _embedding_service = None
