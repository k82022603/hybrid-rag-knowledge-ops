"""
BGE-M3 임베딩 서비스
STORY-004: BGE-M3 임베딩 생성
"""
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class ChunkEmbedding:
    """청크 임베딩 결과"""
    chunk_id: str
    dense_vector: List[float]
    sparse_vector: Optional[Dict[int, float]] = None
    model_name: str = "BAAI/bge-m3"
    created_at: datetime = field(default_factory=datetime.utcnow)


class EmbeddingService:
    """BGE-M3 기반 임베딩 서비스

    Features:
        - Dense 임베딩 (1024차원)
        - Sparse 임베딩 (Hybrid 검색용)
        - 배치 처리 지원
        - CPU/GPU 자동 감지
        - BGE-M3 / sentence-transformers 자동 폴백
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        use_fp16: bool = True,
        device: Optional[str] = None,
        batch_size: int = 32,
        max_length: int = 8192,
    ):
        self.model_name = model_name
        self.use_fp16 = use_fp16
        self.batch_size = batch_size
        self.max_length = max_length
        self._model = None
        self._model_type: Optional[str] = None

        if device is None:
            try:
                import torch
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                self.device = "cpu"
        else:
            self.device = device

        logger.info(
            "EmbeddingService initialized: model=%s, device=%s, fp16=%s",
            model_name, self.device, use_fp16,
        )

    @property
    def model(self):
        """모델 지연 로딩 (Lazy Loading)"""
        if self._model is None:
            self._load_model()
        return self._model

    def _load_model(self):
        """BGE-M3 모델 로드 (FlagEmbedding -> sentence-transformers 폴백)"""
        try:
            from FlagEmbedding import BGEM3FlagModel
            self._model = BGEM3FlagModel(
                self.model_name,
                use_fp16=self.use_fp16 and self.device != "cpu",
                device=self.device,
            )
            self._model_type = "flag_embedding"
            logger.info("BGE-M3 model loaded via FlagEmbedding on %s", self.device)
        except ImportError:
            logger.warning("FlagEmbedding not available, trying sentence-transformers")
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name, device=self.device)
                self._model_type = "sentence_transformers"
                logger.info("Model loaded via sentence-transformers: %s", self.model_name)
            except ImportError:
                raise ImportError(
                    "Neither FlagEmbedding nor sentence-transformers installed. "
                    "Run: pip install FlagEmbedding or pip install sentence-transformers"
                )

    def embed(self, text: str) -> List[float]:
        """단일 텍스트 Dense 임베딩

        Args:
            text: 임베딩할 텍스트

        Returns:
            1024차원 float 벡터
        """
        results = self.embed_batch([text])
        return results[0]

    def embed_batch(
        self,
        texts: List[str],
        return_sparse: bool = False,
    ) -> Any:
        """배치 텍스트 임베딩 생성

        Args:
            texts: 임베딩할 텍스트 리스트
            return_sparse: True이면 (dense, sparse) 튜플 반환

        Returns:
            Dense 벡터 리스트, 또는 (dense, sparse) 튜플
        """
        if not texts:
            return [] if not return_sparse else ([], [])

        if self._model_type == "flag_embedding" or self._model_type is None:
            try:
                result = self.model.encode(
                    texts,
                    batch_size=self.batch_size,
                    max_length=self.max_length,
                    return_dense=True,
                    return_sparse=return_sparse,
                    return_colbert_vecs=False,
                )
                dense = result["dense_vecs"].tolist()
                if return_sparse:
                    sparse = result.get("lexical_weights", [])
                    return dense, sparse
                return dense
            except Exception as e:
                if self._model_type == "flag_embedding":
                    raise
                logger.debug("FlagEmbedding encode failed: %s", e)

        # sentence-transformers fallback
        embeddings = self.model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        dense = embeddings.tolist()
        if return_sparse:
            return dense, [{} for _ in texts]
        return dense

    def embed_chunks(
        self,
        chunk_ids: List[str],
        texts: List[str],
    ) -> List[ChunkEmbedding]:
        """청크 리스트에 대한 임베딩 생성

        Args:
            chunk_ids: 청크 ID 리스트
            texts: 청크 텍스트 리스트

        Returns:
            ChunkEmbedding 리스트

        Raises:
            ValueError: chunk_ids와 texts 길이가 다를 경우
        """
        if len(chunk_ids) != len(texts):
            raise ValueError(
                f"chunk_ids({len(chunk_ids)})와 texts({len(texts)}) 길이 불일치"
            )

        vectors = self.embed_batch(texts)

        return [
            ChunkEmbedding(chunk_id=cid, dense_vector=vec, model_name=self.model_name)
            for cid, vec in zip(chunk_ids, vectors)
        ]

    @property
    def vector_dimension(self) -> int:
        """임베딩 벡터 차원 수 (BGE-M3: 1024)"""
        return 1024


_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service(**kwargs) -> EmbeddingService:
    """EmbeddingService 싱글톤 팩토리

    Args:
        **kwargs: EmbeddingService 생성자 인자

    Returns:
        EmbeddingService 인스턴스 (싱글톤)
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService(**kwargs)
    return _embedding_service
