"""
SearchService 단위 테스트

Hybrid/Semantic/Keyword 검색 서비스 테스트
- RRF 융합 알고리즘
- 검색 필터
- 검색 이력
- 에러 핸들링
"""

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from app.agents.state import SearchResult
from app.services.search import SearchFilters, SearchHistoryStore, SearchService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_search_result(
    chunk_id: str,
    content: str = "test content",
    score: float = 1.0,
    source: str = "vector",
    document_id: str = "doc_1",
) -> SearchResult:
    """테스트용 SearchResult 생성 헬퍼"""
    return SearchResult(
        chunk_id=chunk_id,
        document_id=document_id,
        content=content,
        score=score,
        source=source,
        metadata={"title": f"Document {document_id}"},
    )


# ---------------------------------------------------------------------------
# SearchFilters 테스트
# ---------------------------------------------------------------------------


class TestSearchFilters:
    """SearchFilters 테스트"""

    def test_from_dict_none(self):
        """None 입력 시 빈 필터 생성"""
        filters = SearchFilters.from_dict(None)
        assert filters.project_name is None
        assert filters.document_type is None
        assert filters.file_types == []

    def test_from_dict_with_values(self):
        """필터 값 파싱"""
        data = {
            "project_name": "Project A",
            "document_type": "기술문서",
            "category": "기술",
            "date_from": "2026-01-01",
            "date_to": "2026-12-31",
            "file_types": ["pdf", "docx"],
            "tags": ["Python", "RAG"],
        }
        filters = SearchFilters.from_dict(data)

        assert filters.project_name == "Project A"
        assert filters.document_type == "기술문서"
        assert filters.category == "기술"
        assert filters.date_from == "2026-01-01"
        assert filters.date_to == "2026-12-31"
        assert filters.file_types == ["pdf", "docx"]
        assert filters.tags == ["Python", "RAG"]

    def test_to_es_filter_empty(self):
        """빈 필터 → 빈 ES 쿼리"""
        filters = SearchFilters()
        es_filters = filters.to_es_filter()
        assert es_filters == []

    def test_to_es_filter_project_name(self):
        """프로젝트명 필터"""
        filters = SearchFilters(project_name="Project A")
        es_filters = filters.to_es_filter()

        assert len(es_filters) == 1
        assert es_filters[0] == {"term": {"metadata.project_name": "Project A"}}

    def test_to_es_filter_date_range(self):
        """날짜 범위 필터"""
        filters = SearchFilters(date_from="2026-01-01", date_to="2026-12-31")
        es_filters = filters.to_es_filter()

        assert len(es_filters) == 1
        assert "range" in es_filters[0]

    def test_to_es_filter_multiple(self):
        """복합 필터"""
        filters = SearchFilters(
            project_name="Project A",
            document_type="기술문서",
            file_types=["pdf"],
        )
        es_filters = filters.to_es_filter()
        assert len(es_filters) == 3


# ---------------------------------------------------------------------------
# SearchHistoryStore 테스트
# ---------------------------------------------------------------------------


class TestSearchHistoryStore:
    """SearchHistoryStore 테스트"""

    def test_record_and_get_recent(self):
        """검색 이력 기록 및 조회"""
        store = SearchHistoryStore()

        store.record(
            query="RAG 파이프라인",
            search_type="hybrid",
            result_count=10,
            latency_ms=150.5,
            user_id="user_1",
        )
        store.record(
            query="Elasticsearch 설정",
            search_type="keyword",
            result_count=5,
            latency_ms=80.0,
        )

        recent = store.get_recent(limit=10)
        assert len(recent) == 2
        assert recent[0]["query"] == "Elasticsearch 설정"  # 최신 먼저
        assert recent[1]["query"] == "RAG 파이프라인"

    def test_max_entries(self):
        """최대 항목 수 제한"""
        store = SearchHistoryStore(max_entries=5)

        for i in range(10):
            store.record(
                query=f"query_{i}",
                search_type="hybrid",
                result_count=1,
                latency_ms=10.0,
            )

        recent = store.get_recent(limit=100)
        assert len(recent) == 5
        # 최근 5개만 남아야 함
        assert recent[0]["query"] == "query_9"


# ---------------------------------------------------------------------------
# SearchService RRF 융합 테스트
# ---------------------------------------------------------------------------


