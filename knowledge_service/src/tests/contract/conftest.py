"""
Contract Test Configuration and Shared Fixtures

Provides JSON Schema definitions and validation utilities for
service-to-service API contract testing.

Author: QA Agent
Sprint: Sprint 04 Day 3
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

# Project root path setup
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))


# =============================================================================
# Pytest Configuration
# =============================================================================


def pytest_configure(config):
    """Register custom pytest markers for contract tests."""
    config.addinivalue_line("markers", "contract: Contract tests (service-to-service)")
    config.addinivalue_line("markers", "sprint04_fb_e2e: Sprint 04 Frontend/Backend E2E")


# =============================================================================
# JSON Schema Definitions
# =============================================================================


@pytest.fixture
def backend_to_ai_search_request_schema() -> Dict[str, Any]:
    """JSON Schema for Backend -> AI Service search request.

    POST /internal/v1/search/hybrid
    or POST /api/v1/search
    """
    return {
        "type": "object",
        "required": ["query"],
        "properties": {
            "query": {"type": "string", "minLength": 1, "maxLength": 1000},
            "searchType": {
                "type": "string",
                "enum": ["vector", "graph", "hybrid"],
            },
            "topK": {"type": "integer", "minimum": 1, "maximum": 100},
            "filters": {
                "type": "object",
                "properties": {
                    "projectName": {"type": "string"},
                    "documentType": {"type": "string"},
                    "dateRange": {
                        "type": "object",
                        "properties": {
                            "start": {"type": "string", "format": "date"},
                            "end": {"type": "string", "format": "date"},
                        },
                    },
                    "categories": {
                        "type": "object",
                        "properties": {
                            "level1": {"type": "string"},
                            "level2": {"type": "string"},
                        },
                    },
                    "author": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
            },
            "includeAnswer": {"type": "boolean"},
            "includeGraphContext": {"type": "boolean"},
        },
    }


@pytest.fixture
def backend_to_ai_search_response_schema() -> Dict[str, Any]:
    """JSON Schema for AI Service search response.

    Response from POST /internal/v1/search/hybrid
    """
    return {
        "type": "object",
        "required": ["success"],
        "properties": {
            "success": {"type": "boolean"},
            "data": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "answer": {"type": "string"},
                    "results": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "knowledgeId": {"type": "string"},
                                "title": {"type": "string"},
                                "text": {"type": "string"},
                                "score": {"type": "number", "minimum": 0, "maximum": 1},
                                "metadata": {"type": "object"},
                                "graphContext": {"type": "object"},
                            },
                        },
                    },
                    "searchMetadata": {
                        "type": "object",
                        "properties": {
                            "searchType": {"type": "string"},
                            "totalResults": {"type": "integer"},
                            "vectorResultsCount": {"type": "integer"},
                            "graphResultsCount": {"type": "integer"},
                            "fusionMethod": {"type": "string"},
                            "latencyMs": {"type": "number"},
                        },
                    },
                    "sources": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "knowledgeId": {"type": "string"},
                                "title": {"type": "string"},
                                "author": {"type": "string"},
                            },
                        },
                    },
                },
            },
        },
    }


@pytest.fixture
def ai_to_knowledge_retriever_request_schema() -> Dict[str, Any]:
    """JSON Schema for AI Service -> Knowledge Service retriever request.

    POST /internal/v1/search/retrieve
    """
    return {
        "type": "object",
        "required": ["query"],
        "properties": {
            "query": {"type": "string", "minLength": 1},
            "top_k": {"type": "integer", "minimum": 1, "maximum": 100},
            "search_type": {
                "type": "string",
                "enum": ["vector", "keyword", "graph", "hybrid"],
            },
            "filters": {"type": "object"},
            "embedding": {
                "type": "array",
                "items": {"type": "number"},
            },
        },
    }


@pytest.fixture
def ai_to_knowledge_retriever_response_schema() -> Dict[str, Any]:
    """JSON Schema for Knowledge Service retriever response."""
    return {
        "type": "object",
        "properties": {
            "documents": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "content": {"type": "string"},
                        "metadata": {"type": "object"},
                        "score": {"type": "number"},
                        "source": {"type": "string"},
                    },
                },
            },
            "total": {"type": "integer"},
            "search_type": {"type": "string"},
        },
    }


@pytest.fixture
def sse_token_event_schema() -> Dict[str, Any]:
    """JSON Schema for SSE token event."""
    return {
        "type": "object",
        "required": ["type", "content"],
        "properties": {
            "type": {"type": "string", "const": "token"},
            "content": {"type": "string"},
        },
    }


@pytest.fixture
def sse_sources_event_schema() -> Dict[str, Any]:
    """JSON Schema for SSE sources event."""
    return {
        "type": "object",
        "required": ["type", "content"],
        "properties": {
            "type": {"type": "string", "const": "sources"},
            "content": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["knowledgeId", "title"],
                    "properties": {
                        "knowledgeId": {"type": "string"},
                        "title": {"type": "string"},
                        "author": {"type": "string"},
                    },
                },
            },
        },
    }


@pytest.fixture
def sse_done_event_schema() -> Dict[str, Any]:
    """JSON Schema for SSE done event."""
    return {
        "type": "object",
        "required": ["type"],
        "properties": {
            "type": {"type": "string", "const": "done"},
            "conversationId": {"type": "string"},
        },
    }


@pytest.fixture
def sse_chat_request_schema() -> Dict[str, Any]:
    """JSON Schema for SSE chat stream request.

    POST /api/v1/search/chat/stream
    """
    return {
        "type": "object",
        "required": ["query"],
        "properties": {
            "query": {"type": "string", "minLength": 1},
            "conversation_history": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["role", "content"],
                    "properties": {
                        "role": {"type": "string", "enum": ["user", "assistant"]},
                        "content": {"type": "string"},
                    },
                },
            },
            "top_k": {"type": "integer", "minimum": 1, "maximum": 100},
            "conversationId": {"type": ["string", "null"]},
            "filters": {"type": "object"},
        },
    }


# =============================================================================
# Schema Validation Utility
# =============================================================================


def validate_json_schema(data: Any, schema: Dict[str, Any]) -> List[str]:
    """Validate data against a JSON Schema and return list of errors.

    Simple validation without jsonschema library dependency.
    Validates type, required fields, enums, and basic constraints.

    Args:
        data: Data to validate
        schema: JSON Schema dict

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    if not isinstance(data, dict) and schema.get("type") == "object":
        errors.append(f"Expected object, got {type(data).__name__}")
        return errors

    # Check type
    expected_type = schema.get("type")
    if expected_type:
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
            "null": type(None),
        }
        if isinstance(expected_type, list):
            # Union type
            expected = tuple(type_map.get(t, object) for t in expected_type)
            if not isinstance(data, expected):
                errors.append(f"Expected one of {expected_type}, got {type(data).__name__}")
        elif expected_type in type_map:
            expected = type_map[expected_type]
            if not isinstance(data, expected):
                errors.append(f"Expected {expected_type}, got {type(data).__name__}")

    # Check required fields
    if isinstance(data, dict):
        required = schema.get("required", [])
        for field in required:
            if field not in data:
                errors.append(f"Missing required field: '{field}'")

        # Check properties
        properties = schema.get("properties", {})
        for field_name, field_schema in properties.items():
            if field_name in data:
                field_errors = validate_json_schema(data[field_name], field_schema)
                errors.extend(
                    f"{field_name}.{e}" for e in field_errors
                )

    # Check enum
    if "enum" in schema and data not in schema["enum"]:
        errors.append(f"Value '{data}' not in enum {schema['enum']}")

    # Check const
    if "const" in schema and data != schema["const"]:
        errors.append(f"Value '{data}' does not match const '{schema['const']}'")

    # Check string constraints
    if isinstance(data, str):
        if "minLength" in schema and len(data) < schema["minLength"]:
            errors.append(f"String length {len(data)} < minLength {schema['minLength']}")
        if "maxLength" in schema and len(data) > schema["maxLength"]:
            errors.append(f"String length {len(data)} > maxLength {schema['maxLength']}")

    # Check number constraints
    if isinstance(data, (int, float)):
        if "minimum" in schema and data < schema["minimum"]:
            errors.append(f"Value {data} < minimum {schema['minimum']}")
        if "maximum" in schema and data > schema["maximum"]:
            errors.append(f"Value {data} > maximum {schema['maximum']}")

    # Check array items
    if isinstance(data, list) and "items" in schema:
        for i, item in enumerate(data):
            item_errors = validate_json_schema(item, schema["items"])
            errors.extend(f"[{i}].{e}" for e in item_errors)

    return errors
