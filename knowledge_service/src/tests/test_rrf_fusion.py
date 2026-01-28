"""
RRF Fusion 알고리즘 단위 테스트

STORY-031: RRF Fusion 알고리즘 구현
- AC1: ES 결과 20개 + Neo4j 결과 20개 -> RRF Fusion -> 통합 순위 결과 반환
- AC2: 동일 문서가 양쪽에 존재 시 양쪽 순위 점수 합산
- AC3: 가중치 (es=0.6, neo4j=0.4) 반영된 점수 계산
- AC4: k=60, RRF 공식 1/(k+rank+1) 적용
- AC5: 정렬된 결과 반환

테스트 범주:
1. RRFResult 데이터클래스 테스트
2. RRFFusion 초기화 및 검증 테스트
3. AC별 수용 기준 테스트 (5개)
4. 점수 계산 정확성 테스트
5. 가중치 적용 테스트
6. 중복 문서 처리 테스트
7. 빈 결과 및 에지 케이스 테스트
8. fuse_with_explanation 테스트
9. SearchResult 호환 테스트
10. 싱글톤 팩토리 테스트
"""

import sys
from types import ModuleType
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# 환경 의존성 Mock: WSL2/CI에서 torch/langchain 패키지 누락 방지
# app.services.__init__이 llm_service -> langchain_openai를 import하므로
# rrf_fusion 모듈 import 전에 누락 패키지를 mock해야 합니다.
# ---------------------------------------------------------------------------

_TORCH_IMPORT_ERROR = False
try:
    import torch  # noqa: F401
except (OSError, ImportError, ValueError):
    _TORCH_IMPORT_ERROR = True
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
    _torch_mock.no_grad = MagicMock(  # type: ignore[attr-defined]
        return_value=MagicMock(__enter__=MagicMock(), __exit__=MagicMock())
    )
    sys.modules["torch"] = _torch_mock
    for submod in [
        "torch.nn",
        "torch.nn.functional",
        "torch.utils",
        "torch.utils.data",
        "torch.cuda",
        "torch.amp",
    ]:
        if submod not in sys.modules:
            sys.modules[submod] = MagicMock()

# Mock missing langchain/ML/infra packages to avoid ImportError from __init__.py chain
# The import chain: app.services.__init__ -> llm_service -> langchain_openai
#                   app.services.search -> app.agents.state -> app.agents.__init__
#                   -> vip_agent -> langgraph, etc.
_LANGCHAIN_MOCKED = False
_MOCK_PACKAGES = [
    # LangChain ecosystem
    "langchain_openai",
    "langchain_core",
    "langchain_core.language_models",
    "langchain_core.language_models.chat_models",
    "langchain_core.messages",
    "langchain_core.prompts",
    "langchain_core.output_parsers",
    "langchain_community",
    "langchain",
    # LangGraph
    "langgraph",
    "langgraph.graph",
    "langgraph.prebuilt",
    "langgraph.checkpoint",
    # OpenAI
    "openai",
    # Embedding models
    "FlagEmbedding",
    "sentence_transformers",
    "transformers",
    # Infrastructure
    "elasticsearch",
    "neo4j",
    "minio",
    "redis",
    # Numpy (if missing)
]
for _pkg in _MOCK_PACKAGES:
    if _pkg not in sys.modules:
        sys.modules[_pkg] = MagicMock()
        _LANGCHAIN_MOCKED = True

from app.services.rrf_fusion import (  # noqa: E402
    RRFFusion,
    RRFFusionExplanation,
    RRFResult,
    get_rrf_fusion,
    reset_rrf_fusion,
)


# ---------------------------------------------------------------------------
# Test Fixtures & Helpers
# ---------------------------------------------------------------------------


def _make_es_results(count: int = 20) -> List[Dict[str, Any]]:
    """ES 검색 결과 생성 (딕셔너리 형태)"""
    return [
        {
            "doc_id": f"es-doc-{i}",
            "content": f"Elasticsearch result content {i}",
            "metadata": {
                "source": "elasticsearch",
                "score": round(1.0 - (i * 0.04), 4),
                "index": i,
            },
        }
        for i in range(count)
    ]


def _make_neo4j_results(count: int = 20) -> List[Dict[str, Any]]:
    """Neo4j 검색 결과 생성 (딕셔너리 형태)"""
    return [
        {
            "doc_id": f"neo4j-doc-{i}",
            "content": f"Neo4j graph result content {i}",
            "metadata": {
                "source": "neo4j",
                "score": round(0.95 - (i * 0.04), 4),
                "index": i,
            },
        }
        for i in range(count)
    ]


def _make_overlapping_results() -> tuple:
    """ES와 Neo4j에 중복 문서가 있는 결과 생성"""
    es_results = [
        {"doc_id": "shared-1", "content": "Shared doc 1 (ES)", "metadata": {"source": "es"}},
        {"doc_id": "es-only-1", "content": "ES only 1", "metadata": {"source": "es"}},
        {"doc_id": "shared-2", "content": "Shared doc 2 (ES)", "metadata": {"source": "es"}},
        {"doc_id": "es-only-2", "content": "ES only 2", "metadata": {"source": "es"}},
    ]
    neo4j_results = [
        {"doc_id": "shared-2", "content": "Shared doc 2 (Neo4j)", "metadata": {"source": "neo4j"}},
        {"doc_id": "neo4j-only-1", "content": "Neo4j only 1", "metadata": {"source": "neo4j"}},
        {"doc_id": "shared-1", "content": "Shared doc 1 (Neo4j)", "metadata": {"source": "neo4j"}},
        {"doc_id": "neo4j-only-2", "content": "Neo4j only 2", "metadata": {"source": "neo4j"}},
    ]
    return es_results, neo4j_results


