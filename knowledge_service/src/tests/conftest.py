"""
pytest 공통 설정 및 Fixture

테스트 전반에서 사용되는 공통 fixture 정의
"""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.config import settings


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
