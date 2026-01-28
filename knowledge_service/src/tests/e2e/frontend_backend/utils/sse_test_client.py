"""
SSE Test Client for POST-based Server-Sent Events

Custom client for validating POST-based SSE streaming protocol
(STORY-050 migration from EventSource GET to fetch+ReadableStream POST).

Features:
- POST-based SSE stream parsing
- UTF-8 Korean text handling
- AbortController simulation (via timeout/cancellation)
- Event collection and analysis utilities

Actual SSE Event Types (from search.py):
- start: Search start event with sources and context_length
- chunk: Answer text chunk
- error: Error event with message
- end:   Stream termination

Usage:
    client = SSETestClient(base_url="http://localhost:8080", token="jwt-token")
    events = await client.collect_all_events("RAG 시스템 동작 원리")

Author: QA Agent
Sprint: Sprint 04 Day 3
"""

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx


@dataclass
class SSEEvent:
    """Parsed SSE event with type information.

    Event types: start, chunk, end, error
    """

    event_type: str  # "start", "chunk", "end", "error"
    content: Any = None
    raw_data: str = ""
    timestamp: float = 0.0


@dataclass
class SSEStreamResult:
    """Collected result from a complete SSE stream."""

    events: List[SSEEvent] = field(default_factory=list)
    chunks: List[str] = field(default_factory=list)
    full_text: str = ""
    sources: List[Dict] = field(default_factory=list)
    is_complete: bool = False
    was_aborted: bool = False
    error: Optional[str] = None
    response_headers: Dict[str, str] = field(default_factory=dict)
    status_code: int = 0

    @property
    def chunk_count(self) -> int:
        """Number of chunk events received."""
        return len(self.chunks)

    @property
    def has_end_event(self) -> bool:
        """Whether stream ended with an end event."""
        return any(e.event_type == "end" for e in self.events)

    @property
    def has_start_event(self) -> bool:
        """Whether stream started with a start event."""
        return any(e.event_type == "start" for e in self.events)

    @property
    def has_sources(self) -> bool:
        """Whether source documents were provided."""
        return len(self.sources) > 0

    def contains_replacement_chars(self) -> bool:
        """Check for UTF-8 encoding artifacts (U+FFFD)."""
        return "\ufffd" in self.full_text


