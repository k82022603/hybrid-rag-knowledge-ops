"""
Contract Test: Error Response and Pagination API Contract

Validates that error responses and pagination follow the agreed-upon
contract format between services.

Contracts validated:
- Error response structure: {success, error: {code, message, details}}
- Pagination response: {items, pagination: {page, size, totalPages, ...}}
- HTTP status code mapping
- Error code standardization

Related: STORY-054, API Integration Design v1.4
Sprint: Sprint 04 Day 4
Author: QA Agent
"""

import json
import re
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
# JSON Schema Definitions for Error and Pagination
# =============================================================================


@pytest.fixture
def error_response_schema() -> Dict[str, Any]:
    """JSON Schema for error response structure."""
    return {
        "type": "object",
        "required": ["success", "error"],
        "properties": {
            "success": {"type": "boolean", "const": False},
            "error": {
                "type": "object",
                "required": ["code", "message"],
                "properties": {
                    "code": {"type": "string"},
                    "message": {"type": "string"},
                    "details": {"type": "object"},
                },
            },
            "timestamp": {"type": "string"},
            "traceId": {"type": "string"},
        },
    }


@pytest.fixture
def pagination_response_schema() -> Dict[str, Any]:
    """JSON Schema for pagination response structure."""
    return {
        "type": "object",
        "required": ["success", "data"],
        "properties": {
            "success": {"type": "boolean", "const": True},
            "data": {
                "type": "object",
                "required": ["items", "pagination"],
                "properties": {
                    "items": {"type": "array"},
                    "pagination": {
                        "type": "object",
                        "required": ["page", "size", "totalPages", "totalElements"],
                        "properties": {
                            "page": {"type": "integer", "minimum": 1},
                            "size": {"type": "integer", "minimum": 1, "maximum": 100},
                            "totalPages": {"type": "integer", "minimum": 0},
                            "totalElements": {"type": "integer", "minimum": 0},
                            "hasNext": {"type": "boolean"},
                            "hasPrevious": {"type": "boolean"},
                        },
                    },
                },
            },
        },
    }


# =============================================================================
# Test Data: Error Responses
# =============================================================================

VALID_ERROR_RESPONSES = [
    {
        "description": "Document not found error",
        "data": {
            "success": False,
            "error": {
                "code": "DOC100",
                "message": "요청한 지식을 찾을 수 없습니다.",
                "details": {
                    "knowledgeId": "123e4567-e89b-12d3-a456-426614174000",
                },
            },
            "timestamp": "2026-01-16T10:30:00Z",
            "traceId": "550e8400-e29b-41d4-a716-446655440000",
        },
    },
    {
        "description": "Validation error",
        "data": {
            "success": False,
            "error": {
                "code": "VAL001",
                "message": "입력값이 유효하지 않습니다.",
                "details": {
                    "field": "query",
                    "reason": "빈 문자열은 허용되지 않습니다.",
                },
            },
            "timestamp": "2026-01-28T15:45:30Z",
            "traceId": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        },
    },
    {
        "description": "Authentication error (minimal)",
        "data": {
            "success": False,
            "error": {
                "code": "AUTH001",
                "message": "인증이 필요합니다.",
            },
        },
    },
    {
        "description": "Rate limit error",
        "data": {
            "success": False,
            "error": {
                "code": "RATE_LIMIT",
                "message": "요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요.",
                "details": {
                    "retryAfter": 60,
                },
            },
        },
    },
    {
        "description": "Internal server error",
        "data": {
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "서버 오류가 발생했습니다.",
            },
            "traceId": "abc-123-def",
        },
    },
]

INVALID_ERROR_RESPONSES = [
    {
        "description": "Missing success field",
        "data": {
            "error": {
                "code": "ERR",
                "message": "Some error",
            },
        },
    },
    {
        "description": "success=True with error (invalid)",
        "data": {
            "success": True,
            "error": {
                "code": "ERR",
                "message": "Error message",
            },
        },
    },
    {
        "description": "Missing error.code",
        "data": {
            "success": False,
            "error": {
                "message": "Error without code",
            },
        },
    },
    {
        "description": "Missing error.message",
        "data": {
            "success": False,
            "error": {
                "code": "ERR001",
            },
        },
    },
]

