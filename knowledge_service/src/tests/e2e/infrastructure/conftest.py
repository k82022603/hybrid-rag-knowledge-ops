"""
Infrastructure E2E Test Configuration

pytest fixtures and configuration for infrastructure testing.
SCRUM-20: Sprint 01 Validation
"""

import os
import subprocess
import time
from typing import Dict, Generator, List, Optional

import pytest
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# =============================================================================
# PYTEST CONFIGURATION - SCRUM-20: Phased Testing
# =============================================================================

def pytest_configure(config):
    """Register custom pytest markers for phased testing."""
    config.addinivalue_line(
        "markers", "infrastructure: Infrastructure layer tests (databases, monitoring)"
    )
    config.addinivalue_line(
        "markers", "application: Application layer tests (requires app containers)"
    )


# =============================================================================
# CONFIGURATION
# =============================================================================

# Container names (18 containers)
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
    # "kp-init-db",  # One-shot container, not always running
]

# Service endpoints
SERVICE_ENDPOINTS = {
    "nginx": {"url": "http://localhost:80", "health": "/"},
    "frontend": {"url": "http://localhost:80", "health": "/"},
    "api-gateway": {"url": "http://localhost:8080", "health": "/actuator/health"},
    "backend": {"url": "http://localhost:8081", "health": "/actuator/health"},
    "ai-service": {"url": "http://localhost:8000", "health": "/health"},
    "keycloak": {"url": "http://localhost:8180", "health": "/health/ready"},
    "postgresql": {"host": "localhost", "port": 5432},
    "neo4j": {"url": "http://localhost:7474", "health": "/"},
    "elasticsearch": {"url": "http://localhost:9200", "health": "/_cluster/health"},
    "kibana": {"url": "http://localhost:5601", "health": "/api/status"},
    "redis": {"host": "localhost", "port": 6379},
    "minio": {"url": "http://localhost:9000", "health": "/minio/health/live"},
    "prometheus": {"url": "http://localhost:9090", "health": "/-/healthy"},
    "grafana": {"url": "http://localhost:3001", "health": "/api/health"},
    "loki": {"url": "http://localhost:3100", "health": "/ready"},
    "jaeger": {"url": "http://localhost:16686", "health": "/"},
}

# Environment variables (loaded from .env or defaults)
DEFAULT_CONFIG = {
    "POSTGRES_USER": os.getenv("DB_USERNAME", "knowledge"),
    "POSTGRES_PASSWORD": os.getenv("DB_PASSWORD", "knowledge"),
    "POSTGRES_DB": os.getenv("DB_NAME", "knowledge"),
    "NEO4J_USER": os.getenv("NEO4J_USER", "neo4j"),
    "NEO4J_PASSWORD": os.getenv("NEO4J_PASSWORD", ""),
    "ELASTIC_USER": os.getenv("ELASTIC_USER", "elastic"),
    "ELASTIC_PASSWORD": os.getenv("ELASTIC_PASSWORD", ""),
    "KEYCLOAK_ADMIN": os.getenv("KEYCLOAK_ADMIN", "admin"),
    "KEYCLOAK_ADMIN_PASSWORD": os.getenv("KEYCLOAK_ADMIN_PASSWORD", ""),
    "KEYCLOAK_REALM": os.getenv("KEYCLOAK_REALM", "hybrid-rag"),
    "MINIO_ACCESS_KEY": os.getenv("MINIO_ACCESS_KEY", ""),
    "MINIO_SECRET_KEY": os.getenv("MINIO_SECRET_KEY", ""),
    "GRAFANA_ADMIN_USER": os.getenv("GRAFANA_ADMIN_USER", "admin"),
    "GRAFANA_ADMIN_PASSWORD": os.getenv("GRAFANA_ADMIN_PASSWORD", "admin"),
}


# =============================================================================
# SESSION FIXTURES
# =============================================================================

@pytest.fixture(scope="session")
def docker_compose_dir() -> str:
    """Docker Compose directory path."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ))))
    return os.path.join(base_dir, "infrastructure", "docker")


@pytest.fixture(scope="session")
def config() -> Dict[str, str]:
    """Test configuration from environment."""
    return DEFAULT_CONFIG


@pytest.fixture(scope="session")
def http_session() -> requests.Session:
    """HTTP session with retry logic."""
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


@pytest.fixture(scope="session")
def containers() -> List[str]:
    """List of container names."""
    return CONTAINERS


@pytest.fixture(scope="session")
def service_endpoints() -> Dict[str, Dict]:
    """Service endpoint configurations."""
    return SERVICE_ENDPOINTS


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
        # First get basic status (works for all containers)
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
        status_info = {
            "status": parts[0],
            "running": parts[1],
            "health": None
        }

        # Try to get health status (may fail for containers without health check)
        health_result = subprocess.run(
            ["docker", "inspect", "--format",
             '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}',
             container_name],
            capture_output=True,
            text=True,
            timeout=10
        )
        if health_result.returncode == 0:
            health = health_result.stdout.strip()
            status_info["health"] = health if health != "none" else None

        return status_info
    except (subprocess.SubprocessError, FileNotFoundError):
        return None


def wait_for_container_healthy(container_name: str, timeout: int = 300) -> bool:
    """Wait for container to become healthy."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        status = get_container_status(container_name)
        if status:
            if status.get("health") == "healthy":
                return True
            if status.get("status") == "running" and not status.get("health"):
                # Container without health check
                return True
        time.sleep(5)
    return False


def wait_for_http_endpoint(url: str, timeout: int = 60) -> bool:
    """Wait for HTTP endpoint to respond."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code < 500:
                return True
        except requests.RequestException:
            pass
        time.sleep(2)
    return False


# =============================================================================
# SKIP CONDITIONS
# =============================================================================

docker_available = pytest.mark.skipif(
    not is_docker_available(),
    reason="Docker is not available"
)
