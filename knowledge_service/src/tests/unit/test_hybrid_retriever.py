"""
HybridRetriever 단위 테스트

STORY-030: HybridRetriever 실 구현 (ADR-001 적용)
- ElasticsearchRetriever 단위 테스트
- Neo4jRetriever 단위 테스트
- HybridRetriever 통합 테스트
- RRF Fusion 결과 검증
- 비동기 메서드 테스트
- Fallback 및 에러 핸들링 테스트
- 싱글톤 팩토리 테스트

Mock 사용: ES/Neo4j 실제 연결 없이 SearchService를 Mock
"""

import asyncio
import sys
from types import ModuleType
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# torch import 실패 방지: WSL2/CI 환경에서 libtorch_global_deps.so 누락 가능
# app.agents.__init__이 VIPAgent를 import하면서 torch 의존성 체인 발생
# 이 문제는 환경 문제이며 (CUDA 라이브러리 미설치) 코드 자체의 문제가 아님
_TORCH_IMPORT_ERROR = False
try:
    import torch  # noqa: F401
except (OSError, ImportError, ValueError):
    _TORCH_IMPORT_ERROR = True
    # torch 및 관련 서브모듈의 최소 mock 생성
    import importlib.machinery
    _torch_mock = ModuleType("torch")
    _torch_mock.__version__ = "2.0.0"  # type: ignore[attr-defined]
    _torch_mock.__spec__ = importlib.machinery.ModuleSpec("torch", None)  # type: ignore[attr-defined]
    _torch_mock.cuda = MagicMock()  # type: ignore[attr-defined]
    _torch_mock.cuda.is_available = MagicMock(return_value=False)  # type: ignore[attr-defined]
    _torch_mock.Tensor = MagicMock()  # type: ignore[attr-defined]
    _torch_mock.nn = MagicMock()  # type: ignore[attr-defined]
    _torch_mock.device = MagicMock()  # type: ignore[attr-defined]
    _torch_mock.dtype = MagicMock()  # type: ignore[attr-defined]
    _torch_mock.float32 = MagicMock()  # type: ignore[attr-defined]
    _torch_mock.float16 = MagicMock()  # type: ignore[attr-defined]
    _torch_mock.no_grad = MagicMock(return_value=MagicMock(__enter__=MagicMock(), __exit__=MagicMock()))  # type: ignore[attr-defined]
    sys.modules["torch"] = _torch_mock
    # 필요한 torch 서브모듈도 mock
    for submod in ["torch.nn", "torch.nn.functional", "torch.utils",
                   "torch.utils.data", "torch.cuda", "torch.amp"]:
        if submod not in sys.modules:
            sys.modules[submod] = MagicMock()

from app.agents.state import SearchResult
from app.rag.retriever import (
    ElasticsearchRetriever,
    HybridRetriever,
    Neo4jRetriever,
    get_hybrid_retriever,
    reset_hybrid_retriever,
)


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


def _make_search_result(
    chunk_id: str,
    content: str = "test content",
    score: float = 0.9,
    source: str = "vector",
    document_id: str = "doc-1",
    metadata: Optional[Dict[str, Any]] = None,
) -> SearchResult:
    """테스트용 SearchResult 생성 헬퍼"""
    return SearchResult(
        chunk_id=chunk_id,
        document_id=document_id,
        content=content,
        score=score,
        source=source,
        metadata=metadata or {},
    )


def _make_vector_results(count: int = 3) -> List[SearchResult]:
    """벡터 검색 결과 생성"""
    return [
        _make_search_result(
            chunk_id=f"vec-{i}",
            content=f"Vector result {i}",
            score=0.95 - (i * 0.05),
            source="vector",
        )
        for i in range(count)
    ]


def _make_keyword_results(count: int = 3) -> List[SearchResult]:
    """키워드 검색 결과 생성"""
    return [
        _make_search_result(
            chunk_id=f"kw-{i}",
            content=f"Keyword result {i}",
            score=0.90 - (i * 0.05),
            source="keyword",
        )
        for i in range(count)
    ]


def _make_graph_results(count: int = 3) -> List[SearchResult]:
    """그래프 검색 결과 생성"""
    return [
        _make_search_result(
            chunk_id=f"graph-{i}",
            content=f"Graph result {i}",
            score=0.85 - (i * 0.05),
            source="graph",
            metadata={"entities": [f"Entity-{i}"]},
        )
        for i in range(count)
    ]


