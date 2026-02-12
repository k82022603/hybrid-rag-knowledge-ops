#!/usr/bin/env python3
"""
전체 문서 ETL 파이프라인 실행 스크립트

knowledge_data/documents/ 하위 모든 디렉토리를 스캔하여
파싱 → 청킹 → 임베딩 → ES/Neo4j 적재를 수행합니다.

사용법 (컨테이너 내부):
    python /app/scripts/run_etl_full.py

최적 설정 (CPU 환경, 2026-02-10 확정):
    - batch_size: 4
    - max_text_length: 1000
    - workers: 1
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List

# Add app to path
sys.path.insert(0, "/app/src")
os.chdir("/app")

# Disable GPU
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

from app.core.logging import get_logger
from app.services.initial_data_loader import (
    InitialDataLoader,
    DataSource,
    DocType,
    LoadResult,
    LoadStatus,
)

logger = get_logger(__name__)

# Progress tracking file
PROGRESS_FILE = "/app/knowledge_data/etl_progress.json"

# Global counters for progress tracking
_progress = {
    "status": "initializing",
    "started_at": "",
    "total_files": 0,
    "processed": 0,
    "success": 0,
    "failed": 0,
    "skipped": 0,
    "chunks_total": 0,
    "current_file": "",
    "current_source": "",
    "elapsed_seconds": 0,
    "rate_per_minute": 0,
}
_start_time = 0.0


def save_progress():
    """진행 상황을 JSON 파일로 저장"""
    try:
        elapsed = time.monotonic() - _start_time
        _progress["elapsed_seconds"] = round(elapsed)
        processed = _progress["success"] + _progress["failed"] + _progress["skipped"]
        _progress["processed"] = processed
        if elapsed > 60:
            _progress["rate_per_minute"] = round(_progress["success"] / (elapsed / 60), 1)
        with open(PROGRESS_FILE, "w") as f:
            json.dump(_progress, f, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        logger.warning("Failed to save progress: %s", e)


def get_all_data_sources(base_dir: str) -> list:
    """documents/ 하위 모든 디렉토리를 데이터소스로 생성"""
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
        if not entry.is_dir():
            continue
        if entry.name.startswith("."):
            continue

        doc_type = type_map.get(entry.name.lower(), DocType.UNKNOWN)
        sources.append(
            DataSource(
                name=entry.name,
                path=str(entry),
                doc_type=doc_type,
                description=f"Auto-discovered: {entry.name}",
            )
        )

    return sources


# Monkey-patch _load_source to track progress per file
_original_load_source = InitialDataLoader._load_source


async def _patched_load_source(self, source: DataSource) -> List[LoadResult]:
    """진행 상황 추적이 포함된 _load_source"""
    logger.info("Processing data source: name=%s, path=%s", source.name, source.path)

    files = self._discover_files(source)
    if not files:
        logger.warning("No files found in data source: %s", source.name)
        return []

    logger.info("Found %d files in data source '%s'", len(files), source.name)
    _progress["current_source"] = source.name

    results: List[LoadResult] = []

    for i, file_info in enumerate(files):
        _progress["current_file"] = file_info.file_name
        print(
            f"  [{_progress['processed']+1}/{_progress['total_files']}] "
            f"{source.name}/{file_info.file_name}",
            flush=True,
        )

        result = await self._process_file(file_info)
        results.append(result)

        # Update progress counters
        if result.status == LoadStatus.SUCCESS:
            _progress["success"] += 1
            _progress["chunks_total"] += result.chunk_count
        elif result.status == LoadStatus.FAILED:
            _progress["failed"] += 1
        elif result.status == LoadStatus.SKIPPED:
            _progress["skipped"] += 1

        # Save progress every 10 files
        if (_progress["processed"] + 1) % 10 == 0:
            save_progress()

        if result.status == LoadStatus.FAILED and not self.continue_on_error:
            break

    save_progress()
    return results


# Apply patch
InitialDataLoader._load_source = _patched_load_source


async def main():
    global _start_time
    _start_time = time.monotonic()
    started_at = datetime.now().isoformat()
    _progress["started_at"] = started_at
    _progress["status"] = "running"

    print("=" * 60)
    print(f"ETL Pipeline Started: {started_at}")
    print("=" * 60)

    # 초기화
    loader = InitialDataLoader(
        project_root="/app",
        chunk_size=600,
        chunk_overlap=100,
        batch_size=4,       # CPU 최적값 (2026-02-10 확정)
        max_retries=2,
        continue_on_error=True,
        enable_embeddings=True,
        enable_entity_extraction=False,  # 엔티티 추출은 별도 단계
    )

    # 모든 디렉토리를 데이터소스로 등록
    base_dir = "/app/knowledge_data/documents"
    sources = get_all_data_sources(base_dir)

    print(f"\nData sources discovered: {len(sources)}")
    for src in sources:
        loader.add_source(src)
        print(f"  - {src.name}: {src.path}")

    # 파일 탐색
    all_files = loader.discover_files()
    total_files = len(all_files)
    _progress["total_files"] = total_files
    print(f"\nTotal files to process: {total_files}")
    save_progress()

    # ETL 실행
    print("\nStarting ETL processing...\n")
    summary = await loader.load_all()

    elapsed = time.monotonic() - _start_time
    completed_at = datetime.now().isoformat()

    # 최종 결과
    _progress.update({
        "status": "completed",
        "completed_at": completed_at,
        "total_files": summary.total_files,
        "success": summary.success_count,
        "failed": summary.failed_count,
        "skipped": summary.skipped_count,
        "chunks_total": summary.total_chunks,
        "entities_total": summary.total_entities,
        "elapsed_seconds": round(elapsed),
        "rate_per_minute": round(summary.success_count / (elapsed / 60), 1) if elapsed > 0 else 0,
        "success_rate": round(summary.success_rate * 100, 1),
    })
    save_progress()

    print("\n" + "=" * 60)
    print("ETL Pipeline Completed!")
    print("=" * 60)
    print(f"  Total files:    {summary.total_files}")
    print(f"  Success:        {summary.success_count}")
    print(f"  Failed:         {summary.failed_count}")
    print(f"  Skipped:        {summary.skipped_count}")
    print(f"  Total chunks:   {summary.total_chunks}")
    print(f"  Total entities: {summary.total_entities}")
    print(f"  Elapsed:        {int(elapsed)}s ({elapsed/60:.1f}m)")
    print(f"  Rate:           {_progress['rate_per_minute']} files/min")
    print(f"  Success rate:   {_progress['success_rate']}%")

    return _progress


if __name__ == "__main__":
    result = asyncio.run(main())
    print(f"\nResult saved to: {PROGRESS_FILE}")
