#!/usr/bin/env python3
"""
Embedding Full Cycle Batch Program

ES 청크에 대한 임베딩 생성 + ES 업데이트 + PG 동기화를 수행하는
Full Cycle 배치 프로그램입니다.

기능:
    - 5가지 실행 모드: all, document, file, reprocess + --force
    - 체크포인트/재개 (--resume)
    - OOM 방지 (--stop-service, 메모리 모니터링)
    - PG documents 테이블 동기화 (processing_status, es_synced)
    - 작업 이력 JSON 저장

사용법:
    # 컨테이너 내에서 실행
    python3 /app/scripts/embedding_full_cycle.py --mode all --stop-service
    python3 /app/scripts/embedding_full_cycle.py --mode document --doc-id <UUID>
    python3 /app/scripts/embedding_full_cycle.py --mode file --file-name "파일명.pdf"
    python3 /app/scripts/embedding_full_cycle.py --mode reprocess --since 2026-02-01
    python3 /app/scripts/embedding_full_cycle.py --mode all --force --batch-size 8
    python3 /app/scripts/embedding_full_cycle.py --resume /tmp/embedding_checkpoint.json
"""

import argparse
import asyncio
import functools
import gc
import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

# docker exec에서 stdout이 fully-buffered 되는 문제 방지
print = functools.partial(print, flush=True)

sys.path.insert(0, "/app")
os.chdir("/app")

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class DocumentResult:
    """문서별 임베딩 결과"""
    document_id: str
    file_name: str
    total_chunks: int = 0
    processed: int = 0
    skipped: int = 0
    failed: int = 0


@dataclass
class EmbeddingBatchSummary:
    """배치 실행 결과 요약"""
    started_at: str = ""
    completed_at: str = ""
    mode: str = "all"
    force: bool = False
    total_chunks: int = 0
    processed: int = 0
    skipped: int = 0
    failed: int = 0
    per_document: Dict[str, Any] = field(default_factory=dict)
    elapsed_seconds: float = 0.0
    batch_size: int = 16
    dry_run: bool = False
    error_message: Optional[str] = None


@dataclass
class Checkpoint:
    """체크포인트 (중단 후 재개용)"""
    processed_ids: List[str] = field(default_factory=list)
    total_processed: int = 0
    total_skipped: int = 0
    total_failed: int = 0
    per_document: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    mode: str = "all"
    force: bool = False


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def get_memory_gb() -> float:
    """cgroup 또는 /proc/meminfo에서 메모리 사용량(GB) 반환"""
    # cgroup v2
    try:
        with open("/sys/fs/cgroup/memory.current") as f:
            return int(f.read().strip()) / 1024**3
    except Exception:
        pass
    # cgroup v1
    try:
        with open("/sys/fs/cgroup/memory/memory.usage_in_bytes") as f:
            return int(f.read().strip()) / 1024**3
    except Exception:
        pass
    # fallback: psutil
    try:
        import psutil
        return psutil.virtual_memory().used / 1024**3
    except Exception:
        return 0.0


