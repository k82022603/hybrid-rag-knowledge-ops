"""
GPU 임베딩 결과를 Elasticsearch에 벌크 임포트하는 스크립트

Usage:
    # 컨테이너 내부에서 실행
    python3 scripts/import_embeddings.py /tmp/chunks_for_gpu_embeddings.jsonl

    # 또는 호스트에서 docker exec로 실행
    docker cp embeddings_result.jsonl kp-ai-service:/tmp/
    docker exec kp-ai-service python3 scripts/import_embeddings.py /tmp/embeddings_result.jsonl

    # pending 건만 처리 (이어하기)
    docker exec kp-ai-service python3 scripts/import_embeddings.py /tmp/embeddings_result.jsonl --skip-completed
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error

# Add app to path for status_callback
sys.path.insert(0, "/app/src")

ES_URL = os.getenv("ELASTICSEARCH_URL", "http://elasticsearch:9200")
INDEX = "knowledge_chunks"
BULK_SIZE = 100


def get_completed_ids():
    """이미 completed인 chunk_id 목록 조회"""
    completed = set()
    body = json.dumps({
        "size": 0,
        "query": {"term": {"embedding_status.keyword": "completed"}},
        "aggs": {"ids": {"terms": {"field": "_id", "size": 60000}}}
    })
    try:
        req = urllib.request.Request(
            f"{ES_URL}/{INDEX}/_search",
            data=body.encode(),
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read())
        for b in data["aggregations"]["ids"]["buckets"]:
            completed.add(b["key"])
    except Exception:
        pass
    return completed


def bulk_update_embeddings(input_file: str, skip_completed: bool = False):
    """JSONL 파일에서 임베딩을 읽어 ES에 벌크 업데이트"""
    print(f"Loading embeddings from: {input_file}")

    records = []
    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    total_loaded = len(records)
    print(f"Total records loaded: {total_loaded}")

    if skip_completed:
        print("Fetching already completed IDs...")
        completed_ids = get_completed_ids()
        records = [r for r in records if r["chunk_id"] not in completed_ids]
        print(f"Skipping {total_loaded - len(records)} completed, processing {len(records)} remaining")

    if not records:
        print("No records to process!")
        return

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

            # sparse_vector를 JSON 문자열로 직렬화 (동적 매핑 폭발 방지)
            sparse_json = json.dumps(sparse, ensure_ascii=False)

            action = json.dumps({"update": {"_index": INDEX, "_id": chunk_id}})
            doc = json.dumps(
                {
                    "doc": {
                        "dense_vector": dense,
                        "sparse_vector_json": sparse_json,
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
            resp = urllib.request.urlopen(req, timeout=120)
            result = json.loads(resp.read())

            batch_errors = 0
            if result.get("errors"):
                for item in result["items"]:
                    if "error" in item.get("update", {}):
                        batch_errors += 1
                        failed += 1
                        if batch_errors <= 3:
                            err = item["update"]["error"]
                            print(f"  Error: {err.get('type')}: {err.get('reason', '')[:100]}")
                    else:
                        updated += 1
                if batch_errors > 3:
                    print(f"  ... and {batch_errors - 3} more errors in this batch")
            else:
                updated += len(batch)

        except (urllib.error.URLError, Exception) as e:
            print(f"  Bulk request failed: {e}")
            failed += len(batch)

        progress = batch_start + len(batch)
        elapsed = time.time() - start
        rate = progress / elapsed if elapsed > 0 else 0
        remaining = (len(records) - progress) / rate if rate > 0 else 0
        print(f"  Progress: {progress}/{len(records)} ({rate:.0f} docs/s, ~{remaining/60:.0f}m left)")

    elapsed = time.time() - start
    print(f"\nCompleted in {elapsed:.1f}s ({elapsed/60:.1f}m)")
    print(f"  Updated: {updated}")
    print(f"  Failed: {failed}")

    # STORY-089: Phase 2 GPU 임베딩 완료 → document별 PG 상태 콜백 (completed, es_synced=true)
    if updated > 0:
        print("\nNotifying PG status (completed, es_synced=true) for processed documents...")
        try:
            from app.services.status_callback import notify_status_sync

            # 처리된 청크에서 unique document_id 추출
            doc_ids_updated: set = set()
            for rec in records:
                doc_id = rec.get("document_id")
                if doc_id:
                    doc_ids_updated.add(doc_id)

            notified = 0
            for doc_id in doc_ids_updated:
                ok = notify_status_sync(
                    document_id=doc_id,
                    status="completed",
                    progress_percent=100,
                    es_synced=True,
                )
                if ok:
                    notified += 1

            print(f"  PG callbacks sent: {notified}/{len(doc_ids_updated)} documents")
        except Exception as e:
            print(f"  PG callback failed (non-critical): {e}")

    # 결과 검증 (embedding_status 기반)
    verify_url = f"{ES_URL}/{INDEX}/_search"
    verify_query = json.dumps({
        "size": 0,
        "aggs": {
            "status": {
                "terms": {"field": "embedding_status.keyword", "size": 10, "missing": "none"}
            }
        }
    })
    try:
        req = urllib.request.Request(
            verify_url,
            data=verify_query.encode(),
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req)
        vdata = json.loads(resp.read())
        total = vdata["hits"]["total"]["value"]
        print(f"\nVerification:")
        print(f"  Total chunks: {total}")
        for b in vdata["aggregations"]["status"]["buckets"]:
            pct = b['doc_count'] / total * 100
            print(f"  {b['key']}: {b['doc_count']} ({pct:.1f}%)")
    except Exception as e:
        print(f"Verification failed: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_embeddings.py <embeddings.jsonl> [--skip-completed]")
        sys.exit(1)

    skip = "--skip-completed" in sys.argv
    bulk_update_embeddings(sys.argv[1], skip_completed=skip)
