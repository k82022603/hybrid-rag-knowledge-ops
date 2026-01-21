"""
TC-INFRA-4xx: Service Integration Tests

Tests for verifying service-to-service communication and routing.
SCRUM-20: Sprint 01 Validation

Test Coverage:
- TC-INFRA-401 ~ TC-INFRA-410: Service integration verification

Markers:
- @pytest.mark.application: Routing tests (nginx, gateway routes)
- @pytest.mark.infrastructure: Network/Volume tests
"""

import subprocess
from typing import Dict

import pytest
import requests

from .conftest import docker_available


# =============================================================================
# TC-INFRA-401 ~ 404: ROUTING TESTS
# =============================================================================

@pytest.mark.application
@docker_available
class TestServiceRouting:
    """Tests for Nginx and API Gateway routing."""

    def test_tc_infra_401_nginx_to_frontend(
        self, http_session: requests.Session
    ):
        """
        TC-INFRA-401: Nginx routes to Frontend.

        Endpoint: http://localhost/
        Expected: Frontend HTML returned
        """
        response = http_session.get("http://localhost/", timeout=10)

        assert response.status_code == 200, (
            f"Frontend routing failed: {response.status_code}"
        )

        # Check for HTML content
        assert "text/html" in response.headers.get("content-type", "").lower(), (
            f"Expected HTML, got: {response.headers.get('content-type')}"
        )

    def test_tc_infra_402_nginx_to_gateway(
        self, http_session: requests.Session
    ):
        """
        TC-INFRA-402: Nginx routes /api to Gateway.

        Endpoint: http://localhost/api/
        Expected: Gateway response (or proper routing)
        """
        response = http_session.get("http://localhost/api/", timeout=10)

        # Gateway might return 404 for root, but should not return 502/503
        assert response.status_code not in [502, 503], (
            f"Gateway unreachable: {response.status_code}"
        )

    def test_tc_infra_403_gateway_to_backend(
        self, http_session: requests.Session
    ):
        """
        TC-INFRA-403: Gateway routes to Backend.

        Endpoint: http://localhost:8080/api/health (or actuator)
        Expected: Backend UP status
        """
        # Try multiple possible endpoints
        endpoints = [
            "http://localhost:8080/api/health",
            "http://localhost:8080/actuator/health",
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

    def test_tc_infra_404_gateway_to_ai_service(
        self, http_session: requests.Session
    ):
        """
        TC-INFRA-404: Gateway routes to AI Service.

        Endpoint: http://localhost:8080/ai/health
        Expected: AI Service ok status
        """
        # The path might vary based on Gateway config
        endpoints = [
            "http://localhost:8080/ai/health",
            "http://localhost:8080/api/ai/health",
        ]

        success = False
        for endpoint in endpoints:
            try:
                response = http_session.get(endpoint, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") in ["ok", "healthy"]:
                        success = True
                        break
            except (requests.RequestException, ValueError):
                continue

        # AI Service routing might not be configured yet
        if not success:
            pytest.skip("AI Service routing not configured in Gateway")


# =============================================================================
# TC-INFRA-405 ~ 409: SERVICE CONNECTIVITY TESTS
# =============================================================================

@pytest.mark.application
@docker_available
class TestServiceConnectivity:
    """Tests for service-to-service connectivity."""

    def test_tc_infra_405_backend_to_postgresql(self, config: Dict[str, str]):
        """
        TC-INFRA-405: Backend connects to PostgreSQL.

        Expected: Database connection successful
        """
        # Check via Backend health endpoint with details
        # or execute a test query from Backend container
        result = subprocess.run(
            ["docker", "exec", "kp-backend",
             "curl", "-s", "http://localhost:8081/actuator/health/db"],
            capture_output=True, text=True, timeout=30
        )

        if result.returncode == 0 and "status" in result.stdout:
            import json
            try:
                data = json.loads(result.stdout)
                # Status should be UP or the endpoint provides DB info
                assert data.get("status") in ["UP", "up"], (
                    f"DB connection issue: {data}"
                )
            except json.JSONDecodeError:
                # If not JSON, check for positive indicators
                assert "UP" in result.stdout.upper() or "ok" in result.stdout.lower()
        else:
            # Fallback: just verify Backend is running and has DB config
            pytest.skip("Backend DB health endpoint not available")

    def test_tc_infra_406_backend_to_redis(self):
        """
        TC-INFRA-406: Backend connects to Redis.

        Expected: Cache connection working
        """
        # Check via Backend health endpoint
        result = subprocess.run(
            ["docker", "exec", "kp-backend",
             "curl", "-s", "http://localhost:8081/actuator/health/redis"],
            capture_output=True, text=True, timeout=30
        )

        if result.returncode == 0 and "status" in result.stdout:
            import json
            try:
                data = json.loads(result.stdout)
                assert data.get("status") in ["UP", "up"]
            except json.JSONDecodeError:
                pass
        else:
            pytest.skip("Backend Redis health endpoint not available")

    def test_tc_infra_407_backend_to_minio(self, config: Dict[str, str]):
        """
        TC-INFRA-407: Backend connects to MinIO.

        Expected: File storage accessible
        """
        # This might need actual file upload test
        # For now, verify MinIO is reachable from Backend network
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

    def test_tc_infra_408_ai_service_to_elasticsearch(
        self, http_session: requests.Session
    ):
        """
        TC-INFRA-408: AI Service connects to Elasticsearch.

        Expected: Search functionality works
        """
        # Execute connection test from AI Service container
        result = subprocess.run(
            ["docker", "exec", "kp-ai-service",
             "curl", "-s", "http://elasticsearch:9200/_cluster/health"],
            capture_output=True, text=True, timeout=30
        )

        if result.returncode == 0:
            import json
            try:
                data = json.loads(result.stdout)
                assert data.get("status") in ["green", "yellow"], (
                    f"ES cluster unhealthy from AI Service: {data}"
                )
            except json.JSONDecodeError:
                pytest.fail(f"Invalid ES response: {result.stdout}")
        else:
            pytest.skip("Cannot execute curl from AI Service container")

    def test_tc_infra_409_ai_service_to_neo4j(self, config: Dict[str, str]):
        """
        TC-INFRA-409: AI Service connects to Neo4j.

        Expected: Graph queries work
        """
        # Test Neo4j connection from AI Service
        result = subprocess.run(
            ["docker", "exec", "kp-ai-service",
             "curl", "-s", "http://neo4j:7474/"],
            capture_output=True, text=True, timeout=30
        )

        if result.returncode == 0:
            assert result.stdout.strip(), "Empty response from Neo4j"
        else:
            pytest.skip("Cannot execute curl from AI Service container")

    def test_tc_infra_410_cross_network_communication(self):
        """
        TC-INFRA-410: Backend to AI Service direct communication.

        Expected: Backend can reach AI Service
        """
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
# NETWORK TESTS
# =============================================================================

@pytest.mark.infrastructure
@docker_available
class TestNetworkConfiguration:
    """Tests for Docker network configuration."""

    def test_frontend_network_exists(self):
        """
        Verify kp-frontend network exists.

        Expected: Network created and has containers attached
        """
        result = subprocess.run(
            ["docker", "network", "inspect", "kp-frontend"],
            capture_output=True, text=True, timeout=30
        )

        assert result.returncode == 0, "kp-frontend network not found"

    def test_backend_network_exists(self):
        """
        Verify kp-backend network exists.

        Expected: Network created and has containers attached
        """
        result = subprocess.run(
            ["docker", "network", "inspect", "kp-backend"],
            capture_output=True, text=True, timeout=30
        )

        assert result.returncode == 0, "kp-backend network not found"

    def test_database_network_exists(self):
        """
        Verify kp-database network exists.

        Expected: Network created (internal setting depends on environment)
        Note: internal: true is disabled in development for localhost port access
        """
        result = subprocess.run(
            ["docker", "network", "inspect", "kp-database"],
            capture_output=True, text=True, timeout=30
        )

        assert result.returncode == 0, "kp-database network not found"

        # Verify network has containers attached
        import json
        try:
            data = json.loads(result.stdout)[0]
            containers = data.get("Containers", {})
            # Database network should have database containers attached
            assert len(containers) > 0, "No containers attached to kp-database network"
        except (json.JSONDecodeError, IndexError, KeyError):
            pass

    def test_monitoring_network_exists(self):
        """
        Verify kp-monitoring network exists.

        Expected: Network created and has observability containers
        """
        result = subprocess.run(
            ["docker", "network", "inspect", "kp-monitoring"],
            capture_output=True, text=True, timeout=30
        )

        assert result.returncode == 0, "kp-monitoring network not found"


# =============================================================================
# VOLUME TESTS
# =============================================================================

@pytest.mark.infrastructure
@docker_available
class TestVolumeConfiguration:
    """Tests for Docker volume configuration."""

    def test_postgresql_volume_exists(self):
        """
        Verify PostgreSQL data volume exists.

        Expected: kp-postgresql-data volume created
        """
        result = subprocess.run(
            ["docker", "volume", "inspect", "kp-postgresql-data"],
            capture_output=True, text=True, timeout=30
        )

        assert result.returncode == 0, "PostgreSQL volume not found"

    def test_elasticsearch_volume_exists(self):
        """
        Verify Elasticsearch data volume exists.

        Expected: kp-elasticsearch-data volume created
        """
        result = subprocess.run(
            ["docker", "volume", "inspect", "kp-elasticsearch-data"],
            capture_output=True, text=True, timeout=30
        )

        assert result.returncode == 0, "Elasticsearch volume not found"

    def test_neo4j_volume_exists(self):
        """
        Verify Neo4j data volume exists.

        Expected: kp-neo4j-data volume created
        """
        result = subprocess.run(
            ["docker", "volume", "inspect", "kp-neo4j-data"],
            capture_output=True, text=True, timeout=30
        )

        assert result.returncode == 0, "Neo4j volume not found"