class TestRRFFusion:
    """RRF 융합 알고리즘 테스트"""

    def setup_method(self):
        """테스트 설정"""
        with patch("app.services.search.get_embedder"):
            self.service = SearchService()

    def test_empty_results(self):
        """빈 결과 융합"""
        fused = self.service._rrf_fusion(
            result_lists=[[], [], []],
            source_names=["vector", "keyword", "graph"],
        )
        assert fused == []

    def test_single_source(self):
        """단일 소스 결과"""
        results = [
            make_search_result("chunk_1", score=1.0),
            make_search_result("chunk_2", score=0.8),
        ]

        fused = self.service._rrf_fusion(
            result_lists=[results],
            source_names=["vector"],
        )

        assert len(fused) == 2
        assert fused[0].chunk_id == "chunk_1"  # 1/(60+1) > 1/(60+2)
        assert fused[0].score > fused[1].score

    def test_multiple_sources_no_overlap(self):
        """다중 소스, 겹침 없음"""
        vector_results = [
            make_search_result("v_1", source="vector"),
            make_search_result("v_2", source="vector"),
        ]
        keyword_results = [
            make_search_result("k_1", source="keyword"),
            make_search_result("k_2", source="keyword"),
        ]

        fused = self.service._rrf_fusion(
            result_lists=[vector_results, keyword_results],
            source_names=["vector", "keyword"],
        )

        assert len(fused) == 4

    def test_multiple_sources_with_overlap(self):
        """다중 소스, 동일 청크 겹침 → 점수 합산"""
        vector_results = [
            make_search_result("chunk_A", source="vector"),  # rank 0
            make_search_result("chunk_B", source="vector"),  # rank 1
        ]
        keyword_results = [
            make_search_result("chunk_A", source="keyword"),  # rank 0 (겹침)
            make_search_result("chunk_C", source="keyword"),  # rank 1
        ]

        fused = self.service._rrf_fusion(
            result_lists=[vector_results, keyword_results],
            source_names=["vector", "keyword"],
            k=60,
        )

        # chunk_A는 양쪽에서 rank 0이므로 점수가 가장 높음
        assert len(fused) == 3
        assert fused[0].chunk_id == "chunk_A"

        # chunk_A의 RRF 점수 = 1/(60+1) + 1/(60+1) = 2/61
        expected_score_a = 2 * (1.0 / (60 + 1))
        assert abs(fused[0].score - expected_score_a) < 1e-5

    def test_rrf_k_parameter(self):
        """RRF k 파라미터 영향"""
        results = [
            make_search_result(f"chunk_{i}") for i in range(5)
        ]

        # k=1: 상위 순위와 하위 순위 차이가 큼
        fused_k1 = self.service._rrf_fusion(
            result_lists=[results],
            k=1,
        )
        # k=1000: 순위 간 차이가 작음
        fused_k1000 = self.service._rrf_fusion(
            result_lists=[results],
            k=1000,
        )

        # k가 작을수록 상위/하위 점수 차이가 큼
        ratio_k1 = fused_k1[0].score / fused_k1[-1].score
        ratio_k1000 = fused_k1000[0].score / fused_k1000[-1].score

        assert ratio_k1 > ratio_k1000

    def test_rrf_preserves_metadata(self):
        """RRF 융합 시 메타데이터 보존"""
        results = [
            make_search_result("chunk_1", content="important content"),
        ]

        fused = self.service._rrf_fusion(
            result_lists=[results],
            source_names=["vector"],
        )

        assert fused[0].content == "important content"
        assert "rrf_score" in fused[0].metadata
        assert "source_ranks" in fused[0].metadata

    def test_three_source_fusion(self):
        """Vector + Keyword + Graph 3소스 융합"""
        vector = [make_search_result("A"), make_search_result("B")]
        keyword = [make_search_result("B"), make_search_result("C")]
        graph = [make_search_result("A"), make_search_result("C")]

        fused = self.service._rrf_fusion(
            result_lists=[vector, keyword, graph],
            source_names=["vector", "keyword", "graph"],
            k=60,
        )

        # A: vector rank 0 + graph rank 0
        # B: vector rank 1 + keyword rank 0
        # C: keyword rank 1 + graph rank 1
        assert len(fused) == 3

        # A와 B는 각각 2개 소스에서 등장
        # A = 1/(60+1) + 1/(60+1) = 2/61
        # B = 1/(60+2) + 1/(60+1) = 1/62 + 1/61
        scores = {r.chunk_id: r.score for r in fused}
        assert scores["A"] > scores["C"]  # A는 두 소스 rank 0, C는 두 소스 rank 1


# ---------------------------------------------------------------------------
# SearchService 통합 테스트 (외부 의존 없이)
# ---------------------------------------------------------------------------


