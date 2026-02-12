#!/usr/bin/env python3
"""
임베딩 배치 후처리 v2 (Phase 3 최적화)

최적화 내용:
1. OMP_NUM_THREADS=8 / MKL_NUM_THREADS=8 / TORCH_NUM_THREADS=8 (v2.1)
2. normalize_embeddings=False + numpy 벡터 정규화 (CPU 연산 절감)
3. torch.set_num_threads(8) 명시적 설정 (HyperThreading 활용)
4. 배치 내 텍스트 길이 정렬 (패딩 최소화)
5. ES _source 최소화, scroll timeout 증가

기준선 (v1): 0.7~1.7 t/s (torch 2스레드, Phase 2 병행)
v2 튜닝: swappiness=10 + 4스레드 (2026-02-12 15:00) → 0.8 t/s
v2.1 튜닝: 8스레드 (2026-02-12 16:30, Data Agent) → 0.85 t/s 목표
목표: 0.85+ t/s (71,876 chunks / 24.5 hours)
"""

import json
import os
import sys
import time
from datetime import datetime

# ── 최적화 #1: 환경변수 설정 (import 전에 해야 함) ──
# v2.1 튜닝: 4→8 스레드 (HyperThreading 활용, OOM 위험 8%, +6% 속도 예상)
# Data Agent 분석 (2026-02-12): i7-1360P (4P+HT=8L) GEMM 최적화
os.environ["OMP_NUM_THREADS"] = "8"
os.environ["MKL_NUM_THREADS"] = "8"
os.environ["TORCH_NUM_THREADS"] = "8"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

sys.path.insert(0, "/app/src")
os.chdir("/app")

# ── 최적화 #2: torch 스레드 명시 설정 ──
import torch
torch.set_num_threads(8)
torch.set_num_interop_threads(4)

import numpy as np
from elasticsearch import Elasticsearch, helpers
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)

PROGRESS_FILE = "/tmp/etl_progress.json"
ES_INDEX = "knowledge_chunks"
EMBED_BATCH = 32
ES_SCROLL_SIZE = 200
MAX_TEXT_LEN = 1000

_progress = {
    "phase": "phase3-embedding-v2.1",
    "status": "initializing",
    "version": "v2.1-hyperthreading",
    "optimizations": [
        "OMP_NUM_THREADS=8",
        "torch.set_num_threads(8)",
        "torch.set_num_interop_threads(4)",
        "numpy_normalize",
        "length_sorted_batches",
        "i7-1360P HyperThreading",
    ],
    "started_at": "",
    "total_chunks": 0,
    "embedded": 0,
    "cache_hits": 0,
    "errors": 0,
    "elapsed_seconds": 0,
    "rate_texts_per_sec": 0,
    "eta_minutes": 0,
}


def save_progress(start_time: float):
    elapsed = time.monotonic() - start_time
    _progress["elapsed_seconds"] = round(elapsed)
    if elapsed > 30 and _progress["embedded"] > 0:
        rate = _progress["embedded"] / elapsed
        _progress["rate_texts_per_sec"] = round(rate, 2)
        remaining = _progress["total_chunks"] - _progress["embedded"]
        _progress["eta_minutes"] = round(remaining / rate / 60) if rate > 0 else 0
    try:
        with open(PROGRESS_FILE, "w") as f:
            json.dump(_progress, f, ensure_ascii=False, indent=2, default=str)
    except Exception:
        pass


def numpy_normalize(vectors: np.ndarray) -> np.ndarray:
    """NumPy 벡터화 L2 정규화 (순수 Python 대비 10x+ 빠름)"""
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-12)  # division by zero 방지
    return vectors / norms


