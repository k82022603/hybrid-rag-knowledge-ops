"""
BGE-M3 임베딩 모듈

Multilingual Dense + Sparse 벡터 생성
"""

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class Embedder:
    """
    BGE-M3 임베딩 생성기

    Dense 벡터 (1024차원)와 Sparse 벡터를 동시에 생성합니다.
    """

    def __init__(self):
        """초기화"""
        self._model: Optional[Any] = None
        self._tokenizer: Optional[Any] = None

    @property
    def is_loaded(self) -> bool:
        """모델 로딩 여부"""
        return self._model is not None

    async def load_model(self) -> None:
        """
        BGE-M3 모델 로딩

        CPU 환경에서 16GB RAM 제약을 고려하여 lazy loading 구현
        """
        if self._model is not None:
            return

        logger.info(f"Loading embedding model: {settings.embedding_model}")

        # TODO: 실제 모델 로딩 구현
        # from sentence_transformers import SentenceTransformer
        # self._model = SentenceTransformer(settings.embedding_model)

        logger.info("Embedding model loaded")

    async def embed(self, text: str) -> np.ndarray:
        """
        단일 텍스트 임베딩 생성

        Args:
            text: 임베딩할 텍스트

        Returns:
            Dense 벡터 (1024차원)
        """
        if not self.is_loaded:
            await self.load_model()

        # TODO: 실제 임베딩 생성 구현
        # return self._model.encode(text, normalize_embeddings=True)

        # 스켈레톤: 더미 벡터 반환
        return np.zeros(settings.embedding_dimension, dtype=np.float32)

    async def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 32,
    ) -> List[np.ndarray]:
        """
        배치 임베딩 생성

        Args:
            texts: 임베딩할 텍스트 목록
            batch_size: 배치 크기

        Returns:
            Dense 벡터 목록
        """
        if not self.is_loaded:
            await self.load_model()

        logger.info(f"Embedding batch of {len(texts)} texts")

        # TODO: 실제 배치 임베딩 구현
        # return self._model.encode(
        #     texts,
        #     batch_size=batch_size,
        #     normalize_embeddings=True,
        #     show_progress_bar=True,
        # )

        # 스켈레톤: 더미 벡터 목록 반환
        return [
            np.zeros(settings.embedding_dimension, dtype=np.float32)
            for _ in texts
        ]

    async def embed_hybrid(
        self,
        text: str,
    ) -> Tuple[np.ndarray, Dict[str, float]]:
        """
        Hybrid 임베딩 생성 (Dense + Sparse)

        Args:
            text: 임베딩할 텍스트

        Returns:
            (Dense 벡터, Sparse 벡터 딕셔너리)
        """
        dense = await self.embed(text)

        # TODO: Sparse 벡터 생성 (BM25 또는 SPLADE)
        sparse: Dict[str, float] = {}

        return dense, sparse


# 싱글톤 인스턴스
_embedder: Optional[Embedder] = None


def get_embedder() -> Embedder:
    """Embedder 인스턴스 반환"""
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder
