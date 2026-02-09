#!/usr/bin/env python3
"""Single file loader WITHOUT embedding - saves ~2GB memory by skipping BGE-M3 model"""
import asyncio
import os
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/app')
os.chdir('/app')


async def process_single_file(file_path: str, doc_type_str: str):
    """단일 파일 ETL 처리 (임베딩 비활성화)"""
    from app.services.initial_data_loader import InitialDataLoader, DocType, FileInfo

    fpath = Path(file_path)
    if not fpath.exists():
        print(f'FILE NOT FOUND: {fpath}')
        return 'failed'

    doc_type = DocType.TECHNICAL if doc_type_str == 'TECHNICAL' else DocType.POLICY

    loader = InitialDataLoader(
        chunk_size=500,
        chunk_overlap=50,
        batch_size=32,
        max_retries=2,
        continue_on_error=True,
        enable_embeddings=False,       # Skip BGE-M3 (~2GB savings)
        enable_entity_extraction=True,  # Keep DeepSeek entity extraction (API-based, low memory)
    )

    stat = fpath.stat()
    file_info = FileInfo(
        file_path=fpath,
        file_name=fpath.name,
        file_size=stat.st_size,
        extension=fpath.suffix.lower(),
        source_name='batch3',
        doc_type=doc_type,
        modified_at=datetime.fromtimestamp(stat.st_mtime),
    )

    start = time.monotonic()
    result = await loader._process_file(file_info)
    elapsed = time.monotonic() - start

    status_str = result.status.value.upper()
    print(f'RESULT: {status_str}')
    print(f'CHUNKS: {result.chunk_count}')
    print(f'ENTITIES: {result.entity_count}')
    print(f'TIME: {elapsed:.0f}s')
    if result.error_message:
        print(f'ERROR: {result.error_message}')

    # Memory check
    try:
        with open('/sys/fs/cgroup/memory.current') as f:
            mem_bytes = int(f.read().strip())
            mem_gb = mem_bytes / 1024**3
            print(f'MEMORY: {mem_gb:.1f}GB')
    except Exception:
        pass

    return result.status.value


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: python load_single_noembedding.py <file_path> <doc_type>')
        sys.exit(1)
    file_path = sys.argv[1]
    doc_type = sys.argv[2]
    result = asyncio.run(process_single_file(file_path, doc_type))
    sys.exit(0 if result == 'success' else 1)
