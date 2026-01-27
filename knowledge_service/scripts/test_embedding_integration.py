#!/usr/bin/env python3
"""EmbeddingService 통합 검증 스크립트

STORY-004: EmbeddingService 클래스를 통한 전체 파이프라인 검증
실행: PYTHONPATH=src python scripts/test_embedding_integration.py

사전 조건:
  pip install torch --index-url https://download.pytorch.org/whl/cpu
  pip install FlagEmbedding sentence-transformers numpy
"""

import asyncio
import math
import sys
import time


def test_embedding_service():
    """EmbeddingService 통합 테스트 (7개 체크)"""
    results = {"passed": 0, "failed": 0, "errors": []}

    print("=" * 60)
    print("EmbeddingService Integration Test")
    print("=" * 60)

    # 1. 서비스 초기화
    print("\n[1/7] 서비스 초기화...")
    try:
        from app.services.embedding import ChunkEmbedding, EmbeddingService

        svc = EmbeddingService()
        print(f"  OK: model={svc.model_name}, device={svc.device}")
        results["passed"] += 1
    except Exception as e:
        print(f"  FAIL: {e}")
        results["failed"] += 1
        results["errors"].append(f"Init: {e}")
        return False

    # 2. 단일 임베딩
    print("\n[2/7] 단일 임베딩 (embed)...")
    try:
        start = time.time()
        vec = svc.embed("Knowledge Graph 기반 지식 검색 시스템")
        elapsed = time.time() - start
        assert len(vec) == 1024, f"Expected 1024, got {len(vec)}"
        print(f"  OK: dim={len(vec)}, time={elapsed:.3f}s")
        results["passed"] += 1
    except Exception as e:
        print(f"  FAIL: {e}")
        results["failed"] += 1
        results["errors"].append(f"Single embed: {e}")

    # 3. 배치 임베딩
    print("\n[3/7] 배치 임베딩 (embed_batch)...")
    try:
        texts = [
            "한국어 문서 검색",
            "English document retrieval",
            "하이브리드 RAG 파이프라인",
            "Neo4j Knowledge Graph",
            "Elasticsearch 벡터 검색",
        ]
        start = time.time()
        vecs = svc.embed_batch(texts)
        elapsed = time.time() - start
        assert len(vecs) == 5
        assert all(len(v) == 1024 for v in vecs)
        print(f"  OK: {len(vecs)}건, dim={len(vecs[0])}, time={elapsed:.3f}s")
        results["passed"] += 1
    except Exception as e:
        print(f"  FAIL: {e}")
        results["failed"] += 1
        results["errors"].append(f"Batch embed: {e}")

    # 4. Sparse 임베딩
    print("\n[4/7] Sparse 임베딩 (return_sparse=True)...")
    try:
        dense, sparse = svc.embed_batch(["테스트 문서"], return_sparse=True)
        assert len(dense) == 1
        assert len(sparse) == 1
        sparse_type = type(sparse[0]).__name__
        sparse_len = len(sparse[0]) if isinstance(sparse[0], dict) else "N/A"
        print(f"  OK: dense={len(dense)}, sparse type={sparse_type}, tokens={sparse_len}")
        results["passed"] += 1
    except Exception as e:
        print(f"  FAIL: {e}")
        results["failed"] += 1
        results["errors"].append(f"Sparse embed: {e}")

    # 5. 청크 임베딩
    print("\n[5/7] 청크 임베딩 (embed_chunks)...")
    try:
        chunk_ids = ["chunk_001", "chunk_002", "chunk_003"]
        chunk_texts = [
            "첫 번째 청크: 시스템 아키텍처 개요",
            "두 번째 청크: 데이터 파이프라인 설명",
            "세 번째 청크: 검색 알고리즘 비교",
        ]
        results_chunks = svc.embed_chunks(chunk_ids, chunk_texts)
        assert len(results_chunks) == 3
        assert all(isinstance(r, ChunkEmbedding) for r in results_chunks)
        assert results_chunks[0].chunk_id == "chunk_001"
        assert len(results_chunks[0].dense_vector) == 1024
        print(f"  OK: {len(results_chunks)}건, model={results_chunks[0].model_name}")
        results["passed"] += 1
    except Exception as e:
        print(f"  FAIL: {e}")
        results["failed"] += 1
        results["errors"].append(f"Chunk embed: {e}")

    # 6. 비동기 임베딩
    print("\n[6/7] 비동기 임베딩 (aembed)...")
    try:

        async def async_test():
            vec = await svc.aembed("비동기 임베딩 테스트")
            return vec

        async_vec = asyncio.run(async_test())
        assert len(async_vec) == 1024
        print(f"  OK: dim={len(async_vec)}")
        results["passed"] += 1
    except Exception as e:
        print(f"  FAIL: {e}")
        results["failed"] += 1
        results["errors"].append(f"Async embed: {e}")

    # 7. L2 정규화 검증
    print("\n[7/7] L2 정규화 검증...")
    try:
        test_vec = svc.embed("정규화 테스트 문서")
        norm = math.sqrt(sum(x * x for x in test_vec))
        is_normalized = abs(norm - 1.0) < 0.01
        print(f"  L2 norm: {norm:.6f} {'(OK)' if is_normalized else '(WARN: not unit vector)'}")
        if is_normalized:
            results["passed"] += 1
        else:
            results["failed"] += 1
            results["errors"].append(f"Normalization: norm={norm:.6f}")
    except Exception as e:
        print(f"  FAIL: {e}")
        results["failed"] += 1
        results["errors"].append(f"Normalization: {e}")

    # 결과 요약
    total = results["passed"] + results["failed"]
    print("\n" + "=" * 60)
    if results["failed"] == 0:
        print(f"RESULT: ALL PASSED ({results['passed']}/{total})")
    else:
        print(f"RESULT: {results['failed']} FAILED ({results['passed']}/{total})")
        for err in results["errors"]:
            print(f"  - {err}")
    print("=" * 60)

    return results["failed"] == 0


if __name__ == "__main__":
    success = test_embedding_service()
    sys.exit(0 if success else 1)