@pytest.fixture
def fusion() -> RRFFusion:
    """기본 RRFFusion 인스턴스 (k=60)"""
    return RRFFusion(k=60)


@pytest.fixture
def es_results_20() -> List[Dict[str, Any]]:
    """ES 결과 20개"""
    return _make_es_results(20)


@pytest.fixture
def neo4j_results_20() -> List[Dict[str, Any]]:
    """Neo4j 결과 20개"""
    return _make_neo4j_results(20)


# ---------------------------------------------------------------------------
# 1. RRFResult 데이터클래스 테스트
# ---------------------------------------------------------------------------


class TestRRFResult:
    """RRFResult 데이터클래스 테스트"""

    def test_create_rrf_result(self):
        """RRFResult 기본 생성"""
        result = RRFResult(
            doc_id="doc-1",
            content="test content",
            metadata={"key": "value"},
            rrf_score=0.032787,
            source_scores={"es": 0.016393, "neo4j": 0.016393},
        )

        assert result.doc_id == "doc-1"
        assert result.content == "test content"
        assert result.metadata == {"key": "value"}
        assert result.rrf_score == 0.032787
        assert result.source_scores == {"es": 0.016393, "neo4j": 0.016393}

    def test_rrf_result_defaults(self):
        """RRFResult 기본값 검증"""
        result = RRFResult(doc_id="doc-2", content="minimal")

        assert result.metadata == {}
        assert result.rrf_score == 0.0
        assert result.source_scores == {}

    def test_rrf_result_repr(self):
        """RRFResult __repr__ 검증"""
        result = RRFResult(
            doc_id="doc-1",
            content="test",
            rrf_score=0.032787,
            source_scores={"es": 0.016, "neo4j": 0.016},
        )

        repr_str = repr(result)
        assert "doc-1" in repr_str
        assert "0.032787" in repr_str
        assert "es" in repr_str
        assert "neo4j" in repr_str


# ---------------------------------------------------------------------------
# 2. RRFFusion 초기화 및 검증 테스트
# ---------------------------------------------------------------------------


class TestRRFFusionInit:
    """RRFFusion 초기화 테스트"""

    def test_default_k(self):
        """기본 k=60 검증"""
        f = RRFFusion()
        assert f.k == 60

    def test_custom_k(self):
        """사용자 지정 k 검증"""
        f = RRFFusion(k=100)
        assert f.k == 100

    def test_invalid_k_zero(self):
        """k=0 시 ValueError"""
        with pytest.raises(ValueError, match="positive integer"):
            RRFFusion(k=0)

    def test_invalid_k_negative(self):
        """k<0 시 ValueError"""
        with pytest.raises(ValueError, match="positive integer"):
            RRFFusion(k=-10)

    def test_validation_empty_result_lists(self, fusion):
        """빈 result_lists 검증"""
        with pytest.raises(ValueError, match="at least one source"):
            fusion.fuse(result_lists=[])

    def test_validation_weights_length_mismatch(self, fusion):
        """weights 길이 불일치 검증"""
        with pytest.raises(ValueError, match="weights length"):
            fusion.fuse(
                result_lists=[[], []],
                weights=[0.5],  # 2개 소스에 1개 가중치
            )

    def test_validation_source_names_length_mismatch(self, fusion):
        """source_names 길이 불일치 검증"""
        with pytest.raises(ValueError, match="source_names length"):
            fusion.fuse(
                result_lists=[[], []],
                source_names=["only_one"],
            )

    def test_validation_negative_weight(self, fusion):
        """음수 가중치 검증"""
        with pytest.raises(ValueError, match="negative"):
            fusion.fuse(
                result_lists=[[], []],
                weights=[0.6, -0.4],
            )

    def test_validation_invalid_result_lists_type(self, fusion):
        """잘못된 result_lists 타입 검증"""
        with pytest.raises(ValueError, match="must be a list"):
            fusion.fuse(result_lists="not a list")  # type: ignore


# ---------------------------------------------------------------------------
# 3. AC별 수용 기준 테스트
# ---------------------------------------------------------------------------


