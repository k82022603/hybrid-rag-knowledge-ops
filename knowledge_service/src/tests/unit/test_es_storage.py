"""ElasticsearchStorageService 단위 테스트

STORY-006: Neo4j/Elasticsearch 저장 서비스 - Elasticsearch 단위 테스트

테스트 범위:
    - 서비스 초기화 및 설정
    - 인덱스 생성 (create_index)
    - 인덱스 삭제 (delete_index)
    - 청크 벌크 인덱싱 (index_chunks)
    - 단일 청크 인덱싱 (index_single)
    - 벡터 유사도 검색 (search_vectors)
    - 키워드 검색 (search_keyword)
    - 문서 삭제 (delete_by_document_id)
    - 연결 검증 (verify_connectivity)
    - 싱글톤 팩토리
    - 에러 핸들링
    - StorageTransaction 통합
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# importlib로 직접 모듈 로드
import importlib.util

_es_spec = importlib.util.spec_from_file_location(
    "app.storage.es_storage",
    os.path.join(
        os.path.dirname(__file__), "..", "..", "app", "storage", "es_storage.py"
    ),
)
_es_module = importlib.util.module_from_spec(_es_spec)
sys.modules["app.storage.es_storage"] = _es_module
_es_spec.loader.exec_module(_es_module)

ElasticsearchStorageService = _es_module.ElasticsearchStorageService
get_es_storage_service = _es_module.get_es_storage_service
reset_es_storage_service = _es_module.reset_es_storage_service
DEFAULT_INDEX_SETTINGS = _es_module.DEFAULT_INDEX_SETTINGS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_singleton():
    """각 테스트 전후로 싱글톤 리셋"""
    reset_es_storage_service()
    yield
    reset_es_storage_service()


@pytest.fixture
def mock_settings():
    """설정 모킹"""
    mock_s = MagicMock()
    mock_s.elasticsearch_url = "http://localhost:9200"
    mock_s.elasticsearch_host = "localhost"
    mock_s.elasticsearch_port = 9200
    mock_s.elasticsearch_user = None
    mock_s.elasticsearch_password = None
    mock_s.elasticsearch_index = "knowledge_chunks"
    original_settings = _es_module.settings
    _es_module.settings = mock_s
    yield mock_s
    _es_module.settings = original_settings


@pytest.fixture
def service(mock_settings):
    """ElasticsearchStorageService 인스턴스"""
    return ElasticsearchStorageService(
        hosts=["http://localhost:9200"],
        index_name="test_knowledge_chunks",
    )


@pytest.fixture
def sample_chunks():
    """테스트용 청크 리스트"""
    return [
        {
            "chunk_id": "chunk-001",
            "document_id": "doc-001",
            "content": "Python은 범용 프로그래밍 언어입니다.",
            "dense_vector": [0.1] * 1024,
            "chunk_index": 0,
            "token_count": 10,
            "heading": "프로그래밍 언어",
            "metadata": {
                "document_type": "기술문서",
                "project_name": "RAG",
                "title": "Python 가이드",
            },
        },
        {
            "chunk_id": "chunk-002",
            "document_id": "doc-001",
            "content": "Neo4j는 그래프 데이터베이스입니다.",
            "dense_vector": [0.2] * 1024,
            "chunk_index": 1,
            "token_count": 12,
            "heading": "데이터베이스",
            "metadata": {
                "document_type": "기술문서",
                "project_name": "RAG",
                "title": "Neo4j 가이드",
            },
        },
        {
            "chunk_id": "chunk-003",
            "document_id": "doc-001",
            "content": "Elasticsearch는 검색 엔진입니다.",
            "dense_vector": [0.3] * 1024,
            "chunk_index": 2,
            "token_count": 11,
            "metadata": {},
        },
    ]


def _make_mock_client():
    """Mock Elasticsearch 클라이언트 생성"""
    mock_client = AsyncMock()

    # indices
    mock_client.indices = AsyncMock()
    mock_client.indices.exists = AsyncMock(return_value=False)
    mock_client.indices.create = AsyncMock()
    mock_client.indices.delete = AsyncMock()
    mock_client.indices.stats = AsyncMock(return_value={
        "_all": {
            "primaries": {
                "docs": {"count": 100},
                "store": {"size_in_bytes": 1024000},
            },
        },
    })

    # search
    mock_client.search = AsyncMock(return_value={
        "hits": {
            "total": {"value": 2},
            "hits": [
                {
                    "_id": "chunk-001",
                    "_score": 0.95,
                    "_source": {
                        "chunk_id": "chunk-001",
                        "document_id": "doc-001",
                        "text": "Python은 범용 프로그래밍 언어입니다.",
                        "chunk_index": 0,
                        "heading": "프로그래밍 언어",
                        "token_count": 10,
                        "metadata": {"title": "Python 가이드"},
                    },
                },
                {
                    "_id": "chunk-002",
                    "_score": 0.80,
                    "_source": {
                        "chunk_id": "chunk-002",
                        "document_id": "doc-001",
                        "text": "Neo4j는 그래프 데이터베이스입니다.",
                        "chunk_index": 1,
                        "heading": "데이터베이스",
                        "token_count": 12,
                        "metadata": {"title": "Neo4j 가이드"},
                    },
                    "highlight": {
                        "text": ["<em>Neo4j</em>는 그래프 데이터베이스입니다."],
                    },
                },
            ],
        },
    })

    # count
    mock_client.count = AsyncMock(return_value={"count": 100})

    # delete
    mock_client.delete = AsyncMock()
    mock_client.delete_by_query = AsyncMock(return_value={"deleted": 3})

    # info
    mock_client.info = AsyncMock(return_value={
        "version": {"number": "8.11.0"},
    })

    # close
    mock_client.close = AsyncMock()

    return mock_client


# ---------------------------------------------------------------------------
# Tests: Initialization
# ---------------------------------------------------------------------------


class TestElasticsearchStorageServiceInit:
    """초기화 테스트"""

    def test_init_with_defaults(self, mock_settings):
        """기본 설정으로 초기화"""
        svc = ElasticsearchStorageService()
        assert svc._hosts == ["http://localhost:9200"]
        assert svc._index_name == "knowledge_chunks"
        assert svc._client is None

    def test_init_with_custom_params(self, mock_settings):
        """커스텀 파라미터로 초기화"""
        svc = ElasticsearchStorageService(
            hosts=["http://custom:9200"],
            index_name="custom_index",
        )
        assert svc._hosts == ["http://custom:9200"]
        assert svc._index_name == "custom_index"

    def test_init_with_auth(self, mock_settings):
        """인증 정보 포함 초기화"""
        svc = ElasticsearchStorageService(
            hosts=["http://localhost:9200"],
            basic_auth=("elastic", "password"),
        )
        assert svc._basic_auth == ("elastic", "password")

    def test_client_not_created_on_init(self, service):
        """초기화 시 클라이언트가 생성되지 않음 (lazy)"""
        assert service._client is None


# ---------------------------------------------------------------------------
# Tests: create_index
# ---------------------------------------------------------------------------


class TestCreateIndex:
    """인덱스 생성 테스트"""

    @pytest.mark.asyncio
    async def test_create_index_new(self, service):
        """새 인덱스 생성"""
        mock_client = _make_mock_client()
        mock_client.indices.exists = AsyncMock(return_value=False)
        service._client = mock_client

        result = await service.create_index()

        assert result is True
        mock_client.indices.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_index_already_exists(self, service):
        """이미 존재하는 인덱스"""
        mock_client = _make_mock_client()
        mock_client.indices.exists = AsyncMock(return_value=True)
        service._client = mock_client

        result = await service.create_index()

        assert result is True
        mock_client.indices.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_index_custom_name(self, service):
        """커스텀 인덱스 이름으로 생성"""
        mock_client = _make_mock_client()
        service._client = mock_client

        await service.create_index(index_name="custom_index")

        mock_client.indices.exists.assert_called_with(index="custom_index")

    @pytest.mark.asyncio
    async def test_create_index_with_settings_override(self, service):
        """커스텀 설정으로 인덱스 생성"""
        mock_client = _make_mock_client()
        service._client = mock_client

        custom_settings = {"settings": {"number_of_shards": 3}}
        await service.create_index(settings_override=custom_settings)

        _, kwargs = mock_client.indices.create.call_args
        assert kwargs["body"] == custom_settings


# ---------------------------------------------------------------------------
# Tests: delete_index
# ---------------------------------------------------------------------------


class TestDeleteIndex:
    """인덱스 삭제 테스트"""

    @pytest.mark.asyncio
    async def test_delete_index_exists(self, service):
        """존재하는 인덱스 삭제"""
        mock_client = _make_mock_client()
        mock_client.indices.exists = AsyncMock(return_value=True)
        service._client = mock_client

        result = await service.delete_index()

        assert result is True
        mock_client.indices.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_index_not_exists(self, service):
        """존재하지 않는 인덱스 삭제 시도"""
        mock_client = _make_mock_client()
        mock_client.indices.exists = AsyncMock(return_value=False)
        service._client = mock_client

        result = await service.delete_index()

        assert result is True
        mock_client.indices.delete.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: index_chunks
# ---------------------------------------------------------------------------


class TestIndexChunks:
    """청크 인덱싱 테스트"""

    @pytest.mark.asyncio
    async def test_index_chunks_empty(self, service):
        """빈 청크 리스트 인덱싱"""
        result = await service.index_chunks([])
        assert result["indexed"] == 0
        assert result["errors"] == 0

    @pytest.mark.asyncio
    async def test_index_chunks_success(self, service, sample_chunks):
        """청크 벌크 인덱싱 성공"""
        mock_client = _make_mock_client()
        mock_client.indices.exists = AsyncMock(return_value=True)
        service._client = mock_client

        # async_bulk 모킹
        with patch(
            "elasticsearch.helpers.async_bulk",
            new_callable=AsyncMock,
            return_value=(3, []),
        ) as mock_bulk:
            result = await service.index_chunks(sample_chunks)

            assert result["indexed"] == 3
            assert result["errors"] == 0
            assert result["latency_ms"] > 0

            # bulk에 전달된 actions 확인
            actions = mock_bulk.call_args[0][1]
            assert len(actions) == 3

            # 각 action의 구조 확인
            for action in actions:
                assert "_index" in action
                assert "_id" in action
                assert "_source" in action
                assert "dense_vector" in action["_source"]
                assert "text" in action["_source"]

    @pytest.mark.asyncio
    async def test_index_chunks_with_errors(self, service, sample_chunks):
        """일부 청크 인덱싱 실패"""
        mock_client = _make_mock_client()
        mock_client.indices.exists = AsyncMock(return_value=True)
        service._client = mock_client

        error_items = [{"index": {"_id": "chunk-003", "error": "mapping error"}}]

        with patch(
            "elasticsearch.helpers.async_bulk",
            new_callable=AsyncMock,
            return_value=(2, error_items),
        ):
            result = await service.index_chunks(sample_chunks)

            assert result["indexed"] == 2
            assert result["errors"] == 1

    @pytest.mark.asyncio
    async def test_index_chunks_auto_creates_index(self, service, sample_chunks):
        """인덱스가 없으면 자동 생성"""
        mock_client = _make_mock_client()
        mock_client.indices.exists = AsyncMock(return_value=False)
        service._client = mock_client

        with patch(
            "elasticsearch.helpers.async_bulk",
            new_callable=AsyncMock,
            return_value=(3, []),
        ):
            await service.index_chunks(sample_chunks)

            # 인덱스 생성 호출 확인
            mock_client.indices.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_index_chunks_custom_index(self, service, sample_chunks):
        """커스텀 인덱스에 인덱싱"""
        mock_client = _make_mock_client()
        mock_client.indices.exists = AsyncMock(return_value=True)
        service._client = mock_client

        with patch(
            "elasticsearch.helpers.async_bulk",
            new_callable=AsyncMock,
            return_value=(3, []),
        ) as mock_bulk:
            await service.index_chunks(sample_chunks, index_name="custom_idx")

            actions = mock_bulk.call_args[0][1]
            for action in actions:
                assert action["_index"] == "custom_idx"


# ---------------------------------------------------------------------------
# Tests: index_single
# ---------------------------------------------------------------------------


class TestIndexSingle:
    """단일 청크 인덱싱 테스트"""

    @pytest.mark.asyncio
    async def test_index_single_success(self, service, sample_chunks):
        """단일 청크 인덱싱 성공"""
        mock_client = _make_mock_client()
        mock_client.indices.exists = AsyncMock(return_value=True)
        service._client = mock_client

        with patch(
            "elasticsearch.helpers.async_bulk",
            new_callable=AsyncMock,
            return_value=(1, []),
        ):
            result = await service.index_single(sample_chunks[0])
            assert result is True


# ---------------------------------------------------------------------------
# Tests: search_vectors
# ---------------------------------------------------------------------------


class TestSearchVectors:
    """벡터 유사도 검색 테스트"""

    @pytest.mark.asyncio
    async def test_search_vectors_success(self, service):
        """벡터 검색 성공"""
        mock_client = _make_mock_client()
        service._client = mock_client

        query_vector = [0.1] * 1024
        results = await service.search_vectors(query_vector, top_k=5)

        assert len(results) == 2
        assert results[0]["chunk_id"] == "chunk-001"
        assert results[0]["score"] == 0.95
        assert results[0]["text"] == "Python은 범용 프로그래밍 언어입니다."
        assert results[0]["document_id"] == "doc-001"

        # kNN 쿼리 구조 확인
        call_kwargs = mock_client.search.call_args[1]
        body = call_kwargs["body"]
        assert "knn" in body
        assert body["knn"]["field"] == "dense_vector"
        assert body["knn"]["k"] == 5

    @pytest.mark.asyncio
    async def test_search_vectors_with_filters(self, service):
        """필터 적용 벡터 검색"""
        mock_client = _make_mock_client()
        service._client = mock_client

        query_vector = [0.1] * 1024
        filters = {"term": {"metadata.project_name": "RAG"}}

        await service.search_vectors(query_vector, filters=filters)

        call_kwargs = mock_client.search.call_args[1]
        body = call_kwargs["body"]
        assert "filter" in body["knn"]

    @pytest.mark.asyncio
    async def test_search_vectors_excludes_dense_vector(self, service):
        """검색 결과에서 dense_vector 필드 제외"""
        mock_client = _make_mock_client()
        service._client = mock_client

        await service.search_vectors([0.1] * 1024)

        call_kwargs = mock_client.search.call_args[1]
        body = call_kwargs["body"]
        assert "dense_vector" in body["_source"]["excludes"]


# ---------------------------------------------------------------------------
# Tests: search_keyword
# ---------------------------------------------------------------------------


class TestSearchKeyword:
    """키워드 검색 테스트"""

    @pytest.mark.asyncio
    async def test_search_keyword_success(self, service):
        """키워드 검색 성공"""
        mock_client = _make_mock_client()
        service._client = mock_client

        results = await service.search_keyword("Python 프로그래밍", top_k=5)

        assert len(results) == 2
        assert results[0]["score"] == 0.95

        # multi_match 쿼리 확인
        call_kwargs = mock_client.search.call_args[1]
        body = call_kwargs["body"]
        assert "query" in body
        assert "bool" in body["query"]
        assert "must" in body["query"]["bool"]

    @pytest.mark.asyncio
    async def test_search_keyword_with_highlight(self, service):
        """하이라이트 포함 키워드 검색"""
        mock_client = _make_mock_client()
        service._client = mock_client

        results = await service.search_keyword("Neo4j")

        # 두 번째 결과에 하이라이트가 있어야 함
        assert "highlight" in results[1]
        assert "text" in results[1]["highlight"]

    @pytest.mark.asyncio
    async def test_search_keyword_with_filters(self, service):
        """필터 적용 키워드 검색"""
        mock_client = _make_mock_client()
        service._client = mock_client

        filters = {"term": {"metadata.document_type": "기술문서"}}
        await service.search_keyword("Python", filters=filters)

        call_kwargs = mock_client.search.call_args[1]
        body = call_kwargs["body"]
        assert "filter" in body["query"]["bool"]


# ---------------------------------------------------------------------------
# Tests: delete_by_document_id
# ---------------------------------------------------------------------------


class TestDeleteByDocumentId:
    """문서 ID 기반 삭제 테스트"""

    @pytest.mark.asyncio
    async def test_delete_by_document_id(self, service):
        """문서 ID로 청크 삭제"""
        mock_client = _make_mock_client()
        service._client = mock_client

        deleted = await service.delete_by_document_id("doc-001")

        assert deleted == 3
        mock_client.delete_by_query.assert_called_once()

        # 쿼리 확인
        call_kwargs = mock_client.delete_by_query.call_args[1]
        assert call_kwargs["body"]["query"]["term"]["document_id"] == "doc-001"

    @pytest.mark.asyncio
    async def test_delete_by_chunk_id(self, service):
        """청크 ID로 단일 삭제"""
        mock_client = _make_mock_client()
        service._client = mock_client

        result = await service.delete_by_chunk_id("chunk-001")
        assert result is True
        mock_client.delete.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: verify_connectivity
# ---------------------------------------------------------------------------


class TestESVerifyConnectivity:
    """ES 연결 검증 테스트"""

    @pytest.mark.asyncio
    async def test_verify_connectivity_success(self, service):
        """연결 성공"""
        mock_client = _make_mock_client()
        service._client = mock_client

        result = await service.verify_connectivity()
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_connectivity_failure(self, service):
        """연결 실패"""
        mock_client = _make_mock_client()
        mock_client.info = AsyncMock(side_effect=Exception("Connection refused"))
        service._client = mock_client

        result = await service.verify_connectivity()
        assert result is False


# ---------------------------------------------------------------------------
# Tests: close
# ---------------------------------------------------------------------------


class TestESClose:
    """ES 연결 종료 테스트"""

    @pytest.mark.asyncio
    async def test_close_with_client(self, service):
        """클라이언트가 있을 때 종료"""
        mock_client = _make_mock_client()
        service._client = mock_client

        await service.close()

        mock_client.close.assert_called_once()
        assert service._client is None

    @pytest.mark.asyncio
    async def test_close_without_client(self, service):
        """클라이언트가 없을 때 종료 (무시)"""
        await service.close()
        assert service._client is None


# ---------------------------------------------------------------------------
# Tests: health_check
# ---------------------------------------------------------------------------


class TestESHealthCheck:
    """ES 상태 점검 테스트"""

    @pytest.mark.asyncio
    async def test_health_check_connected(self, service):
        """연결된 상태의 health check"""
        mock_client = _make_mock_client()
        mock_client.indices.exists = AsyncMock(return_value=True)
        service._client = mock_client

        health = await service.health_check()

        assert health["service"] == "ElasticsearchStorageService"
        assert health["connected"] is True
        assert health["index_exists"] is True
        assert health["doc_count"] == 100

    @pytest.mark.asyncio
    async def test_health_check_disconnected(self, service):
        """연결 실패 상태의 health check"""
        mock_client = _make_mock_client()
        mock_client.info = AsyncMock(side_effect=Exception("Refused"))
        service._client = mock_client

        health = await service.health_check()

        assert health["connected"] is False


# ---------------------------------------------------------------------------
# Tests: get_document_count
# ---------------------------------------------------------------------------


class TestGetDocumentCount:
    """문서 수 조회 테스트"""

    @pytest.mark.asyncio
    async def test_get_document_count(self, service):
        """문서 수 조회"""
        mock_client = _make_mock_client()
        service._client = mock_client

        count = await service.get_document_count()
        assert count == 100

    @pytest.mark.asyncio
    async def test_get_document_count_error(self, service):
        """문서 수 조회 실패 시 0 반환"""
        mock_client = _make_mock_client()
        mock_client.count = AsyncMock(side_effect=Exception("Error"))
        service._client = mock_client

        count = await service.get_document_count()
        assert count == 0


# ---------------------------------------------------------------------------
# Tests: Singleton factory
# ---------------------------------------------------------------------------


class TestESSingletonFactory:
    """ES 싱글톤 팩토리 테스트"""

    def test_get_service_creates_instance(self, mock_settings):
        """첫 호출 시 인스턴스 생성"""
        svc = get_es_storage_service()
        assert isinstance(svc, ElasticsearchStorageService)

    def test_get_service_returns_same_instance(self, mock_settings):
        """이후 호출 시 동일 인스턴스 반환"""
        svc1 = get_es_storage_service()
        svc2 = get_es_storage_service()
        assert svc1 is svc2

    def test_reset_clears_instance(self, mock_settings):
        """리셋 후 새 인스턴스 생성"""
        svc1 = get_es_storage_service()
        reset_es_storage_service()
        svc2 = get_es_storage_service()
        assert svc1 is not svc2


# ---------------------------------------------------------------------------
# Tests: DEFAULT_INDEX_SETTINGS
# ---------------------------------------------------------------------------


class TestDefaultIndexSettings:
    """기본 인덱스 설정 테스트"""

    def test_has_settings(self):
        """settings 키 존재"""
        assert "settings" in DEFAULT_INDEX_SETTINGS

    def test_has_mappings(self):
        """mappings 키 존재"""
        assert "mappings" in DEFAULT_INDEX_SETTINGS

    def test_dense_vector_config(self):
        """dense_vector 필드 설정 확인"""
        props = DEFAULT_INDEX_SETTINGS["mappings"]["properties"]
        dv = props["dense_vector"]
        assert dv["type"] == "dense_vector"
        assert dv["dims"] == 1024
        assert dv["similarity"] == "cosine"
        assert dv["index"] is True

    def test_text_analyzer(self):
        """text 필드 분석기 설정 확인"""
        props = DEFAULT_INDEX_SETTINGS["mappings"]["properties"]
        assert props["text"]["analyzer"] == "korean_analyzer"

    def test_metadata_properties(self):
        """metadata 하위 필드 존재 확인"""
        meta = DEFAULT_INDEX_SETTINGS["mappings"]["properties"]["metadata"]
        assert "properties" in meta
        assert "document_type" in meta["properties"]
        assert "project_name" in meta["properties"]
        assert "title" in meta["properties"]

    def test_knn_enabled(self):
        """kNN 인덱스 활성화 확인"""
        assert DEFAULT_INDEX_SETTINGS["settings"]["index.knn"] is True


# ---------------------------------------------------------------------------
# Tests: _parse_hits utility
# ---------------------------------------------------------------------------


class TestParseHits:
    """검색 결과 파싱 테스트"""

    def test_parse_hits_basic(self):
        """기본 hits 파싱"""
        response = {
            "hits": {
                "hits": [
                    {
                        "_id": "c1",
                        "_score": 0.9,
                        "_source": {
                            "document_id": "d1",
                            "text": "내용",
                            "chunk_index": 0,
                            "heading": "제목",
                            "token_count": 5,
                            "metadata": {"key": "val"},
                        },
                    },
                ],
            },
        }

        results = ElasticsearchStorageService._parse_hits(response)

        assert len(results) == 1
        assert results[0]["chunk_id"] == "c1"
        assert results[0]["score"] == 0.9
        assert results[0]["text"] == "내용"
        assert results[0]["metadata"] == {"key": "val"}

    def test_parse_hits_with_highlight(self):
        """하이라이트 포함 파싱"""
        response = {
            "hits": {
                "hits": [
                    {
                        "_id": "c1",
                        "_score": 0.8,
                        "_source": {
                            "document_id": "d1",
                            "text": "원본 텍스트",
                            "metadata": {},
                        },
                        "highlight": {
                            "text": ["<em>원본</em> 텍스트"],
                        },
                    },
                ],
            },
        }

        results = ElasticsearchStorageService._parse_hits(response)
        assert "highlight" in results[0]

    def test_parse_hits_empty(self):
        """빈 결과 파싱"""
        response = {"hits": {"hits": []}}
        results = ElasticsearchStorageService._parse_hits(response)
        assert results == []

    def test_parse_hits_missing_fields(self):
        """필드 누락 시 기본값 처리"""
        response = {
            "hits": {
                "hits": [
                    {
                        "_id": "c1",
                        "_source": {},
                    },
                ],
            },
        }

        results = ElasticsearchStorageService._parse_hits(response)
        assert results[0]["text"] == ""
        assert results[0]["document_id"] == ""
        assert results[0]["score"] == 0.0