def get_memory_percent() -> float:
    """시스템 메모리 사용률(%) 반환"""
    try:
        import psutil
        return psutil.virtual_memory().percent
    except Exception:
        pass
    try:
        with open("/proc/meminfo") as f:
            lines = f.readlines()
        info = {}
        for line in lines:
            parts = line.split()
            if len(parts) >= 2:
                info[parts[0].rstrip(":")] = int(parts[1])
        total = info.get("MemTotal", 1)
        available = info.get("MemAvailable", total)
        return (1 - available / total) * 100
    except Exception:
        return 0.0


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class EmbeddingFullCycle:
    """Full Cycle 임베딩 배치 프로세서"""

    CHECKPOINT_INTERVAL = 50  # 배치 수 기준

    def __init__(
        self,
        es_url: str = "http://elasticsearch:9200",
        pg_dsn: str = "",
        batch_size: int = 16,
        scroll_size: int = 20,
        scroll_timeout: str = "60m",
        dry_run: bool = False,
        force: bool = False,
        stop_service: bool = False,
    ):
        self.es_url = es_url
        self.pg_dsn = pg_dsn
        self.batch_size = batch_size
        self.scroll_size = scroll_size
        self.scroll_timeout = scroll_timeout
        self.dry_run = dry_run
        self.force = force
        self.stop_service = stop_service
        self.index_name = os.getenv("ELASTICSEARCH_INDEX", "knowledge_chunks")

        self._es = None
        self._pg_pool = None
        self._embedding_svc = None
        self._stopped_pids: List[int] = []

    # ------------------------------------------------------------------
    # Service management
    # ------------------------------------------------------------------

    def _stop_web_service(self) -> None:
        """uvicorn 웹 프로세스 중지 (메모리 확보)"""
        print("[SERVICE] Stopping uvicorn web process for memory...")
        try:
            result = subprocess.run(
                ["pgrep", "-f", "uvicorn"],
                capture_output=True, text=True
            )
            pids = [int(p) for p in result.stdout.strip().split("\n") if p.strip()]
            # 현재 프로세스는 제외
            my_pid = os.getpid()
            pids = [p for p in pids if p != my_pid]

            for pid in pids:
                try:
                    os.kill(pid, signal.SIGTERM)
                    self._stopped_pids.append(pid)
                    print(f"  [SERVICE] Stopped uvicorn pid={pid}")
                except ProcessLookupError:
                    pass

            if pids:
                time.sleep(2)  # graceful shutdown 대기
                print(f"[SERVICE] {len(pids)} uvicorn process(es) stopped")
            else:
                print("[SERVICE] No uvicorn process found")

        except Exception as e:
            print(f"[SERVICE] Warning: could not stop uvicorn: {e}")

    def _start_web_service(self) -> None:
        """uvicorn 웹 프로세스 재시작"""
        print("[SERVICE] Restarting uvicorn web process...")
        try:
            subprocess.Popen(
                ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            print("[SERVICE] uvicorn restart initiated")
        except Exception as e:
            print(f"[SERVICE] Warning: could not restart uvicorn: {e}")
            print("[SERVICE] You may need to restart the container manually")

    # ------------------------------------------------------------------
    # Init services
    # ------------------------------------------------------------------

    async def _init_services(self) -> None:
        """ES 클라이언트, 임베딩 모델, PG 풀 초기화"""
        from elasticsearch import AsyncElasticsearch
        self._es = AsyncElasticsearch(self.es_url, request_timeout=120)

        # PG 연결
        if self.pg_dsn:
            try:
                import asyncpg
                self._pg_pool = await asyncpg.create_pool(
                    self.pg_dsn, min_size=1, max_size=3
                )
                print(f"[PG] Connected to PostgreSQL")
            except Exception as e:
                print(f"[PG] Warning: could not connect: {e}")
                self._pg_pool = None
        else:
            # 환경변수에서 DSN 구성
            pg_host = os.getenv("POSTGRES_HOST", "postgresql")
            pg_port = os.getenv("POSTGRES_PORT", "5432")
            pg_user = os.getenv("POSTGRES_USER", "postgres")
            pg_pass = os.getenv("POSTGRES_PASSWORD", "")
            pg_db = os.getenv("POSTGRES_DB", "knowledge_db")
            dsn = f"postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}"
            try:
                import asyncpg
                self._pg_pool = await asyncpg.create_pool(
                    dsn, min_size=1, max_size=3
                )
                print(f"[PG] Connected to PostgreSQL ({pg_host}:{pg_port}/{pg_db})")
            except Exception as e:
                print(f"[PG] Warning: could not connect: {e}")
                self._pg_pool = None

        # 임베딩 모델 로딩
        if not self.dry_run:
            print("[MODEL] Loading BGE-M3 embedding model...")
            model_start = time.monotonic()
            from app.services.embedding import EmbeddingService
            self._embedding_svc = EmbeddingService(cache_enabled=False)
            _ = self._embedding_svc.model  # 지연 로딩 트리거
            elapsed = time.monotonic() - model_start
            print(f"[MODEL] Loaded in {elapsed:.1f}s, device={self._embedding_svc.device}")
            print(f"[MEMORY] {get_memory_gb():.1f}GB after model load")

    async def _cleanup(self) -> None:
        """리소스 정리"""
        if self._es:
            await self._es.close()
        if self._pg_pool:
            await self._pg_pool.close()

    # ------------------------------------------------------------------
    # ES Query Builder
    # ------------------------------------------------------------------

    def _build_es_query(
        self,
        mode: str,
        doc_id: Optional[str] = None,
        file_name: Optional[str] = None,
        since: Optional[str] = None,
    ) -> dict:
        """실행 모드에 따른 ES 쿼리 생성"""
        must_clauses = []
        must_not_clauses = []

        # force가 아니면 임베딩 없는 것만
        if not self.force:
            must_not_clauses.append({"exists": {"field": "dense_vector"}})

        if mode == "all":
            pass  # 추가 필터 없음

        elif mode == "document":
            if not doc_id:
                raise ValueError("--doc-id required for document mode")
            # document_id는 text+keyword 매핑 → .keyword 서브필드 사용
            must_clauses.append({"term": {"document_id.keyword": doc_id}})

        elif mode == "file":
            if not file_name:
                raise ValueError("--file-name required for file mode")
            # metadata.file_name은 keyword 타입
            must_clauses.append({"match": {"metadata.file_name": file_name}})

        elif mode == "reprocess":
            if not since:
                raise ValueError("--since required for reprocess mode")
            must_clauses.append({"range": {"created_at": {"gte": since}}})

        query = {"bool": {}}
        if must_clauses:
            query["bool"]["must"] = must_clauses
        if must_not_clauses:
            query["bool"]["must_not"] = must_not_clauses

        # bool이 비어있으면 match_all
        if not query["bool"]:
            query = {"match_all": {}}

        return query

    # ------------------------------------------------------------------
    # Checkpoint management
    # ------------------------------------------------------------------

    def _save_checkpoint(self, checkpoint: Checkpoint) -> str:
        """체크포인트 저장"""
        checkpoint.created_at = utcnow_iso()
        path = "/tmp/embedding_checkpoint.json"
        data = asdict(checkpoint)
        # Set을 List로 변환 (JSON 호환)
        with open(path, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return path

    @staticmethod
    def _load_checkpoint(path: str) -> Checkpoint:
        """체크포인트 로드"""
        with open(path) as f:
            data = json.load(f)
        return Checkpoint(
            processed_ids=data.get("processed_ids", []),
            total_processed=data.get("total_processed", 0),
            total_skipped=data.get("total_skipped", 0),
            total_failed=data.get("total_failed", 0),
            per_document=data.get("per_document", {}),
            created_at=data.get("created_at", ""),
            mode=data.get("mode", "all"),
            force=data.get("force", False),
        )

    # ------------------------------------------------------------------
    # Embedding + ES update
    # ------------------------------------------------------------------

    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        """텍스트 배치 임베딩 생성"""
        return self._embedding_svc.embed_batch(texts, return_sparse=False)

    async def _bulk_update_es(
        self, doc_updates: List[Tuple[str, List[float]]]
    ) -> Tuple[int, int]:
        """ES bulk update로 dense_vector 추가. (success, failed) 반환"""
        bulk_body = []
        for es_doc_id, vector in doc_updates:
            bulk_body.append({"update": {"_index": self.index_name, "_id": es_doc_id}})
            bulk_body.append({"doc": {"dense_vector": vector}})

        try:
            resp = await self._es.bulk(operations=bulk_body, refresh=False)
            if resp.get("errors"):
                success = 0
                failed = 0
                for item in resp["items"]:
                    if "error" in item.get("update", {}):
                        err = item["update"]["error"]
                        print(f"  [ES_ERR] {err.get('reason', str(err)[:100])}")
                        failed += 1
                    else:
                        success += 1
                return success, failed
            return len(doc_updates), 0
        except Exception as e:
            print(f"  [ES_ERR] Bulk update failed: {e}")
            return 0, len(doc_updates)

    # ------------------------------------------------------------------
    # PG sync
    # ------------------------------------------------------------------

    async def _update_pg_documents(
        self, per_document: Dict[str, DocumentResult]
    ) -> None:
        """PG documents 테이블의 processing_status, es_synced 업데이트"""
        if not self._pg_pool:
            print("[PG] Skipping PG sync (no connection)")
            return

        print(f"[PG] Syncing {len(per_document)} document(s) to PostgreSQL...")
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        updated = 0
        errors = 0

        async with self._pg_pool.acquire() as conn:
            for doc_id, result in per_document.items():
                try:
                    if isinstance(result, dict):
                        processed = result.get("processed", 0)
                        failed = result.get("failed", 0)
                    else:
                        processed = result.processed
                        failed = result.failed

                    status = "completed" if failed == 0 and processed > 0 else (
                        "failed" if processed == 0 and failed > 0 else "completed"
                    )
                    es_synced = processed > 0

                    await conn.execute(
                        """
                        UPDATE documents
                        SET processing_status = $2,
                            es_synced = $3,
                            es_synced_at = $4,
                            updated_at = $4
                        WHERE id = $1::uuid
                        """,
                        doc_id,
                        status,
                        es_synced,
                        now,
                    )
                    updated += 1
                except Exception as e:
                    print(f"  [PG_ERR] doc={doc_id}: {e}")
                    errors += 1

        print(f"[PG] Sync complete: updated={updated}, errors={errors}")

    # ------------------------------------------------------------------
    # Memory management
    # ------------------------------------------------------------------

    def _check_memory(self) -> bool:
        """메모리 확인. 안전하면 True, 위험하면 False"""
        mem_pct = get_memory_percent()
        if mem_pct > 85:
            print(f"  [MEMORY] WARNING: {mem_pct:.1f}% used, running GC...")
            gc.collect()
            time.sleep(10)
            mem_pct = get_memory_percent()
            if mem_pct > 90:
                print(f"  [MEMORY] CRITICAL: {mem_pct:.1f}% - pausing 30s...")
                time.sleep(30)
                gc.collect()
                return get_memory_percent() < 90
        return True

    # ------------------------------------------------------------------
    # Main run
    # ------------------------------------------------------------------

    async def run(
        self,
        mode: str = "all",
        doc_id: Optional[str] = None,
        file_name: Optional[str] = None,
        since: Optional[str] = None,
        resume_path: Optional[str] = None,
    ) -> EmbeddingBatchSummary:
        """Full Cycle 임베딩 배치 실행"""

        summary = EmbeddingBatchSummary(
            started_at=utcnow_iso(),
            mode=mode,
            force=self.force,
            batch_size=self.batch_size,
            dry_run=self.dry_run,
        )

        # 체크포인트 로드
        checkpoint = None
        processed_ids: Set[str] = set()
        per_document: Dict[str, DocumentResult] = {}

        if resume_path:
            checkpoint = self._load_checkpoint(resume_path)
            processed_ids = set(checkpoint.processed_ids)
            # per_document 복원
            for d_id, d_data in checkpoint.per_document.items():
                if isinstance(d_data, dict):
                    per_document[d_id] = DocumentResult(**d_data)
                else:
                    per_document[d_id] = d_data
            summary.processed = checkpoint.total_processed
            summary.skipped = checkpoint.total_skipped
            summary.failed = checkpoint.total_failed
            mode = checkpoint.mode
            self.force = checkpoint.force
            print(f"[RESUME] Loaded checkpoint: {len(processed_ids)} already processed")

        print(f"[CONFIG] ES={self.es_url}, index={self.index_name}")
        print(f"[CONFIG] mode={mode}, force={self.force}, batch_size={self.batch_size}, scroll_size={self.scroll_size}, scroll_timeout={self.scroll_timeout}")
        print(f"[CONFIG] dry_run={self.dry_run}, stop_service={self.stop_service}")
        print(f"[MEMORY] {get_memory_gb():.1f}GB at start")

        # 서비스 중지 (옵션)
        if self.stop_service:
            self._stop_web_service()

        try:
            # 서비스 초기화
            await self._init_services()

            # ES 쿼리 빌드
            query = self._build_es_query(mode, doc_id, file_name, since)
            print(f"[QUERY] {json.dumps(query, ensure_ascii=False)[:200]}")

            # 총 대상 수 확인
            count_resp = await self._es.count(
                index=self.index_name, body={"query": query}
            )
            total = count_resp["count"]
            summary.total_chunks = total
            print(f"[SCAN] {total} target chunks found")

            if total == 0:
                print("[DONE] No chunks to process.")
                summary.completed_at = utcnow_iso()
                return summary

            if self.dry_run:
                print(f"[DRY_RUN] Would process {total} chunks. Exiting.")
                summary.completed_at = utcnow_iso()
                return summary

            # Scroll API로 분할 처리
            search_body = {
                "query": query,
                "_source": ["text", "content", "chunk_id", "document_id",
                            "metadata.file_name"],
                "sort": ["_doc"],
            }

            scroll_resp = await self._es.search(
                index=self.index_name,
                body=search_body,
                scroll=self.scroll_timeout,
                size=self.scroll_size,
            )
            scroll_id = scroll_resp["_scroll_id"]
            hits = scroll_resp["hits"]["hits"]

            total_start = time.monotonic()
            batch_count = 0

            while hits:
                # 배치 단위로 처리
                for batch_start in range(0, len(hits), self.batch_size):
                    batch_hits = hits[batch_start:batch_start + self.batch_size]

                    # 메모리 체크
                    if not self._check_memory():
                        print("[MEMORY] Cannot continue due to memory pressure")
                        # 체크포인트 저장 후 종료
                        ckpt = Checkpoint(
                            processed_ids=list(processed_ids),
                            total_processed=summary.processed,
                            total_skipped=summary.skipped,
                            total_failed=summary.failed,
                            per_document={
                                k: asdict(v) for k, v in per_document.items()
                            },
                            mode=mode,
                            force=self.force,
                        )
                        ckpt_path = self._save_checkpoint(ckpt)
                        print(f"[CHECKPOINT] Saved to {ckpt_path}")
                        summary.error_message = "Stopped due to memory pressure"
                        break

                    # 텍스트 및 메타데이터 추출
                    chunk_texts = []
                    chunk_es_ids = []
                    chunk_doc_ids = []

                    for hit in batch_hits:
                        es_id = hit["_id"]

                        # 이미 처리된 건 스킵
                        if es_id in processed_ids:
                            summary.skipped += 1
                            continue

                        source = hit["_source"]
                        text = source.get("text") or source.get("content") or ""

                        if not text.strip():
                            summary.failed += 1
                            processed_ids.add(es_id)
                            continue

                        doc_id_val = source.get("document_id", "unknown")
                        file_name_val = ""
                        meta = source.get("metadata", {})
                        if isinstance(meta, dict):
                            file_name_val = meta.get("file_name", "")

                        # per_document 트래킹
                        if doc_id_val not in per_document:
                            per_document[doc_id_val] = DocumentResult(
                                document_id=doc_id_val,
                                file_name=file_name_val,
                            )
                        per_document[doc_id_val].total_chunks += 1

                        chunk_texts.append(text)
                        chunk_es_ids.append(es_id)
                        chunk_doc_ids.append(doc_id_val)

                    if not chunk_texts:
                        continue

                    # 임베딩 생성
                    try:
                        vectors = self._embed_batch(chunk_texts)
                    except Exception as e:
                        print(f"  [EMB_ERR] Batch embedding failed: {e}")
                        for cid, did in zip(chunk_es_ids, chunk_doc_ids):
                            summary.failed += 1
                            processed_ids.add(cid)
                            if did in per_document:
                                per_document[did].failed += 1
                        continue

                    # ES bulk update
                    updates = list(zip(chunk_es_ids, vectors))
                    success, failed = await self._bulk_update_es(updates)

                    # 결과 반영
                    for i, (cid, did) in enumerate(zip(chunk_es_ids, chunk_doc_ids)):
                        processed_ids.add(cid)
                        if i < success:
                            summary.processed += 1
                            if did in per_document:
                                per_document[did].processed += 1
                        else:
                            summary.failed += 1
                            if did in per_document:
                                per_document[did].failed += 1

                    batch_count += 1

                    # 진행률 로깅
                    total_done = summary.processed + summary.skipped + summary.failed
                    pct = (total_done / total * 100) if total > 0 else 100
                    elapsed = time.monotonic() - total_start
                    rate = summary.processed / elapsed if elapsed > 0 else 0
                    mem_gb = get_memory_gb()
                    print(
                        f"  [PROGRESS] {total_done}/{total} ({pct:.1f}%) | "
                        f"ok={summary.processed} skip={summary.skipped} "
                        f"fail={summary.failed} | "
                        f"{rate:.1f} chunks/s | mem={mem_gb:.1f}GB"
                    )

                    # GC
                    gc.collect()

                    # 체크포인트 저장
                    if batch_count % self.CHECKPOINT_INTERVAL == 0:
                        ckpt = Checkpoint(
                            processed_ids=list(processed_ids),
                            total_processed=summary.processed,
                            total_skipped=summary.skipped,
                            total_failed=summary.failed,
                            per_document={
                                k: asdict(v) for k, v in per_document.items()
                            },
                            mode=mode,
                            force=self.force,
                        )
                        ckpt_path = self._save_checkpoint(ckpt)
                        print(f"  [CHECKPOINT] Auto-saved ({batch_count} batches)")

                else:
                    # inner for loop 정상 완료 → 다음 scroll
                    try:
                        scroll_resp = await self._es.scroll(
                            scroll_id=scroll_id, scroll=self.scroll_timeout
                        )
                        scroll_id = scroll_resp["_scroll_id"]
                        hits = scroll_resp["hits"]["hits"]
                    except Exception as e:
                        print(f"[SCROLL_ERR] {e}")
                        # scroll 만료 시 체크포인트 저장 후 종료
                        ckpt = Checkpoint(
                            processed_ids=list(processed_ids),
                            total_processed=summary.processed,
                            total_skipped=summary.skipped,
                            total_failed=summary.failed,
                            per_document={
                                k: asdict(v) for k, v in per_document.items()
                            },
                            mode=mode,
                            force=self.force,
                        )
                        ckpt_path = self._save_checkpoint(ckpt)
                        print(f"[CHECKPOINT] Saved on scroll error: {ckpt_path}")
                        summary.error_message = f"Scroll error: {e}"
                        break
                    continue

                # inner for loop이 break로 종료됨 (메모리 문제)
                break

            # Scroll 정리
            try:
                await self._es.clear_scroll(scroll_id=scroll_id)
            except Exception:
                pass

            # PG 동기화
            await self._update_pg_documents(per_document)

        except Exception as e:
            summary.error_message = str(e)
            print(f"[FATAL] {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self._cleanup()

        # 서비스 재시작 (옵션)
        if self.stop_service and self._stopped_pids:
            self._start_web_service()

        # 결과 요약
        summary.completed_at = utcnow_iso()
        summary.elapsed_seconds = round(
            time.monotonic() - (total_start if 'total_start' in dir() else time.monotonic()),
            1
        )
        summary.per_document = {
            k: asdict(v) if not isinstance(v, dict) else v
            for k, v in per_document.items()
        }

        self._print_summary(summary)
        self._save_result_json(summary)

        # 최종 체크포인트 정리 (성공 시)
        if not summary.error_message:
            try:
                os.remove("/tmp/embedding_checkpoint.json")
            except FileNotFoundError:
                pass

        return summary

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    @staticmethod
    def _print_summary(summary: EmbeddingBatchSummary) -> None:
        """결과 요약 출력"""
        print()
        print("=" * 70)
        print("[RESULT] Embedding Full Cycle Batch Completed")
        print(f"  Mode:           {summary.mode} (force={summary.force})")
        print(f"  Total targets:  {summary.total_chunks}")
        print(f"  Processed:      {summary.processed}")
        print(f"  Skipped:        {summary.skipped}")
        print(f"  Failed:         {summary.failed}")
        print(f"  Elapsed:        {summary.elapsed_seconds:.1f}s")
        if summary.elapsed_seconds > 0 and summary.processed > 0:
            rate = summary.processed / summary.elapsed_seconds
            print(f"  Rate:           {rate:.2f} chunks/s")
        print(f"  Documents:      {len(summary.per_document)}")
        if summary.error_message:
            print(f"  Error:          {summary.error_message}")
        print(f"  Memory:         {get_memory_gb():.1f}GB")
        print("=" * 70)

    @staticmethod
    def _save_result_json(summary: EmbeddingBatchSummary) -> None:
        """결과 JSON 파일 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_dir = "/app/docs/results"
        os.makedirs(results_dir, exist_ok=True)
        path = f"{results_dir}/embedding_batch_{timestamp}.json"

        data = asdict(summary)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"[RESULT] Saved to {path}")

        # 호스트 측에도 저장 시도
        host_dir = "/app/knowledge_service/docs/results"
        if os.path.isdir(os.path.dirname(host_dir)):
            os.makedirs(host_dir, exist_ok=True)
            host_path = f"{host_dir}/embedding_batch_{timestamp}.json"
            try:
                with open(host_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Embedding Full Cycle Batch - ES 임베딩 + PG 동기화",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 미처리 전체 청크 임베딩
  python3 embedding_full_cycle.py --mode all --stop-service

  # 특정 문서만 재처리
  python3 embedding_full_cycle.py --mode document --doc-id <UUID> --force

  # 특정 파일 재처리
  python3 embedding_full_cycle.py --mode file --file-name "계약서.pdf" --force

  # 2026-02-01 이후 데이터 재처리
  python3 embedding_full_cycle.py --mode reprocess --since 2026-02-01

  # 중단 후 재개
  python3 embedding_full_cycle.py --resume /tmp/embedding_checkpoint.json

  # Dry run (처리 대상만 확인)
  python3 embedding_full_cycle.py --mode all --dry-run
        """,
    )
    parser.add_argument(
        "--mode",
        choices=["all", "document", "file", "reprocess"],
        default="all",
        help="실행 모드 (default: all)",
    )
    parser.add_argument(
        "--doc-id",
        type=str,
        help="문서 UUID (document 모드 필수)",
    )
    parser.add_argument(
        "--file-name",
        type=str,
        help="파일명 (file 모드 필수)",
    )
    parser.add_argument(
        "--since",
        type=str,
        help="시작일 YYYY-MM-DD (reprocess 모드 필수)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=16,
        help="임베딩 배치 크기 (default: 16)",
    )
    parser.add_argument(
        "--scroll-size",
        type=int,
        default=20,
        help="ES scroll 페이지 크기 (default: 20, 긴 텍스트 시 줄임)",
    )
    parser.add_argument(
        "--scroll-timeout",
        type=str,
        default="60m",
        help="ES scroll 유지시간 (default: 60m)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="처리 대상 수만 확인 (실제 처리 없음)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="기존 임베딩 있어도 강제 재처리",
    )
    parser.add_argument(
        "--resume",
        type=str,
        metavar="CHECKPOINT_PATH",
        help="체크포인트 파일에서 재개",
    )
    parser.add_argument(
        "--stop-service",
        action="store_true",
        help="배치 전 uvicorn 웹 프로세스 중지 (메모리 확보)",
    )
    parser.add_argument(
        "--pg-dsn",
        type=str,
        default="",
        help="PostgreSQL DSN (미지정 시 환경변수 사용)",
    )

    args = parser.parse_args()

    processor = EmbeddingFullCycle(
        es_url=os.getenv("ELASTICSEARCH_URL", "http://elasticsearch:9200"),
        pg_dsn=args.pg_dsn,
        batch_size=args.batch_size,
        scroll_size=args.scroll_size,
        scroll_timeout=args.scroll_timeout,
        dry_run=args.dry_run,
        force=args.force,
        stop_service=args.stop_service,
    )

    summary = asyncio.run(processor.run(
        mode=args.mode,
        doc_id=args.doc_id,
        file_name=args.file_name,
        since=args.since,
        resume_path=args.resume,
    ))

    # 종료 코드: 에러 있으면 1
    sys.exit(1 if summary.error_message else 0)


if __name__ == "__main__":
    main()