class TestAcceptanceCriteria:
    """STORY-031 Acceptance Criteria 테스트"""

    def test_ac1_es_20_neo4j_20_fused_results(
        self, fusion, es_results_20, neo4j_results_20
    ):
        """
        AC1: ES 결과 20개 + Neo4j 결과 20개 -> RRF Fusion -> 통합 순위 결과 반환

        양쪽 소스의 결과가 모두 반영되고, 고유 문서 기준으로
        통합된 결과가 반환되어야 합니다.
        """
        results = fusion.fuse(
            result_lists=[es_results_20, neo4j_results_20],
            source_names=["es", "neo4j"],
        )

        # 모든 결과가 포함되어야 함 (중복 없으므로 40개)
        assert len(results) == 40

        # 모든 결과가 RRFResult 타입
        for r in results:
            assert isinstance(r, RRFResult)

        # ES 결과 20개가 모두 포함
        es_doc_ids = {f"es-doc-{i}" for i in range(20)}
        result_doc_ids = {r.doc_id for r in results}
        assert es_doc_ids.issubset(result_doc_ids)

        # Neo4j 결과 20개가 모두 포함
        neo4j_doc_ids = {f"neo4j-doc-{i}" for i in range(20)}
        assert neo4j_doc_ids.issubset(result_doc_ids)

    def test_ac2_duplicate_document_score_summed(self, fusion):
        """
        AC2: 동일 문서가 양쪽에 존재 시 양쪽 순위 점수 합산

        같은 doc_id가 ES와 Neo4j 모두에 있을 경우,
        두 소스의 RRF 점수가 합산되어야 합니다.
        """
        es_results = [
            {"doc_id": "shared-doc", "content": "Shared content", "metadata": {}},
            {"doc_id": "es-only", "content": "ES only", "metadata": {}},
        ]
        neo4j_results = [
            {"doc_id": "neo4j-only", "content": "Neo4j only", "metadata": {}},
            {"doc_id": "shared-doc", "content": "Shared content", "metadata": {}},
        ]

        results = fusion.fuse(
            result_lists=[es_results, neo4j_results],
            source_names=["es", "neo4j"],
        )

        # 고유 문서 3개
        assert len(results) == 3

        # shared-doc 찾기
        shared = next(r for r in results if r.doc_id == "shared-doc")

        # 양쪽 소스의 점수가 합산
        assert "es" in shared.source_scores
        assert "neo4j" in shared.source_scores

        # ES rank=0: 1/(60+0+1) = 1/61
        es_score = 1.0 / (60 + 0 + 1)
        # Neo4j rank=1: 1/(60+1+1) = 1/62
        neo4j_score = 1.0 / (60 + 1 + 1)

        expected_total = es_score + neo4j_score
        assert abs(shared.rrf_score - round(expected_total, 6)) < 1e-5

        # shared-doc가 가장 높은 점수 (두 소스 합산)
        assert results[0].doc_id == "shared-doc"

    def test_ac3_weighted_scores(self, fusion):
        """
        AC3: 가중치 (es=0.6, neo4j=0.4) 반영된 점수 계산

        ES에 0.6, Neo4j에 0.4 가중치를 적용했을 때
        점수가 올바르게 계산되어야 합니다.
        """
        es_results = [
            {"doc_id": "doc-A", "content": "A", "metadata": {}},
        ]
        neo4j_results = [
            {"doc_id": "doc-A", "content": "A", "metadata": {}},
        ]

        results = fusion.fuse(
            result_lists=[es_results, neo4j_results],
            weights=[0.6, 0.4],
            source_names=["es", "neo4j"],
        )

        assert len(results) == 1
        doc_a = results[0]

        # ES rank=0, weight=0.6: 0.6 * 1/(60+0+1) = 0.6/61
        es_weighted = 0.6 * (1.0 / (60 + 0 + 1))
        # Neo4j rank=0, weight=0.4: 0.4 * 1/(60+0+1) = 0.4/61
        neo4j_weighted = 0.4 * (1.0 / (60 + 0 + 1))

        expected_total = round(es_weighted + neo4j_weighted, 6)
        assert doc_a.rrf_score == expected_total

        # ES 점수가 Neo4j보다 높아야 함 (같은 rank지만 가중치가 다름)
        assert doc_a.source_scores["es"] > doc_a.source_scores["neo4j"]

    def test_ac4_rrf_formula_k60(self):
        """
        AC4: k=60, RRF 공식 1/(k+rank+1) 적용

        k=60일 때 각 rank에 대한 RRF 점수가 정확히 계산되는지 검증합니다.
        """
        fusion = RRFFusion(k=60)

        results = [
            {"doc_id": f"doc-{i}", "content": f"Content {i}", "metadata": {}}
            for i in range(5)
        ]

        fused = fusion.fuse(
            result_lists=[results],
            source_names=["source"],
        )

        # 각 rank별 기대 점수 검증
        expected_scores = [
            round(1.0 / (60 + rank + 1), 6) for rank in range(5)
        ]

        for i, result in enumerate(fused):
            assert result.rrf_score == expected_scores[i], (
                f"Rank {i}: expected {expected_scores[i]}, got {result.rrf_score}"
            )

        # rank 0: 1/61 ~= 0.016393
        assert abs(fused[0].rrf_score - 1.0 / 61) < 1e-5
        # rank 1: 1/62 ~= 0.016129
        assert abs(fused[1].rrf_score - 1.0 / 62) < 1e-5
        # rank 4: 1/65 ~= 0.015385
        assert abs(fused[4].rrf_score - 1.0 / 65) < 1e-5

    def test_ac5_sorted_results(self, fusion, es_results_20, neo4j_results_20):
        """
        AC5: 정렬된 결과 반환

        융합된 결과가 RRF 점수 기준 내림차순으로 정렬되어야 합니다.
        """
        results = fusion.fuse(
            result_lists=[es_results_20, neo4j_results_20],
            weights=[0.6, 0.4],
            source_names=["es", "neo4j"],
        )

        # 내림차순 정렬 검증
        for i in range(len(results) - 1):
            assert results[i].rrf_score >= results[i + 1].rrf_score, (
                f"Results not sorted at index {i}: "
                f"{results[i].rrf_score} < {results[i + 1].rrf_score}"
            )


# ---------------------------------------------------------------------------
# 4. 점수 계산 정확성 테스트
# ---------------------------------------------------------------------------


