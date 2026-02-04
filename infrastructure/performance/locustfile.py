"""
Locust Performance Test - Hybrid RAG Knowledge Platform

STORY-081: Performance Baseline Testing

Alternative to k6 for Python-based load testing.
Supports distributed testing and real-time web UI.

Usage:
    locust -f locustfile.py --host=http://localhost:8000
    locust -f locustfile.py --host=http://localhost:8000 --users 100 --spawn-rate 10

Performance Targets:
    - API Response P50: < 500ms
    - API Response P95: < 2s (acceptable < 3s)
    - Search Latency P95: < 3s (acceptable < 5s)
    - Throughput: > 100 req/s (acceptable > 50 req/s)
    - Error Rate: < 0.1% (acceptable < 1%)
"""

import json
import os
import random
import time
from typing import Any, Dict, List, Optional

from locust import HttpUser, between, events, task
from locust.runners import MasterRunner, WorkerRunner

# =============================================================================
# CONFIGURATION
# =============================================================================

API_PREFIX = os.getenv("API_PREFIX", "/api/v1")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "")

# Sample search queries (Korean)
SEARCH_QUERIES: List[str] = [
    "프로젝트 관리 방법론",
    "소프트웨어 개발 프로세스",
    "품질 관리 절차",
    "보안 정책 가이드라인",
    "시스템 아키텍처 설계",
    "API 연동 가이드",
    "데이터베이스 설계 원칙",
    "테스트 자동화 전략",
    "배포 파이프라인 구성",
    "모니터링 및 알림 설정",
    "장애 대응 프로세스",
    "코드 리뷰 체크리스트",
    "성능 최적화 기법",
    "클라우드 인프라 관리",
    "컨테이너 오케스트레이션",
]

# Sample chat questions (Korean)
CHAT_QUESTIONS: List[str] = [
    "프로젝트 일정 관리에서 가장 중요한 것은 무엇인가요?",
    "RAG 시스템의 장점을 설명해주세요.",
    "마이크로서비스 아키텍처의 특징은 무엇인가요?",
    "CI/CD 파이프라인 구축 방법을 알려주세요.",
    "코드 품질을 높이는 방법은 무엇인가요?",
]

# =============================================================================
# METRICS COLLECTION
# =============================================================================


class PerformanceMetrics:
    """Performance metrics collector."""

    def __init__(self):
        self.search_latencies: List[float] = []
        self.chat_latencies: List[float] = []
        self.errors: int = 0
        self.requests: int = 0

    def add_search_latency(self, latency_ms: float) -> None:
        self.search_latencies.append(latency_ms)

    def add_chat_latency(self, latency_ms: float) -> None:
        self.chat_latencies.append(latency_ms)

    def add_error(self) -> None:
        self.errors += 1

    def add_request(self) -> None:
        self.requests += 1

    def get_percentile(self, data: List[float], percentile: float) -> float:
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]

    def get_summary(self) -> Dict[str, Any]:
        return {
            "search_latency_p50": self.get_percentile(self.search_latencies, 50),
            "search_latency_p95": self.get_percentile(self.search_latencies, 95),
            "chat_latency_p50": self.get_percentile(self.chat_latencies, 50),
            "chat_latency_p95": self.get_percentile(self.chat_latencies, 95),
            "error_rate": (self.errors / self.requests * 100) if self.requests else 0,
            "total_requests": self.requests,
        }


metrics = PerformanceMetrics()


# =============================================================================
# EVENT HOOKS
# =============================================================================


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Test start event handler."""
    print("=" * 60)
    print("Hybrid RAG Knowledge Platform - Performance Test")
    print("=" * 60)
    print(f"Host: {environment.host}")
    print(f"API Prefix: {API_PREFIX}")
    print(f"Auth Token: {'Configured' if AUTH_TOKEN else 'Not configured'}")
    print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Test stop event handler."""
    summary = metrics.get_summary()
    print("\n" + "=" * 60)
    print("PERFORMANCE TEST RESULTS")
    print("=" * 60)
    print(f"Search Latency P50: {summary['search_latency_p50']:.2f}ms")
    print(f"Search Latency P95: {summary['search_latency_p95']:.2f}ms")
    print(f"Chat Latency P50: {summary['chat_latency_p50']:.2f}ms")
    print(f"Chat Latency P95: {summary['chat_latency_p95']:.2f}ms")
    print(f"Error Rate: {summary['error_rate']:.4f}%")
    print(f"Total Requests: {summary['total_requests']}")
    print("=" * 60)

    # Save results to file
    with open("locust-results.json", "w") as f:
        json.dump(
            {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "platform": "Hybrid RAG Knowledge Platform",
                "metrics": summary,
            },
            f,
            indent=2,
        )