class SSETestClient:
    """POST-based SSE client for Frontend/Backend E2E testing.

    Simulates the browser's fetch+ReadableStream approach for SSE consumption
    as implemented in STORY-050.
    """

    def __init__(
        self,
        base_url: str,
        token: str,
        timeout: float = 30.0,
    ):
        """Initialize SSE test client.

        Args:
            base_url: Backend service base URL (e.g., http://localhost:8080)
            token: JWT access token for Authorization header
            timeout: Request timeout in seconds (default 30s)
        """
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def _build_headers(self) -> Dict[str, str]:
        """Build standard request headers."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }

    async def stream_search(
        self,
        query: str,
        conversation_history: Optional[List[Dict]] = None,
        top_k: int = 5,
        timeout: Optional[float] = None,
    ) -> AsyncIterator[SSEEvent]:
        """Send POST SSE search and yield parsed events.

        Args:
            query: Search query text
            conversation_history: Optional chat history
            top_k: Number of results to retrieve
            timeout: Override default timeout

        Yields:
            SSEEvent objects parsed from the stream
        """
        request_timeout = timeout or self.timeout

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/v1/search/chat/stream",
                json={
                    "query": query,
                    "top_k": top_k,
                },
                headers=self._build_headers(),
                timeout=request_timeout,
            ) as response:
                assert response.status_code == 200, (
                    f"Expected 200, got {response.status_code}"
                )

                buffer = ""
                async for chunk in response.aiter_text():
                    buffer += chunk
                    while "\n\n" in buffer:
                        event_str, buffer = buffer.split("\n\n", 1)
                        event = self._parse_event(event_str)
                        if event:
                            yield event

    async def collect_all_events(
        self,
        query: str,
        conversation_history: Optional[List[Dict]] = None,
        top_k: int = 5,
        timeout: Optional[float] = None,
    ) -> SSEStreamResult:
        """Collect all SSE events into a structured result.

        Args:
            query: Search query text
            conversation_history: Optional chat history
            top_k: Number of results to retrieve
            timeout: Override default timeout

        Returns:
            SSEStreamResult with all collected events and metadata
        """
        result = SSEStreamResult()

        try:
            async for event in self.stream_search(
                query=query,
                conversation_history=conversation_history,
                top_k=top_k,
                timeout=timeout,
            ):
                result.events.append(event)

                if event.event_type == "chunk":
                    result.chunks.append(str(event.content))
                elif event.event_type == "start":
                    if isinstance(event.content, dict):
                        result.sources = event.content.get("sources", [])
                elif event.event_type == "end":
                    result.is_complete = True

            result.full_text = "".join(result.chunks)

        except asyncio.CancelledError:
            result.was_aborted = True
            result.full_text = "".join(result.chunks)
        except httpx.TimeoutException as e:
            result.error = f"Timeout: {e}"
        except Exception as e:
            result.error = f"Error: {e}"

        return result

    async def stream_with_abort(
        self,
        query: str,
        abort_after_events: int = 3,
        **kwargs,
    ) -> SSEStreamResult:
        """Start streaming and abort after N events (AbortController simulation).

        Args:
            query: Search query text
            abort_after_events: Number of events to receive before aborting
            **kwargs: Additional arguments passed to stream_search

        Returns:
            SSEStreamResult with partial data and was_aborted=True
        """
        result = SSEStreamResult()
        event_count = 0

        try:
            async for event in self.stream_search(query=query, **kwargs):
                result.events.append(event)
                event_count += 1

                if event.event_type == "chunk":
                    result.chunks.append(str(event.content))

                if event_count >= abort_after_events:
                    result.was_aborted = True
                    break

        except Exception as e:
            result.error = f"Error during abort: {e}"

        result.full_text = "".join(result.chunks)
        return result

    @staticmethod
    def _parse_event(event_str: str) -> Optional[SSEEvent]:
        """Parse a raw SSE event string into an SSEEvent object.

        Args:
            event_str: Raw event string (e.g., 'data: {"type":"chunk","content":"Hello"}')

        Returns:
            Parsed SSEEvent or None if unparseable
        """
        import time

        for line in event_str.strip().split("\n"):
            if line.startswith("data: "):
                data_str = line[6:]
                try:
                    data = json.loads(data_str)
                    return SSEEvent(
                        event_type=data.get("type", "unknown"),
                        content=data.get("content"),
                        raw_data=data_str,
                        timestamp=time.time(),
                    )
                except json.JSONDecodeError:
                    return SSEEvent(
                        event_type="parse_error",
                        content=data_str,
                        raw_data=data_str,
                        timestamp=time.time(),
                    )
        return None


def create_mock_sse_response(
    tokens: Optional[List[str]] = None,
    sources: Optional[List[Dict]] = None,
    include_end: bool = True,
) -> str:
    """Create a mock SSE response string for testing.

    Uses actual SSE event types: start, chunk, end, error.

    Args:
        tokens: List of text chunk strings to include as 'chunk' events
        sources: List of source document dicts for the 'start' event
        include_end: Whether to include end event

    Returns:
        Formatted SSE response string
    """
    events = []

    if tokens is None:
        tokens = ["RAG 시스템은 ", "검색 증강 생성을 ", "결합한 기술입니다."]

    # Start event with sources
    if sources is not None:
        sources_json = json.dumps(sources, ensure_ascii=False)
    else:
        default_sources = [
            {"knowledgeId": "k-001", "title": "RAG 시스템 개요"},
            {"knowledgeId": "k-002", "title": "검색 파이프라인 가이드"},
        ]
        sources_json = json.dumps(default_sources, ensure_ascii=False)

    events.append(
        f'data: {{"type":"start","sources":{sources_json},"context_length":1500}}\n\n'
    )

    # Chunk events for text content
    for token in tokens:
        token_escaped = json.dumps(token, ensure_ascii=False)[1:-1]
        events.append(f'data: {{"type":"chunk","content":"{token_escaped}"}}\n\n')

    # End event
    if include_end:
        events.append('data: {"type":"end"}\n\n')

    return "".join(events)