class TestScoreCalculation:
    """RRF 점수 계산 정확성 테스트"""

    def test_single_source_scores(self, fusion):
        """단일 소스 점수 계산"""
        results = [
            {"doc_id": "d1", "content": "c1", "metadata": {}},
            {"doc_id": "d2", "content": "c2", "metadata": {}},
            {"doc_id": "d3", "content": "c3", "metadata": {}},
        ]

        fused = fusion.fuse(result_lists=[results], source_names=["s1"])

        # rank 0: 1/(60+0+1) = 1/61
        assert abs(fused[0].rrf_score - 1.0 / 61) < 1e-6
        # rank 1: 1/(60+1+1) = 1/62
        assert abs(fused[1].rrf_score - 1.0 / 62) < 1e-6
        # rank 2: 1/(60+2+1) = 1/63
        assert abs(fused[2].rrf_score - 1.0 / 63) < 1e-6

    def test_two_source_no_overlap(self, fusion):
        """두 소스, 중복 없는 경우 점수 계산"""
        source_a = [
            {"doc_id": "a1", "content": "a1", "metadata": {}},
            {"doc_id": "a2", "content": "a2", "metadata": {}},
        ]
        source_b = [
            {"doc_id": "b1", "content": "b1", "metadata": {}},
        ]

        fused = fusion.fuse(
            result_lists=[source_a, source_b],
            source_names=["a", "b"],
        )

        assert len(fused) == 3

        # a1: rank=0 in source_a -> 1/61
        a1 = next(r for r in fused if r.doc_id == "a1")
        assert abs(a1.rrf_score - 1.0 / 61) < 1e-6

        # b1: rank=0 in source_b -> 1/61
        b1 = next(r for r in fused if r.doc_id == "b1")
        assert abs(b1.rrf_score - 1.0 / 61) < 1e-6

    def test_two_source_with_overlap_exact_scores(self, fusion):
        """두 소스, 중복 있는 경우 정확한 점수 합산"""
        source_a = [
            {"doc_id": "shared", "content": "shared", "metadata": {}},  # rank 0
            {"doc_id": "a-only", "content": "a", "metadata": {}},  # rank 1
        ]
        source_b = [
            {"doc_id": "b-only", "content": "b", "metadata": {}},  # rank 0
            {"doc_id": "shared", "content": "shared", "metadata": {}},  # rank 1
        ]

        fused = fusion.fuse(
            result_lists=[source_a, source_b],
            source_names=["a", "b"],
        )

        shared = next(r for r in fused if r.doc_id == "shared")
        expected = 1.0 / 61 + 1.0 / 62  # rank 0 in a + rank 1 in b
        assert abs(shared.rrf_score - round(expected, 6)) < 1e-5

    def test_different_k_values(self):
        """다양한 k 값에 따른 점수 변화 검증"""
        results = [{"doc_id": "doc-1", "content": "c", "metadata": {}}]

        fusion_k1 = RRFFusion(k=1)
        fusion_k60 = RRFFusion(k=60)
        fusion_k100 = RRFFusion(k=100)

        r1 = fusion_k1.fuse(result_lists=[results], source_names=["s"])
        r60 = fusion_k60.fuse(result_lists=[results], source_names=["s"])
        r100 = fusion_k100.fuse(result_lists=[results], source_names=["s"])

        # k가 작을수록 점수가 높음
        assert r1[0].rrf_score > r60[0].rrf_score > r100[0].rrf_score

        # 구체적 값 검증
        # k=1: 1/(1+0+1) = 0.5
        assert abs(r1[0].rrf_score - 0.5) < 1e-5
        # k=60: 1/(60+0+1) ~= 0.016393
        assert abs(r60[0].rrf_score - 1.0 / 61) < 1e-5
        # k=100: 1/(100+0+1) ~= 0.009901
        assert abs(r100[0].rrf_score - 1.0 / 101) < 1e-5


# ---------------------------------------------------------------------------
# 5. 가중치 적용 테스트
# ---------------------------------------------------------------------------


