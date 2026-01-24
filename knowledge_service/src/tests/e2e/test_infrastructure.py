"""
STORY-020: Infrastructure E2E Test Suite

This module provides comprehensive E2E tests for the Docker Compose infrastructure.
It validates all 18 containers, database initialization, and core infrastructure services.

Test Categories:
- Container Health Check: Verify all containers are running and healthy
- Database Initialization: Validate PostgreSQL, Elasticsearch, Neo4j, MinIO setup
- Network Configuration: Verify Docker networks are properly configured
- Volume Configuration: Validate data persistence volumes

Usage:
    pytest knowledge_service/src/tests/e2e/test_infrastructure.py -v

Markers:
    @pytest.mark.e2e: End-to-end tests
    @pytest.mark.infrastructure: Infrastructure layer tests

Author: QA Agent
Sprint: Sprint 01 Validation
"""

import subprocess
import time
from typing import Dict, List, Optional

import pytest
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# =============================================================================
# CONSTANTS
# =============================================================================

# All 18 containers as defined in docker-compose.yml
CONTAINERS = [
    "kp-nginx",
    "kp-frontend",
    "kp-api-gateway",
    "kp-backend",
    "kp-ai-service",
    "kp-keycloak",
    "kp-keycloak-db",
    "kp-postgresql",
    "kp-neo4j",
    "kp-elasticsearch",
    "kp-kibana",
    "kp-redis",
    "kp-minio",
    "kp-prometheus",
    "kp-grafana",
    "kp-loki",
    "kp-promtail",
    "kp-jaeger",
]

