#!/usr/bin/env python3
"""Batch document loading script - handles special characters in filenames"""
import asyncio
import os
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/app')
os.chdir('/app')


async def process_single_file(file_path: str, doc_type_str: str):
    """단일 파일 ETL 처리"""
    from app.services.initial_data_loader import InitialDataLoader, DocType, FileInfo

    fpath = Path(file_path)
    if not fpath.exists():
        print(f'  FILE NOT FOUND: {fpath}')
        return 'failed'

    doc_type = DocType.TECHNICAL if doc_type_str == 'TECHNICAL' else DocType.POLICY

    loader = InitialDataLoader(
        chunk_size=500,
        chunk_overlap=50,
        batch_size=32,
        max_retries=2,
        continue_on_error=True,
        enable_embeddings=True,
        enable_entity_extraction=True,
    )

    stat = fpath.stat()
    file_info = FileInfo(
        file_path=fpath,
        file_name=fpath.name,
        file_size=stat.st_size,
        extension=fpath.suffix.lower(),
        source_name='batch2',
        doc_type=doc_type,
        modified_at=datetime.fromtimestamp(stat.st_mtime),
    )

    start = time.monotonic()
    result = await loader._process_file(file_info)
    elapsed = time.monotonic() - start

    status_str = result.status.value.upper()
    print(f'  {status_str}: chunks={result.chunk_count} entities={result.entity_count} time={elapsed:.0f}s')
    if result.error_message:
        print(f'  ERROR: {result.error_message}')

    return result.status.value


async def main():
    # Batch 2-2: 남은 소형 4건 + 중형 3건 + 대형 3건
    files = [
        # 소형 (이전 배치에서 특수문자로 실패한 4건)
        ("/app/knowledge_data/documents/AI/OpenAI\u2019s GPT o1 \u2014 A Leap in AI Reasoning.pdf", "TECHNICAL"),
        ("/app/knowledge_data/documents/AI/RAG/Reranking (Korean).pdf", "TECHNICAL"),
        ("/app/knowledge_data/documents/AI/RAG/s3 - You Don\u2019t Need That Much Data to Train a Search Agent via RL-2505.14146v1.pdf", "TECHNICAL"),
        ("/app/knowledge_data/documents/AI/AIAgent/\ub7ad\uccb4\uc778\ucf54\ub9ac\uc544 \ubc0b\uc5c5 2024-0226-\uc774\uc7ac\uc11d.pdf", "TECHNICAL"),
        # 중형 (5~10MB)
        ("/app/knowledge_data/documents/\ubc95\ub960\uc790\ub8cc/2015\uc9c0\ubc29\uc790\uce58_\uad00\uacc4\ubc95\ub839\uc9d1.pdf", "POLICY"),
        ("/app/knowledge_data/documents/AI/\ube44\uc988\ub2c8\uc2a4\uc5d0 \uc2e4\uc81c\ub85c \ud65c\uc6a9 \uac00\ub2a5\ud55c LLM \uc11c\ube44\uc2a4 \ub9cc\ub4e4\uae30.pdf", "TECHNICAL"),
        ("/app/knowledge_data/documents/\ubc95\ub960\uc790\ub8cc/\uc18c\ubc29\uc2dc\uc124\ubc95 \ubc0f \ud654\uc7ac\uc608\ubc29\ubc95\ub839\uc9d1.pdf", "POLICY"),
        # 대형 (10~20MB)
        ("/app/knowledge_data/documents/AI/AIAgent/LLM \uae30\ubc18 AI \uc5d0\uc774\uc804\ud2b8 \uae30\ucd08\uc640 \uc2e4\uc2b5-20250516-\uac15\uc758\ubc30\ud3ec\uc6a9.pdf", "TECHNICAL"),
        ("/app/knowledge_data/documents/AI/\uc544\ud0a4\ud14d\ucc98\ud300 AI\ud504\ub85c\uc81d\ud2b8 \uc774\ud574 \uc6cc\ud06c\uc0f5-20250108.pdf", "TECHNICAL"),
        ("/app/knowledge_data/documents/AI/RAG/\ub525\ub7ec\ub2dd\uacfc RAG\ub97c \ud65c\uc6a9\ud55c AI \uc751\uc6a9 \uae30\ucd08\uacfc\uc815-20250516-\uac15\uc758\ubc30\ud3ec\uc6a9.pdf", "TECHNICAL"),
    ]

    print(f'=== Batch 2-2 Start: {len(files)} files (small 4 + medium 3 + large 3) ===')
    print(f'Time: {time.strftime("%H:%M:%S")}')
    print()

    results = {'success': 0, 'failed': 0, 'skip': 0, 'skipped': 0}
    total_start = time.monotonic()

    for i, (fpath, dtype) in enumerate(files, 1):
        fname = os.path.basename(fpath)
        try:
            fsize = os.path.getsize(fpath) / 1024 / 1024
        except FileNotFoundError:
            fsize = 0
        print(f'[{i}/{len(files)}] {fname} ({fsize:.1f}MB)')
        status = await process_single_file(fpath, dtype)
        results[status] = results.get(status, 0) + 1
        # Memory check
        try:
            with open('/sys/fs/cgroup/memory.current') as f:
                mem_gb = int(f.read().strip()) / 1024**3
                print(f'  Memory: {mem_gb:.1f}GB / 10GB')
        except Exception:
            pass
        print()

    total_elapsed = time.monotonic() - total_start
    print(f'=== Batch 2-2 Complete ===')
    print(f'Success: {results.get("success", 0)} | Failed: {results.get("failed", 0)} | Skipped: {results.get("skip", 0) + results.get("skipped", 0)}')
    print(f'Total time: {total_elapsed:.0f}s ({total_elapsed/60:.1f}min)')


if __name__ == '__main__':
    asyncio.run(main())