class TestSearchServiceNoExternalDeps:
    """외부 서비스 없이 SearchService 테스트"""

    def setup_method(self):
        """테스트 설정 - ES/Neo4j 없는 환경"""
        with patch("app.services.search.get_embedder"):
            self.service = SearchService(es_client=None, neo4j_driver=None)

    @pytest.mark.asyncio
    async def test_hybrid_search_no_clients(self):
        """ES/Neo4j 없이 hybrid 검색 → 빈 결과"""
        result = await self.service.hybrid_search(
            query="RAG 파이프라인",
            top_k=10,
        )

        assert result["search_type"] == "hybrid"
        assert result["total"] == 0
        assert result["results"] == []
        assert result["latency_ms"] >= 0

    @pytest.mark.asyncio
    async def test_semantic_search_no_es(self):
        """ES 없이 semantic 검색 → 빈 결과"""
        result = await self.service.semantic_search(
            query="Elasticsearch 설정",
            top_k=5,
        )

        assert result["search_type"] == "semantic"
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_keyword_search_no_es(self):
        """ES 없이 keyword 검색 → 빈 결과"""
        result = await self.service.keyword_search(
            query="BM25 검색",
            top_k=5,
        )

        assert result["search_type"] == "keyword"
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_hybrid_search_records_history(self):
        """검색 이력 기록 확인"""
        await self.service.hybrid_search(
            query="test query",
            user_id="user_123",
        )

        history = self.service.history_store.get_recent(limit=1)
        assert len(history) == 1
        assert history[0]["query"] == "test query"
        assert history[0]["search_type"] == "hybrid"

    @pytest.mark.asyncio
    async def test_hybrid_search_with_filters(self):
        """필터 적용 검색"""
        result = await self.service.hybrid_search(
            query="filtered search",
            filters={
                "project_name": "Project A",
                "document_type": "기술문서",
            },
            top_k=5,
        )

        assert result["total"] == 0  # ES 없으므로 빈 결과

    @pytest.mark.asyncio
    async def test_graph_search_no_neo4j(self):
        """Neo4j 없이 graph 검색 → 빈 결과"""
        results = await self.service._graph_search(
            query="graph search test",
            top_k=10,
        )
        assert results == []


# ---------------------------------------------------------------------------
# ES 응답 파싱 테스트
# ---------------------------------------------------------------------------


class TestESResultParsing:
    """Elasticsearch 응답 파싱 테스트"""

    def setup_method(self):
        """테스트 설정"""
        with patch("app.services.search.get_embedder"):
            self.service = SearchService()

    def test_parse_empty_response(self):
        """빈 ES 응답 파싱"""
        response = {"hits": {"hits": [], "total": {"value": 0}}}
        results = self.service._parse_es_results(response, source="vector")
        assert results == []

    def test_parse_single_hit(self):
        """단일 ES 히트 파싱"""
        response = {
            "hits": {
                "hits": [
                    {
                        "_id": "chunk_001",
                        "_score": 0.95,
                        "_source": {
                            "content": "Elasticsearch kNN 검색을 사용합니다.",
                            "metadata": {
                                "document_id": "doc_001",
                                "title": "ES 가이드",
                            },
                        },
                    }
                ],
                "total": {"value": 1},
            }
        }

        results = self.service._parse_es_results(response, source="vector")
        assert len(results) == 1
        assert results[0].chunk_id == "chunk_001"
        assert results[0].score == 0.95
        assert results[0].content == "Elasticsearch kNN 검색을 사용합니다."
        assert results[0].source == "vector"
        assert results[0].metadata["search_source"] == "vector"

    def test_parse_with_highlight(self):
        """하이라이트 포함 ES 응답 파싱"""
        response = {
            "hits": {
                "hits": [
                    {
                        "_id": "chunk_002",
                        "_score": 0.8,
                        "_source": {
                            "content": "RAG 파이프라인을 구현합니다.",
                            "metadata": {"document_id": "doc_002"},
                        },
                        "highlight": {
                            "content": ["<em>RAG</em> 파이프라인을 구현합니다."],
                        },
                    }
                ],
                "total": {"value": 1},
            }
        }

        results = self.service._parse_es_results(response, source="keyword")
        assert len(results) == 1
        assert "highlight" in results[0].metadata

    def test_parse_multiple_hits(self):
        """여러 ES 히트 파싱"""
        response = {
            "hits": {
                "hits": [
                    {
                        "_id": f"chunk_{i}",
                        "_score": 1.0 - i * 0.1,
                        "_source": {
                            "content": f"Content {i}",
                            "metadata": {"document_id": f"doc_{i}"},
                        },
                    }
                    for i in range(5)
                ],
                "total": {"value": 5},
            }
        }

        results = self.service._parse_es_results(response, source="vector")
        assert len(results) == 5
        assert results[0].score > results[4].score
