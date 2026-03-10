"""
Elasticsearch 적재 모듈

청크 및 벡터 데이터를 Elasticsearch에 벌크 인덱싱합니다.

Functions:
    store_to_elasticsearch: ES에 청크 + 벡터 저장
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def store_to_elasticsearch(
    document_id: str,
    chunks: List[Any],
    embeddings: Optional[List[Any]],
    metadata: Dict[str, Any],
    es_client_holder: Any = None,
) -> None:
    """Elasticsearch에 청크 및 벡터 저장

    Args:
        document_id: 문서 ID
        chunks: 청크 리스트
        embeddings: 임베딩 리스트
        metadata: 메타데이터
        es_client_holder: ES 클라이언트를 보유한 객체 (_es_client 속성 필요)
    """
    try:
        # Elasticsearch 클라이언트 확인
        es_url = settings.elasticsearch_url
        index_name = settings.elasticsearch_index

        logger.info(
            "Storing to Elasticsearch: doc_id=%s, chunks=%d, index=%s",
            document_id[:8],
            len(chunks),
            index_name,
        )

        # 벌크 인덱싱 문서 준비
        # ES date 매핑 호환: yyyy-MM-dd'T'HH:mm:ss.SSSZ (밀리초 3자리 + Z)
        now_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
        bulk_docs = []
        for i, chunk in enumerate(chunks):
            doc = {
                "document_id": document_id,
                "chunk_id": chunk.id,
                "chunk_index": i,
                "text": chunk.content,  # ES 매핑 필드명 "text"에 맞춤 (기존 "content"는 매핑 불일치)
                "heading": chunk.heading,
                "token_count": chunk.token_count,
                "metadata": metadata,
                "created_at": now_iso,
                # v2 추적 필드
                "embedding_status": "success" if embeddings else "pending",
                "chunker_version": "v2",
                "original_text_length": len(chunk.content),
                "embedded_at": now_iso if embeddings else None,
                "embedding_model": "bge-m3" if embeddings else None,
            }

            # 임베딩 벡터 추가
            if embeddings and i < len(embeddings):
                doc["dense_vector"] = embeddings[i].dense_vector
                if embeddings[i].sparse_vector:
                    doc["sparse_vector"] = embeddings[i].sparse_vector

            bulk_docs.append(doc)

        # 실제 ES 클라이언트 호출 (연결 가능 시)
        try:
            from elasticsearch import AsyncElasticsearch

            # ES 클라이언트 싱글톤 재사용 (P0 수정: 매 호출마다 new 방지)
            if es_client_holder is not None:
                if es_client_holder._es_client is None:
                    es_client_holder._es_client = AsyncElasticsearch(es_url)
                es = es_client_holder._es_client
            else:
                es = AsyncElasticsearch(es_url)

            # 벌크 인덱싱
            actions = []
            for doc in bulk_docs:
                actions.append({"index": {"_index": index_name, "_id": doc["chunk_id"]}})
                actions.append(doc)

            if actions:
                bulk_resp = await es.bulk(operations=actions, refresh="wait_for")
                if bulk_resp.get("errors"):
                    failed_items = [
                        item for item in bulk_resp["items"]
                        if "error" in item.get("index", {})
                    ]
                    logger.error(
                        "Elasticsearch bulk errors: %d/%d failed. First error: %s",
                        len(failed_items),
                        len(bulk_docs),
                        failed_items[0]["index"]["error"] if failed_items else "unknown",
                    )
                else:
                    logger.info(
                        "Elasticsearch bulk indexed: %d documents (verified)", len(bulk_docs)
                    )

            # es_client_holder가 없으면 자체 생성한 클라이언트를 닫음
            if es_client_holder is None:
                await es.close()

        except ImportError:
            logger.warning(
                "elasticsearch package not installed, skipping ES storage "
                "(prepared %d documents for indexing)",
                len(bulk_docs),
            )
        except Exception as e:
            logger.warning(
                "Elasticsearch storage failed (non-critical): %s", e
            )

    except Exception as e:
        logger.error("Elasticsearch storage error: %s", e)
        # 비치명적 에러 - 계속 진행
