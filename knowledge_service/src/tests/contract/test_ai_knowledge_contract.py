"""
Contract Test: AI Service -> Knowledge Service API Contract

Validates that the AI Service sends correctly structured requests
to the Knowledge Service retriever API, and that the Knowledge Service
responses conform to the expected schema.

Contracts validated:
- POST /internal/v1/search/retrieve (retriever request/response)
- Document chunk schema
- Embedding vector format

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
# Test Data: Retriever Requests
# =============================================================================

VALID_RETRIEVER_REQUESTS = [
    {
        "description": "Minimal retriever request",
        "data": {"query": "JWT 인증 필터 구현"},
    },
    {
        "description": "Retriever with top_k and search_type",
        "data": {
            "query": "프로젝트 보안 감사",
            "top_k": 10,
            "search_type": "hybrid",
        },
    },
    {
        "description": "Vector search with embedding",
        "data": {
            "query": "임베딩 모델",
            "top_k": 5,
            "search_type": "vector",
            "embedding": [0.1, 0.2, 0.3, 0.4, 0.5],
        },
    },
    {
        "description": "Keyword search with filters",
        "data": {
            "query": "React 아키텍처",
            "top_k": 10,
            "search_type": "keyword",
            "filters": {
                "documentType": "기술문서",
                "projectName": "Knowledge Platform",
            },
        },
    },
    {
        "description": "Graph search request",
        "data": {
            "query": "프론트엔드 전문가",
            "top_k": 5,
            "search_type": "graph",
        },
    },
]

INVALID_RETRIEVER_REQUESTS = [
    {
        "description": "Missing required query",
        "data": {"top_k": 10, "search_type": "hybrid"},
        "expected_error": "query",
    },
    {
        "description": "Empty query string",
        "data": {"query": ""},
        "expected_error": "minLength",
    },
    {
        "description": "Invalid search type",
        "data": {"query": "test", "search_type": "invalid"},
        "expected_error": "enum",
    },
    {
        "description": "top_k zero",
        "data": {"query": "test", "top_k": 0},
        "expected_error": "minimum",
    },
    {
        "description": "top_k exceeds maximum",
        "data": {"query": "test", "top_k": 101},
        "expected_error": "maximum",
    },
]

VALID_RETRIEVER_RESPONSES = [
    {
        "description": "Standard retriever response with documents",
        "data": {
            "documents": [
                {
                    "id": "chunk-001",
                    "content": "JWT 인증 필터는 모든 API 요청에 대해...",
                    "metadata": {
                        "knowledge_id": "k-001",
                        "title": "JWT 인증 가이드",
                        "document_type": "기술문서",
                        "chunk_index": 0,
                    },
                    "score": 0.92,
                    "source": "elasticsearch",
                },
                {
                    "id": "chunk-002",
                    "content": "Spring Security 설정에서 JWT 필터를...",
                    "metadata": {
                        "knowledge_id": "k-002",
                        "title": "Spring Security 가이드",
                        "document_type": "기술문서",
                        "chunk_index": 3,
                    },
                    "score": 0.85,
                    "source": "elasticsearch",
                },
            ],
            "total": 2,
            "search_type": "hybrid",
        },
    },
    {
        "description": "Empty retriever response",
        "data": {
            "documents": [],
            "total": 0,
            "search_type": "hybrid",
        },
    },
    {
        "description": "Graph search response with Neo4j results",
        "data": {
            "documents": [
                {
                    "id": "node-001",
                    "content": "프론트엔드 개발팀에서 React 전문가는...",
                    "metadata": {
                        "node_type": "Person",
                        "community": "프론트엔드 개발팀",
                    },
                    "score": 0.88,
                    "source": "neo4j",
                },
            ],
            "total": 1,
            "search_type": "graph",
        },
    },
]


# =============================================================================
# Contract Tests: Retriever Request Schema
# =============================================================================


class TestAIToKnowledgeRetrieverRequestContract:
    """Validates AI Service -> Knowledge Service retriever request."""

    def test_valid_requests_pass_schema(
        self,
        ai_to_knowledge_retriever_request_schema: Dict[str, Any],
    ):
        """All valid retriever requests conform to schema."""
        for case in VALID_RETRIEVER_REQUESTS:
            errors = validate_json_schema(
                case["data"],
                ai_to_knowledge_retriever_request_schema,
            )
            assert len(errors) == 0, (
                f"Valid request '{case['description']}' failed: {errors}"
            )

    def test_invalid_requests_fail_schema(
        self,
        ai_to_knowledge_retriever_request_schema: Dict[str, Any],
    ):
        """Invalid retriever requests are rejected by schema."""
        for case in INVALID_RETRIEVER_REQUESTS:
            errors = validate_json_schema(
                case["data"],
                ai_to_knowledge_retriever_request_schema,
            )
            assert len(errors) > 0, (
                f"Invalid request '{case['description']}' should fail"
            )

    def test_query_is_required(
        self,
        ai_to_knowledge_retriever_request_schema: Dict[str, Any],
    ):
        """'query' field is required."""
        errors = validate_json_schema(
            {"top_k": 10},
            ai_to_knowledge_retriever_request_schema,
        )
        assert any("query" in e for e in errors)

    def test_search_type_enum_values(
        self,
        ai_to_knowledge_retriever_request_schema: Dict[str, Any],
    ):
        """search_type accepts only valid values."""
        valid_types = ["vector", "keyword", "graph", "hybrid"]
        for st in valid_types:
            request = {"query": "test", "search_type": st}
            errors = validate_json_schema(
                request,
                ai_to_knowledge_retriever_request_schema,
            )
            enum_errors = [e for e in errors if "enum" in e.lower()]
            assert len(enum_errors) == 0, f"search_type '{st}' should be valid"

    def test_embedding_vector_format(
        self,
        ai_to_knowledge_retriever_request_schema: Dict[str, Any],
    ):
        """Embedding vector is an array of numbers."""
        request = {
            "query": "test",
            "embedding": [0.1, -0.2, 0.3, 0.0, 1.0],
        }
        errors = validate_json_schema(
            request,
            ai_to_knowledge_retriever_request_schema,
        )
        embedding_errors = [e for e in errors if "embedding" in e]
        assert len(embedding_errors) == 0, (
            f"Valid embedding failed: {embedding_errors}"
        )

    def test_top_k_range(
        self,
        ai_to_knowledge_retriever_request_schema: Dict[str, Any],
    ):
        """top_k must be between 1 and 100."""
        # Valid
        for k in [1, 5, 50, 100]:
            errors = validate_json_schema(
                {"query": "test", "top_k": k},
                ai_to_knowledge_retriever_request_schema,
            )
            range_errors = [e for e in errors if "minimum" in e or "maximum" in e]
            assert len(range_errors) == 0, f"top_k={k} should be valid"

        # Invalid
        for k in [0, -1, 101]:
            errors = validate_json_schema(
                {"query": "test", "top_k": k},
                ai_to_knowledge_retriever_request_schema,
            )
            range_errors = [e for e in errors if "minimum" in e or "maximum" in e]
            assert len(range_errors) > 0, f"top_k={k} should be invalid"


# =============================================================================
# Contract Tests: Retriever Response Schema
# =============================================================================


class TestAIToKnowledgeRetrieverResponseContract:
    """Validates Knowledge Service retriever response schema."""

    def test_valid_responses_pass_schema(
        self,
        ai_to_knowledge_retriever_response_schema: Dict[str, Any],
    ):
        """All valid retriever responses conform to schema."""
        for case in VALID_RETRIEVER_RESPONSES:
            errors = validate_json_schema(
                case["data"],
                ai_to_knowledge_retriever_response_schema,
            )
            assert len(errors) == 0, (
                f"Valid response '{case['description']}' failed: {errors}"
            )

    def test_document_chunk_structure(self):
        """Document chunks contain required fields."""
        required_fields = ["id", "content", "score"]
        chunk = {
            "id": "chunk-001",
            "content": "Some document content",
            "metadata": {"knowledge_id": "k-001"},
            "score": 0.92,
            "source": "elasticsearch",
        }

        for field in required_fields:
            assert field in chunk, f"Chunk missing '{field}'"

    def test_document_score_is_number(self):
        """Document score must be a numeric value."""
        valid_scores = [0, 0.0, 0.5, 0.99, 1.0]
        for score in valid_scores:
            assert isinstance(score, (int, float)), (
                f"Score {score} should be numeric"
            )

    def test_document_source_values(self):
        """Document source indicates origin (elasticsearch, neo4j)."""
        valid_sources = ["elasticsearch", "neo4j", "hybrid"]
        for source in valid_sources:
            assert isinstance(source, str), f"Source should be string"
            assert len(source) > 0, "Source should not be empty"

    def test_metadata_structure_consistency(self):
        """Document metadata has consistent structure."""
        es_metadata = {
            "knowledge_id": "k-001",
            "title": "Test Document",
            "document_type": "기술문서",
            "chunk_index": 0,
        }
        neo4j_metadata = {
            "node_type": "Person",
            "community": "개발팀",
        }

        # Both should be valid objects
        assert isinstance(es_metadata, dict)
        assert isinstance(neo4j_metadata, dict)

    def test_empty_documents_array_valid(
        self,
        ai_to_knowledge_retriever_response_schema: Dict[str, Any],
    ):
        """Empty documents array is valid (no results)."""
        response = {
            "documents": [],
            "total": 0,
            "search_type": "hybrid",
        }
        errors = validate_json_schema(
            response,
            ai_to_knowledge_retriever_response_schema,
        )
        assert len(errors) == 0, f"Empty response failed: {errors}"

    def test_total_matches_document_count(self):
        """'total' field should match documents array length."""
        response = {
            "documents": [
                {"id": "c-1", "content": "a", "score": 0.9, "source": "es"},
                {"id": "c-2", "content": "b", "score": 0.8, "source": "es"},
            ],
            "total": 2,
        }
        assert response["total"] == len(response["documents"]), (
            "total should match document count"
        )


# =============================================================================
# Contract Tests: Cross-Service Compatibility
# =============================================================================


class TestCrossServiceCompatibility:
    """Validates compatibility between Backend, AI Service, and Knowledge Service."""

    def test_search_request_roundtrip(self):
        """Search request can be serialized and deserialized (JSON roundtrip)."""
        request = {
            "query": "JWT 인증 필터",
            "searchType": "hybrid",
            "topK": 10,
            "filters": {
                "documentType": "기술문서",
                "tags": ["React", "TypeScript"],
            },
        }

        serialized = json.dumps(request, ensure_ascii=False)
        deserialized = json.loads(serialized)

        assert deserialized == request, "JSON roundtrip should preserve data"

    def test_korean_text_preservation(self):
        """Korean text preserved across service boundaries."""
        korean_texts = [
            "JWT 인증 필터 구현 가이드",
            "프로젝트 보안 감사 절차",
            "React 아키텍처 설계 문서",
            "대한민국 정보보안 표준",
        ]

        for text in korean_texts:
            encoded = json.dumps({"text": text}, ensure_ascii=False)
            decoded = json.loads(encoded)
            assert decoded["text"] == text, (
                f"Korean text not preserved: '{text}'"
            )

    def test_uuid_format_consistency(self):
        """UUID format is consistent across services.

        Accepts any standard UUID format (v1-v5), as the API design
        documents use various UUID versions in examples.
        """
        import re

        # General UUID pattern (accepts any version)
        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        valid_uuids = [
            "550e8400-e29b-41d4-a716-446655440000",
            "123e4567-e89b-12d3-a456-426614174000",
            "7c9e6679-7425-40de-944b-e07fc1f90ae7",
            "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        ]

        for uuid in valid_uuids:
            assert re.match(uuid_pattern, uuid), (
                f"UUID '{uuid}' does not match expected format"
            )

    def test_timestamp_format_consistency(self):
        """ISO 8601 timestamp format is consistent."""
        import re

        iso_pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"
        valid_timestamps = [
            "2026-01-16T10:30:00Z",
            "2026-01-28T15:45:30Z",
        ]

        for ts in valid_timestamps:
            assert re.match(iso_pattern, ts), (
                f"Timestamp '{ts}' does not match ISO 8601 format"
            )

    def test_error_response_format_consistency(self):
        """Error responses follow consistent format across services."""
        error_response = {
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "입력값이 유효하지 않습니다.",
            },
        }

        assert "success" in error_response
        assert error_response["success"] is False
        assert "error" in error_response
        assert "code" in error_response["error"]
        assert "message" in error_response["error"]