@events.request.add_listener
def on_request(
    request_type: str,
    name: str,
    response_time: float,
    response_length: int,
    response: Any,
    exception: Optional[Exception],
    **kwargs,
):
    """Request event handler for custom metrics."""
    metrics.add_request()

    if exception:
        metrics.add_error()
        return

    # Track latencies by endpoint
    if "search" in name.lower():
        metrics.add_search_latency(response_time)
    elif "chat" in name.lower():
        metrics.add_chat_latency(response_time)


# =============================================================================
# USER CLASSES
# =============================================================================


class HybridRAGUser(HttpUser):
    """
    Simulates a typical user of the Hybrid RAG Knowledge Platform.

    Behavior:
    - 10% health checks
    - 50% search operations (hybrid, semantic, keyword)
    - 20% chat operations
    - 20% document operations
    """

    # Wait time between tasks (1-3 seconds)
    wait_time = between(1, 3)

    # Request headers
    headers: Dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Accept-Language": "ko-KR",
    }

    def on_start(self):
        """Setup before tasks start."""
        if AUTH_TOKEN:
            self.headers["Authorization"] = f"Bearer {AUTH_TOKEN}"

    # -------------------------------------------------------------------------
    # Health Check Tasks
    # -------------------------------------------------------------------------

    @task(1)
    def health_check(self):
        """Health check endpoint."""
        with self.client.get(
            f"{API_PREFIX}/health",
            headers=self.headers,
            name="[Health] GET /health",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "status" in data:
                        response.success()
                    else:
                        response.failure("Missing 'status' field")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(1)
    def liveness_probe(self):
        """Kubernetes liveness probe."""
        self.client.get(
            f"{API_PREFIX}/health/live",
            headers=self.headers,
            name="[Health] GET /health/live",
        )

    @task(1)
    def readiness_probe(self):
        """Kubernetes readiness probe."""
        self.client.get(
            f"{API_PREFIX}/health/ready",
            headers=self.headers,
            name="[Health] GET /health/ready",
        )

    # -------------------------------------------------------------------------
    # Search Tasks
    # -------------------------------------------------------------------------

    @task(5)
    def hybrid_search(self):
        """Hybrid search (Vector + Keyword + Graph)."""
        query = random.choice(SEARCH_QUERIES)
        payload = {
            "query": query,
            "top_k": 10,
            "useGraph": True,
            "useVector": True,
        }

        with self.client.post(
            f"{API_PREFIX}/search/hybrid",
            json=payload,
            headers=self.headers,
            name="[Search] POST /search/hybrid",
            timeout=10,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "results" in data and isinstance(data["results"], list):
                        response.success()
                    else:
                        response.failure("Missing 'results' field")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(3)
    def semantic_search(self):
        """Semantic vector search."""
        query = random.choice(SEARCH_QUERIES)
        payload = {
            "query": query,
            "top_k": 10,
        }

        with self.client.post(
            f"{API_PREFIX}/search/semantic",
            json=payload,
            headers=self.headers,
            name="[Search] POST /search/semantic",
            timeout=10,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(2)
    def keyword_search(self):
        """Keyword BM25 search."""
        query = random.choice(SEARCH_QUERIES)
        payload = {
            "query": query,
            "top_k": 10,
        }

        with self.client.post(
            f"{API_PREFIX}/search/keyword",
            json=payload,
            headers=self.headers,
            name="[Search] POST /search/keyword",
            timeout=5,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")

    # -------------------------------------------------------------------------
    # Chat Tasks
    # -------------------------------------------------------------------------

    @task(2)
    def chat_search(self):
        """Chat with LangGraph RAG workflow."""
        question = random.choice(CHAT_QUESTIONS)
        payload = {
            "query": question,
            "topK": 5,
            "useReasoner": False,
        }

        with self.client.post(
            f"{API_PREFIX}/search/chat",
            json=payload,
            headers=self.headers,
            name="[Chat] POST /search/chat",
            timeout=30,  # LLM operations can take longer
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "answer" in data and len(data["answer"]) > 0:
                        response.success()
                    else:
                        response.failure("Missing or empty 'answer' field")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Status code: {response.status_code}")

    # -------------------------------------------------------------------------
    # Document Tasks
    # -------------------------------------------------------------------------

    @task(2)
    def list_documents(self):
        """List documents with pagination."""
        page = random.randint(1, 5)
        with self.client.get(
            f"{API_PREFIX}/documents?page={page}&page_size=20",
            headers=self.headers,
            name="[Documents] GET /documents",
            timeout=5,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "documents" in data and isinstance(data["documents"], list):
                        response.success()
                    else:
                        response.failure("Missing 'documents' field")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Status code: {response.status_code}")


class SearchHeavyUser(HttpUser):
    """
    User that primarily performs search operations.
    Used for testing search-specific performance.
    """

    wait_time = between(0.5, 2)
    weight = 3  # Higher weight = more instances

    headers: Dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    def on_start(self):
        if AUTH_TOKEN:
            self.headers["Authorization"] = f"Bearer {AUTH_TOKEN}"

    @task(10)
    def hybrid_search(self):
        """High-frequency hybrid search."""
        query = random.choice(SEARCH_QUERIES)
        payload = {
            "query": query,
            "top_k": 10,
            "useGraph": True,
            "useVector": True,
        }

        self.client.post(
            f"{API_PREFIX}/search/hybrid",
            json=payload,
            headers=self.headers,
            name="[SearchHeavy] POST /search/hybrid",
            timeout=10,
        )

    @task(5)
    def semantic_search(self):
        """High-frequency semantic search."""
        query = random.choice(SEARCH_QUERIES)
        payload = {
            "query": query,
            "top_k": 10,
        }

        self.client.post(
            f"{API_PREFIX}/search/semantic",
            json=payload,
            headers=self.headers,
            name="[SearchHeavy] POST /search/semantic",
            timeout=10,
        )


class ChatHeavyUser(HttpUser):
    """
    User that primarily uses chat functionality.
    Used for testing LLM-dependent operations.
    """

    wait_time = between(2, 5)  # Longer wait for LLM operations
    weight = 1

    headers: Dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    def on_start(self):
        if AUTH_TOKEN:
            self.headers["Authorization"] = f"Bearer {AUTH_TOKEN}"

    @task(1)
    def chat_search(self):
        """Chat with RAG workflow."""
        question = random.choice(CHAT_QUESTIONS)
        payload = {
            "query": question,
            "topK": 5,
            "useReasoner": False,
        }

        self.client.post(
            f"{API_PREFIX}/search/chat",
            json=payload,
            headers=self.headers,
            name="[ChatHeavy] POST /search/chat",
            timeout=30,
        )


# =============================================================================
# CUSTOM LOAD SHAPES
# =============================================================================


class StagesShape:
    """
    Custom load shape for staged testing.

    Stages:
    1. Warm-up: 0 -> 10 users over 1 minute
    2. Normal load: 10 -> 50 users over 2 minutes
    3. Peak load: 50 -> 100 users over 2 minutes
    4. Sustained: 100 users for 5 minutes
    5. Cool-down: 100 -> 0 users over 1 minute
    """

    stages = [
        {"duration": 60, "users": 10, "spawn_rate": 1},    # Warm-up
        {"duration": 120, "users": 50, "spawn_rate": 2},   # Normal load
        {"duration": 120, "users": 100, "spawn_rate": 2},  # Peak load
        {"duration": 300, "users": 100, "spawn_rate": 10}, # Sustained
        {"duration": 60, "users": 0, "spawn_rate": 5},     # Cool-down
    ]

    def __init__(self):
        self.time_active = 0

    def tick(self):
        run_time = self.get_run_time()
        current_time = 0

        for stage in self.stages:
            current_time += stage["duration"]
            if run_time < current_time:
                return (stage["users"], stage["spawn_rate"])

        return None

    def get_run_time(self):
        return self.time_active


# =============================================================================
# MAIN ENTRY POINT (for running as script)
# =============================================================================

if __name__ == "__main__":
    import subprocess
    import sys

    # Run locust with default parameters
    cmd = [
        sys.executable, "-m", "locust",
        "-f", __file__,
        "--host", os.getenv("HOST", "http://localhost:8000"),
        "--users", os.getenv("USERS", "10"),
        "--spawn-rate", os.getenv("SPAWN_RATE", "2"),
        "--run-time", os.getenv("RUN_TIME", "5m"),
        "--headless",
        "--html", "locust-report.html",
    ]

    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd)
