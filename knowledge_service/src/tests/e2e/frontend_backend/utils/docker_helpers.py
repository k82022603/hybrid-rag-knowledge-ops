"""
Docker Container Control Utilities for E2E Testing

Provides helpers for managing Docker containers during E2E tests,
including stopping/starting services to simulate failure scenarios.

Features:
- Container stop/start with health check polling
- Service health verification
- Cleanup context managers

Note: These helpers are designed for tests that require Docker Compose
environment. In mock mode, they return simulated responses.

Author: QA Agent
Sprint: Sprint 04 Day 3
"""

import asyncio
import subprocess
import time
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from typing import Dict, List, Optional

import httpx


@dataclass
class ContainerInfo:
    """Information about a Docker container."""

    name: str
    port: int
    health_path: str = "/health"
    health_timeout: float = 30.0


# Container registry for the Hybrid RAG Knowledge Platform
CONTAINERS: Dict[str, ContainerInfo] = {
    "frontend": ContainerInfo(name="kp-frontend", port=3000, health_path="/"),
    "gateway": ContainerInfo(name="kp-gateway", port=8080, health_path="/actuator/health"),
    "backend": ContainerInfo(name="kp-backend", port=8081, health_path="/actuator/health"),
    "ai_service": ContainerInfo(name="kp-ai-service", port=8000, health_path="/health"),
    "knowledge_service": ContainerInfo(
        name="kp-knowledge-service", port=8001, health_path="/health"
    ),
    "postgres": ContainerInfo(name="kp-postgres", port=5432, health_path=""),
    "elasticsearch": ContainerInfo(name="kp-elasticsearch", port=9200, health_path="/"),
    "neo4j": ContainerInfo(name="kp-neo4j", port=7474, health_path="/"),
    "keycloak": ContainerInfo(name="kp-keycloak", port=8180, health_path="/health"),
    "redis": ContainerInfo(name="kp-redis", port=6379, health_path=""),
    "nginx": ContainerInfo(name="kp-nginx", port=80, health_path="/"),
}


def stop_container(container_key: str) -> bool:
    """Stop a Docker container by key.

    Args:
        container_key: Container identifier (e.g., 'backend', 'keycloak')

    Returns:
        True if successfully stopped, False otherwise
    """
    info = CONTAINERS.get(container_key)
    if not info:
        return False

    try:
        result = subprocess.run(
            ["docker", "stop", info.name],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def start_container(container_key: str) -> bool:
    """Start a Docker container by key.

    Args:
        container_key: Container identifier

    Returns:
        True if successfully started, False otherwise
    """
    info = CONTAINERS.get(container_key)
    if not info:
        return False

    try:
        result = subprocess.run(
            ["docker", "start", info.name],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def check_container_health(container_key: str, timeout: float = 5.0) -> bool:
    """Check if a container is healthy via HTTP health endpoint.

    Args:
        container_key: Container identifier
        timeout: HTTP request timeout

    Returns:
        True if healthy, False otherwise
    """
    info = CONTAINERS.get(container_key)
    if not info or not info.health_path:
        return False

    try:
        response = httpx.get(
            f"http://localhost:{info.port}{info.health_path}",
            timeout=timeout,
        )
        return response.status_code < 500
    except (httpx.RequestError, httpx.TimeoutException):
        return False


async def wait_for_container_health(
    container_key: str,
    timeout: float = 60.0,
    poll_interval: float = 2.0,
) -> bool:
    """Wait for a container to become healthy.

    Args:
        container_key: Container identifier
        timeout: Maximum wait time in seconds
        poll_interval: Time between health checks

    Returns:
        True if container became healthy within timeout
    """
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        if check_container_health(container_key):
            return True
        await asyncio.sleep(poll_interval)
    return False


@contextmanager
def container_down(container_key: str):
    """Context manager to temporarily stop a container.

    Stops the container on entry and restarts on exit.
    Useful for failure scenario testing.

    Args:
        container_key: Container identifier

    Example:
        with container_down("keycloak"):
            # Test behavior when Keycloak is unavailable
            response = client.post("/api/v1/auth/login", ...)
            assert response.status_code == 503
    """
    try:
        stop_container(container_key)
        time.sleep(2)  # Wait for container to fully stop
        yield
    finally:
        start_container(container_key)
        time.sleep(5)  # Wait for container to start up


@asynccontextmanager
async def async_container_down(container_key: str):
    """Async context manager to temporarily stop a container.

    Args:
        container_key: Container identifier
    """
    try:
        stop_container(container_key)
        await asyncio.sleep(2)
        yield
    finally:
        start_container(container_key)
        await asyncio.sleep(5)


def is_docker_available() -> bool:
    """Check if Docker is available on the system.

    Returns:
        True if docker CLI is available and daemon is running
    """
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def get_all_container_statuses() -> Dict[str, bool]:
    """Get health status of all registered containers.

    Returns:
        Dict mapping container keys to their health status
    """
    statuses = {}
    for key in CONTAINERS:
        statuses[key] = check_container_health(key, timeout=3.0)
    return statuses
