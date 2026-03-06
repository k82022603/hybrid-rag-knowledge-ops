"""Neo4jStorageService 단위 테스트

STORY-006: Neo4j/Elasticsearch 저장 서비스 - Neo4j 단위 테스트

테스트 범위:
    - 서비스 초기화 및 설정
    - 엔티티 저장 (save_entities)
    - 관계 저장 (save_relationships)
    - 문서 그래프 저장 (save_document_graph)
    - 청크 저장 (save_chunks)
    - 서브그래프 조회 (query_subgraph)
    - 엔티티 조회 (get_entity_by_name)
    - 문서 그래프 삭제 (delete_document_graph)
    - 연결 검증 (verify_connectivity)
    - 싱글톤 팩토리
    - 에러 핸들링
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Async iteration helper for mocking Neo4j Result objects
# ---------------------------------------------------------------------------

class AsyncRecordIterator:
    """Mock async iterator that properly implements __aiter__/__anext__.

    Neo4j Result objects support ``async for record in result``.
    ``AsyncMock.__aiter__`` returns a coroutine which does NOT satisfy
    the async-iterator protocol.  This helper wraps a plain iterable so
    that it can be consumed via ``async for``.
    """

    def __init__(self, records):
        self._records = iter(records)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._records)
        except StopIteration:
            raise StopAsyncIteration

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# importlib로 직접 모듈 로드 (무거운 의존성 회피)
import importlib.util

_neo4j_spec = importlib.util.spec_from_file_location(
    "app.storage.neo4j_storage",
    os.path.join(
        os.path.dirname(__file__), "..", "..", "app", "storage", "neo4j_storage.py"
    ),
)
_neo4j_module = importlib.util.module_from_spec(_neo4j_spec)
sys.modules["app.storage.neo4j_storage"] = _neo4j_module
_neo4j_spec.loader.exec_module(_neo4j_module)

Neo4jStorageService = _neo4j_module.Neo4jStorageService
get_neo4j_storage_service = _neo4j_module.get_neo4j_storage_service
reset_neo4j_storage_service = _neo4j_module.reset_neo4j_storage_service
_get_neo4j_label = _neo4j_module._get_neo4j_label
# 전략 패턴 관련 모듈
EntityLabelStrategy = _neo4j_module.EntityLabelStrategy
_get_label_strategy = _neo4j_module._get_label_strategy
_LABEL_STRATEGIES = _neo4j_module._LABEL_STRATEGIES
_DEFAULT_STRATEGY = _neo4j_module._DEFAULT_STRATEGY

# 상태 모듈에서 Entity, Relationship 가져오기
from app.agents.state import Entity, Relationship


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_singleton():
    """각 테스트 전후로 싱글톤 리셋"""
    reset_neo4j_storage_service()
    yield
    reset_neo4j_storage_service()


@pytest.fixture
def mock_settings():
    """설정 모킹"""
    mock_s = MagicMock()
    mock_s.neo4j_uri = "bolt://localhost:7687"
    mock_s.neo4j_user = "neo4j"
    mock_s.neo4j_password = "test_password"
    original_settings = _neo4j_module.settings
    _neo4j_module.settings = mock_s
    yield mock_s
    _neo4j_module.settings = original_settings


@pytest.fixture
def service(mock_settings):
    """Neo4jStorageService 인스턴스"""
    return Neo4jStorageService(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="test_password",
    )


@pytest.fixture
def sample_entities():
    """테스트용 엔티티 리스트"""
    return [
        Entity(id="e1", name="Python", type="Technology", description="프로그래밍 언어"),
        Entity(id="e2", name="홍길동", type="Person", description="개발자"),
        Entity(id="e3", name="RAG", type="Concept", description="검색 증강 생성"),
        Entity(id="e4", name="2024-01-01", type="Date", description="프로젝트 시작일"),
        Entity(id="e5", name="서울", type="Location", description="본사 위치"),
    ]


@pytest.fixture
def sample_relationships():
    """테스트용 관계 리스트"""
    return [
        Relationship(source="e2", target="e1", type="USES", description="Python을 사용"),
        Relationship(source="e2", target="e3", type="CREATED", description="RAG 개발"),
        Relationship(
            source="e1", target="e3", type="RELATED_TO", description="Python과 RAG 관련"
        ),
    ]


class MockNeo4jResult:
    """Mock Neo4j Result that supports both ``async for`` and ``.single()``.

    ``MagicMock`` / ``AsyncMock`` cannot easily provide a working
    ``__aiter__`` / ``__anext__`` pair because dunder methods are resolved
    on the *type*, not the instance.  This lightweight class avoids that
    problem entirely.
    """

    def __init__(self, records=None, single_value=None):
        if single_value is None and records:
            single_value = records[0]
        self._records = list(records) if records else []
        self._single_value = single_value
        self._iter = None

    def __aiter__(self):
        self._iter = iter(self._records)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration

    async def single(self):
        return self._single_value


def _make_mock_result(records=None, single_value=None):
    """Mock Neo4j Result 생성 (async for 지원).

    Args:
        records: async for로 순회할 레코드 리스트 (None이면 [single_value] 사용)
        single_value: result.single()이 반환할 값
    """
    if single_value is None and records is None:
        single_value = {"cnt": 3, "kid": "doc-001"}
    if records is None:
        records = [single_value] if single_value is not None else []

    return MockNeo4jResult(records=records, single_value=single_value)


def _make_mock_session():
    """Mock Neo4j 세션 생성"""
    mock_session = AsyncMock()

    mock_result = _make_mock_result()
    mock_session.run = AsyncMock(return_value=mock_result)

    return mock_session


def _make_mock_driver():
    """Mock Neo4j 드라이버 생성"""
    mock_driver = AsyncMock()
    mock_session = _make_mock_session()

    # session() 컨텍스트 매니저
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    mock_driver.session = MagicMock(return_value=mock_ctx)

    mock_driver.verify_connectivity = AsyncMock()
    mock_driver.close = AsyncMock()

    return mock_driver, mock_session


# ---------------------------------------------------------------------------
# Tests: Initialization
# ---------------------------------------------------------------------------


class TestNeo4jStorageServiceInit:
    """초기화 테스트"""

    def test_init_with_defaults(self, mock_settings):
        """기본 설정으로 초기화"""
        svc = Neo4jStorageService()
        assert svc._uri == "bolt://localhost:7687"
        assert svc._user == "neo4j"
        assert svc._database == "neo4j"
        assert svc._driver is None

    def test_init_with_custom_params(self, mock_settings):
        """커스텀 파라미터로 초기화"""
        svc = Neo4jStorageService(
            uri="bolt://custom:7687",
            user="custom_user",
            password="custom_pass",
            database="custom_db",
        )
        assert svc._uri == "bolt://custom:7687"
        assert svc._user == "custom_user"
        assert svc._database == "custom_db"

    def test_driver_not_created_on_init(self, service):
        """초기화 시 드라이버가 생성되지 않음 (lazy)"""
        assert service._driver is None


# ---------------------------------------------------------------------------
# Tests: Entity label mapping
# ---------------------------------------------------------------------------


class TestEntityLabelMapping:
    """엔티티 유형 -> Neo4j 라벨 매핑 테스트"""

    def test_person_mapping(self):
        assert _get_neo4j_label("Person") == "Person"

    def test_organization_mapping(self):
        assert _get_neo4j_label("Organization") == "Person"

    def test_technology_mapping(self):
        assert _get_neo4j_label("Technology") == "Technology"

    def test_project_mapping(self):
        assert _get_neo4j_label("Project") == "Topic"

    def test_concept_mapping(self):
        assert _get_neo4j_label("Concept") == "Topic"

    def test_date_mapping(self):
        assert _get_neo4j_label("Date") == "Keyword"

    def test_location_mapping(self):
        assert _get_neo4j_label("Location") == "Keyword"

    def test_unknown_type_defaults_to_keyword(self):
        assert _get_neo4j_label("UnknownType") == "Keyword"


# ---------------------------------------------------------------------------
# Tests: save_entities
# ---------------------------------------------------------------------------


class TestSaveEntities:
    """엔티티 저장 테스트"""

    @pytest.mark.asyncio
    async def test_save_entities_empty_list(self, service):
        """빈 엔티티 리스트 저장 - 0 반환"""
        result = await service.save_entities([])
        assert result == 0

    @pytest.mark.asyncio
    async def test_save_entities_success(self, service, sample_entities):
        """엔티티 저장 성공"""
        mock_driver, mock_session = _make_mock_driver()
        service._driver = mock_driver

        result = await service.save_entities(sample_entities)

        # 4개 그룹 (Person, Technology, Topic, Keyword) 이므로 각 3 반환
        # 그룹 수에 따라 session.run 호출 횟수가 달라짐
        assert result > 0
        assert mock_session.run.called

    @pytest.mark.asyncio
    async def test_save_entities_with_knowledge_id(self, service, sample_entities):
        """Knowledge ID와 함께 엔티티 저장 (MENTIONED_IN 관계 생성)"""
        mock_driver, mock_session = _make_mock_driver()
        service._driver = mock_driver

        result = await service.save_entities(
            sample_entities, knowledge_id="doc-001"
        )

        assert result > 0
        # MENTIONED_IN 관계 생성을 위한 추가 쿼리가 실행되었는지 확인
        call_count = mock_session.run.call_count
        # 엔티티 저장 + MENTIONED_IN 관계 = 그룹 수 x 2
        assert call_count > len(set(_get_neo4j_label(e.type) for e in sample_entities))

    @pytest.mark.asyncio
    async def test_save_entities_groups_by_label(self, service, sample_entities):
        """엔티티가 라벨별로 그룹핑되는지 확인"""
        mock_driver, mock_session = _make_mock_driver()
        service._driver = mock_driver

        await service.save_entities(sample_entities)

        # 각 그룹별로 UNWIND 쿼리가 실행됨
        for call_args in mock_session.run.call_args_list:
            cypher = call_args[0][0]
            assert "UNWIND" in cypher or "MATCH" in cypher

    @pytest.mark.asyncio
    async def test_save_entities_driver_error(self, service, sample_entities):
        """드라이버 오류 시 Neo4jError 발생"""
        # neo4j 패키지가 없는 경우를 시뮬레이션
        with patch.dict(sys.modules, {"neo4j": None}):
            # _driver가 None이면 _ensure_driver가 호출됨
            service._driver = None
            with pytest.raises(Exception):
                await service.save_entities(sample_entities)


# ---------------------------------------------------------------------------
# Tests: save_relationships
# ---------------------------------------------------------------------------


class TestSaveRelationships:
    """관계 저장 테스트"""

    @pytest.mark.asyncio
    async def test_save_relationships_empty(self, service):
        """빈 관계 리스트 저장"""
        result = await service.save_relationships([], [])
        assert result == 0

    @pytest.mark.asyncio
    async def test_save_relationships_success(
        self, service, sample_entities, sample_relationships
    ):
        """관계 저장 성공"""
        mock_driver, mock_session = _make_mock_driver()
        service._driver = mock_driver

        result = await service.save_relationships(
            sample_relationships, sample_entities
        )

        assert result > 0
        assert mock_session.run.called

    @pytest.mark.asyncio
    async def test_save_relationships_invalid_entity_id(
        self, service, sample_entities
    ):
        """존재하지 않는 엔티티 ID를 가진 관계는 무시"""
        mock_driver, mock_session = _make_mock_driver()
        service._driver = mock_driver

        invalid_rels = [
            Relationship(
                source="nonexistent_1",
                target="nonexistent_2",
                type="USES",
                description="유효하지 않은 관계",
            ),
        ]

        result = await service.save_relationships(invalid_rels, sample_entities)
        assert result == 0

    @pytest.mark.asyncio
    async def test_save_relationships_no_entities(
        self, service, sample_relationships
    ):
        """엔티티 없이 관계 저장 시도"""
        result = await service.save_relationships(sample_relationships, [])
        assert result == 0


# ---------------------------------------------------------------------------
# Tests: save_document_graph
# ---------------------------------------------------------------------------


class TestSaveDocumentGraph:
    """문서 그래프 저장 테스트"""

    @pytest.mark.asyncio
    async def test_save_document_graph_success(
        self, service, sample_entities, sample_relationships
    ):
        """문서 그래프 일괄 저장 성공"""
        mock_driver, mock_session = _make_mock_driver()
        service._driver = mock_driver

        stats = await service.save_document_graph(
            document_id="doc-001",
            title="테스트 문서",
            entities=sample_entities,
            relationships=sample_relationships,
            metadata={"document_type": "기술문서", "project_name": "RAG"},
        )

        assert "knowledge" in stats
        assert stats["knowledge"] == 1
        assert "entities" in stats
        assert "relationships" in stats

    @pytest.mark.asyncio
    async def test_save_document_graph_empty_entities(self, service):
        """엔티티 없이 문서 그래프 저장"""
        mock_driver, mock_session = _make_mock_driver()
        service._driver = mock_driver

        stats = await service.save_document_graph(
            document_id="doc-002",
            title="빈 문서",
            entities=[],
            relationships=[],
        )

        assert stats["knowledge"] == 1
        assert stats["entities"] == 0
        assert stats["relationships"] == 0


# ---------------------------------------------------------------------------
# Tests: save_chunks
# ---------------------------------------------------------------------------


class TestSaveChunks:
    """청크 저장 테스트"""

    @pytest.mark.asyncio
    async def test_save_chunks_empty(self, service):
        """빈 청크 리스트"""
        result = await service.save_chunks("doc-001", [])
        assert result == 0

    @pytest.mark.asyncio
    async def test_save_chunks_success(self, service):
        """청크 저장 성공"""
        mock_driver, mock_session = _make_mock_driver()
        service._driver = mock_driver

        chunks = [
            {
                "chunk_id": "chunk-001",
                "content": "테스트 청크 내용 1",
                "chunk_index": 0,
                "token_count": 10,
            },
            {
                "chunk_id": "chunk-002",
                "content": "테스트 청크 내용 2",
                "chunk_index": 1,
                "token_count": 15,
            },
        ]

        result = await service.save_chunks("doc-001", chunks)
        assert result > 0
        assert mock_session.run.called

        # MERGE + CONTAINS 쿼리 확인
        cypher = mock_session.run.call_args[0][0]
        assert "MERGE" in cypher
        assert "CONTAINS" in cypher


# ---------------------------------------------------------------------------
# Tests: query_subgraph
# ---------------------------------------------------------------------------


class TestQuerySubgraph:
    """서브그래프 조회 테스트"""

    @pytest.mark.asyncio
    async def test_query_subgraph_empty_result(self, service):
        """결과 없는 서브그래프 조회"""
        mock_driver, mock_session = _make_mock_driver()

        # 빈 결과 반환 (async for 가능한 이터레이터)
        mock_result = _make_mock_result(records=[], single_value=None)
        mock_session.run = AsyncMock(return_value=mock_result)

        service._driver = mock_driver

        result = await service.query_subgraph("없는_엔티티")

        assert result["nodes"] == []
        assert result["edges"] == []
        assert result["center"] == "없는_엔티티"

    @pytest.mark.asyncio
    async def test_query_subgraph_with_depth(self, service):
        """깊이 지정 서브그래프 조회"""
        mock_driver, mock_session = _make_mock_driver()

        # 빈 결과 반환 (async for 가능한 이터레이터)
        mock_result = _make_mock_result(records=[], single_value=None)
        mock_session.run = AsyncMock(return_value=mock_result)

        service._driver = mock_driver

        await service.query_subgraph("Python", depth=3, limit=100)

        # Cypher 쿼리에 depth가 반영되었는지 확인
        cypher = mock_session.run.call_args[0][0]
        assert "3" in cypher

    @pytest.mark.asyncio
    async def test_query_subgraph_depth_validation_non_integer(self, service):
        """depth가 정수가 아닐 경우 ValueError 발생 (Cypher 인젝션 방지)"""
        mock_driver, _ = _make_mock_driver()
        service._driver = mock_driver

        with pytest.raises(ValueError) as exc_info:
            await service.query_subgraph("Python", depth="3; DROP DATABASE")  # type: ignore

        assert "must be an integer" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_query_subgraph_depth_clamped_to_max(self, service):
        """depth가 최대값(5)을 초과할 경우 5로 제한"""
        mock_driver, mock_session = _make_mock_driver()
        mock_result = _make_mock_result(records=[], single_value=None)
        mock_session.run = AsyncMock(return_value=mock_result)
        service._driver = mock_driver

        await service.query_subgraph("Python", depth=10)

        # Cypher 쿼리에 최대값 5가 반영되었는지 확인
        cypher = mock_session.run.call_args[0][0]
        assert "[r*1..5]" in cypher

    @pytest.mark.asyncio
    async def test_query_subgraph_depth_clamped_to_min(self, service):
        """depth가 최소값(1) 미만일 경우 1로 제한"""
        mock_driver, mock_session = _make_mock_driver()
        mock_result = _make_mock_result(records=[], single_value=None)
        mock_session.run = AsyncMock(return_value=mock_result)
        service._driver = mock_driver

        await service.query_subgraph("Python", depth=0)

        # Cypher 쿼리에 최소값 1이 반영되었는지 확인
        cypher = mock_session.run.call_args[0][0]
        assert "[r*1..1]" in cypher

    @pytest.mark.asyncio
    async def test_query_subgraph_depth_valid_range(self, service):
        """depth가 유효 범위(1-5) 내에 있으면 그대로 사용"""
        mock_driver, mock_session = _make_mock_driver()
        mock_result = _make_mock_result(records=[], single_value=None)
        mock_session.run = AsyncMock(return_value=mock_result)
        service._driver = mock_driver

        await service.query_subgraph("Python", depth=4)

        # Cypher 쿼리에 지정한 depth가 반영되었는지 확인
        cypher = mock_session.run.call_args[0][0]
        assert "[r*1..4]" in cypher


# ---------------------------------------------------------------------------
# Tests: get_entity_by_name
# ---------------------------------------------------------------------------


class TestGetEntityByName:
    """엔티티 이름 조회 테스트"""

    @pytest.mark.asyncio
    async def test_get_entity_found(self, service):
        """엔티티 조회 성공"""
        mock_driver, mock_session = _make_mock_driver()

        mock_node = {"name": "Python", "description": "프로그래밍 언어"}
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(
            return_value={"n": mock_node, "labels": ["Technology"]}
        )
        mock_session.run = AsyncMock(return_value=mock_result)

        service._driver = mock_driver

        result = await service.get_entity_by_name("Python")

        assert result is not None
        assert result["labels"] == ["Technology"]

    @pytest.mark.asyncio
    async def test_get_entity_not_found(self, service):
        """존재하지 않는 엔티티 조회"""
        mock_driver, mock_session = _make_mock_driver()

        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value=None)
        mock_session.run = AsyncMock(return_value=mock_result)

        service._driver = mock_driver

        result = await service.get_entity_by_name("NonExistent")
        assert result is None


# ---------------------------------------------------------------------------
# Tests: delete_document_graph
# ---------------------------------------------------------------------------


class TestDeleteDocumentGraph:
    """문서 그래프 삭제 테스트"""

    @pytest.mark.asyncio
    async def test_delete_document_graph(self, service):
        """문서 그래프 삭제 성공"""
        mock_driver, mock_session = _make_mock_driver()

        # 청크 삭제 결과
        chunk_result = AsyncMock()
        chunk_result.single = AsyncMock(return_value={"deleted_chunks": 5})

        # Knowledge 삭제 결과
        knowledge_result = AsyncMock()
        knowledge_result.single = AsyncMock(return_value={"deleted_knowledge": 1})

        mock_session.run = AsyncMock(
            side_effect=[chunk_result, knowledge_result]
        )

        service._driver = mock_driver

        total = await service.delete_document_graph("doc-001")
        assert total == 6  # 5 chunks + 1 knowledge


# ---------------------------------------------------------------------------
# Tests: verify_connectivity
# ---------------------------------------------------------------------------


class TestVerifyConnectivity:
    """연결 검증 테스트"""

    @pytest.mark.asyncio
    async def test_verify_connectivity_success(self, service):
        """연결 성공"""
        mock_driver, _ = _make_mock_driver()
        service._driver = mock_driver

        result = await service.verify_connectivity()
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_connectivity_failure(self, service):
        """연결 실패"""
        mock_driver, _ = _make_mock_driver()
        mock_driver.verify_connectivity = AsyncMock(side_effect=Exception("Connection refused"))
        service._driver = mock_driver

        result = await service.verify_connectivity()
        assert result is False


# ---------------------------------------------------------------------------
# Tests: close
# ---------------------------------------------------------------------------


class TestClose:
    """연결 종료 테스트"""

    @pytest.mark.asyncio
    async def test_close_with_driver(self, service):
        """드라이버가 있을 때 종료"""
        mock_driver, _ = _make_mock_driver()
        service._driver = mock_driver

        await service.close()

        mock_driver.close.assert_called_once()
        assert service._driver is None

    @pytest.mark.asyncio
    async def test_close_without_driver(self, service):
        """드라이버가 없을 때 종료 (무시)"""
        await service.close()
        assert service._driver is None


# ---------------------------------------------------------------------------
# Tests: health_check
# ---------------------------------------------------------------------------


class TestHealthCheck:
    """상태 점검 테스트"""

    @pytest.mark.asyncio
    async def test_health_check_connected(self, service):
        """연결된 상태의 health check"""
        mock_driver, mock_session = _make_mock_driver()

        # stats 결과 (async for 가능한 이터레이터)
        stats_records = [
            {"label": ["Knowledge"], "cnt": 100},
            {"label": ["Chunk"], "cnt": 500},
        ]
        mock_stats_result = _make_mock_result(records=stats_records, single_value=None)
        mock_session.run = AsyncMock(return_value=mock_stats_result)

        service._driver = mock_driver

        health = await service.health_check()

        assert health["service"] == "Neo4jStorageService"
        assert health["connected"] is True

    @pytest.mark.asyncio
    async def test_health_check_disconnected(self, service):
        """연결 실패 상태의 health check"""
        mock_driver, _ = _make_mock_driver()
        mock_driver.verify_connectivity = AsyncMock(side_effect=Exception("Refused"))
        service._driver = mock_driver

        health = await service.health_check()

        assert health["connected"] is False


# ---------------------------------------------------------------------------
# Tests: Singleton factory
# ---------------------------------------------------------------------------


class TestSingletonFactory:
    """싱글톤 팩토리 테스트"""

    def test_get_service_creates_instance(self, mock_settings):
        """첫 호출 시 인스턴스 생성"""
        svc = get_neo4j_storage_service()
        assert isinstance(svc, Neo4jStorageService)

    def test_get_service_returns_same_instance(self, mock_settings):
        """이후 호출 시 동일 인스턴스 반환"""
        svc1 = get_neo4j_storage_service()
        svc2 = get_neo4j_storage_service()
        assert svc1 is svc2

    def test_reset_clears_instance(self, mock_settings):
        """리셋 후 새 인스턴스 생성"""
        svc1 = get_neo4j_storage_service()
        reset_neo4j_storage_service()
        svc2 = get_neo4j_storage_service()
        assert svc1 is not svc2


# ---------------------------------------------------------------------------
# Tests: _node_to_dict utility
# ---------------------------------------------------------------------------


class TestNodeToDict:
    """노드 변환 유틸리티 테스트"""

    def test_node_to_dict_with_dict(self):
        """딕셔너리 변환 가능한 노드"""
        node = {"name": "Python", "type": "Technology"}
        result = Neo4jStorageService._node_to_dict(node)
        assert result == {"name": "Python", "type": "Technology"}

    def test_node_to_dict_with_none(self):
        """None 노드"""
        result = Neo4jStorageService._node_to_dict(None)
        assert result == {}

    def test_node_to_dict_with_non_iterable(self):
        """변환 불가능한 노드"""
        result = Neo4jStorageService._node_to_dict(42)
        assert "_raw" in result


# ---------------------------------------------------------------------------
# EntityLabelStrategy 전략 패턴 테스트 (SCRUM-64 TECH-DEBT-001)
# ---------------------------------------------------------------------------


class TestEntityLabelStrategy:
    """EntityLabelStrategy 전략 패턴 테스트

    if/elif/else 체인을 딕셔너리 매핑으로 리팩토링한 결과 검증
    """

    def test_strategy_exists_for_all_labels(self):
        """모든 주요 라벨에 전략이 정의되어 있는지 확인"""
        assert "Person" in _LABEL_STRATEGIES
        assert "Technology" in _LABEL_STRATEGIES
        assert "Topic" in _LABEL_STRATEGIES
        assert "Keyword" in _LABEL_STRATEGIES

    def test_person_strategy_config(self):
        """Person 전략 설정 검증"""
        strategy = _get_label_strategy("Person")
        assert strategy.merge_key == "name"
        assert strategy.include_entity_type is True
        assert strategy.include_slug is False

    def test_technology_strategy_config(self):
        """Technology 전략 설정 검증"""
        strategy = _get_label_strategy("Technology")
        assert strategy.merge_key == "name"
        assert strategy.include_entity_type is False
        assert strategy.include_slug is False

    def test_topic_strategy_config(self):
        """Topic 전략 설정 검증"""
        strategy = _get_label_strategy("Topic")
        assert strategy.merge_key == "name"
        assert strategy.include_entity_type is False
        assert strategy.include_slug is True

    def test_keyword_strategy_config(self):
        """Keyword 전략 설정 검증"""
        strategy = _get_label_strategy("Keyword")
        assert strategy.merge_key == "value"
        assert strategy.include_entity_type is True
        assert strategy.include_slug is False

    def test_unknown_label_returns_default_strategy(self):
        """알 수 없는 라벨은 기본 전략 반환"""
        strategy = _get_label_strategy("UnknownLabel")
        assert strategy == _DEFAULT_STRATEGY
        assert strategy.merge_key == "value"
        assert strategy.include_entity_type is True

    def test_build_entity_data_person(self):
        """Person 엔티티 데이터 생성 검증"""
        strategy = _get_label_strategy("Person")
        entity = Entity(
            id="e1",
            name="홍길동",
            type="Person",
            description="테스트 개발자",
        )
        data = strategy.build_entity_data(entity)

        assert data["merge_val"] == "홍길동"
        assert data["description"] == "테스트 개발자"
        assert data["original_id"] == "e1"
        assert data["entity_type"] == "Person"  # include_entity_type=True
        assert "slug" not in data  # include_slug=False

    def test_build_entity_data_topic(self):
        """Topic 엔티티 데이터 생성 검증 (slug 포함)"""
        strategy = _get_label_strategy("Topic")
        entity = Entity(
            id="e2",
            name="Machine Learning",
            type="Concept",
            description="AI 기술",
        )
        data = strategy.build_entity_data(entity)

        assert data["merge_val"] == "Machine Learning"
        assert data["slug"] == "machine-learning"  # include_slug=True
        assert "entity_type" not in data  # include_entity_type=False

    def test_build_entity_data_technology(self):
        """Technology 엔티티 데이터 생성 검증"""
        strategy = _get_label_strategy("Technology")
        entity = Entity(
            id="e3",
            name="Python",
            type="Technology",
            description="프로그래밍 언어",
        )
        data = strategy.build_entity_data(entity)

        assert data["merge_val"] == "Python"
        assert data["description"] == "프로그래밍 언어"
        assert "entity_type" not in data  # include_entity_type=False
        assert "slug" not in data  # include_slug=False

    def test_build_cypher_person(self):
        """Person Cypher 쿼리 생성 검증"""
        strategy = _get_label_strategy("Person")
        cypher = strategy.build_cypher("Person")

        assert "MERGE (n:Person {name: ent.merge_val})" in cypher
        assert "n.entity_type = ent.entity_type" in cypher
        assert "n.description = ent.description" in cypher
        assert "n.original_id = ent.original_id" in cypher
        assert "n.updated_at = $now" in cypher

    def test_build_cypher_topic(self):
        """Topic Cypher 쿼리 생성 검증 (slug 포함)"""
        strategy = _get_label_strategy("Topic")
        cypher = strategy.build_cypher("Topic")

        assert "MERGE (n:Topic {name: ent.merge_val})" in cypher
        assert "n.slug = ent.slug" in cypher
        assert "entity_type" not in cypher  # include_entity_type=False

    def test_build_cypher_keyword(self):
        """Keyword Cypher 쿼리 생성 검증 (value 필드)"""
        strategy = _get_label_strategy("Keyword")
        cypher = strategy.build_cypher("Keyword")

        assert "MERGE (n:Keyword {value: ent.merge_val})" in cypher
        assert "n.entity_type = ent.entity_type" in cypher

    def test_default_strategy_for_new_label(self):
        """새 라벨 추가 시 기본 전략으로 폴백"""
        # 새로운 라벨 타입이 추가되더라도 기본 전략으로 동작
        strategy = _get_label_strategy("NewCustomLabel")
        assert strategy.merge_key == "value"

        cypher = strategy.build_cypher("NewCustomLabel")
        assert "MERGE (n:NewCustomLabel {value: ent.merge_val})" in cypher

    def test_entity_data_with_none_description(self):
        """description이 None인 경우 빈 문자열로 처리"""
        strategy = _get_label_strategy("Technology")
        entity = Entity(
            id="e4",
            name="Go",
            type="Technology",
            description=None,
        )
        data = strategy.build_entity_data(entity)

        assert data["description"] == ""
