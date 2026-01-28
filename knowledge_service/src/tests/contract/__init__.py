"""
Contract Tests Package - STORY-054

Validates API contracts between services:
- Backend -> AI Service (search API)
- AI Service -> Knowledge Service (retriever API)
- SSE Event Format (streaming protocol)

Contract tests verify schema compatibility without requiring
all services to be running. They use JSON Schema validation
and mock stubs to verify request/response structures.

Test Markers:
    @pytest.mark.contract: Contract tests
    @pytest.mark.sprint04_fb_e2e: Sprint 04 tests

Usage:
    pytest knowledge_service/src/tests/contract/ -v
    pytest knowledge_service/src/tests/contract/ -m contract -v

Author: QA Agent
Sprint: Sprint 04 Day 3
"""
