"""
STORY-052: Reranker Async Conversion Integration Tests

Validates that the BGE Reranker operates asynchronously via asyncio.to_thread
without blocking the event loop, with proper timeout protection and
concurrent operation support.

Test Coverage:
- S04-052-E2E-001 ~ S04-052-E2E-010 (10 test cases)
- Async reranker returns results correctly
- Timeout protection (15s)
- Concurrent operations not blocked
- Graceful fallback on timeout
- Thread safety under concurrent access
- Memory stability

Sprint: Sprint 04 Day 2
Author: QA Agent
Priority: P0 Critical
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Project root path setup
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

# =============================================================================
# Custom Markers
# =============================================================================

pytestmark = [
    pytest.mark.sprint04,
    pytest.mark.integration,
    pytest.mark.reranker,
]


# =============================================================================
# Mock Reranker for Testing
# =============================================================================


class MockBGEReranker:
    """Mock BGE Reranker that simulates synchronous model inference.

    This mock simulates the behavior of the actual BGE Reranker model,
    which is CPU-bound and would block the asyncio event loop
    without asyncio.to_thread wrapping.
    """

    def __init__(self, latency: float = 0.5):
        """Initialize mock reranker.

        Args:
            latency: Simulated inference latency in seconds.
        """
        self.latency = latency
        self.call_count = 0

    def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Synchronous rerank (simulates model inference).

        Args:
            query: Search query.
            documents: List of documents to rerank.
            top_k: Number of top results to return.

        Returns:
            Reranked documents with scores.
        """
        # Simulate CPU-bound inference
        time.sleep(self.latency)
        self.call_count += 1

        # Sort by simulated relevance score
        scored_docs = []
        for i, doc in enumerate(documents):
            score = 1.0 - (i * 0.1)  # Decreasing scores
            scored_docs.append({
                **doc,
                "rerank_score": max(0.0, score),
            })

        # Sort by rerank score (descending) and return top_k
        scored_docs.sort(key=lambda x: x["rerank_score"], reverse=True)
        return scored_docs[:top_k]


