"""
Graph API 엔드포인트

Neo4j Knowledge Graph 기반 검색 제공
- /experts: 토픽별 전문가 검색
- /entities: 엔티티 조회
- /subgraph: 서브그래프 탐색

P0 작업: Backend-RAG API 불일치 해결
"""

import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.routes.auth import get_current_user
from app.core.exceptions import Neo4jError
from app.core.logging import get_logger
from app.storage.neo4j_storage import get_neo4j_storage_service

logger = get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------


class ExpertSearchRequest(BaseModel):
    """전문가 검색 요청 모델"""

    topic: str = Field(min_length=1, max_length=200, description="검색할 토픽/기술 키워드")
    limit: int = Field(default=10, ge=1, le=50, description="반환할 전문가 수")


class Expert(BaseModel):
    """전문가 정보 모델"""

    name: str = Field(description="전문가 이름")
    expertise: List[str] = Field(default_factory=list, description="전문 분야 목록")
    score: float = Field(description="관련성 점수")
    description: Optional[str] = Field(default=None, description="전문가 설명")
    related_projects: List[str] = Field(default_factory=list, description="관련 프로젝트")


class ExpertSearchResponse(BaseModel):
    """전문가 검색 응답 모델"""

    topic: str = Field(description="검색 토픽")
    experts: List[Expert] = Field(description="전문가 목록")
    total: int = Field(description="검색된 전문가 수")
    latency_ms: Optional[float] = Field(default=None, description="검색 소요 시간 (ms)")


class EntitySearchRequest(BaseModel):
    """엔티티 검색 요청 모델"""

    name: str = Field(min_length=1, max_length=200, description="검색할 엔티티 이름")


class EntityResponse(BaseModel):
    """엔티티 응답 모델"""

    name: str = Field(description="엔티티 이름")
    type: str = Field(description="엔티티 유형")
    description: Optional[str] = Field(default=None, description="엔티티 설명")
    labels: List[str] = Field(default_factory=list, description="Neo4j 라벨")
    properties: Dict[str, Any] = Field(default_factory=dict, description="추가 속성")


class SubgraphRequest(BaseModel):
    """서브그래프 탐색 요청 모델"""

    entity_name: str = Field(min_length=1, max_length=200, description="중심 엔티티 이름")
    depth: int = Field(default=2, ge=1, le=5, description="탐색 깊이")
    limit: int = Field(default=50, ge=1, le=200, description="최대 노드 수")


class SubgraphResponse(BaseModel):
    """서브그래프 응답 모델"""

    center: str = Field(description="중심 엔티티")
    nodes: List[Dict[str, Any]] = Field(description="노드 목록")
    edges: List[Dict[str, Any]] = Field(description="엣지 목록")
    node_count: int = Field(description="노드 수")


# ---------------------------------------------------------------------------
# Expert Search Endpoint (P0 - Primary)
# ---------------------------------------------------------------------------


