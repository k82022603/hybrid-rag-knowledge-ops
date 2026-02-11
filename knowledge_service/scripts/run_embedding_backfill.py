#!/usr/bin/env python3
"""
임베딩 배치 후처리 (Phase 3)

ES에서 dense_vector 없는 청크를 조회 → BGE-M3 임베딩 생성 → ES bulk update.
Redis 캐시 활용, 단일 프로세스 최대 throughput.

최적화:
- ES scroll API로 메모리 효율적 조회
- batch_size=32 (CPU BGE-M3 최적)
- max_text_length=1000 (CPU OOM 방지)
- Redis 캐시 (동일 텍스트 재계산 방지)
- 진행률 /tmp/etl_progress.json 저장
"""

import json
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, "/app/src")
os.chdir("/app")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

from elasticsearch import Elasticsearch, helpers
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)

PROGRESS_FILE = "/tmp/etl_progress.json"
ES_INDEX = "knowledge_chunks"
EMBED_BATCH = 32          # 모델 배치 사이즈
ES_SCROLL_SIZE = 200      # ES scroll 한 번에 가져올 문서 수
MAX_TEXT_LEN = 1000        # CPU OOM 방지

_progress = {
    "phase": "phase3-embedding",
    "status": "initializing",
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


def main():
    start_time = time.monotonic()
    _progress["started_at"] = datetime.now().isoformat()
    _progress["status"] = "running"

    print("=" * 60)
    print(f"Embedding Backfill (Phase 3) Started")
    print(f"Model: BGE-M3, Batch: {EMBED_BATCH}, MaxLen: {MAX_TEXT_LEN}")
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

    # 임베딩 서비스 초기화
    from app.services.embedding import EmbeddingService
    embed_svc = EmbeddingService(batch_size=EMBED_BATCH, max_length=MAX_TEXT_LEN)
    # 모델 미리 로드
    _ = embed_svc.model
    print(f"Model loaded: {embed_svc.model_name}, dim={embed_svc.vector_dimension}")
    save_progress(start_time)

    # ES scroll로 임베딩 없는 청크 순회
    scroll_body = {
        "query": {"bool": {"must_not": [{"exists": {"field": "dense_vector"}}]}},
        "_source": ["chunk_id", "text"],
        "sort": ["_doc"],
    }

    batch_texts = []
    batch_ids = []     # ES _id
    batch_chunk_ids = []
    total_embedded = 0
    total_cache_hits = 0
    total_errors = 0
    batch_count = 0

    print(f"\nStarting scroll (batch={ES_SCROLL_SIZE})...\n")

    for doc in helpers.scan(
        es,
        index=ES_INDEX,
        query=scroll_body,
        scroll="10m",
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

        # 텍스트 절단
        if len(text) > MAX_TEXT_LEN:
            text = text[:MAX_TEXT_LEN]

        batch_texts.append(text)
        batch_ids.append(es_id)
        batch_chunk_ids.append(chunk_id)

        # 배치가 찼으면 임베딩 생성 + ES 업데이트
        if len(batch_texts) >= EMBED_BATCH:
            try:
                dense_vectors = embed_svc.embed_batch(batch_texts, return_sparse=False)

                # ES bulk update
                actions = []
                for i, vec in enumerate(dense_vectors):
                    actions.append({
                        "_op_type": "update",
                        "_index": ES_INDEX,
                        "_id": batch_ids[i],
                        "doc": {"dense_vector": vec},
                    })
                helpers.bulk(es, actions, request_timeout=60)

                total_embedded += len(batch_texts)
                batch_count += 1

            except Exception as e:
                logger.error("Batch embedding failed: %s", e)
                total_errors += len(batch_texts)

            # 진행률 출력
            _progress["embedded"] = total_embedded
            _progress["errors"] = total_errors
            if batch_count % 5 == 0:
                save_progress(start_time)
                elapsed = time.monotonic() - start_time
                rate = total_embedded / elapsed if elapsed > 0 else 0
                remaining = total - total_embedded
                eta = remaining / rate / 60 if rate > 0 else 0
                print(
                    f"  [{total_embedded}/{total}] "
                    f"{total_embedded*100//total}% | "
                    f"{rate:.1f} texts/s | "
                    f"ETA: {eta:.0f}min | "
                    f"errors: {total_errors}",
                    flush=True,
                )

            batch_texts.clear()
            batch_ids.clear()
            batch_chunk_ids.clear()

    # 마지막 잔여 배치 처리
    if batch_texts:
        try:
            dense_vectors = embed_svc.embed_batch(batch_texts, return_sparse=False)
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
    print("Embedding Backfill Completed!")
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