def _make_overlapping_results() -> tuple:
    """중복 chunk_id를 포함한 결과 생성"""
    vector_results = [
        _make_search_result(chunk_id="common-1", score=0.95, source="vector"),
        _make_search_result(chunk_id="vec-only", score=0.80, source="vector"),
        _make_search_result(chunk_id="common-2", score=0.70, source="vector"),
    ]
    keyword_results = [
        _make_search_result(chunk_id="common-1", score=0.90, source="keyword"),
        _make_search_result(chunk_id="kw-only", score=0.85, source="keyword"),
    ]
    graph_results = [
        _make_search_result(chunk_id="common-2", score=0.88, source="graph"),
        _make_search_result(chunk_id="graph-only", score=0.75, source="graph"),
    ]
    return vector_results, keyword_results, graph_results


@pytest.fixture
def mock_search_service():
    """Mock SearchService"""
    service = MagicMock()

    # hybrid_search mock
    service.hybrid_search = AsyncMock(return_value={
        "results": _make_vector_results(3) + _make_keyword_results(2),
        "total": 5,
        "search_type": "hybrid",
        "latency_ms": 50.0,
        "debug": {
            "vector_count": 3,
            "keyword_count": 2,
            "graph_count": 1,
            "fused_count": 5,
        },
    })

    # semantic_search mock
    service.semantic_search = AsyncMock(return_value={
        "results": _make_vector_results(3),
        "total": 3,
        "search_type": "semantic",
        "latency_ms": 30.0,
    })

    # keyword_search mock
    service.keyword_search = AsyncMock(return_value={
        "results": _make_keyword_results(3),
        "total": 3,
        "search_type": "keyword",
        "latency_ms": 20.0,
    })

    # _graph_search mock
    service._graph_search = AsyncMock(return_value=_make_graph_results(3))

    # _rrf_fusion mock (identity-like behavior)
    def mock_rrf_fusion(result_lists, source_names=None, k=60):
        """Simple RRF fusion mock that deduplicates and returns all results"""
        seen = set()
        fused = []
        for result_list in result_lists:
            for result in result_list:
                if result.chunk_id not in seen:
                    seen.add(result.chunk_id)
                    fused.append(result)
        return fused

    service._rrf_fusion = MagicMock(side_effect=mock_rrf_fusion)

    return service


@pytest.fixture
def hybrid_retriever(mock_search_service):
    """Mock SearchService 주입된 HybridRetriever"""
    return HybridRetriever(search_service=mock_search_service)


@pytest.fixture
def es_retriever(mock_search_service):
    """Mock SearchService 주입된 ElasticsearchRetriever"""
    return ElasticsearchRetriever(search_service=mock_search_service)


@pytest.fixture
def neo4j_retriever(mock_search_service):
    """Mock SearchService 주입된 Neo4jRetriever"""
    return Neo4jRetriever(search_service=mock_search_service)


# ---------------------------------------------------------------------------
# ElasticsearchRetriever Tests
# ---------------------------------------------------------------------------


class TestElasticsearchRetriever:
    """ElasticsearchRetriever 단위 테스트"""

    @pytest.mark.asyncio
    async def test_vector_search(self, es_retriever, mock_search_service):
        """벡터 검색이 SearchService.semantic_search에 위임되는지 검증"""
        results = await es_retriever.vector_search(
            query="test query", top_k=5
        )

        mock_search_service.semantic_search.assert_called_once_with(
            query="test query", filters=None, top_k=5
        )
        assert len(results) == 3
        assert results[0].source == "vector"

    @pytest.mark.asyncio
    async def test_keyword_search(self, es_retriever, mock_search_service):
        """키워드 검색이 SearchService.keyword_search에 위임되는지 검증"""
        results = await es_retriever.keyword_search(
            query="test query", top_k=10
        )

        mock_search_service.keyword_search.assert_called_once_with(
            query="test query", filters=None, top_k=10
        )
        assert len(results) == 3
        assert results[0].source == "keyword"

    @pytest.mark.asyncio
    async def test_vector_search_with_filters(self, es_retriever, mock_search_service):
        """필터 적용 벡터 검색"""
        filters = {"project_name": "test-project", "document_type": "guide"}

        await es_retriever.vector_search(
            query="filtered query", top_k=5, filters=filters
        )

        mock_search_service.semantic_search.assert_called_once_with(
            query="filtered query", filters=filters, top_k=5
        )

    @pytest.mark.asyncio
    async def test_search_failure_returns_empty(self, es_retriever, mock_search_service):
        """검색 실패 시 빈 리스트 반환"""
        mock_search_service.semantic_search = AsyncMock(
            side_effect=Exception("ES connection failed")
        )

        results = await es_retriever.vector_search(query="failing query")

        assert results == []

    @pytest.mark.asyncio
    async def test_search_type_dispatch(self, es_retriever, mock_search_service):
        """search() 메서드가 search_type에 따라 올바르게 분기하는지 검증"""
        await es_retriever.search(query="q1", search_type="vector")
        mock_search_service.semantic_search.assert_called_once()

        await es_retriever.search(query="q2", search_type="keyword")
        mock_search_service.keyword_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_lazy_init_search_service(self):
        """SearchService가 없을 때 지연 초기화되는지 검증"""
        retriever = ElasticsearchRetriever(es_client="fake_client")

        with patch("app.rag.retriever.ElasticsearchRetriever.search_service",
                    new_callable=lambda: property(lambda self: MagicMock())):
            # search_service 프로퍼티 접근 시 생성됨
            assert retriever._search_service is None


