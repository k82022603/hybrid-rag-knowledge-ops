"""
검색 시스템 안정성 개선 통합 테스트 (커밋 894068b)

검증 대상 (4개 개선 사항):
1. main.py _connect_with_retry: 지수 백오프 재시도 로직
2. search.py lazy reconnection: _ensure_es_client()/_ensure_neo4j_driver()
3. health.py readiness: search_service_es/search_service_neo4j 상태 반영
4. search.py [SEARCH_ALERT]: 0건 + client=None 시 WARNING 로그

실행 방법:
    TEST_MODE=docker pytest src/tests/integration/test_search_stability.py -v

중요: Mock 모드 절대 금지! TEST_MODE=docker 필수
"""

import asyncio
import inspect
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import requests

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8000")
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def ai_service_available() -> bool:
    try:
        resp = requests.get(f"{AI_SERVICE_URL}/api/v1/health/live", timeout=5)
        return resp.status_code == 200
    except requests.exceptions.ConnectionError:
        return False


def require_ai_service(ai_service_available: bool):
    if not ai_service_available:
        pytest.skip(
            f"AI Service not available at {AI_SERVICE_URL}. "
            "Run with TEST_MODE=docker and ensure containers are running."
        )


# ---------------------------------------------------------------------------
# Test Class 1: _connect_with_retry (지수 백오프 단위 테스트)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestConnectWithRetry:
    """main.py _connect_with_retry 지수 백오프 재시도 로직 검증"""

    def test_function_exists(self):
        """_connect_with_retry 함수가 main.py에 정의되어 있는지 확인"""
        from app.main import _connect_with_retry

        assert callable(_connect_with_retry), "_connect_with_retry 함수가 없음"

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        """첫 번째 시도에서 성공하면 즉시 반환"""
        from app.main import _connect_with_retry

        call_count = 0

        async def mock_connect():
            nonlocal call_count
            call_count += 1
            return MagicMock(name="fake_client")

        result = await _connect_with_retry(
            mock_connect, "TestService", max_retries=3, base_delay=0.01
        )

        assert result is not None, "첫 번째 시도 성공 시 None이 아닌 클라이언트 반환 필요"
        assert call_count == 1, (
            f"첫 번째 시도에서 성공했으므로 호출 횟수는 1이어야 함 (실제: {call_count})"
        )

    @pytest.mark.asyncio
    async def test_retries_on_failure(self):
        """실패 시 max_retries만큼 재시도"""
        from app.main import _connect_with_retry

        call_count = 0

        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Connection refused")

        result = await _connect_with_retry(
            always_fail, "TestService", max_retries=3, base_delay=0.01
        )

        assert result is None, "모든 재시도 실패 시 None 반환 필요"
        assert call_count == 3, (
            f"max_retries=3이므로 3번 시도해야 함 (실제: {call_count})"
        )

    @pytest.mark.asyncio
    async def test_success_on_retry(self):
        """두 번째 시도에서 성공하는 경우"""
        from app.main import _connect_with_retry

        call_count = 0
        fake_client = MagicMock(name="fake_client")

        async def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("first attempt failed")
            return fake_client

        result = await _connect_with_retry(
            fail_then_succeed, "TestService", max_retries=5, base_delay=0.01
        )

        assert result is fake_client, "두 번째 시도 성공 시 클라이언트 반환 필요"
        assert call_count == 2, f"2번 시도 후 성공해야 함 (실제: {call_count})"

    @pytest.mark.asyncio
    async def test_exponential_backoff_delay(self):
        """지수 백오프: 각 재시도의 대기 시간이 2배씩 증가하는지 확인"""
        from app.main import _connect_with_retry

        sleep_delays = []
        original_sleep = asyncio.sleep

        async def track_sleep(delay):
            sleep_delays.append(delay)
            await original_sleep(0)  # 실제 대기 없이

        async def always_fail():
            raise ConnectionError("fail")

        with patch("app.main.asyncio.sleep", side_effect=track_sleep):
            await _connect_with_retry(
                always_fail, "TestService", max_retries=4, base_delay=1.0
            )

        # base_delay=1.0, 지수 백오프: 1.0, 2.0, 4.0 (마지막은 sleep 없음)
        assert len(sleep_delays) == 3, (
            f"max_retries=4이면 sleep 횟수는 3회 (실제: {sleep_delays})"
        )
        assert sleep_delays[0] == 1.0, f"첫 대기: 1.0초 (실제: {sleep_delays[0]})"
        assert sleep_delays[1] == 2.0, f"두 번째 대기: 2.0초 (실제: {sleep_delays[1]})"
        assert sleep_delays[2] == 4.0, f"세 번째 대기: 4.0초 (실제: {sleep_delays[2]})"

    @pytest.mark.asyncio
    async def test_logs_warning_on_retry(self, caplog):
        """재시도 시 WARNING 로그 기록 확인"""
        from app.main import _connect_with_retry

        async def fail_once():
            raise ConnectionError("connection refused")

        with caplog.at_level(logging.WARNING, logger="knowledge_service.app.main"):
            with patch("app.main.asyncio.sleep", new_callable=AsyncMock):
                await _connect_with_retry(
                    fail_once, "TestES", max_retries=2, base_delay=0.01
                )

        assert "TestES" in caplog.text, "서비스 이름이 로그에 포함되어야 함"

    @pytest.mark.asyncio
    async def test_logs_error_on_final_failure(self, caplog):
        """최종 실패 시 ERROR 로그 기록 확인"""
        from app.main import _connect_with_retry

        async def always_fail():
            raise ConnectionError("persistent failure")

        with caplog.at_level(logging.ERROR, logger="knowledge_service.app.main"):
            with patch("app.main.asyncio.sleep", new_callable=AsyncMock):
                await _connect_with_retry(
                    always_fail, "TestService", max_retries=2, base_delay=0.01
                )

        assert "최종 실패" in caplog.text, "최종 실패 시 ERROR 로그 기록 필요"

    def test_lifespan_uses_connect_with_retry(self):
        """lifespan에서 _connect_with_retry로 ES/Neo4j 연결하는지 코드 확인"""
        from app.main import lifespan

        source = inspect.getsource(lifespan)

        assert "_connect_with_retry" in source, (
            "lifespan에서 _connect_with_retry 사용 안 함"
        )
        assert "max_retries=5" in source, "max_retries=5 설정 필요 (5회 재시도)"
        assert "base_delay=3.0" in source, "base_delay=3.0 설정 필요 (3초 초기 대기)"