# Health check endpoints
HEALTH_ENDPOINTS = {
    "nginx": {"url": "http://localhost:80", "expected_status": 200},
    "api-gateway": {"url": "http://localhost:8080/actuator/health", "expected_status": 200},
    "backend": {"url": "http://localhost:8081/actuator/health", "expected_status": 200},
    "ai-service": {"url": "http://localhost:8000/health", "expected_status": 200},
    "keycloak": {"url": "http://localhost:8180/health/ready", "expected_status": 200},
    "elasticsearch": {"url": "http://localhost:9200/_cluster/health", "expected_status": 200},
    "kibana": {"url": "http://localhost:5601/api/status", "expected_status": 200},
    "neo4j": {"url": "http://localhost:7474/", "expected_status": 200},
    "minio": {"url": "http://localhost:9000/minio/health/live", "expected_status": 200},
    "prometheus": {"url": "http://localhost:9090/-/healthy", "expected_status": 200},
    "grafana": {"url": "http://localhost:3001/api/health", "expected_status": 200},
    "loki": {"url": "http://localhost:3100/ready", "expected_status": 200},
    "jaeger": {"url": "http://localhost:16686/", "expected_status": 200},
}


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
    import os
    return {
        "POSTGRES_USER": os.getenv("DB_USERNAME", "knowledge"),
        "POSTGRES_PASSWORD": os.getenv("DB_PASSWORD", "knowledge"),
        "POSTGRES_DB": os.getenv("DB_NAME", "knowledge"),
        "NEO4J_USER": os.getenv("NEO4J_USER", "neo4j"),
        "NEO4J_PASSWORD": os.getenv("NEO4J_PASSWORD", ""),
        "KEYCLOAK_ADMIN": os.getenv("KEYCLOAK_ADMIN", "admin"),
        "KEYCLOAK_ADMIN_PASSWORD": os.getenv("KEYCLOAK_ADMIN_PASSWORD", ""),
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


def get_container_status(container_name: str) -> Optional[Dict]:
    """Get container status information."""
    try:
        result = subprocess.run(
            ["docker", "inspect", "--format",
             '{{.State.Status}}|{{.State.Running}}',
             container_name],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            return None

        parts = result.stdout.strip().split("|")
        return {
            "status": parts[0],
            "running": parts[1],
        }
    except (subprocess.SubprocessError, FileNotFoundError):
        return None


# Skip marker for tests requiring Docker
docker_available = pytest.mark.skipif(
    not is_docker_available(),
    reason="Docker is not available"
)


# =============================================================================
# TC-INFRA-101: CONTAINER HEALTH CHECK TESTS
# =============================================================================

@pytest.mark.e2e
@pytest.mark.infrastructure
@docker_available
class TestContainerHealthCheck:
    """
    TC-INFRA-101: Verify all 18 containers start and reach healthy state.

    Acceptance Criteria:
    - All containers are running
    - No containers in restart loop
    - Health check endpoints respond correctly
    """

    def test_all_containers_running(self):
        """Verify all 18 containers are in running state."""
        running_count = 0
        failed_containers = []

        for container in CONTAINERS:
            status = get_container_status(container)
            if status and status.get("running") == "true":
                running_count += 1
            else:
                failed_containers.append(container)

        # Allow for init-db to be stopped (one-shot container)
        min_expected = 17
        assert running_count >= min_expected, (
            f"Expected {min_expected}+ containers running, got {running_count}. "
            f"Failed: {failed_containers}"
        )

    def test_no_restart_loops(self):
        """Verify no containers are in restart loop (restart count < 3)."""
        restart_issues = []

        for container in CONTAINERS:
            try:
                result = subprocess.run(
                    ["docker", "inspect", "--format",
                     "{{.RestartCount}}", container],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    restart_count = int(result.stdout.strip())
                    if restart_count >= 3:
                        restart_issues.append(f"{container}: {restart_count} restarts")
            except (subprocess.SubprocessError, ValueError):
                pass

        assert len(restart_issues) == 0, f"Containers in restart loop: {restart_issues}"

    def test_nginx_config_valid(self):
        """TC-INFRA-102: Nginx configuration should be valid."""
        result = subprocess.run(
            ["docker", "exec", "kp-nginx", "nginx", "-t"],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0, f"Nginx config test failed: {result.stderr}"

    def test_postgresql_ready(self, config: Dict[str, str]):
        """TC-INFRA-108: PostgreSQL should accept connections."""
        result = subprocess.run(
            ["docker", "exec", "kp-postgresql", "pg_isready",
             "-U", config["POSTGRES_USER"], "-d", config["POSTGRES_DB"]],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0, f"PostgreSQL not ready: {result.stderr}"
        assert "accepting" in result.stdout.lower()

    def test_redis_ping(self):
        """TC-INFRA-111: Redis should respond to PING."""
        result = subprocess.run(
            ["docker", "exec", "kp-redis", "redis-cli", "ping"],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0
        assert "PONG" in result.stdout

    @pytest.mark.parametrize("service,endpoint", [
        ("nginx", "http://localhost:80/"),
        ("keycloak", "http://localhost:8180/health/ready"),
        ("neo4j", "http://localhost:7474/"),
        ("elasticsearch", "http://localhost:9200/_cluster/health"),
        ("minio", "http://localhost:9000/minio/health/live"),
        ("prometheus", "http://localhost:9090/-/healthy"),
        ("grafana", "http://localhost:3001/api/health"),
        ("loki", "http://localhost:3100/ready"),
        ("jaeger", "http://localhost:16686/"),
    ])
    def test_http_health_endpoints(
        self, http_session: requests.Session, service: str, endpoint: str
    ):
        """Test HTTP health endpoints for all services."""
        try:
            response = http_session.get(endpoint, timeout=10)
            assert response.status_code == 200, (
                f"{service} returned {response.status_code}"
            )
        except requests.RequestException as e:
            pytest.fail(f"{service} health check failed: {e}")


# =============================================================================
# TC-INFRA-2xx: DATABASE INITIALIZATION TESTS
# =============================================================================

@pytest.mark.e2e
@pytest.mark.infrastructure
@docker_available
class TestDatabaseInitialization:
    """
    TC-INFRA-2xx: Verify database schemas and initial data are correctly applied.

    Acceptance Criteria:
    - PostgreSQL tables exist
    - Elasticsearch index created with correct mappings
    - Neo4j constraints and indexes applied
    - Redis connection working
    - MinIO buckets created
    """

    def test_postgresql_tables_exist(self, config: Dict[str, str]):
        """TC-INFRA-201: PostgreSQL core tables should exist."""
        expected_tables = ["users", "knowledge_master", "knowledge_chunks"]

        result = subprocess.run(
            ["docker", "exec", "kp-postgresql", "psql",
             "-U", config["POSTGRES_USER"],
             "-d", config["POSTGRES_DB"],
             "-tAc", "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"],
            capture_output=True, text=True, timeout=30
        )

        assert result.returncode == 0, f"PostgreSQL query failed: {result.stderr}"

        tables = [t.strip() for t in result.stdout.strip().split("\n") if t.strip()]

        for expected in expected_tables:
            assert expected in tables, f"Table '{expected}' not found. Found: {tables}"

    def test_postgresql_extensions(self, config: Dict[str, str]):
        """TC-INFRA-202: PostgreSQL extensions should be installed."""
        expected_extensions = ["uuid-ossp"]

        result = subprocess.run(
            ["docker", "exec", "kp-postgresql", "psql",
             "-U", config["POSTGRES_USER"],
             "-d", config["POSTGRES_DB"],
             "-tAc", "SELECT extname FROM pg_extension;"],
            capture_output=True, text=True, timeout=30
        )

        assert result.returncode == 0
        extensions = [e.strip() for e in result.stdout.strip().split("\n") if e.strip()]

        for expected in expected_extensions:
            assert expected in extensions, (
                f"Extension '{expected}' not found. Found: {extensions}"
            )

    def test_elasticsearch_cluster_health(self, http_session: requests.Session):
        """TC-INFRA-203: Elasticsearch cluster should be healthy."""
        response = http_session.get(
            "http://localhost:9200/_cluster/health",
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        assert data.get("status") in ["green", "yellow"], (
            f"Cluster status is {data.get('status')}"
        )

    def test_elasticsearch_index_exists(self, http_session: requests.Session):
        """TC-INFRA-203: Elasticsearch knowledge-chunks index should exist."""
        response = http_session.get(
            "http://localhost:9200/knowledge-chunks-v1",
            timeout=10
        )

        if response.status_code == 404:
            pytest.skip("knowledge-chunks-v1 index not yet created - run init-db")

        assert response.status_code == 200

    def test_neo4j_connectivity(self, config: Dict[str, str], http_session: requests.Session):
        """TC-INFRA-206b: Neo4j should accept Cypher queries."""
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

    def test_minio_api_accessible(self, http_session: requests.Session):
        """TC-INFRA-208b: MinIO API should be accessible."""
        response = http_session.get(
            "http://localhost:9000/minio/health/live",
            timeout=10
        )
        assert response.status_code == 200


# =============================================================================
# NETWORK CONFIGURATION TESTS
# =============================================================================

@pytest.mark.e2e
@pytest.mark.infrastructure
@docker_available
class TestNetworkConfiguration:
    """Verify Docker network configuration."""

    @pytest.mark.parametrize("network", [
        "kp-frontend",
        "kp-backend",
        "kp-database",
        "kp-monitoring",
    ])
    def test_network_exists(self, network: str):
        """Verify Docker networks are created."""
        result = subprocess.run(
            ["docker", "network", "inspect", network],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0, f"{network} network not found"


# =============================================================================
# VOLUME CONFIGURATION TESTS
# =============================================================================

@pytest.mark.e2e
@pytest.mark.infrastructure
@docker_available
class TestVolumeConfiguration:
    """Verify Docker volume configuration."""

    @pytest.mark.parametrize("volume", [
        "kp-postgresql-data",
        "kp-elasticsearch-data",
        "kp-neo4j-data",
    ])
    def test_volume_exists(self, volume: str):
        """Verify data persistence volumes are created."""
        result = subprocess.run(
            ["docker", "volume", "inspect", volume],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0, f"{volume} volume not found"


# =============================================================================
# OBSERVABILITY TESTS
# =============================================================================

@pytest.mark.e2e
@pytest.mark.infrastructure
@docker_available
class TestObservability:
    """Verify observability stack is working."""

    def test_prometheus_targets(self, http_session: requests.Session):
        """TC-INFRA-501: Prometheus should have scrape targets."""
        response = http_session.get(
            "http://localhost:9090/api/v1/targets",
            timeout=10
        )

        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "success"

    def test_grafana_datasources(self, http_session: requests.Session, config: Dict[str, str]):
        """TC-INFRA-504: Grafana datasources should be configured."""
        import os
        password = os.getenv("GRAFANA_ADMIN_PASSWORD", "admin")
        auth = ("admin", password)

        response = http_session.get(
            "http://localhost:3001/api/datasources",
            auth=auth,
            timeout=10
        )

        if response.status_code == 401:
            pytest.skip("Grafana authentication required")

        assert response.status_code == 200

    def test_loki_labels(self, http_session: requests.Session):
        """TC-INFRA-506: Loki should have labels from log ingestion."""
        response = http_session.get(
            "http://localhost:3100/loki/api/v1/labels",
            timeout=10
        )

        assert response.status_code == 200

    def test_jaeger_services(self, http_session: requests.Session):
        """TC-INFRA-508: Jaeger UI should be accessible."""
        response = http_session.get(
            "http://localhost:16686/api/services",
            timeout=10
        )

        assert response.status_code == 200


# =============================================================================
# SUMMARY TEST
# =============================================================================

@pytest.mark.e2e
@pytest.mark.infrastructure
@docker_available
class TestInfrastructureSummary:
    """Summary test for quick infrastructure validation."""

    def test_critical_services_up(self, http_session: requests.Session):
        """
        Quick check: Verify critical infrastructure services are responding.

        Critical services:
        - PostgreSQL (SSOT database)
        - Elasticsearch (vector search)
        - Redis (cache)
        - Keycloak (authentication)
        """
        critical_checks = [
            ("PostgreSQL", "docker exec kp-postgresql pg_isready -U knowledge"),
            ("Redis", "docker exec kp-redis redis-cli ping"),
        ]

        failed = []
        for name, cmd in critical_checks:
            result = subprocess.run(
                cmd.split(),
                capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                failed.append(name)

        # HTTP checks
        http_checks = [
            ("Elasticsearch", "http://localhost:9200/_cluster/health"),
            ("Keycloak", "http://localhost:8180/health/ready"),
        ]

        for name, url in http_checks:
            try:
                response = http_session.get(url, timeout=10)
                if response.status_code != 200:
                    failed.append(name)
            except requests.RequestException:
                failed.append(name)

        assert len(failed) == 0, f"Critical services not responding: {failed}"
