"""
Frontend/Backend E2E Tests Package

Sprint 04 Day 3 - STORY-054: Frontend-Backend Integration E2E Tests
25 scenarios across 5 categories:
  A: Authentication Flow (5 TC)
  B: Search Flow (5 TC)
  C: SSE Streaming (5 TC)
  D: Security Verification (5 TC)
  E: Error Handling (5 TC)

Test Markers:
  @pytest.mark.e2e: End-to-end tests
  @pytest.mark.sprint04_fb_e2e: Sprint 04 Frontend/Backend E2E
  @pytest.mark.auth_flow: Category A tests
  @pytest.mark.search_flow: Category B tests
  @pytest.mark.sse_streaming: Category C tests
  @pytest.mark.security_verification: Category D tests
  @pytest.mark.error_handling: Category E tests

Usage:
    # Run all Frontend/Backend E2E tests
    pytest knowledge_service/src/tests/e2e/frontend_backend/ -v

    # Run by category
    pytest knowledge_service/src/tests/e2e/frontend_backend/ -m auth_flow -v
    pytest knowledge_service/src/tests/e2e/frontend_backend/ -m search_flow -v

    # Run P0 only (all categories, critical scenarios)
    pytest knowledge_service/src/tests/e2e/frontend_backend/ -m "sprint04_fb_e2e and not p1" -v

Requirements:
    - Docker Compose environment or mock mode
    - pytest, pytest-asyncio, httpx, pyjwt

Author: QA Agent
Sprint: Sprint 04 Day 3
"""