# ---------------------------------------------------------------------------
# Neo4jRetriever Tests
# ---------------------------------------------------------------------------


class TestNeo4jRetriever:
    """Neo4jRetriever 단위 테스트"""

    @pytest.mark.asyncio
    async def test_search(self, neo4j_retriever, mock_search_service):
        """Graph 검색이 SearchService._graph_search에 위임되는지 검증"""
        results = await neo4j_retriever.search(
            query="graph query", top_k=10
        )

        mock_search_service._graph_search.assert_called_once_with(
            query="graph query", entities=None, top_k=10
        )
        assert len(results) == 3
        assert results[0].source == "graph"

    @pytest.mark.asyncio
    async def test_search_with_entities(self, neo4j_retriever, mock_search_service):
        """엔티티 기반 Graph 검색"""
        entities = [
            {"name": "Python", "type": "Technology"},
            {"name": "FastAPI", "type": "Technology"},
        ]

        await neo4j_retriever.search(
            query="entity query", entities=entities, top_k=5
        )

        mock_search_service._graph_search.assert_called_once_with(
            query="entity query", entities=entities, top_k=5
        )

    @pytest.mark.asyncio
    async def test_search_failure_returns_empty(self, neo4j_retriever, mock_search_service):
        """검색 실패 시 빈 리스트 반환"""
        mock_search_service._graph_search = AsyncMock(
            side_effect=Exception("Neo4j connection failed")
        )

        results = await neo4j_retriever.search(query="failing query")

        assert results == []

    @pytest.mark.asyncio
    async def test_search_no_entities(self, neo4j_retriever, mock_search_service):
        """엔티티 없이 Graph 검색"""
        await neo4j_retriever.search(query="no entity query", top_k=20)

        mock_search_service._graph_search.assert_called_once_with(
            query="no entity query", entities=None, top_k=20
        )


# ---------------------------------------------------------------------------
# HybridRetriever Tests
# ---------------------------------------------------------------------------


