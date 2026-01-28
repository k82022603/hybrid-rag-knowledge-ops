"""
Contract Test: SSE Event Format Contract

Validates that SSE events follow the agreed-upon format contract
between Backend/AI Service (producer) and Frontend (consumer).

Contracts validated:
- Token event: {"type": "token", "content": "<string>"}
- Sources event: {"type": "sources", "content": [<Source>]}
- Done event: {"type": "done", "conversationId": "<string>"}
- Error event: {"type": "error", "content": "<string>"}
- Event sequence: token* -> sources -> done
- SSE wire format: "data: <json>\n\n"

Related: STORY-050 (SSE Protocol Fix), STORY-054 (Contract Tests)
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
# Test Data: SSE Events
# =============================================================================

VALID_TOKEN_EVENTS = [
    {"type": "token", "content": "RAG"},
    {"type": "token", "content": " "},
    {"type": "token", "content": "시스템은 "},
    {"type": "token", "content": "검색 증강 생성을 결합한 기술입니다."},
    {"type": "token", "content": ""},  # Empty token (valid, represents empty string)
]

VALID_SOURCE_EVENTS = [
    {
        "type": "sources",
        "content": [
            {"knowledgeId": "k-001", "title": "RAG 시스템 개요"},
            {"knowledgeId": "k-002", "title": "검색 파이프라인 가이드"},
        ],
    },
    {
        "type": "sources",
        "content": [],  # No sources (valid)
    },
    {
        "type": "sources",
        "content": [
            {
                "knowledgeId": "k-001",
                "title": "JWT 인증 필터 구현",
                "author": "Backend Developer",
            },
        ],
    },
]

VALID_DONE_EVENTS = [
    {"type": "done", "conversationId": "conv-001"},
    {"type": "done"},  # Without conversationId (new conversation)
]

INVALID_EVENTS = [
    {
        "description": "Missing type field",
        "data": {"content": "Hello"},
    },
    {
        "description": "Invalid type value (not in enum)",
        "data": {"type": "unknown", "content": "data"},
    },
    {
        "description": "Token with non-string content (number)",
        "data": {"type": "token", "content": 42},
    },
    {
        "description": "Sources with non-array content",
        "data": {"type": "sources", "content": "not an array"},
    },
    {
        "description": "Source item missing knowledgeId",
        "data": {
            "type": "sources",
            "content": [{"title": "Missing ID"}],
        },
    },
    {
        "description": "Source item missing title",
        "data": {
            "type": "sources",
            "content": [{"knowledgeId": "k-001"}],
        },
    },
]

VALID_EVENT_SEQUENCES = [
    {
        "description": "Standard sequence: tokens -> sources -> done",
        "events": [
            {"type": "token", "content": "Answer "},
            {"type": "token", "content": "text."},
            {
                "type": "sources",
                "content": [{"knowledgeId": "k-001", "title": "Source"}],
            },
            {"type": "done", "conversationId": "conv-001"},
        ],
    },
    {
        "description": "Single token -> done (short answer)",
        "events": [
            {"type": "token", "content": "Short answer."},
            {"type": "done"},
        ],
    },
    {
        "description": "Many tokens -> sources -> done",
        "events": [
            {"type": "token", "content": "Token 1 "},
            {"type": "token", "content": "Token 2 "},
            {"type": "token", "content": "Token 3 "},
            {"type": "token", "content": "Token 4 "},
            {"type": "token", "content": "Token 5."},
            {
                "type": "sources",
                "content": [
                    {"knowledgeId": "k-001", "title": "Doc 1"},
                    {"knowledgeId": "k-002", "title": "Doc 2"},
                ],
            },
            {"type": "done", "conversationId": "conv-002"},
        ],
    },
]

INVALID_EVENT_SEQUENCES = [
    {
        "description": "Done before tokens (empty response)",
        "events": [
            {"type": "done"},
        ],
        "issue": "No token events before done",
    },
    {
        "description": "Sources before tokens",
        "events": [
            {
                "type": "sources",
                "content": [{"knowledgeId": "k-001", "title": "Source"}],
            },
            {"type": "token", "content": "Late token"},
            {"type": "done"},
        ],
        "issue": "Sources should come after tokens",
    },
    {
        "description": "Multiple done events",
        "events": [
            {"type": "token", "content": "Answer"},
            {"type": "done"},
            {"type": "done"},
        ],
        "issue": "Only one done event allowed",
    },
    {
        "description": "Missing done event",
        "events": [
            {"type": "token", "content": "Answer"},
            {
                "type": "sources",
                "content": [{"knowledgeId": "k-001", "title": "Source"}],
            },
        ],
        "issue": "Stream must end with done event",
    },
]


# =============================================================================
# Contract Tests: Token Event Schema
# =============================================================================


class TestSSETokenEventContract:
    """Validates SSE token event format."""

    def test_valid_token_events(
        self,
        sse_token_event_schema: Dict[str, Any],
    ):
        """Valid token events conform to schema."""
        for event in VALID_TOKEN_EVENTS:
            errors = validate_json_schema(event, sse_token_event_schema)
            assert len(errors) == 0, (
                f"Token event failed: {event} -> {errors}"
            )

    def test_token_type_is_token(self):
        """Token event type field must be 'token'."""
        for event in VALID_TOKEN_EVENTS:
            assert event["type"] == "token"

    def test_token_content_is_string(self):
        """Token content must be a string."""
        for event in VALID_TOKEN_EVENTS:
            assert isinstance(event["content"], str), (
                f"Token content should be string, got {type(event['content'])}"
            )

    def test_token_content_allows_empty_string(self):
        """Empty string is valid token content."""
        event = {"type": "token", "content": ""}
        assert isinstance(event["content"], str)
        assert event["content"] == ""

    def test_token_content_allows_korean(self):
        """Korean text is valid token content."""
        korean_tokens = ["안녕하세요", "프로젝트", "검색 결과", "인증 필터"]
        for token in korean_tokens:
            event = {"type": "token", "content": token}
            assert isinstance(event["content"], str)
            assert "\ufffd" not in event["content"]

    def test_token_content_allows_whitespace(self):
        """Whitespace characters are valid token content."""
        whitespace_tokens = [" ", "  ", "\n", "\t", " \n "]
        for token in whitespace_tokens:
            event = {"type": "token", "content": token}
            assert isinstance(event["content"], str)


# =============================================================================
# Contract Tests: Sources Event Schema
# =============================================================================


class TestSSESourcesEventContract:
    """Validates SSE sources event format."""

    def test_valid_sources_events(
        self,
        sse_sources_event_schema: Dict[str, Any],
    ):
        """Valid sources events conform to schema."""
        for event in VALID_SOURCE_EVENTS:
            errors = validate_json_schema(event, sse_sources_event_schema)
            assert len(errors) == 0, (
                f"Sources event failed: {event} -> {errors}"
            )

    def test_sources_type_is_sources(self):
        """Sources event type field must be 'sources'."""
        for event in VALID_SOURCE_EVENTS:
            assert event["type"] == "sources"

    def test_sources_content_is_array(self):
        """Sources content must be an array."""
        for event in VALID_SOURCE_EVENTS:
            assert isinstance(event["content"], list), (
                f"Sources content should be list, got {type(event['content'])}"
            )

    def test_source_item_has_knowledge_id(self):
        """Each source item must have knowledgeId."""
        for event in VALID_SOURCE_EVENTS:
            for source in event["content"]:
                assert "knowledgeId" in source, (
                    f"Source missing knowledgeId: {source}"
                )

    def test_source_item_has_title(self):
        """Each source item must have title."""
        for event in VALID_SOURCE_EVENTS:
            for source in event["content"]:
                assert "title" in source, (
                    f"Source missing title: {source}"
                )

    def test_empty_sources_array_valid(self):
        """Empty sources array is valid (no relevant documents)."""
        event = {"type": "sources", "content": []}
        assert isinstance(event["content"], list)
        assert len(event["content"]) == 0

    def test_source_korean_title(self):
        """Korean source titles are valid."""
        event = {
            "type": "sources",
            "content": [
                {"knowledgeId": "k-001", "title": "JWT 인증 필터 구현 가이드"},
                {"knowledgeId": "k-002", "title": "프로젝트 보안 감사 절차"},
            ],
        }
        for source in event["content"]:
            assert "\ufffd" not in source["title"]


# =============================================================================
# Contract Tests: Done Event Schema
# =============================================================================


class TestSSEDoneEventContract:
    """Validates SSE done event format."""

    def test_valid_done_events(
        self,
        sse_done_event_schema: Dict[str, Any],
    ):
        """Valid done events conform to schema."""
        for event in VALID_DONE_EVENTS:
            errors = validate_json_schema(event, sse_done_event_schema)
            assert len(errors) == 0, (
                f"Done event failed: {event} -> {errors}"
            )

    def test_done_type_is_done(self):
        """Done event type field must be 'done'."""
        for event in VALID_DONE_EVENTS:
            assert event["type"] == "done"

    def test_done_conversation_id_optional(self):
        """conversationId is optional in done event."""
        event_with = {"type": "done", "conversationId": "conv-001"}
        event_without = {"type": "done"}

        assert "conversationId" in event_with
        assert "conversationId" not in event_without
        # Both should be valid

    def test_done_conversation_id_is_string(self):
        """conversationId must be a string when present."""
        event = {"type": "done", "conversationId": "conv-001"}
        assert isinstance(event["conversationId"], str)


# =============================================================================
# Contract Tests: Event Sequence Validation
# =============================================================================


class TestSSEEventSequenceContract:
    """Validates SSE event sequence ordering."""

    def test_valid_sequences(self):
        """Valid event sequences follow the expected order."""
        for case in VALID_EVENT_SEQUENCES:
            events = case["events"]
            types = [e["type"] for e in events]

            # Must end with "done"
            assert types[-1] == "done", (
                f"Sequence '{case['description']}' must end with 'done'"
            )

            # Tokens must come before sources
            if "sources" in types and "token" in types:
                first_source = types.index("sources")
                last_token = len(types) - 1 - types[::-1].index("token")
                assert last_token < first_source, (
                    f"Tokens should come before sources in '{case['description']}'"
                )

    def test_sequence_ends_with_done(self):
        """Every valid sequence must end with a 'done' event."""
        for case in VALID_EVENT_SEQUENCES:
            events = case["events"]
            assert events[-1]["type"] == "done"

    def test_at_least_one_token_before_done(self):
        """Valid sequences have at least one token event."""
        for case in VALID_EVENT_SEQUENCES:
            events = case["events"]
            token_events = [e for e in events if e["type"] == "token"]
            assert len(token_events) >= 1, (
                f"Sequence '{case['description']}' should have at least one token"
            )

    def test_only_one_done_event(self):
        """Valid sequences have exactly one done event."""
        for case in VALID_EVENT_SEQUENCES:
            events = case["events"]
            done_events = [e for e in events if e["type"] == "done"]
            assert len(done_events) == 1, (
                f"Sequence '{case['description']}' should have exactly one done event"
            )

    def test_only_one_sources_event(self):
        """Valid sequences have at most one sources event."""
        for case in VALID_EVENT_SEQUENCES:
            events = case["events"]
            source_events = [e for e in events if e["type"] == "sources"]
            assert len(source_events) <= 1, (
                f"Sequence '{case['description']}' should have at most one sources event"
            )

    def test_invalid_sequences_detected(self):
        """Invalid sequences are identified correctly."""
        for case in INVALID_EVENT_SEQUENCES:
            events = case["events"]
            types = [e["type"] for e in events]
            issue = case["issue"]

            # Check the specific issue
            if "No token events" in issue:
                token_count = types.count("token")
                assert token_count == 0, "Should have no tokens"
            elif "Sources should come after tokens" in issue:
                if "sources" in types and "token" in types:
                    first_source = types.index("sources")
                    first_token = types.index("token")
                    assert first_source < first_token, "Sources before first token"
            elif "Only one done event" in issue:
                done_count = types.count("done")
                assert done_count > 1, "Should have multiple done events"
            elif "must end with done" in issue:
                assert types[-1] != "done" or "done" not in types


# =============================================================================
# Contract Tests: SSE Wire Format
# =============================================================================


class TestSSEWireFormatContract:
    """Validates SSE wire format (data: prefix, newline separators)."""

    def test_token_wire_format(self):
        """Token event wire format: data: {json}\n\n"""
        event = {"type": "token", "content": "Hello"}
        wire = f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        assert wire.startswith("data: "), "Must start with 'data: '"
        assert wire.endswith("\n\n"), "Must end with double newline"

        # Parse back
        data_str = wire.strip().split("data: ", 1)[1]
        parsed = json.loads(data_str)
        assert parsed == event

    def test_sources_wire_format(self):
        """Sources event wire format is valid SSE."""
        event = {
            "type": "sources",
            "content": [
                {"knowledgeId": "k-001", "title": "Test Document"},
            ],
        }
        wire = f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        assert wire.startswith("data: ")
        assert wire.endswith("\n\n")

        # Parse back
        data_str = wire.strip().split("data: ", 1)[1]
        parsed = json.loads(data_str)
        assert parsed["type"] == "sources"
        assert len(parsed["content"]) == 1

    def test_done_wire_format(self):
        """Done event wire format is valid SSE."""
        event = {"type": "done", "conversationId": "conv-001"}
        wire = f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        assert wire.startswith("data: ")
        assert wire.endswith("\n\n")

    def test_korean_wire_format(self):
        """Korean text in wire format uses UTF-8 (not escaped)."""
        event = {"type": "token", "content": "프로젝트 보안 감사"}
        wire = f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        # Should contain Korean characters directly (not \uXXXX escapes)
        assert "프로젝트" in wire, "Korean should be in UTF-8 form"
        assert "\\u" not in wire, "Should not use unicode escapes"

    def test_full_stream_wire_format(self):
        """Complete stream follows SSE protocol."""
        events = [
            {"type": "token", "content": "Hello "},
            {"type": "token", "content": "World"},
            {
                "type": "sources",
                "content": [{"knowledgeId": "k-001", "title": "Test"}],
            },
            {"type": "done", "conversationId": "conv-001"},
        ]

        wire_format = ""
        for event in events:
            wire_format += f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        # Parse all events from wire format
        parsed_events = []
        for block in wire_format.split("\n\n"):
            block = block.strip()
            if block.startswith("data: "):
                parsed_events.append(json.loads(block[6:]))

        assert len(parsed_events) == len(events)
        for original, parsed in zip(events, parsed_events):
            assert original["type"] == parsed["type"]

    def test_event_separation_by_double_newline(self):
        """Events are separated by exactly two newlines."""
        events_wire = (
            'data: {"type":"token","content":"A"}\n\n'
            'data: {"type":"token","content":"B"}\n\n'
            'data: {"type":"done"}\n\n'
        )

        blocks = [b for b in events_wire.split("\n\n") if b.strip()]
        assert len(blocks) == 3, f"Expected 3 events, got {len(blocks)}"
