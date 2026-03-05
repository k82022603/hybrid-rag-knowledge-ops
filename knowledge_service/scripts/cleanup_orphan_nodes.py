"""
Neo4j 고아 Entity 노드 정리 스크립트 (STORY-120)

Chunk와 연결되지 않은 Entity 노드(고아 노드)를 식별하고 삭제합니다.
고아 비율 1% 미만 유지가 목표입니다.

정의:
  - 고아 Entity: MENTIONS 관계(Chunk → Entity)가 없는 Entity 노드
  - 즉, 어떤 Chunk와도 연결되어 있지 않은 Entity

사용법:
    # 컨테이너 내부에서 실행
    docker exec kp-ai-service python scripts/cleanup_orphan_nodes.py

    # dry-run (삭제하지 않고 목록만 확인)
    docker exec kp-ai-service python scripts/cleanup_orphan_nodes.py --dry-run

    # 삭제 배치 크기 지정
    docker exec kp-ai-service python scripts/cleanup_orphan_nodes.py --batch-size 100

환경변수:
    ORPHAN_BATCH_SIZE: 삭제 배치 크기 (기본: 200)
    ORPHAN_MAX_RATIO: 허용 최대 고아 비율 (기본: 0.01 = 1%)
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from neo4j import GraphDatabase

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

ORPHAN_BATCH_SIZE = int(os.getenv("ORPHAN_BATCH_SIZE", "200"))
ORPHAN_MAX_RATIO = float(os.getenv("ORPHAN_MAX_RATIO", "0.01"))  # 1%


# ---------------------------------------------------------------------------
# 통계 수집
# ---------------------------------------------------------------------------


def get_graph_stats(driver) -> Dict[str, int]:
    """Entity 노드 전체/고아 수 조회"""
    with driver.session() as session:
        r_total = session.run("MATCH (e:Entity) RETURN count(e) AS cnt")
        total = r_total.single()["cnt"]

        r_orphan = session.run(
            """
            MATCH (e:Entity)
            WHERE NOT (e)<-[:MENTIONS]-()
            RETURN count(e) AS cnt
            """
        )
        orphan = r_orphan.single()["cnt"]

        r_chunk = session.run("MATCH (c:Chunk) RETURN count(c) AS cnt")
        chunks = r_chunk.single()["cnt"]

        r_rel = session.run(
            "MATCH ()-[r:RELATED_TO]->() RETURN count(r) AS cnt"
        )
        rels = r_rel.single()["cnt"]

    return {
        "total_entities": total,
        "orphan_entities": orphan,
        "total_chunks": chunks,
        "total_relationships": rels,
    }


def compute_orphan_ratio(stats: Dict[str, int]) -> float:
    """고아 비율 계산 (전체 Entity 대비)"""
    total = stats["total_entities"]
    if total == 0:
        return 0.0
    return stats["orphan_entities"] / total


# ---------------------------------------------------------------------------
# 고아 노드 정리
# ---------------------------------------------------------------------------


def delete_orphan_entities_batch(driver, batch_size: int) -> int:
    """
    MENTIONS 관계가 없는 Entity를 배치 삭제합니다.
    연결된 RELATED_TO 관계도 함께 삭제됩니다.

    Returns:
        삭제된 노드 수
    """
    with driver.session() as session:
        result = session.run(
            """
            MATCH (e:Entity)
            WHERE NOT (e)<-[:MENTIONS]-()
            WITH e LIMIT $batch_size
            DETACH DELETE e
            RETURN count(e) AS deleted
            """,
            batch_size=batch_size,
        )
        record = result.single()
        return record["deleted"] if record else 0


def list_orphan_samples(driver, limit: int = 20) -> list:
    """고아 Entity 샘플 목록 반환 (dry-run 확인용)"""
    with driver.session() as session:
        result = session.run(
            """
            MATCH (e:Entity)
            WHERE NOT (e)<-[:MENTIONS]-()
            RETURN e.name AS name, e.entity_type AS type
            ORDER BY e.name
            LIMIT $limit
            """,
            limit=limit,
        )
        return [{"name": r["name"], "type": r["type"]} for r in result]


# ---------------------------------------------------------------------------
# 메인 로직
# ---------------------------------------------------------------------------


def run_cleanup(dry_run: bool = False, batch_size: int = ORPHAN_BATCH_SIZE) -> Dict:
    """
    고아 Entity 노드 정리를 실행합니다.

    Args:
        dry_run: True면 삭제하지 않고 통계만 출력
        batch_size: 배치 삭제 단위

    Returns:
        실행 결과 통계 dict
    """
    logger.info("=" * 60)
    logger.info("Neo4j Orphan Entity Cleanup - STORY-120")
    logger.info("=" * 60)
    logger.info("Mode: %s", "DRY-RUN" if dry_run else "DELETE")
    logger.info("Batch size: %d", batch_size)
    logger.info("Max allowed orphan ratio: %.1f%%", ORPHAN_MAX_RATIO * 100)

    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )

    start_time = time.time()

    try:
        # 초기 통계
        stats_before = get_graph_stats(driver)
        orphan_ratio_before = compute_orphan_ratio(stats_before)

        logger.info("\n[Before Cleanup]")
        logger.info("  Total entities:  %d", stats_before["total_entities"])
        logger.info("  Orphan entities: %d (%.2f%%)", stats_before["orphan_entities"], orphan_ratio_before * 100)
        logger.info("  Total chunks:    %d", stats_before["total_chunks"])
        logger.info("  Relationships:   %d", stats_before["total_relationships"])

        if dry_run:
            # dry-run: 샘플 목록 출력
            samples = list_orphan_samples(driver, limit=20)
            if samples:
                logger.info("\n[Orphan Entity Samples (up to 20)]")
                for s in samples:
                    logger.info("  - %s (%s)", s["name"], s["type"] or "Unknown")
            else:
                logger.info("No orphan entities found.")

            elapsed = time.time() - start_time
            return {
                "mode": "dry_run",
                "orphan_count": stats_before["orphan_entities"],
                "orphan_ratio": round(orphan_ratio_before, 4),
                "within_threshold": orphan_ratio_before <= ORPHAN_MAX_RATIO,
                "elapsed_seconds": round(elapsed, 1),
            }

        # 고아 비율이 이미 기준 이하면 스킵
        if stats_before["orphan_entities"] == 0:
            logger.info("No orphan entities. Nothing to clean up.")
            return {
                "mode": "delete",
                "deleted": 0,
                "orphan_ratio_before": 0.0,
                "orphan_ratio_after": 0.0,
                "within_threshold": True,
                "elapsed_seconds": 0.0,
            }

        # 배치 삭제 루프
        total_deleted = 0
        round_num = 0

        while True:
            deleted = delete_orphan_entities_batch(driver, batch_size)
            total_deleted += deleted
            round_num += 1

            logger.info("Round %d: deleted %d nodes (total: %d)", round_num, deleted, total_deleted)

            if deleted == 0:
                break

        # 최종 통계
        stats_after = get_graph_stats(driver)
        orphan_ratio_after = compute_orphan_ratio(stats_after)

        elapsed = time.time() - start_time

        logger.info("\n[After Cleanup]")
        logger.info("  Total entities:  %d", stats_after["total_entities"])
        logger.info("  Orphan entities: %d (%.2f%%)", stats_after["orphan_entities"], orphan_ratio_after * 100)
        logger.info("  Deleted:         %d nodes", total_deleted)
        logger.info("  Elapsed:         %.1fs", elapsed)

        within_threshold = orphan_ratio_after <= ORPHAN_MAX_RATIO
        if within_threshold:
            logger.info("PASS: Orphan ratio %.2f%% is within %.1f%% threshold",
                        orphan_ratio_after * 100, ORPHAN_MAX_RATIO * 100)
        else:
            logger.warning(
                "WARN: Orphan ratio %.2f%% still exceeds %.1f%% threshold after cleanup",
                orphan_ratio_after * 100, ORPHAN_MAX_RATIO * 100,
            )

        return {
            "mode": "delete",
            "deleted": total_deleted,
            "orphan_count_before": stats_before["orphan_entities"],
            "orphan_count_after": stats_after["orphan_entities"],
            "orphan_ratio_before": round(orphan_ratio_before, 4),
            "orphan_ratio_after": round(orphan_ratio_after, 4),
            "within_threshold": within_threshold,
            "total_entities_after": stats_after["total_entities"],
            "elapsed_seconds": round(elapsed, 1),
        }

    finally:
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

    parser = argparse.ArgumentParser(
        description="Neo4j 고아 Entity 노드 정리 (STORY-120)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="삭제하지 않고 고아 노드 목록만 출력",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=ORPHAN_BATCH_SIZE,
        help=f"배치 삭제 단위 (기본: {ORPHAN_BATCH_SIZE})",
    )
    args = parser.parse_args()

    result = run_cleanup(dry_run=args.dry_run, batch_size=args.batch_size)

    print("\n" + "=" * 60)
    print("Cleanup Result:")
    for k, v in result.items():
        print(f"  {k}: {v}")
    print("=" * 60)

    # 고아 비율 기준 초과 시 비정상 종료
    if not result.get("within_threshold", True):
        sys.exit(1)
