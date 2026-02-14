#!/usr/bin/env python3
"""
ETL Phase 1: 파싱 + 청킹만 실행 (임베딩 제외)

GPU 임베딩 전 모든 파일을 파싱하고 청킹하여 ES에 저장합니다.
임베딩은 pending 상태로 남겨두고, Phase 2(Colab GPU)에서 처리합니다.

사용법 (컨테이너 내부):
    python /app/scripts/run_etl_phase1_chunks.py

Phase 파이프라인:
    Phase 1 (이 스크립트): 파싱 → 청킹 → ES/PG 저장 (embedding=OFF)
    Phase 2 (Colab GPU): ES에서 pending 청크 추출 → GPU 임베딩 → ES 임포트
    Phase 3: 엔티티 추출 → Neo4j/PG 업데이트
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
os.environ.setdefault("OMP_NUM_THREADS", "6")
os.environ.setdefault("MKL_NUM_THREADS", "6")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "true")

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
PROGRESS_FILE = "/app/knowledge_data/etl_phase1_progress.json"

# Global counters
_progress = {
    "phase": "phase1_chunks",
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


# Monkey-patch _load_source for progress tracking
_original_load_source = InitialDataLoader._load_source


# 파일 크기 분류 기준 (P1-4 수정: 2026-02-14)
MAX_FILE_SIZE_MB = 30   # 대형: 스킵
MED_FILE_SIZE_MB = 5    # 중형: OCR OFF로 처리
# 소형 (<5MB): 전체 기능 (OCR + 테이블)


# 파일 유형별 처리 우선순위 (낮을수록 먼저 처리)
# MD/TXT -> HTML -> DOCX -> PPTX -> PDF 순서 (경량 파일 우선)
_EXT_PRIORITY = {
    ".md": 0, ".markdown": 0, ".txt": 0, ".log": 0,
    ".html": 1, ".htm": 1, ".svg": 1,
    ".ipynb": 2,
    ".docx": 3,
    ".pptx": 4,
    ".pdf": 5,
}


async def _patched_load_source(self, source: DataSource) -> List[LoadResult]:
    logger.info("Processing data source: name=%s, path=%s", source.name, source.path)

    files = self._discover_files(source)
    if not files:
        logger.warning("No files found in data source: %s", source.name)
        return []

    # 파일 유형별 정렬: 경량(MD/TXT) -> 중량(PDF) 순서 + 크기 오름차순
    files.sort(key=lambda f: (_EXT_PRIORITY.get(f.extension, 9), f.file_size))
    logger.info(
        "Found %d files in data source '%s' (sorted: fast-first)",
        len(files), source.name,
    )

    _progress["current_source"] = source.name

    results: List[LoadResult] = []

    for i, file_info in enumerate(files):
        _progress["current_file"] = file_info.file_name
        print(
            f"  [{_progress['processed']+1}/{_progress['total_files']}] "
            f"{source.name}/{file_info.file_name}",
            flush=True,
        )

        # 대용량 파일 스킵 (OOM 방지)
        file_path = Path(file_info.file_path) if hasattr(file_info, 'file_path') else None
        if file_path and file_path.exists():
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            if file_size_mb > MAX_FILE_SIZE_MB:
                logger.warning(
                    "Skipping oversized file: %s (%.1f MB > %d MB limit)",
                    file_info.file_name, file_size_mb, MAX_FILE_SIZE_MB,
                )
                _progress["skipped"] += 1
                save_progress()
                continue

        result = await self._process_file(file_info)
        results.append(result)

        if result.status == LoadStatus.SUCCESS:
            _progress["success"] += 1
            _progress["chunks_total"] += result.chunk_count
        elif result.status == LoadStatus.FAILED:
            _progress["failed"] += 1
        elif result.status == LoadStatus.SKIPPED:
            _progress["skipped"] += 1

        if (_progress["processed"] + 1) % 10 == 0:
            save_progress()

        if result.status == LoadStatus.FAILED and not self.continue_on_error:
            break

    save_progress()
    return results


InitialDataLoader._load_source = _patched_load_source


async def main():
    global _start_time
    _start_time = time.monotonic()
    started_at = datetime.now().isoformat()
    _progress["started_at"] = started_at
    _progress["status"] = "running"

    print("=" * 60)
    print(f"ETL Phase 1: Parse + Chunk (No Embedding)")
    print(f"Started: {started_at}")
    print("=" * 60)

    # Phase 1: 임베딩 OFF, 엔티티 OFF
    loader = InitialDataLoader(
        project_root="/app",
        chunk_size=1000,
        chunk_overlap=200,
        batch_size=4,
        max_retries=2,
        continue_on_error=True,
        enable_embeddings=False,        # Phase 1: 임베딩 건너뜀
        enable_entity_extraction=False,  # Phase 3에서 처리
    )

    base_dir = "/app/knowledge_data/documents"
    sources = get_all_data_sources(base_dir)

    print(f"\nData sources discovered: {len(sources)}")
    for src in sources:
        loader.add_source(src)
        print(f"  - {src.name}: {src.path}")

    all_files = loader.discover_files()
    total_files = len(all_files)
    _progress["total_files"] = total_files
    print(f"\nTotal files to process: {total_files}")
    save_progress()

    print("\nStarting Phase 1 (Parse + Chunk only)...\n")
    summary = await loader.load_all()

    elapsed = time.monotonic() - _start_time
    completed_at = datetime.now().isoformat()

    _progress.update({
        "status": "completed",
        "completed_at": completed_at,
        "total_files": summary.total_files,
        "success": summary.success_count,
        "failed": summary.failed_count,
        "skipped": summary.skipped_count,
        "chunks_total": summary.total_chunks,
        "elapsed_seconds": round(elapsed),
        "rate_per_minute": round(summary.success_count / (elapsed / 60), 1) if elapsed > 0 else 0,
        "success_rate": round(summary.success_rate * 100, 1),
    })
    save_progress()

    print("\n" + "=" * 60)
    print("Phase 1 Completed!")
    print("=" * 60)
    print(f"  Total files:    {summary.total_files}")
    print(f"  Success:        {summary.success_count}")
    print(f"  Failed:         {summary.failed_count}")
    print(f"  Skipped:        {summary.skipped_count}")
    print(f"  Total chunks:   {summary.total_chunks}")
    print(f"  Elapsed:        {int(elapsed)}s ({elapsed/60:.1f}m)")
    print(f"  Rate:           {_progress['rate_per_minute']} files/min")
    print(f"  Success rate:   {_progress['success_rate']}%")
    print(f"\nNext: Export pending chunks → Colab GPU embedding → Import")

    return _progress


if __name__ == "__main__":
    result = asyncio.run(main())
    print(f"\nProgress saved to: {PROGRESS_FILE}")