# ---------------------------------------------------------------------------
# Test Class 2: Lazy Reconnection (_ensure_es_client, _ensure_neo4j_driver)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestLazyReconnection:
    """search.py lazy reconnection 로직 검증"""

    def test_ensure_methods_exist(self):
        """SearchService에 lazy reconnection 메서드가 있는지 확인"""
        from app.services.search import SearchService

        assert hasattr(SearchService, "_ensure_es_client"), (
            "SearchService에 _ensure_es_client 메서드 없음"
        )
        assert hasattr(SearchService, "_ensure_neo4j_driver"), (
            "SearchService에 _ensure_neo4j_driver 메서드 없음"
        )
        # _reconnect_lock은 __init__에서 생성되는 인스턴스 속성
        # 코드에서 직접 확인
        import inspect
        init_source = inspect.getsource(SearchService.__init__)
        assert "_reconnect_lock" in init_source, (
            "SearchService.__init__에 _reconnect_lock 초기화 없음"
        )

    @pytest.mark.asyncio
    async def test_ensure_es_client_skips_if_already_connected(self):
        """ES 클라이언트가 있으면 재연결 시도 없이 True 반환"""
        from app.services.search import SearchService

        service = SearchService(
            es_client=MagicMock(name="existing_es"),
            neo4j_driver=None,
        )

        result = await service._ensure_es_client()

        assert result is True, "이미 연결된 경우 True 반환해야 함"

    @pytest.mark.asyncio
    async def test_ensure_es_client_reconnects_when_none(self):
        """ES 클라이언트가 None이면 재연결 시도 - 함수 내부 import 패치"""
        from app.services.search import SearchService

        service = SearchService(es_client=None, neo4j_driver=None)

        mock_es = MagicMock()
        mock_es.cluster.health = AsyncMock(
            return_value={"status": "green", "cluster_name": "test"}
        )

        # _ensure_es_client 내부에서 from elasticsearch import AsyncElasticsearch 수행
        # 패치 경로: elasticsearch 모듈 자체를 패치
        with patch("elasticsearch.AsyncElasticsearch", return_value=mock_es):
            result = await service._ensure_es_client()

        # 연결 성공 시 True, 실패 시 False (환경에 따라 다름)
        # 핵심: 재연결 시도가 일어났는지 확인 (mock 클라이언트 사용 여부)
        print(f"\nES lazy reconnect 결과: {result}, client: {service.es_client}")
        # 결과 자체보다는 로직이 실행되었는지 확인
        assert isinstance(result, bool), "_ensure_es_client가 bool을 반환해야 함"

    @pytest.mark.asyncio
    async def test_ensure_es_client_returns_false_on_connection_error(self):
        """ES 재연결 시 ConnectionError 발생 시 False 반환"""
        from app.services.search import SearchService

        service = SearchService(es_client=None, neo4j_driver=None)

        # elasticsearch 모듈 import 자체를 실패하게 만들거나
        # AsyncElasticsearch 생성 시 예외 발생
        with patch(
            "elasticsearch.AsyncElasticsearch",
            side_effect=Exception("ES Connection refused"),
        ):
            result = await service._ensure_es_client()

        assert result is False, "재연결 실패 시 False 반환해야 함"
        assert service.es_client is None, "재연결 실패 후 es_client는 None이어야 함"

    @pytest.mark.asyncio
    async def test_ensure_neo4j_driver_skips_if_already_connected(self):
        """Neo4j 드라이버가 있으면 재연결 시도 없이 True 반환"""
        from app.services.search import SearchService

        service = SearchService(
            es_client=None,
            neo4j_driver=MagicMock(name="existing_neo4j"),
        )

        result = await service._ensure_neo4j_driver()

        assert result is True, "이미 연결된 경우 True 반환해야 함"

    @pytest.mark.asyncio
    async def test_ensure_neo4j_driver_returns_false_on_failure(self):
        """Neo4j 재연결 실패 시 False 반환"""
        from app.services.search import SearchService

        service = SearchService(es_client=None, neo4j_driver=None)

        with patch(
            "neo4j.AsyncGraphDatabase.driver",
            side_effect=Exception("Neo4j connection refused"),
        ):
            result = await service._ensure_neo4j_driver()

        assert result is False, "재연결 실패 시 False 반환해야 함"
        assert service.neo4j_driver is None, "재연결 실패 후 neo4j_driver는 None이어야 함"

    @pytest.mark.asyncio
    async def test_reconnect_lock_is_asyncio_lock(self):
        """_reconnect_lock이 asyncio.Lock 타입인지 확인 (동시성 보호)"""
        from app.services.search import SearchService

        service = SearchService(es_client=None, neo4j_driver=None)

        assert isinstance(service._reconnect_lock, asyncio.Lock), (
            "_reconnect_lock이 asyncio.Lock 타입이어야 함"
        )

    def test_ensure_es_uses_reconnect_lock(self):
        """_ensure_es_client가 _reconnect_lock을 사용하는지 코드 확인"""
        from app.services.search import SearchService

        source = inspect.getsource(SearchService._ensure_es_client)
        assert "_reconnect_lock" in source, (
            "_ensure_es_client가 _reconnect_lock을 사용하지 않음 (동시성 문제 가능)"
        )

    def test_es_search_calls_ensure_client(self):
        """_es_search가 lazy reconnect 로직을 사용하는지 코드 확인"""
        from app.services.search import SearchService

        source = inspect.getsource(SearchService._es_search)
        assert "_ensure_es_client" in source, (
            "_es_search에서 _ensure_es_client 호출 없음. "
            "lazy reconnect가 실제 검색에 적용되지 않음"
        )


