"""
검색 API 엔드포인트 테스트

/api/v1/search 엔드포인트 테스트
"""

import pytest
from fastapi.testclient import TestClient


class TestSearchEndpoints:
    """검색 엔드포인트 테스트"""

    def test_hybrid_search(self, client: TestClient, api_prefix: str, sample_query: str):
        """Hybrid 검색 테스트"""
        response = client.post(
            f"{api_prefix}/search/hybrid",
            json={"query": sample_query, "top_k": 5},
        )

        assert response.status_code == 200

        data = response.json()
        assert "query" in data
        assert "results" in data
        assert "total" in data

        assert data["query"] == sample_query
        assert isinstance(data["results"], list)

    def test_hybrid_search_validation_error(self, client: TestClient, api_prefix: str):
        """Hybrid 검색 유효성 검사 테스트"""
        # 빈 쿼리
        response = client.post(
            f"{api_prefix}/search/hybrid",
            json={"query": "", "top_k": 5},
        )

        assert response.status_code == 422  # Validation Error

    def test_chat_search(self, client: TestClient, api_prefix: str, sample_query: str):
        """대화형 검색 테스트"""
        response = client.post(
            f"{api_prefix}/search/chat",
            json={"query": sample_query},
        )

        assert response.status_code == 200

        data = response.json()
        assert "answer" in data
        assert "sources" in data

    def test_chat_search_with_conversation_id(
        self, client: TestClient, api_prefix: str, sample_query: str
    ):
        """대화 ID를 포함한 대화형 검색 테스트"""
        response = client.post(
            f"{api_prefix}/search/chat",
            json={
                "query": sample_query,
                "conversation_id": "test-conv-123",
            },
        )

        assert response.status_code == 200

        data = response.json()
        assert data["conversation_id"] == "test-conv-123"
