"""
Health Check 엔드포인트 테스트

/api/v1/health 엔드포인트 테스트
"""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Health Check 엔드포인트 테스트"""

    def test_health_check(self, client: TestClient, api_prefix: str):
        """기본 Health Check 테스트"""
        response = client.get(f"{api_prefix}/health")

        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "timestamp" in data
        assert "dependencies" in data

        assert data["status"] in ["healthy", "degraded", "unhealthy"]

    def test_liveness_probe(self, client: TestClient, api_prefix: str):
        """Liveness Probe 테스트"""
        response = client.get(f"{api_prefix}/health/live")

        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "alive"

    def test_readiness_probe(self, client: TestClient, api_prefix: str):
        """Readiness Probe 테스트"""
        response = client.get(f"{api_prefix}/health/ready")

        assert response.status_code == 200

        data = response.json()
        assert "ready" in data
        assert "checks" in data
        assert isinstance(data["checks"], dict)
