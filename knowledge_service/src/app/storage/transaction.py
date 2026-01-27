"""
트랜잭션 관리 모듈

STORY-006: Neo4j/Elasticsearch 저장 서비스 구현

Neo4j + Elasticsearch + PostgreSQL 에 걸친 원자적 저장을 관리합니다.
- 2PC (Two-Phase Commit) 패턴의 보상 트랜잭션 구현
- 저장 실패 시 롤백 (compensating transaction)
- 문서 전체 파이프라인: Graph + Vector + Metadata
- 저장 상태 추적 및 로깅

Note:
    분산 트랜잭션의 진정한 원자성은 보장하기 어렵습니다.
    여기서는 "보상 트랜잭션" 패턴으로 실패 시 이미 저장된 데이터를
    삭제하여 일관성을 유지합니다.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from app.agents.state import Entity, Relationship
from app.core.exceptions import (
    ElasticsearchError,
    KnowledgeServiceError,
    Neo4jError,
)
from app.core.logging import get_logger
from app.storage.es_storage import ElasticsearchStorageService, get_es_storage_service
from app.storage.neo4j_storage import Neo4jStorageService, get_neo4j_storage_service

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Transaction state tracking
# ---------------------------------------------------------------------------


class TransactionPhase(str, Enum):
    """트랜잭션 실행 단계"""

    PENDING = "pending"
    NEO4J_SAVING = "neo4j_saving"
    NEO4J_SAVED = "neo4j_saved"
    ES_SAVING = "es_saving"
    ES_SAVED = "es_saved"
    COMPLETED = "completed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


@dataclass
class TransactionState:
    """트랜잭션 상태 추적

    Attributes:
        document_id: 처리 중인 문서 ID
        phase: 현재 트랜잭션 단계
        neo4j_saved: Neo4j 저장 성공 여부
        es_saved: Elasticsearch 저장 성공 여부
        neo4j_stats: Neo4j 저장 통계
        es_stats: Elasticsearch 저장 통계
        error: 에러 메시지 (실패 시)
        started_at: 트랜잭션 시작 시간
        completed_at: 트랜잭션 완료 시간
    """

    document_id: str
    phase: TransactionPhase = TransactionPhase.PENDING
    neo4j_saved: bool = False
    es_saved: bool = False
    neo4j_stats: Dict[str, int] = field(default_factory=dict)
    es_stats: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# StorageTransaction
# ---------------------------------------------------------------------------


class StorageTransaction:
    """
    다중 저장소 트랜잭션 관리자

    Neo4j와 Elasticsearch에 걸친 문서 저장을 원자적으로 관리합니다.
    보상 트랜잭션 패턴으로 실패 시 이미 저장된 데이터를 롤백합니다.

    Pipeline:
        1. Neo4j: Knowledge 노드 + 엔티티 + 관계 + 청크 저장
        2. Elasticsearch: 청크 + 벡터 인덱싱
        3. 실패 시: 역순으로 롤백 (ES 삭제 -> Neo4j 삭제)

    Usage:
        ```python
        tx = StorageTransaction()
        result = await tx.save_document(
            document_id="doc-001",
            title="기술 문서",
            entities=entities,
            relationships=relationships,
            chunks=chunks_with_vectors,
        )
        ```

    Attributes:
        _neo4j: Neo4jStorageService 인스턴스
        _es: ElasticsearchStorageService 인스턴스
    """

    def __init__(
        self,
        neo4j_service: Optional[Neo4jStorageService] = None,
        es_service: Optional[ElasticsearchStorageService] = None,
    ):
        """StorageTransaction 초기화

        Args:
            neo4j_service: Neo4j 저장 서비스 (None이면 싱글톤 사용)
            es_service: Elasticsearch 저장 서비스 (None이면 싱글톤 사용)
        """
        self._neo4j = neo4j_service or get_neo4j_storage_service()
        self._es = es_service or get_es_storage_service()
        self._state: Optional[TransactionState] = None

    @property
    def state(self) -> Optional[TransactionState]:
        """현재 트랜잭션 상태"""
        return self._state

    # ------------------------------------------------------------------
    # Main transaction method
    # ------------------------------------------------------------------

    async def save_document(
        self,
        document_id: str,
        title: str,
        entities: List[Entity],
        relationships: List[Relationship],
        chunks: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """문서 전체 파이프라인 저장 (Graph + Vector + Metadata)

        Neo4j에 Knowledge Graph를, Elasticsearch에 벡터 인덱스를 저장합니다.
        실패 시 보상 트랜잭션으로 롤백합니다.

        Args:
            document_id: 문서 고유 ID
            title: 문서 제목
            entities: 추출된 엔티티 리스트
            relationships: 추출된 관계 리스트
            chunks: 청크 데이터 리스트 (dense_vector 포함)
            metadata: 문서 메타데이터 (document_type, project_name 등)

        Returns:
            저장 결과 딕셔너리
            {
                "document_id": str,
                "status": "completed" | "failed",
                "neo4j": {"knowledge": 1, "entities": n, "relationships": m},
                "elasticsearch": {"indexed": n, "errors": m},
                "latency_ms": float,
            }

        Raises:
            KnowledgeServiceError: 저장 및 롤백 모두 실패 시
        """
        start_time = time.monotonic()
        self._state = TransactionState(document_id=document_id)

        logger.info(
            "Transaction started: doc_id=%s, entities=%d, rels=%d, chunks=%d",
            document_id,
            len(entities),
            len(relationships),
            len(chunks),
        )

        try:
            # Phase 1: Neo4j 저장
            self._state.phase = TransactionPhase.NEO4J_SAVING
            neo4j_stats = await self._save_to_neo4j(
                document_id=document_id,
                title=title,
                entities=entities,
                relationships=relationships,
                chunks=chunks,
                metadata=metadata,
            )
            self._state.neo4j_saved = True
            self._state.neo4j_stats = neo4j_stats
            self._state.phase = TransactionPhase.NEO4J_SAVED

            logger.info(
                "Neo4j phase complete: doc_id=%s, stats=%s",
                document_id,
                neo4j_stats,
            )

            # Phase 2: Elasticsearch 저장
            self._state.phase = TransactionPhase.ES_SAVING
            es_stats = await self._save_to_elasticsearch(
                document_id=document_id,
                chunks=chunks,
            )
            self._state.es_saved = True
            self._state.es_stats = es_stats
            self._state.phase = TransactionPhase.ES_SAVED

            logger.info(
                "ES phase complete: doc_id=%s, stats=%s",
                document_id,
                es_stats,
            )

            # 성공
            self._state.phase = TransactionPhase.COMPLETED
            self._state.completed_at = datetime.now(timezone.utc)
            latency_ms = (time.monotonic() - start_time) * 1000

            result = {
                "document_id": document_id,
                "status": "completed",
                "neo4j": neo4j_stats,
                "elasticsearch": es_stats,
                "latency_ms": round(latency_ms, 2),
            }

            logger.info(
                "Transaction completed: doc_id=%s, latency=%.1fms",
                document_id,
                latency_ms,
            )

            return result

        except Exception as e:
            # 실패 -> 롤백
            self._state.error = str(e)
            logger.error(
                "Transaction failed at phase=%s: doc_id=%s, error=%s",
                self._state.phase.value,
                document_id,
                e,
            )

            await self._rollback(document_id)

            latency_ms = (time.monotonic() - start_time) * 1000
            return {
                "document_id": document_id,
                "status": "failed",
                "error": str(e),
                "failed_phase": self._state.phase.value,
                "neo4j": self._state.neo4j_stats,
                "elasticsearch": self._state.es_stats,
                "latency_ms": round(latency_ms, 2),
            }

    # ------------------------------------------------------------------
    # Phase methods
    # ------------------------------------------------------------------

    async def _save_to_neo4j(
        self,
        document_id: str,
        title: str,
        entities: List[Entity],
        relationships: List[Relationship],
        chunks: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, int]:
        """Neo4j 저장 단계

        Args:
            document_id: 문서 ID
            title: 문서 제목
            entities: 엔티티 리스트
            relationships: 관계 리스트
            chunks: 청크 리스트
            metadata: 메타데이터

        Returns:
            저장 통계

        Raises:
            Neo4jError: 저장 실패
        """
        # Knowledge + 엔티티 + 관계 저장
        graph_stats = await self._neo4j.save_document_graph(
            document_id=document_id,
            title=title,
            entities=entities,
            relationships=relationships,
            metadata=metadata,
        )

        # 청크 노드 저장
        chunk_count = 0
        if chunks:
            chunk_data = [
                {
                    "chunk_id": c.get("chunk_id", c.get("id", "")),
                    "content": c.get("content", c.get("text", "")),
                    "chunk_index": c.get("chunk_index", 0),
                    "token_count": c.get("token_count", 0),
                }
                for c in chunks
            ]
            chunk_count = await self._neo4j.save_chunks(
                knowledge_id=document_id,
                chunks=chunk_data,
            )

        graph_stats["chunks"] = chunk_count
        return graph_stats

    async def _save_to_elasticsearch(
        self,
        document_id: str,
        chunks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Elasticsearch 저장 단계

        Args:
            document_id: 문서 ID
            chunks: 청크 리스트 (dense_vector 포함)

        Returns:
            인덱싱 통계

        Raises:
            ElasticsearchError: 인덱싱 실패
        """
        if not chunks:
            return {"indexed": 0, "errors": 0, "latency_ms": 0.0}

        # document_id 보장
        for chunk in chunks:
            if "document_id" not in chunk:
                chunk["document_id"] = document_id

        return await self._es.index_chunks(chunks=chunks)

    # ------------------------------------------------------------------
    # Rollback
    # ------------------------------------------------------------------

    async def _rollback(self, document_id: str) -> None:
        """보상 트랜잭션으로 롤백

        이미 저장된 데이터를 역순으로 삭제합니다.
        롤백 자체가 실패해도 로깅만 하고 예외를 전파하지 않습니다.

        Args:
            document_id: 롤백할 문서 ID
        """
        self._state.phase = TransactionPhase.ROLLING_BACK
        logger.warning(
            "Rolling back transaction: doc_id=%s, neo4j_saved=%s, es_saved=%s",
            document_id,
            self._state.neo4j_saved,
            self._state.es_saved,
        )

        # ES 롤백 (역순)
        if self._state.es_saved:
            try:
                deleted = await self._es.delete_by_document_id(document_id)
                logger.info(
                    "ES rollback completed: doc_id=%s, deleted=%d",
                    document_id,
                    deleted,
                )
            except Exception as e:
                logger.error(
                    "ES rollback failed: doc_id=%s, error=%s",
                    document_id,
                    e,
                )

        # Neo4j 롤백
        if self._state.neo4j_saved:
            try:
                deleted = await self._neo4j.delete_document_graph(document_id)
                logger.info(
                    "Neo4j rollback completed: doc_id=%s, deleted=%d",
                    document_id,
                    deleted,
                )
            except Exception as e:
                logger.error(
                    "Neo4j rollback failed: doc_id=%s, error=%s",
                    document_id,
                    e,
                )

        self._state.phase = TransactionPhase.ROLLED_BACK
        self._state.completed_at = datetime.now(timezone.utc)

        logger.info("Rollback completed: doc_id=%s", document_id)

    # ------------------------------------------------------------------
    # Direct rollback API
    # ------------------------------------------------------------------

    async def rollback_document(self, document_id: str) -> Dict[str, Any]:
        """명시적 롤백 API

        외부에서 문서 삭제를 요청할 때 사용합니다.

        Args:
            document_id: 삭제할 문서 ID

        Returns:
            삭제 결과 딕셔너리
        """
        start_time = time.monotonic()
        es_deleted = 0
        neo4j_deleted = 0

        try:
            es_deleted = await self._es.delete_by_document_id(document_id)
        except Exception as e:
            logger.warning("ES delete failed during rollback: %s", e)

        try:
            neo4j_deleted = await self._neo4j.delete_document_graph(document_id)
        except Exception as e:
            logger.warning("Neo4j delete failed during rollback: %s", e)

        latency_ms = (time.monotonic() - start_time) * 1000

        return {
            "document_id": document_id,
            "es_deleted": es_deleted,
            "neo4j_deleted": neo4j_deleted,
            "latency_ms": round(latency_ms, 2),
        }

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    async def health_check(self) -> Dict[str, Any]:
        """전체 저장소 상태 점검

        Returns:
            상태 정보 딕셔너리
        """
        neo4j_health = await self._neo4j.health_check()
        es_health = await self._es.health_check()

        return {
            "service": "StorageTransaction",
            "neo4j": neo4j_health,
            "elasticsearch": es_health,
            "all_connected": (
                neo4j_health.get("connected", False)
                and es_health.get("connected", False)
            ),
        }
