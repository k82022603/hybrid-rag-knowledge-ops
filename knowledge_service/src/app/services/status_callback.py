"""
STORY-089: AI Service → Backend PG 상태 동기화 콜백 헬퍼

AI Service 파이프라인(온라인 + ETL 배치)에서 각 처리 단계 완료 시
Backend REST API를 호출하여 PostgreSQL documents 테이블을 업데이트합니다.

엔드포인트: POST /api/v1/documents/{document_id}/status
인증: X-Internal-Service: ai-service 헤더

상태 흐름:
    uploaded → queued → parsing(10%) → chunking(30%) → embedding(50%)
             → storing(70%) → extracting(85%) → completed(100%) / failed(0%)

ETL 3-Phase 콜백 시점:
    Phase 1 완료: status=chunking, progress=30, chunk_count, neo4j_synced=true
    Phase 2 완료: status=completed, progress=100, es_synced=true
    Phase 3 완료: status=completed (변경 없음), entity_count만 업데이트
"""

import os
from typing import Any, Dict, Optional
from uuid import UUID

from app.core.logging import get_logger

logger = get_logger(__name__)

# Backend API URL (Docker network 내부 통신)
# kp-api-gateway:8080 → SpringBoot Gateway → /api/v1/documents/{id}/status
_BACKEND_URL = os.getenv(
    "BACKEND_INTERNAL_URL",
    "http://kp-api-gateway:8080",
)
_CALLBACK_PATH = "/api/v1/documents/{document_id}/status"
_INTERNAL_SERVICE_HEADER = "ai-service"


async def notify_status(
    document_id: str | UUID,
    status: str,
    progress_percent: int = 0,
    error_message: Optional[str] = None,
    chunk_count: Optional[int] = None,
    entity_count: Optional[int] = None,
    es_synced: Optional[bool] = None,
    neo4j_synced: Optional[bool] = None,
) -> bool:
    """Backend API 콜백으로 PG 문서 처리 상태 업데이트

    STORY-089: AI Service 파이프라인 각 단계에서 호출.
    실패 시 경고 로그만 남기고 파이프라인 진행 유지 (non-blocking).

    Args:
        document_id: 문서 UUID
        status: 처리 상태 (parsing/chunking/embedding/storing/extracting/completed/failed)
        progress_percent: 진행률 0-100
        error_message: 실패 시 에러 메시지
        chunk_count: 생성된 청크 수 (completed 시)
        entity_count: 추출된 엔티티 수 (Phase 3 완료 시)
        es_synced: ES 동기화 완료 여부 (Phase 2 완료 시)
        neo4j_synced: Neo4j 동기화 완료 여부 (Phase 1 완료 시)

    Returns:
        True: 콜백 성공, False: 실패 (non-critical)
    """
    import httpx

    doc_id_str = str(document_id)
    url = f"{_BACKEND_URL}{_CALLBACK_PATH.format(document_id=doc_id_str)}"

    # 요청 바디 구성
    body: Dict[str, Any] = {
        "status": status,
        "progress_percent": progress_percent,
        "error_message": error_message,
        "metadata": {},
    }

    if chunk_count is not None:
        body["metadata"]["chunk_count"] = chunk_count
    if entity_count is not None:
        body["metadata"]["entity_count"] = entity_count
    if es_synced is not None:
        body["metadata"]["es_synced"] = es_synced
    if neo4j_synced is not None:
        body["metadata"]["neo4j_synced"] = neo4j_synced

    headers = {
        "Content-Type": "application/json",
        "X-Internal-Service": _INTERNAL_SERVICE_HEADER,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=body, headers=headers)
            if resp.status_code == 200:
                logger.debug(
                    "Status callback OK: doc=%s, status=%s, progress=%d%%",
                    doc_id_str[:8], status, progress_percent,
                )
                return True
            else:
                logger.warning(
                    "Status callback failed: doc=%s, status=%s, http=%d, body=%s",
                    doc_id_str[:8], status, resp.status_code, resp.text[:200],
                )
                return False

    except httpx.TimeoutException:
        logger.warning(
            "Status callback timeout: doc=%s, status=%s (non-critical)",
            doc_id_str[:8], status,
        )
        return False
    except Exception as e:
        logger.warning(
            "Status callback error: doc=%s, status=%s, error=%s (non-critical)",
            doc_id_str[:8], status, e,
        )
        return False


def notify_status_sync(
    document_id: str,
    status: str,
    progress_percent: int = 0,
    error_message: Optional[str] = None,
    chunk_count: Optional[int] = None,
    entity_count: Optional[int] = None,
    es_synced: Optional[bool] = None,
    neo4j_synced: Optional[bool] = None,
) -> bool:
    """동기 버전 콜백 (ETL 스크립트의 동기 컨텍스트용)

    import_embeddings.py 처럼 asyncio 루프 없이 실행되는
    순수 동기 스크립트에서 사용합니다.

    Args:
        동일 파라미터 (notify_status 참조)

    Returns:
        True: 콜백 성공, False: 실패 (non-critical)
    """
    import json
    import urllib.error
    import urllib.request

    doc_id_str = str(document_id)
    url = f"{_BACKEND_URL}{_CALLBACK_PATH.format(document_id=doc_id_str)}"

    body: Dict[str, Any] = {
        "status": status,
        "progress_percent": progress_percent,
        "error_message": error_message,
        "metadata": {},
    }

    if chunk_count is not None:
        body["metadata"]["chunk_count"] = chunk_count
    if entity_count is not None:
        body["metadata"]["entity_count"] = entity_count
    if es_synced is not None:
        body["metadata"]["es_synced"] = es_synced
    if neo4j_synced is not None:
        body["metadata"]["neo4j_synced"] = neo4j_synced

    try:
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "X-Internal-Service": _INTERNAL_SERVICE_HEADER,
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                logger.debug(
                    "Status callback OK: doc=%s, status=%s",
                    doc_id_str[:8], status,
                )
                return True
            else:
                logger.warning(
                    "Status callback failed: doc=%s, http=%d",
                    doc_id_str[:8], resp.status,
                )
                return False

    except urllib.error.URLError as e:
        logger.warning(
            "Status callback URLError: doc=%s, status=%s, error=%s (non-critical)",
            doc_id_str[:8], status, e,
        )
        return False
    except Exception as e:
        logger.warning(
            "Status callback error: doc=%s, error=%s (non-critical)",
            doc_id_str[:8], e,
        )
        return False
