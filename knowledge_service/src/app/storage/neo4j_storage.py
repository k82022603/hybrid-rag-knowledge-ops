"""
Neo4j 그래프 저장 서비스

STORY-006: Neo4j/Elasticsearch 저장 서비스 구현

엔티티/관계를 Knowledge Graph에 저장하고 조회합니다.
- MERGE 기반 중복 방지 (upsert 패턴)
- 비동기 지원 (async/await)
- 벌크 저장 최적화 (UNWIND)
- 트랜잭션 기반 원자성 보장
- 싱글톤 패턴 (get_neo4j_storage_service)

Neo4j Schema (infrastructure/database/neo4j/schema.cypher 참조):
    - Knowledge 노드: knowledge_id (UNIQUE), title, document_type
    - Chunk 노드: chunk_id (UNIQUE), knowledge_id
    - Person/Technology/Topic/Keyword 엔티티 노드
    - 관계: CONTAINS, MENTIONED_IN, USED_IN, CATEGORIZED_BY 등
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.agents.state import Entity, Relationship
from app.core.config import settings
from app.core.exceptions import Neo4jError
from app.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Entity type -> Neo4j label mapping
# ---------------------------------------------------------------------------

_ENTITY_TYPE_LABEL_MAP: Dict[str, str] = {
    "Person": "Person",
    "Organization": "Person",  # Organization -> Person label (people/orgs share node)
    "Technology": "Technology",
    "Project": "Topic",
    "Concept": "Topic",
    "Date": "Keyword",
    "Location": "Keyword",
}

_ENTITY_TYPE_ID_FIELD_MAP: Dict[str, str] = {
    "Person": "person_id",
    "Technology": "name",
    "Topic": "name",
    "Keyword": "value",
}


# ---------------------------------------------------------------------------
# Entity Label Strategy Pattern
# ---------------------------------------------------------------------------

from dataclasses import dataclass
from typing import Callable


@dataclass
class EntityLabelStrategy:
    """엔티티 라벨별 저장 전략

    각 Neo4j 라벨에 대한 저장 로직을 캡슐화합니다.

    Attributes:
        merge_key: MERGE 절에서 사용할 필드명 (name, value 등)
        include_entity_type: entity_type 필드 포함 여부
        include_slug: slug 필드 포함 여부 (Topic용)
        extra_fields: 추가 SET 절 필드 목록
    """

    merge_key: str = "name"
    include_entity_type: bool = False
    include_slug: bool = False

    def build_entity_data(self, entity: Any) -> Dict[str, Any]:
        """엔티티를 Cypher 파라미터로 변환

        Args:
            entity: Entity 객체

        Returns:
            Cypher UNWIND에서 사용할 딕셔너리
        """
        data = {
            "merge_val": entity.name,
            "description": entity.description or "",
            "original_id": entity.id,
        }
        if self.include_entity_type:
            data["entity_type"] = entity.type
        if self.include_slug:
            data["slug"] = entity.name.lower().replace(" ", "-")
        return data

    def build_cypher(self, label: str) -> str:
        """라벨에 맞는 Cypher 쿼리 생성

        Args:
            label: Neo4j 노드 라벨

        Returns:
            UNWIND + MERGE Cypher 쿼리 문자열
        """
        set_clauses = ["n.description = ent.description",
                       "n.original_id = ent.original_id",
                       "n.updated_at = $now"]

        if self.include_entity_type:
            set_clauses.insert(0, "n.entity_type = ent.entity_type")
        if self.include_slug:
            set_clauses.insert(0, "n.slug = ent.slug")

        set_clause = ",\n                ".join(set_clauses)

        return f"""
            UNWIND $entities AS ent
            MERGE (n:{label} {{{self.merge_key}: ent.merge_val}})
            SET {set_clause}
            RETURN count(n) AS cnt
            """


# 라벨별 저장 전략 매핑
# 새로운 엔티티 타입 추가 시 이 딕셔너리에만 추가하면 됨
_LABEL_STRATEGIES: Dict[str, EntityLabelStrategy] = {
    "Person": EntityLabelStrategy(
        merge_key="name",
        include_entity_type=True,
        include_slug=False,
    ),
    "Technology": EntityLabelStrategy(
        merge_key="name",
        include_entity_type=False,
        include_slug=False,
    ),
    "Topic": EntityLabelStrategy(
        merge_key="name",
        include_entity_type=False,
        include_slug=True,
    ),
    "Keyword": EntityLabelStrategy(
        merge_key="value",
        include_entity_type=True,
        include_slug=False,
    ),
}

# 기본 전략 (매핑에 없는 라벨용)
_DEFAULT_STRATEGY = EntityLabelStrategy(
    merge_key="value",
    include_entity_type=True,
    include_slug=False,
)


def _get_label_strategy(label: str) -> EntityLabelStrategy:
    """라벨에 맞는 저장 전략 반환

    Args:
        label: Neo4j 노드 라벨

    Returns:
        해당 라벨의 EntityLabelStrategy
    """
    return _LABEL_STRATEGIES.get(label, _DEFAULT_STRATEGY)


def _get_neo4j_label(entity_type: str) -> str:
    """엔티티 유형을 Neo4j 라벨로 매핑

    Args:
        entity_type: 엔티티 유형 (Person, Technology, Concept 등)

    Returns:
        Neo4j 노드 라벨 문자열
    """
    return _ENTITY_TYPE_LABEL_MAP.get(entity_type, "Keyword")


# ---------------------------------------------------------------------------
# Neo4jStorageService
# ---------------------------------------------------------------------------


class Neo4jStorageService:
    """
    Neo4j Knowledge Graph 저장 서비스

    엔티티와 관계를 Neo4j 그래프 데이터베이스에 저장하고 조회합니다.
    MERGE 패턴을 사용하여 중복 노드를 방지하고, UNWIND를 사용하여
    벌크 저장을 최적화합니다.

    Attributes:
        _driver: Neo4j 비동기 드라이버 인스턴스
        _database: Neo4j 데이터베이스 이름
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: str = "neo4j",
    ):
        """Neo4jStorageService 초기화

        드라이버를 즉시 생성하지 않고, 첫 사용 시 지연 연결합니다.

        Args:
            uri: Neo4j bolt URI (기본: 설정값)
            user: Neo4j 사용자 (기본: 설정값)
            password: Neo4j 비밀번호 (기본: 설정값)
            database: Neo4j 데이터베이스 이름 (기본: 'neo4j')
        """
        self._uri = uri or settings.neo4j_uri
        self._user = user or settings.neo4j_user
        self._password = password or settings.neo4j_password
        self._database = database
        self._driver: Optional[Any] = None

        logger.info(
            "Neo4jStorageService initialized: uri=%s, user=%s, database=%s",
            self._uri,
            self._user,
            self._database,
        )

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def _ensure_driver(self) -> Any:
        """Neo4j 드라이버 지연 초기화 (lazy connection)

        Returns:
            Neo4j AsyncGraphDatabase 드라이버

        Raises:
            Neo4jError: 드라이버 생성 실패 시
        """
        if self._driver is not None:
            return self._driver

        try:
            from neo4j import AsyncGraphDatabase

            auth = (self._user, self._password) if self._password else None
            self._driver = AsyncGraphDatabase.driver(
                self._uri,
                auth=auth,
                max_connection_pool_size=50,
                connection_acquisition_timeout=30,
            )
            logger.info("Neo4j driver connected: uri=%s", self._uri)
            return self._driver
        except ImportError:
            raise Neo4jError(
                message="neo4j 패키지가 설치되지 않았습니다. pip install neo4j",
                details={"package": "neo4j"},
            )
        except Exception as e:
            raise Neo4jError(
                message=f"Neo4j 드라이버 생성 실패: {e}",
                details={"uri": self._uri},
            )

    async def close(self) -> None:
        """드라이버 연결 종료"""
        if self._driver is not None:
            await self._driver.close()
            self._driver = None
            logger.info("Neo4j driver closed")

    async def verify_connectivity(self) -> bool:
        """Neo4j 연결 상태 확인

        Returns:
            연결 성공 여부
        """
        try:
            driver = self._ensure_driver()
            await driver.verify_connectivity()
            return True
        except Exception as e:
            logger.warning("Neo4j connectivity check failed: %s", e)
            return False

    # ------------------------------------------------------------------
    # Entity CRUD
    # ------------------------------------------------------------------

    async def save_entities(
        self,
        entities: List[Entity],
        knowledge_id: Optional[str] = None,
    ) -> int:
        """엔티티 목록을 Neo4j에 저장 (MERGE - upsert)

        동일 이름의 엔티티가 이미 존재하면 속성을 업데이트합니다.
        knowledge_id가 주어지면 MENTIONED_IN 관계도 함께 생성합니다.

        Args:
            entities: 저장할 엔티티 리스트
            knowledge_id: 연결할 Knowledge 노드 ID (Optional)

        Returns:
            저장된 엔티티 수

        Raises:
            Neo4jError: 저장 실패 시
        """
        if not entities:
            return 0

        start_time = time.monotonic()
        driver = self._ensure_driver()

        # 엔티티 유형별로 그룹핑 (Neo4j 라벨이 다르므로)
        grouped: Dict[str, List[Entity]] = {}
        for entity in entities:
            label = _get_neo4j_label(entity.type)
            grouped.setdefault(label, []).append(entity)

        saved_count = 0

        try:
            async with driver.session(database=self._database) as session:
                for label, label_entities in grouped.items():
                    count = await self._save_entities_by_label(
                        session=session,
                        label=label,
                        entities=label_entities,
                        knowledge_id=knowledge_id,
                    )
                    saved_count += count

            latency_ms = (time.monotonic() - start_time) * 1000
            logger.info(
                "Entities saved: total=%d, groups=%d, latency=%.1fms",
                saved_count,
                len(grouped),
                latency_ms,
            )
            return saved_count

        except Neo4jError:
            raise
        except Exception as e:
            raise Neo4jError(
                message=f"엔티티 저장 실패: {e}",
                details={"entity_count": len(entities)},
            )

    async def _save_entities_by_label(
        self,
        session: Any,
        label: str,
        entities: List[Entity],
        knowledge_id: Optional[str] = None,
    ) -> int:
        """특정 라벨의 엔티티를 벌크 저장

        UNWIND를 사용하여 한 번의 트랜잭션으로 여러 엔티티를 저장합니다.

        Args:
            session: Neo4j 세션
            label: Neo4j 노드 라벨
            entities: 동일 라벨의 엔티티 리스트
            knowledge_id: 연결할 Knowledge 노드 ID

        Returns:
            저장된 엔티티 수
        """
        now_iso = datetime.now(timezone.utc).isoformat()

        # 전략 패턴으로 라벨별 저장 로직 처리
        strategy = _get_label_strategy(label)
        entity_data = [strategy.build_entity_data(e) for e in entities]
        cypher = strategy.build_cypher(label)

        result = await session.run(
            cypher,
            entities=entity_data,
            now=now_iso,
        )
        record = await result.single()
        count = record["cnt"] if record else 0

        # knowledge_id가 있으면 MENTIONED_IN 관계 생성
        if knowledge_id and count > 0:
            await self._link_entities_to_knowledge(
                session=session,
                label=label,
                entities=entities,
                knowledge_id=knowledge_id,
            )

        return count

    async def _link_entities_to_knowledge(
        self,
        session: Any,
        label: str,
        entities: List[Entity],
        knowledge_id: str,
    ) -> None:
        """엔티티와 Knowledge 노드를 MENTIONED_IN 관계로 연결

        Args:
            session: Neo4j 세션
            label: 엔티티 라벨
            entities: 엔티티 리스트
            knowledge_id: Knowledge 노드 ID
        """
        now_iso = datetime.now(timezone.utc).isoformat()

        # 전략 패턴에서 merge_key 가져오기
        strategy = _get_label_strategy(label)
        merge_field = strategy.merge_key

        entity_names = [e.name for e in entities]

        cypher = f"""
        MATCH (k:Knowledge {{knowledge_id: $knowledge_id}})
        UNWIND $names AS entity_name
        MATCH (n:{label} {{{merge_field}: entity_name}})
        MERGE (n)-[r:MENTIONED_IN]->(k)
        SET r.created_at = $now
        """

        await session.run(
            cypher,
            knowledge_id=knowledge_id,
            names=entity_names,
            now=now_iso,
        )

    # ------------------------------------------------------------------
    # Relationship CRUD
    # ------------------------------------------------------------------

    async def save_relationships(
        self,
        relationships: List[Relationship],
        entities: List[Entity],
    ) -> int:
        """관계 목록을 Neo4j에 저장 (MERGE)

        source/target 엔티티 ID를 기반으로 이름을 매핑한 후,
        MERGE를 통해 관계를 생성합니다.

        Args:
            relationships: 저장할 관계 리스트
            entities: 관련된 엔티티 리스트 (ID -> 이름 매핑용)

        Returns:
            저장된 관계 수

        Raises:
            Neo4jError: 저장 실패 시
        """
        if not relationships or not entities:
            return 0

        start_time = time.monotonic()
        driver = self._ensure_driver()

        # 엔티티 ID -> (이름, 라벨) 매핑
        entity_map: Dict[str, Tuple[str, str]] = {}
        for e in entities:
            label = _get_neo4j_label(e.type)
            entity_map[e.id] = (e.name, label)

        # 유효한 관계만 필터링
        valid_rels = []
        for rel in relationships:
            if rel.source in entity_map and rel.target in entity_map:
                src_name, src_label = entity_map[rel.source]
                tgt_name, tgt_label = entity_map[rel.target]
                valid_rels.append({
                    "source_name": src_name,
                    "source_label": src_label,
                    "target_name": tgt_name,
                    "target_label": tgt_label,
                    "rel_type": rel.type or "RELATED_TO",
                    "description": rel.description or "",
                })

        if not valid_rels:
            logger.debug("No valid relationships to save (entity IDs not found)")
            return 0

        try:
            now_iso = datetime.now(timezone.utc).isoformat()
            saved_count = 0

            async with driver.session(database=self._database) as session:
                # 라벨 조합별로 그룹핑하여 Cypher 실행
                label_groups: Dict[Tuple[str, str], List[Dict]] = {}
                for rel in valid_rels:
                    key = (rel["source_label"], rel["target_label"])
                    label_groups.setdefault(key, []).append(rel)

                for (src_label, tgt_label), rels in label_groups.items():
                    # 전략 패턴에서 merge_key 가져오기
                    src_field = _get_label_strategy(src_label).merge_key
                    tgt_field = _get_label_strategy(tgt_label).merge_key

                    # UNWIND로 벌크 생성
                    cypher = f"""
                    UNWIND $rels AS rel
                    MATCH (s:{src_label} {{{src_field}: rel.source_name}})
                    MATCH (t:{tgt_label} {{{tgt_field}: rel.target_name}})
                    MERGE (s)-[r:RELATED_TO {{type: rel.rel_type}}]->(t)
                    SET r.description = rel.description,
                        r.updated_at = $now
                    RETURN count(r) AS cnt
                    """

                    result = await session.run(
                        cypher,
                        rels=rels,
                        now=now_iso,
                    )
                    record = await result.single()
                    saved_count += record["cnt"] if record else 0

            latency_ms = (time.monotonic() - start_time) * 1000
            logger.info(
                "Relationships saved: total=%d (valid=%d, input=%d), latency=%.1fms",
                saved_count,
                len(valid_rels),
                len(relationships),
                latency_ms,
            )
            return saved_count

        except Neo4jError:
            raise
        except Exception as e:
            raise Neo4jError(
                message=f"관계 저장 실패: {e}",
                details={"relationship_count": len(relationships)},
            )

    # ------------------------------------------------------------------
    # Document graph operations
    # ------------------------------------------------------------------

    async def save_document_graph(
        self,
        document_id: str,
        title: str,
        entities: List[Entity],
        relationships: List[Relationship],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, int]:
        """문서 그래프를 일괄 저장

        Knowledge 노드 생성 후 엔티티와 관계를 저장합니다.

        Args:
            document_id: 문서 고유 ID (knowledge_id)
            title: 문서 제목
            entities: 추출된 엔티티 리스트
            relationships: 추출된 관계 리스트
            metadata: 문서 메타데이터 (document_type, project_name 등)

        Returns:
            저장 통계 딕셔너리 {"knowledge": 1, "entities": n, "relationships": m}

        Raises:
            Neo4jError: 저장 실패 시
        """
        start_time = time.monotonic()
        driver = self._ensure_driver()
        meta = metadata or {}
        now_iso = datetime.now(timezone.utc).isoformat()

        try:
            # 1. Knowledge 노드 생성/업데이트
            async with driver.session(database=self._database) as session:
                cypher = """
                MERGE (k:Knowledge {knowledge_id: $knowledge_id})
                ON CREATE SET k.created_at = $now
                SET k.title = $title,
                    k.document_type = $document_type,
                    k.project_name = $project_name,
                    k.summary = $summary,
                    k.updated_at = $now
                RETURN k.knowledge_id AS kid
                """
                result = await session.run(
                    cypher,
                    knowledge_id=document_id,
                    title=title,
                    document_type=meta.get("document_type", ""),
                    project_name=meta.get("project_name", ""),
                    summary=meta.get("summary", ""),
                    now=now_iso,
                )
                await result.single()

            # 2. 엔티티 저장 + MENTIONED_IN 관계
            entity_count = await self.save_entities(
                entities=entities,
                knowledge_id=document_id,
            )

            # 3. 관계 저장
            rel_count = await self.save_relationships(
                relationships=relationships,
                entities=entities,
            )

            latency_ms = (time.monotonic() - start_time) * 1000
            stats = {
                "knowledge": 1,
                "entities": entity_count,
                "relationships": rel_count,
            }

            logger.info(
                "Document graph saved: doc_id=%s, entities=%d, rels=%d, latency=%.1fms",
                document_id,
                entity_count,
                rel_count,
                latency_ms,
            )

            return stats

        except Neo4jError:
            raise
        except Exception as e:
            raise Neo4jError(
                message=f"문서 그래프 저장 실패: {e}",
                details={"document_id": document_id},
            )

    async def save_chunks(
        self,
        knowledge_id: str,
        chunks: List[Dict[str, Any]],
    ) -> int:
        """청크 노드를 Neo4j에 저장하고 Knowledge 노드와 CONTAINS 관계 생성

        Args:
            knowledge_id: Knowledge 노드 ID
            chunks: 청크 데이터 리스트
                [{"chunk_id": str, "content": str, "chunk_index": int, ...}]

        Returns:
            저장된 청크 수

        Raises:
            Neo4jError: 저장 실패 시
        """
        if not chunks:
            return 0

        driver = self._ensure_driver()
        now_iso = datetime.now(timezone.utc).isoformat()

        try:
            async with driver.session(database=self._database) as session:
                chunk_data = [
                    {
                        "chunk_id": c.get("chunk_id", c.get("id", "")),
                        "content": c.get("content", "")[:500],  # 그래프에는 요약만
                        "chunk_index": c.get("chunk_index", 0),
                        "token_count": c.get("token_count", 0),
                    }
                    for c in chunks
                ]

                cypher = """
                MATCH (k:Knowledge {knowledge_id: $knowledge_id})
                UNWIND $chunks AS chunk
                MERGE (c:Chunk {chunk_id: chunk.chunk_id})
                ON CREATE SET c.created_at = $now
                SET c.content = chunk.content,
                    c.chunk_index = chunk.chunk_index,
                    c.token_count = chunk.token_count,
                    c.knowledge_id = $knowledge_id,
                    c.updated_at = $now
                MERGE (k)-[r:CONTAINS]->(c)
                SET r.chunk_index = chunk.chunk_index
                RETURN count(c) AS cnt
                """

                result = await session.run(
                    cypher,
                    knowledge_id=knowledge_id,
                    chunks=chunk_data,
                    now=now_iso,
                )
                record = await result.single()
                count = record["cnt"] if record else 0

                logger.info(
                    "Chunks saved to Neo4j: knowledge_id=%s, count=%d",
                    knowledge_id,
                    count,
                )
                return count

        except Exception as e:
            raise Neo4jError(
                message=f"청크 저장 실패: {e}",
                details={"knowledge_id": knowledge_id, "chunk_count": len(chunks)},
            )

    # ------------------------------------------------------------------
    # Query operations
    # ------------------------------------------------------------------

    # 보안: depth 파라미터 허용 범위 (Cypher 인젝션 방지)
    _MIN_DEPTH = 1
    _MAX_DEPTH = 5

    async def query_subgraph(
        self,
        entity_name: str,
        depth: int = 2,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """특정 엔티티를 중심으로 서브그래프 조회

        Args:
            entity_name: 중심 엔티티 이름
            depth: 탐색 깊이 (기본 2, 범위: 1-5)
            limit: 반환할 최대 노드 수

        Returns:
            서브그래프 딕셔너리 {"nodes": [...], "edges": [...], "center": str}

        Raises:
            Neo4jError: 조회 실패 시
            ValueError: depth 값이 정수가 아닌 경우
        """
        # ------------------------------------------------------------------
        # 보안: depth 파라미터 검증 (Cypher 인젝션 방지)
        # Neo4j 가변 길이 패턴 [*1..n]은 $param 형태의 파라미터 바인딩을
        # 지원하지 않으므로, 문자열 포맷팅이 필요합니다.
        # 안전성 확보를 위해 다음 검증을 수행합니다:
        # 1. 정수형 타입 검증
        # 2. 허용 범위 제한 (1-5)
        # ------------------------------------------------------------------
        if not isinstance(depth, int):
            raise ValueError(f"depth must be an integer, got {type(depth).__name__}")

        # 범위 제한: 1 <= depth <= 5 (성능 및 보안)
        validated_depth = max(self._MIN_DEPTH, min(depth, self._MAX_DEPTH))
        if validated_depth != depth:
            logger.warning(
                "depth value clamped: requested=%s, applied=%d (range: %d-%d)",
                depth,
                validated_depth,
                self._MIN_DEPTH,
                self._MAX_DEPTH,
            )

        driver = self._ensure_driver()

        try:
            async with driver.session(database=self._database) as session:
                # 서브그래프 조회: 노드 + 관계를 별도로 수집
                # 보안: validated_depth는 위에서 정수형 및 범위(1-5) 검증 완료
                cypher = f"""
                MATCH (center)
                WHERE center.name = $entity_name OR center.value = $entity_name
                   OR center.name CONTAINS $entity_name
                WITH center
                ORDER BY CASE
                    WHEN center.name = $entity_name THEN 0
                    WHEN center.value = $entity_name THEN 1
                    ELSE 2
                END
                LIMIT 1
                CALL {{
                    WITH center
                    MATCH (center)-[r*1..{validated_depth}]-(related)
                    WITH DISTINCT related
                    RETURN related
                    LIMIT $limit
                }}
                WITH center, collect(related) AS related_nodes
                WITH center, related_nodes,
                     [center] + related_nodes AS all_nodes
                UNWIND all_nodes AS a
                UNWIND all_nodes AS b
                WITH center, all_nodes,
                     a, b
                WHERE elementId(a) < elementId(b)
                OPTIONAL MATCH (a)-[r]-(b)
                WHERE r IS NOT NULL
                WITH center, all_nodes,
                     collect(DISTINCT r) AS rels
                RETURN center, all_nodes, rels
                """

                result = await session.run(
                    cypher,
                    entity_name=entity_name,
                    limit=limit,
                )

                records = [dict(record) async for record in result]

                if not records:
                    return {"nodes": [], "edges": [], "center": entity_name}

                record = records[0]

                # 노드 파싱: id, name, type(label) 포함
                nodes_out = []
                seen_ids = set()

                for node in record.get("all_nodes", []):
                    if node is None:
                        continue
                    node_id = str(node.element_id) if hasattr(node, "element_id") else str(id(node))
                    if node_id in seen_ids:
                        continue
                    seen_ids.add(node_id)

                    labels = list(node.labels) if hasattr(node, "labels") else []
                    props = dict(node) if node else {}
                    node_name = props.get("name") or props.get("value") or props.get("title", "Unknown")
                    node_type = labels[0] if labels else "Entity"

                    nodes_out.append({
                        "id": node_id,
                        "name": node_name,
                        "type": node_type,
                        "labels": labels,
                        "properties": {k: str(v) if not isinstance(v, (str, int, float, bool)) else v
                                       for k, v in props.items()},
                    })

                # 엣지 파싱: source, target, type 포함
                edges_out = []
                for rel in record.get("rels", []):
                    if rel is None:
                        continue
                    edges_out.append({
                        "source": str(rel.start_node.element_id) if hasattr(rel, "start_node") else "",
                        "target": str(rel.end_node.element_id) if hasattr(rel, "end_node") else "",
                        "type": rel.type if hasattr(rel, "type") else "RELATED_TO",
                    })

                logger.info(
                    "Subgraph query: entity=%s, depth=%d, nodes=%d, edges=%d",
                    entity_name,
                    validated_depth,
                    len(nodes_out),
                    len(edges_out),
                )

                return {
                    "nodes": nodes_out,
                    "edges": edges_out,
                    "center": entity_name,
                }

        except Exception as e:
            raise Neo4jError(
                message=f"서브그래프 조회 실패: {e}",
                details={"entity_name": entity_name, "depth": depth},
            )

    async def get_entity_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """이름으로 엔티티 조회

        Args:
            name: 엔티티 이름

        Returns:
            엔티티 딕셔너리 또는 None
        """
        driver = self._ensure_driver()

        try:
            async with driver.session(database=self._database) as session:
                cypher = """
                MATCH (n)
                WHERE n.name = $name OR n.value = $name
                RETURN n, labels(n) AS labels
                LIMIT 1
                """
                result = await session.run(cypher, name=name)
                record = await result.single()

                if record is None:
                    return None

                node_dict = self._node_to_dict(record["n"])
                node_dict["labels"] = list(record["labels"])
                return node_dict

        except Exception as e:
            logger.warning("Entity lookup failed: name=%s, error=%s", name, e)
            return None

    # ------------------------------------------------------------------
    # Delete operations (rollback support)
    # ------------------------------------------------------------------

    async def delete_document_graph(self, document_id: str) -> int:
        """문서와 관련된 모든 그래프 노드/관계 삭제 (롤백용)

        Knowledge 노드와 CONTAINS 관계로 연결된 Chunk 노드를 삭제합니다.
        엔티티 노드는 다른 문서에서도 참조될 수 있으므로 삭제하지 않습니다.

        Args:
            document_id: 삭제할 Knowledge 노드 ID

        Returns:
            삭제된 노드 수

        Raises:
            Neo4jError: 삭제 실패 시
        """
        driver = self._ensure_driver()

        try:
            async with driver.session(database=self._database) as session:
                # Chunk 노드 삭제 (CONTAINS 관계 포함)
                cypher_chunks = """
                MATCH (k:Knowledge {knowledge_id: $doc_id})-[:CONTAINS]->(c:Chunk)
                DETACH DELETE c
                RETURN count(c) AS deleted_chunks
                """
                result = await session.run(cypher_chunks, doc_id=document_id)
                record = await result.single()
                deleted_chunks = record["deleted_chunks"] if record else 0

                # Knowledge 노드 삭제
                cypher_knowledge = """
                MATCH (k:Knowledge {knowledge_id: $doc_id})
                DETACH DELETE k
                RETURN count(k) AS deleted_knowledge
                """
                result = await session.run(cypher_knowledge, doc_id=document_id)
                record = await result.single()
                deleted_knowledge = record["deleted_knowledge"] if record else 0

                total = deleted_chunks + deleted_knowledge
                logger.info(
                    "Document graph deleted: doc_id=%s, chunks=%d, knowledge=%d",
                    document_id,
                    deleted_chunks,
                    deleted_knowledge,
                )
                return total

        except Exception as e:
            raise Neo4jError(
                message=f"문서 그래프 삭제 실패: {e}",
                details={"document_id": document_id},
            )

    # ------------------------------------------------------------------
    # Health & stats
    # ------------------------------------------------------------------

    async def health_check(self) -> Dict[str, Any]:
        """서비스 상태 점검

        Returns:
            상태 정보 딕셔너리
        """
        connected = await self.verify_connectivity()

        result = {
            "service": "Neo4jStorageService",
            "connected": connected,
            "uri": self._uri,
            "database": self._database,
        }

        if connected:
            try:
                driver = self._ensure_driver()
                async with driver.session(database=self._database) as session:
                    stats_result = await session.run(
                        "MATCH (n) RETURN labels(n) AS label, count(n) AS cnt "
                        "ORDER BY cnt DESC LIMIT 10"
                    )
                    records = [dict(r) async for r in stats_result]
                    result["node_stats"] = {
                        str(r["label"]): r["cnt"] for r in records
                    }
            except Exception as e:
                result["stats_error"] = str(e)

        return result

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _node_to_dict(node: Any) -> Dict[str, Any]:
        """Neo4j Node 객체를 딕셔너리로 변환

        Args:
            node: Neo4j Node 객체

        Returns:
            노드 속성 딕셔너리
        """
        if node is None:
            return {}
        try:
            return dict(node)
        except (TypeError, AttributeError):
            return {"_raw": str(node)}


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------

_neo4j_storage_service: Optional[Neo4jStorageService] = None


def get_neo4j_storage_service(**kwargs: Any) -> Neo4jStorageService:
    """Neo4jStorageService 싱글톤 팩토리

    처음 호출 시 인스턴스를 생성하고, 이후에는 동일 인스턴스를 반환합니다.

    Args:
        **kwargs: Neo4jStorageService 생성자 인자

    Returns:
        Neo4jStorageService 인스턴스 (싱글톤)
    """
    global _neo4j_storage_service
    if _neo4j_storage_service is None:
        _neo4j_storage_service = Neo4jStorageService(**kwargs)
    return _neo4j_storage_service


def reset_neo4j_storage_service() -> None:
    """싱글톤 인스턴스 초기화 (테스트용)"""
    global _neo4j_storage_service
    _neo4j_storage_service = None
