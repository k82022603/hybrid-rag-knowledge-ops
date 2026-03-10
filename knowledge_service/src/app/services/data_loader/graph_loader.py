"""
Neo4j 그래프 데이터 적재 모듈

Document, Chunk, Entity 노드 및 관계를 Neo4j에 저장합니다.

Functions:
    store_to_neo4j: Neo4j에 그래프 데이터 저장
"""

from typing import Any, Dict, List

from app.core.config import settings
from app.core.logging import get_logger
from app.services.data_loader.models import FileInfo

logger = get_logger(__name__)


async def store_to_neo4j(
    document_id: str,
    file_info: FileInfo,
    chunks: List[Any],
    entities: List[Any],
    metadata: Dict[str, Any],
) -> None:
    """Neo4j에 그래프 데이터 저장

    Args:
        document_id: 문서 ID
        file_info: 파일 정보
        chunks: 청크 리스트
        entities: 엔티티 리스트
        metadata: 메타데이터
    """
    try:
        logger.info(
            "Storing to Neo4j: doc_id=%s, chunks=%d, entities=%d",
            document_id[:8],
            len(chunks),
            len(entities),
        )

        try:
            from neo4j import AsyncGraphDatabase

            driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password or ""),
            )

            try:
                async with driver.session() as session:
                    # Document 노드 생성
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

                    # Chunk 노드 및 PART_OF 관계 생성
                    for chunk in chunks:
                        await session.run(
                            """
                            MERGE (c:Chunk {id: $chunk_id})
                            SET c.content = $content,
                                c.chunk_index = $chunk_index,
                                c.heading = $heading,
                                c.token_count = $token_count
                            WITH c
                            MATCH (d:Document {id: $doc_id})
                            MERGE (c)-[:PART_OF]->(d)
                            """,
                            chunk_id=chunk.id,
                            content=chunk.content[:500],  # 저장 시 내용 제한
                            chunk_index=chunk.chunk_index,
                            heading=chunk.heading,
                            token_count=getattr(chunk, "token_count", 0),
                            doc_id=document_id,
                        )

                    # Entity 노드 + HAS_ENTITY 관계 생성
                    for entity in entities:
                        await session.run(
                            """
                            MERGE (e:Entity {name: $name})
                            SET e.type = $type,
                                e.description = $description
                            WITH e
                            MATCH (d:Document {id: $doc_id})
                            MERGE (d)-[:HAS_ENTITY]->(e)
                            """,
                            name=entity.name,
                            type=entity.type,
                            description=getattr(entity, "description", None),
                            doc_id=document_id,
                        )

                    # Entity 간 RELATED_TO 관계 생성 (동일 문서 내 엔티티)
                    if len(entities) > 1:
                        entity_names = [e.name for e in entities]
                        await session.run(
                            """
                            MATCH (d:Document {id: $doc_id})-[:HAS_ENTITY]->(e1:Entity)
                            MATCH (d)-[:HAS_ENTITY]->(e2:Entity)
                            WHERE e1.name < e2.name
                            MERGE (e1)-[:RELATED_TO {source_doc: $doc_id}]->(e2)
                            """,
                            doc_id=document_id,
                        )

                    logger.info(
                        "Neo4j storage completed: doc=%s, chunks=%d, entities=%d",
                        document_id[:8],
                        len(chunks),
                        len(entities),
                    )

            finally:
                await driver.close()

        except ImportError:
            logger.warning(
                "neo4j package not installed, skipping Neo4j storage "
                "(prepared doc=%s, chunks=%d, entities=%d)",
                document_id[:8],
                len(chunks),
                len(entities),
            )
        except Exception as e:
            logger.warning(
                "Neo4j storage failed (non-critical): %s", e
            )

    except Exception as e:
        logger.error("Neo4j storage error: %s", e)
