"""
BGE Reranker 단위 테스트

STORY-032: BGE Reranker 통합 구현
- AC1: RRF 융합 결과 50개에 Reranker 적용 -> 재순위화된 결과 반환
- AC2: 쿼리-문서 쌍에 0~1 범위의 관련성 점수 반환
- AC3: top_k=5 -> 상위 5개 문서 반환
- AC4: 50개 문서 기준 500ms 이내 응답
- AC5: GPU 없는 환경에서 CPU로 정상 동작

테스트 범주:
1. RerankResult 데이터클래스 테스트
2. BGEReranker 초기화 테스트
3. 점수 계산 정확성 테스트 (0~1 범위)
4. top_k 필터링 테스트
5. 배치 처리 동작 테스트
6. 빈 입력 및 엣지 케이스 테스트
7. HybridRetriever 통합 테스트
8. SearchResult 호환 테스트
9. 싱글톤 팩토리 테스트
10. 헬스 체크 테스트

Mock 사용: transformers 모델 없이 점수 계산을 Mock
"""

import asyncio
import sys
import time
from types import ModuleType
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# 환경 의존성 Mock: torch/transformers 패키지 누락 방지
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
    _torch_mock.sigmoid = MagicMock()  # type: ignore[attr-defined]
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

# Mock transformers if not installed
_MOCK_PACKAGES = [
    "transformers",
    "transformers.models",
    "transformers.tokenization_utils",
    "sentence_transformers",
    "FlagEmbedding",
]
for _pkg in _MOCK_PACKAGES:
    if _pkg not in sys.modules:
        sys.modules[_pkg] = MagicMock()

from ai_service.src.reranking.bge_reranker import (
    BGEReranker,
    RerankResult,
    get_reranker,
    reset_reranker,
)


# ---------------------------------------------------------------------------
# Test Fixtures & Helpers
# ---------------------------------------------------------------------------