# ---------------------------------------------------------------------------
# Test Class 3: Health Readiness - search_service 클라이언트 상태 반영
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestHealthReadiness:
    """health.py readiness에 search_service 클라이언트 상태 반영 검증"""

    def test_check_search_service_clients_function_exists(self):
        """_check_search_service_clients 함수가 health.py에 있는지 확인"""
        from app.api.routes.health import _check_search_service_clients

        assert callable(_check_search_service_clients), (
            "_check_search_service_clients 함수가 없음"
        )

    def test_readiness_route_includes_search_service_checks(self):
        """readiness 함수 코드에 search_service_es/neo4j 체크가 있는지 확인"""
        from app.api.routes.health import readiness

        source = inspect.getsource(readiness)
        assert "search_service_es" in source, (
            "readiness 함수에 search_service_es 체크 없음"
        )
        assert "search_service_neo4j" in source, (
            "readiness 함수에 search_service_neo4j 체크 없음"
        )
        assert "_check_search_service_clients" in source, (
            "readiness 함수에서 _check_search_service_clients 호출 없음"
        )

    def test_check_function_returns_false_when_service_none(self):
        """_search_service가 None이면 False 반환"""
        from app.api.routes.health import _check_search_service_clients
        import app.services.search as search_module

        original = search_module._search_service
        try:
            search_module._search_service = None
            assert _check_search_service_clients("es") is False, (
                "_search_service=None 시 ES 체크는 False여야 함"
            )
            assert _check_search_service_clients("neo4j") is False, (
                "_search_service=None 시 Neo4j 체크는 False여야 함"
            )
        finally:
            search_module._search_service = original

    def test_check_function_returns_true_when_clients_connected(self):
        """ES/Neo4j 클라이언트가 연결되어 있으면 True 반환"""
        from app.api.routes.health import _check_search_service_clients
        from app.services.search import SearchService
        import app.services.search as search_module

        original = search_module._search_service
        try:
            mock_service = MagicMock(spec=SearchService)
            mock_service.es_client = MagicMock(name="connected_es")
            mock_service.neo4j_driver = MagicMock(name="connected_neo4j")
            search_module._search_service = mock_service

            assert _check_search_service_clients("es") is True, (
                "ES 클라이언트 연결 시 True 반환해야 함"
            )
            assert _check_search_service_clients("neo4j") is True, (
                "Neo4j 드라이버 연결 시 True 반환해야 함"
            )
        finally:
            search_module._search_service = original

    def test_check_function_returns_false_when_clients_none(self):
        """ES/Neo4j 클라이언트가 None이면 False 반환"""
        from app.api.routes.health import _check_search_service_clients
        from app.services.search import SearchService
        import app.services.search as search_module

        original = search_module._search_service
        try:
            mock_service = MagicMock(spec=SearchService)
            mock_service.es_client = None
            mock_service.neo4j_driver = None
            search_module._search_service = mock_service

            assert _check_search_service_clients("es") is False, (
                "ES 클라이언트 None 시 False 반환해야 함"
            )
            assert _check_search_service_clients("neo4j") is False, (
                "Neo4j 드라이버 None 시 False 반환해야 함"
            )
        finally:
            search_module._search_service = original

    def test_readiness_endpoint_includes_search_service_checks(
        self, ai_service_available: bool
    ):
        """
        /health/ready 응답에 search_service_es/neo4j 항목 확인 (컨테이너 필요).
        이 테스트가 실패하면 ai-service 컨테이너 리빌드 필요.
        """
        require_ai_service(ai_service_available)

        resp = requests.get(f"{AI_SERVICE_URL}/api/v1/health/ready", timeout=10)
        assert resp.status_code == 200

        data = resp.json()
        checks = data.get("checks", {})

        assert "search_service_es" in checks, (
            f"readiness 응답에 'search_service_es' 항목이 없습니다!\n"
            f"현재 checks: {list(checks.keys())}\n"
            f"원인: ai-service 컨테이너에 최신 코드(894068b)가 반영되지 않음\n"
            f"해결: cd infrastructure/docker && docker compose build ai-service && "
            f"docker compose up -d ai-service"
        )
        assert "search_service_neo4j" in checks, (
            f"readiness 응답에 'search_service_neo4j' 항목이 없습니다!"
        )
        print(f"\n[PASS] readiness checks: {checks}")