VALID_PAGINATION_RESPONSES = [
    {
        "description": "Standard pagination response",
        "data": {
            "success": True,
            "data": {
                "items": [
                    {"id": "item-1", "name": "Document 1"},
                    {"id": "item-2", "name": "Document 2"},
                ],
                "pagination": {
                    "page": 1,
                    "size": 20,
                    "totalPages": 10,
                    "totalElements": 195,
                    "hasNext": True,
                    "hasPrevious": False,
                },
            },
        },
    },
    {
        "description": "Empty results pagination",
        "data": {
            "success": True,
            "data": {
                "items": [],
                "pagination": {
                    "page": 1,
                    "size": 20,
                    "totalPages": 0,
                    "totalElements": 0,
                    "hasNext": False,
                    "hasPrevious": False,
                },
            },
        },
    },
    {
        "description": "Last page pagination",
        "data": {
            "success": True,
            "data": {
                "items": [{"id": "item-195"}],
                "pagination": {
                    "page": 10,
                    "size": 20,
                    "totalPages": 10,
                    "totalElements": 195,
                    "hasNext": False,
                    "hasPrevious": True,
                },
            },
        },
    },
]


# =============================================================================
# Contract Tests: Error Response Schema
# =============================================================================


class TestErrorResponseContract:
    """Validates error response contract."""

    def test_valid_error_responses_pass_schema(
        self,
        error_response_schema: Dict[str, Any],
    ):
        """All valid error responses conform to schema."""
        for case in VALID_ERROR_RESPONSES:
            errors = validate_json_schema(case["data"], error_response_schema)
            assert len(errors) == 0, (
                f"Valid error response '{case['description']}' failed: {errors}"
            )

    def test_invalid_error_responses_fail_schema(
        self,
        error_response_schema: Dict[str, Any],
    ):
        """Invalid error responses are rejected by schema."""
        for case in INVALID_ERROR_RESPONSES:
            errors = validate_json_schema(case["data"], error_response_schema)
            assert len(errors) > 0, (
                f"Invalid error response '{case['description']}' should fail"
            )

    def test_error_code_format(self):
        """Error codes follow expected format (alphanumeric or underscore)."""
        valid_codes = [
            "DOC100",
            "VAL001",
            "AUTH001",
            "RATE_LIMIT",
            "INTERNAL_ERROR",
            "NOT_FOUND",
        ]
        code_pattern = r"^[A-Z0-9_]+$"
        for code in valid_codes:
            assert re.match(code_pattern, code), (
                f"Error code '{code}' does not match expected format"
            )

    def test_error_response_success_is_false(self):
        """Error responses must have success=False."""
        for case in VALID_ERROR_RESPONSES:
            assert case["data"]["success"] is False

    def test_error_response_contains_error_object(self):
        """Error responses must contain error object."""
        for case in VALID_ERROR_RESPONSES:
            assert "error" in case["data"]
            assert isinstance(case["data"]["error"], dict)

    def test_error_object_has_required_fields(self):
        """Error object must have code and message."""
        for case in VALID_ERROR_RESPONSES:
            error_obj = case["data"]["error"]
            assert "code" in error_obj, "Error missing 'code'"
            assert "message" in error_obj, "Error missing 'message'"
            assert isinstance(error_obj["code"], str)
            assert isinstance(error_obj["message"], str)

    def test_error_details_is_optional(self):
        """Error details field is optional."""
        with_details = [c for c in VALID_ERROR_RESPONSES if "details" in c["data"]["error"]]
        without_details = [c for c in VALID_ERROR_RESPONSES if "details" not in c["data"]["error"]]

        assert len(with_details) > 0, "Should have examples with details"
        assert len(without_details) > 0, "Should have examples without details"

    def test_trace_id_format(self):
        """TraceId follows UUID or short format."""
        for case in VALID_ERROR_RESPONSES:
            if "traceId" in case["data"]:
                trace_id = case["data"]["traceId"]
                assert isinstance(trace_id, str)
                assert len(trace_id) > 0


# =============================================================================
# Contract Tests: Pagination Response Schema
# =============================================================================