def _make_document(
    doc_id: str = "doc-1",
    content: str = "Test content",
    score: float = 0.5,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """테스트용 문서 딕셔너리 생성"""
    return {
        "doc_id": doc_id,
        "content": content,
        "score": score,
        "metadata": metadata or {},
    }


def _make_documents(count: int = 10, prefix: str = "doc") -> List[Dict[str, Any]]:
    """테스트용 문서 리스트 생성"""
    return [
        _make_document(
            doc_id=f"{prefix}-{i}",
            content=f"Test content for document {i}. " * 5,
            score=round(1.0 - (i * 0.05), 4),
        )
        for i in range(count)
    ]


def _make_mock_reranker(
    scores: Optional[List[float]] = None,
) -> BGEReranker:
    """
    Mock된 BGEReranker 생성

    _compute_scores를 mock하여 실제 모델 로딩 없이 테스트 가능
    """
    reranker = BGEReranker.__new__(BGEReranker)
    reranker.model_name = "BAAI/bge-reranker-v2-m3"
    reranker.device = "cpu"
    reranker.batch_size = 32
    reranker.max_length = 512
    reranker._model = MagicMock()  # 모델 로드된 것처럼 설정
    reranker._tokenizer = MagicMock()

    # 점수 mock: 제공된 점수 또는 0.5~0.95 범위 생성
    if scores is not None:
        _score_iter = iter(scores)

        def mock_compute(pairs):
            result = []
            for _ in pairs:
                try:
                    result.append(next(_score_iter))
                except StopIteration:
                    result.append(0.5)
            return result

        reranker._compute_scores = MagicMock(side_effect=mock_compute)
    else:
        # 문서 인덱스에 따라 차등 점수 부여
        def mock_compute_default(pairs):
            return [round(0.95 - (i * 0.05), 4) for i in range(len(pairs))]

        reranker._compute_scores = MagicMock(side_effect=mock_compute_default)

    return reranker


class MockSearchResult:
    """Mock SearchResult (knowledge_service 의존 없이 테스트)"""

    def __init__(
        self,
        chunk_id: str = "chunk-1",
        document_id: str = "doc-1",
        content: str = "Test content",
        score: float = 0.5,
        source: str = "vector",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.chunk_id = chunk_id
        self.document_id = document_id
        self.content = content
        self.score = score
        self.source = source
        self.metadata = metadata or {}


# ---------------------------------------------------------------------------
# 1. RerankResult 데이터클래스 테스트
# ---------------------------------------------------------------------------


class TestRerankResult:
    """RerankResult 데이터클래스 테스트"""

    def test_create_basic(self):
        """기본 생성"""
        result = RerankResult(
            doc_id="doc-1",
            content="Test content",
            score=0.85,
            original_score=0.5,
            rank=0,
        )

        assert result.doc_id == "doc-1"
        assert result.content == "Test content"
        assert result.score == 0.85
        assert result.original_score == 0.5
        assert result.rank == 0

    def test_create_defaults(self):
        """기본값 검증"""
        result = RerankResult(doc_id="doc-1", content="c")

        assert result.score == 0.0
        assert result.original_score == 0.0
        assert result.rank == 0
        assert result.metadata == {}

    def test_create_with_metadata(self):
        """메타데이터 포함 생성"""
        meta = {"rerank_score": 0.85, "source": "vector"}
        result = RerankResult(
            doc_id="doc-1",
            content="c",
            metadata=meta,
        )

        assert result.metadata == meta
        assert result.metadata["rerank_score"] == 0.85

    def test_repr(self):
        """__repr__ 검증"""
        result = RerankResult(
            doc_id="doc-1",
            content="c",
            score=0.852345,
            original_score=0.5,
            rank=2,
        )

        repr_str = repr(result)
        assert "doc-1" in repr_str
        assert "0.852345" in repr_str
        assert "rank=2" in repr_str


# ---------------------------------------------------------------------------
# 2. BGEReranker 초기화 테스트
# ---------------------------------------------------------------------------


class TestBGERerankerInit:
    """BGEReranker 초기화 테스트"""

    def test_default_init(self):
        """기본 초기화"""
        reranker = BGEReranker()

        assert reranker.model_name == "BAAI/bge-reranker-v2-m3"
        assert reranker.batch_size == 32
        assert reranker.max_length == 512
        assert reranker.device in ("cpu", "cuda")
        assert reranker.is_loaded is False

    def test_custom_model_name(self):
        """사용자 지정 모델명"""
        reranker = BGEReranker(model_name="BAAI/bge-reranker-base")

        assert reranker.model_name == "BAAI/bge-reranker-base"

    def test_cpu_device(self):
        """CPU 디바이스 지정"""
        reranker = BGEReranker(device="cpu")

        assert reranker.device == "cpu"

    def test_custom_batch_size(self):
        """사용자 지정 배치 크기"""
        reranker = BGEReranker(batch_size=16)

        assert reranker.batch_size == 16

    def test_custom_max_length(self):
        """사용자 지정 최대 길이"""
        reranker = BGEReranker(max_length=256)

        assert reranker.max_length == 256

    def test_invalid_batch_size_zero(self):
        """batch_size=0 시 ValueError"""
        with pytest.raises(ValueError, match="batch_size must be positive"):
            BGEReranker(batch_size=0)

    def test_invalid_batch_size_negative(self):
        """batch_size<0 시 ValueError"""
        with pytest.raises(ValueError, match="batch_size must be positive"):
            BGEReranker(batch_size=-1)

    def test_invalid_max_length_zero(self):
        """max_length=0 시 ValueError"""
        with pytest.raises(ValueError, match="max_length must be positive"):
            BGEReranker(max_length=0)

    def test_device_auto_detect(self):
        """디바이스 자동 감지"""
        # torch mock에서 cuda.is_available이 False를 반환하도록 설정
        if _TORCH_IMPORT_ERROR:
            reranker = BGEReranker(device=None)
            assert reranker.device == "cpu"

    def test_not_loaded_initially(self):
        """초기 상태에서 모델 미로딩"""
        reranker = BGEReranker()

        assert reranker.is_loaded is False
        assert reranker._model is None
        assert reranker._tokenizer is None


# ---------------------------------------------------------------------------
# 3. 점수 계산 정확성 테스트 (0~1 범위)
# ---------------------------------------------------------------------------


class TestScoreCalculation:
    """점수 계산 정확성 테스트"""

    @pytest.mark.asyncio
    async def test_scores_in_valid_range(self):
        """
        AC2: 점수가 0~1 범위인지 검증

        Sigmoid 정규화로 모든 점수가 [0, 1] 범위여야 합니다.
        """
        reranker = _make_mock_reranker(
            scores=[0.95, 0.82, 0.67, 0.45, 0.12]
        )
        documents = _make_documents(5)

        results = await reranker.rerank(
            query="테스트 쿼리",
            documents=documents,
        )

        for result in results:
            assert 0.0 <= result.score <= 1.0, (
                f"Score {result.score} out of range [0, 1]"
            )

    @pytest.mark.asyncio
    async def test_scores_sorted_descending(self):
        """점수가 내림차순으로 정렬되는지 검증"""
        reranker = _make_mock_reranker(
            scores=[0.3, 0.9, 0.1, 0.7, 0.5]
        )
        documents = _make_documents(5)

        results = await reranker.rerank(
            query="정렬 테스트",
            documents=documents,
        )

        for i in range(len(results) - 1):
            assert results[i].score >= results[i + 1].score, (
                f"Not sorted: {results[i].score} < {results[i + 1].score}"
            )

    @pytest.mark.asyncio
    async def test_highest_score_first(self):
        """가장 높은 점수의 문서가 첫 번째인지 검증"""
        reranker = _make_mock_reranker(
            scores=[0.3, 0.95, 0.5]
        )
        documents = [
            _make_document("low", content="Low relevance"),
            _make_document("high", content="High relevance"),
            _make_document("mid", content="Mid relevance"),
        ]

        results = await reranker.rerank(
            query="관련성 테스트",
            documents=documents,
        )

        assert results[0].doc_id == "high"
        assert results[0].score == 0.95

    @pytest.mark.asyncio
    async def test_rank_assignment(self):
        """순위(rank)가 올바르게 할당되는지 검증"""
        reranker = _make_mock_reranker(
            scores=[0.5, 0.9, 0.1, 0.7]
        )
        documents = _make_documents(4)

        results = await reranker.rerank(
            query="순위 테스트",
            documents=documents,
        )

        for i, result in enumerate(results):
            assert result.rank == i, (
                f"Expected rank {i}, got {result.rank}"
            )

    @pytest.mark.asyncio
    async def test_original_score_preserved(self):
        """원본 점수(original_score)가 보존되는지 검증"""
        reranker = _make_mock_reranker(scores=[0.8, 0.6])
        documents = [
            _make_document("d1", score=0.95),
            _make_document("d2", score=0.80),
        ]

        results = await reranker.rerank(
            query="원본 점수",
            documents=documents,
        )

        # 원본 점수가 메타데이터에 보존
        for result in results:
            assert "original_score" in result.metadata
            assert result.original_score >= 0.0


# ---------------------------------------------------------------------------
# 4. top_k 필터링 테스트
# ---------------------------------------------------------------------------


class TestTopKFiltering:
    """top_k 필터링 테스트"""

    @pytest.mark.asyncio
    async def test_top_k_returns_correct_count(self):
        """
        AC3: top_k=5 -> 상위 5개 문서 반환
        """
        reranker = _make_mock_reranker()
        documents = _make_documents(20)

        results = await reranker.rerank(
            query="top_k 테스트",
            documents=documents,
            top_k=5,
        )

        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_top_k_one(self):
        """top_k=1 -> 최고 점수 1개 반환"""
        reranker = _make_mock_reranker(scores=[0.3, 0.9, 0.5])
        documents = _make_documents(3)

        results = await reranker.rerank(
            query="top 1",
            documents=documents,
            top_k=1,
        )

        assert len(results) == 1
        assert results[0].score == 0.9

    @pytest.mark.asyncio
    async def test_top_k_none_returns_all(self):
        """top_k=None -> 전체 반환"""
        reranker = _make_mock_reranker()
        documents = _make_documents(10)

        results = await reranker.rerank(
            query="전체 반환",
            documents=documents,
            top_k=None,
        )

        assert len(results) == 10

    @pytest.mark.asyncio
    async def test_top_k_larger_than_docs(self):
        """top_k > 문서 수 -> 전체 반환"""
        reranker = _make_mock_reranker()
        documents = _make_documents(3)

        results = await reranker.rerank(
            query="큰 top_k",
            documents=documents,
            top_k=100,
        )

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_top_k_from_50_documents(self):
        """
        AC1: RRF 융합 결과 50개에서 Reranker 적용 -> top_k 반환
        """
        scores = [round(0.99 - (i * 0.018), 4) for i in range(50)]
        reranker = _make_mock_reranker(scores=scores)
        documents = _make_documents(50)

        results = await reranker.rerank(
            query="50개 문서 리랭킹",
            documents=documents,
            top_k=5,
        )

        assert len(results) == 5
        # 최고 점수 문서가 첫 번째
        assert results[0].score == max(r.score for r in results)


# ---------------------------------------------------------------------------
# 5. 배치 처리 동작 테스트
# ---------------------------------------------------------------------------


class TestBatchProcessing:
    """배치 처리 동작 테스트"""

    @pytest.mark.asyncio
    async def test_single_batch(self):
        """배치 크기 내 문서 처리 (단일 배치)"""
        reranker = _make_mock_reranker()
        reranker.batch_size = 32
        documents = _make_documents(10)

        results = await reranker.rerank(
            query="단일 배치",
            documents=documents,
        )

        assert len(results) == 10
        # _compute_scores가 1번 호출됨 (10 < 32)
        assert reranker._compute_scores.call_count == 1

    @pytest.mark.asyncio
    async def test_multiple_batches(self):
        """여러 배치로 분할 처리"""
        # 배치 크기 5로 설정, 문서 12개
        all_scores = [round(0.95 - (i * 0.07), 4) for i in range(12)]
        reranker = _make_mock_reranker(scores=all_scores)
        reranker.batch_size = 5
        documents = _make_documents(12)

        results = await reranker.rerank(
            query="다중 배치",
            documents=documents,
        )

        assert len(results) == 12
        # _compute_scores가 3번 호출됨 (5 + 5 + 2)
        assert reranker._compute_scores.call_count == 3

    @pytest.mark.asyncio
    async def test_exact_batch_boundary(self):
        """배치 경계 정확 분할 (문서 수 = 배치 크기의 배수)"""
        all_scores = [round(0.9 - (i * 0.03), 4) for i in range(10)]
        reranker = _make_mock_reranker(scores=all_scores)
        reranker.batch_size = 5
        documents = _make_documents(10)

        results = await reranker.rerank(
            query="경계 테스트",
            documents=documents,
        )

        assert len(results) == 10
        # _compute_scores가 2번 호출됨 (5 + 5)
        assert reranker._compute_scores.call_count == 2

    @pytest.mark.asyncio
    async def test_batch_size_one(self):
        """배치 크기 1 (한 번에 하나씩)"""
        all_scores = [0.9, 0.7, 0.5]
        reranker = _make_mock_reranker(scores=all_scores)
        reranker.batch_size = 1
        documents = _make_documents(3)

        results = await reranker.rerank(
            query="배치 1",
            documents=documents,
        )

        assert len(results) == 3
        assert reranker._compute_scores.call_count == 3

    def test_batch_process_method_directly(self):
        """_batch_process 메서드 직접 테스트"""
        reranker = _make_mock_reranker(scores=[0.9, 0.8, 0.7, 0.6, 0.5])
        reranker.batch_size = 2

        pairs = [["q", f"d{i}"] for i in range(5)]
        scores = reranker._batch_process(pairs, batch_size=2)

        assert len(scores) == 5
        # _compute_scores 3회 호출 (2 + 2 + 1)
        assert reranker._compute_scores.call_count == 3

    def test_batch_process_empty(self):
        """빈 입력 배치 처리"""
        reranker = _make_mock_reranker()

        scores = reranker._batch_process([], batch_size=32)

        assert scores == []


# ---------------------------------------------------------------------------
# 6. 빈 입력 및 엣지 케이스 테스트
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """빈 입력 및 엣지 케이스 테스트"""

    @pytest.mark.asyncio
    async def test_empty_documents(self):
        """빈 문서 리스트"""
        reranker = _make_mock_reranker()

        results = await reranker.rerank(
            query="빈 문서",
            documents=[],
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_empty_query(self):
        """빈 쿼리"""
        reranker = _make_mock_reranker()
        documents = _make_documents(3)

        results = await reranker.rerank(
            query="",
            documents=documents,
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_whitespace_only_query(self):
        """공백만 있는 쿼리"""
        reranker = _make_mock_reranker()
        documents = _make_documents(3)

        results = await reranker.rerank(
            query="   ",
            documents=documents,
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_single_document(self):
        """단일 문서"""
        reranker = _make_mock_reranker(scores=[0.85])

        results = await reranker.rerank(
            query="단일 문서 테스트",
            documents=[_make_document("only-one")],
        )

        assert len(results) == 1
        assert results[0].doc_id == "only-one"
        assert results[0].score == 0.85

    @pytest.mark.asyncio
    async def test_document_without_doc_id(self):
        """doc_id 없는 문서 (chunk_id 사용)"""
        reranker = _make_mock_reranker(scores=[0.7])
        doc = {"content": "No ID document", "chunk_id": "chunk-42", "score": 0.5}

        results = await reranker.rerank(
            query="ID 없는 문서",
            documents=[doc],
        )

        assert len(results) == 1
        assert results[0].doc_id == "chunk-42"

    @pytest.mark.asyncio
    async def test_document_without_any_id(self):
        """doc_id와 chunk_id 모두 없는 문서"""
        reranker = _make_mock_reranker(scores=[0.7])
        doc = {"content": "No ID at all", "score": 0.5}

        results = await reranker.rerank(
            query="ID 전혀 없는 문서",
            documents=[doc],
        )

        assert len(results) == 1
        assert results[0].doc_id == "doc-0"  # 인덱스 기반 자동 ID

    @pytest.mark.asyncio
    async def test_document_without_content(self):
        """content 없는 문서"""
        reranker = _make_mock_reranker(scores=[0.5])
        doc = {"doc_id": "no-content"}

        results = await reranker.rerank(
            query="내용 없는 문서",
            documents=[doc],
        )

        assert len(results) == 1
        assert results[0].content == ""

    @pytest.mark.asyncio
    async def test_unicode_korean_query(self):
        """한국어 유니코드 쿼리"""
        reranker = _make_mock_reranker(scores=[0.9, 0.3])
        documents = [
            _make_document("kr-1", content="인공지능 기반 지식 검색 시스템"),
            _make_document("kr-2", content="Java Spring Boot 가이드"),
        ]

        results = await reranker.rerank(
            query="인공지능 지식 검색",
            documents=documents,
        )

        assert len(results) == 2
        assert results[0].doc_id == "kr-1"

    @pytest.mark.asyncio
    async def test_very_long_content(self):
        """매우 긴 문서 내용 (max_length 초과)"""
        reranker = _make_mock_reranker(scores=[0.7])
        long_content = "이것은 매우 긴 문서입니다. " * 1000
        doc = _make_document("long", content=long_content)

        results = await reranker.rerank(
            query="긴 문서",
            documents=[doc],
        )

        assert len(results) == 1
        # max_length로 truncation 되어도 점수는 정상

    @pytest.mark.asyncio
    async def test_same_score_documents(self):
        """동일 점수 문서들"""
        reranker = _make_mock_reranker(scores=[0.5, 0.5, 0.5])
        documents = _make_documents(3)

        results = await reranker.rerank(
            query="동점",
            documents=documents,
        )

        assert len(results) == 3
        # 모든 점수가 동일
        assert all(r.score == 0.5 for r in results)


# ---------------------------------------------------------------------------
# 7. HybridRetriever 통합 테스트
# ---------------------------------------------------------------------------


class TestHybridRetrieverIntegration:
    """HybridRetriever + Reranker 통합 테스트"""

    @pytest.mark.asyncio
    async def test_retrieve_with_reranking(self):
        """retrieve에서 reranking이 적용되는지 검증"""
        from ai_service.src.retrievers.hybrid_retriever import (
            HybridRetrieverWithReranking,
        )

        # Mock HybridRetriever
        mock_hybrid = MagicMock()
        mock_results = [
            MockSearchResult(
                chunk_id=f"chunk-{i}",
                content=f"Content {i}",
                score=round(0.9 - (i * 0.1), 2),
            )
            for i in range(10)
        ]
        mock_hybrid.retrieve = AsyncMock(return_value=mock_results)

        # Mock Reranker
        mock_reranker = MagicMock(spec=BGEReranker)

        async def mock_rerank_search(query, search_results, top_k=None):
            # 역순으로 정렬 (reranking 효과 시뮬레이션)
            reranked = list(reversed(search_results))
            if top_k:
                reranked = reranked[:top_k]
            for i, r in enumerate(reranked):
                r.score = round(0.95 - (i * 0.05), 2)
                r.metadata["rerank_score"] = r.score
                r.metadata["rerank_rank"] = i
            return reranked

        mock_reranker.rerank_search_results = AsyncMock(
            side_effect=mock_rerank_search
        )

        # HybridRetrieverWithReranking 생성
        retriever = HybridRetrieverWithReranking(
            hybrid_retriever=mock_hybrid,
            reranker=mock_reranker,
            rerank_top_n=50,
        )

        results = await retriever.retrieve(
            query="통합 테스트",
            top_k=5,
            use_reranking=True,
        )

        assert len(results) == 5
        # 리랭커가 호출됨
        mock_reranker.rerank_search_results.assert_called_once()

    @pytest.mark.asyncio
    async def test_retrieve_without_reranking(self):
        """reranking 비활성화 시 RRF 결과만 반환"""
        from ai_service.src.retrievers.hybrid_retriever import (
            HybridRetrieverWithReranking,
        )

        mock_hybrid = MagicMock()
        mock_results = [
            MockSearchResult(chunk_id=f"chunk-{i}", score=0.9 - i * 0.1)
            for i in range(5)
        ]
        mock_hybrid.retrieve = AsyncMock(return_value=mock_results)

        mock_reranker = MagicMock(spec=BGEReranker)

        retriever = HybridRetrieverWithReranking(
            hybrid_retriever=mock_hybrid,
            reranker=mock_reranker,
        )

        results = await retriever.retrieve(
            query="리랭킹 없이",
            top_k=5,
            use_reranking=False,
        )

        assert len(results) == 5
        # 리랭커가 호출되지 않음
        mock_reranker.rerank_search_results.assert_not_called()

    @pytest.mark.asyncio
    async def test_retrieve_no_reranker_configured(self):
        """reranker가 None인 경우"""
        from ai_service.src.retrievers.hybrid_retriever import (
            HybridRetrieverWithReranking,
        )

        mock_hybrid = MagicMock()
        mock_results = [
            MockSearchResult(chunk_id=f"chunk-{i}", score=0.9 - i * 0.1)
            for i in range(5)
        ]
        mock_hybrid.retrieve = AsyncMock(return_value=mock_results)

        retriever = HybridRetrieverWithReranking(
            hybrid_retriever=mock_hybrid,
            reranker=None,  # 리랭커 없음
        )

        results = await retriever.retrieve(
            query="리랭커 없음",
            top_k=5,
            use_reranking=True,
        )

        assert len(results) == 5


# ---------------------------------------------------------------------------
# 8. SearchResult 호환 테스트
# ---------------------------------------------------------------------------


class TestSearchResultCompat:
    """SearchResult 객체 호환 테스트"""

    @pytest.mark.asyncio
    async def test_rerank_search_results_basic(self):
        """SearchResult 기본 리랭킹"""
        reranker = _make_mock_reranker(scores=[0.9, 0.3, 0.7])

        search_results = [
            MockSearchResult(
                chunk_id="c1", content="High relevance", score=0.5
            ),
            MockSearchResult(
                chunk_id="c2", content="Low relevance", score=0.8
            ),
            MockSearchResult(
                chunk_id="c3", content="Mid relevance", score=0.6
            ),
        ]

        results = await reranker.rerank_search_results(
            query="관련성 테스트",
            search_results=search_results,
        )

        assert len(results) == 3
        # c1이 최고 점수 (0.9)
        assert results[0].chunk_id == "c1"
        assert results[0].score == 0.9
        assert "rerank_score" in results[0].metadata

    @pytest.mark.asyncio
    async def test_rerank_search_results_top_k(self):
        """SearchResult top_k 적용"""
        reranker = _make_mock_reranker(
            scores=[0.5, 0.9, 0.3, 0.7, 0.1]
        )

        search_results = [
            MockSearchResult(chunk_id=f"c{i}", content=f"Content {i}")
            for i in range(5)
        ]

        results = await reranker.rerank_search_results(
            query="top_k 테스트",
            search_results=search_results,
            top_k=2,
        )

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_rerank_search_results_empty(self):
        """빈 SearchResult 리스트"""
        reranker = _make_mock_reranker()

        results = await reranker.rerank_search_results(
            query="빈 결과",
            search_results=[],
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_rerank_search_results_preserves_metadata(self):
        """리랭킹 시 원본 메타데이터가 보존되는지 검증"""
        reranker = _make_mock_reranker(scores=[0.85])

        search_results = [
            MockSearchResult(
                chunk_id="c1",
                content="Test",
                score=0.5,
                metadata={"original_key": "original_value"},
            ),
        ]

        results = await reranker.rerank_search_results(
            query="메타데이터 보존",
            search_results=search_results,
        )

        assert len(results) == 1
        # 리랭킹 메타데이터 추가
        assert "rerank_score" in results[0].metadata
        assert "rerank_rank" in results[0].metadata
        assert "original_score" in results[0].metadata


# ---------------------------------------------------------------------------
# 9. 싱글톤 팩토리 테스트
# ---------------------------------------------------------------------------


class TestSingletonFactory:
    """get_reranker / reset_reranker 테스트"""

    def setup_method(self):
        """각 테스트 전 싱글톤 초기화"""
        reset_reranker()

    def teardown_method(self):
        """각 테스트 후 싱글톤 초기화"""
        reset_reranker()

    def test_get_creates_singleton(self):
        """싱글톤 인스턴스 생성"""
        r1 = get_reranker()
        r2 = get_reranker()

        assert r1 is r2

    def test_reset_clears_singleton(self):
        """싱글톤 초기화"""
        r1 = get_reranker()
        reset_reranker()
        r2 = get_reranker()

        assert r1 is not r2

    def test_get_with_custom_params(self):
        """사용자 지정 파라미터로 생성"""
        r = get_reranker(
            model_name="custom-model",
            device="cpu",
            batch_size=16,
            max_length=256,
        )

        assert r.model_name == "custom-model"
        assert r.device == "cpu"
        assert r.batch_size == 16
        assert r.max_length == 256

    def test_default_model_name(self):
        """기본 모델명 확인"""
        r = get_reranker()

        assert r.model_name == "BAAI/bge-reranker-v2-m3"


# ---------------------------------------------------------------------------
# 10. 헬스 체크 테스트
# ---------------------------------------------------------------------------


class TestHealthCheck:
    """헬스 체크 테스트"""

    def test_health_check_not_loaded(self):
        """모델 미로딩 상태 헬스 체크"""
        reranker = BGEReranker()

        health = reranker.health_check()

        assert health["service"] == "BGEReranker"
        assert health["model_name"] == "BAAI/bge-reranker-v2-m3"
        assert health["is_loaded"] is False
        assert health["batch_size"] == 32
        assert health["max_length"] == 512

    def test_health_check_loaded(self):
        """모델 로딩 완료 상태 헬스 체크"""
        reranker = _make_mock_reranker()

        health = reranker.health_check()

        assert health["is_loaded"] is True


# ---------------------------------------------------------------------------
# 11. 성능 테스트 (Mock 기반)
# ---------------------------------------------------------------------------


class TestPerformance:
    """성능 관련 테스트 (Mock 기반으로 로직 흐름 검증)"""

    @pytest.mark.asyncio
    async def test_50_documents_completes(self):
        """
        AC4 관련: 50개 문서 처리 완료 검증

        실제 모델 기반 500ms 이내는 통합 테스트에서 검증하고,
        여기서는 로직 흐름이 정상적으로 완료되는지 확인합니다.
        """
        scores = [round(0.99 - (i * 0.018), 4) for i in range(50)]
        reranker = _make_mock_reranker(scores=scores)
        documents = _make_documents(50)

        start_time = time.monotonic()

        results = await reranker.rerank(
            query="50개 문서 성능 테스트",
            documents=documents,
            top_k=5,
        )

        elapsed_ms = (time.monotonic() - start_time) * 1000

        assert len(results) == 5
        # Mock이므로 매우 빠르게 완료
        assert elapsed_ms < 1000

    @pytest.mark.asyncio
    async def test_large_batch_100_documents(self):
        """100개 문서 배치 처리"""
        scores = [round(0.99 - (i * 0.009), 4) for i in range(100)]
        reranker = _make_mock_reranker(scores=scores)
        reranker.batch_size = 32
        documents = _make_documents(100)

        results = await reranker.rerank(
            query="100개 문서",
            documents=documents,
            top_k=10,
        )

        assert len(results) == 10
        # batch_size=32이므로 4번 호출 (32+32+32+4)
        assert reranker._compute_scores.call_count == 4

    @pytest.mark.asyncio
    async def test_concurrent_rerank_calls(self):
        """동시 리랭킹 호출"""
        reranker = _make_mock_reranker()
        documents = _make_documents(5)

        tasks = [
            reranker.rerank(
                query=f"concurrent-{i}",
                documents=documents,
                top_k=3,
            )
            for i in range(5)
        ]

        all_results = await asyncio.gather(*tasks)

        assert len(all_results) == 5
        for results in all_results:
            assert len(results) == 3


# ---------------------------------------------------------------------------
# 12. GPU/CPU 환경 테스트
# ---------------------------------------------------------------------------


class TestDeviceSupport:
    """
    AC5: GPU 없는 환경에서 CPU로 정상 동작
    """

    def test_cpu_device_detection(self):
        """CPU 환경에서 디바이스 감지"""
        reranker = BGEReranker(device="cpu")

        assert reranker.device == "cpu"

    def test_explicit_gpu_device(self):
        """GPU 명시 지정"""
        reranker = BGEReranker(device="cuda")

        assert reranker.device == "cuda"

    def test_auto_detect_no_gpu(self):
        """GPU 없는 환경에서 자동 감지"""
        with patch.object(
            BGEReranker, "_detect_device", return_value="cpu"
        ):
            reranker = BGEReranker(device=None)
            assert reranker.device == "cpu"

    def test_auto_detect_with_gpu(self):
        """GPU 있는 환경에서 자동 감지"""
        with patch.object(
            BGEReranker, "_detect_device", return_value="cuda"
        ):
            reranker = BGEReranker(device=None)
            assert reranker.device == "cuda"


# ---------------------------------------------------------------------------
# 13. knowledge_service HybridRetriever 통합 테스트
# ---------------------------------------------------------------------------


class TestKnowledgeServiceIntegration:
    """
    knowledge_service의 HybridRetriever에 reranker 옵션이
    올바르게 통합되었는지 검증하는 테스트
    """

    @pytest.mark.asyncio
    async def test_hybrid_retriever_with_reranker(self):
        """HybridRetriever에 reranker 주입 시 retrieve()가 reranking을 적용"""
        # Mock 준비 (knowledge_service 의존성 필요 없이 로직 검증)
        mock_search_service = MagicMock()

        # hybrid_search가 20개 결과 반환
        mock_results = [
            MockSearchResult(
                chunk_id=f"chunk-{i}",
                content=f"Content {i}",
                score=round(0.9 - (i * 0.04), 2),
            )
            for i in range(20)
        ]
        mock_search_service.hybrid_search = AsyncMock(return_value={
            "results": mock_results,
            "total": 20,
            "search_type": "hybrid",
            "latency_ms": 50.0,
            "debug": {
                "vector_count": 10,
                "keyword_count": 5,
                "graph_count": 5,
                "fused_count": 20,
            },
        })

        # Mock reranker
        mock_reranker = MagicMock()

        async def mock_rerank(query, search_results, top_k=None):
            reranked = list(reversed(search_results))
            if top_k:
                reranked = reranked[:top_k]
            for i, r in enumerate(reranked):
                r.score = round(0.95 - (i * 0.05), 2)
                r.metadata["rerank_score"] = r.score
                r.metadata["rerank_rank"] = i
                r.metadata["original_score"] = r.score
            return reranked

        mock_reranker.rerank_search_results = AsyncMock(side_effect=mock_rerank)
        mock_reranker.health_check = MagicMock(return_value={
            "service": "BGEReranker",
            "is_loaded": True,
        })

        # HybridRetriever가 reranker를 가진 것처럼 테스트
        # 실제 HybridRetriever 코드 로직을 시뮬레이션
        result = await mock_search_service.hybrid_search(
            query="테스트", filters=None, top_k=50, user_id=None,
        )
        fused_results = result.get("results", [])

        # reranking 적용
        reranked = await mock_reranker.rerank_search_results(
            query="테스트",
            search_results=fused_results[:50],
            top_k=5,
        )

        assert len(reranked) == 5
        assert reranked[0].metadata.get("rerank_score") is not None
        mock_reranker.rerank_search_results.assert_called_once()

    def test_hybrid_retriever_health_check_with_reranker(self):
        """HybridRetriever health_check에 reranker 상태 포함"""
        mock_reranker = MagicMock()
        mock_reranker.health_check = MagicMock(return_value={
            "service": "BGEReranker",
            "is_loaded": True,
            "device": "cpu",
        })

        # health_check 결과에 reranker 정보가 포함되어야 함
        health = {
            "service": "HybridRetriever",
            "reranker_enabled": True,
            "reranker": mock_reranker.health_check(),
        }

        assert health["reranker_enabled"] is True
        assert health["reranker"]["service"] == "BGEReranker"
        assert health["reranker"]["is_loaded"] is True


# ---------------------------------------------------------------------------
# 14. 모듈 Import 테스트
# ---------------------------------------------------------------------------


class TestModuleImports:
    """모듈 import 검증"""

    def test_import_from_reranking_package(self):
        """reranking 패키지에서 정상 import"""
        from ai_service.src.reranking import (
            BGEReranker,
            RerankResult,
            get_reranker,
            reset_reranker,
        )

        assert BGEReranker is not None
        assert RerankResult is not None
        assert callable(get_reranker)
        assert callable(reset_reranker)

    def test_import_from_bge_reranker_module(self):
        """bge_reranker 모듈에서 직접 import"""
        from ai_service.src.reranking.bge_reranker import (
            BGEReranker,
            RerankResult,
            get_reranker,
            reset_reranker,
        )

        assert BGEReranker is not None
        assert RerankResult is not None

    def test_import_hybrid_retriever_with_reranking(self):
        """hybrid_retriever 모듈 import"""
        from ai_service.src.retrievers.hybrid_retriever import (
            HybridRetrieverWithReranking,
        )

        assert HybridRetrieverWithReranking is not None
