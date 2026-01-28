"""
Reranker Async 전환 테스트

STORY-052: Reranker async 전환 (asyncio.to_thread 래핑)

테스트 범주:
1. async rerank()이 asyncio.to_thread()를 사용하는지 검증
2. _sync_rerank()이 기존과 동일한 결과를 반환하는지 검증
3. arerank_with_timeout() 타임아웃 보호 테스트
4. _fallback_results() 동작 테스트
5. 동시 실행 시 이벤트루프 블로킹 없음 검증
6. RerankerAdapter 타임아웃 통합 테스트
7. thread-safety 검증 (동시 5개 요청)

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
)
from ai_service.src.adapters.reranker_adapter import RerankerAdapter


# ---------------------------------------------------------------------------
# Test Helpers
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
    """Mock된 BGEReranker 생성 (_compute_scores를 mock)"""
    reranker = BGEReranker.__new__(BGEReranker)
    reranker.model_name = "BAAI/bge-reranker-v2-m3"
    reranker.device = "cpu"
    reranker.batch_size = 32
    reranker.max_length = 512
    reranker._model = MagicMock()
    reranker._tokenizer = MagicMock()

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
        def mock_compute_default(pairs):
            return [round(0.95 - (i * 0.05), 4) for i in range(len(pairs))]

        reranker._compute_scores = MagicMock(side_effect=mock_compute_default)

    return reranker


def _make_slow_mock_reranker(
    delay: float = 0.5,
    scores: Optional[List[float]] = None,
) -> BGEReranker:
    """
    느린 Mock BGEReranker 생성 (동시성 테스트용)

    _compute_scores에 delay를 추가하여 CPU-intensive 작업을 시뮬레이션
    """
    reranker = BGEReranker.__new__(BGEReranker)
    reranker.model_name = "BAAI/bge-reranker-v2-m3"
    reranker.device = "cpu"
    reranker.batch_size = 32
    reranker.max_length = 512
    reranker._model = MagicMock()
    reranker._tokenizer = MagicMock()

    def mock_compute_slow(pairs):
        time.sleep(delay)  # CPU-intensive 작업 시뮬레이션
        if scores:
            return scores[:len(pairs)]
        return [round(0.95 - (i * 0.05), 4) for i in range(len(pairs))]

    reranker._compute_scores = MagicMock(side_effect=mock_compute_slow)

    return reranker


# ---------------------------------------------------------------------------
# 1. asyncio.to_thread() 래핑 동작 검증
# ---------------------------------------------------------------------------


class TestAsyncToThread:
    """asyncio.to_thread() 래핑 동작 테스트"""

    @pytest.mark.asyncio
    async def test_rerank_uses_to_thread(self):
        """
        rerank()이 asyncio.to_thread()를 사용하여 _sync_rerank를 호출하는지 검증
        """
        reranker = _make_mock_reranker(scores=[0.9, 0.7, 0.5])
        documents = _make_documents(3)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            # to_thread가 실제 _sync_rerank 결과를 반환하도록 설정
            mock_to_thread.return_value = reranker._sync_rerank(
                "test query", documents, None
            )

            results = await reranker.rerank(
                query="test query",
                documents=documents,
            )

            # asyncio.to_thread이 호출되었는지 확인
            mock_to_thread.assert_called_once()
            # 첫 번째 인자가 _sync_rerank인지 확인
            call_args = mock_to_thread.call_args
            assert call_args[0][0] == reranker._sync_rerank

    @pytest.mark.asyncio
    async def test_rerank_returns_results(self):
        """rerank()이 정상 결과를 반환하는지 검증"""
        reranker = _make_mock_reranker(scores=[0.9, 0.3, 0.7])
        documents = _make_documents(3)

        results = await reranker.rerank(
            query="async 테스트",
            documents=documents,
        )

        assert len(results) == 3
        # 점수 내림차순 정렬 확인
        assert results[0].score >= results[1].score >= results[2].score

    @pytest.mark.asyncio
    async def test_rerank_empty_documents(self):
        """빈 문서 리스트에서 asyncio.to_thread이 호출되지 않음"""
        reranker = _make_mock_reranker()

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            results = await reranker.rerank(
                query="empty test",
                documents=[],
            )

            # 빈 입력은 to_thread 호출 전에 반환
            mock_to_thread.assert_not_called()
            assert results == []

    @pytest.mark.asyncio
    async def test_rerank_empty_query(self):
        """빈 쿼리에서 asyncio.to_thread이 호출되지 않음"""
        reranker = _make_mock_reranker()
        documents = _make_documents(3)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            results = await reranker.rerank(
                query="",
                documents=documents,
            )

            mock_to_thread.assert_not_called()
            assert results == []


# ---------------------------------------------------------------------------
# 2. _sync_rerank() 결과 동일성 검증
# ---------------------------------------------------------------------------


class TestSyncRerank:
    """_sync_rerank() 동기 메서드 테스트"""

    def test_sync_rerank_basic(self):
        """_sync_rerank이 올바른 결과를 반환"""
        reranker = _make_mock_reranker(scores=[0.9, 0.3, 0.7])
        documents = _make_documents(3)

        results = reranker._sync_rerank(
            query="sync 테스트",
            documents=documents,
        )

        assert len(results) == 3
        # 점수 내림차순 정렬
        assert results[0].score == 0.9
        assert results[1].score == 0.7
        assert results[2].score == 0.3

    def test_sync_rerank_with_top_k(self):
        """_sync_rerank에 top_k 적용"""
        reranker = _make_mock_reranker(scores=[0.9, 0.3, 0.7, 0.5, 0.1])
        documents = _make_documents(5)

        results = reranker._sync_rerank(
            query="top_k 테스트",
            documents=documents,
            top_k=2,
        )

        assert len(results) == 2
        assert results[0].score == 0.9

    def test_sync_rerank_rank_assignment(self):
        """_sync_rerank에서 순위(rank) 할당 확인"""
        reranker = _make_mock_reranker(scores=[0.5, 0.9, 0.1])
        documents = _make_documents(3)

        results = reranker._sync_rerank(
            query="rank 테스트",
            documents=documents,
        )

        for i, result in enumerate(results):
            assert result.rank == i

    def test_sync_rerank_preserves_metadata(self):
        """_sync_rerank에서 메타데이터 보존"""
        reranker = _make_mock_reranker(scores=[0.8])
        doc = _make_document("d1", score=0.5, metadata={"key": "value"})

        results = reranker._sync_rerank(
            query="메타데이터",
            documents=[doc],
        )

        assert results[0].metadata["key"] == "value"
        assert results[0].metadata["rerank_score"] == 0.8
        assert results[0].original_score == 0.5

    @pytest.mark.asyncio
    async def test_sync_and_async_produce_same_results(self):
        """
        _sync_rerank()과 rerank()이 동일한 결과를 생성하는지 검증
        (AC3: 기존과 동일한 reranked document 리스트 반환)
        """
        scores = [0.9, 0.3, 0.7, 0.5, 0.1]

        # sync 결과
        sync_reranker = _make_mock_reranker(scores=list(scores))
        documents = _make_documents(5)
        sync_results = sync_reranker._sync_rerank(
            query="동일성 테스트",
            documents=documents,
        )

        # async 결과
        async_reranker = _make_mock_reranker(scores=list(scores))
        async_results = await async_reranker.rerank(
            query="동일성 테스트",
            documents=documents,
        )

        # 결과 비교
        assert len(sync_results) == len(async_results)
        for sync_r, async_r in zip(sync_results, async_results):
            assert sync_r.doc_id == async_r.doc_id
            assert sync_r.score == async_r.score
            assert sync_r.rank == async_r.rank
            assert sync_r.original_score == async_r.original_score


# ---------------------------------------------------------------------------
# 3. arerank_with_timeout() 테스트
# ---------------------------------------------------------------------------


class TestArerankWithTimeout:
    """arerank_with_timeout() 타임아웃 보호 테스트"""

    @pytest.mark.asyncio
    async def test_timeout_returns_results_within_time(self):
        """타임아웃 내 완료 시 정상 결과 반환"""
        reranker = _make_mock_reranker(scores=[0.9, 0.7, 0.5])
        documents = _make_documents(3)

        results = await reranker.arerank_with_timeout(
            query="timeout 테스트",
            documents=documents,
            timeout=5.0,
        )

        assert len(results) == 3
        assert results[0].score == 0.9

    @pytest.mark.asyncio
    async def test_timeout_with_top_k(self):
        """타임아웃 + top_k 조합"""
        reranker = _make_mock_reranker(scores=[0.9, 0.7, 0.5, 0.3, 0.1])
        documents = _make_documents(5)

        results = await reranker.arerank_with_timeout(
            query="timeout top_k",
            documents=documents,
            top_k=2,
            timeout=5.0,
        )

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_timeout_triggers_fallback(self):
        """타임아웃 발생 시 fallback 결과 반환"""
        # 매우 느린 리랭커 생성 (0.5초 지연)
        reranker = _make_slow_mock_reranker(delay=2.0)
        documents = _make_documents(3)

        results = await reranker.arerank_with_timeout(
            query="slow query",
            documents=documents,
            top_k=2,
            timeout=0.1,  # 0.1초 타임아웃 (리랭킹보다 짧음)
        )

        # fallback 결과 반환
        assert len(results) == 2
        # fallback 메타데이터 확인
        assert results[0].metadata.get("rerank_fallback") is True

    @pytest.mark.asyncio
    async def test_timeout_fallback_preserves_order(self):
        """타임아웃 fallback이 원본 순서를 유지"""
        reranker = _make_slow_mock_reranker(delay=2.0)
        documents = [
            _make_document("first", score=0.9),
            _make_document("second", score=0.7),
            _make_document("third", score=0.5),
        ]

        results = await reranker.arerank_with_timeout(
            query="order test",
            documents=documents,
            timeout=0.1,
        )

        assert results[0].doc_id == "first"
        assert results[1].doc_id == "second"
        assert results[2].doc_id == "third"

    @pytest.mark.asyncio
    async def test_timeout_fallback_uses_original_scores(self):
        """타임아웃 fallback이 원본 점수를 사용"""
        reranker = _make_slow_mock_reranker(delay=2.0)
        documents = [
            _make_document("d1", score=0.95),
            _make_document("d2", score=0.80),
        ]

        results = await reranker.arerank_with_timeout(
            query="score test",
            documents=documents,
            timeout=0.1,
        )

        assert results[0].score == 0.95
        assert results[1].score == 0.80


# ---------------------------------------------------------------------------
# 4. _fallback_results() 테스트
# ---------------------------------------------------------------------------


class TestFallbackResults:
    """_fallback_results() 동작 테스트"""

    def test_fallback_basic(self):
        """기본 fallback 결과 생성"""
        reranker = _make_mock_reranker()
        documents = _make_documents(3)

        results = reranker._fallback_results(documents)

        assert len(results) == 3
        for i, result in enumerate(results):
            assert result.rank == i
            assert result.metadata.get("rerank_fallback") is True

    def test_fallback_with_top_k(self):
        """top_k 적용된 fallback"""
        reranker = _make_mock_reranker()
        documents = _make_documents(10)

        results = reranker._fallback_results(documents, top_k=3)

        assert len(results) == 3

    def test_fallback_preserves_doc_ids(self):
        """fallback이 문서 ID를 보존"""
        reranker = _make_mock_reranker()
        documents = [
            _make_document("alpha"),
            _make_document("beta"),
        ]

        results = reranker._fallback_results(documents)

        assert results[0].doc_id == "alpha"
        assert results[1].doc_id == "beta"

    def test_fallback_uses_original_scores(self):
        """fallback이 원본 점수를 score로 사용"""
        reranker = _make_mock_reranker()
        documents = [
            _make_document("d1", score=0.95),
            _make_document("d2", score=0.80),
        ]

        results = reranker._fallback_results(documents)

        assert results[0].score == 0.95
        assert results[0].original_score == 0.95
        assert results[1].score == 0.80

    def test_fallback_empty_documents(self):
        """빈 문서에 대한 fallback"""
        reranker = _make_mock_reranker()

        results = reranker._fallback_results([])

        assert results == []

    def test_fallback_top_k_none(self):
        """top_k=None이면 전체 반환"""
        reranker = _make_mock_reranker()
        documents = _make_documents(5)

        results = reranker._fallback_results(documents, top_k=None)

        assert len(results) == 5


# ---------------------------------------------------------------------------
# 5. 동시 실행 시 이벤트루프 블로킹 없음 검증
# ---------------------------------------------------------------------------


class TestConcurrency:
    """동시 실행 이벤트루프 비블로킹 검증"""

    @pytest.mark.asyncio
    async def test_async_rerank_does_not_block_event_loop(self):
        """
        AC1: async rerank가 이벤트루프를 블로킹하지 않는지 검증

        reranker가 실행되는 동안 다른 async 작업이 동시에 진행될 수 있어야 함
        """
        # 0.3초 지연이 있는 reranker
        reranker = _make_slow_mock_reranker(delay=0.3, scores=[0.9, 0.7])
        documents = _make_documents(2)

        concurrent_task_completed = False
        concurrent_task_start_time = None
        concurrent_task_end_time = None

        async def concurrent_task():
            nonlocal concurrent_task_completed
            nonlocal concurrent_task_start_time, concurrent_task_end_time
            concurrent_task_start_time = time.monotonic()
            await asyncio.sleep(0.05)  # 50ms sleep
            concurrent_task_end_time = time.monotonic()
            concurrent_task_completed = True
            return True

        start = time.monotonic()

        # 리랭킹과 동시 작업을 병렬로 실행
        rerank_result, concurrent_result = await asyncio.gather(
            reranker.rerank("concurrent test", documents),
            concurrent_task(),
        )

        total_time = time.monotonic() - start

        # concurrent_task가 완료되었어야 함
        assert concurrent_task_completed is True
        assert concurrent_result is True

        # concurrent_task는 리랭킹 완료 전에 끝나야 함 (비블로킹 증거)
        assert concurrent_task_end_time is not None
        concurrent_task_duration = concurrent_task_end_time - concurrent_task_start_time
        # concurrent_task는 ~50ms에 끝나야 하므로, 200ms 미만이면 블로킹 아님
        assert concurrent_task_duration < 0.2, (
            f"concurrent_task took {concurrent_task_duration:.3f}s, "
            f"expected < 0.2s (event loop likely blocked)"
        )

        # 리랭킹 결과도 정상
        assert len(rerank_result) == 2

    @pytest.mark.asyncio
    async def test_multiple_concurrent_reranks(self):
        """
        AC2: 동시에 여러 리랭킹 요청이 처리되는지 검증
        """
        reranker = _make_mock_reranker()
        documents = _make_documents(5)

        # 5개 동시 리랭킹
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

    @pytest.mark.asyncio
    async def test_concurrent_rerank_and_io(self):
        """
        AC2: 리랭킹 실행 중에 I/O 작업(검색)이 정상 진행되는지 검증
        """
        reranker = _make_slow_mock_reranker(delay=0.2, scores=[0.9])
        documents = [_make_document("d1")]

        io_completed_times: List[float] = []
        start = time.monotonic()

        async def mock_io_search():
            """모의 I/O 검색 (빠르게 완료)"""
            await asyncio.sleep(0.02)
            io_completed_times.append(time.monotonic() - start)
            return "search_complete"

        # 리랭킹과 I/O 검색을 병렬로 실행
        rerank_task = reranker.rerank("io test", documents)
        io_task = mock_io_search()

        results = await asyncio.gather(rerank_task, io_task)

        # I/O 작업이 리랭킹보다 먼저 완료되어야 함
        assert len(io_completed_times) == 1
        assert io_completed_times[0] < 0.15, (
            f"I/O task took {io_completed_times[0]:.3f}s, "
            f"should complete before reranker (~0.2s)"
        )


# ---------------------------------------------------------------------------
# 6. RerankerAdapter 타임아웃 통합 테스트
# ---------------------------------------------------------------------------


class TestRerankerAdapterAsync:
    """RerankerAdapter + async/timeout 통합 테스트"""

    @pytest.mark.asyncio
    async def test_adapter_uses_timeout(self):
        """RerankerAdapter가 타임아웃을 적용하는지 검증"""
        reranker = _make_mock_reranker(scores=[0.9, 0.7])
        adapter = RerankerAdapter(
            reranker=reranker,
            timeout=10.0,
        )

        documents = _make_documents(2)
        results = await adapter.rerank(
            query="adapter timeout",
            documents=documents,
            top_k=2,
        )

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_adapter_default_timeout(self):
        """RerankerAdapter 기본 타임아웃 값 확인"""
        adapter = RerankerAdapter(
            reranker=_make_mock_reranker(),
        )

        assert adapter._timeout == 15.0

    @pytest.mark.asyncio
    async def test_adapter_custom_timeout(self):
        """RerankerAdapter 커스텀 타임아웃"""
        adapter = RerankerAdapter(
            reranker=_make_mock_reranker(),
            timeout=30.0,
        )

        assert adapter._timeout == 30.0

    @pytest.mark.asyncio
    async def test_adapter_health_check_includes_timeout(self):
        """health_check에 타임아웃 정보 포함"""
        adapter = RerankerAdapter(
            reranker=_make_mock_reranker(),
            timeout=20.0,
        )

        health = adapter.health_check()

        assert health["timeout"] == 20.0

    @pytest.mark.asyncio
    async def test_adapter_fallback_on_timeout(self):
        """어댑터에서 타임아웃 시 fallback 동작"""
        slow_reranker = _make_slow_mock_reranker(delay=2.0)
        adapter = RerankerAdapter(
            reranker=slow_reranker,
            timeout=0.1,
        )

        documents = _make_documents(3)
        results = await adapter.rerank(
            query="timeout fallback",
            documents=documents,
            top_k=2,
        )

        # 타임아웃 fallback 결과 반환 (원본 순서)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_adapter_without_reranker(self):
        """리랭커 없이 원본 순서 반환"""
        adapter = RerankerAdapter(
            reranker=None,
            default_top_k=5,
        )

        documents = _make_documents(10)
        results = await adapter.rerank(
            query="no reranker",
            documents=documents,
        )

        assert len(results) == 5


# ---------------------------------------------------------------------------
# 7. Thread-Safety 검증
# ---------------------------------------------------------------------------


class TestThreadSafety:
    """thread-safety 검증 (동시 5개 요청)"""

    @pytest.mark.asyncio
    async def test_concurrent_5_requests_no_crash(self):
        """
        AC4: 동시 5개 요청 시 크래시 없음

        thread-safety를 검증합니다. BGE Reranker 모델은
        read-only inference이므로 thread-safe해야 합니다.
        """
        reranker = _make_mock_reranker()
        documents = _make_documents(10)

        tasks = [
            reranker.rerank(
                query=f"thread-safety-{i}",
                documents=documents,
                top_k=5,
            )
            for i in range(5)
        ]

        # 5개 동시 실행 - 크래시 없어야 함
        all_results = await asyncio.gather(*tasks, return_exceptions=True)

        # 모든 결과가 예외가 아닌 정상 리스트여야 함
        for i, result in enumerate(all_results):
            assert not isinstance(result, Exception), (
                f"Request {i} failed with: {result}"
            )
            assert isinstance(result, list)
            assert len(result) == 5

    @pytest.mark.asyncio
    async def test_concurrent_rerank_with_timeout(self):
        """동시 5개 요청에 타임아웃 적용"""
        reranker = _make_mock_reranker()
        documents = _make_documents(5)

        tasks = [
            reranker.arerank_with_timeout(
                query=f"timeout-thread-{i}",
                documents=documents,
                top_k=3,
                timeout=10.0,
            )
            for i in range(5)
        ]

        all_results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in all_results:
            assert not isinstance(result, Exception)
            assert len(result) == 3


# ---------------------------------------------------------------------------
# 8. 성능 벤치마크 (Mock 기반)
# ---------------------------------------------------------------------------


class TestAsyncPerformance:
    """async 전환 성능 벤치마크 (Mock 기반)"""

    @pytest.mark.asyncio
    async def test_async_overhead_minimal(self):
        """
        asyncio.to_thread() 래핑의 오버헤드가 미미한지 검증
        """
        reranker = _make_mock_reranker()
        documents = _make_documents(50)

        start = time.monotonic()
        results = await reranker.rerank(
            query="overhead test",
            documents=documents,
            top_k=10,
        )
        elapsed_ms = (time.monotonic() - start) * 1000

        assert len(results) == 10
        # Mock이므로 100ms 이내에 완료되어야 함
        assert elapsed_ms < 100, f"Async overhead too high: {elapsed_ms:.1f}ms"

    @pytest.mark.asyncio
    async def test_timeout_overhead_minimal(self):
        """arerank_with_timeout의 추가 오버헤드가 미미한지 검증"""
        reranker = _make_mock_reranker()
        documents = _make_documents(50)

        start = time.monotonic()
        results = await reranker.arerank_with_timeout(
            query="timeout overhead",
            documents=documents,
            top_k=10,
            timeout=5.0,
        )
        elapsed_ms = (time.monotonic() - start) * 1000

        assert len(results) == 10
        # Mock이므로 100ms 이내에 완료되어야 함
        assert elapsed_ms < 100, f"Timeout overhead too high: {elapsed_ms:.1f}ms"
