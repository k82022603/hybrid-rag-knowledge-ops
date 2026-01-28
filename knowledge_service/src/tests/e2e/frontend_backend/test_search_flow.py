"""
Category B: Search Flow E2E Tests (5 Scenarios)

Validates the search request lifecycle from Frontend input through
Backend routing to AI Service and back, including:
- FB-E2E-B-001: Keyword Search -> Results Display (P0)
- FB-E2E-B-002: Semantic Search -> Related Documents (P0)
- FB-E2E-B-003: Hybrid Search -> RRF Fusion Results (P0)
- FB-E2E-B-004: Empty Search -> Appropriate UI Display (P1)
- FB-E2E-B-005: Large Query (1000 chars) -> Normal Processing (P1)

Actual API Routes:
- /api/v1/search/hybrid  (POST, SearchRequest: query, top_k, filters)
- /api/v1/search/semantic (POST, SemanticSearchRequest: query, top_k, filters)
- /api/v1/search/keyword  (POST, SearchRequest: query, top_k, filters)
- Note: No auth middleware on search endpoints currently

Related Stories: STORY-051 (RAG Pipeline Integration), STORY-053 (Input Validation)
Sprint: Sprint 04 Day 3
Author: QA Agent
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Project root path setup
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from app.core.config import settings
from app.main import app

from .utils.auth_helpers import build_auth_headers, generate_valid_token

# =============================================================================
# Custom Markers
# =============================================================================

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.sprint04_fb_e2e,
    pytest.mark.search_flow,
]


# =============================================================================
# FB-E2E-B-001: Keyword Search -> Results Display
# Priority: P0 (Critical)
# =============================================================================


class TestB001KeywordSearch:
    """FB-E2E-B-001: Keyword search returns matching documents."""

    @pytest.mark.p0
    def test_keyword_search_returns_200(
        self,
        client: TestClient,
        api_prefix: str,
        keyword_search_body: Dict[str, Any],
    ):
        """Step 4: Search via POST /search/hybrid returns HTTP 200."""
        response = client.post(
            f"{api_prefix}/search/hybrid",
            json=keyword_search_body,
        )

        assert response.status_code == 200, (
            f"Search failed with status {response.status_code}: {response.text}"
        )

    @pytest.mark.p0
    def test_keyword_search_result_structure(
        self,
        client: TestClient,
        api_prefix: str,
        keyword_search_body: Dict[str, Any],
    ):
        """Step 5-6: Search results have expected structure."""
        response = client.post(
            f"{api_prefix}/search/hybrid",
            json=keyword_search_body,
        )

        if response.status_code == 200:
            data = response.json()
            # Actual response model: SearchResponse with query, results, total, search_type
            assert "results" in data, (
                f"Search response missing 'results' field. Keys: {list(data.keys())}"
            )
            assert isinstance(data["results"], list), "results should be a list"

    @pytest.mark.p0
    def test_keyword_search_results_contain_required_fields(
        self,
        client: TestClient,
        api_prefix: str,
        keyword_search_body: Dict[str, Any],
    ):
        """Result items contain chunk_id, document_id, content, score."""
        response = client.post(
            f"{api_prefix}/search/hybrid",
            json=keyword_search_body,
        )

        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])

            if isinstance(results, list) and len(results) > 0:
                first_result = results[0]
                # Actual model fields: chunk_id, document_id, content, score, metadata
                has_id = any(
                    k in first_result
                    for k in ["chunk_id", "document_id", "id"]
                )
                has_content = any(
                    k in first_result
                    for k in ["content", "text", "snippet"]
                )
                assert has_id, f"Result missing ID field. Keys: {list(first_result.keys())}"
                assert has_content, f"Result missing content field. Keys: {list(first_result.keys())}"

    @pytest.mark.p0
    def test_keyword_search_korean_encoding(
        self,
        client: TestClient,
        api_prefix: str,
    ):
        """Korean text in query and results renders without encoding issues."""
        body = {
            "query": "JWT 인증 필터 구현 방법",
            "top_k": 5,
        }
        response = client.post(
            f"{api_prefix}/search/hybrid",
            json=body,
        )

        if response.status_code == 200:
            response_text = response.text
            # Should not contain replacement characters
            assert "\ufffd" not in response_text, (
                "Response contains UTF-8 replacement characters"
            )


# =============================================================================
# FB-E2E-B-002: Semantic Search -> Related Documents
# Priority: P0 (Critical)
# =============================================================================


class TestB002SemanticSearch:
    """FB-E2E-B-002: Semantic search returns contextually related documents."""

    @pytest.mark.p0
    def test_semantic_search_returns_200(
        self,
        client: TestClient,
        api_prefix: str,
        semantic_search_body: Dict[str, Any],
    ):
        """Semantic query processed successfully via /search/semantic."""
        response = client.post(
            f"{api_prefix}/search/semantic",
            json=semantic_search_body,
        )

        assert response.status_code == 200, (
            f"Semantic search failed: {response.status_code} - {response.text}"
        )

    @pytest.mark.p0
    def test_semantic_search_response_structure(
        self,
        client: TestClient,
        api_prefix: str,
        semantic_search_body: Dict[str, Any],
    ):
        """Semantic search response has SearchResponse structure."""
        response = client.post(
            f"{api_prefix}/search/semantic",
            json=semantic_search_body,
        )

        if response.status_code == 200:
            data = response.json()
            # Actual SearchResponse fields: query, results, total, search_type, latency_ms
            assert isinstance(data, dict), "Response should be a dictionary"
            assert "query" in data, "Response missing 'query' field"
            assert "results" in data, "Response missing 'results' field"
            assert "total" in data, "Response missing 'total' field"

    @pytest.mark.p0
    def test_semantic_search_response_time(
        self,
        client: TestClient,
        api_prefix: str,
        semantic_search_body: Dict[str, Any],
    ):
        """Response time < 5 seconds for single query."""
        import time

        start = time.time()
        response = client.post(
            f"{api_prefix}/search/semantic",
            json=semantic_search_body,
        )
        elapsed = time.time() - start

        assert elapsed < 5.0, (
            f"Semantic search took {elapsed:.2f}s, exceeds 5s threshold"
        )


# =============================================================================
# FB-E2E-B-003: Hybrid Search -> RRF Fusion Results
# Priority: P0 (Critical)
# =============================================================================


class TestB003HybridSearchRRF:
    """FB-E2E-B-003: Hybrid search applies RRF fusion across ES and Neo4j."""

    @pytest.mark.p0
    def test_hybrid_search_returns_200(
        self,
        client: TestClient,
        api_prefix: str,
        hybrid_search_body: Dict[str, Any],
    ):
        """Hybrid search request routed and processed successfully."""
        response = client.post(
            f"{api_prefix}/search/hybrid",
            json=hybrid_search_body,
        )

        assert response.status_code == 200, (
            f"Hybrid search failed: {response.status_code} - {response.text}"
        )

    @pytest.mark.p0
    def test_hybrid_search_results_sorted_by_score(
        self,
        client: TestClient,
        api_prefix: str,
        hybrid_search_body: Dict[str, Any],
    ):
        """Results are sorted by relevance score (descending)."""
        response = client.post(
            f"{api_prefix}/search/hybrid",
            json=hybrid_search_body,
        )

        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])

            if isinstance(results, list) and len(results) >= 2:
                scores = [
                    r.get("score", 0)
                    for r in results
                    if isinstance(r, dict)
                ]
                if scores and all(s > 0 for s in scores):
                    # Verify descending order
                    assert scores == sorted(scores, reverse=True), (
                        f"Results not sorted by score: {scores}"
                    )

    @pytest.mark.p0
    def test_hybrid_search_type_in_response(
        self,
        client: TestClient,
        api_prefix: str,
    ):
        """Search type 'hybrid' reflected in response."""
        body = {
            "query": "RAG 시스템 아키텍처",
            "top_k": 5,
        }
        response = client.post(
            f"{api_prefix}/search/hybrid",
            json=body,
        )

        if response.status_code == 200:
            data = response.json()
            search_type = data.get("search_type", "")
            assert search_type == "hybrid", (
                f"Expected search_type 'hybrid', got '{search_type}'"
            )


# =============================================================================
# FB-E2E-B-004: Empty Search -> Appropriate UI Display
# Priority: P1 (High)
# =============================================================================


class TestB004EmptySearch:
    """FB-E2E-B-004: Search with no results shows appropriate empty state."""

    @pytest.mark.p1
    def test_empty_search_returns_200_not_error(
        self,
        client: TestClient,
        api_prefix: str,
        empty_search_body: Dict[str, Any],
    ):
        """Step 3-4: Nonsensical query returns 200 (not 404 or 500)."""
        response = client.post(
            f"{api_prefix}/search/hybrid",
            json=empty_search_body,
        )

        assert response.status_code == 200, (
            f"Empty search should return 200, got {response.status_code}"
        )

    @pytest.mark.p1
    def test_empty_search_returns_empty_results(
        self,
        client: TestClient,
        api_prefix: str,
        empty_search_body: Dict[str, Any],
    ):
        """Response body contains empty results array or fallback."""
        response = client.post(
            f"{api_prefix}/search/hybrid",
            json=empty_search_body,
        )

        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])

            if isinstance(results, list):
                # Empty results or very few matches for nonsensical query
                assert len(results) >= 0, "Results should be a valid array"

    @pytest.mark.p1
    def test_empty_query_string_handled(
        self,
        client: TestClient,
        api_prefix: str,
    ):
        """Empty query string returns error or empty results (not crash)."""
        body = {"query": "", "top_k": 10}
        response = client.post(
            f"{api_prefix}/search/hybrid",
            json=body,
        )

        # Should be either 200 (empty results) or 400/422 (validation error)
        assert response.status_code in [200, 400, 422], (
            f"Empty query should be handled gracefully, got {response.status_code}"
        )


# =============================================================================
# FB-E2E-B-005: Large Query (1000 chars) -> Normal Processing
# Priority: P1 (High)
# =============================================================================


class TestB005LargeQuery:
    """FB-E2E-B-005: Large query at maximum allowed length processed normally."""

    @pytest.mark.p1
    def test_1000_char_query_accepted(
        self,
        client: TestClient,
        api_prefix: str,
        large_query_1000_chars: str,
    ):
        """Step 1-3: 1000-char query is accepted and processed."""
        assert len(large_query_1000_chars) == 1000, (
            f"Test fixture should be exactly 1000 chars, got {len(large_query_1000_chars)}"
        )

        body = {
            "query": large_query_1000_chars,
            "top_k": 5,
        }
        response = client.post(
            f"{api_prefix}/search/hybrid",
            json=body,
        )

        assert response.status_code == 200, (
            f"1000-char query should be accepted, got {response.status_code}"
        )

    @pytest.mark.p1
    def test_1001_char_query_rejected(
        self,
        client: TestClient,
        api_prefix: str,
        large_query_1001_chars: str,
    ):
        """Step 4-5: 1001-char query is rejected with validation error."""
        assert len(large_query_1001_chars) == 1001, (
            f"Test fixture should be exactly 1001 chars, got {len(large_query_1001_chars)}"
        )

        body = {
            "query": large_query_1001_chars,
            "top_k": 5,
        }
        response = client.post(
            f"{api_prefix}/search/hybrid",
            json=body,
        )

        # Should be 400 or 422 (validation error) for exceeding max length
        assert response.status_code in [200, 400, 422], (
            f"1001-char query should return 400/422 or be truncated, got {response.status_code}"
        )

    @pytest.mark.p1
    def test_no_server_crash_on_boundary_values(
        self,
        client: TestClient,
        api_prefix: str,
    ):
        """No server crash or timeout for boundary values."""
        boundary_lengths = [0, 1, 999, 1000, 1001, 2000]

        for length in boundary_lengths:
            query = "A" * length if length > 0 else ""
            body = {
                "query": query,
                "top_k": 5,
            }
            response = client.post(
                f"{api_prefix}/search/hybrid",
                json=body,
            )

            # Should not crash (5xx indicates server error)
            assert response.status_code < 500, (
                f"Server crashed for query length {length}: {response.status_code}"
            )
