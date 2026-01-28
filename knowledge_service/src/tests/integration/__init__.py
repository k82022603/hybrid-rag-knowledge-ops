"""
Sprint 04 Integration Tests Package

P0 Critical story integration tests for Sprint 04.
Tests are designed to execute once P0 stories are fully implemented.

Test Modules:
- test_story050_sse_protocol.py: STORY-050 SSE Protocol Fix (POST SSE)
- test_story052_reranker_async.py: STORY-052 Reranker Async Conversion
- test_story053_security.py: STORY-053 Security Hardening

Test Markers:
- @pytest.mark.sprint04: Sprint 04 tests
- @pytest.mark.integration: Integration-level tests
- @pytest.mark.sse: SSE protocol tests
- @pytest.mark.security: Security hardening tests
- @pytest.mark.reranker: Reranker async tests

Usage:
    # Run all Sprint 04 integration tests
    pytest knowledge_service/src/tests/integration/ -v -m sprint04

    # Run SSE protocol tests only
    pytest knowledge_service/src/tests/integration/test_story050_sse_protocol.py -v

    # Run security tests only
    pytest knowledge_service/src/tests/integration/test_story053_security.py -v

    # Run reranker async tests only
    pytest knowledge_service/src/tests/integration/test_story052_reranker_async.py -v

Author: QA Agent
Sprint: Sprint 04 Day 2
"""
