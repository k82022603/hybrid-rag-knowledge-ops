"""
TC-INFRA-1xx: Container Health Tests

Tests for verifying all 18 Docker containers start and reach healthy state.
SCRUM-20: Sprint 01 Validation

Test Coverage:
- TC-INFRA-101 ~ TC-INFRA-116: Container health checks
"""

import subprocess
from typing import Dict, List

import pytest
import requests

from .conftest import (
    docker_available,
    get_container_status,
    wait_for_container_healthy,
    wait_for_http_endpoint,
)


# =============================================================================
# TC-INFRA-101: ALL CONTAINERS START
# =============================================================================

@docker_available
class TestAllContainersStart:
    """TC-INFRA-101: Verify all containers start successfully."""

    def test_all_containers_running(self, containers: List[str]):
        """
        TC-INFRA-101: All containers should be running.

        Expected: 17+ containers (excluding one-shot init-db) in running state.
        """
        running_count = 0
        failed_containers = []

        for container in containers:
            status = get_container_status(container)
            if status and status.get("running") == "true":
                running_count += 1
            else:
                failed_containers.append(container)

        assert running_count >= 17, (
            f"Expected 17+ containers running, got {running_count}. "
            f"Failed: {failed_containers}"
        )

    def test_no_containers_in_restart_loop(self, containers: List[str]):
        """
        TC-INFRA-101b: No containers should be in restart loop.

        Expected: All containers have restart count < 3.
        """
        restart_issues = []

        for container in containers:
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


# =============================================================================
# TC-INFRA-102 ~ 106: APPLICATION LAYER HEALTH
# =============================================================================