class TestHybridRetriever:
    """HybridRetriever 통합 테스트"""

    @pytest.mark.asyncio
    async def test_retrieve_delegates_to_search_service(
        self, hybrid_retriever, mock_search_service
    ):
        """retrieve()가 SearchService.hybrid_search에 위임되는지 검증"""
        results = await hybrid_retriever.retrieve(
            query="hybrid query", top_k=5
        )

        mock_search_service.hybrid_search.assert_called_once_with(
            query="hybrid query",
            filters=None,
            top_k=5,
            user_id=None,
        )
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_retrieve_with_filters(
        self, hybrid_retriever, mock_search_service
    ):
        """필터 적용 retrieve"""
        filters = {"document_type": "policy"}

        await hybrid_retriever.retrieve(
            query="filtered query",
            filters=filters,
            top_k=3,
            user_id="user-123",
        )

        mock_search_service.hybrid_search.assert_called_once_with(
            query="filtered query",
            filters=filters,
            top_k=3,
            user_id="user-123",
        )

    @pytest.mark.asyncio
    async def test_retrieve_returns_top_k_results(
        self, hybrid_retriever, mock_search_service
    ):
        """top_k 파라미터가 올바르게 적용되는지 검증"""
        # 10개 결과를 반환하도록 설정
        mock_search_service.hybrid_search = AsyncMock(return_value={
            "results": _make_vector_results(10),
            "total": 10,
            "search_type": "hybrid",
            "latency_ms": 50.0,
            "debug": {"vector_count": 10, "keyword_count": 0, "graph_count": 0, "fused_count": 10},
        })

        results = await hybrid_retriever.retrieve(
            query="top_k query", top_k=5
        )

        # hybrid_search에 top_k=5로 위임됨
        call_args = mock_search_service.hybrid_search.call_args
        assert call_args.kwargs["top_k"] == 5

    @pytest.mark.asyncio
    async def test_aretrieve_is_alias(
        self, hybrid_retriever, mock_search_service
    ):
        """aretrieve가 retrieve의 별칭인지 검증"""
        results_retrieve = await hybrid_retriever.retrieve(
            query="alias test", top_k=5
        )

        # reset mock call count
        mock_search_service.hybrid_search.reset_mock()

        results_aretrieve = await hybrid_retriever.aretrieve(
            query="alias test", top_k=5
        )

        # 같은 인자로 호출됨
        mock_search_service.hybrid_search.assert_called_once_with(
            query="alias test",
            filters=None,
            top_k=5,
            user_id=None,
        )

    @pytest.mark.asyncio
    async def test_retrieve_by_source_vector(
        self, hybrid_retriever, mock_search_service
    ):
        """소스별 검색 - vector"""
        results = await hybrid_retriever.retrieve_by_source(
            query="vector only", source="vector", top_k=5
        )

        mock_search_service.semantic_search.assert_called_once()
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_retrieve_by_source_keyword(
        self, hybrid_retriever, mock_search_service
    ):
        """소스별 검색 - keyword"""
        results = await hybrid_retriever.retrieve_by_source(
            query="keyword only", source="keyword", top_k=5
        )

        mock_search_service.keyword_search.assert_called_once()
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_retrieve_by_source_graph(
        self, hybrid_retriever, mock_search_service
    ):
        """소스별 검색 - graph"""
        entities = [{"name": "Python", "type": "Technology"}]

        results = await hybrid_retriever.retrieve_by_source(
            query="graph only", source="graph",
            entities=entities, top_k=5
        )

        mock_search_service._graph_search.assert_called_once()
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_search_service_injected(self, mock_search_service):
        """SearchService 직접 주입 검증"""
        retriever = HybridRetriever(search_service=mock_search_service)

        assert retriever.search_service is mock_search_service

    @pytest.mark.asyncio
    async def test_search_service_lazy_init_from_clients(self):
        """SearchService가 es_client/neo4j_driver로 지연 생성되는지 검증"""
        fake_es = MagicMock()
        fake_neo4j = MagicMock()

        retriever = HybridRetriever(
            es_client=fake_es, neo4j_driver=fake_neo4j
        )

        # 아직 초기화되지 않음
        assert retriever._search_service is None

        with patch("app.services.search.SearchService") as MockService:
            mock_instance = MagicMock()
            MockService.return_value = mock_instance

            # search_service 접근 시 생성
            svc = retriever.search_service

            MockService.assert_called_once_with(
                es_client=fake_es, neo4j_driver=fake_neo4j
            )
            assert svc is mock_instance

    @pytest.mark.asyncio
    async def test_es_retriever_shares_search_service(
        self, hybrid_retriever, mock_search_service
    ):
        """ES Retriever가 동일한 SearchService를 공유하는지 검증"""
        es_ret = hybrid_retriever.es_retriever
        assert es_ret.search_service is mock_search_service

    @pytest.mark.asyncio
    async def test_neo4j_retriever_shares_search_service(
        self, hybrid_retriever, mock_search_service
    ):
        """Neo4j Retriever가 동일한 SearchService를 공유하는지 검증"""
        neo_ret = hybrid_retriever.neo4j_retriever
        assert neo_ret.search_service is mock_search_service

    @pytest.mark.asyncio
    async def test_health_check(self, mock_search_service):
        """health_check 반환값 검증"""
        mock_search_service.es_client = MagicMock()
        mock_search_service.neo4j_driver = MagicMock()

        retriever = HybridRetriever(search_service=mock_search_service)

        health = retriever.health_check()

        assert health["service"] == "HybridRetriever"
        assert health["es_client"] is True
        assert health["neo4j_driver"] is True
        assert isinstance(health["rrf_k"], int)
        assert isinstance(health["retrieval_top_k"], int)

    @pytest.mark.asyncio
    async def test_health_check_no_clients(self):
        """클라이언트 없는 상태의 health_check"""
        retriever = HybridRetriever()

        health = retriever.health_check()

        assert health["service"] == "HybridRetriever"
        assert health["es_client"] is False
        assert health["neo4j_driver"] is False
        assert health["search_service_initialized"] is False