class TestWeights:
    """가중치 적용 테스트"""

    def test_equal_weights(self, fusion):
        """동일 가중치 (기본값)"""
        source_a = [{"doc_id": "d1", "content": "c", "metadata": {}}]
        source_b = [{"doc_id": "d1", "content": "c", "metadata": {}}]

        fused = fusion.fuse(
            result_lists=[source_a, source_b],
            weights=[1.0, 1.0],
            source_names=["a", "b"],
        )

        # 양쪽 동일 가중치 -> score = 1.0*1/61 + 1.0*1/61 = 2/61
        assert abs(fused[0].rrf_score - round(2.0 / 61, 6)) < 1e-5

    def test_weighted_es_neo4j(self, fusion):
        """ES=0.6, Neo4j=0.4 가중치 적용"""
        es = [{"doc_id": "d1", "content": "c", "metadata": {}}]
        neo4j = [{"doc_id": "d2", "content": "c", "metadata": {}}]

        fused = fusion.fuse(
            result_lists=[es, neo4j],
            weights=[0.6, 0.4],
            source_names=["es", "neo4j"],
        )

        d1 = next(r for r in fused if r.doc_id == "d1")
        d2 = next(r for r in fused if r.doc_id == "d2")

        # d1 (ES only, rank 0): 0.6 * 1/61
        expected_d1 = round(0.6 * (1.0 / 61), 6)
        assert d1.rrf_score == expected_d1

        # d2 (Neo4j only, rank 0): 0.4 * 1/61
        expected_d2 = round(0.4 * (1.0 / 61), 6)
        assert d2.rrf_score == expected_d2

        # ES 가중치가 높으므로 d1 > d2
        assert d1.rrf_score > d2.rrf_score

    def test_zero_weight_excludes_source(self, fusion):
        """가중치 0은 해당 소스를 실질적으로 무시"""
        source_a = [{"doc_id": "d1", "content": "c", "metadata": {}}]
        source_b = [{"doc_id": "d2", "content": "c", "metadata": {}}]

        fused = fusion.fuse(
            result_lists=[source_a, source_b],
            weights=[1.0, 0.0],
            source_names=["a", "b"],
        )

        d1 = next(r for r in fused if r.doc_id == "d1")
        d2 = next(r for r in fused if r.doc_id == "d2")

        assert d1.rrf_score > 0
        assert d2.rrf_score == 0.0

    def test_default_weights_all_equal(self, fusion):
        """기본 가중치는 모든 소스에 1.0"""
        source_a = [{"doc_id": "d1", "content": "c", "metadata": {}}]
        source_b = [{"doc_id": "d2", "content": "c", "metadata": {}}]
        source_c = [{"doc_id": "d3", "content": "c", "metadata": {}}]

        fused = fusion.fuse(
            result_lists=[source_a, source_b, source_c],
            source_names=["a", "b", "c"],
        )

        # 모든 결과가 동일한 점수 (각각 rank 0, weight 1.0)
        assert fused[0].rrf_score == fused[1].rrf_score == fused[2].rrf_score

    def test_extreme_weight_ratio(self, fusion):
        """극단적 가중치 비율"""
        source_a = [{"doc_id": "d1", "content": "c", "metadata": {}}]
        source_b = [{"doc_id": "d2", "content": "c", "metadata": {}}]

        fused = fusion.fuse(
            result_lists=[source_a, source_b],
            weights=[100.0, 0.01],
            source_names=["a", "b"],
        )

        d1 = next(r for r in fused if r.doc_id == "d1")
        d2 = next(r for r in fused if r.doc_id == "d2")

        assert d1.rrf_score > d2.rrf_score * 100  # 큰 비율 차이


# ---------------------------------------------------------------------------
# 6. 중복 문서 처리 테스트
# ---------------------------------------------------------------------------


class TestDuplicateHandling:
    """중복 문서 처리 테스트"""

    def test_overlapping_docs_deduplication(self, fusion):
        """중복 문서는 하나로 합산"""
        es_results, neo4j_results = _make_overlapping_results()

        fused = fusion.fuse(
            result_lists=[es_results, neo4j_results],
            source_names=["es", "neo4j"],
        )

        doc_ids = [r.doc_id for r in fused]
        assert len(doc_ids) == len(set(doc_ids)), "Duplicate doc_ids in results"

        # 6개 고유 문서: shared-1, es-only-1, shared-2, es-only-2,
        #                neo4j-only-1, neo4j-only-2
        assert len(fused) == 6

    def test_shared_docs_ranked_higher(self, fusion):
        """양쪽 모두에 있는 문서가 더 높은 순위"""
        es_results, neo4j_results = _make_overlapping_results()

        fused = fusion.fuse(
            result_lists=[es_results, neo4j_results],
            source_names=["es", "neo4j"],
        )

        # shared-1과 shared-2가 상위에 위치해야 함
        shared_1 = next(r for r in fused if r.doc_id == "shared-1")
        shared_2 = next(r for r in fused if r.doc_id == "shared-2")
        es_only = next(r for r in fused if r.doc_id == "es-only-2")

        # 양쪽에 있는 문서는 한쪽만 있는 문서보다 점수가 높음
        assert shared_1.rrf_score > es_only.rrf_score
        assert shared_2.rrf_score > es_only.rrf_score

    def test_shared_doc_source_scores(self, fusion):
        """공유 문서의 소스별 점수 확인"""
        es_results, neo4j_results = _make_overlapping_results()

        fused = fusion.fuse(
            result_lists=[es_results, neo4j_results],
            source_names=["es", "neo4j"],
        )

        shared_1 = next(r for r in fused if r.doc_id == "shared-1")

        # shared-1: ES rank=0, Neo4j rank=2
        assert "es" in shared_1.source_scores
        assert "neo4j" in shared_1.source_scores

        # ES rank 0: 1/(60+0+1) = 1/61
        assert abs(shared_1.source_scores["es"] - round(1.0 / 61, 6)) < 1e-5
        # Neo4j rank 2: 1/(60+2+1) = 1/63
        assert abs(shared_1.source_scores["neo4j"] - round(1.0 / 63, 6)) < 1e-5

    def test_first_occurrence_content_preserved(self, fusion):
        """중복 시 첫 번째 등장의 content가 보존됨"""
        es = [{"doc_id": "shared", "content": "ES version", "metadata": {"from": "es"}}]
        neo4j = [{"doc_id": "shared", "content": "Neo4j version", "metadata": {"from": "neo4j"}}]

        fused = fusion.fuse(
            result_lists=[es, neo4j],
            source_names=["es", "neo4j"],
        )

        assert fused[0].content == "ES version"
        assert fused[0].metadata["from"] == "es"