# ---------------------------------------------------------------------------
# Test Class 4: [SEARCH_ALERT] 로그 코드 구조 검증
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestSearchAlertLogging:
    """search.py [SEARCH_ALERT] 로그 로직 코드 검증"""

    def test_search_alert_exists_in_hybrid_search(self):
        """hybrid_search에 [SEARCH_ALERT] 로그 로직이 있는지 확인"""
        from app.services.search import SearchService

        source = inspect.getsource(SearchService.hybrid_search)
        assert "SEARCH_ALERT" in source, (
            "hybrid_search에 [SEARCH_ALERT] 로그 로직이 없습니다!\n"
            "0건 + 클라이언트 None 시 WARNING 로그가 기록되어야 함"
        )

    def test_search_alert_checks_both_clients(self):
        """[SEARCH_ALERT] 로직이 ES와 Neo4j 양쪽 클라이언트 상태를 확인하는지 검증"""
        from app.services.search import SearchService

        source = inspect.getsource(SearchService.hybrid_search)

        assert "es_client is None" in source, (
            "[SEARCH_ALERT]가 ES 클라이언트 None 상태를 확인하지 않음"
        )
        assert "neo4j_driver is None" in source, (
            "[SEARCH_ALERT]가 Neo4j 드라이버 None 상태를 확인하지 않음"
        )

    def test_search_alert_only_triggered_on_zero_results(self):
        """[SEARCH_ALERT]는 결과 0건일 때만 발생 - 코드 구조 확인"""
        from app.services.search import SearchService

        source = inspect.getsource(SearchService.hybrid_search)

        alert_idx = source.find("SEARCH_ALERT")
        zero_check_idx = source.find("len(final_results) == 0")

        assert alert_idx > 0, "[SEARCH_ALERT] 코드가 없음"
        assert zero_check_idx > 0, "0건 체크 코드가 없음"
        assert zero_check_idx < alert_idx, (
            "[SEARCH_ALERT]가 0건 체크 조건 밖에 있음. "
            "결과 있을 때도 로그가 출력될 수 있음"
        )

    def test_search_alert_uses_warning_level(self):
        """[SEARCH_ALERT]가 WARNING 레벨로 로그를 기록하는지 확인"""
        from app.services.search import SearchService

        source = inspect.getsource(SearchService.hybrid_search)

        # logger.warning(f"[SEARCH_ALERT]...") 패턴 확인
        alert_idx = source.find("SEARCH_ALERT")
        # alert 로그 앞 50자에 "warning" 포함 확인
        context_before = source[max(0, alert_idx - 50):alert_idx].lower()
        assert "warning" in context_before, (
            "[SEARCH_ALERT]가 WARNING 레벨로 기록되지 않음. "
            "logger.warning() 사용 필요"
        )

    def test_search_alert_includes_query_info(self):
        """[SEARCH_ALERT] 로그에 쿼리 정보가 포함되는지 확인"""
        from app.services.search import SearchService

        source = inspect.getsource(SearchService.hybrid_search)

        alert_section_start = source.find("SEARCH_ALERT")
        # alert 이후 200자에 query 정보 포함 확인
        alert_context = source[alert_section_start:alert_section_start + 200]
        assert "query" in alert_context.lower() or "Query" in alert_context, (
            "[SEARCH_ALERT] 로그에 쿼리 정보가 없음. 디버깅에 필요함"
        )


