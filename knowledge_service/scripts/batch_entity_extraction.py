"""
배치 엔티티 추출 스크립트 (Sprint 12 - Phase 3)

Neo4j 청크에서 DeepSeek V3.2로 엔티티/관계를 추출하여 Neo4j에 저장한다.
체크포인트 기반으로 중단/재개가 가능하다.

사용법:
    # 컨테이너 내부에서 실행
    docker exec kp-ai-service python scripts/batch_entity_extraction.py

    # 또는 nohup으로 백그라운드 실행
    docker exec kp-ai-service nohup python scripts/batch_entity_extraction.py > /tmp/entity_extraction.log 2>&1 &

환경변수:
    ENTITY_MIN_TOKENS: 최소 토큰 수 (기본: 150)
    ENTITY_CONCURRENCY: 동시 처리 수 (기본: 3)
    ENTITY_MAX_GLEANINGS: Gleaning 횟수 (기본: 1)
    ENTITY_BATCH_SIZE: Neo4j 저장 배치 크기 (기본: 50)
    ENTITY_CHECKPOINT_FILE: 체크포인트 파일 경로 (기본: /tmp/entity_checkpoint.json)
    ENTITY_PARTITION: 파티션 설정 "ID/TOTAL" (예: "0/2" = 2개 워커 중 첫째)
    DEEPSEEK_API_KEY: DeepSeek API 키 (워커별 다른 키 지정 가능)
"""

import asyncio
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# 프로젝트 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from neo4j import GraphDatabase

from app.core.config import settings
from app.core.logging import get_logger
from app.services.entity_extraction import EntityExtractionService

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# 설정
# ---------------------------------------------------------------------------

MIN_TOKENS = int(os.getenv("ENTITY_MIN_TOKENS", "150"))
CONCURRENCY = int(os.getenv("ENTITY_CONCURRENCY", "3"))
MAX_GLEANINGS = int(os.getenv("ENTITY_MAX_GLEANINGS", "1"))
BATCH_SIZE = int(os.getenv("ENTITY_BATCH_SIZE", "50"))
CHECKPOINT_FILE = os.getenv("ENTITY_CHECKPOINT_FILE", "/tmp/entity_checkpoint.json")

# 파티셔닝: "0/2" = 2개 워커 중 0번 (짝수 인덱스), "1/2" = 1번 (홀수 인덱스)
_partition_raw = os.getenv("ENTITY_PARTITION", "")
if _partition_raw and "/" in _partition_raw:
    PARTITION_ID, PARTITION_TOTAL = map(int, _partition_raw.split("/"))
else:
    PARTITION_ID, PARTITION_TOTAL = 0, 1  # 파티셔닝 없음 (전체 처리)

# Graceful shutdown
_shutdown_requested = False


def _handle_signal(signum, frame):
    global _shutdown_requested
    _shutdown_requested = True
    logger.warning("Shutdown requested (signal %d). Finishing current batch...", signum)


signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


# ---------------------------------------------------------------------------
# 체크포인트 관리
# ---------------------------------------------------------------------------