# ---------------------------------------------------------------------------
# 7. 빈 결과 및 엣지 케이스 테스트
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """빈 결과 및 엣지 케이스 테스트"""

    def test_all_empty_lists(self, fusion):
        """모든 소스가 빈 리스트"""
        fused = fusion.fuse(
            result_lists=[[], []],
            source_names=["es", "neo4j"],
        )

        assert fused == []

    def test_one_empty_one_nonempty(self, fusion):
        """한 소스만 결과 있음"""
        es = [{"doc_id": "d1", "content": "c", "metadata": {}}]

        fused = fusion.fuse(
            result_lists=[es, []],
            source_names=["es", "neo4j"],
        )

        assert len(fused) == 1
        assert fused[0].doc_id == "d1"

    def test_single_result_single_source(self, fusion):
        """단일 소스, 단일 결과"""
        results = [{"doc_id": "only", "content": "c", "metadata": {}}]

        fused = fusion.fuse(
            result_lists=[results],
            source_names=["single"],
        )

        assert len(fused) == 1
        assert fused[0].doc_id == "only"

    def test_three_sources(self, fusion):
        """3개 소스 융합"""
        s1 = [{"doc_id": "d1", "content": "c1", "metadata": {}}]
        s2 = [{"doc_id": "d1", "content": "c1", "metadata": {}}]
        s3 = [{"doc_id": "d1", "content": "c1", "metadata": {}}]

        fused = fusion.fuse(
            result_lists=[s1, s2, s3],
            weights=[0.5, 0.3, 0.2],
            source_names=["vector", "keyword", "graph"],
        )

        assert len(fused) == 1
        # d1: 0.5/61 + 0.3/61 + 0.2/61 = 1.0/61
        expected = round(1.0 / 61, 6)
        assert fused[0].rrf_score == expected

    def test_result_without_content(self, fusion):
        """content가 없는 결과"""
        results = [{"doc_id": "no-content", "metadata": {}}]

        fused = fusion.fuse(result_lists=[results], source_names=["s"])

        assert fused[0].content == ""

    def test_result_without_metadata(self, fusion):
        """metadata가 없는 결과"""
        results = [{"doc_id": "no-meta", "content": "c"}]

        fused = fusion.fuse(result_lists=[results], source_names=["s"])

        assert fused[0].metadata == {}

    def test_result_with_no_doc_id_skipped(self, fusion):
        """doc_id가 없는 결과는 건너뜀"""
        results = [
            {"content": "no id", "metadata": {}},  # doc_id 없음
            {"doc_id": "valid", "content": "valid", "metadata": {}},
        ]

        fused = fusion.fuse(result_lists=[results], source_names=["s"])

        assert len(fused) == 1
        assert fused[0].doc_id == "valid"

    def test_large_result_set(self, fusion):
        """대규모 결과 세트 (100개 x 3소스)"""
        s1 = [{"doc_id": f"s1-{i}", "content": f"c{i}", "metadata": {}} for i in range(100)]
        s2 = [{"doc_id": f"s2-{i}", "content": f"c{i}", "metadata": {}} for i in range(100)]
        s3 = [{"doc_id": f"s3-{i}", "content": f"c{i}", "metadata": {}} for i in range(100)]

        fused = fusion.fuse(
            result_lists=[s1, s2, s3],
            source_names=["a", "b", "c"],
        )

        assert len(fused) == 300  # 모두 고유

        # 정렬 검증
        for i in range(len(fused) - 1):
            assert fused[i].rrf_score >= fused[i + 1].rrf_score

    def test_auto_source_names(self, fusion):
        """source_names 미지정 시 자동 생성"""
        results_a = [{"doc_id": "d1", "content": "c", "metadata": {}}]
        results_b = [{"doc_id": "d1", "content": "c", "metadata": {}}]

        fused = fusion.fuse(result_lists=[results_a, results_b])

        # 자동 이름: source_0, source_1
        assert "source_0" in fused[0].source_scores
        assert "source_1" in fused[0].source_scores


# ---------------------------------------------------------------------------
# 8. fuse_with_explanation 테스트
# ---------------------------------------------------------------------------