@router.post(
    "/experts",
    response_model=ExpertSearchResponse,
    summary="전문가 검색",
    description="토픽/기술 키워드로 관련 전문가를 Neo4j Knowledge Graph에서 검색",
)
async def search_experts(
    request: ExpertSearchRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> ExpertSearchResponse:
    """
    토픽 기반 전문가 검색

    Neo4j Knowledge Graph에서 특정 토픽/기술과 관련된 전문가(Person)를
    검색합니다. MENTIONED_IN, USES, PARTICIPATED 관계를 기반으로
    관련성 점수를 계산합니다.

    Args:
        request: 전문가 검색 요청 (topic, limit)

    Returns:
        전문가 목록 및 전문 분야 정보

    Raises:
        HTTPException(500): Neo4j 조회 실패
    """
    logger.info(f"Expert search - Topic: {request.topic}, Limit: {request.limit}")
    start_time = time.monotonic()

    try:
        neo4j_service = get_neo4j_storage_service()

        # Neo4j 드라이버 접근
        driver = neo4j_service._ensure_driver()

        experts: List[Expert] = []

        async with driver.session(database=neo4j_service._database) as session:
            # 전문가 검색 Cypher 쿼리
            # Person 노드가 Technology/Topic/Knowledge 노드와 연결된 관계 기반으로 검색
            cypher = """
            // 1. 토픽/기술과 매칭되는 노드 찾기
            MATCH (topic)
            WHERE (topic:Technology AND toLower(topic.name) CONTAINS toLower($topic_keyword))
               OR (topic:Topic AND toLower(topic.name) CONTAINS toLower($topic_keyword))
               OR (topic:Keyword AND toLower(topic.value) CONTAINS toLower($topic_keyword))

            // 2. 관련 Person 노드 찾기 (여러 관계 유형)
            MATCH (person:Person)-[r]-(topic)
            WHERE type(r) IN ['MENTIONED_IN', 'USES', 'PARTICIPATED', 'RELATED_TO', 'CREATED', 'MANAGES']

            // 3. Person별 통계 집계
            WITH person,
                 collect(DISTINCT CASE
                     WHEN topic:Technology THEN topic.name
                     WHEN topic:Topic THEN topic.name
                     WHEN topic:Keyword THEN topic.value
                 END) AS expertise_list,
                 count(DISTINCT r) AS rel_count

            // 4. 관련 프로젝트 조회
            OPTIONAL MATCH (person)-[:PARTICIPATED|CREATED|MANAGES]->(project)
            WHERE project:Topic OR project:Knowledge

            WITH person, expertise_list, rel_count,
                 collect(DISTINCT COALESCE(project.name, project.title)) AS projects

            // 5. 점수 계산 및 정렬
            WITH person,
                 expertise_list,
                 projects,
                 (toFloat(rel_count) + size(expertise_list) * 0.5) / 10.0 AS score

            RETURN person.name AS name,
                   person.description AS description,
                   expertise_list AS expertise,
                   projects AS related_projects,
                   score

            ORDER BY score DESC
            LIMIT $limit
            """

            result = await session.run(
                cypher,
                topic_keyword=request.topic,
                limit=request.limit,
            )

            records = [dict(record) async for record in result]

            for record in records:
                # expertise 필터링 (null 제거)
                expertise = [e for e in record.get("expertise", []) if e]
                projects = [p for p in record.get("related_projects", []) if p]

                expert = Expert(
                    name=record.get("name", "Unknown"),
                    expertise=expertise[:10],  # 최대 10개
                    score=min(record.get("score", 0.0), 1.0),  # 0~1 범위로 정규화
                    description=record.get("description"),
                    related_projects=projects[:5],  # 최대 5개
                )
                experts.append(expert)

        latency_ms = (time.monotonic() - start_time) * 1000

        logger.info(
            f"Expert search complete - Topic: {request.topic}, "
            f"Found: {len(experts)}, Latency: {latency_ms:.1f}ms"
        )

        return ExpertSearchResponse(
            topic=request.topic,
            experts=experts,
            total=len(experts),
            latency_ms=round(latency_ms, 2),
        )

    except Neo4jError as e:
        logger.error(f"Neo4j error during expert search: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Knowledge Graph 조회 실패: {str(e)}",
        )
    except Exception as e:
        logger.exception(f"Expert search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"전문가 검색 처리 중 오류가 발생했습니다: {str(e)}",
        )


# ---------------------------------------------------------------------------
# Entity Search Endpoint
# ---------------------------------------------------------------------------


@router.get(
    "/entities/{name}",
    response_model=EntityResponse,
    summary="엔티티 조회",
    description="이름으로 엔티티 조회",
)
async def get_entity(
    name: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> EntityResponse:
    """
    이름으로 엔티티 조회

    Args:
        name: 엔티티 이름

    Returns:
        엔티티 정보

    Raises:
        HTTPException(404): 엔티티를 찾을 수 없음
        HTTPException(500): Neo4j 조회 실패
    """
    logger.info(f"Entity lookup - Name: {name}")

    try:
        neo4j_service = get_neo4j_storage_service()
        entity = await neo4j_service.get_entity_by_name(name)

        if entity is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"엔티티를 찾을 수 없습니다: {name}",
            )

        labels = entity.pop("labels", [])
        entity_type = labels[0] if labels else "Unknown"

        return EntityResponse(
            name=entity.get("name") or entity.get("value", name),
            type=entity_type,
            description=entity.get("description"),
            labels=labels,
            properties=entity,
        )

    except HTTPException:
        raise
    except Neo4jError as e:
        logger.error(f"Neo4j error during entity lookup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Knowledge Graph 조회 실패: {str(e)}",
        )
    except Exception as e:
        logger.exception(f"Entity lookup failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"엔티티 조회 중 오류가 발생했습니다: {str(e)}",
        )


# ---------------------------------------------------------------------------
# Subgraph Exploration Endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/subgraph",
    response_model=SubgraphResponse,
    summary="서브그래프 탐색",
    description="특정 엔티티를 중심으로 연결된 서브그래프 탐색",
)
async def explore_subgraph(
    request: SubgraphRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SubgraphResponse:
    """
    서브그래프 탐색

    특정 엔티티를 중심으로 지정된 깊이까지 연결된 노드와 관계를 탐색합니다.

    Args:
        request: 서브그래프 탐색 요청

    Returns:
        서브그래프 정보 (노드, 엣지)

    Raises:
        HTTPException(500): Neo4j 조회 실패
    """
    logger.info(
        f"Subgraph exploration - Entity: {request.entity_name}, "
        f"Depth: {request.depth}, Limit: {request.limit}"
    )

    try:
        neo4j_service = get_neo4j_storage_service()
        subgraph = await neo4j_service.query_subgraph(
            entity_name=request.entity_name,
            depth=request.depth,
            limit=request.limit,
        )

        return SubgraphResponse(
            center=subgraph.get("center", request.entity_name),
            nodes=subgraph.get("nodes", []),
            edges=subgraph.get("edges", []),
            node_count=len(subgraph.get("nodes", [])),
        )

    except Neo4jError as e:
        logger.error(f"Neo4j error during subgraph exploration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Knowledge Graph 조회 실패: {str(e)}",
        )
    except Exception as e:
        logger.exception(f"Subgraph exploration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"서브그래프 탐색 중 오류가 발생했습니다: {str(e)}",
        )