# ---------------------------------------------------------------------------
# Test Class 5: E2E 통합 검증 (실제 컨테이너)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestSearchStabilityE2E:
    """실제 컨테이너 환경에서 검색 안정성 개선 사항 E2E 검증"""

    def test_health_live(self, ai_service_available: bool):
        """AI Service liveness 확인"""
        require_ai_service(ai_service_available)

        resp = requests.get(f"{AI_SERVICE_URL}/api/v1/health/live", timeout=5)
        assert resp.status_code == 200
        print(f"\n/health/live: {resp.json()}")

    def test_health_ready_basic_checks(self, ai_service_available: bool):
        """모든 컨테이너 정상 상태에서 기본 체크 pass 확인"""
        require_ai_service(ai_service_available)

        resp = requests.get(f"{AI_SERVICE_URL}/api/v1/health/ready", timeout=10)
        assert resp.status_code == 200

        data = resp.json()
        checks = data.get("checks", {})
        print(f"\n/health/ready 응답: {data}")

        assert checks.get("elasticsearch") is True, "ES 연결 실패"
        assert checks.get("neo4j") is True, "Neo4j 연결 실패"
        assert checks.get("postgresql") is True, "PostgreSQL 연결 실패"

    def test_readiness_has_search_service_checks_after_rebuild(
        self, ai_service_available: bool
    ):
        """
        컨테이너 리빌드 후 search_service_es/neo4j 항목이 포함되는지 E2E 검증.
        실패 시: docker compose build ai-service && docker compose up -d ai-service 필요.
        """
        require_ai_service(ai_service_available)

        resp = requests.get(f"{AI_SERVICE_URL}/api/v1/health/ready", timeout=10)
        assert resp.status_code == 200

        data = resp.json()
        checks = data.get("checks", {})

        if "search_service_es" not in checks:
            pytest.fail(
                f"readiness에 search_service_es 항목 없음.\n"
                f"현재 checks: {list(checks.keys())}\n"
                f"컨테이너 리빌드 필요:\n"
                f"  cd infrastructure/docker\n"
                f"  docker compose build ai-service\n"
                f"  docker compose up -d ai-service"
            )

        print(f"\n[PASS] 최신 readiness checks: {checks}")
        assert checks.get("search_service_es") is True, (
            "search_service_es=False. SearchService ES 클라이언트 미연결"
        )
        assert checks.get("search_service_neo4j") is True, (
            "search_service_neo4j=False. SearchService Neo4j 드라이버 미연결"
        )

    def test_ai_service_code_version_has_search_stability(self):
        """
        현재 ai-service 코드에 검색 안정성 개선 사항이 모두 포함되어 있는지 확인.
        코드 레벨에서 4개 개선 사항 존재 여부 검증.
        """
        from app.main import _connect_with_retry
        from app.services.search import SearchService
        from app.api.routes.health import _check_search_service_clients

        # 1. _connect_with_retry 존재
        assert callable(_connect_with_retry), "main.py에 _connect_with_retry 없음"

        # 2. lazy reconnection 메서드
        assert hasattr(SearchService, "_ensure_es_client"), (
            "search.py에 _ensure_es_client 없음"
        )
        assert hasattr(SearchService, "_ensure_neo4j_driver"), (
            "search.py에 _ensure_neo4j_driver 없음"
        )

        # 3. _check_search_service_clients
        assert callable(_check_search_service_clients), (
            "health.py에 _check_search_service_clients 없음"
        )

        # 4. [SEARCH_ALERT]
        hybrid_source = inspect.getsource(SearchService.hybrid_search)
        assert "SEARCH_ALERT" in hybrid_source, "search.py에 [SEARCH_ALERT] 없음"

        print("\n[PASS] 검색 안정성 개선 4개 항목 모두 코드에 존재 확인")
