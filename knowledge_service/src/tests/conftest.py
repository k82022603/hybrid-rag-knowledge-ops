"""
pytest 공통 설정 및 Fixture

테스트 전반에서 사용되는 공통 fixture 정의
"""

from datetime import datetime, timedelta
from typing import Any, Dict
from unittest.mock import patch

import jwt
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.config import settings


# =============================================================================
# JWT Token Fixtures
# =============================================================================


def get_test_jwt_secret() -> str:
    """
    테스트용 JWT Secret 키 반환

    settings.jwt_secret_key가 비어있으면 테스트용 기본값 사용
    """
    if settings.jwt_secret_key:
        return settings.jwt_secret_key
    # 테스트용 기본 시크릿 (32자 이상)
    return "test-jwt-secret-key-for-unit-testing-32chars"


# 테스트 사용자 정보 (USERS 딕셔너리에 추가될 데이터)
TEST_USER_DATA = {
    "id": "user-test-001",
    "email": "test@example.com",
    "password_hash": "",  # 테스트에서 로그인 필요 없음 (토큰 직접 생성)
    "name": "테스트 사용자",
    "role": "user",
    "created_at": "2026-01-01T00:00:00Z",
}


@pytest.fixture(scope="session", autouse=True)
def setup_test_users():
    """
    테스트 세션 시작 시 USERS 딕셔너리에 테스트 사용자 추가

    autouse=True로 모든 테스트에서 자동으로 실행됩니다.
    """
    from app.api.routes.auth import USERS

    # 테스트 사용자 추가
    USERS["test@example.com"] = TEST_USER_DATA.copy()

    yield

    # 테스트 후 정리 (선택)
    if "test@example.com" in USERS:
        del USERS["test@example.com"]


@pytest.fixture(scope="session")
def jwt_secret() -> str:
    """JWT Secret Key"""
    return get_test_jwt_secret()


@pytest.fixture(scope="session")
def jwt_algorithm() -> str:
    """JWT Algorithm"""
    return settings.jwt_algorithm


@pytest.fixture(scope="function")
def test_user_payload() -> Dict[str, Any]:
    """테스트 사용자 JWT 페이로드"""
    return {
        "sub": "user-test-001",
        "email": "test@example.com",
        "role": "user",
        "type": "access",
    }


@pytest.fixture(scope="function")
def valid_access_token(
    jwt_secret: str, jwt_algorithm: str, test_user_payload: Dict[str, Any]
) -> str:
    """유효한 JWT 액세스 토큰 생성"""
    payload = {
        **test_user_payload,
        "exp": datetime.utcnow() + timedelta(minutes=30),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, jwt_secret, algorithm=jwt_algorithm)


@pytest.fixture(scope="function")
def expired_access_token(
    jwt_secret: str, jwt_algorithm: str, test_user_payload: Dict[str, Any]
) -> str:
    """만료된 JWT 액세스 토큰 생성"""
    payload = {
        **test_user_payload,
        "exp": datetime.utcnow() - timedelta(hours=1),
        "iat": datetime.utcnow() - timedelta(hours=2),
    }
    return jwt.encode(payload, jwt_secret, algorithm=jwt_algorithm)


@pytest.fixture(scope="function")
def auth_headers(valid_access_token: str) -> Dict[str, str]:
    """인증 헤더 (Bearer Token)"""
    return {"Authorization": f"Bearer {valid_access_token}"}


# =============================================================================
# HTTP Client Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def anyio_backend():
    """비동기 백엔드 설정"""
    return "asyncio"


@pytest.fixture(scope="function")
def client() -> TestClient:
    """동기 테스트 클라이언트"""
    return TestClient(app)


@pytest.fixture(scope="function")
async def async_client() -> AsyncClient:
    """비동기 테스트 클라이언트"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="session")
def api_prefix() -> str:
    """API 프리픽스"""
    return settings.api_v1_prefix


# =============================================================================
# Sample Data Fixtures
# =============================================================================


@pytest.fixture
def sample_text() -> str:
    """테스트용 샘플 텍스트"""
    return """
    Hybrid RAG 플랫폼은 Vector Search와 Graph Search를 결합한
    지능형 검색 시스템입니다. 이 프로젝트는 Neo4j 그래프 데이터베이스와
    Elasticsearch 벡터 검색을 활용합니다.

    주요 기술:
    - LangGraph: AI 워크플로우 오케스트레이션
    - DeepSeek: LLM 모델 (95% 비용 절감)
    - BGE-M3: 다국어 임베딩
    """


@pytest.fixture
def sample_query() -> str:
    """테스트용 샘플 질의"""
    return "Hybrid RAG 플랫폼의 주요 기술은 무엇인가요?"


@pytest.fixture
def fixtures_dir():
    """테스트 fixture 디렉토리 경로"""
    from pathlib import Path

    return Path(__file__).parent / "fixtures"


@pytest.fixture
def documents_dir(fixtures_dir):
    """테스트 문서 fixture 디렉토리 경로"""
    return fixtures_dir / "documents"


@pytest.fixture
def sample_markdown_path(documents_dir):
    """샘플 Markdown 파일 경로"""
    return documents_dir / "sample_markdown.md"


@pytest.fixture
def sample_text_path(documents_dir):
    """샘플 텍스트 파일 경로"""
    return documents_dir / "sample_text.txt"


@pytest.fixture
def sample_html_path(documents_dir):
    """샘플 HTML 파일 경로"""
    return documents_dir / "sample_html.html"