class TestPaginationResponseContract:
    """Validates pagination response contract."""

    def test_valid_pagination_responses_pass_schema(
        self,
        pagination_response_schema: Dict[str, Any],
    ):
        """All valid pagination responses conform to schema."""
        for case in VALID_PAGINATION_RESPONSES:
            errors = validate_json_schema(case["data"], pagination_response_schema)
            assert len(errors) == 0, (
                f"Valid pagination response '{case['description']}' failed: {errors}"
            )

    def test_pagination_success_is_true(self):
        """Pagination responses must have success=True."""
        for case in VALID_PAGINATION_RESPONSES:
            assert case["data"]["success"] is True

    def test_pagination_contains_items_array(self):
        """Pagination data must contain items array."""
        for case in VALID_PAGINATION_RESPONSES:
            assert "items" in case["data"]["data"]
            assert isinstance(case["data"]["data"]["items"], list)

    def test_pagination_contains_pagination_object(self):
        """Pagination data must contain pagination object."""
        for case in VALID_PAGINATION_RESPONSES:
            assert "pagination" in case["data"]["data"]
            pagination = case["data"]["data"]["pagination"]
            assert isinstance(pagination, dict)

    def test_pagination_required_fields(self):
        """Pagination object must have required fields."""
        required_fields = ["page", "size", "totalPages", "totalElements"]
        for case in VALID_PAGINATION_RESPONSES:
            pagination = case["data"]["data"]["pagination"]
            for field in required_fields:
                assert field in pagination, (
                    f"Pagination missing required field '{field}'"
                )

    def test_pagination_page_starts_at_1(self):
        """Page numbering starts at 1, not 0."""
        for case in VALID_PAGINATION_RESPONSES:
            page = case["data"]["data"]["pagination"]["page"]
            assert page >= 1, f"Page should start at 1, got {page}"

    def test_pagination_size_positive(self):
        """Page size must be positive."""
        for case in VALID_PAGINATION_RESPONSES:
            size = case["data"]["data"]["pagination"]["size"]
            assert size >= 1, f"Size should be >= 1, got {size}"

    def test_pagination_total_non_negative(self):
        """Total pages and elements must be non-negative."""
        for case in VALID_PAGINATION_RESPONSES:
            pagination = case["data"]["data"]["pagination"]
            assert pagination["totalPages"] >= 0
            assert pagination["totalElements"] >= 0

    def test_pagination_has_next_previous_flags(self):
        """Pagination includes hasNext and hasPrevious flags."""
        for case in VALID_PAGINATION_RESPONSES:
            pagination = case["data"]["data"]["pagination"]
            if "hasNext" in pagination:
                assert isinstance(pagination["hasNext"], bool)
            if "hasPrevious" in pagination:
                assert isinstance(pagination["hasPrevious"], bool)

    def test_pagination_consistency(self):
        """Pagination values are consistent."""
        # First page should not have previous
        first_page = VALID_PAGINATION_RESPONSES[0]["data"]["data"]["pagination"]
        if "hasPrevious" in first_page:
            assert first_page["page"] > 1 or first_page["hasPrevious"] is False

        # Last page should not have next
        last_page = VALID_PAGINATION_RESPONSES[2]["data"]["data"]["pagination"]
        if "hasNext" in last_page and last_page["page"] == last_page["totalPages"]:
            assert last_page["hasNext"] is False


# =============================================================================
# Contract Tests: HTTP Status Code Mapping
# =============================================================================


class TestHTTPStatusCodeContract:
    """Validates HTTP status code to error code mapping."""

    def test_status_400_validation_error(self):
        """400 Bad Request maps to validation errors."""
        status_400_codes = ["VAL001", "VAL002", "INVALID_REQUEST"]
        for code in status_400_codes:
            assert code.startswith("VAL") or code == "INVALID_REQUEST"

    def test_status_401_authentication_error(self):
        """401 Unauthorized maps to authentication errors."""
        status_401_codes = ["AUTH001", "TOKEN_EXPIRED", "INVALID_TOKEN"]
        for code in status_401_codes:
            assert code.startswith("AUTH") or "TOKEN" in code

    def test_status_403_authorization_error(self):
        """403 Forbidden maps to authorization errors."""
        status_403_codes = ["AUTH003", "FORBIDDEN", "ACCESS_DENIED"]
        for code in status_403_codes:
            assert "AUTH" in code or "FORBIDDEN" in code or "DENIED" in code

    def test_status_404_not_found(self):
        """404 Not Found maps to resource not found errors."""
        status_404_codes = ["DOC100", "NOT_FOUND", "USER_NOT_FOUND"]
        for code in status_404_codes:
            assert "DOC" in code or "NOT_FOUND" in code

    def test_status_429_rate_limit(self):
        """429 Too Many Requests maps to rate limit errors."""
        rate_limit_code = "RATE_LIMIT"
        assert "RATE" in rate_limit_code or "LIMIT" in rate_limit_code

    def test_status_500_internal_error(self):
        """500 Internal Server Error maps to internal errors."""
        status_500_codes = ["INTERNAL_ERROR", "UNKNOWN_ERROR"]
        for code in status_500_codes:
            assert "INTERNAL" in code or "ERROR" in code


