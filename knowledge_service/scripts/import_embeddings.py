"""
GPU 임베딩 결과를 Elasticsearch에 벌크 임포트하는 스크립트

Usage:
    # 컨테이너 내부에서 실행
    python3 scripts/import_embeddings.py /tmp/chunks_need_sparse_embeddings.jsonl

    # 또는 호스트에서 docker exec로 실행
    docker cp embeddings_result.jsonl kp-ai-service:/tmp/
    docker exec kp-ai-service python3 scripts/import_embeddings.py /tmp/embeddings_result.jsonl
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error

ES_URL = os.getenv("ELASTICSEARCH_URL", "http://elasticsearch:9200")
INDEX = "knowledge_chunks"
BULK_SIZE = 200


def bulk_update_embeddings(input_file: str):
    """JSONL 파일에서 임베딩을 읽어 ES에 벌크 업데이트"""
    print(f"Loading embeddings from: {input_file}")

    records = []
    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    print(f"Total records: {len(records)}")

    updated = 0
    failed = 0
    start = time.time()

    for batch_start in range(0, len(records), BULK_SIZE):
        batch = records[batch_start : batch_start + BULK_SIZE]
        bulk_body = ""

        for rec in batch:
            chunk_id = rec["chunk_id"]
            dense = rec["dense_vector"]
            sparse = rec["sparse_vector"]

            action = json.dumps({"update": {"_index": INDEX, "_id": chunk_id}})
            doc = json.dumps(
                {
                    "doc": {
                        "dense_vector": dense,
                        "sparse_vector": sparse,
                        "embedding_status": "completed",
                        "embedding_model": "bge-m3",
                    }
                }
            )
            bulk_body += action + "\n" + doc + "\n"

        try:
            req = urllib.request.Request(
                f"{ES_URL}/_bulk",
                data=bulk_body.encode("utf-8"),
                headers={"Content-Type": "application/x-ndjson"},
            )
            resp = urllib.request.urlopen(req)
            result = json.loads(resp.read())

            if result.get("errors"):
                for item in result["items"]:
                    if "error" in item.get("update", {}):
                        failed += 1
                        err = item["update"]["error"]
                        print(f"  Error: {err.get('type')}: {err.get('reason', '')[:100]}")
                    else:
                        updated += 1
            else:
                updated += len(batch)

        except urllib.error.URLError as e:
            print(f"  Bulk request failed: {e}")
            failed += len(batch)

        progress = batch_start + len(batch)
        elapsed = time.time() - start
        rate = progress / elapsed if elapsed > 0 else 0
        print(f"  Progress: {progress}/{len(records)} ({rate:.0f} docs/s)")

    elapsed = time.time() - start
    print(f"\nCompleted in {elapsed:.1f}s")
    print(f"  Updated: {updated}")
    print(f"  Failed: {failed}")

    # 결과 검증
    verify_url = f"{ES_URL}/{INDEX}/_search"
    verify_query = json.dumps(
        {
            "size": 0,
            "aggs": {
                "has_sparse": {"filter": {"exists": {"field": "sparse_vector"}}},
                "has_dense": {"filter": {"exists": {"field": "dense_vector"}}},
            },
        }
    )
    try:
        req = urllib.request.Request(
            verify_url,
            data=verify_query.encode(),
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req)
        vdata = json.loads(resp.read())
        total = vdata["hits"]["total"]["value"]
        has_sparse = vdata["aggregations"]["has_sparse"]["doc_count"]
        has_dense = vdata["aggregations"]["has_dense"]["doc_count"]
        print(f"\nVerification:")
        print(f"  Total chunks: {total}")
        print(f"  Has dense: {has_dense} ({has_dense/total*100:.1f}%)")
        print(f"  Has sparse: {has_sparse} ({has_sparse/total*100:.1f}%)")
    except Exception as e:
        print(f"Verification failed: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_embeddings.py <embeddings.jsonl>")
        sys.exit(1)

    bulk_update_embeddings(sys.argv[1])
