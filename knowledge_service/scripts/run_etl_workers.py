#!/usr/bin/env python3
"""
2-Worker 병렬 ETL 파이프라인

asyncio.Semaphore(2)로 동시 2파일 처리.
파싱/청킹과 임베딩이 겹쳐서 처리량 개선 기대.

이미 처리된 파일은 file_hash dedup으로 자동 건너뜀.
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List

sys.path.insert(0, "/app/src")
os.chdir("/app")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

from app.core.logging import get_logger
from app.services.initial_data_loader import (
    InitialDataLoader,
    DataSource,
    DocType,
    LoadResult,
    LoadStatus,
    FileInfo,
)

logger = get_logger(__name__)

PROGRESS_FILE = "/tmp/etl_progress.json"
NUM_WORKERS = 2

# Global progress
_progress = {
    "status": "initializing",
    "started_at": "",
    "total_files": 0,
    "processed": 0,
    "success": 0,
    "failed": 0,
    "skipped": 0,
    "chunks_total": 0,
    "current_files": [],
    "current_source": "",
    "elapsed_seconds": 0,
    "rate_per_minute": 0,
    "workers": NUM_WORKERS,
}
_start_time = 0.0
_lock = asyncio.Lock()


def save_progress():
    try:
        elapsed = time.monotonic() - _start_time
        _progress["elapsed_seconds"] = round(elapsed)
        _progress["processed"] = _progress["success"] + _progress["failed"] + _progress["skipped"]
        if elapsed > 60:
            _progress["rate_per_minute"] = round(_progress["success"] / (elapsed / 60), 1)
        with open(PROGRESS_FILE, "w") as f:
            json.dump(_progress, f, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        logger.warning("Failed to save progress: %s", e)


def get_all_data_sources(base_dir: str) -> list:
    base = Path(base_dir)
    sources = []
    type_map = {
        "technical": DocType.TECHNICAL,
        "guides": DocType.GUIDE,
        "presentations": DocType.PRESENTATION,
        "policies": DocType.POLICY,
        "standards": DocType.STANDARD,
    }
    for entry in sorted(base.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        doc_type = type_map.get(entry.name.lower(), DocType.UNKNOWN)
        sources.append(DataSource(
            name=entry.name,
            path=str(entry),
            doc_type=doc_type,
            description=f"Auto-discovered: {entry.name}",
        ))
    return sources


async def process_file_worker(
    loader: InitialDataLoader,
    file_info: FileInfo,
    semaphore: asyncio.Semaphore,
    file_idx: int,
    total: int,
    source_name: str,
) -> LoadResult:
    """세마포어로 제한된 워커에서 파일 처리"""
    async with semaphore:
        async with _lock:
            _progress["current_files"].append(file_info.file_name)
            if len(_progress["current_files"]) > NUM_WORKERS:
                _progress["current_files"] = _progress["current_files"][-NUM_WORKERS:]

        processed = _progress["success"] + _progress["failed"] + _progress["skipped"]
        print(
            f"  [{processed+1}/{total}] W{semaphore._value+1 if hasattr(semaphore, '_value') else '?'} "
            f"{source_name}/{file_info.file_name}",
            flush=True,
        )

        result = await loader._process_file(file_info)

        async with _lock:
            if result.status == LoadStatus.SUCCESS:
                _progress["success"] += 1
                _progress["chunks_total"] += result.chunk_count
            elif result.status == LoadStatus.FAILED:
                _progress["failed"] += 1
            elif result.status == LoadStatus.SKIPPED:
                _progress["skipped"] += 1

            # Remove from current files
            if file_info.file_name in _progress["current_files"]:
                _progress["current_files"].remove(file_info.file_name)

            # Save every 5 files
            if (_progress["success"] + _progress["failed"] + _progress["skipped"]) % 5 == 0:
                save_progress()

        return result


async def load_source_parallel(
    loader: InitialDataLoader,
    source: DataSource,
    semaphore: asyncio.Semaphore,
    total: int,
) -> List[LoadResult]:
    """소스 내 파일들을 병렬 처리"""
    logger.info("Processing data source: name=%s, path=%s", source.name, source.path)

    files = loader._discover_files(source)
    if not files:
        logger.warning("No files found: %s", source.name)
        return []

    logger.info("Found %d files in '%s'", len(files), source.name)
    _progress["current_source"] = source.name

    # Create tasks for all files in this source
    tasks = [
        process_file_worker(loader, f, semaphore, i, total, source.name)
        for i, f in enumerate(files)
    ]

    # Run with concurrency limit via semaphore
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Handle exceptions
    final_results = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            logger.error("Worker exception for %s: %s", files[i].file_name, r)
            async with _lock:
                _progress["failed"] += 1
            final_results.append(LoadResult(
                file_path=str(files[i].file_path),
                file_name=files[i].file_name,
                status=LoadStatus.FAILED,
                error_message=str(r),
            ))
        else:
            final_results.append(r)

    save_progress()

    success = sum(1 for r in final_results if r.status == LoadStatus.SUCCESS)
    failed = sum(1 for r in final_results if r.status == LoadStatus.FAILED)
    skipped = sum(1 for r in final_results if r.status == LoadStatus.SKIPPED)
    logger.info(
        "Source '%s' done: total=%d, success=%d, failed=%d, skipped=%d",
        source.name, len(final_results), success, failed, skipped,
    )

    return final_results


async def main():
    global _start_time
    _start_time = time.monotonic()
    started_at = datetime.now().isoformat()
    _progress["started_at"] = started_at
    _progress["status"] = "running"

    print("=" * 60)
    print(f"ETL Pipeline Started (Workers={NUM_WORKERS}): {started_at}")
    print("=" * 60)

    loader = InitialDataLoader(
        project_root="/app",
        chunk_size=600,
        chunk_overlap=100,
        batch_size=4,
        max_retries=2,
        continue_on_error=True,
        enable_embeddings=True,
        enable_entity_extraction=False,
    )

    base_dir = "/app/knowledge_data/documents"
    sources = get_all_data_sources(base_dir)

    print(f"\nData sources: {len(sources)}")
    for src in sources:
        loader.add_source(src)
        print(f"  - {src.name}")

    all_files = loader.discover_files()
    total_files = len(all_files)
    _progress["total_files"] = total_files
    print(f"\nTotal files: {total_files}")
    print(f"Workers: {NUM_WORKERS}")
    save_progress()

    # Semaphore for concurrency control
    semaphore = asyncio.Semaphore(NUM_WORKERS)

    print(f"\nStarting parallel ETL (semaphore={NUM_WORKERS})...\n")

    all_results = []
    for source in loader.data_sources:
        results = await load_source_parallel(loader, source, semaphore, total_files)
        all_results.extend(results)

    elapsed = time.monotonic() - _start_time

    total = len(all_results)
    success = sum(1 for r in all_results if r.status == LoadStatus.SUCCESS)
    failed = sum(1 for r in all_results if r.status == LoadStatus.FAILED)
    skipped = sum(1 for r in all_results if r.status == LoadStatus.SKIPPED)
    chunks = sum(r.chunk_count for r in all_results if r.chunk_count)

    _progress.update({
        "status": "completed",
        "completed_at": datetime.now().isoformat(),
        "total_files": total,
        "success": success,
        "failed": failed,
        "skipped": skipped,
        "chunks_total": chunks,
        "elapsed_seconds": round(elapsed),
        "rate_per_minute": round(success / (elapsed / 60), 1) if elapsed > 60 else 0,
        "success_rate": round(success / total * 100, 1) if total > 0 else 0,
    })
    save_progress()

    print("\n" + "=" * 60)
    print(f"ETL Pipeline Completed! (Workers={NUM_WORKERS})")
    print("=" * 60)
    print(f"  Total:    {total}")
    print(f"  Success:  {success}")
    print(f"  Failed:   {failed}")
    print(f"  Skipped:  {skipped}")
    print(f"  Chunks:   {chunks}")
    print(f"  Elapsed:  {int(elapsed)}s ({elapsed/60:.1f}m)")
    print(f"  Rate:     {_progress['rate_per_minute']} files/min")
    print(f"  Success%: {_progress['success_rate']}%")


if __name__ == "__main__":
    asyncio.run(main())
    print(f"\nSaved: {PROGRESS_FILE}")