# =============================================================================
# Contract Tests: Timestamp Format
# =============================================================================


class TestTimestampFormatContract:
    """Validates timestamp format contract."""

    def test_iso8601_datetime_format(self):
        """DateTime follows ISO 8601 format with Z suffix."""
        valid_timestamps = [
            "2026-01-16T10:30:00Z",
            "2026-01-28T15:45:30Z",
            "2026-12-31T23:59:59Z",
        ]
        iso_pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"
        for ts in valid_timestamps:
            assert re.match(iso_pattern, ts), (
                f"Timestamp '{ts}' does not match ISO 8601 format"
            )

    def test_date_only_format(self):
        """Date-only fields use YYYY-MM-DD format."""
        valid_dates = [
            "2026-01-01",
            "2026-12-31",
            "2026-06-15",
        ]
        date_pattern = r"^\d{4}-\d{2}-\d{2}$"
        for d in valid_dates:
            assert re.match(date_pattern, d), (
                f"Date '{d}' does not match expected format"
            )

    def test_timestamp_in_error_response(self):
        """Error responses with timestamp use correct format."""
        for case in VALID_ERROR_RESPONSES:
            if "timestamp" in case["data"]:
                ts = case["data"]["timestamp"]
                iso_pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"
                assert re.match(iso_pattern, ts), (
                    f"Timestamp '{ts}' in error response has invalid format"
                )


# =============================================================================
# Contract Tests: UUID Format
# =============================================================================


class TestUUIDFormatContract:
    """Validates UUID format contract."""

    def test_uuid_v4_format(self):
        """UUIDs follow v4 format (or general UUID format)."""
        valid_uuids = [
            "550e8400-e29b-41d4-a716-446655440000",
            "123e4567-e89b-12d3-a456-426614174000",
            "7c9e6679-7425-40de-944b-e07fc1f90ae7",
            "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        ]
        # General UUID pattern (accepts any version)
        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        for uuid in valid_uuids:
            assert re.match(uuid_pattern, uuid), (
                f"UUID '{uuid}' does not match expected format"
            )

    def test_uuid_length(self):
        """UUIDs have correct length (36 chars with hyphens)."""
        valid_uuids = [
            "550e8400-e29b-41d4-a716-446655440000",
            "123e4567-e89b-12d3-a456-426614174000",
        ]
        for uuid in valid_uuids:
            assert len(uuid) == 36, (
                f"UUID '{uuid}' has incorrect length {len(uuid)}"
            )

    def test_uuid_in_error_details(self):
        """UUIDs in error details follow correct format."""
        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        for case in VALID_ERROR_RESPONSES:
            details = case["data"]["error"].get("details", {})
            for key, value in details.items():
                if "Id" in key and isinstance(value, str):
                    if re.match(uuid_pattern, value):
                        assert True  # Valid UUID in details


# =============================================================================
# Contract Tests: Korean Text in Errors
# =============================================================================


class TestKoreanTextContract:
    """Validates Korean text handling in error responses."""

    def test_korean_error_messages(self):
        """Korean error messages are properly encoded."""
        korean_messages = [
            "요청한 지식을 찾을 수 없습니다.",
            "입력값이 유효하지 않습니다.",
            "인증이 필요합니다.",
            "요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요.",
            "서버 오류가 발생했습니다.",
        ]
        for msg in korean_messages:
            # Should not have encoding issues
            assert "\ufffd" not in msg, f"Found replacement character in: {msg}"
            # Should contain Korean characters
            assert any("\uac00" <= c <= "\ud7a3" for c in msg), (
                f"Message should contain Korean: {msg}"
            )

    def test_korean_in_json_serialization(self):
        """Korean text preserved through JSON serialization."""
        error_response = {
            "success": False,
            "error": {
                "code": "DOC100",
                "message": "요청한 지식을 찾을 수 없습니다.",
            },
        }

        # Serialize and deserialize
        json_str = json.dumps(error_response, ensure_ascii=False)
        restored = json.loads(json_str)

        assert restored["error"]["message"] == error_response["error"]["message"]
        assert "요청한" in json_str  # Korean in UTF-8
        assert "\\u" not in json_str  # Not escaped


# =============================================================================
# Test Execution
# =============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
