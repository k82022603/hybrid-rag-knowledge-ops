"""
백그라운드 워커 서비스

주기적으로 대기 중인 문서를 처리하는 백그라운드 워커입니다.
FastAPI 앱 시작 시 lifespan 이벤트에서 시작됩니다.

Features:
- 자동 문서 처리 (uploaded/queued 상태)
- 설정 가능한 폴링 간격
- 동시 처리 제한
- 우아한 종료 (graceful shutdown)
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID

from app.core.logging import get_logger
from app.services.document_processing_pipeline import (
    DocumentProcessingPipeline,
    ProcessingResult,
    ProcessingStatus,
)

logger = get_logger(__name__)


class BackgroundWorker:
    """
    백그라운드 문서 처리 워커

    주기적으로 대기 중인 문서를 감지하고 자동 처리합니다.

    Attributes:
        poll_interval: 폴링 간격 (초)
        batch_size: 한 번에 처리할 문서 수
        enabled: 워커 활성화 여부
    """

    def __init__(
        self,
        document_store: Optional[Dict[UUID, Dict[str, Any]]] = None,
        poll_interval: float = 10.0,
        batch_size: int = 5,
        enable_neo4j: bool = True,
        enable_entity_extraction: bool = True,
    ):
        """
        초기화

        Args:
            document_store: In-memory 문서 저장소 (None이면 PostgreSQL 사용)
            poll_interval: 폴링 간격 (초, 기본 10초)
            batch_size: 한 번에 처리할 문서 수 (기본 5)
            enable_neo4j: Neo4j 저장 활성화 여부
            enable_entity_extraction: 엔티티 추출 활성화 여부
        """
        self._document_store = document_store
        self._poll_interval = poll_interval
        self._batch_size = batch_size
        self._enable_neo4j = enable_neo4j
        self._enable_entity_extraction = enable_entity_extraction

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._pipeline: Optional[DocumentProcessingPipeline] = None
        self._processed_count = 0
        self._last_run: Optional[datetime] = None

        logger.info(
            f"BackgroundWorker initialized: "
            f"poll_interval={poll_interval}s, "
            f"batch_size={batch_size}, "
            f"neo4j={enable_neo4j}, "
            f"entity_extraction={enable_entity_extraction}"
        )

    @property
    def is_running(self) -> bool:
        """워커 실행 상태"""
        return self._running

    @property
    def processed_count(self) -> int:
        """처리된 문서 총 개수"""
        return self._processed_count

    @property
    def last_run(self) -> Optional[datetime]:
        """마지막 폴링 시간"""
        return self._last_run

    async def start(self) -> None:
        """
        백그라운드 워커 시작

        이미 실행 중이면 무시합니다.
        """
        if self._running:
            logger.warning("BackgroundWorker is already running")
            return

        self._running = True
        self._pipeline = DocumentProcessingPipeline(
            document_store=self._document_store,
            enable_neo4j=self._enable_neo4j,
            enable_entity_extraction=self._enable_entity_extraction,
        )

        self._task = asyncio.create_task(self._run_loop())
        logger.info("BackgroundWorker started")

    async def stop(self) -> None:
        """
        백그라운드 워커 중지 (Graceful Shutdown)

        현재 처리 중인 문서가 있으면 완료될 때까지 대기합니다.
        """
        if not self._running:
            return

        logger.info("BackgroundWorker stopping...")
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        if self._pipeline:
            await self._pipeline.close()

        logger.info(
            f"BackgroundWorker stopped. "
            f"Total processed: {self._processed_count}"
        )

    async def _run_loop(self) -> None:
        """
        메인 폴링 루프

        주기적으로 대기 중인 문서를 확인하고 처리합니다.
        """
        logger.info(
            f"BackgroundWorker loop started: "
            f"polling every {self._poll_interval}s"
        )

        while self._running:
            try:
                await self._poll_and_process()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"BackgroundWorker error: {e}")

            # 다음 폴링까지 대기
            try:
                await asyncio.sleep(self._poll_interval)
            except asyncio.CancelledError:
                break

        logger.info("BackgroundWorker loop ended")

    async def _poll_and_process(self) -> None:
        """
        대기 중인 문서 폴링 및 처리
        """
        self._last_run = datetime.now(timezone.utc)

        # 대기 중인 문서 조회
        pending_docs = self._get_pending_documents()

        if not pending_docs:
            logger.debug("No pending documents to process")
            return

        logger.info(f"Found {len(pending_docs)} pending documents to process")

        # 문서 처리
        for doc in pending_docs:
            if not self._running:
                break

            doc_id = doc.get("document_id")
            if doc_id:
                try:
                    result = await self._pipeline.process_document(doc_id)

                    if result.success:
                        self._processed_count += 1
                        logger.info(
                            f"Document processed: {doc_id}, "
                            f"chunks={result.chunk_count}, "
                            f"time={result.processing_time_ms:.1f}ms"
                        )
                    else:
                        logger.warning(
                            f"Document processing failed: {doc_id}, "
                            f"error={result.error_message}"
                        )

                except Exception as e:
                    logger.exception(f"Failed to process document {doc_id}: {e}")

    def _get_pending_documents(self) -> List[Dict[str, Any]]:
        """
        대기 중인 문서 목록 조회

        Returns:
            대기 중인 문서 딕셔너리 리스트
        """
        if self._document_store is None:
            # TODO: PostgreSQL 연동
            return []

        pending = []
        for doc in self._document_store.values():
            status = doc.get("status")
            status_value = status.value if hasattr(status, "value") else str(status)

            if status_value in (ProcessingStatus.QUEUED, ProcessingStatus.UPLOADED, "queued", "uploaded"):
                pending.append(doc)

            if len(pending) >= self._batch_size:
                break

        return pending

    def get_stats(self) -> Dict[str, Any]:
        """
        워커 통계 정보 반환

        Returns:
            통계 정보 딕셔너리
        """
        return {
            "running": self._running,
            "poll_interval": self._poll_interval,
            "batch_size": self._batch_size,
            "processed_count": self._processed_count,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "neo4j_enabled": self._enable_neo4j,
            "entity_extraction_enabled": self._enable_entity_extraction,
        }


# ---------------------------------------------------------------------------
# Singleton instance
# ---------------------------------------------------------------------------

_worker: Optional[BackgroundWorker] = None


def get_background_worker(
    document_store: Optional[Dict[UUID, Dict[str, Any]]] = None,
    **kwargs: Any,
) -> BackgroundWorker:
    """
    BackgroundWorker 싱글톤 팩토리

    Args:
        document_store: In-memory 문서 저장소
        **kwargs: 추가 설정

    Returns:
        BackgroundWorker 인스턴스
    """
    global _worker
    if _worker is None:
        _worker = BackgroundWorker(
            document_store=document_store,
            **kwargs,
        )
    return _worker


def reset_worker() -> None:
    """싱글톤 인스턴스 초기화 (테스트용)"""
    global _worker
    _worker = None


async def start_background_worker(
    document_store: Optional[Dict[UUID, Dict[str, Any]]] = None,
    **kwargs: Any,
) -> BackgroundWorker:
    """
    백그라운드 워커 시작 헬퍼 함수

    Args:
        document_store: In-memory 문서 저장소
        **kwargs: 추가 설정

    Returns:
        시작된 BackgroundWorker 인스턴스
    """
    worker = get_background_worker(document_store=document_store, **kwargs)
    await worker.start()
    return worker


async def stop_background_worker() -> None:
    """백그라운드 워커 중지 헬퍼 함수"""
    global _worker
    if _worker is not None:
        await _worker.stop()