class TestFuseWithExplanation:
    """fuse_with_explanation 메서드 테스트"""

    def test_explanation_returns_correct_type(self, fusion):
        """반환 타입 검증"""
        results = [{"doc_id": "d1", "content": "c", "metadata": {}}]

        explanation = fusion.fuse_with_explanation(
            result_lists=[results],
            source_names=["s1"],
        )

        assert isinstance(explanation, RRFFusionExplanation)

    def test_explanation_contains_results(self, fusion):
        """설명에 결과가 포함"""
        es = [{"doc_id": "d1", "content": "c", "metadata": {}}]
        neo4j = [{"doc_id": "d1", "content": "c", "metadata": {}}]

        explanation = fusion.fuse_with_explanation(
            result_lists=[es, neo4j],
            weights=[0.6, 0.4],
            source_names=["es", "neo4j"],
        )

        assert len(explanation.results) == 1
        assert explanation.results[0].doc_id == "d1"

    def test_explanation_k_and_weights(self, fusion):
        """설명의 k, weights 정보"""
        explanation = fusion.fuse_with_explanation(
            result_lists=[[], []],
            weights=[0.6, 0.4],
            source_names=["es", "neo4j"],
        )

        assert explanation.k == 60
        assert explanation.weights == {"es": 0.6, "neo4j": 0.4}

    def test_explanation_source_counts(self, fusion):
        """설명의 소스별 결과 수"""
        es = _make_es_results(15)
        neo4j = _make_neo4j_results(10)

        explanation = fusion.fuse_with_explanation(
            result_lists=[es, neo4j],
            source_names=["es", "neo4j"],
        )

        assert explanation.source_counts == {"es": 15, "neo4j": 10}
        assert explanation.total_unique == 25

    def test_explanation_fusion_details(self, fusion):
        """설명의 fusion_details 상세 정보"""
        es = [
            {"doc_id": "shared", "content": "c", "metadata": {}},
            {"doc_id": "es-only", "content": "c", "metadata": {}},
        ]
        neo4j = [
            {"doc_id": "neo4j-only", "content": "c", "metadata": {}},
            {"doc_id": "shared", "content": "c", "metadata": {}},
        ]

        explanation = fusion.fuse_with_explanation(
            result_lists=[es, neo4j],
            weights=[0.6, 0.4],
            source_names=["es", "neo4j"],
        )

        assert len(explanation.fusion_details) == 3

        # shared 문서의 상세 정보 확인
        shared_detail = next(
            d for d in explanation.fusion_details if d["doc_id"] == "shared"
        )
        assert shared_detail["num_sources"] == 2
        assert "es" in shared_detail["source_contributions"]
        assert "neo4j" in shared_detail["source_contributions"]

        es_contrib = shared_detail["source_contributions"]["es"]
        assert es_contrib["rank"] == 0
        assert es_contrib["weight"] == 0.6
        assert abs(es_contrib["raw_rrf_score"] - round(1.0 / 61, 6)) < 1e-5
        assert abs(es_contrib["weighted_rrf_score"] - round(0.6 / 61, 6)) < 1e-5

    def test_explanation_matches_fuse_results(self, fusion):
        """fuse_with_explanation 결과가 fuse 결과와 동일"""
        es = _make_es_results(10)
        neo4j = _make_neo4j_results(10)

        fused = fusion.fuse(
            result_lists=[es, neo4j],
            weights=[0.6, 0.4],
            source_names=["es", "neo4j"],
        )

        explanation = fusion.fuse_with_explanation(
            result_lists=[es, neo4j],
            weights=[0.6, 0.4],
            source_names=["es", "neo4j"],
        )

        assert len(fused) == len(explanation.results)

        for f_result, e_result in zip(fused, explanation.results):
            assert f_result.doc_id == e_result.doc_id
            assert f_result.rrf_score == e_result.rrf_score


# ---------------------------------------------------------------------------
# 9. SearchResult 호환 테스트
# ---------------------------------------------------------------------------


