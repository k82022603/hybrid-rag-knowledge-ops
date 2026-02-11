"""
기존 PG documents 레코드에 file_hash 백필 스크립트 (STORY-108)

file_hash가 NULL인 레코드를 찾아, file_path에 해당하는 파일의
SHA-256 해시를 계산하여 업데이트합니다.

임베딩을 다시 하지 않고도 dedup이 작동하도록 합니다.

Usage:
    docker exec kp-ai-service python3 scripts/backfill_file_hash.py
    docker exec kp-ai-service python3 scripts/backfill_file_hash.py --dry-run
"""

import asyncio
import hashlib
import sys
from pathlib import Path

import asyncpg


def compute_file_hash(file_path: Path) -> str:
    """SHA-256 해시 계산"""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for block in iter(lambda: f.read(8192), b""):
            sha256.update(block)
    return sha256.hexdigest()


async def main(dry_run: bool = False) -> None:
    import os

    sys.path.insert(0, "/app/src")
    os.environ.setdefault("ENVIRONMENT", "production")

    from app.core.config import settings

    conn = await asyncpg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        user=settings.postgres_user,
        password=settings.postgres_password,
        database=settings.postgres_db,
    )

    rows = await conn.fetch(
        "SELECT id, title, file_path FROM documents WHERE file_hash IS NULL ORDER BY created_at"
    )

    print(f"=== file_hash 백필 {'(DRY RUN)' if dry_run else ''} ===")
    print(f"NULL hash 레코드: {len(rows)}건\n")

    updated = 0
    skipped = 0
    not_found = 0

    for row in rows:
        doc_id = row[0]
        title = (row[1] or "N/A")[:50]
        file_path_str = row[2] or ""

        file_path = Path(file_path_str)
        if not file_path.exists():
            print(f"  SKIP (파일 없음): {title} | {file_path_str}")
            not_found += 1
            continue

        file_hash = compute_file_hash(file_path)

        if dry_run:
            print(f"  DRY: {title} | hash={file_hash[:16]}...")
            updated += 1
        else:
            await conn.execute(
                "UPDATE documents SET file_hash = $1, updated_at = NOW() WHERE id = $2",
                file_hash,
                doc_id,
            )
            print(f"  OK:  {title} | hash={file_hash[:16]}...")
            updated += 1

    await conn.close()

    print(f"\n=== 결과 ===")
    print(f"업데이트: {updated}건")
    print(f"파일 없음: {not_found}건")
    print(f"총: {updated + not_found + skipped}건")

    if dry_run:
        print("\n(DRY RUN - 실제 업데이트 없음. --dry-run 제거하여 실행)")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    asyncio.run(main(dry_run=dry_run))