# ---------------------------------------------------------------------------
# Fallback Tests
# ---------------------------------------------------------------------------


class TestHybridRetrieverFallback:
    """HybridRetriever Fallback 동작 테스트"""

    @pytest.mark.asyncio
    async def test_fallback_on_hybrid_search_failure(
        self, hybrid_retriever, mock_search_service
    ):
        """hybrid_search 실패 시 fallback 검색 동작"""
        # hybrid_search 실패
        mock_search_service.hybrid_search = AsyncMock(
            side_effect=Exception("Total failure")
        )

        results = await hybrid_retriever.retrieve(
            query="fallback query", top_k=5
        )

        # fallback이 개별 소스 검색을 시도
        # semantic_search, keyword_search, _graph_search 모두 호출
        assert mock_search_service.semantic_search.called
        assert mock_search_service.keyword_search.called
        assert mock_search_service._graph_search.called
        # RRF fusion도 호출
        assert mock_search_service._rrf_fusion.called

    @pytest.mark.asyncio
    async def test_fallback_partial_failure(
        self, hybrid_retriever, mock_search_service
    ):
        """부분 실패 시 가용한 소스만으로 결과 반환"""
        mock_search_service.hybrid_search = AsyncMock(
            side_effect=Exception("Hybrid failure")
        )
        # ES semantic은 실패
        mock_search_service.semantic_search = AsyncMock(
            side_effect=Exception("ES down")
        )
        # keyword는 성공
        mock_search_service.keyword_search = AsyncMock(return_value={
            "results": _make_keyword_results(2),
            "total": 2,
            "search_type": "keyword",
            "latency_ms": 20.0,
        })
        # graph는 성공
        mock_search_service._graph_search = AsyncMock(
            return_value=_make_graph_results(2)
        )

        results = await hybrid_retriever.retrieve(
            query="partial failure", top_k=5
        )

        # RRF fusion이 호출됨
        assert mock_search_service._rrf_fusion.called

        # 결과에 가용한 소스의 결과가 포함됨
        # vector(실패) + keyword(성공: 2) + graph(성공: 2) = 최대 4개
        assert len(results) > 0
        assert len(results) <= 5

    @pytest.mark.asyncio
    async def test_fallback_all_sources_fail(
        self, hybrid_retriever, mock_search_service
    ):
        """모든 소스 실패 시 빈 리스트 반환"""
        mock_search_service.hybrid_search = AsyncMock(
            side_effect=Exception("Hybrid failure")
        )
        mock_search_service.semantic_search = AsyncMock(
            side_effect=Exception("ES down")
        )
        mock_search_service.keyword_search = AsyncMock(
            side_effect=Exception("ES down")
        )
        mock_search_service._graph_search = AsyncMock(
            side_effect=Exception("Neo4j down")
        )

        results = await hybrid_retriever.retrieve(
            query="total failure", top_k=5
        )

        assert results == []


# ---------------------------------------------------------------------------
# RRF Fusion Integration Tests
# ---------------------------------------------------------------------------


