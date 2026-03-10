"""
임베딩 생성/엔티티 추출 모듈

BGE-M3 임베딩 생성과 LLM 기반 엔티티 추출을 담당합니다.

Functions:
    generate_embeddings: 청크에 대한 벡터 임베딩 생성
    extract_entities: LLM 기반 엔티티 추출
"""

from typing import Any, List, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


async def generate_embeddings(
    embedding_service: Any,
    chunks: List[Any],
) -> Optional[List[Any]]:
    """청크에 대한 임베딩 생성

    BGE-M3 임베딩 서비스를 사용하여 벡터를 생성합니다.

    Args:
        embedding_service: EmbeddingService 인스턴스
        chunks: Chunk 객체 리스트

    Returns:
        ChunkEmbedding 리스트 또는 None
    """
    if not chunks:
        return None

    try:
        chunk_ids = [chunk.id for chunk in chunks]
        texts = [chunk.content for chunk in chunks]

        embeddings = await embedding_service.aembed_chunks(
            chunk_ids=chunk_ids,
            texts=texts,
            return_sparse=True,
        )

        logger.debug(
            "Generated embeddings: %d chunks, dimension=%d",
            len(embeddings),
            embedding_service.vector_dimension,
        )

        return embeddings

    except Exception as e:
        logger.error("Embedding generation failed: %s", e)
        raise


async def extract_entities(
    entity_extractor: Any,
    parsed_doc: Any,
) -> List[Any]:
    """엔티티 추출

    LLM 기반 엔티티 추출 서비스를 사용합니다.

    Args:
        entity_extractor: EntityExtractionService 인스턴스
        parsed_doc: 파싱된 문서

    Returns:
        Entity 리스트
    """
    if not parsed_doc or not parsed_doc.content:
        return []

    try:
        entities = await entity_extractor.extract_entities(
            text=parsed_doc.content,
            enable_gleaning=True,
        )

        logger.debug("Extracted %d entities", len(entities))
        return entities

    except Exception as e:
        logger.error("Entity extraction failed: %s", e)
        raise
