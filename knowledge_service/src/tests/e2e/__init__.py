"""
E2E (End-to-End) Tests Package

Contains infrastructure and integration tests for the Hybrid RAG Knowledge Platform.

STORY-020: Infrastructure E2E Test Implementation

Test Modules:
- test_infrastructure.py: Container health, database init, network/volume tests
- test_keycloak.py: Keycloak OAuth2/OIDC authentication tests
- test_integration.py: Service routing and connectivity tests

Test Markers:
- @pytest.mark.e2e: End-to-end tests
- @pytest.mark.infrastructure: Infrastructure layer tests
- @pytest.mark.keycloak: Keycloak authentication tests
- @pytest.mark.integration: Service integration tests

Usage:
    # Run all E2E tests
    pytest knowledge_service/src/tests/e2e/ -v

    # Run only infrastructure tests
    pytest knowledge_service/src/tests/e2e/ -m infrastructure -v

    # Run only Keycloak tests
    pytest knowledge_service/src/tests/e2e/ -m keycloak -v

    # Run only integration tests
    pytest knowledge_service/src/tests/e2e/ -m integration -v

Requirements:
    - Docker Compose environment running (18 containers)
    - Environment variables configured (.env file)
    - Network connectivity to localhost ports

Author: QA Agent
Sprint: Sprint 01 Validation
"""
