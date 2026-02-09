#!/usr/bin/env python3
"""
ES knowledge_chunks 인덱스에 임베딩 벡터 후속 추가 스크립트

Batch 3 적재 시 enable_embeddings=False로 저장된 chunks에
BGE-M3 (1024차원) dense vector를 추가합니다.

사용법:
    docker cp knowledge_service/scripts/add_embeddings_batch.py kp-ai-service:/app/
    docker exec kp-ai-service python3 /app/add_embeddings_batch.py --batch-size 32

특징:
    - ES scroll API로 분할 조회 (OOM 방지)
    - 기존 임베딩이 있는 chunk는 건너뜀
    - 배치 크기 조절 가능
    - 매 배치마다 진행률 및 메모리 사용량 로깅
    - 실패한 chunk는 건너뛰고 계속 진행
"""

import argparse
import asyncio
import os
import sys
import time

sys.path.insert(0, "/app")
os.chdir("/app")


def get_memory_gb() -> float:
    """cgroup memory 사용량 (GB) 반환"""
    try:
        with open("/sys/fs/cgroup/memory.current") as f:
            return int(f.read().strip()) / 1024**3
    except Exception:
        return 0.0


async def run(batch_size: int, scroll_size: int, dry_run: bool) -> None:
    from elasticsearch import AsyncElasticsearch

    es_url = os.getenv("ELASTICSEARCH_URL", "http://elasticsearch:9200")
    index_name = os.getenv("ELASTICSEARCH_INDEX", "knowledge_chunks")

    print(f"[CONFIG] ES={es_url}, index={index_name}")
    print(f"[CONFIG] batch_size={batch_size}, scroll_size={scroll_size}, dry_run={dry_run}")
    print(f"[MEMORY] {get_memory_gb():.1f}GB at start")

    # ------------------------------------------------------------------
    # Step 1: BGE-M3 모델 로드
    # ------------------------------------------------------------------
    print("[MODEL] Loading BGE-M3 embedding model...")
    model_start = time.monotonic()

    from app.services.embedding import EmbeddingService

    embedding_svc = EmbeddingService(cache_enabled=False)
    # 모델 지연 로딩 트리거
    _ = embedding_svc.model
    model_elapsed = time.monotonic() - model_start
    print(f"[MODEL] Loaded in {model_elapsed:.1f}s, device={embedding_svc.device}")
    print(f"[MEMORY] {get_memory_gb():.1f}GB after model load")

    # ------------------------------------------------------------------
    # Step 2: 임베딩 없는 chunk 수 확인
    # ------------------------------------------------------------------
    es = AsyncElasticsearch(es_url, request_timeout=60)

    try:
        # dense_vector 필드가 존재하지 않는 문서 쿼리
        count_query = {
            "query": {
                "bool": {
                    "must_not": [
                        {"exists": {"field": "dense_vector"}}
                    ]
                }
            }
        }

        count_resp = await es.count(index=index_name, body=count_query)
        total_missing = count_resp["count"]
        print(f"[SCAN] {total_missing} chunks without embeddings found")

        if total_missing == 0:
            print("[DONE] All chunks already have embeddings. Nothing to do.")
            return

        if dry_run:
            print(f"[DRY_RUN] Would process {total_missing} chunks. Exiting.")
            return

        # ------------------------------------------------------------------
        # Step 3: Scroll API로 분할 처리
        # ------------------------------------------------------------------
        # text 필드 또는 content 필드에서 텍스트 가져오기
        search_body = {
            "query": {
                "bool": {
                    "must_not": [
                        {"exists": {"field": "dense_vector"}}
                    ]
                }
            },
            "_source": ["text", "content", "chunk_id"],
            "sort": ["_doc"],
        }

        scroll_resp = await es.search(
            index=index_name,
            body=search_body,
            scroll="5m",
            size=scroll_size,
        )

        scroll_id = scroll_resp["_scroll_id"]
        hits = scroll_resp["hits"]["hits"]

        processed = 0
        updated = 0
        failed = 0
        total_start = time.monotonic()

        while hits:
            # 배치 단위로 나누어 처리
            for batch_start in range(0, len(hits), batch_size):
                batch_hits = hits[batch_start:batch_start + batch_size]

                # 텍스트와 ID 추출
                chunk_ids = []
                texts = []
                es_doc_ids = []

                for hit in batch_hits:
                    source = hit["_source"]
                    doc_id = hit["_id"]
                    # text 필드 우선, 없으면 content 필드
                    text = source.get("text") or source.get("content") or ""

                    if not text.strip():
                        print(f"  [WARN] Empty text for chunk {doc_id}, skipping")
                        failed += 1
                        continue

                    chunk_ids.append(source.get("chunk_id", doc_id))
                    texts.append(text)
                    es_doc_ids.append(doc_id)

                if not texts:
                    continue

                # 임베딩 생성
                try:
                    dense_vectors = embedding_svc.embed_batch(texts, return_sparse=False)
                except Exception as e:
                    print(f"  [ERROR] Embedding failed for batch: {e}")
                    failed += len(texts)
                    continue

                # ES bulk update
                bulk_body = []
                for doc_id, vector in zip(es_doc_ids, dense_vectors):
                    bulk_body.append({"update": {"_index": index_name, "_id": doc_id}})
                    bulk_body.append({"doc": {"dense_vector": vector}})

                try:
                    bulk_resp = await es.bulk(operations=bulk_body, refresh=False)
                    if bulk_resp.get("errors"):
                        for item in bulk_resp["items"]:
                            if "error" in item.get("update", {}):
                                err = item["update"]["error"]
                                print(f"  [ERROR] Update failed: {err.get('reason', err)}")
                                failed += 1
                            else:
                                updated += 1
                    else:
                        updated += len(es_doc_ids)
                except Exception as e:
                    print(f"  [ERROR] Bulk update failed: {e}")
                    failed += len(es_doc_ids)
                    continue

                processed += len(batch_hits)

                # 진행률 로깅
                pct = (processed / total_missing * 100) if total_missing > 0 else 100
                elapsed = time.monotonic() - total_start
                rate = processed / elapsed if elapsed > 0 else 0
                mem_gb = get_memory_gb()
                print(
                    f"  [PROGRESS] {processed}/{total_missing} ({pct:.1f}%) | "
                    f"updated={updated} failed={failed} | "
                    f"{rate:.1f} chunks/s | mem={mem_gb:.1f}GB"
                )

            # 다음 scroll 페이지
            scroll_resp = await es.scroll(scroll_id=scroll_id, scroll="5m")
            scroll_id = scroll_resp["_scroll_id"]
            hits = scroll_resp["hits"]["hits"]

        # scroll 정리
        try:
            await es.clear_scroll(scroll_id=scroll_id)
        except Exception:
            pass

        # ------------------------------------------------------------------
        # Step 4: 결과 요약
        # ------------------------------------------------------------------
        total_elapsed = time.monotonic() - total_start
        print()
        print("=" * 60)
        print(f"[RESULT] Embedding batch completed")
        print(f"  Total chunks:   {total_missing}")
        print(f"  Updated:        {updated}")
        print(f"  Failed:         {failed}")
        print(f"  Elapsed:        {total_elapsed:.1f}s")
        print(f"  Rate:           {updated / total_elapsed:.1f} chunks/s" if total_elapsed > 0 else "")
        print(f"  Memory:         {get_memory_gb():.1f}GB")
        print("=" * 60)

    finally:
        await es.close()


def main():
    parser = argparse.ArgumentParser(
        description="Add BGE-M3 embeddings to ES chunks that have no embedding"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Number of texts to embed at once (default: 32)",
    )
    parser.add_argument(
        "--scroll-size",
        type=int,
        default=200,
        help="ES scroll page size (default: 200)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only count chunks, do not process",
    )
    args = parser.parse_args()

    asyncio.run(run(
        batch_size=args.batch_size,
        scroll_size=args.scroll_size,
        dry_run=args.dry_run,
    ))


if __name__ == "__main__":
    main()
