"""
비즈니스 서비스 모듈

도메인 로직 및 외부 서비스 연동
- llm_service: LLM 호출 관리 (DeepSeek V3.2)
- storage: 파일 스토리지 (MinIO / 로컬 폴백)
- search: 통합 검색 서비스 (Hybrid/Semantic/Keyword)
- rag_pipeline: RAG 파이프라인 (Retrieval-Augmentation-Generation)
- entity_extraction: 엔티티/관계 추출 + Gleaning
- embedding: BGE-M3 임베딩 서비스 (Dense + Sparse)
- rrf_fusion: RRF (Reciprocal Rank Fusion) 알고리즘
"""

from app.services.llm_service import LLMService
from app.services.storage import delete_file, get_file_url, upload_file
from app.services.search import SearchService, get_search_service
from app.services.rag_pipeline import RAGPipeline, get_rag_pipeline
from app.services.entity_extraction import EntityExtractionService, get_entity_extraction_service
from app.services.embedding import (
    ChunkEmbedding,
    EmbeddingCache,
    EmbeddingService,
    get_embedding_service,
    reset_embedding_service,
)
from app.services.rrf_fusion import (
    RRFFusion,
    RRFResult,
    RRFFusionExplanation,
    get_rrf_fusion,
    reset_rrf_fusion,
)

__all__ = [
    # LLM
    "LLMService",
    # Storage
    "upload_file",
    "get_file_url",
    "delete_file",
    # Search
    "SearchService",
    "get_search_service",
    # RAG Pipeline
    "RAGPipeline",
    "get_rag_pipeline",
    # Entity Extraction
    "EntityExtractionService",
    "get_entity_extraction_service",
    # Embedding
    "ChunkEmbedding",
    "EmbeddingCache",
    "EmbeddingService",
    "get_embedding_service",
    "reset_embedding_service",
    # RRF Fusion
    "RRFFusion",
    "RRFResult",
    "RRFFusionExplanation",
    "get_rrf_fusion",
    "reset_rrf_fusion",
]
