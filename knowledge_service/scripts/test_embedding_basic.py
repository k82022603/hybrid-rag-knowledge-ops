#!/usr/bin/env python3
"""BGE-M3 임베딩 모델 기본 검증 스크립트

STORY-004: 실제 모델 로드 + 1024차원 벡터 생성 검증
실행: python scripts/test_embedding_basic.py

사전 조건:
  pip install torch --index-url https://download.pytorch.org/whl/cpu
  pip install FlagEmbedding sentence-transformers
"""

import math
import sys
import time


def cosine_similarity(a, b):
    """코사인 유사도 계산"""
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na > 0 and nb > 0 else 0


def test_basic_embedding():
    """1024차원 Dense 벡터 정상 생성 확인"""
    results = {"passed": 0, "failed": 0, "errors": []}

    print("=" * 60)
    print("BGE-M3 Embedding Model - Basic Verification")
    print("=" * 60)

    # Step 1: PyTorch 로드
    print("\n[1/5] PyTorch 로드...")
    try:
        import torch

        print(f"  OK: PyTorch {torch.__version__}")
        print(f"  CUDA: {'Yes' if torch.cuda.is_available() else 'No (CPU mode)'}")
        results["passed"] += 1
    except Exception as e:
        print(f"  FAIL: {e}")
        results["failed"] += 1
        results["errors"].append(f"PyTorch load: {e}")
        print("\n=== FAILED: PyTorch를 로드할 수 없습니다 ===")
        return False

    # Step 2: 모델 로드
    print("\n[2/5] BGE-M3 모델 로드 (첫 실행 시 ~1.5GB 다운로드)...")
    model = None
    model_type = None
    load_start = time.time()

    try:
        from FlagEmbedding import BGEM3FlagModel

        model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=False, device="cpu")
        model_type = "FlagEmbedding"
    except ImportError:
        print("  FlagEmbedding 미설치, sentence-transformers로 폴백...")
        try:
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer("BAAI/bge-m3", device="cpu")
            model_type = "sentence-transformers"
        except Exception as e:
            print(f"  FAIL: 모든 로드 방법 실패 - {e}")
            results["failed"] += 1
            return False
    except Exception as e:
        print(f"  FlagEmbedding 실패 ({e}), sentence-transformers로 폴백...")
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("BAAI/bge-m3", device="cpu")
        model_type = "sentence-transformers"

    load_time = time.time() - load_start
    print(f"  OK: {model_type} ({load_time:.1f}s)")
    results["passed"] += 1

    # Step 3: 단일 텍스트 임베딩
    print("\n[3/5] 단일 텍스트 임베딩...")
    test_text = "Knowledge Graph 기반 하이브리드 RAG 검색 시스템의 아키텍처를 설명합니다."
    embed_start = time.time()

    try:
        if model_type == "FlagEmbedding":
            result = model.encode(
                [test_text],
                return_dense=True,
                return_sparse=False,
                return_colbert_vecs=False,
            )
            vector = result["dense_vecs"][0].tolist()
        else:
            vector = model.encode([test_text], normalize_embeddings=True)[0].tolist()

        embed_time = time.time() - embed_start
        dim = len(vector)
        norm = math.sqrt(sum(x * x for x in vector))

        print(f"  차원: {dim} {'(OK)' if dim == 1024 else '(FAIL: expected 1024)'}")
        print(f"  L2 norm: {norm:.6f} {'(OK)' if abs(norm - 1.0) < 0.05 else '(WARN)'}")
        print(f"  앞 5개: [{', '.join(f'{v:.4f}' for v in vector[:5])}]")
        print(f"  소요: {embed_time:.3f}s")

        if dim == 1024:
            results["passed"] += 1
        else:
            results["failed"] += 1
            results["errors"].append(f"Dimension: expected 1024, got {dim}")
    except Exception as e:
        print(f"  FAIL: {e}")
        results["failed"] += 1
        results["errors"].append(f"Single embed: {e}")

    # Step 4: 다국어 + 유사도
    print("\n[4/5] 다국어 임베딩 + 유사도...")
    multilingual_texts = [
        "한국어 문서 검색 시스템",
        "English document search system",
        "Knowledge Graph와 Vector Search의 하이브리드 접근",
    ]

    try:
        if model_type == "FlagEmbedding":
            result = model.encode(
                multilingual_texts,
                return_dense=True,
                return_sparse=False,
                return_colbert_vecs=False,
            )
            vectors = result["dense_vecs"].tolist()
        else:
            vectors = model.encode(multilingual_texts, normalize_embeddings=True).tolist()

        for i, (text, vec) in enumerate(zip(multilingual_texts, vectors)):
            print(f"  [{i + 1}] '{text[:30]}' -> dim={len(vec)}")

        sim_ko_en = cosine_similarity(vectors[0], vectors[1])
        sim_ko_hybrid = cosine_similarity(vectors[0], vectors[2])
        print(f"  한국어<->영어 유사도: {sim_ko_en:.4f} (같은 의미 -> 0.7+ 기대)")
        print(f"  한국어<->하이브리드: {sim_ko_hybrid:.4f}")

        if sim_ko_en > 0.5:
            results["passed"] += 1
        else:
            results["failed"] += 1
            results["errors"].append(f"Cross-lingual similarity too low: {sim_ko_en:.4f}")
    except Exception as e:
        print(f"  FAIL: {e}")
        results["failed"] += 1
        results["errors"].append(f"Multilingual: {e}")

    # Step 5: 배치 성능
    print("\n[5/5] 배치 성능 (32건)...")
    batch_texts = [f"테스트 문서 번호 {i}: 지식 그래프 검색" for i in range(32)]

    try:
        batch_start = time.time()
        if model_type == "FlagEmbedding":
            result = model.encode(
                batch_texts,
                batch_size=16,
                return_dense=True,
                return_sparse=False,
                return_colbert_vecs=False,
            )
            batch_vecs = result["dense_vecs"].tolist()
        else:
            batch_vecs = model.encode(
                batch_texts, batch_size=16, normalize_embeddings=True
            ).tolist()

        batch_time = time.time() - batch_start
        print(f"  32건: {batch_time:.3f}s ({32 / batch_time:.1f} texts/s)")
        print(f"  shape: ({len(batch_vecs)}, {len(batch_vecs[0])})")

        if len(batch_vecs) == 32 and len(batch_vecs[0]) == 1024:
            results["passed"] += 1
        else:
            results["failed"] += 1
    except Exception as e:
        print(f"  FAIL: {e}")
        results["failed"] += 1
        results["errors"].append(f"Batch: {e}")

    # 결과 요약
    total = results["passed"] + results["failed"]
    print("\n" + "=" * 60)
    if results["failed"] == 0:
        print(f"RESULT: ALL PASSED ({results['passed']}/{total})")
    else:
        print(f"RESULT: {results['failed']} FAILED ({results['passed']}/{total})")
        for err in results["errors"]:
            print(f"  - {err}")
    print(f"  Model: {model_type} (BAAI/bge-m3)")
    print(f"  Load: {load_time:.1f}s")
    print("=" * 60)

    return results["failed"] == 0


if __name__ == "__main__":
    success = test_basic_embedding()
    sys.exit(0 if success else 1)
