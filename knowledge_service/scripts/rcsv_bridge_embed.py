#!/usr/bin/env python3
"""
RCSV Bridge: HRKP 청크를 OpenAI 임베딩으로 변환하여 RCSV ES 인덱스에 적재

Docker 컨테이너 내부에서 실행:
    docker exec kp-ai-service python3 /app/scripts/rcsv_bridge_embed.py

동작:
1. knowledge_chunks 인덱스에서 전체 청크 텍스트 추출
2. OpenAI text-embedding-3-small (1536d)로 임베딩
3. rcsv-pdf-documents 인덱스에 적재
"""

import json
import os
import sys
import time
from typing import Any, Dict, List

import requests
from elasticsearch import Elasticsearch, helpers

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
ES_URL = os.getenv("ELASTICSEARCH_URL", "http://elasticsearch:9200")
SOURCE_INDEX = "knowledge_chunks"
TARGET_INDEX = "rcsv-pdf-documents"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM = 1536
BATCH_SIZE = 512  # OpenAI max: 2048, but 512 is safer for memory


def create_target_index(es: Elasticsearch) -> None:
    """RCSV 호환 ES 인덱스 생성"""
    if es.indices.exists(index=TARGET_INDEX):
        count = es.count(index=TARGET_INDEX)["count"]
        if count > 0:
            print(f"  Target index '{TARGET_INDEX}' already has {count} docs. Skipping creation.")
            return
        es.indices.delete(index=TARGET_INDEX)

    mapping = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
        },
        "mappings": {
            "properties": {
                "text": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                },
                "vector_field": {
                    "type": "dense_vector",
                    "dims": EMBED_DIM,
                    "index": True,
                    "similarity": "cosine",
                },
                "metadata": {"type": "object", "enabled": True},
                "chunk_id": {"type": "keyword"},
                "document_id": {"type": "keyword"},
            }
        },
    }
    es.indices.create(index=TARGET_INDEX, body=mapping)
    print(f"  Created index '{TARGET_INDEX}' (dims={EMBED_DIM})")


def scroll_source_chunks(es: Elasticsearch) -> List[Dict[str, Any]]:
    """knowledge_chunks에서 전체 청크 텍스트 + 메타데이터 추출"""
    chunks: List[Dict[str, Any]] = []
    resp = es.search(
        index=SOURCE_INDEX,
        body={"query": {"match_all": {}}, "_source": ["chunk_id", "document_id", "content", "metadata"]},
        scroll="5m",
        size=1000,
    )
    scroll_id = resp["_scroll_id"]
    hits = resp["hits"]["hits"]

    while hits:
        for hit in hits:
            src = hit["_source"]
            chunks.append({
                "chunk_id": src.get("chunk_id", hit["_id"]),
                "document_id": src.get("document_id", ""),
                "text": src.get("content", ""),
                "metadata": src.get("metadata", {}),
            })
        resp = es.scroll(scroll_id=scroll_id, scroll="5m")
        scroll_id = resp["_scroll_id"]
        hits = resp["hits"]["hits"]

    es.clear_scroll(scroll_id=scroll_id)
    return chunks


def openai_embed_batch(texts: List[str]) -> List[List[float]]:
    """OpenAI API 배치 임베딩"""
    # Truncate very long texts (max ~8000 tokens for small model)
    truncated = [t[:6000] for t in texts]

    resp = requests.post(
        "https://api.openai.com/v1/embeddings",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={"model": OPENAI_EMBED_MODEL, "input": truncated},
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()["data"]
    return [item["embedding"] for item in data]


def bulk_index(es: Elasticsearch, chunks: List[Dict], embeddings: List[List[float]]) -> int:
    """ES bulk 인덱싱"""
    actions = []
    for chunk, emb in zip(chunks, embeddings):
        actions.append({
            "_index": TARGET_INDEX,
            "_id": chunk["chunk_id"],
            "_source": {
                "text": chunk["text"],
                "vector_field": emb,
                "metadata": chunk["metadata"],
                "chunk_id": chunk["chunk_id"],
                "document_id": chunk["document_id"],
            },
        })
    success, errors = helpers.bulk(es, actions, raise_on_error=False)
    return success


def main():
    print("=" * 60)
    print("  RCSV Bridge: OpenAI Embedding & ES Index Population")
    print("=" * 60)

    es = Elasticsearch(ES_URL)
    print(f"  ES: {ES_URL} (cluster: {es.info()['cluster_name']})")

    # 1. Check if already done
    if es.indices.exists(index=TARGET_INDEX):
        count = es.count(index=TARGET_INDEX)["count"]
        if count > 10000:
            print(f"  Target index already has {count} docs. Already populated!")
            return

    # 2. Create target index
    print("\n[1/3] Creating target index...")
    create_target_index(es)

    # 3. Read source chunks
    print("\n[2/3] Reading source chunks...")
    chunks = scroll_source_chunks(es)
    print(f"  Read {len(chunks)} chunks from '{SOURCE_INDEX}'")

    # 4. Embed and index in batches
    print(f"\n[3/3] Embedding with OpenAI ({OPENAI_EMBED_MODEL}) & indexing...")
    total_indexed = 0
    start_time = time.monotonic()

    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        texts = [c["text"] for c in batch]

        try:
            embeddings = openai_embed_batch(texts)
            indexed = bulk_index(es, batch, embeddings)
            total_indexed += indexed
            elapsed = time.monotonic() - start_time
            rate = total_indexed / elapsed if elapsed > 0 else 0
            print(
                f"  Batch {i//BATCH_SIZE + 1}: "
                f"{total_indexed}/{len(chunks)} indexed "
                f"({rate:.0f} docs/s, {elapsed:.1f}s elapsed)"
            )
        except Exception as e:
            print(f"  [ERROR] Batch {i//BATCH_SIZE + 1} failed: {e}")
            continue

    elapsed_total = time.monotonic() - start_time
    print(f"\n  Done! {total_indexed}/{len(chunks)} indexed in {elapsed_total:.1f}s")

    # Verify
    es.indices.refresh(index=TARGET_INDEX)
    final_count = es.count(index=TARGET_INDEX)["count"]
    print(f"  Final count in '{TARGET_INDEX}': {final_count}")


if __name__ == "__main__":
    main()