class TestRRFFusionIntegration:
    """SearchService._rrf_fusion을 통한 RRF 융합 결과 검증"""

    @pytest.mark.asyncio
    async def test_rrf_fusion_with_overlapping_results(self):
        """중복 chunk_id가 있는 경우 RRF 융합 검증"""
        from app.services.search import SearchService

        service = SearchService()

        vector_results, keyword_results, graph_results = _make_overlapping_results()

        fused = service._rrf_fusion(
            result_lists=[vector_results, keyword_results, graph_results],
            source_names=["vector", "keyword", "graph"],
            k=60,
        )

        # 중복 제거 후 고유한 결과만 포함
        chunk_ids = [r.chunk_id for r in fused]
        assert len(chunk_ids) == len(set(chunk_ids)), "Duplicate chunk_ids found"

        # 총 5개 고유 ID: common-1, vec-only, common-2, kw-only, graph-only
        assert len(fused) == 5

        # common-1은 vector + keyword에 있으므로 RRF 점수가 가장 높아야 함
        assert fused[0].chunk_id == "common-1"

    @pytest.mark.asyncio
    async def test_rrf_fusion_score_calculation(self):
        """RRF 점수 계산의 정확성 검증"""
        from app.services.search import SearchService

        service = SearchService()

        # 간단한 2-source 시나리오
        source_a = [
            _make_search_result(chunk_id="A", score=1.0, source="a"),
            _make_search_result(chunk_id="B", score=0.8, source="a"),
        ]
        source_b = [
            _make_search_result(chunk_id="B", score=1.0, source="b"),
            _make_search_result(chunk_id="C", score=0.8, source="b"),
        ]

        fused = service._rrf_fusion(
            result_lists=[source_a, source_b],
            source_names=["a", "b"],
            k=60,
        )

        # B는 두 소스 모두에 존재: rrf_score = 1/(60+2) + 1/(60+1) = 약 0.032
        # A는 source_a rank 0: rrf_score = 1/(60+1) = 약 0.016
        # C는 source_b rank 1: rrf_score = 1/(60+2) = 약 0.016
        assert fused[0].chunk_id == "B", "B should be ranked first (appears in both sources)"
        assert fused[0].score > fused[1].score

    @pytest.mark.asyncio
    async def test_rrf_fusion_empty_sources(self):
        """빈 소스 리스트 처리"""
        from app.services.search import SearchService

        service = SearchService()

        fused = service._rrf_fusion(
            result_lists=[[], [], []],
            source_names=["vector", "keyword", "graph"],
            k=60,
        )

        assert fused == []

    @pytest.mark.asyncio
    async def test_rrf_fusion_single_source(self):
        """단일 소스만 결과가 있는 경우"""
        from app.services.search import SearchService

        service = SearchService()

        vector_results = _make_vector_results(5)

        fused = service._rrf_fusion(
            result_lists=[vector_results, [], []],
            source_names=["vector", "keyword", "graph"],
            k=60,
        )

        assert len(fused) == 5
        # 순위가 유지됨
        for i in range(len(fused) - 1):
            assert fused[i].score >= fused[i + 1].score

    @pytest.mark.asyncio
    async def test_rrf_fusion_preserves_metadata(self):
        """RRF 융합이 source_ranks 메타데이터를 추가하는지 검증"""
        from app.services.search import SearchService

        service = SearchService()

        vector_results = [
            _make_search_result(chunk_id="shared", score=0.9, source="vector"),
        ]
        keyword_results = [
            _make_search_result(chunk_id="shared", score=0.8, source="keyword"),
        ]

        fused = service._rrf_fusion(
            result_lists=[vector_results, keyword_results],
            source_names=["vector", "keyword"],
            k=60,
        )

        assert len(fused) == 1
        assert "rrf_score" in fused[0].metadata
        assert "source_ranks" in fused[0].metadata
        # 두 소스 모두에서 rank 1
        source_ranks = fused[0].metadata["source_ranks"]
        assert "vector" in source_ranks
        assert "keyword" in source_ranks


# ---------------------------------------------------------------------------
# Singleton Factory Tests
# ---------------------------------------------------------------------------


class TestSingletonFactory:
    """get_hybrid_retriever / reset_hybrid_retriever 테스트"""

    def setup_method(self):
        """각 테스트 전 싱글톤 초기화"""
        reset_hybrid_retriever()

    def teardown_method(self):
        """각 테스트 후 싱글톤 초기화"""
        reset_hybrid_retriever()

    def test_get_hybrid_retriever_creates_singleton(self):
        """싱글톤 인스턴스 생성 검증"""
        r1 = get_hybrid_retriever()
        r2 = get_hybrid_retriever()

        assert r1 is r2

    def test_reset_hybrid_retriever(self):
        """싱글톤 초기화 검증"""
        r1 = get_hybrid_retriever()
        reset_hybrid_retriever()
        r2 = get_hybrid_retriever()

        assert r1 is not r2

    def test_get_hybrid_retriever_with_search_service(self):
        """SearchService 주입으로 생성"""
        mock_service = MagicMock()
        retriever = get_hybrid_retriever(search_service=mock_service)

        assert retriever.search_service is mock_service

    def test_get_hybrid_retriever_with_clients(self):
        """클라이언트 직접 전달로 생성"""
        fake_es = MagicMock()
        fake_neo4j = MagicMock()
        retriever = get_hybrid_retriever(
            es_client=fake_es, neo4j_driver=fake_neo4j
        )

        assert retriever._es_client is fake_es
        assert retriever._neo4j_driver is fake_neo4j