class TestSearchResultCompat:
    """SearchResult 객체 호환 테스트 (fuse_search_results)"""

    def _make_search_result(
        self,
        chunk_id: str,
        content: str = "test",
        score: float = 0.9,
        source: str = "vector",
        document_id: str = "doc-1",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """테스트용 SearchResult 생성"""
        from app.agents.state import SearchResult

        return SearchResult(
            chunk_id=chunk_id,
            document_id=document_id,
            content=content,
            score=score,
            source=source,
            metadata=metadata or {},
        )

    def test_fuse_search_results_basic(self, fusion):
        """기본 SearchResult 융합"""
        es = [
            self._make_search_result("chunk-1", source="vector"),
            self._make_search_result("chunk-2", source="vector"),
        ]
        neo4j = [
            self._make_search_result("chunk-2", source="graph"),
            self._make_search_result("chunk-3", source="graph"),
        ]

        fused = fusion.fuse_search_results(
            result_lists=[es, neo4j],
            weights=[0.6, 0.4],
            source_names=["es", "neo4j"],
        )

        assert len(fused) == 3

        # chunk-2가 양쪽에 있으므로 최상위
        assert fused[0].chunk_id == "chunk-2"

        # 메타데이터에 rrf 정보 추가 확인
        assert "rrf_score" in fused[0].metadata
        assert "source_ranks" in fused[0].metadata
        assert "source_scores" in fused[0].metadata

    def test_fuse_search_results_weighted(self, fusion):
        """가중치 적용 SearchResult 융합"""
        es = [self._make_search_result("chunk-1", source="vector")]
        neo4j = [self._make_search_result("chunk-2", source="graph")]

        fused = fusion.fuse_search_results(
            result_lists=[es, neo4j],
            weights=[0.6, 0.4],
            source_names=["es", "neo4j"],
        )

        c1 = next(r for r in fused if r.chunk_id == "chunk-1")
        c2 = next(r for r in fused if r.chunk_id == "chunk-2")

        # ES weight=0.6 > Neo4j weight=0.4
        assert c1.score > c2.score

    def test_fuse_search_results_empty(self, fusion):
        """빈 SearchResult 리스트"""
        fused = fusion.fuse_search_results(result_lists=[])

        assert fused == []

    def test_fuse_search_results_source_ranks(self, fusion):
        """source_ranks 메타데이터 확인"""
        es = [
            self._make_search_result("shared", source="vector"),
        ]
        neo4j = [
            self._make_search_result("neo-only", source="graph"),
            self._make_search_result("shared", source="graph"),
        ]

        fused = fusion.fuse_search_results(
            result_lists=[es, neo4j],
            source_names=["es", "neo4j"],
        )

        shared = next(r for r in fused if r.chunk_id == "shared")

        # ES에서 rank 1, Neo4j에서 rank 2 (1-based)
        assert shared.metadata["source_ranks"]["es"] == 1
        assert shared.metadata["source_ranks"]["neo4j"] == 2


# ---------------------------------------------------------------------------
# 10. 싱글톤 팩토리 테스트
# ---------------------------------------------------------------------------


class TestSingletonFactory:
    """get_rrf_fusion / reset_rrf_fusion 테스트"""

    def setup_method(self):
        """각 테스트 전 싱글톤 초기화"""
        reset_rrf_fusion()

    def teardown_method(self):
        """각 테스트 후 싱글톤 초기화"""
        reset_rrf_fusion()

    def test_get_creates_singleton(self):
        """싱글톤 인스턴스 생성"""
        f1 = get_rrf_fusion()
        f2 = get_rrf_fusion()
        assert f1 is f2

    def test_get_with_custom_k(self):
        """사용자 지정 k로 싱글톤 생성"""
        f = get_rrf_fusion(k=100)
        assert f.k == 100

    def test_reset_clears_singleton(self):
        """싱글톤 초기화"""
        f1 = get_rrf_fusion()
        reset_rrf_fusion()
        f2 = get_rrf_fusion()
        assert f1 is not f2

    def test_default_k_is_60(self):
        """기본 k 값은 60"""
        f = get_rrf_fusion()
        assert f.k == 60


# ---------------------------------------------------------------------------
# 11. 통합 시나리오 테스트
# ---------------------------------------------------------------------------


class TestIntegrationScenarios:
    """실제 사용 시나리오 테스트"""

    def test_realistic_hybrid_search_scenario(self):
        """
        실제 Hybrid Search 시나리오

        ES(Vector) 20개 + Neo4j(Graph) 20개, 5개 중복
        가중치: es=0.6, neo4j=0.4
        """
        fusion = RRFFusion(k=60)

        # ES 결과 (20개, 일부 공유 ID)
        es_results = []
        for i in range(20):
            if i < 5:
                doc_id = f"shared-{i}"  # 처음 5개는 공유
            else:
                doc_id = f"es-{i}"
            es_results.append({
                "doc_id": doc_id,
                "content": f"ES content for {doc_id}",
                "metadata": {"source": "es", "rank": i},
            })

        # Neo4j 결과 (20개, 일부 공유 ID)
        neo4j_results = []
        for i in range(20):
            if i < 5:
                # Neo4j에서는 역순으로 공유 (다양한 rank 조합)
                doc_id = f"shared-{4 - i}"
            else:
                doc_id = f"neo4j-{i}"
            neo4j_results.append({
                "doc_id": doc_id,
                "content": f"Neo4j content for {doc_id}",
                "metadata": {"source": "neo4j", "rank": i},
            })

        results = fusion.fuse(
            result_lists=[es_results, neo4j_results],
            weights=[0.6, 0.4],
            source_names=["es", "neo4j"],
        )

        # 총 35개 고유 문서 (20 + 20 - 5 중복)
        assert len(results) == 35

        # 정렬 검증
        for i in range(len(results) - 1):
            assert results[i].rrf_score >= results[i + 1].rrf_score

        # 공유 문서가 상위에 위치 (양쪽 점수 합산)
        top_5_ids = {r.doc_id for r in results[:5]}
        shared_ids = {f"shared-{i}" for i in range(5)}

        # 최소 3개 이상의 공유 문서가 상위 5개에 포함
        overlap = top_5_ids & shared_ids
        assert len(overlap) >= 3, (
            f"Expected at least 3 shared docs in top 5, got {len(overlap)}: "
            f"top_5={top_5_ids}, shared={shared_ids}"
        )

    def test_three_source_vip_pipeline(self):
        """
        VIP 3단계 파이프라인: Vector + Keyword + Graph

        가중치: vector=0.4, keyword=0.3, graph=0.3
        """
        fusion = RRFFusion(k=60)

        vector = [
            {"doc_id": f"v-{i}", "content": f"Vector {i}", "metadata": {}}
            for i in range(10)
        ]
        keyword = [
            {"doc_id": f"k-{i}", "content": f"Keyword {i}", "metadata": {}}
            for i in range(10)
        ]
        graph = [
            {"doc_id": f"g-{i}", "content": f"Graph {i}", "metadata": {}}
            for i in range(10)
        ]

        # 일부 공유: v-0 = k-5, k-0 = g-5
        vector[0] = {"doc_id": "shared-vk", "content": "VK", "metadata": {}}
        keyword[5] = {"doc_id": "shared-vk", "content": "VK", "metadata": {}}
        keyword[0] = {"doc_id": "shared-kg", "content": "KG", "metadata": {}}
        graph[5] = {"doc_id": "shared-kg", "content": "KG", "metadata": {}}

        results = fusion.fuse(
            result_lists=[vector, keyword, graph],
            weights=[0.4, 0.3, 0.3],
            source_names=["vector", "keyword", "graph"],
        )

        # 28개 고유 (30 - 2 공유)
        assert len(results) == 28

        # 정렬 검증
        for i in range(len(results) - 1):
            assert results[i].rrf_score >= results[i + 1].rrf_score

        # 공유 문서가 상위에 위치
        shared_vk = next(r for r in results if r.doc_id == "shared-vk")
        shared_kg = next(r for r in results if r.doc_id == "shared-kg")

        assert "vector" in shared_vk.source_scores
        assert "keyword" in shared_vk.source_scores
        assert "keyword" in shared_kg.source_scores
        assert "graph" in shared_kg.source_scores
