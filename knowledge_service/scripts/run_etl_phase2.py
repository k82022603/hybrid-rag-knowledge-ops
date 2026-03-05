#!/usr/bin/env python3
# DEPRECATED: etl_cli.py phase1 으로 대체 (STORY-125). Sprint 10에서 삭제 예정.
"""
ETL Phase 2 - 바이너리 파일 처리 (PDF/PPTX/DOCX/XLSX)

파일 크기순 정렬 (작은 것부터), 임베딩 OFF, 2워커.
file_hash dedup으로 이미 처리된 파일 자동 건너뜀.
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
NUM_WORKERS = 2  # 바이너리 파싱은 CPU 집중이므로 2워커
BINARY_EXTENSIONS = {'.pdf', '.pptx', '.docx', '.xlsx', '.doc'}

_progress = {
    "status": "initializing",
    "phase": "phase2-binary",
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
        if elapsed > 30 and _progress["success"] > 0:
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
    total: int,
    idx: int,
) -> LoadResult:
    async with semaphore:
        file_size_mb = file_info.file_size / (1024 * 1024)
        ext = file_info.file_path.suffix.lower()

        async with _lock:
            _progress["current_files"].append(file_info.file_name)
            if len(_progress["current_files"]) > NUM_WORKERS:
                _progress["current_files"] = _progress["current_files"][-NUM_WORKERS:]

        print(
            f"  [{idx+1}/{total}] {file_size_mb:.1f}MB {ext} {file_info.source_name}/{file_info.file_name}",
            flush=True,
        )

        start = time.monotonic()
        result = await loader._process_file(file_info)
        elapsed = time.monotonic() - start

        async with _lock:
            if result.status == LoadStatus.SUCCESS:
                _progress["success"] += 1
                _progress["chunks_total"] += result.chunk_count
                print(f"    OK: {result.chunk_count} chunks, {elapsed:.1f}s", flush=True)
            elif result.status == LoadStatus.FAILED:
                _progress["failed"] += 1
                print(f"    FAIL: {result.error_message[:80] if result.error_message else 'unknown'}", flush=True)
            elif result.status == LoadStatus.SKIPPED:
                _progress["skipped"] += 1

            if file_info.file_name in _progress["current_files"]:
                _progress["current_files"].remove(file_info.file_name)

            total_done = _progress["success"] + _progress["failed"] + _progress["skipped"]
            if total_done % 5 == 0:
                save_progress()

        return result


async def main():
    global _start_time
    _start_time = time.monotonic()
    started_at = datetime.now().isoformat()
    _progress["started_at"] = started_at
    _progress["status"] = "running"

    print("=" * 60)
    print(f"ETL Phase 2 (BINARY FILES) Started: {started_at}")
    print(f"Workers={NUM_WORKERS}, Embedding=OFF, Types={BINARY_EXTENSIONS}")
    print("=" * 60)

    loader = InitialDataLoader(
        project_root="/app",
        chunk_size=600,
        chunk_overlap=100,
        batch_size=4,
        max_retries=2,
        continue_on_error=True,
        enable_embeddings=False,
        enable_entity_extraction=False,
    )

    base_dir = "/app/knowledge_data/documents"
    sources = get_all_data_sources(base_dir)
    for src in sources:
        loader.add_source(src)

    # 모든 파일 탐색 후 바이너리 파일만 필터링
    all_files = loader.discover_files()

    binary_files = [
        f for f in all_files
        if f.file_path.suffix.lower() in BINARY_EXTENSIONS
    ]

    # 크기순 정렬 (작은 것부터)
    binary_files.sort(key=lambda f: f.file_size)

    total = len(binary_files)
    _progress["total_files"] = total
    print(f"\nBinary files to process: {total}")
    print(f"Size range: {binary_files[0].file_size/1024:.0f}KB ~ {binary_files[-1].file_size/1024/1024:.1f}MB")
    print(f"Workers: {NUM_WORKERS}")

    # 크기 분포
    under_1mb = sum(1 for f in binary_files if f.file_size < 1024*1024)
    under_5mb = sum(1 for f in binary_files if f.file_size < 5*1024*1024)
    under_10mb = sum(1 for f in binary_files if f.file_size < 10*1024*1024)
    print(f"  <1MB: {under_1mb} | <5MB: {under_5mb} | <10MB: {under_10mb} | total: {total}")
    save_progress()

    semaphore = asyncio.Semaphore(NUM_WORKERS)

    print(f"\nStarting Phase 2 (smallest first)...\n")

    tasks = [
        process_file_worker(loader, f, semaphore, total, i)
        for i, f in enumerate(binary_files)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Handle exceptions
    final_results = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            logger.error("Exception: %s: %s", binary_files[i].file_name, r)
            _progress["failed"] += 1
            final_results.append(LoadResult(
                file_path=str(binary_files[i].file_path),
                file_name=binary_files[i].file_name,
                status=LoadStatus.FAILED,
                error_message=str(r),
            ))
        else:
            final_results.append(r)

    elapsed = time.monotonic() - _start_time
    success = sum(1 for r in final_results if r.status == LoadStatus.SUCCESS)
    failed = sum(1 for r in final_results if r.status == LoadStatus.FAILED)
    skipped = sum(1 for r in final_results if r.status == LoadStatus.SKIPPED)
    chunks = sum(r.chunk_count for r in final_results if r.chunk_count)

    _progress.update({
        "status": "completed",
        "completed_at": datetime.now().isoformat(),
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
    print(f"ETL Phase 2 (BINARY) Completed!")
    print("=" * 60)
    print(f"  Total:    {total}")
    print(f"  Success:  {success}")
    print(f"  Failed:   {failed}")
    print(f"  Skipped:  {skipped}")
    print(f"  Chunks:   {chunks}")
    print(f"  Elapsed:  {int(elapsed)}s ({elapsed/60:.1f}m)")
    print(f"  Rate:     {_progress['rate_per_minute']} files/min")
    print(f"  Success%: {_progress['success_rate']}%")

    # 실패 파일 목록
    failed_files = [r for r in final_results if r.status == LoadStatus.FAILED]
    if failed_files:
        print(f"\n  Failed files ({len(failed_files)}):")
        for r in failed_files[:20]:
            print(f"    - {r.file_name}: {r.error_message[:60] if r.error_message else '?'}")


if __name__ == "__main__":
    asyncio.run(main())
    print(f"\nSaved: {PROGRESS_FILE}")