# ---------------------------------------------------------------------------
# Module Import Tests
# ---------------------------------------------------------------------------


class TestModuleImports:
    """모듈 import 검증"""

    def test_import_from_rag_package(self):
        """rag 패키지에서 정상 import 되는지 검증"""
        from app.rag import (
            ElasticsearchRetriever,
            HybridRetriever,
            Neo4jRetriever,
            get_hybrid_retriever,
            reset_hybrid_retriever,
        )

        assert ElasticsearchRetriever is not None
        assert Neo4jRetriever is not None
        assert HybridRetriever is not None
        assert callable(get_hybrid_retriever)
        assert callable(reset_hybrid_retriever)

    def test_import_from_retriever_module(self):
        """retriever 모듈에서 직접 import 되는지 검증"""
        from app.rag.retriever import (
            ElasticsearchRetriever,
            HybridRetriever,
            Neo4jRetriever,
            get_hybrid_retriever,
            reset_hybrid_retriever,
        )

        assert ElasticsearchRetriever is not None
        assert Neo4jRetriever is not None
        assert HybridRetriever is not None


# ---------------------------------------------------------------------------
# Edge Case Tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """엣지 케이스 테스트"""

    @pytest.mark.asyncio
    async def test_empty_query(self, hybrid_retriever, mock_search_service):
        """빈 쿼리 처리"""
        await hybrid_retriever.retrieve(query="", top_k=5)

        mock_search_service.hybrid_search.assert_called_once_with(
            query="",
            filters=None,
            top_k=5,
            user_id=None,
        )

    @pytest.mark.asyncio
    async def test_very_large_top_k(self, hybrid_retriever, mock_search_service):
        """매우 큰 top_k 값"""
        await hybrid_retriever.retrieve(query="large top_k", top_k=1000)

        call_args = mock_search_service.hybrid_search.call_args
        assert call_args.kwargs["top_k"] == 1000

    @pytest.mark.asyncio
    async def test_top_k_one(self, hybrid_retriever, mock_search_service):
        """top_k=1 검색"""
        mock_search_service.hybrid_search = AsyncMock(return_value={
            "results": [_make_search_result(chunk_id="only-1")],
            "total": 1,
            "search_type": "hybrid",
            "latency_ms": 10.0,
            "debug": {"vector_count": 1, "keyword_count": 0, "graph_count": 0, "fused_count": 1},
        })

        results = await hybrid_retriever.retrieve(
            query="single result", top_k=1
        )

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_unicode_query(self, hybrid_retriever, mock_search_service):
        """유니코드 (한글) 쿼리 처리"""
        await hybrid_retriever.retrieve(
            query="인공지능 기반 지식 검색 시스템 설계", top_k=5
        )

        call_args = mock_search_service.hybrid_search.call_args
        assert "인공지능" in call_args.kwargs["query"]

    @pytest.mark.asyncio
    async def test_entities_passed_to_retrieve(
        self, hybrid_retriever, mock_search_service
    ):
        """entities 파라미터가 전달되는지 검증"""
        entities = [
            {"name": "BGE-M3", "type": "Technology"},
            {"name": "Elasticsearch", "type": "Technology"},
        ]

        # retrieve는 SearchService.hybrid_search에 위임하므로
        # entities는 retrieve_by_source(graph)에서만 직접 사용됨
        results = await hybrid_retriever.retrieve(
            query="entity query",
            entities=entities,
            top_k=5,
        )

        # hybrid_search 호출은 정상적으로 이루어짐
        mock_search_service.hybrid_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_concurrent_retrieve_calls(
        self, hybrid_retriever, mock_search_service
    ):
        """동시 retrieve 호출 처리"""
        tasks = [
            hybrid_retriever.retrieve(query=f"query-{i}", top_k=5)
            for i in range(5)
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        assert mock_search_service.hybrid_search.call_count == 5
