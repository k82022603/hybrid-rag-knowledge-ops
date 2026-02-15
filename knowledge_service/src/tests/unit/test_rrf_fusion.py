"""
RRF Fusion 알고리즘 단위 테스트

TEST_MODE=docker pytest src/tests/unit/test_rrf_fusion.py -v
"""

import pytest

from app.services.rrf_fusion import (
    RRFFusion,
    RRFResult,
    RRFFusionExplanation,
    get_rrf_fusion,
    reset_rrf_fusion,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fusion():
    """기본 RRFFusion 인스턴스 (k=60)"""
    return RRFFusion(k=60)


@pytest.fixture
def sample_results():
    """테스트용 검색 결과"""
    es_results = [
        {"doc_id": "doc-1", "content": "ES result 1", "metadata": {"source": "es"}},
        {"doc_id": "doc-2", "content": "ES result 2", "metadata": {"source": "es"}},
        {"doc_id": "doc-3", "content": "ES result 3", "metadata": {"source": "es"}},
    ]
    neo4j_results = [
        {"doc_id": "doc-2", "content": "Neo4j result 2", "metadata": {"source": "neo4j"}},
        {"doc_id": "doc-4", "content": "Neo4j result 4", "metadata": {"source": "neo4j"}},
        {"doc_id": "doc-1", "content": "Neo4j result 1", "metadata": {"source": "neo4j"}},
    ]
    return es_results, neo4j_results


# ---------------------------------------------------------------------------
# 초기화 테스트
# ---------------------------------------------------------------------------


class TestRRFFusionInit:
    """RRFFusion 초기화 테스트"""

    def test_default_k(self):
        f = RRFFusion()
        assert f.k == 60

    def test_custom_k(self):
        f = RRFFusion(k=30)
        assert f.k == 30

    def test_invalid_k_zero(self):
        with pytest.raises(ValueError, match="positive integer"):
            RRFFusion(k=0)

    def test_invalid_k_negative(self):
        with pytest.raises(ValueError):
            RRFFusion(k=-1)


# ---------------------------------------------------------------------------
# fuse() 테스트
# ---------------------------------------------------------------------------


class TestFuse:
    """RRF 융합 기본 테스트"""

    def test_single_source(self, fusion):
        results = [
            {"doc_id": "a", "content": "text a"},
            {"doc_id": "b", "content": "text b"},
        ]
        fused = fusion.fuse(result_lists=[results])
        assert len(fused) == 2
        assert fused[0].doc_id == "a"  # rank 0 -> higher score
        assert fused[0].rrf_score > fused[1].rrf_score

    def test_two_sources_overlap(self, fusion, sample_results):
        """두 소스에 모두 존재하는 문서가 더 높은 점수"""
        es, neo4j = sample_results
        fused = fusion.fuse(
            result_lists=[es, neo4j],
            source_names=["es", "neo4j"],
        )

        # doc-1, doc-2는 양쪽에 있으므로 상위
        ids = [r.doc_id for r in fused]
        assert "doc-1" in ids[:3]
        assert "doc-2" in ids[:3]

        # 양쪽에 있는 doc은 source_scores에 두 소스 모두 있음
        doc2 = next(r for r in fused if r.doc_id == "doc-2")
        assert "es" in doc2.source_scores
        assert "neo4j" in doc2.source_scores

    def test_rrf_score_formula(self, fusion):
        """RRF 공식: weight * 1/(k+rank+1) 검증"""
        results = [{"doc_id": "x", "content": ""}]
        fused = fusion.fuse(result_lists=[results], weights=[1.0])

        expected = 1.0 / (60 + 0 + 1)  # k=60, rank=0
        assert abs(fused[0].rrf_score - round(expected, 6)) < 1e-6

    def test_weighted_fusion(self, fusion):
        """가중치가 점수에 반영됨"""
        src1 = [{"doc_id": "a", "content": ""}]
        src2 = [{"doc_id": "b", "content": ""}]

        fused = fusion.fuse(
            result_lists=[src1, src2],
            weights=[2.0, 1.0],
        )

        # weight=2.0인 소스의 문서가 더 높은 점수
        assert fused[0].doc_id == "a"
        assert fused[0].rrf_score > fused[1].rrf_score

    def test_auto_source_names(self, fusion):
        """source_names 미지정 시 자동 생성"""
        fused = fusion.fuse(
            result_lists=[[{"doc_id": "a"}], [{"doc_id": "b"}]],
        )
        assert "source_0" in fused[0].source_scores
        assert "source_1" in fused[1].source_scores

    def test_empty_source_list(self, fusion):
        """하나의 소스가 빈 리스트"""
        fused = fusion.fuse(
            result_lists=[[{"doc_id": "a"}], []],
            source_names=["es", "neo4j"],
        )
        assert len(fused) == 1
        assert fused[0].doc_id == "a"

    def test_no_doc_id_skipped(self, fusion):
        """doc_id 없는 결과는 건너뜀"""
        results = [
            {"doc_id": "a", "content": "ok"},
            {"content": "no id"},
        ]
        fused = fusion.fuse(result_lists=[results])
        assert len(fused) == 1

    def test_metadata_preserved(self, fusion):
        """메타데이터가 보존됨 (첫 등장 기준)"""
        results = [{"doc_id": "a", "content": "text", "metadata": {"key": "value"}}]
        fused = fusion.fuse(result_lists=[results])
        assert fused[0].metadata.get("key") == "value"

    def test_content_preserved(self, fusion):
        """content가 보존됨"""
        results = [{"doc_id": "a", "content": "hello world"}]
        fused = fusion.fuse(result_lists=[results])
        assert fused[0].content == "hello world"


# ---------------------------------------------------------------------------
# 입력 검증 테스트
# ---------------------------------------------------------------------------


class TestValidation:
    """입력 검증 테스트"""

    def test_empty_result_lists(self, fusion):
        with pytest.raises(ValueError, match="at least one source"):
            fusion.fuse(result_lists=[])

    def test_weights_length_mismatch(self, fusion):
        with pytest.raises(ValueError, match="weights length"):
            fusion.fuse(
                result_lists=[[{"doc_id": "a"}]],
                weights=[1.0, 2.0],
            )

    def test_source_names_length_mismatch(self, fusion):
        with pytest.raises(ValueError, match="source_names length"):
            fusion.fuse(
                result_lists=[[{"doc_id": "a"}]],
                source_names=["es", "neo4j"],
            )

    def test_negative_weight(self, fusion):
        with pytest.raises(ValueError, match="negative"):
            fusion.fuse(
                result_lists=[[{"doc_id": "a"}]],
                weights=[-1.0],
            )

    def test_not_list(self, fusion):
        with pytest.raises(ValueError, match="must be a list"):
            fusion.fuse(result_lists="not a list")


# ---------------------------------------------------------------------------
# fuse_with_explanation() 테스트
# ---------------------------------------------------------------------------


class TestFuseWithExplanation:
    """설명 포함 융합 테스트"""

    def test_explanation_structure(self, fusion, sample_results):
        es, neo4j = sample_results
        explanation = fusion.fuse_with_explanation(
            result_lists=[es, neo4j],
            weights=[0.6, 0.4],
            source_names=["es", "neo4j"],
        )

        assert isinstance(explanation, RRFFusionExplanation)
        assert explanation.k == 60
        assert explanation.weights == {"es": 0.6, "neo4j": 0.4}
        assert explanation.source_counts["es"] == 3
        assert explanation.source_counts["neo4j"] == 3
        assert explanation.total_unique == 4  # doc-1,2,3,4

    def test_fusion_details_contain_ranks(self, fusion):
        src = [{"doc_id": "a"}, {"doc_id": "b"}]
        explanation = fusion.fuse_with_explanation(
            result_lists=[src],
            source_names=["es"],
        )

        detail = explanation.fusion_details[0]
        assert "source_contributions" in detail
        assert "es" in detail["source_contributions"]
        assert "rank" in detail["source_contributions"]["es"]


# ---------------------------------------------------------------------------
# fuse_search_results() 테스트
# ---------------------------------------------------------------------------


class TestFuseSearchResults:
    """SearchResult 호환 융합 테스트"""

    def test_search_result_objects(self, fusion):
        """SearchResult-like 객체 처리"""

        class MockSearchResult:
            def __init__(self, chunk_id, content="", score=0.0):
                self.chunk_id = chunk_id
                self.content = content
                self.score = score
                self.metadata = {}
                self.source = ""

        sr1 = [MockSearchResult("c1", "text1"), MockSearchResult("c2", "text2")]
        sr2 = [MockSearchResult("c2", "text2"), MockSearchResult("c3", "text3")]

        fused = fusion.fuse_search_results(
            result_lists=[sr1, sr2],
            weights=[1.0, 1.0],
            source_names=["vector", "keyword"],
        )

        assert len(fused) == 3  # c1, c2, c3
        # c2 appears in both -> highest score
        assert fused[0].chunk_id == "c2"
        assert fused[0].metadata.get("rrf_score") is not None
        assert "source_ranks" in fused[0].metadata

    def test_empty_search_results(self, fusion):
        result = fusion.fuse_search_results(result_lists=[])
        assert result == []


# ---------------------------------------------------------------------------
# 정렬 정확성 테스트
# ---------------------------------------------------------------------------


class TestSortingAccuracy:
    """점수 기반 정렬 정확성"""

    def test_descending_order(self, fusion):
        """결과가 RRF 점수 내림차순"""
        src = [{"doc_id": f"d{i}"} for i in range(10)]
        fused = fusion.fuse(result_lists=[src])
        scores = [r.rrf_score for r in fused]
        assert scores == sorted(scores, reverse=True)

    def test_three_source_rrf(self, fusion):
        """3-way RRF (vector + keyword + sparse)"""
        vector = [{"doc_id": "a"}, {"doc_id": "b"}, {"doc_id": "c"}]
        keyword = [{"doc_id": "b"}, {"doc_id": "d"}, {"doc_id": "a"}]
        sparse = [{"doc_id": "a"}, {"doc_id": "c"}, {"doc_id": "d"}]

        fused = fusion.fuse(
            result_lists=[vector, keyword, sparse],
            weights=[1.0, 1.0, 0.7],
            source_names=["vector", "keyword", "sparse"],
        )

        # 'a' appears in all 3 sources -> highest
        assert fused[0].doc_id == "a"
        assert len(fused[0].source_scores) == 3


# ---------------------------------------------------------------------------
# 싱글톤 테스트
# ---------------------------------------------------------------------------


class TestSingleton:
    """get_rrf_fusion / reset_rrf_fusion 테스트"""

    def test_singleton(self):
        reset_rrf_fusion()
        f1 = get_rrf_fusion()
        f2 = get_rrf_fusion()
        assert f1 is f2
        reset_rrf_fusion()

    def test_reset(self):
        f1 = get_rrf_fusion()
        reset_rrf_fusion()
        f2 = get_rrf_fusion()
        assert f1 is not f2
        reset_rrf_fusion()


# ---------------------------------------------------------------------------
# RRFResult dataclass 테스트
# ---------------------------------------------------------------------------


class TestRRFResult:
    """RRFResult 데이터클래스 테스트"""

    def test_repr(self):
        r = RRFResult(
            doc_id="test-1",
            content="hello",
            rrf_score=0.016393,
            source_scores={"es": 0.01, "neo4j": 0.006393},
        )
        repr_str = repr(r)
        assert "test-1" in repr_str
        assert "0.016393" in repr_str

    def test_default_values(self):
        r = RRFResult(doc_id="x", content="y")
        assert r.rrf_score == 0.0
        assert r.source_scores == {}
        assert r.metadata == {}
