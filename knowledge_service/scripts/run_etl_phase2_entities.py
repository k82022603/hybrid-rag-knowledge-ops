#!/usr/bin/env python3
"""
ETL Phase 2: 엔티티 추출 후처리

Phase 1 (run_etl_fast.py)에서 임베딩/저장이 완료된 문서에 대해
엔티티 추출 + Neo4j Entity 노드 생성을 수행합니다.

특징:
  - ES에서 document_id 목록 조회 -> 엔티티 미추출 문서 대상
  - DeepSeek API 비동기 동시 호출 (concurrency 제어)
  - Neo4j UNWIND 벌크 저장
  - 중단 후 재개 지원 (--resume)

사용법 (컨테이너 내부):
    python /app/scripts/run_etl_phase2_entities.py
    python /app/scripts/run_etl_phase2_entities.py --concurrency 5
    python /app/scripts/run_etl_phase2_entities.py --resume
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Add app to path
sys.path.insert(0, "/app/src")
os.chdir("/app")

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

from app.core.config import settings
from app.core.logging import get_logger
from app.services.status_callback import notify_status

logger = get_logger(__name__)

PROGRESS_FILE = "/app/knowledge_data/etl_phase2_progress.json"
COMPLETED_FILE = "/app/knowledge_data/etl_phase2_completed.json"

_progress = {
    "status": "initializing",
    "mode": "phase2_entities",
    "started_at": "",
    "total_docs": 0,
    "processed": 0,
    "success": 0,
    "failed": 0,
    "skipped": 0,
    "entities_total": 0,
    "relationships_total": 0,
    "current_doc": "",
    "elapsed_seconds": 0,
    "rate_per_minute": 0,
}
_start_time = 0.0
_completed_docs: Set[str] = set()


def save_progress():
    """진행 상황 저장"""
    try:
        elapsed = time.monotonic() - _start_time
        _progress["elapsed_seconds"] = round(elapsed)
        if elapsed > 60 and _progress["success"] > 0:
            _progress["rate_per_minute"] = round(
                _progress["success"] / (elapsed / 60), 1
            )
        with open(PROGRESS_FILE, "w") as f:
            json.dump(_progress, f, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        logger.warning("Failed to save progress: %s", e)


def save_completed_docs():
    """완료된 문서 목록 저장"""
    try:
        with open(COMPLETED_FILE, "w") as f:
            json.dump(sorted(list(_completed_docs)), f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning("Failed to save completed docs: %s", e)


def load_completed_docs() -> Set[str]:
    """이전 실행에서 완료된 문서 목록 로드"""
    try:
        if Path(COMPLETED_FILE).exists():
            with open(COMPLETED_FILE) as f:
                return set(json.load(f))
    except Exception as e:
        logger.warning("Failed to load completed docs: %s", e)
    return set()


async def get_documents_from_es() -> List[Dict[str, Any]]:
    """ES에서 document_id별 대표 텍스트 조회"""
    try:
        from elasticsearch import AsyncElasticsearch

        es = AsyncElasticsearch(settings.elasticsearch_url)
        try:
            # document_id별 집계 + 대표 텍스트
            resp = await es.search(
                index=settings.elasticsearch_index,
                body={
                    "size": 0,
                    "aggs": {
                        "docs": {
                            "terms": {
                                "field": "document_id.keyword",
                                "size": 10000,
                            },
                            "aggs": {
                                "sample_text": {
                                    "top_hits": {
                                        "size": 5,
                                        "_source": ["document_id", "text", "chunk_index", "metadata"],
                                        "sort": [{"chunk_index": "asc"}],
                                    }
                                }
                            }
                        }
                    }
                },
            )

            documents = []
            for bucket in resp["aggregations"]["docs"]["buckets"]:
                doc_id = bucket["key"]
                hits = bucket["sample_text"]["hits"]["hits"]
                # 상위 5개 청크 텍스트를 결합
                texts = [h["_source"].get("text", "") for h in hits]
                combined_text = "\n\n".join(texts)
                metadata = hits[0]["_source"].get("metadata", {}) if hits else {}

                documents.append({
                    "document_id": doc_id,
                    "text": combined_text,
                    "metadata": metadata,
                    "chunk_count": bucket["doc_count"],
                })

            logger.info("Found %d documents in ES", len(documents))
            return documents

        finally:
            await es.close()

    except Exception as e:
        logger.error("Failed to query ES: %s", e)
        return []


async def check_neo4j_entities(doc_id: str) -> bool:
    """Neo4j에서 해당 문서에 Entity가 있는지 확인"""
    try:
        from neo4j import AsyncGraphDatabase

        driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password or ""),
        )
        try:
            async with driver.session() as session:
                result = await session.run(
                    """
                    MATCH (d:Document {id: $doc_id})<-[:PART_OF]-(c:Chunk)<-[:MENTIONED_IN]-(e:Entity)
                    RETURN count(e) as entity_count
                    """,
                    doc_id=doc_id,
                )
                record = await result.single()
                return record and record["entity_count"] > 0
        finally:
            await driver.close()
    except Exception:
        return False


async def store_entities_to_neo4j(
    doc_id: str,
    entities: list,
    relationships: list,
) -> None:
    """엔티티와 관계를 Neo4j에 벌크 저장"""
    try:
        from neo4j import AsyncGraphDatabase

        driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password or ""),
        )
        try:
            async with driver.session() as session:
                # Entity 노드 벌크 생성
                if entities:
                    entity_data = [
                        {
                            "name": e.name,
                            "type": e.type,
                            "description": getattr(e, "description", None),
                        }
                        for e in entities
                    ]
                    await session.run(
                        """
                        UNWIND $entities AS entity
                        MERGE (e:Entity {name: entity.name})
                        SET e.type = entity.type,
                            e.description = entity.description
                        """,
                        entities=entity_data,
                    )

                # Relationship 벌크 생성
                if relationships:
                    # 엔티티 이름 -> id 매핑
                    entity_name_map = {e.id: e.name for e in entities}
                    rel_data = [
                        {
                            "source_name": entity_name_map.get(r.source, r.source),
                            "target_name": entity_name_map.get(r.target, r.target),
                            "type": r.type,
                            "description": getattr(r, "description", None),
                        }
                        for r in relationships
                        if r.source in entity_name_map and r.target in entity_name_map
                    ]
                    if rel_data:
                        await session.run(
                            """
                            UNWIND $rels AS rel
                            MATCH (s:Entity {name: rel.source_name})
                            MATCH (t:Entity {name: rel.target_name})
                            MERGE (s)-[r:RELATED_TO {type: rel.type}]->(t)
                            SET r.description = rel.description
                            """,
                            rels=rel_data,
                        )

                logger.info(
                    "Neo4j Phase 2 stored: doc=%s, entities=%d, rels=%d",
                    doc_id[:8], len(entities), len(relationships),
                )

        finally:
            await driver.close()

    except Exception as e:
        logger.error("Neo4j Phase 2 storage failed for doc %s: %s", doc_id[:8], e)
        raise


async def process_document(
    doc: Dict[str, Any],
    entity_extractor,
    semaphore: asyncio.Semaphore,
) -> Dict[str, Any]:
    """단일 문서에 대한 엔티티 추출 + Neo4j 저장"""
    doc_id = doc["document_id"]
    result = {"doc_id": doc_id, "status": "pending", "entities": 0, "relationships": 0}

    async with semaphore:
        start = time.monotonic()
        _progress["current_doc"] = doc_id[:8]

        try:
            text = doc.get("text", "")
            if not text or len(text.strip()) < 50:
                result["status"] = "skipped"
                result["reason"] = "Text too short"
                return result

            # 엔티티 + 관계 추출
            extraction = await entity_extractor.extract_full(
                text=text,
                enable_gleaning=True,
            )

            entities = extraction.entities
            relationships = extraction.relationships

            result["entities"] = len(entities)
            result["relationships"] = len(relationships)

            # Neo4j 저장
            if entities:
                await store_entities_to_neo4j(doc_id, entities, relationships)

            elapsed_ms = (time.monotonic() - start) * 1000
            result["status"] = "success"
            result["elapsed_ms"] = round(elapsed_ms, 1)

            logger.info(
                "Phase 2 doc processed: %s, entities=%d, rels=%d, time=%.1fms",
                doc_id[:8], len(entities), len(relationships), elapsed_ms,
            )

            # STORY-089: Phase 3 완료 → PG entity_count 업데이트 (status=completed 유지)
            await notify_status(
                document_id=doc_id,
                status="completed",
                progress_percent=100,
                entity_count=len(entities),
            )

        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            logger.error("Phase 2 failed for doc %s: %s", doc_id[:8], e)

        return result


async def main():
    global _start_time, _completed_docs

    parser = argparse.ArgumentParser(description="ETL Phase 2: Entity Extraction")
    parser.add_argument(
        "--concurrency", "-c", type=int, default=3,
        help="동시 처리 문서 수 (DeepSeek API 동시 호출, 기본: 3)",
    )
    parser.add_argument(
        "--resume", action="store_true", default=False,
        help="이전 실행에서 중단된 지점부터 재개",
    )
    parser.add_argument(
        "--max-docs", type=int, default=0,
        help="최대 처리 문서 수 (0=전체, 테스트용)",
    )
    args = parser.parse_args()

    _start_time = time.monotonic()
    started_at = datetime.now().isoformat()
    _progress["started_at"] = started_at
    _progress["status"] = "running"

    if args.resume:
        _completed_docs = load_completed_docs()
        print(f"Resuming: {len(_completed_docs)} docs already completed")

    print("=" * 60)
    print(f"ETL Phase 2: Entity Extraction Started: {started_at}")
    print(f"  Concurrency: {args.concurrency}")
    print(f"  Resume mode: {args.resume}")
    print("=" * 60)

    # ES에서 문서 목록 조회
    print("\nQuerying documents from Elasticsearch...")
    all_docs = await get_documents_from_es()
    if not all_docs:
        print("No documents found in Elasticsearch. Run Phase 1 first.")
        return

    # 이미 완료된 문서 건너뛰기
    pending_docs = [d for d in all_docs if d["document_id"] not in _completed_docs]
    if args.max_docs > 0:
        pending_docs = pending_docs[:args.max_docs]

    _progress["total_docs"] = len(pending_docs)
    print(f"\nTotal documents: {len(all_docs)}")
    print(f"Already completed: {len(_completed_docs)}")
    print(f"To process: {len(pending_docs)}")
    save_progress()

    # 엔티티 추출 서비스 초기화
    from app.services.entity_extraction import get_entity_extraction_service
    entity_extractor = get_entity_extraction_service()

    # 동시 처리
    semaphore = asyncio.Semaphore(args.concurrency)

    print("\nStarting entity extraction...\n")

    batch_size = args.concurrency * 2
    for i in range(0, len(pending_docs), batch_size):
        batch = pending_docs[i:i + batch_size]
        results = await asyncio.gather(
            *[process_document(doc, entity_extractor, semaphore) for doc in batch],
            return_exceptions=True,
        )

        for j, r in enumerate(results):
            if isinstance(r, Exception):
                _progress["failed"] += 1
                logger.error("Batch exception: %s", r)
            else:
                _progress["processed"] += 1
                if r["status"] == "success":
                    _progress["success"] += 1
                    _progress["entities_total"] += r.get("entities", 0)
                    _progress["relationships_total"] += r.get("relationships", 0)
                    _completed_docs.add(r["doc_id"])
                elif r["status"] == "failed":
                    _progress["failed"] += 1
                else:
                    _progress["skipped"] += 1
                    _completed_docs.add(r["doc_id"])

        if (i // batch_size + 1) % 2 == 0:
            save_progress()
            save_completed_docs()

        print(
            f"  Progress: {_progress['processed']}/{_progress['total_docs']} "
            f"(success={_progress['success']}, failed={_progress['failed']}, "
            f"entities={_progress['entities_total']})",
            flush=True,
        )

    elapsed = time.monotonic() - _start_time
    _progress.update({
        "status": "completed",
        "completed_at": datetime.now().isoformat(),
        "elapsed_seconds": round(elapsed),
    })
    save_progress()
    save_completed_docs()

    print("\n" + "=" * 60)
    print("ETL Phase 2: Entity Extraction Completed!")
    print("=" * 60)
    print(f"  Total docs:       {_progress['total_docs']}")
    print(f"  Success:          {_progress['success']}")
    print(f"  Failed:           {_progress['failed']}")
    print(f"  Skipped:          {_progress['skipped']}")
    print(f"  Total entities:   {_progress['entities_total']}")
    print(f"  Total relations:  {_progress['relationships_total']}")
    print(f"  Elapsed:          {int(elapsed)}s ({elapsed/60:.1f}m, {elapsed/3600:.1f}h)")
    if elapsed > 60 and _progress["success"] > 0:
        print(f"  Rate:             {_progress['rate_per_minute']} docs/min")


if __name__ == "__main__":
    asyncio.run(main())
    print(f"\nProgress saved to: {PROGRESS_FILE}")
    print(f"Completed docs saved to: {COMPLETED_FILE}")