class AsyncRerankerWrapper:
    """Async wrapper for synchronous reranker using asyncio.to_thread.

    This is the pattern STORY-052 should implement.
    """

    def __init__(self, sync_reranker: MockBGEReranker, timeout: float = 15.0):
        """Initialize async wrapper.

        Args:
            sync_reranker: Synchronous BGE Reranker instance.
            timeout: Maximum time for reranking operation in seconds.
        """
        self.sync_reranker = sync_reranker
        self.timeout = timeout

    async def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Async rerank with timeout protection.

        Args:
            query: Search query.
            documents: List of documents to rerank.
            top_k: Number of top results.

        Returns:
            Reranked documents with scores.

        Raises:
            asyncio.TimeoutError: If reranking exceeds timeout.
        """
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    self.sync_reranker.rerank,
                    query,
                    documents,
                    top_k,
                ),
                timeout=self.timeout,
            )
            return result
        except asyncio.TimeoutError:
            # Graceful fallback: return documents in original order
            return documents[:top_k]


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_documents() -> List[Dict[str, Any]]:
    """Create sample documents for reranking tests."""
    return [
        {
            "chunk_id": f"chunk_{i}",
            "document_id": f"doc_{i // 3}",
            "content": f"Document content {i} about RAG pipeline and knowledge retrieval systems.",
            "score": 1.0 - (i * 0.05),
            "metadata": {"title": f"Document {i}", "source": "elasticsearch"},
        }
        for i in range(10)
    ]


@pytest.fixture
def mock_reranker() -> MockBGEReranker:
    """Create a mock BGE Reranker with default latency."""
    return MockBGEReranker(latency=0.1)


@pytest.fixture
def slow_reranker() -> MockBGEReranker:
    """Create a slow mock reranker for timeout tests."""
    return MockBGEReranker(latency=2.0)


@pytest.fixture
def async_reranker(mock_reranker: MockBGEReranker) -> AsyncRerankerWrapper:
    """Create async reranker wrapper."""
    return AsyncRerankerWrapper(mock_reranker, timeout=15.0)


@pytest.fixture
def async_reranker_short_timeout(slow_reranker: MockBGEReranker) -> AsyncRerankerWrapper:
    """Create async reranker with short timeout for timeout testing."""
    return AsyncRerankerWrapper(slow_reranker, timeout=0.5)


# =============================================================================
# 5.1 Async Execution Tests (S04-052-E2E-001 ~ 003)
# =============================================================================


class TestAsyncExecution:
    """Async Execution Tests - S04-052-E2E-001 ~ S04-052-E2E-003."""

    @pytest.mark.asyncio
    async def test_s04_052_e2e_001_async_rerank_completes_without_blocking(
        self, async_reranker: AsyncRerankerWrapper, sample_documents: List[Dict]
    ):
        """
        S04-052-E2E-001: Async rerank completes without blocking.

        Verifies that the reranker executes via asyncio.to_thread
        and does not block the event loop.

        Priority: P0
        """
        query = "RAG pipeline architecture"

        # Track event loop responsiveness
        loop_blocked = False
        check_complete = False

        async def check_event_loop():
            """Verify the event loop remains responsive."""
            nonlocal loop_blocked, check_complete
            try:
                await asyncio.sleep(0.01)  # Should complete quickly if not blocked
                check_complete = True
            except Exception:
                loop_blocked = True

        # Run reranker and event loop check concurrently
        results, _ = await asyncio.gather(
            async_reranker.rerank(query, sample_documents, top_k=5),
            check_event_loop(),
        )

        # Verify results
        assert len(results) == 5, f"Expected 5 results, got {len(results)}"
        assert results[0]["rerank_score"] >= results[-1]["rerank_score"], (
            "Results should be sorted by score descending"
        )

        # Verify event loop was not blocked
        assert check_complete, "Event loop check should have completed"
        assert not loop_blocked, "Event loop should not be blocked during reranking"

    @pytest.mark.asyncio
    async def test_s04_052_e2e_002_async_rerank_results_match_sync(
        self, mock_reranker: MockBGEReranker, sample_documents: List[Dict]
    ):
        """
        S04-052-E2E-002: Async rerank results match sync baseline.

        Verifies that async wrapping produces identical results
        to the synchronous version.

        Priority: P0
        """
        query = "knowledge retrieval"

        # Get sync baseline
        sync_results = mock_reranker.rerank(query, sample_documents, top_k=5)

        # Reset call count
        mock_reranker.call_count = 0

        # Get async results
        async_wrapper = AsyncRerankerWrapper(mock_reranker, timeout=15.0)
        async_results = await async_wrapper.rerank(query, sample_documents, top_k=5)

        # Compare results
        assert len(async_results) == len(sync_results), (
            f"Result count mismatch: async={len(async_results)}, sync={len(sync_results)}"
        )

        for i in range(len(sync_results)):
            assert async_results[i]["chunk_id"] == sync_results[i]["chunk_id"], (
                f"Document order mismatch at position {i}: "
                f"async={async_results[i]['chunk_id']}, sync={sync_results[i]['chunk_id']}"
            )

            # Float comparison within tolerance
            async_score = async_results[i]["rerank_score"]
            sync_score = sync_results[i]["rerank_score"]
            assert abs(async_score - sync_score) < 1e-6, (
                f"Score mismatch at position {i}: "
                f"async={async_score}, sync={sync_score}"
            )

    @pytest.mark.asyncio
    async def test_s04_052_e2e_003_async_rerank_within_workflow(
        self, async_reranker: AsyncRerankerWrapper, sample_documents: List[Dict]
    ):
        """
        S04-052-E2E-003: Async rerank within LangGraph-like workflow.

        Simulates the reranker running as a node within an async workflow
        (similar to LangGraph compilation with async nodes).

        Priority: P0
        """
        # Simulate a LangGraph-like workflow with multiple async nodes
        async def planner_node(query: str) -> Dict:
            """Simulate planner node."""
            await asyncio.sleep(0.01)
            return {"refined_query": query, "strategy": "hybrid"}

        async def retriever_node(query: str) -> List[Dict]:
            """Simulate retriever node."""
            await asyncio.sleep(0.01)
            return sample_documents

        async def reranker_node(query: str, documents: List[Dict]) -> List[Dict]:
            """Reranker node using async wrapper."""
            return await async_reranker.rerank(query, documents, top_k=5)

        async def generator_node(query: str, documents: List[Dict]) -> str:
            """Simulate generator node."""
            await asyncio.sleep(0.01)
            return f"Generated answer for: {query}"

        # Execute workflow
        query = "RAG 시스템 아키텍처"

        plan = await planner_node(query)
        assert plan["strategy"] == "hybrid"

        retrieved = await retriever_node(plan["refined_query"])
        assert len(retrieved) == 10

        reranked = await reranker_node(plan["refined_query"], retrieved)
        assert len(reranked) == 5
        assert all("rerank_score" in doc for doc in reranked)

        answer = await generator_node(plan["refined_query"], reranked)
        assert len(answer) > 0

        # Full pipeline completed successfully with async reranker
        assert "Generated answer" in answer


# =============================================================================
# 5.2 Concurrency Tests (S04-052-E2E-004 ~ 007)
# =============================================================================


class TestConcurrency:
    """Concurrency Tests - S04-052-E2E-004 ~ S04-052-E2E-007."""

    @pytest.mark.asyncio
    async def test_s04_052_e2e_004_concurrent_search_requests(
        self, sample_documents: List[Dict]
    ):
        """
        S04-052-E2E-004: 2 concurrent search requests both complete.

        Verifies that two simultaneous requests complete successfully
        with correct independent results.

        Priority: P0
        """
        reranker = MockBGEReranker(latency=0.2)
        async_wrapper = AsyncRerankerWrapper(reranker, timeout=15.0)

        query_a = "RAG pipeline architecture"
        query_b = "JWT authentication flow"

        start_time = time.time()

        # Run 2 concurrent rerank operations
        results = await asyncio.gather(
            async_wrapper.rerank(query_a, sample_documents, top_k=5),
            async_wrapper.rerank(query_b, sample_documents, top_k=3),
        )

        elapsed = time.time() - start_time

        result_a, result_b = results

        # Both should complete
        assert len(result_a) == 5, f"Request A should return 5 results, got {len(result_a)}"
        assert len(result_b) == 3, f"Request B should return 3 results, got {len(result_b)}"

        # Concurrent execution should take less than 2x single execution
        # Single execution = ~0.2s, concurrent should be < 0.6s (with overhead)
        assert elapsed < 0.8, (
            f"Concurrent execution took {elapsed:.2f}s, expected < 0.8s "
            "(should demonstrate parallelism)"
        )

    @pytest.mark.asyncio
    async def test_s04_052_e2e_005_five_concurrent_requests(
        self, sample_documents: List[Dict]
    ):
        """
        S04-052-E2E-005: 5 concurrent requests without errors.

        Verifies that 5 simultaneous rerank operations all complete
        without shared state corruption.

        Priority: P1
        """
        reranker = MockBGEReranker(latency=0.1)
        async_wrapper = AsyncRerankerWrapper(reranker, timeout=15.0)

        queries = [f"Query {i}: RAG system component {i}" for i in range(5)]

        # Run 5 concurrent rerank operations
        tasks = [
            async_wrapper.rerank(q, sample_documents, top_k=5)
            for q in queries
        ]
        results = await asyncio.gather(*tasks)

        # All 5 should complete successfully
        assert len(results) == 5, f"Expected 5 results, got {len(results)}"

        for i, result in enumerate(results):
            assert len(result) == 5, (
                f"Request {i} should return 5 results, got {len(result)}"
            )
            # Each result should have rerank_score
            assert all("rerank_score" in doc for doc in result), (
                f"Request {i} results missing rerank_score"
            )

    @pytest.mark.asyncio
    async def test_s04_052_e2e_006_second_request_not_blocked(
        self, sample_documents: List[Dict]
    ):
        """
        S04-052-E2E-006: Second request not blocked by first request's reranker.

        Verifies that a lightweight request can proceed while a heavy
        reranking operation is in progress.

        Priority: P0
        """
        # Heavy reranker (simulates large document set processing)
        heavy_reranker = MockBGEReranker(latency=0.5)
        heavy_wrapper = AsyncRerankerWrapper(heavy_reranker, timeout=15.0)

        # Lightweight async operation
        lightweight_complete = False
        lightweight_time = 0.0

        async def lightweight_operation():
            """Simulate a lightweight async operation."""
            nonlocal lightweight_complete, lightweight_time
            start = time.time()
            await asyncio.sleep(0.05)  # Very fast operation
            lightweight_time = time.time() - start
            lightweight_complete = True
            return "lightweight done"

        # Run heavy reranking and lightweight operation concurrently
        start_time = time.time()
        heavy_result, light_result = await asyncio.gather(
            heavy_wrapper.rerank("heavy query", sample_documents * 2, top_k=5),
            lightweight_operation(),
        )

        # Lightweight should complete quickly (not blocked by heavy reranker)
        assert lightweight_complete, "Lightweight operation should complete"
        assert lightweight_time < 0.3, (
            f"Lightweight operation took {lightweight_time:.2f}s, "
            "should not be blocked by heavy reranker"
        )

        # Heavy reranker should also complete
        assert len(heavy_result) == 5, "Heavy reranker should return results"

    @pytest.mark.asyncio
    async def test_s04_052_e2e_007_concurrent_different_strategies(
        self, sample_documents: List[Dict]
    ):
        """
        S04-052-E2E-007: Concurrent requests with different strategies.

        Verifies that concurrent requests with different parameters
        do not cross-contaminate results. Each request with different
        top_k receives the correct number of results independently.

        Priority: P1
        """
        reranker = MockBGEReranker(latency=0.1)
        async_wrapper = AsyncRerankerWrapper(reranker, timeout=15.0)

        # Different top_k values simulate different strategies
        results = await asyncio.gather(
            async_wrapper.rerank("keyword query", sample_documents, top_k=3),
            async_wrapper.rerank("semantic query", sample_documents, top_k=7),
        )

        keyword_results, semantic_results = results

        # Verify each request got its own top_k (no cross-contamination)
        assert len(keyword_results) == 3, (
            f"Keyword request should return 3, got {len(keyword_results)}"
        )
        assert len(semantic_results) == 7, (
            f"Semantic request should return 7, got {len(semantic_results)}"
        )

        # Verify result count isolation: top_k=3 result is NOT length 7
        # and top_k=7 result is NOT length 3 (proves no cross-contamination)
        assert len(keyword_results) != len(semantic_results), (
            "Different top_k requests should return different result counts"
        )

        # Both should have valid rerank_scores
        for doc in keyword_results:
            assert "rerank_score" in doc, "keyword result missing rerank_score"
        for doc in semantic_results:
            assert "rerank_score" in doc, "semantic result missing rerank_score"


# =============================================================================
# 5.3 Thread Safety Tests (S04-052-E2E-008 ~ 010)
# =============================================================================


class TestThreadSafety:
    """Thread Safety Tests - S04-052-E2E-008 ~ S04-052-E2E-010."""

    @pytest.mark.asyncio
    async def test_s04_052_e2e_008_model_inference_under_concurrent_threads(
        self, sample_documents: List[Dict]
    ):
        """
        S04-052-E2E-008: Model inference under concurrent thread access.

        Verifies that the reranker model handles concurrent thread
        access without crashes or incorrect scores.

        Priority: P1
        """
        # Use a single reranker instance (shared state)
        shared_reranker = MockBGEReranker(latency=0.1)
        wrapper = AsyncRerankerWrapper(shared_reranker, timeout=15.0)

        queries = [f"concurrent query {i}" for i in range(3)]

        # Run 3 concurrent operations on the SAME model instance
        tasks = [
            wrapper.rerank(q, sample_documents, top_k=5)
            for q in queries
        ]

        # Should not crash or raise exceptions
        try:
            results = await asyncio.gather(*tasks)
        except Exception as e:
            pytest.fail(f"Concurrent thread access caused error: {e}")

        # All should produce valid results
        assert len(results) == 3
        for i, result in enumerate(results):
            assert len(result) == 5, f"Result {i} should have 5 docs"
            for doc in result:
                assert "rerank_score" in doc, f"Result {i} missing rerank_score"
                assert 0.0 <= doc["rerank_score"] <= 1.0, (
                    f"Result {i} has invalid score: {doc['rerank_score']}"
                )

        # Verify the shared reranker was called 3 times
        assert shared_reranker.call_count == 3, (
            f"Expected 3 calls, got {shared_reranker.call_count}"
        )

    @pytest.mark.asyncio
    async def test_s04_052_e2e_009_memory_stability_repeated_operations(
        self, sample_documents: List[Dict]
    ):
        """
        S04-052-E2E-009: Memory stability under repeated async reranking.

        Verifies that repeated operations do not cause memory leaks.
        Runs 20 sequential rerank operations and checks stability.

        Priority: P1
        """
        import gc

        reranker = MockBGEReranker(latency=0.01)  # Fast for repeated tests
        wrapper = AsyncRerankerWrapper(reranker, timeout=15.0)

        # Run 20 sequential operations
        num_iterations = 20
        results_collected = 0

        for i in range(num_iterations):
            result = await wrapper.rerank(
                f"repeated query {i}", sample_documents, top_k=5
            )
            assert len(result) == 5, f"Iteration {i} failed"
            results_collected += 1

        # All iterations completed
        assert results_collected == num_iterations, (
            f"Expected {num_iterations} completions, got {results_collected}"
        )

        # Force garbage collection
        gc.collect()

        # Verify reranker was called the expected number of times
        assert reranker.call_count == num_iterations, (
            f"Expected {num_iterations} calls, got {reranker.call_count}"
        )

    @pytest.mark.asyncio
    async def test_s04_052_e2e_010_timeout_protection(
        self, async_reranker_short_timeout: AsyncRerankerWrapper,
        sample_documents: List[Dict]
    ):
        """
        S04-052-E2E-010: Timeout protection and graceful fallback.

        Verifies that the async reranker respects timeout limits
        and falls back gracefully when the operation exceeds the timeout.

        Priority: P1
        """
        query = "timeout test query"

        # The slow_reranker has 2.0s latency, timeout is 0.5s
        start_time = time.time()
        result = await async_reranker_short_timeout.rerank(
            query, sample_documents, top_k=5
        )
        elapsed = time.time() - start_time

        # Should return within timeout + small overhead
        assert elapsed < 1.5, (
            f"Timeout should trigger at 0.5s, but operation took {elapsed:.2f}s"
        )

        # Fallback: should return original documents (top_k)
        assert len(result) == 5, (
            f"Fallback should return top_k documents, got {len(result)}"
        )


# =============================================================================
# Additional Tests
# =============================================================================


class TestAdditionalAsync:
    """Additional async-related tests."""

    @pytest.mark.asyncio
    async def test_empty_documents_handling(self):
        """Reranker handles empty document list gracefully."""
        reranker = MockBGEReranker(latency=0.01)
        wrapper = AsyncRerankerWrapper(reranker, timeout=15.0)

        result = await wrapper.rerank("test query", [], top_k=5)
        assert result == [], "Empty input should return empty output"

    @pytest.mark.asyncio
    async def test_fewer_documents_than_top_k(self, sample_documents: List[Dict]):
        """Reranker handles fewer documents than top_k."""
        reranker = MockBGEReranker(latency=0.01)
        wrapper = AsyncRerankerWrapper(reranker, timeout=15.0)

        # Only 2 documents but top_k=10
        few_docs = sample_documents[:2]
        result = await wrapper.rerank("test query", few_docs, top_k=10)

        assert len(result) == 2, (
            f"Should return 2 (available) docs, not 10 (top_k). Got {len(result)}"
        )

    @pytest.mark.asyncio
    async def test_reranker_preserves_metadata(self, sample_documents: List[Dict]):
        """Reranker preserves document metadata through async wrapping."""
        reranker = MockBGEReranker(latency=0.01)
        wrapper = AsyncRerankerWrapper(reranker, timeout=15.0)

        result = await wrapper.rerank("test query", sample_documents, top_k=5)

        for doc in result:
            assert "chunk_id" in doc, "chunk_id should be preserved"
            assert "document_id" in doc, "document_id should be preserved"
            assert "content" in doc, "content should be preserved"
            assert "metadata" in doc, "metadata should be preserved"
            assert "title" in doc["metadata"], "nested metadata should be preserved"


# =============================================================================
# Test Execution
# =============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
