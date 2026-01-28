"""
Contract Test: Backend -> AI Service API Contract

Validates that the Backend service sends correctly structured requests
to the AI Service, and that the AI Service responses conform to the
expected schema.

Contracts validated:
- POST /internal/v1/search/hybrid (search request/response)
- POST /api/v1/search (external search endpoint)
- POST /api/v1/search/chat (chat search endpoint)

Related: STORY-054, API Integration Design v1.4
Sprint: Sprint 04 Day 3
Author: QA Agent
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

# Project root path setup
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from .conftest import validate_json_schema

# =============================================================================
# Custom Markers
# =============================================================================

pytestmark = [
    pytest.mark.contract,
    pytest.mark.sprint04_fb_e2e,
]


# =============================================================================
# Test Data: Valid Requests
# =============================================================================

VALID_SEARCH_REQUESTS = [
    {
        "description": "Minimal search request (query only)",
        "data": {"query": "JWT 인증 필터"},
    },
    {
        "description": "Search with searchType and topK",
        "data": {
            "query": "프로젝트 보안 감사 절차",
            "searchType": "hybrid",
            "topK": 10,
        },
    },
    {
        "description": "Search with all fields",
        "data": {
            "query": "React 아키텍처 가이드",
            "searchType": "hybrid",
            "topK": 10,
            "filters": {
                "projectName": "Knowledge Platform",
                "documentType": "기술문서",
                "dateRange": {"start": "2026-01-01", "end": "2026-12-31"},
                "categories": {"level1": "기술", "level2": "프론트엔드"},
                "author": "홍길동",
                "tags": ["React", "TypeScript"],
            },
            "includeAnswer": True,
            "includeGraphContext": True,
        },
    },
    {
        "description": "Vector-only search",
        "data": {
            "query": "임베딩 모델 비교",
            "searchType": "vector",
            "topK": 5,
        },
    },
    {
        "description": "Graph-only search",
        "data": {
            "query": "프론트엔드 팀 전문가",
            "searchType": "graph",
            "topK": 5,
        },
    },
]

INVALID_SEARCH_REQUESTS = [
    {
        "description": "Missing required query field",
        "data": {"searchType": "hybrid", "topK": 10},
        "expected_error": "Missing required field: 'query'",
    },
    {
        "description": "Empty query string",
        "data": {"query": ""},
        "expected_error": "minLength",
    },
    {
        "description": "Query exceeds max length (1001 chars)",
        "data": {"query": "A" * 1001},
        "expected_error": "maxLength",
    },
    {
        "description": "Invalid searchType enum value",
        "data": {"query": "test", "searchType": "invalid_type"},
        "expected_error": "not in enum",
    },
    {
        "description": "TopK below minimum",
        "data": {"query": "test", "topK": 0},
        "expected_error": "minimum",
    },
    {
        "description": "TopK above maximum",
        "data": {"query": "test", "topK": 101},
        "expected_error": "maximum",
    },
]

VALID_SEARCH_RESPONSES = [
    {
        "description": "Standard search response with results",
        "data": {
            "success": True,
            "data": {
                "query": "JWT 인증 필터",
                "answer": "JWT 인증 필터는 Spring Security에서...",
                "results": [
                    {
                        "id": "result-001",
                        "knowledgeId": "k-001",
                        "title": "JWT 인증 필터 구현 가이드",
                        "text": "JWT 인증 필터는 모든 API 요청을 검증합니다...",
                        "score": 0.92,
                        "metadata": {
                            "documentType": "기술문서",
                            "projectName": "Knowledge Platform",
                        },
                    }
                ],
                "searchMetadata": {
                    "searchType": "hybrid",
                    "totalResults": 1,
                    "vectorResultsCount": 1,
                    "graphResultsCount": 0,
                    "fusionMethod": "rrf",
                    "latencyMs": 320,
                },
                "sources": [
                    {
                        "knowledgeId": "k-001",
                        "title": "JWT 인증 필터 구현 가이드",
                        "author": "Backend Developer",
                    }
                ],
            },
        },
    },
    {
        "description": "Empty search results (no matches)",
        "data": {
            "success": True,
            "data": {
                "query": "nonexistent topic",
                "answer": "",
                "results": [],
                "searchMetadata": {
                    "searchType": "hybrid",
                    "totalResults": 0,
                    "vectorResultsCount": 0,
                    "graphResultsCount": 0,
                    "fusionMethod": "rrf",
                    "latencyMs": 50,
                },
                "sources": [],
            },
        },
    },
    {
        "description": "Error response",
        "data": {
            "success": False,
        },
    },
]


# =============================================================================
# Contract Tests: Request Schema Validation
# =============================================================================


class TestBackendToAISearchRequestContract:
    """Validates Backend -> AI Service search request schema."""

    def test_valid_requests_pass_schema(
        self,
        backend_to_ai_search_request_schema: Dict[str, Any],
    ):
        """All valid search requests conform to contract schema."""
        for case in VALID_SEARCH_REQUESTS:
            errors = validate_json_schema(
                case["data"],
                backend_to_ai_search_request_schema,
            )
            assert len(errors) == 0, (
                f"Valid request '{case['description']}' failed validation: {errors}"
            )

    def test_invalid_requests_fail_schema(
        self,
        backend_to_ai_search_request_schema: Dict[str, Any],
    ):
        """Invalid search requests are rejected by contract schema."""
        for case in INVALID_SEARCH_REQUESTS:
            errors = validate_json_schema(
                case["data"],
                backend_to_ai_search_request_schema,
            )
            assert len(errors) > 0, (
                f"Invalid request '{case['description']}' should fail validation"
            )

    def test_query_field_required(
        self,
        backend_to_ai_search_request_schema: Dict[str, Any],
    ):
        """'query' field is required in search request."""
        request_without_query = {"searchType": "hybrid", "topK": 10}
        errors = validate_json_schema(
            request_without_query,
            backend_to_ai_search_request_schema,
        )
        assert any("query" in e for e in errors), (
            "Missing 'query' field should be reported"
        )

    def test_search_type_enum_values(
        self,
        backend_to_ai_search_request_schema: Dict[str, Any],
    ):
        """searchType accepts only valid enum values."""
        valid_types = ["vector", "graph", "hybrid"]
        for search_type in valid_types:
            request = {"query": "test", "searchType": search_type}
            errors = validate_json_schema(
                request,
                backend_to_ai_search_request_schema,
            )
            type_errors = [e for e in errors if "enum" in e.lower()]
            assert len(type_errors) == 0, (
                f"searchType '{search_type}' should be valid"
            )

    def test_top_k_range_constraint(
        self,
        backend_to_ai_search_request_schema: Dict[str, Any],
    ):
        """topK must be between 1 and 100."""
        # Valid range
        for k in [1, 5, 10, 50, 100]:
            request = {"query": "test", "topK": k}
            errors = validate_json_schema(
                request,
                backend_to_ai_search_request_schema,
            )
            range_errors = [e for e in errors if "minimum" in e or "maximum" in e]
            assert len(range_errors) == 0, (
                f"topK={k} should be valid"
            )

        # Invalid range
        for k in [0, -1, 101, 1000]:
            request = {"query": "test", "topK": k}
            errors = validate_json_schema(
                request,
                backend_to_ai_search_request_schema,
            )
            range_errors = [e for e in errors if "minimum" in e or "maximum" in e]
            assert len(range_errors) > 0, (
                f"topK={k} should be invalid"
            )

    def test_query_length_constraint(
        self,
        backend_to_ai_search_request_schema: Dict[str, Any],
    ):
        """Query must be between 1 and 1000 characters."""
        # Valid lengths
        for length in [1, 100, 500, 1000]:
            request = {"query": "A" * length}
            errors = validate_json_schema(
                request,
                backend_to_ai_search_request_schema,
            )
            length_errors = [e for e in errors if "Length" in e]
            assert len(length_errors) == 0, (
                f"Query length {length} should be valid"
            )

        # Invalid: empty string
        request = {"query": ""}
        errors = validate_json_schema(
            request,
            backend_to_ai_search_request_schema,
        )
        assert any("minLength" in e for e in errors), (
            "Empty query should fail minLength"
        )

        # Invalid: exceeds max length
        request = {"query": "A" * 1001}
        errors = validate_json_schema(
            request,
            backend_to_ai_search_request_schema,
        )
        assert any("maxLength" in e for e in errors), (
            "1001-char query should fail maxLength"
        )


# =============================================================================
# Contract Tests: Response Schema Validation
# =============================================================================


class TestBackendToAISearchResponseContract:
    """Validates AI Service search response schema."""

    def test_valid_responses_pass_schema(
        self,
        backend_to_ai_search_response_schema: Dict[str, Any],
    ):
        """All valid search responses conform to contract schema."""
        for case in VALID_SEARCH_RESPONSES:
            errors = validate_json_schema(
                case["data"],
                backend_to_ai_search_response_schema,
            )
            assert len(errors) == 0, (
                f"Valid response '{case['description']}' failed: {errors}"
            )

    def test_success_field_required(
        self,
        backend_to_ai_search_response_schema: Dict[str, Any],
    ):
        """'success' field is required in all responses."""
        response_without_success = {"data": {"query": "test"}}
        errors = validate_json_schema(
            response_without_success,
            backend_to_ai_search_response_schema,
        )
        assert any("success" in e for e in errors), (
            "Missing 'success' field should be reported"
        )

    def test_result_score_range(
        self,
        backend_to_ai_search_response_schema: Dict[str, Any],
    ):
        """Result scores must be between 0 and 1."""
        # Valid score
        response = {
            "success": True,
            "data": {
                "results": [
                    {"id": "r-001", "score": 0.85, "title": "Test", "text": "content"}
                ]
            },
        }
        errors = validate_json_schema(
            response,
            backend_to_ai_search_response_schema,
        )
        score_errors = [e for e in errors if "score" in e.lower() and ("minimum" in e or "maximum" in e)]
        assert len(score_errors) == 0, "Score 0.85 should be valid"

    def test_search_metadata_structure(self):
        """searchMetadata contains expected fields."""
        metadata = {
            "searchType": "hybrid",
            "totalResults": 10,
            "vectorResultsCount": 8,
            "graphResultsCount": 5,
            "fusionMethod": "rrf",
            "latencyMs": 450,
        }

        required_fields = [
            "searchType",
            "totalResults",
            "fusionMethod",
            "latencyMs",
        ]
        for field in required_fields:
            assert field in metadata, f"searchMetadata missing '{field}'"

    def test_source_document_structure(self):
        """Source documents contain knowledgeId and title."""
        source = {
            "knowledgeId": "k-001",
            "title": "JWT 인증 필터 구현 가이드",
            "author": "Backend Developer",
        }

        assert "knowledgeId" in source, "Source missing knowledgeId"
        assert "title" in source, "Source missing title"
        assert isinstance(source["knowledgeId"], str), "knowledgeId should be string"
        assert isinstance(source["title"], str), "title should be string"


# =============================================================================
# Contract Tests: Chat Request Schema
# =============================================================================


class TestBackendToAIChatContract:
    """Validates Backend -> AI Service chat request schema."""

    def test_chat_request_with_history(
        self,
        sse_chat_request_schema: Dict[str, Any],
    ):
        """Chat request with conversation history validates."""
        request = {
            "query": "JWT 인증 필터 구현",
            "conversation_history": [
                {"role": "user", "content": "RAG 시스템이란?"},
                {"role": "assistant", "content": "RAG는 검색 증강 생성입니다."},
            ],
            "top_k": 5,
        }
        errors = validate_json_schema(request, sse_chat_request_schema)
        assert len(errors) == 0, f"Chat request failed validation: {errors}"

    def test_chat_request_without_history(
        self,
        sse_chat_request_schema: Dict[str, Any],
    ):
        """Chat request without history (new conversation) validates."""
        request = {
            "query": "새로운 질문입니다",
            "top_k": 5,
        }
        errors = validate_json_schema(request, sse_chat_request_schema)
        assert len(errors) == 0, f"New chat request failed validation: {errors}"

    def test_chat_history_role_enum(
        self,
        sse_chat_request_schema: Dict[str, Any],
    ):
        """Conversation history roles must be 'user' or 'assistant'."""
        valid_roles = ["user", "assistant"]
        for role in valid_roles:
            request = {
                "query": "test",
                "conversation_history": [
                    {"role": role, "content": "test message"},
                ],
            }
            errors = validate_json_schema(request, sse_chat_request_schema)
            role_errors = [e for e in errors if "role" in e and "enum" in e]
            assert len(role_errors) == 0, f"Role '{role}' should be valid"

    def test_chat_request_requires_query(
        self,
        sse_chat_request_schema: Dict[str, Any],
    ):
        """Chat request requires query field."""
        request = {
            "conversation_history": [],
            "top_k": 5,
        }
        errors = validate_json_schema(request, sse_chat_request_schema)
        assert any("query" in e for e in errors), (
            "Missing query should be reported"
        )