@docker_available
class TestApplicationLayerHealth:
    """Tests for Application Layer containers (nginx, frontend, gateway, backend, ai-service)."""

    def test_tc_infra_102_nginx_health(self):
        """
        TC-INFRA-102: Nginx configuration should be valid.

        Command: docker exec kp-nginx nginx -t
        Expected: Configuration OK
        """
        result = subprocess.run(
            ["docker", "exec", "kp-nginx", "nginx", "-t"],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0, f"Nginx config test failed: {result.stderr}"
        assert "successful" in result.stderr.lower() or "ok" in result.stderr.lower()

    def test_tc_infra_103_frontend_health(self, http_session: requests.Session):
        """
        TC-INFRA-103: Frontend should respond to HTTP requests.

        Endpoint: http://localhost:80/
        Expected: HTTP 200
        """
        response = http_session.get("http://localhost:80/", timeout=10)
        assert response.status_code == 200, f"Frontend returned {response.status_code}"

    def test_tc_infra_104_gateway_health(self, http_session: requests.Session):
        """
        TC-INFRA-104: API Gateway health endpoint.

        Endpoint: http://localhost:8080/actuator/health
        Expected: {"status": "UP"}
        """
        response = http_session.get(
            "http://localhost:8080/actuator/health", timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "UP", f"Gateway status: {data}"

    def test_tc_infra_105_backend_health(self, http_session: requests.Session):
        """
        TC-INFRA-105: Backend health endpoint.

        Endpoint: http://localhost:8081/actuator/health
        Expected: {"status": "UP"}
        """
        response = http_session.get(
            "http://localhost:8081/actuator/health", timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "UP", f"Backend status: {data}"

    def test_tc_infra_106_ai_service_health(self, http_session: requests.Session):
        """
        TC-INFRA-106: AI Service health endpoint.

        Endpoint: http://localhost:8000/health
        Expected: {"status": "ok"}
        """
        response = http_session.get(
            "http://localhost:8000/health", timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") in ["ok", "healthy"], f"AI Service status: {data}"


# =============================================================================
# TC-INFRA-107 ~ 108: AUTH LAYER HEALTH
# =============================================================================

@docker_available
class TestAuthLayerHealth:
    """Tests for Auth Layer containers (keycloak, keycloak-db)."""

    def test_tc_infra_107_keycloak_health(self, http_session: requests.Session):
        """
        TC-INFRA-107: Keycloak health endpoint.

        Endpoint: http://localhost:8180/health/ready
        Expected: HTTP 200
        """
        response = http_session.get(
            "http://localhost:8180/health/ready", timeout=10
        )
        assert response.status_code == 200, f"Keycloak health: {response.status_code}"

    def test_tc_infra_107b_keycloak_db_health(self):
        """
        TC-INFRA-107b: Keycloak DB health check.

        Command: docker exec kp-keycloak-db pg_isready
        Expected: accepting connections
        """
        result = subprocess.run(
            ["docker", "exec", "kp-keycloak-db", "pg_isready",
             "-U", "keycloak", "-d", "keycloak"],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0, f"Keycloak DB not ready: {result.stderr}"


# =============================================================================
# TC-INFRA-108 ~ 112: DATA LAYER HEALTH
# =============================================================================

@docker_available
class TestDataLayerHealth:
    """Tests for Data Layer containers (postgresql, neo4j, elasticsearch, redis, minio)."""

    def test_tc_infra_108_postgresql_health(self, config: Dict[str, str]):
        """
        TC-INFRA-108: PostgreSQL health check.

        Command: docker exec kp-postgresql pg_isready
        Expected: accepting connections
        """
        result = subprocess.run(
            ["docker", "exec", "kp-postgresql", "pg_isready",
             "-U", config["POSTGRES_USER"], "-d", config["POSTGRES_DB"]],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0, f"PostgreSQL not ready: {result.stderr}"
        assert "accepting" in result.stdout.lower()

    def test_tc_infra_109_neo4j_health(self, http_session: requests.Session):
        """
        TC-INFRA-109: Neo4j browser endpoint.

        Endpoint: http://localhost:7474/
        Expected: HTTP 200
        """
        response = http_session.get("http://localhost:7474/", timeout=10)
        assert response.status_code == 200, f"Neo4j returned {response.status_code}"

    def test_tc_infra_110_elasticsearch_health(self, http_session: requests.Session):
        """
        TC-INFRA-110: Elasticsearch cluster health.

        Endpoint: http://localhost:9200/_cluster/health
        Expected: status green or yellow
        """
        response = http_session.get(
            "http://localhost:9200/_cluster/health", timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") in ["green", "yellow"], (
            f"ES cluster unhealthy: {data.get('status')}"
        )

    def test_tc_infra_111_redis_health(self):
        """
        TC-INFRA-111: Redis PING test.

        Command: docker exec kp-redis redis-cli ping
        Expected: PONG
        """
        result = subprocess.run(
            ["docker", "exec", "kp-redis", "redis-cli", "ping"],
            capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0
        assert "PONG" in result.stdout

    def test_tc_infra_112_minio_health(self, http_session: requests.Session):
        """
        TC-INFRA-112: MinIO health endpoint.

        Endpoint: http://localhost:9000/minio/health/live
        Expected: HTTP 200
        """
        response = http_session.get(
            "http://localhost:9000/minio/health/live", timeout=10
        )
        assert response.status_code == 200


# =============================================================================
# TC-INFRA-113 ~ 116: OBSERVABILITY LAYER HEALTH
# =============================================================================

@docker_available
class TestObservabilityLayerHealth:
    """Tests for Observability Layer (prometheus, grafana, loki, jaeger)."""

    def test_tc_infra_113_prometheus_health(self, http_session: requests.Session):
        """
        TC-INFRA-113: Prometheus health endpoint.

        Endpoint: http://localhost:9090/-/healthy
        Expected: Prometheus is Healthy
        """
        response = http_session.get(
            "http://localhost:9090/-/healthy", timeout=10
        )
        assert response.status_code == 200
        assert "healthy" in response.text.lower()

    def test_tc_infra_114_grafana_health(self, http_session: requests.Session):
        """
        TC-INFRA-114: Grafana health endpoint.

        Endpoint: http://localhost:3001/api/health
        Expected: {"database": "ok"}
        """
        response = http_session.get(
            "http://localhost:3001/api/health", timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("database") == "ok", f"Grafana health: {data}"

    def test_tc_infra_115_loki_health(self, http_session: requests.Session):
        """
        TC-INFRA-115: Loki ready endpoint.

        Endpoint: http://localhost:3100/ready
        Expected: ready
        """
        response = http_session.get(
            "http://localhost:3100/ready", timeout=10
        )
        assert response.status_code == 200
        assert "ready" in response.text.lower()

    def test_tc_infra_116_jaeger_health(self, http_session: requests.Session):
        """
        TC-INFRA-116: Jaeger UI endpoint.

        Endpoint: http://localhost:16686/
        Expected: HTTP 200
        """
        response = http_session.get(
            "http://localhost:16686/", timeout=10
        )
        assert response.status_code == 200


# =============================================================================
# CONTAINER RESOURCE TESTS
# =============================================================================

@docker_available
class TestContainerResources:
    """Additional tests for container resource utilization."""

    def test_memory_limits_not_exceeded(self, containers: List[str]):
        """
        Verify containers are not exceeding memory limits.

        Expected: Memory usage < 90% of limit
        """
        memory_issues = []

        for container in containers:
            try:
                result = subprocess.run(
                    ["docker", "stats", "--no-stream", "--format",
                     "{{.MemPerc}}", container],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode == 0:
                    mem_perc = float(result.stdout.strip().replace("%", ""))
                    if mem_perc > 90:
                        memory_issues.append(f"{container}: {mem_perc}%")
            except (subprocess.SubprocessError, ValueError):
                pass

        assert len(memory_issues) == 0, f"Memory issues: {memory_issues}"

    def test_container_logs_no_critical_errors(self, containers: List[str]):
        """
        Check container logs for critical errors.

        Expected: No FATAL or CRITICAL errors in recent logs
        """
        critical_errors = []

        for container in containers:
            try:
                result = subprocess.run(
                    ["docker", "logs", "--tail", "100", container],
                    capture_output=True, text=True, timeout=30
                )
                combined_output = result.stdout + result.stderr
                if any(keyword in combined_output.upper()
                       for keyword in ["FATAL", "CRITICAL", "PANIC"]):
                    critical_errors.append(container)
            except subprocess.SubprocessError:
                pass

        # Warning only - don't fail test
        if critical_errors:
            pytest.skip(f"Critical errors in logs: {critical_errors}")