def main():
    start_time = time.monotonic()
    _progress["started_at"] = datetime.now().isoformat()
    _progress["status"] = "running"

    print("=" * 60)
    print(f"Embedding Backfill v2 (Optimized)")
    print(f"Model: BGE-M3, Batch: {EMBED_BATCH}, MaxLen: {MAX_TEXT_LEN}")
    print(f"torch.num_threads: {torch.get_num_threads()}")
    print(f"OMP_NUM_THREADS: {os.environ.get('OMP_NUM_THREADS', 'unset')}")
    print(f"MKL_NUM_THREADS: {os.environ.get('MKL_NUM_THREADS', 'unset')}")
    print("=" * 60)

    # ES 연결
    es = Elasticsearch(
        [f"http://{settings.elasticsearch_host}:{settings.elasticsearch_port}"],
        request_timeout=60,
    )
    info = es.info()
    print(f"ES connected: {info['version']['number']}")

    # 임베딩 없는 청크 수 확인
    count_resp = es.count(
        index=ES_INDEX,
        body={"query": {"bool": {"must_not": [{"exists": {"field": "dense_vector"}}]}}},
    )
    total = count_resp["count"]
    _progress["total_chunks"] = total
    print(f"Chunks without embedding: {total}")

    if total == 0:
        print("Nothing to embed!")
        _progress["status"] = "completed"
        save_progress(start_time)
        return

    # ── 최적화 #3: 임베딩 서비스 (normalize 비활성화) ──
    from app.services.embedding import EmbeddingService
    embed_svc = EmbeddingService(batch_size=EMBED_BATCH, max_length=MAX_TEXT_LEN)

    # normalize를 False로 변경 (numpy로 직접 처리)
    original_normalize = embed_svc.normalize
    embed_svc.normalize = False
    print(f"[OPT] normalize_embeddings: {original_normalize} → False (numpy 대체)")

    _ = embed_svc.model
    print(f"Model loaded: {embed_svc.model_name}, dim={embed_svc.vector_dimension}")
    print(f"torch.num_threads (after model load): {torch.get_num_threads()}")
    save_progress(start_time)

    # ES scroll
    scroll_body = {
        "query": {"bool": {"must_not": [{"exists": {"field": "dense_vector"}}]}},
        "_source": ["chunk_id", "text"],
        "sort": ["_doc"],
    }

    batch_texts = []
    batch_ids = []
    batch_chunk_ids = []
    total_embedded = 0
    total_cache_hits = 0
    total_errors = 0
    batch_count = 0

    # 속도 측정용 구간별 카운터
    interval_start = time.monotonic()
    interval_count = 0

    print(f"\nStarting scroll (batch={ES_SCROLL_SIZE})...\n")

    for doc in helpers.scan(
        es,
        index=ES_INDEX,
        query=scroll_body,
        scroll="30m",  # 최적화: 10m → 30m (안전 마진)
        size=ES_SCROLL_SIZE,
        request_timeout=120,
    ):
        es_id = doc["_id"]
        src = doc["_source"]
        text = src.get("text", "")
        chunk_id = src.get("chunk_id", es_id)

        if not text or not text.strip():
            total_errors += 1
            continue

        if len(text) > MAX_TEXT_LEN:
            text = text[:MAX_TEXT_LEN]

        batch_texts.append(text)
        batch_ids.append(es_id)
        batch_chunk_ids.append(chunk_id)

        if len(batch_texts) >= EMBED_BATCH:
            try:
                # ── 최적화 #4: 길이 정렬 (패딩 최소화) ──
                sorted_indices = sorted(range(len(batch_texts)), key=lambda i: len(batch_texts[i]))
                sorted_texts = [batch_texts[i] for i in sorted_indices]
                sorted_ids = [batch_ids[i] for i in sorted_indices]

                dense_vectors = embed_svc.embed_batch(sorted_texts, return_sparse=False)

                # ── 최적화 #3: numpy 정규화 ──
                if original_normalize and isinstance(dense_vectors, list):
                    arr = np.array(dense_vectors, dtype=np.float32)
                    arr = numpy_normalize(arr)
                    dense_vectors = arr.tolist()

                # 원래 순서로 복원
                restore = [None] * len(sorted_indices)
                for new_i, orig_i in enumerate(sorted_indices):
                    restore[orig_i] = dense_vectors[new_i]

                # ES bulk update
                actions = []
                for i, vec in enumerate(restore):
                    actions.append({
                        "_op_type": "update",
                        "_index": ES_INDEX,
                        "_id": batch_ids[i],
                        "doc": {"dense_vector": vec},
                    })
                helpers.bulk(es, actions, request_timeout=60)

                total_embedded += len(batch_texts)
                interval_count += len(batch_texts)
                batch_count += 1

            except Exception as e:
                logger.error("Batch embedding failed: %s", e)
                total_errors += len(batch_texts)

            _progress["embedded"] = total_embedded
            _progress["errors"] = total_errors

            if batch_count % 5 == 0:
                save_progress(start_time)
                elapsed = time.monotonic() - start_time
                rate_overall = total_embedded / elapsed if elapsed > 0 else 0

                # 구간 속도 (최근 5배치)
                interval_elapsed = time.monotonic() - interval_start
                rate_interval = interval_count / interval_elapsed if interval_elapsed > 0 else 0

                remaining = total - total_embedded
                eta = remaining / rate_overall / 60 if rate_overall > 0 else 0
                print(
                    f"  [{total_embedded}/{total}] "
                    f"{total_embedded*100//total}% | "
                    f"avg: {rate_overall:.1f} t/s | "
                    f"recent: {rate_interval:.1f} t/s | "
                    f"ETA: {eta:.0f}min | "
                    f"err: {total_errors}",
                    flush=True,
                )
                interval_start = time.monotonic()
                interval_count = 0

            batch_texts.clear()
            batch_ids.clear()
            batch_chunk_ids.clear()

    # 잔여 배치
    if batch_texts:
        try:
            dense_vectors = embed_svc.embed_batch(batch_texts, return_sparse=False)
            if original_normalize and isinstance(dense_vectors, list):
                arr = np.array(dense_vectors, dtype=np.float32)
                arr = numpy_normalize(arr)
                dense_vectors = arr.tolist()

            actions = [
                {
                    "_op_type": "update",
                    "_index": ES_INDEX,
                    "_id": batch_ids[i],
                    "doc": {"dense_vector": vec},
                }
                for i, vec in enumerate(dense_vectors)
            ]
            helpers.bulk(es, actions, request_timeout=60)
            total_embedded += len(batch_texts)
        except Exception as e:
            logger.error("Final batch failed: %s", e)
            total_errors += len(batch_texts)

    elapsed = time.monotonic() - start_time
    rate = total_embedded / elapsed if elapsed > 0 else 0

    _progress.update({
        "status": "completed",
        "completed_at": datetime.now().isoformat(),
        "embedded": total_embedded,
        "errors": total_errors,
        "elapsed_seconds": round(elapsed),
        "rate_texts_per_sec": round(rate, 2),
    })
    save_progress(start_time)

    print("\n" + "=" * 60)
    print("Embedding Backfill v2 Completed!")
    print("=" * 60)
    print(f"  Total:    {total}")
    print(f"  Embedded: {total_embedded}")
    print(f"  Errors:   {total_errors}")
    print(f"  Elapsed:  {int(elapsed)}s ({elapsed/60:.1f}m / {elapsed/3600:.1f}h)")
    print(f"  Rate:     {rate:.2f} texts/s")
    print(f"  Cache:    {embed_svc.cache_stats}")


if __name__ == "__main__":
    main()
    print(f"\nSaved: {PROGRESS_FILE}")
