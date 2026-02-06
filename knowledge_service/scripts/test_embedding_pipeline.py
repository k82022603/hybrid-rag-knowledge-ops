#!/usr/bin/env python3
"""
임베딩 파이프라인 테스트 스크립트

문서 처리 파이프라인을 로컬에서 테스트합니다.

Usage:
    cd knowledge_service
    python scripts/test_embedding_pipeline.py
"""

import asyncio
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

# 환경변수 설정
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("ELASTICSEARCH_HOST", "localhost")
os.environ.setdefault("ELASTICSEARCH_PORT", "9200")
os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("NEO4J_USER", "neo4j")
os.environ.setdefault("NEO4J_PASSWORD", "password")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")


async def test_pipeline():
    """파이프라인 테스트 실행"""
    from app.services.document_processing_pipeline import (
        DocumentProcessingPipeline,
        ProcessingResult,
        ProcessingStatus,
    )
    from app.models.document import DocumentFormat, DocumentStatus

    print("=" * 60)
    print("Document Processing Pipeline Test")
    print("=" * 60)

    # 테스트용 In-memory 문서 저장소
    document_store = {}

    # 테스트 문서 생성 (Markdown)
    doc_id = uuid4()
    test_content = """# Test Document

## Introduction

This is a test document for the embedding pipeline.
It contains information about knowledge management systems and AI technologies.

## Technologies

### Machine Learning

Machine learning is a subset of artificial intelligence that enables systems
to learn and improve from experience without being explicitly programmed.
Popular frameworks include:

- **TensorFlow**: Google's open-source ML framework
- **PyTorch**: Facebook's deep learning library
- **scikit-learn**: Simple and efficient tools for data analysis

### Natural Language Processing

NLP is a field of AI that focuses on the interaction between computers and humans
using natural language. Key techniques include:

1. Named Entity Recognition (NER)
2. Sentiment Analysis
3. Text Classification
4. Question Answering

## Knowledge Graphs

A knowledge graph represents information as a network of entities and their relationships.
They are used in:

- Search engines (Google Knowledge Graph)
- Recommendation systems
- Fraud detection

### GraphRAG

GraphRAG combines traditional RAG (Retrieval-Augmented Generation) with knowledge graphs
to provide more contextual and accurate answers.

Key components:
- Vector embeddings for semantic search
- Graph structures for relationship traversal
- LLM for answer generation

## Conclusion

The integration of ML, NLP, and knowledge graphs creates powerful systems
for intelligent document processing and knowledge retrieval.

---

*Document created for testing purposes*
"""

    # 임시 파일 생성
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".md",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write(test_content)
        temp_path = f.name

    try:
        # 문서 저장소에 등록
        document_store[doc_id] = {
            "document_id": doc_id,
            "filename": "test_document.md",
            "format": DocumentFormat.PDF,  # 실제로는 MD지만 호환성 테스트
            "size_bytes": len(test_content),
            "status": DocumentStatus.QUEUED,
            "progress_percent": 0,
            "error_message": None,
            "storage_path": temp_path,  # 로컬 파일 경로
            "metadata": {"title": "Test Document"},
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

        print(f"\nTest document created: {doc_id}")
        print(f"Storage path: {temp_path}")
        print(f"Content length: {len(test_content)} characters")

        # 파이프라인 생성
        print("\n" + "-" * 60)
        print("Initializing pipeline...")

        pipeline = DocumentProcessingPipeline(
            document_store=document_store,
            enable_neo4j=False,  # Neo4j 연결 없이 테스트
            enable_entity_extraction=False,  # LLM 없이 테스트
        )

        # 문서 처리
        print("\n" + "-" * 60)
        print("Processing document...")

        result = await pipeline.process_document(doc_id)

        # 결과 출력
        print("\n" + "=" * 60)
        print("Processing Result")
        print("=" * 60)
        print(f"Document ID: {result.document_id}")
        print(f"Success: {result.success}")
        print(f"Status: {result.status}")
        print(f"Chunk Count: {result.chunk_count}")
        print(f"Entity Count: {result.entity_count}")
        print(f"Relationship Count: {result.relationship_count}")
        print(f"Processing Time: {result.processing_time_ms:.2f} ms")

        if result.error_message:
            print(f"Error: {result.error_message}")

        # 저장소 상태 확인
        print("\n" + "-" * 60)
        print("Document Store Status")
        print("-" * 60)
        doc = document_store[doc_id]
        print(f"Status: {doc.get('status')}")
        print(f"Progress: {doc.get('progress_percent')}%")
        print(f"Updated: {doc.get('updated_at')}")

        if doc.get("processing_metadata"):
            print(f"Processing Metadata: {doc.get('processing_metadata')}")

        # 파이프라인 정리
        await pipeline.close()

        print("\n" + "=" * 60)
        print("Test completed!")
        print("=" * 60)

        return result.success

    finally:
        # 임시 파일 삭제
        try:
            os.unlink(temp_path)
        except Exception:
            pass


async def test_chunking_only():
    """청킹만 테스트"""
    from app.etl.chunker import SemanticChunker
    from app.models.parsed_document import ParsedDocument

    print("\n" + "=" * 60)
    print("Chunking Test")
    print("=" * 60)

    # 테스트 문서
    content = """# Knowledge Management System

## Overview

A knowledge management system (KMS) is a system for managing knowledge and information.
It provides mechanisms to capture, store, and share organizational knowledge.

## Key Features

1. **Document Storage**: Central repository for all documents
2. **Search**: Full-text and semantic search capabilities
3. **Categorization**: Automatic classification of documents
4. **Access Control**: Role-based permissions

## Implementation

The system uses the following technologies:
- Elasticsearch for search
- Neo4j for knowledge graphs
- PostgreSQL for metadata
- MinIO for file storage
"""

    # ParsedDocument 생성
    parsed_doc = ParsedDocument(
        id=uuid4(),
        file_path="test.md",
        content=content,
    )

    # 청커 초기화
    chunker = SemanticChunker(
        chunk_size=300,
        chunk_overlap=50,
        min_chunk_size=50,
        max_chunk_size=600,
    )

    # 청킹 수행
    result = chunker.chunk_document(parsed_doc)

    print(f"Total chunks: {result.total_chunks}")
    print(f"Average tokens: {result.avg_token_count:.1f}")
    print(f"Processing time: {result.processing_time_ms:.2f} ms")

    print("\nChunks:")
    for i, chunk in enumerate(result.chunks):
        print(f"\n--- Chunk {i+1} ---")
        print(f"ID: {chunk.id}")
        print(f"Index: {chunk.chunk_index}")
        print(f"Tokens: {chunk.token_count}")
        print(f"Heading: {chunk.heading}")
        print(f"Content preview: {chunk.content[:100]}...")


async def test_embedding_service():
    """임베딩 서비스 테스트"""
    print("\n" + "=" * 60)
    print("Embedding Service Test")
    print("=" * 60)

    try:
        from app.services.embedding import EmbeddingService

        print("Initializing embedding service...")
        service = EmbeddingService(
            model_name="BAAI/bge-m3",
            cache_enabled=False,  # 캐시 비활성화
        )

        # 테스트 텍스트
        texts = [
            "Knowledge management systems help organizations store and retrieve information.",
            "Machine learning enables computers to learn from data.",
            "GraphRAG combines retrieval with knowledge graphs for better answers.",
        ]

        print(f"\nGenerating embeddings for {len(texts)} texts...")

        # 임베딩 생성
        embeddings = service.embed_batch(texts)

        print(f"Generated {len(embeddings)} embeddings")
        print(f"Vector dimension: {len(embeddings[0])}")

        # 첫 번째 벡터 샘플 출력
        print(f"\nFirst vector sample (first 10 dims): {embeddings[0][:10]}")

        # 코사인 유사도 테스트
        import math

        def cosine_similarity(v1, v2):
            dot = sum(a * b for a, b in zip(v1, v2))
            norm1 = math.sqrt(sum(a * a for a in v1))
            norm2 = math.sqrt(sum(b * b for b in v2))
            return dot / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0

        print("\nCosine Similarities:")
        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                sim = cosine_similarity(embeddings[i], embeddings[j])
                print(f"  [{i}] vs [{j}]: {sim:.4f}")

        print("\nEmbedding service test passed!")
        return True

    except Exception as e:
        print(f"\nEmbedding service test failed: {e}")
        print("Note: This test requires FlagEmbedding or sentence-transformers")
        return False


if __name__ == "__main__":
    print("\n" + "#" * 60)
    print("#" + " " * 58 + "#")
    print("#" + "  Document Processing Pipeline Test Suite".center(58) + "#")
    print("#" + " " * 58 + "#")
    print("#" * 60 + "\n")

    # 테스트 실행
    asyncio.run(test_chunking_only())

    # 임베딩 서비스 테스트 (시간이 오래 걸릴 수 있음)
    # asyncio.run(test_embedding_service())

    # 전체 파이프라인 테스트 (Elasticsearch 연결 필요)
    # asyncio.run(test_pipeline())

    print("\n\nAll tests completed!")
