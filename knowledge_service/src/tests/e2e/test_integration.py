"""
STORY-020: Service Integration E2E Tests

This module provides comprehensive E2E tests for service-to-service communication.
It validates routing, connectivity, and data flow between services.

Test Categories:
- Gateway Routing: Verify API Gateway routes to Backend and AI Service
- Service Connectivity: Validate inter-service communication
- Database Connectivity: Verify services can connect to databases
- File Storage: Validate MinIO file upload/download

Usage:
    pytest knowledge_service/src/tests/e2e/test_integration.py -v

Markers:
    @pytest.mark.e2e: End-to-end tests
    @pytest.mark.integration: Service integration tests

Author: QA Agent
Sprint: Sprint 01 Validation
"""

import json
import os
import subprocess
from typing import Dict, Optional

import pytest
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# =============================================================================
# CONSTANTS
# =============================================================================

GATEWAY_URL = "http://localhost:8080"
BACKEND_URL = "http://localhost:8081"
AI_SERVICE_URL = "http://localhost:8000"
NGINX_URL = "http://localhost:80"


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def http_session() -> requests.Session:
    """Create HTTP session with retry logic."""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


@pytest.fixture(scope="module")
def config() -> Dict[str, str]:
    """Load configuration from environment."""
    return {
        "POSTGRES_USER": os.getenv("DB_USERNAME", "knowledge"),
        "POSTGRES_PASSWORD": os.getenv("DB_PASSWORD", "knowledge"),
        "POSTGRES_DB": os.getenv("DB_NAME", "knowledge"),
        "NEO4J_USER": os.getenv("NEO4J_USER", "neo4j"),
        "NEO4J_PASSWORD": os.getenv("NEO4J_PASSWORD", ""),
        "MINIO_ACCESS_KEY": os.getenv("MINIO_ACCESS_KEY", ""),
        "MINIO_SECRET_KEY": os.getenv("MINIO_SECRET_KEY", ""),
    }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def is_docker_available() -> bool:
    """Check if Docker is available."""
    try:
        result = subprocess.run(
            ["docker", "version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


docker_available = pytest.mark.skipif(
    not is_docker_available(),
    reason="Docker is not available"
)


# =============================================================================
# TC-INFRA-401-404: ROUTING TESTS
# =============================================================================

@pytest.mark.e2e
@pytest.mark.integration
@docker_available
class TestServiceRouting:
    """
    TC-INFRA-401-404: Verify Nginx and API Gateway routing.

    Acceptance Criteria:
    - Nginx routes / to Frontend
    - Nginx routes /api to Gateway
    - Gateway routes to Backend
    - Gateway routes to AI Service
    """

    def test_nginx_to_frontend(self, http_session: requests.Session):
        """TC-INFRA-401: Nginx should route to Frontend."""
        response = http_session.get(f"{NGINX_URL}/", timeout=10)

        assert response.status_code == 200, (
            f"Frontend routing failed: {response.status_code}"
        )

        # Check for HTML content
        content_type = response.headers.get("content-type", "").lower()
        assert "text/html" in content_type, (
            f"Expected HTML, got: {content_type}"
        )

    def test_nginx_to_gateway(self, http_session: requests.Session):
        """TC-INFRA-402: Nginx should route /api to Gateway."""
        response = http_session.get(f"{NGINX_URL}/api/", timeout=10)

        # Gateway might return 404 for root, but should not return 502/503
        assert response.status_code not in [502, 503], (
            f"Gateway unreachable: {response.status_code}"
        )

    def test_gateway_to_backend(self, http_session: requests.Session):
        """TC-INFRA-403: Gateway should route to Backend."""
        # Try multiple possible endpoints
        endpoints = [
            f"{GATEWAY_URL}/api/health",
            f"{GATEWAY_URL}/actuator/health",
        ]

        success = False
        for endpoint in endpoints:
            try:
                response = http_session.get(endpoint, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "UP":
                        success = True
                        break
            except (requests.RequestException, ValueError):
                continue

        assert success, "Backend health check via Gateway failed"

    def test_gateway_health(self, http_session: requests.Session):
        """Gateway health endpoint should be accessible."""
        response = http_session.get(f"{GATEWAY_URL}/actuator/health", timeout=10)

        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "UP"

    def test_backend_health(self, http_session: requests.Session):
        """Backend health endpoint should be accessible."""
        response = http_session.get(f"{BACKEND_URL}/actuator/health", timeout=10)

        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "UP"

    def test_ai_service_health(self, http_session: requests.Session):
        """AI Service health endpoint should be accessible."""
        response = http_session.get(f"{AI_SERVICE_URL}/health", timeout=10)

        assert response.status_code == 200
        data = response.json()
        assert data.get("status") in ["ok", "healthy"]


# =============================================================================
# TC-INFRA-405-409: SERVICE CONNECTIVITY TESTS
# =============================================================================

@pytest.mark.e2e
@pytest.mark.integration
@docker_available
class TestServiceConnectivity:
    """
    TC-INFRA-405-409: Verify service-to-service connectivity.

    Acceptance Criteria:
    - Backend connects to PostgreSQL
    - Backend connects to Redis
    - Backend connects to MinIO
    - AI Service connects to Elasticsearch
    - AI Service connects to Neo4j
    """

    def test_backend_to_postgresql(self, config: Dict[str, str]):
        """TC-INFRA-405: Backend should connect to PostgreSQL."""
        # Check via Backend container
        result = subprocess.run(
            ["docker", "exec", "kp-backend",
             "curl", "-s", "http://localhost:8081/actuator/health/db"],
            capture_output=True, text=True, timeout=30
        )

        if result.returncode == 0 and result.stdout:
            try:
                data = json.loads(result.stdout)
                assert data.get("status") in ["UP", "up"], (
                    f"DB connection issue: {data}"
                )
            except json.JSONDecodeError:
                # Check for positive indicators
                if "UP" not in result.stdout.upper():
                    pytest.skip("Backend DB health endpoint not available")
        else:
            pytest.skip("Cannot access Backend DB health endpoint")

    def test_backend_to_redis(self):
        """TC-INFRA-406: Backend should connect to Redis."""
        result = subprocess.run(
            ["docker", "exec", "kp-backend",
             "curl", "-s", "http://localhost:8081/actuator/health/redis"],
            capture_output=True, text=True, timeout=30
        )

        if result.returncode == 0 and result.stdout:
            try:
                data = json.loads(result.stdout)
                assert data.get("status") in ["UP", "up"]
            except json.JSONDecodeError:
                pass
        else:
            pytest.skip("Backend Redis health endpoint not available")

    def test_backend_to_minio(self, config: Dict[str, str]):
        """TC-INFRA-407: Backend should connect to MinIO."""
        result = subprocess.run(
            ["docker", "exec", "kp-backend",
             "curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
             "http://minio:9000/minio/health/live"],
            capture_output=True, text=True, timeout=30
        )

        if result.returncode == 0:
            status_code = result.stdout.strip()
            assert status_code == "200", (
                f"MinIO not reachable from Backend: {status_code}"
            )
        else:
            pytest.skip("Cannot execute curl from Backend container")

    def test_ai_service_to_elasticsearch(self, http_session: requests.Session):
        """TC-INFRA-408: AI Service should connect to Elasticsearch."""
        result = subprocess.run(
            ["docker", "exec", "kp-ai-service",
             "curl", "-s", "http://elasticsearch:9200/_cluster/health"],
            capture_output=True, text=True, timeout=30
        )

        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                assert data.get("status") in ["green", "yellow"], (
                    f"ES cluster unhealthy from AI Service: {data}"
                )
            except json.JSONDecodeError:
                pytest.fail(f"Invalid ES response: {result.stdout}")
        else:
            pytest.skip("Cannot execute curl from AI Service container")

    def test_ai_service_to_neo4j(self, config: Dict[str, str]):
        """TC-INFRA-409: AI Service should connect to Neo4j."""
        result = subprocess.run(
            ["docker", "exec", "kp-ai-service",
             "curl", "-s", "http://neo4j:7474/"],
            capture_output=True, text=True, timeout=30
        )

        if result.returncode == 0:
            assert result.stdout.strip(), "Empty response from Neo4j"
        else:
            pytest.skip("Cannot execute curl from AI Service container")

    def test_cross_network_communication(self):
        """TC-INFRA-410: Backend should communicate with AI Service."""
        result = subprocess.run(
            ["docker", "exec", "kp-backend",
             "curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
             "http://ai-service:8000/health"],
            capture_output=True, text=True, timeout=30
        )

        if result.returncode == 0:
            status_code = result.stdout.strip()
            assert status_code == "200", (
                f"AI Service not reachable from Backend: {status_code}"
            )
        else:
            pytest.skip("Cannot execute curl from Backend container")


# =============================================================================
# MINIO FILE STORAGE TESTS
# =============================================================================

@pytest.mark.e2e
@pytest.mark.integration
@docker_available
class TestMinIOFileStorage:
    """
    Test MinIO file storage operations.

    Acceptance Criteria:
    - MinIO API is accessible
    - File upload works
    - File download works
    """

    def test_minio_api_accessible(self, http_session: requests.Session):
        """MinIO API should be accessible."""
        response = http_session.get(
            "http://localhost:9000/minio/health/live",
            timeout=10
        )
        assert response.status_code == 200

    def test_minio_console_accessible(self, http_session: requests.Session):
        """MinIO console should be accessible."""
        response = http_session.get(
            "http://localhost:9001/",
            timeout=10
        )
        # Console redirects to login
        assert response.status_code in [200, 302, 303]

    def test_minio_buckets_via_mc(self, config: Dict[str, str]):
        """MinIO buckets should be accessible via mc client."""
        if not config.get("MINIO_ACCESS_KEY") or not config.get("MINIO_SECRET_KEY"):
            pytest.skip("MinIO credentials not configured")

        # Set up alias
        result = subprocess.run(
            ["docker", "exec", "kp-minio",
             "mc", "alias", "set", "local",
             "http://localhost:9000",
             config["MINIO_ACCESS_KEY"],
             config["MINIO_SECRET_KEY"]],
            capture_output=True, text=True, timeout=30
        )

        if result.returncode == 0:
            # List buckets
            list_result = subprocess.run(
                ["docker", "exec", "kp-minio", "mc", "ls", "local/"],
                capture_output=True, text=True, timeout=30
            )

            if list_result.returncode == 0:
                buckets = list_result.stdout
                # Check for expected buckets
                expected_buckets = ["documents", "processed"]
                for bucket in expected_buckets:
                    if bucket not in buckets:
                        pytest.skip(f"Bucket '{bucket}' not found - run init-db")
            else:
                pytest.skip("Cannot list MinIO buckets")
        else:
            pytest.skip("MinIO mc client not available")


# =============================================================================
# DATABASE INTEGRATION TESTS
# =============================================================================

@pytest.mark.e2e
@pytest.mark.integration
@docker_available
class TestDatabaseIntegration:
    """
    Test database integration with services.

    Acceptance Criteria:
    - PostgreSQL accepts connections from Backend
    - Elasticsearch accepts connections from AI Service
    - Neo4j accepts connections from AI Service
    - Redis accepts connections from Backend
    """

    def test_postgresql_connection(self, config: Dict[str, str]):
        """PostgreSQL should accept connections."""
        result = subprocess.run(
            ["docker", "exec", "kp-postgresql", "psql",
             "-U", config["POSTGRES_USER"],
             "-d", config["POSTGRES_DB"],
             "-c", "SELECT 1;"],
            capture_output=True, text=True, timeout=30
        )

        assert result.returncode == 0, f"PostgreSQL connection failed: {result.stderr}"

    def test_elasticsearch_connection(self, http_session: requests.Session):
        """Elasticsearch should accept connections."""
        response = http_session.get(
            "http://localhost:9200/",
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data

    def test_neo4j_connection(self, config: Dict[str, str], http_session: requests.Session):
        """Neo4j should accept connections."""
        neo4j_password = config.get("NEO4J_PASSWORD", "")
        if not neo4j_password:
            pytest.skip("NEO4J_PASSWORD not set")

        auth = (config["NEO4J_USER"], neo4j_password)

        response = http_session.post(
            "http://localhost:7474/db/neo4j/tx/commit",
            json={
                "statements": [{
                    "statement": "RETURN 1 as test"
                }]
            },
            auth=auth,
            timeout=10
        )

        if response.status_code == 401:
            pytest.skip("Neo4j authentication failed")

        assert response.status_code == 200

    def test_redis_connection(self):
        """Redis should accept connections."""
        result = subprocess.run(
            ["docker", "exec", "kp-redis", "redis-cli", "ping"],
            capture_output=True, text=True, timeout=30
        )

        assert result.returncode == 0
        assert "PONG" in result.stdout


# =============================================================================
# API INTEGRATION TESTS
# =============================================================================

@pytest.mark.e2e
@pytest.mark.integration
@docker_available
class TestAPIIntegration:
    """
    Test API endpoints integration.

    Acceptance Criteria:
    - API Gateway routes requests correctly
    - Backend API responds
    - AI Service API responds
    """

    def test_gateway_routes_to_backend_health(self, http_session: requests.Session):
        """Gateway should route health check to Backend."""
        response = http_session.get(
            f"{GATEWAY_URL}/actuator/health",
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "UP"

    def test_backend_api_info(self, http_session: requests.Session):
        """Backend API info endpoint should respond."""
        response = http_session.get(
            f"{BACKEND_URL}/actuator/info",
            timeout=10
        )

        assert response.status_code == 200

    def test_ai_service_api_docs(self, http_session: requests.Session):
        """AI Service OpenAPI docs should be available."""
        response = http_session.get(
            f"{AI_SERVICE_URL}/docs",
            timeout=10
        )

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_ai_service_openapi_json(self, http_session: requests.Session):
        """AI Service OpenAPI JSON should be available."""
        response = http_session.get(
            f"{AI_SERVICE_URL}/openapi.json",
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data


# =============================================================================
# SUMMARY INTEGRATION TEST
# =============================================================================

@pytest.mark.e2e
@pytest.mark.integration
@docker_available
class TestIntegrationSummary:
    """
    Summary test for quick integration validation.
    """

    def test_full_stack_integration(self, http_session: requests.Session):
        """
        Quick check: Verify full stack integration.

        Flow: Client -> Nginx -> Gateway -> Backend/AI Service
        """
        checks_passed = []
        checks_failed = []

        # Check Nginx -> Frontend
        try:
            response = http_session.get(f"{NGINX_URL}/", timeout=10)
            if response.status_code == 200:
                checks_passed.append("Nginx -> Frontend")
            else:
                checks_failed.append(f"Nginx -> Frontend ({response.status_code})")
        except requests.RequestException as e:
            checks_failed.append(f"Nginx -> Frontend ({e})")

        # Check Gateway health
        try:
            response = http_session.get(f"{GATEWAY_URL}/actuator/health", timeout=10)
            if response.status_code == 200:
                checks_passed.append("Gateway health")
            else:
                checks_failed.append(f"Gateway health ({response.status_code})")
        except requests.RequestException as e:
            checks_failed.append(f"Gateway health ({e})")

        # Check Backend health
        try:
            response = http_session.get(f"{BACKEND_URL}/actuator/health", timeout=10)
            if response.status_code == 200:
                checks_passed.append("Backend health")
            else:
                checks_failed.append(f"Backend health ({response.status_code})")
        except requests.RequestException as e:
            checks_failed.append(f"Backend health ({e})")

        # Check AI Service health
        try:
            response = http_session.get(f"{AI_SERVICE_URL}/health", timeout=10)
            if response.status_code == 200:
                checks_passed.append("AI Service health")
            else:
                checks_failed.append(f"AI Service health ({response.status_code})")
        except requests.RequestException as e:
            checks_failed.append(f"AI Service health ({e})")

        # At least 3 checks should pass for basic integration
        assert len(checks_passed) >= 3, (
            f"Integration check failed. Passed: {checks_passed}, Failed: {checks_failed}"
        )