class Checkpoint:
    """체크포인트 관리: 처리 완료된 chunk_id를 추적"""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.processed: Set[str] = set()
        self.stats = {
            "total_entities": 0,
            "total_relationships": 0,
            "total_chunks_processed": 0,
            "total_errors": 0,
            "start_time": None,
            "last_save_time": None,
        }
        self._load()

    def _load(self):
        if Path(self.filepath).exists():
            with open(self.filepath) as f:
                data = json.load(f)
            self.processed = set(data.get("processed_ids", []))
            self.stats = data.get("stats", self.stats)
            logger.info(
                "Checkpoint loaded: %d chunks already processed", len(self.processed)
            )

    def save(self):
        self.stats["last_save_time"] = datetime.now(timezone.utc).isoformat()
        data = {
            "processed_ids": list(self.processed),
            "stats": self.stats,
        }
        with open(self.filepath, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def mark_done(self, chunk_id: str, entities: int, relationships: int):
        self.processed.add(chunk_id)
        self.stats["total_chunks_processed"] += 1
        self.stats["total_entities"] += entities
        self.stats["total_relationships"] += relationships

    def mark_error(self, chunk_id: str):
        self.processed.add(chunk_id)  # 에러도 재시도 방지
        self.stats["total_errors"] += 1

    def is_processed(self, chunk_id: str) -> bool:
        return chunk_id in self.processed


# ---------------------------------------------------------------------------
# Neo4j 엔티티/관계 저장
# ---------------------------------------------------------------------------


async def save_entities_to_neo4j(
    driver,
    chunk_id: str,
    entities: List[Dict],
    relationships: List[Dict],
):
    """추출된 엔티티와 관계를 Neo4j에 저장"""

    # 엔티티 타입 → Neo4j 추가 라벨 매핑 (neo4j_storage.py와 동일)
    _TYPE_TO_EXTRA_LABEL = {
        "Person": "Person",
        "Organization": "Person",   # Organization은 Person 라벨 사용
        "Technology": "Technology",
        "Project": "Topic",
        "Concept": "Topic",
        "Date": "Keyword",
        "Location": "Keyword",
    }

    with driver.session() as session:
        # 1. Entity 노드 생성 (MERGE로 중복 방지)
        for entity in entities:
            session.run(
                """
                MERGE (e:Entity {name: $name})
                SET e.entity_type = $type,
                    e.description = COALESCE(e.description, $description),
                    e.updated_at = datetime()
                WITH e
                MATCH (c:Chunk {id: $chunk_id})
                MERGE (c)-[:MENTIONS]->(e)
                """,
                name=entity["name"],
                type=entity["type"],
                description=entity.get("description", ""),
                chunk_id=chunk_id,
            )

            # 타입별 추가 라벨 설정 (모든 타입 포함)
            type_label = entity["type"]
            extra_label = _TYPE_TO_EXTRA_LABEL.get(type_label, "Keyword")
            session.run(
                f"MATCH (e:Entity {{name: $name}}) SET e:{extra_label}",
                name=entity["name"],
            )

        # 2. Entity 간 관계 생성
        for rel in relationships:
            session.run(
                """
                MATCH (s:Entity {name: $source_name})
                MATCH (t:Entity {name: $target_name})
                MERGE (s)-[r:RELATED_TO {type: $rel_type}]->(t)
                ON CREATE SET r.description = $description,
                              r.created_at = datetime()
                """,
                source_name=rel["source_name"],
                target_name=rel["target_name"],
                rel_type=rel["type"],
                description=rel.get("description", ""),
            )

        # 3. Chunk에 추출 완료 마킹
        session.run(
            """
            MATCH (c:Chunk {id: $chunk_id})
            SET c.entity_extracted = true,
                c.entity_extracted_at = datetime(),
                c.entity_count = $entity_count
            """,
            chunk_id=chunk_id,
            entity_count=len(entities),
        )


# ---------------------------------------------------------------------------
# 단일 청크 처리
# ---------------------------------------------------------------------------


async def process_chunk(
    svc: EntityExtractionService,
    driver,
    chunk_id: str,
    content: str,
    checkpoint: Checkpoint,
    semaphore: asyncio.Semaphore,
):
    """단일 청크의 엔티티/관계 추출 및 저장"""

    async with semaphore:
        if _shutdown_requested:
            return

        try:
            start = time.time()
            result = await svc.extract_full(content, enable_gleaning=True)
            elapsed = time.time() - start

            # Entity/Relationship를 Neo4j 저장 형식으로 변환
            entities = []
            entity_id_to_name = {}
            for e in result.entities:
                entities.append(
                    {
                        "name": e.name,
                        "type": e.type,
                        "description": e.description or "",
                    }
                )
                entity_id_to_name[e.id] = e.name

            relationships = []
            for r in result.relationships:
                source_name = entity_id_to_name.get(r.source)
                target_name = entity_id_to_name.get(r.target)
                if source_name and target_name:
                    relationships.append(
                        {
                            "source_name": source_name,
                            "target_name": target_name,
                            "type": r.type,
                            "description": r.description or "",
                        }
                    )

            # Neo4j 저장
            await save_entities_to_neo4j(driver, chunk_id, entities, relationships)

            checkpoint.mark_done(chunk_id, len(entities), len(relationships))

            processed = checkpoint.stats["total_chunks_processed"]
            logger.info(
                "Chunk %s: %d entities, %d rels (%.1fs) [%d done]",
                chunk_id[:12],
                len(entities),
                len(relationships),
                elapsed,
                processed,
            )

        except Exception as e:
            checkpoint.mark_error(chunk_id)
            logger.error("Chunk %s failed: %s", chunk_id[:12], str(e)[:200])


# ---------------------------------------------------------------------------
# 메인 배치 로직
# ---------------------------------------------------------------------------


async def run_batch():
    """배치 엔티티 추출 실행"""

    logger.info("=" * 60)
    logger.info("Batch Entity Extraction - Sprint 12 Phase 3")
    logger.info("=" * 60)
    logger.info(
        "Config: min_tokens=%d, concurrency=%d, max_gleanings=%d, partition=%d/%d",
        MIN_TOKENS,
        CONCURRENCY,
        MAX_GLEANINGS,
        PARTITION_ID,
        PARTITION_TOTAL,
    )

    # 체크포인트 로드
    checkpoint = Checkpoint(CHECKPOINT_FILE)
    if not checkpoint.stats["start_time"]:
        checkpoint.stats["start_time"] = datetime.now(timezone.utc).isoformat()

    # Neo4j 드라이버
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )

    # 대상 청크 조회
    with driver.session() as session:
        r = session.run(
            """
            MATCH (c:Chunk)
            WHERE c.token_count >= $min_tokens
            RETURN c.id as id, c.content as content, c.token_count as tc
            ORDER BY c.token_count DESC
            """,
            min_tokens=MIN_TOKENS,
        )
        all_chunks = [(rec["id"], rec["content"], rec["tc"]) for rec in r]

    # 이미 처리된 청크 필터링 (모든 워커의 체크포인트 통합)
    # 다른 워커의 체크포인트도 읽어서 중복 방지
    all_processed = set(checkpoint.processed)
    if PARTITION_TOTAL > 1:
        for pid in range(PARTITION_TOTAL):
            if pid == PARTITION_ID:
                continue
            other_cp = CHECKPOINT_FILE.replace(
                f"_w{PARTITION_ID}", f"_w{pid}"
            )
            if Path(other_cp).exists():
                with open(other_cp) as f:
                    other_data = json.load(f)
                other_ids = set(other_data.get("processed_ids", []))
                all_processed |= other_ids
                logger.info("Loaded %d IDs from worker %d checkpoint", len(other_ids), pid)

    pending = [
        (cid, content, tc)
        for cid, content, tc in all_chunks
        if not (cid in all_processed)
    ]

    # 파티셔닝 적용: 각 워커는 자기 파티션만 처리
    if PARTITION_TOTAL > 1:
        pending = pending[PARTITION_ID::PARTITION_TOTAL]
        logger.info("Partition %d/%d: assigned %d chunks", PARTITION_ID, PARTITION_TOTAL, len(pending))

    logger.info(
        "Total eligible: %d, Already processed: %d, Pending: %d",
        len(all_chunks),
        len(all_chunks) - len(pending),
        len(pending),
    )

    if not pending:
        logger.info("All chunks already processed. Exiting.")
        driver.close()
        return

    # EntityExtractionService 초기화
    svc = EntityExtractionService(max_gleanings=MAX_GLEANINGS)
    semaphore = asyncio.Semaphore(CONCURRENCY)

    # 배치 처리
    batch_start = time.time()
    total_pending = len(pending)

    for i in range(0, len(pending), BATCH_SIZE):
        if _shutdown_requested:
            logger.warning("Shutdown requested. Saving checkpoint...")
            break

        batch = pending[i : i + BATCH_SIZE]

        # 동시 처리
        tasks = [
            process_chunk(svc, driver, cid, content, checkpoint, semaphore)
            for cid, content, tc in batch
        ]
        await asyncio.gather(*tasks)

        # 배치 완료 후 체크포인트 저장
        checkpoint.save()

        elapsed = time.time() - batch_start
        done = checkpoint.stats["total_chunks_processed"]
        rate = done / elapsed if elapsed > 0 else 0
        remaining = (total_pending - (i + len(batch))) / rate if rate > 0 else 0

        logger.info(
            "Batch %d/%d done. Total: %d/%d (%.1f/min, ETA: %.0fmin)",
            i // BATCH_SIZE + 1,
            (total_pending + BATCH_SIZE - 1) // BATCH_SIZE,
            done,
            total_pending,
            rate * 60,
            remaining / 60,
        )

    # 최종 저장
    checkpoint.save()
    total_elapsed = time.time() - batch_start

    # 최종 통계
    logger.info("=" * 60)
    logger.info("Batch Entity Extraction COMPLETE")
    logger.info("=" * 60)
    logger.info("Chunks processed: %d", checkpoint.stats["total_chunks_processed"])
    logger.info("Total entities: %d", checkpoint.stats["total_entities"])
    logger.info("Total relationships: %d", checkpoint.stats["total_relationships"])
    logger.info("Errors: %d", checkpoint.stats["total_errors"])
    logger.info("Elapsed: %.1f minutes", total_elapsed / 60)

    # Neo4j 최종 통계
    with driver.session() as session:
        r = session.run(
            "MATCH (e:Entity) RETURN count(e) as cnt, "
            "count(DISTINCT e.type) as types"
        )
        rec = r.single()
        logger.info(
            "Neo4j Entities: %d (types: %d)",
            rec["cnt"],
            rec["types"],
        )

        r2 = session.run("MATCH ()-[r:RELATED_TO]->() RETURN count(r) as cnt")
        logger.info("Neo4j Relationships: %d", r2.single()["cnt"])

        r3 = session.run("MATCH ()-[r:MENTIONS]->() RETURN count(r) as cnt")
        logger.info("Neo4j MENTIONS links: %d", r3.single()["cnt"])

    driver.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    asyncio.run(run_batch())
