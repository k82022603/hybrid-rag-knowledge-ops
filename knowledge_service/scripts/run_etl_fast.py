#!/usr/bin/env python3
"""
고속 ETL 파이프라인 (Phase 1: 임베딩 전용)

최적화 전략 (78시간 -> 10-12시간):
  1. Entity Extraction 비활성화 (Phase 2로 분리) -> 3-4x 가속
  2. Sparse 벡터 비활성화 (Dense만 생성) -> 1.3x 가속
  3. 동시 N파일 처리 (asyncio.Semaphore) -> 1.5-2x 가속
  4. 임베딩/저장 파이프라인 병렬화
  5. Neo4j UNWIND 벌크 저장

예상 속도: 140-200 files/hour (기존 23 files/hour 대비 6-8x)

사용법 (컨테이너 내부):
    python /app/scripts/run_etl_fast.py
    python /app/scripts/run_etl_fast.py --concurrency 3 --sparse
    python /app/scripts/run_etl_fast.py --resume  # 중단 지점부터 재개

Phase 2 (엔티티 추출)는 별도 실행:
    python /app/scripts/run_etl_phase2_entities.py
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
    FileInfo,
    LoadResult,
    LoadStatus,
)

logger = get_logger(__name__)

# Progress tracking
PROGRESS_FILE = "/app/knowledge_data/etl_fast_progress.json"
COMPLETED_FILE = "/app/knowledge_data/etl_completed_files.json"

_progress = {
    "status": "initializing",
    "mode": "fast_phase1",
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
    "concurrency": 1,
    "sparse_enabled": False,
}
_start_time = 0.0
_completed_files: set = set()
_lock = asyncio.Lock()


def save_progress():
    """진행 상황을 JSON 파일로 저장"""
    try:
        elapsed = time.monotonic() - _start_time
        _progress["elapsed_seconds"] = round(elapsed)
        processed = _progress["success"] + _progress["failed"] + _progress["skipped"]
        _progress["processed"] = processed
        if elapsed > 60 and _progress["success"] > 0:
            _progress["rate_per_minute"] = round(
                _progress["success"] / (elapsed / 60), 1
            )
            remaining = _progress["total_files"] - processed
            eta_minutes = remaining / _progress["rate_per_minute"] if _progress["rate_per_minute"] > 0 else 0
            _progress["eta_minutes"] = round(eta_minutes, 1)
            _progress["eta_hours"] = round(eta_minutes / 60, 1)
        with open(PROGRESS_FILE, "w") as f:
            json.dump(_progress, f, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        logger.warning("Failed to save progress: %s", e)


def save_completed_files():
    """완료된 파일 목록 저장 (resume용)"""
    try:
        with open(COMPLETED_FILE, "w") as f:
            json.dump(sorted(list(_completed_files)), f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning("Failed to save completed files: %s", e)


def load_completed_files() -> set:
    """이전 실행에서 완료된 파일 목록 로드"""
    try:
        if Path(COMPLETED_FILE).exists():
            with open(COMPLETED_FILE) as f:
                return set(json.load(f))
    except Exception as e:
        logger.warning("Failed to load completed files: %s", e)
    return set()


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
        if not entry.is_dir() or entry.name.startswith("."):
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


# ---------------------------------------------------------------------------
# Monkey-patch: 동시 파일 처리 + sparse 제어
# ---------------------------------------------------------------------------

def patch_for_fast_mode(
    loader: InitialDataLoader,
    concurrency: int = 2,
    sparse_enabled: bool = False,
):
    """InitialDataLoader를 고속 모드로 패치

    1. _load_source: 세마포어 기반 동시 처리
    2. _generate_embeddings: sparse 제어
    3. _store_to_neo4j: UNWIND 벌크 저장
    4. _process_file: 임베딩/엔티티 동시 실행 (엔티티 활성화 시)
    """

    semaphore = asyncio.Semaphore(concurrency)

    # --- Patch 1: 동시 파일 처리 ---
    async def _fast_load_source(self, source: DataSource) -> List[LoadResult]:
        """세마포어 기반 동시 파일 처리"""
        logger.info(
            "Processing data source (fast): name=%s, path=%s, concurrency=%d",
            source.name, source.path, concurrency,
        )

        files = self._discover_files(source)
        if not files:
            logger.warning("No files found in data source: %s", source.name)
            return []

        logger.info(
            "Found %d files in data source '%s'", len(files), source.name
        )
        _progress["current_source"] = source.name

        # resume: 이미 완료된 파일 건너뛰기
        pending_files = [
            f for f in files
            if str(f.file_path) not in _completed_files
        ]
        skipped_count = len(files) - len(pending_files)
        if skipped_count > 0:
            logger.info(
                "Skipping %d already-completed files in '%s'",
                skipped_count, source.name,
            )
            _progress["skipped"] += skipped_count

        results: List[LoadResult] = []

        async def process_one(file_info: FileInfo) -> LoadResult:
            async with semaphore:
                async with _lock:
                    _progress["current_files"].append(file_info.file_name)
                    if len(_progress["current_files"]) > concurrency:
                        _progress["current_files"] = _progress["current_files"][-concurrency:]

                print(
                    f"  [{_progress['processed']+1}/{_progress['total_files']}] "
                    f"{source.name}/{file_info.file_name}",
                    flush=True,
                )

                result = await self._process_file(file_info)

                async with _lock:
                    if result.status == LoadStatus.SUCCESS:
                        _progress["success"] += 1
                        _progress["chunks_total"] += result.chunk_count
                        _completed_files.add(str(file_info.file_path))
                    elif result.status == LoadStatus.FAILED:
                        _progress["failed"] += 1
                    elif result.status == LoadStatus.SKIPPED:
                        _progress["skipped"] += 1
                        _completed_files.add(str(file_info.file_path))

                    if (_progress["processed"] + 1) % 5 == 0:
                        save_progress()
                    if (_progress["processed"] + 1) % 20 == 0:
                        save_completed_files()

                    if file_info.file_name in _progress["current_files"]:
                        _progress["current_files"].remove(file_info.file_name)

                return result

        # 배치 단위로 동시 처리
        batch_size = concurrency * 2
        for i in range(0, len(pending_files), batch_size):
            batch = pending_files[i:i + batch_size]
            batch_results = await asyncio.gather(
                *[process_one(f) for f in batch],
                return_exceptions=True,
            )
            for j, br in enumerate(batch_results):
                if isinstance(br, Exception):
                    logger.error(
                        "File processing exception: %s - %s",
                        batch[j].file_name, br,
                    )
                    results.append(LoadResult(
                        file_path=str(batch[j].file_path),
                        file_name=batch[j].file_name,
                        status=LoadStatus.FAILED,
                        error_message=str(br),
                    ))
                    async with _lock:
                        _progress["failed"] += 1
                else:
                    results.append(br)

        save_progress()
        save_completed_files()
        return results

    # --- Patch 2: sparse 제어 ---
    _original_generate_embeddings = InitialDataLoader._generate_embeddings

    async def _fast_generate_embeddings(self, chunks):
        """sparse 벡터 생성 제어"""
        if not chunks:
            return None
        try:
            chunk_ids = [chunk.id for chunk in chunks]
            texts = [chunk.content for chunk in chunks]
            embeddings = await self.embedding_service.aembed_chunks(
                chunk_ids=chunk_ids,
                texts=texts,
                return_sparse=sparse_enabled,
            )
            logger.debug(
                "Generated embeddings (fast): %d chunks, sparse=%s",
                len(embeddings), sparse_enabled,
            )
            return embeddings
        except Exception as e:
            logger.error("Embedding generation failed: %s", e)
            raise

    # --- Patch 3: Neo4j UNWIND 벌크 저장 ---
    _original_store_to_neo4j = InitialDataLoader._store_to_neo4j

    async def _fast_store_to_neo4j(
        self,
        document_id: str,
        file_info,
        chunks,
        entities,
        metadata,
    ) -> None:
        """UNWIND 기반 벌크 Neo4j 저장"""
        try:
            from app.core.config import settings as _settings

            logger.info(
                "Storing to Neo4j (bulk): doc_id=%s, chunks=%d, entities=%d",
                document_id[:8], len(chunks), len(entities),
            )

            try:
                from neo4j import AsyncGraphDatabase

                driver = AsyncGraphDatabase.driver(
                    _settings.neo4j_uri,
                    auth=(_settings.neo4j_user, _settings.neo4j_password or ""),
                )

                try:
                    async with driver.session() as session:
                        # Document 노드
                        await session.run(
                            """
                            MERGE (d:Document {id: $doc_id})
                            SET d.title = $title,
                                d.file_path = $file_path,
                                d.doc_type = $doc_type,
                                d.created_at = datetime()
                            """,
                            doc_id=document_id,
                            title=metadata.get("title", file_info.file_name),
                            file_path=str(file_info.file_path),
                            doc_type=metadata.get("doc_type", "unknown"),
                        )

                        # Chunk 노드 벌크 생성 (UNWIND)
                        if chunks:
                            chunk_data = [
                                {
                                    "id": c.id,
                                    "content": c.content[:500],
                                    "idx": c.chunk_index,
                                    "heading": c.heading,
                                }
                                for c in chunks
                            ]
                            await session.run(
                                """
                                UNWIND $chunks AS chunk
                                MERGE (c:Chunk {id: chunk.id})
                                SET c.content = chunk.content,
                                    c.chunk_index = chunk.idx,
                                    c.heading = chunk.heading
                                WITH c, chunk
                                MATCH (d:Document {id: $doc_id})
                                MERGE (c)-[:PART_OF]->(d)
                                """,
                                chunks=chunk_data,
                                doc_id=document_id,
                            )

                        # Entity 노드 벌크 생성 (UNWIND)
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

                        logger.info(
                            "Neo4j bulk storage completed: doc=%s, chunks=%d, entities=%d",
                            document_id[:8], len(chunks), len(entities),
                        )
                finally:
                    await driver.close()

            except ImportError:
                logger.warning("neo4j package not installed, skipping Neo4j storage")
            except Exception as e:
                logger.warning("Neo4j storage failed (non-critical): %s", e)

        except Exception as e:
            logger.error("Neo4j storage error: %s", e)

    # Apply patches
    loader._load_source = _fast_load_source.__get__(loader, InitialDataLoader)
    loader._generate_embeddings = _fast_generate_embeddings.__get__(loader, InitialDataLoader)
    loader._store_to_neo4j = _fast_store_to_neo4j.__get__(loader, InitialDataLoader)

    # --- Patch 4: 임베딩/엔티티 동시 실행 (엔티티 활성화 시에만 의미) ---
    if loader.enable_entity_extraction:
        _original_process_file = InitialDataLoader._process_file

        async def _fast_process_file(self, file_info: FileInfo) -> LoadResult:
            """임베딩과 엔티티 추출을 동시 실행"""
            import hashlib
            from uuid import uuid4

            result = LoadResult(
                file_path=str(file_info.file_path),
                file_name=file_info.file_name,
                status=LoadStatus.IN_PROGRESS,
            )
            start_time = time.monotonic()

            # Step 0: 중복 검사
            file_hash = self._compute_file_hash(file_info.file_path)
            existing_doc_id = await self._check_duplicate(
                file_hash=file_hash, file_path=str(file_info.file_path),
            )
            if existing_doc_id:
                result.status = LoadStatus.SKIPPED
                result.document_id = existing_doc_id
                result.error_message = f"Duplicate: {existing_doc_id[:8]}"
                result.processing_time_ms = (time.monotonic() - start_time) * 1000
                return result

            for attempt in range(self.max_retries):
                try:
                    # Step 1: 파싱
                    parsed_doc = self._parse_file(file_info)
                    if parsed_doc is None:
                        result.status = LoadStatus.SKIPPED
                        result.error_message = "Empty parse"
                        break

                    # Step 2: 청킹
                    chunks = self._chunk_document(parsed_doc)
                    result.chunk_count = len(chunks)
                    if not chunks:
                        result.status = LoadStatus.SKIPPED
                        result.error_message = "No chunks"
                        break

                    # Step 3: 메타데이터
                    metadata = self._extract_metadata(file_info, parsed_doc)

                    # Step 4+5: 임베딩과 엔티티를 **동시** 실행
                    embeddings = None
                    entities = []

                    tasks = []
                    if self.enable_embeddings:
                        tasks.append(("embeddings", self._generate_embeddings(chunks)))
                    if self.enable_entity_extraction:
                        tasks.append(("entities", self._extract_entities(parsed_doc)))

                    if tasks:
                        task_results = await asyncio.gather(
                            *[t[1] for t in tasks],
                            return_exceptions=True,
                        )
                        for (task_name, _), task_result in zip(tasks, task_results):
                            if isinstance(task_result, Exception):
                                logger.warning(
                                    "%s failed for %s: %s (continuing)",
                                    task_name, file_info.file_name, task_result,
                                )
                            elif task_name == "embeddings":
                                embeddings = task_result
                            elif task_name == "entities":
                                entities = task_result or []
                                result.entity_count = len(entities)

                    # Step 6: 저장
                    document_id = str(uuid4())
                    effective_doc_id = await self._store_document(
                        document_id=document_id,
                        file_info=file_info,
                        parsed_doc=parsed_doc,
                        chunks=chunks,
                        embeddings=embeddings,
                        entities=entities,
                        metadata=metadata,
                        file_hash=file_hash,
                    )

                    result.document_id = effective_doc_id
                    result.status = LoadStatus.SUCCESS
                    result.processing_time_ms = (time.monotonic() - start_time) * 1000
                    break

                except Exception as e:
                    logger.warning(
                        "Fast processing failed [%d/%d]: %s - %s",
                        attempt + 1, self.max_retries, file_info.file_name, e,
                    )
                    result.error_message = str(e)
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                    else:
                        result.status = LoadStatus.FAILED
                        result.processing_time_ms = (time.monotonic() - start_time) * 1000

            return result

        loader._process_file = _fast_process_file.__get__(loader, InitialDataLoader)


async def main():
    global _start_time, _completed_files

    parser = argparse.ArgumentParser(description="Fast ETL Pipeline (Phase 1)")
    parser.add_argument(
        "--concurrency", "-c", type=int, default=2,
        help="동시 처리 파일 수 (기본: 2, 권장: 2-3)",
    )
    parser.add_argument(
        "--sparse", action="store_true", default=False,
        help="Sparse 벡터 생성 활성화 (기본: 비활성화)",
    )
    parser.add_argument(
        "--entities", action="store_true", default=False,
        help="엔티티 추출 활성화 (기본: 비활성화, Phase 2에서 처리)",
    )
    parser.add_argument(
        "--resume", action="store_true", default=False,
        help="이전 실행에서 중단된 지점부터 재개",
    )
    parser.add_argument(
        "--batch-size", type=int, default=4,
        help="임베딩 배치 크기 (기본: 4, CPU 최적값)",
    )
    args = parser.parse_args()

    _start_time = time.monotonic()
    started_at = datetime.now().isoformat()
    _progress["started_at"] = started_at
    _progress["status"] = "running"
    _progress["concurrency"] = args.concurrency
    _progress["sparse_enabled"] = args.sparse

    if args.resume:
        _completed_files = load_completed_files()
        print(f"Resuming: {len(_completed_files)} files already completed")

    print("=" * 60)
    print(f"Fast ETL Pipeline (Phase 1) Started: {started_at}")
    print(f"  Concurrency: {args.concurrency}")
    print(f"  Sparse vectors: {args.sparse}")
    print(f"  Entity extraction: {args.entities}")
    print(f"  Resume mode: {args.resume}")
    print(f"  Batch size: {args.batch_size}")
    print("=" * 60)

    # 초기화 (엔티티 추출 비활성화가 핵심)
    loader = InitialDataLoader(
        project_root="/app",
        chunk_size=1000,
        chunk_overlap=200,
        batch_size=args.batch_size,
        max_retries=2,
        continue_on_error=True,
        enable_embeddings=True,
        enable_entity_extraction=args.entities,
    )

    # 고속 모드 패치 적용
    patch_for_fast_mode(
        loader,
        concurrency=args.concurrency,
        sparse_enabled=args.sparse,
    )

    # 데이터소스 등록
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
    if args.resume:
        print(f"Already completed: {len(_completed_files)}")
        print(f"Remaining: {total_files - len(_completed_files)}")
    save_progress()

    # ETL 실행
    print("\nStarting Fast ETL processing...\n")
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
        "rate_per_minute": round(
            summary.success_count / (elapsed / 60), 1
        ) if elapsed > 0 else 0,
        "success_rate": round(summary.success_rate * 100, 1),
    })
    save_progress()
    save_completed_files()

    print("\n" + "=" * 60)
    print("Fast ETL Pipeline (Phase 1) Completed!")
    print("=" * 60)
    print(f"  Total files:    {summary.total_files}")
    print(f"  Success:        {summary.success_count}")
    print(f"  Failed:         {summary.failed_count}")
    print(f"  Skipped:        {summary.skipped_count}")
    print(f"  Total chunks:   {summary.total_chunks}")
    print(f"  Total entities: {summary.total_entities}")
    print(f"  Elapsed:        {int(elapsed)}s ({elapsed/60:.1f}m, {elapsed/3600:.1f}h)")
    print(f"  Rate:           {_progress['rate_per_minute']} files/min")
    print(f"  Success rate:   {_progress['success_rate']}%")
    print()
    if not args.entities:
        print("NOTE: Entity extraction was disabled (Phase 1 mode).")
        print("Run Phase 2 for entity extraction:")
        print("  python /app/scripts/run_etl_phase2_entities.py")

    return _progress


if __name__ == "__main__":
    result = asyncio.run(main())
    print(f"\nProgress saved to: {PROGRESS_FILE}")
    print(f"Completed files saved to: {COMPLETED_FILE}")
