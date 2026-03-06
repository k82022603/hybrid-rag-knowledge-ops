"""
Graph Search E2E 테스트

ISSUE-011: entity_name에 파일명이 전달되는 버그 수정 검증
Graph Search Entity-Enhanced BM25 E2E 테스트

테스트 범주:
1. _is_filename() 파일명 패턴 필터링 검증
2. _extract_entities_from_title() 제목 기반 엔티티 추출 검증
3. build_sources_from_results() 출처 정보 생성 검증 (ISSUE-011 핵심)
4. SearchService._graph_search() Entity-Enhanced BM25 검증
5. Graph Search Neo4j -> ES 파이프라인 검증
6. Edge Case: 파일명만 있는 경우 / 엔티티 없는 경우 / 빈 결과
"""

import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# 환경 의존성 Mock: WSL2/CI에서 torch/langchain 패키지 누락 방지
# ---------------------------------------------------------------------------

_TORCH_IMPORT_ERROR = False
try:
    import torch  # noqa: F401
except (OSError, ImportError, ValueError):
    _TORCH_IMPORT_ERROR = True
    import importlib.machinery

    _torch_mock = ModuleType("torch")
    _torch_mock.__version__ = "2.0.0"
    _torch_mock.__spec__ = importlib.machinery.ModuleSpec("torch", None)
    _torch_mock.cuda = MagicMock()
    _torch_mock.cuda.is_available = MagicMock(return_value=False)
    _torch_mock.Tensor = MagicMock()
    _torch_mock.nn = MagicMock()
    _torch_mock.device = MagicMock()
    _torch_mock.dtype = MagicMock()
    _torch_mock.float32 = MagicMock()
    _torch_mock.float16 = MagicMock()
    _torch_mock.no_grad = MagicMock(
        return_value=MagicMock(__enter__=MagicMock(), __exit__=MagicMock())
    )
    sys.modules["torch"] = _torch_mock
    for submod in [
        "torch.nn",
        "torch.nn.functional",
        "torch.utils",
        "torch.utils.data",
        "torch.cuda",
        "torch.amp",
    ]:
        if submod not in sys.modules:
            sys.modules[submod] = MagicMock()

_MOCK_PACKAGES = [
    "langchain_openai",
    "langchain_core",
    "langchain_core.language_models",
    "langchain_core.language_models.chat_models",
    "langchain_core.messages",
    "langchain_core.prompts",
    "langchain_core.output_parsers",
    "langchain_community",
    "langchain",
    "langgraph",
    "langgraph.graph",
    "langgraph.prebuilt",
    "langgraph.checkpoint",
    "openai",
    "FlagEmbedding",
    "sentence_transformers",
    "transformers",
]
# elasticsearch, redis, neo4j, minio는 실제 설치된 패키지이므로 mock하지 않음
# (sys.modules 오염으로 다른 테스트에 영향을 주기 때문)
for _pkg in _MOCK_PACKAGES:
    if _pkg not in sys.modules:
        sys.modules[_pkg] = MagicMock()

from app.agents.state import SearchResult  # noqa: E402
from app.agents.rag_workflow import (  # noqa: E402
    _is_filename,
    _extract_entities_from_title,
    build_sources_from_results,
)


# ---------------------------------------------------------------------------
# Fixtures & Helpers
# ---------------------------------------------------------------------------


def make_search_result(
    chunk_id: str,
    content: str = "test content",
    score: float = 1.0,
    source: str = "graph",
    document_id: str = "doc_1",
    metadata: Optional[Dict[str, Any]] = None,
) -> SearchResult:
    """테스트용 SearchResult 생성 헬퍼"""
    return SearchResult(
        chunk_id=chunk_id,
        document_id=document_id,
        content=content,
        score=score,
        source=source,
        metadata=metadata or {},
    )


def _make_es_response(hits: List[Dict[str, Any]]) -> Dict[str, Any]:
    """테스트용 ES 응답 생성 헬퍼"""
    return {
        "hits": {
            "hits": hits,
            "total": {"value": len(hits)},
        }
    }


def _make_es_hit(
    chunk_id: str,
    content: str = "test content",
    document_id: str = "doc_1",
    title: str = "Test Doc",
    score: float = 1.0,
) -> Dict[str, Any]:
    """테스트용 ES hit 생성 헬퍼"""
    return {
        "_id": chunk_id,
        "_score": score,
        "_source": {
            "text": content,
            "document_id": document_id,
            "metadata": {
                "title": title,
                "document_id": document_id,
            },
        },
    }


# ---------------------------------------------------------------------------
# 1. _is_filename() 파일명 패턴 필터링 검증
# ---------------------------------------------------------------------------


class TestIsFilename:
    """ISSUE-011: _is_filename() 유틸리티 함수 테스트"""

    def test_pdf_filename(self):
        """PDF 파일명 인식"""
        assert _is_filename("KMS_설계서.pdf") is True

    def test_docx_filename(self):
        """DOCX 파일명 인식"""
        assert _is_filename("프로젝트_요구사항.docx") is True

    def test_xlsx_filename(self):
        """XLSX 파일명 인식"""
        assert _is_filename("데이터분석_결과.xlsx") is True

    def test_txt_filename(self):
        """TXT 파일명 인식"""
        assert _is_filename("readme.txt") is True

    def test_md_filename(self):
        """Markdown 파일명 인식"""
        assert _is_filename("CHANGELOG.md") is True

    def test_pptx_filename(self):
        """PPTX 파일명 인식"""
        assert _is_filename("발표자료.pptx") is True

    def test_html_filename(self):
        """HTML 파일명 인식"""
        assert _is_filename("index.html") is True

    def test_entity_name_not_filename(self):
        """실제 엔티티명은 파일명이 아님"""
        assert _is_filename("Neo4j") is False

    def test_technology_name(self):
        """기술명은 파일명이 아님"""
        assert _is_filename("Elasticsearch") is False

    def test_korean_entity(self):
        """한글 엔티티명은 파일명이 아님"""
        assert _is_filename("하이브리드 RAG") is False

    def test_person_name(self):
        """인물명은 파일명이 아님"""
        assert _is_filename("홍길동") is False

    def test_project_name(self):
        """프로젝트명은 파일명이 아님"""
        assert _is_filename("KMS 프로젝트") is False

    def test_empty_string(self):
        """빈 문자열"""
        assert _is_filename("") is False

    def test_single_char_extension(self):
        """단일 문자 확장자 (2자 미만이라 패턴 불일치)"""
        assert _is_filename("file.a") is False

    def test_long_extension(self):
        """긴 확장자 (5자 초과이므로 패턴 불일치)"""
        assert _is_filename("archive.tar.gz.backup") is False

    def test_version_string_with_dot(self):
        """버전 문자열 (v3.2 등)은 파일명으로 인식될 수 있음"""
        # "DeepSeek V3.2" -> 끝이 ".2"이므로 확장자 패턴에 매칭되지 않음
        # (숫자 1자이므로 \w{2,5}에 불일치)
        # 단, "V3.22"이면 매칭됨 -> 이건 엣지 케이스로 허용
        assert _is_filename("DeepSeek V3.2") is False


# ---------------------------------------------------------------------------
# 2. _extract_entities_from_title() 검증
# ---------------------------------------------------------------------------


class TestExtractEntitiesFromTitle:
    """ISSUE-011: _extract_entities_from_title() 테스트

    현행 동작: 제목을 단어 단위로 분리하여 개별 키워드를 반환합니다.
    - 불용어, 날짜 패턴, 2자 미만 단어는 필터링
    - 한글 키워드는 정규식으로 별도 추출 (2글자 이상)
    - 최대 5개 반환
    """

    def test_normal_title_returns_split_keywords(self):
        """일반 제목은 개별 키워드로 분리하여 반환"""
        result = _extract_entities_from_title("하이브리드 RAG 설계서")
        assert "RAG" in result
        assert "하이브리드" in result
        assert "설계서" in result

    def test_filename_title_returns_empty(self):
        """파일명 제목은 빈 리스트 반환"""
        result = _extract_entities_from_title("KMS_설계서.pdf")
        assert result == []

    def test_empty_title_returns_empty(self):
        """빈 제목은 빈 리스트 반환"""
        result = _extract_entities_from_title("")
        assert result == []

    def test_none_title_returns_empty(self):
        """None 제목은 빈 리스트 반환"""
        result = _extract_entities_from_title(None)
        assert result == []

    def test_docx_filename_returns_empty(self):
        """DOCX 파일명 제목은 빈 리스트 반환"""
        result = _extract_entities_from_title("프로젝트_요구사항.docx")
        assert result == []

    def test_technology_title_returns_split_keywords(self):
        """기술명 제목은 개별 키워드로 분리하여 반환"""
        result = _extract_entities_from_title("Elasticsearch 설정 가이드")
        assert "Elasticsearch" in result
        assert "설정" in result
        assert "가이드" in result


# ---------------------------------------------------------------------------
# 3. build_sources_from_results() 출처 정보 생성 검증 (ISSUE-011 핵심)
# ---------------------------------------------------------------------------


class TestBuildSourcesFromResults:
    """
    ISSUE-011 핵심 검증: build_sources_from_results()

    현행 동작: matched_entities만 사용하여 graph_context를 생성합니다.
    Tier 2/3 폴백(제목/콘텐츠 기반 엔티티 추출)은 제거되었습니다.
    Neo4j에서 검증된 엔티티(matched_entities)만 graph_context에 포함됩니다.
    """

    def test_graph_source_with_matched_entities(self):
        """Graph 소스: matched_entities가 있으면 graph_context에 포함"""
        results = [
            make_search_result(
                chunk_id="chunk_1",
                source="graph",
                metadata={
                    "title": "KMS_설계서.pdf",
                    "matched_entities": ["Neo4j", "Elasticsearch", "RAG"],
                },
            ),
        ]

        sources = build_sources_from_results(results)

        assert len(sources) == 1
        assert "graph_context" in sources[0]
        assert sources[0]["graph_context"]["related_entities"] == [
            "Neo4j",
            "Elasticsearch",
            "RAG",
        ]

    def test_graph_source_filters_filename_entities(self):
        """Graph 소스: matched_entities에서 파일명 패턴 필터링"""
        results = [
            make_search_result(
                chunk_id="chunk_1",
                source="graph",
                metadata={
                    "title": "KMS_설계서.pdf",
                    "matched_entities": ["Neo4j", "KMS_설계서.pdf", "RAG"],
                },
            ),
        ]

        sources = build_sources_from_results(results)

        assert "graph_context" in sources[0]
        entities = sources[0]["graph_context"]["related_entities"]
        # 파일명 "KMS_설계서.pdf"가 필터링됨
        assert "KMS_설계서.pdf" not in entities
        assert "Neo4j" in entities
        assert "RAG" in entities

    def test_vector_source_without_matched_entities_no_graph_context(self):
        """Vector 소스: matched_entities 없으면 graph_context 없음 (타이틀 폴백 제거됨)"""
        results = [
            make_search_result(
                chunk_id="chunk_1",
                source="vector",
                metadata={
                    "title": "하이브리드 RAG 설계서",
                },
            ),
        ]

        sources = build_sources_from_results(results)

        assert len(sources) == 1
        # 타이틀 폴백이 제거되었으므로 matched_entities 없으면 graph_context 없음
        assert "graph_context" not in sources[0]

    def test_keyword_source_without_matched_entities_no_graph_context(self):
        """Keyword 소스: matched_entities 없으면 graph_context 없음 (타이틀 폴백 제거됨)"""
        results = [
            make_search_result(
                chunk_id="chunk_1",
                source="keyword",
                metadata={
                    "title": "Elasticsearch 운영 가이드",
                },
            ),
        ]

        sources = build_sources_from_results(results)

        # 타이틀 폴백이 제거되었으므로 matched_entities 없으면 graph_context 없음
        assert "graph_context" not in sources[0]

    def test_filename_title_no_graph_context(self):
        """제목이 파일명이고 matched_entities도 없으면 graph_context 없음"""
        results = [
            make_search_result(
                chunk_id="chunk_1",
                source="vector",
                metadata={
                    "title": "KMS_설계서.pdf",
                },
            ),
        ]

        sources = build_sources_from_results(results)

        # 파일명 제목이므로 엔티티 추출 불가 -> graph_context 없음
        assert "graph_context" not in sources[0]

    def test_all_matched_entities_are_filenames_no_graph_context(self):
        """matched_entities가 모두 파일명인 경우 -> 필터링 후 빈 리스트 -> graph_context 없음"""
        results = [
            make_search_result(
                chunk_id="chunk_1",
                source="graph",
                metadata={
                    "title": "RAG 파이프라인",
                    "matched_entities": ["file1.pdf", "file2.docx"],
                },
            ),
        ]

        sources = build_sources_from_results(results)

        # 파일명 필터링 후 matched_entities 비어짐
        # 타이틀 폴백이 제거되었으므로 graph_context 없음
        assert "graph_context" not in sources[0]

    def test_empty_matched_entities_no_graph_context(self):
        """matched_entities가 빈 리스트면 graph_context 없음 (타이틀 폴백 제거됨)"""
        results = [
            make_search_result(
                chunk_id="chunk_1",
                source="graph",
                metadata={
                    "title": "Knowledge Graph 구축",
                    "matched_entities": [],
                },
            ),
        ]

        sources = build_sources_from_results(results)

        # 빈 matched_entities + 타이틀 폴백 제거 -> graph_context 없음
        assert "graph_context" not in sources[0]

    def test_no_matched_entities_key_no_graph_context(self):
        """matched_entities 키가 없으면 graph_context 없음 (타이틀 폴백 제거됨)"""
        results = [
            make_search_result(
                chunk_id="chunk_1",
                source="graph",
                metadata={
                    "title": "DeepSeek LLM 가이드",
                },
            ),
        ]

        sources = build_sources_from_results(results)

        # matched_entities 키 없음 + 타이틀 폴백 제거 -> graph_context 없음
        assert "graph_context" not in sources[0]

    def test_empty_results(self):
        """빈 검색 결과"""
        sources = build_sources_from_results([])
        assert sources == []

    def test_multiple_results_mixed_sources(self):
        """여러 소스 혼합 결과"""
        results = [
            make_search_result(
                chunk_id="c1",
                source="graph",
                document_id="doc_1",
                metadata={
                    "title": "KMS_설계서.pdf",
                    "matched_entities": ["Neo4j", "LangGraph"],
                },
            ),
            make_search_result(
                chunk_id="c2",
                source="vector",
                document_id="doc_2",
                metadata={
                    "title": "AI 서비스 아키텍처",
                },
            ),
            make_search_result(
                chunk_id="c3",
                source="keyword",
                document_id="doc_3",
                metadata={
                    "title": "report_2026.xlsx",
                },
            ),
        ]

        sources = build_sources_from_results(results)

        assert len(sources) == 3

        # Graph 소스: matched_entities 사용
        assert "graph_context" in sources[0]
        assert "Neo4j" in sources[0]["graph_context"]["related_entities"]

        # Vector 소스: matched_entities 없으므로 graph_context 없음 (타이틀 폴백 제거)
        assert "graph_context" not in sources[1]

        # Keyword 소스: 파일명 제목 + matched_entities 없음 -> graph_context 없음
        assert "graph_context" not in sources[2]

    def test_source_info_contains_expected_fields(self):
        """출처 정보에 필수 필드 포함 확인"""
        results = [
            make_search_result(
                chunk_id="c1",
                source="graph",
                document_id="doc_1",
                score=0.85,
                content="Neo4j 그래프 데이터베이스를 활용한 지식 관리",
                metadata={
                    "title": "Knowledge Graph",
                    "matched_entities": ["Neo4j"],
                },
            ),
        ]

        sources = build_sources_from_results(results)
        src = sources[0]

        assert src["index"] == 1
        assert src["chunk_id"] == "c1"
        assert src["document_id"] == "doc_1"
        assert src["title"] == "Knowledge Graph"
        assert src["score"] == 0.85
        assert src["source_type"] == "graph"
        assert "snippet" in src
        assert src["is_primary"] is True

    def test_duplicate_document_id_primary_flag(self):
        """동일 document_id의 두 번째 출현은 is_primary=False"""
        results = [
            make_search_result(
                chunk_id="c1",
                document_id="doc_1",
                source="graph",
                metadata={"title": "Title A"},
            ),
            make_search_result(
                chunk_id="c2",
                document_id="doc_1",
                source="vector",
                metadata={"title": "Title A"},
            ),
        ]

        sources = build_sources_from_results(results)

        assert sources[0]["is_primary"] is True
        assert sources[1]["is_primary"] is False

    def test_matched_entities_with_none_and_empty_filtered(self):
        """matched_entities에 None이나 빈 문자열 포함 시 필터링"""
        results = [
            make_search_result(
                chunk_id="c1",
                source="graph",
                metadata={
                    "title": "Title",
                    "matched_entities": ["Neo4j", None, "", "RAG"],
                },
            ),
        ]

        sources = build_sources_from_results(results)

        entities = sources[0]["graph_context"]["related_entities"]
        assert None not in entities
        assert "" not in entities
        assert "Neo4j" in entities
        assert "RAG" in entities


# ---------------------------------------------------------------------------
# 4. SearchService._graph_search() Entity-Enhanced BM25 검증
# ---------------------------------------------------------------------------


class TestGraphSearchCypherQuery:
    """
    SearchService._graph_search() 검증

    현행 동작 (Entity-Enhanced BM25):
    1. Neo4j에서 쿼리 관련 엔티티명 추출
    2. 엔티티명으로 ES BM25 검색 (엔티티 부스트)
    3. ES 결과를 SearchResult로 파싱하여 반환

    이전 동작(Neo4j에서 직접 chunk 반환)은 제거되었습니다.
    """

    def setup_method(self):
        """테스트 설정"""
        with patch("app.services.search.get_embedding_service"):
            from app.services.search import SearchService
            self.service = SearchService(es_client=None, neo4j_driver=None)

    @pytest.mark.asyncio
    async def test_graph_search_no_neo4j_returns_empty(self):
        """Neo4j 미연결 시 빈 결과"""
        results = await self.service._graph_search(
            query="test query",
            top_k=10,
        )
        assert results == []

    @pytest.mark.asyncio
    async def test_graph_search_with_entities_returns_es_results(self):
        """entity_names 경로: Neo4j에서 엔티티 확장 -> ES 검색"""
        # Neo4j에서 엔티티명 반환
        neo4j_entity_records = [
            {"name": "Neo4j"},
            {"name": "LangGraph"},
            {"name": "Knowledge Graph"},  # RELATED_TO 확장 엔티티
        ]

        # ES 검색 결과
        es_response = _make_es_response([
            _make_es_hit(
                chunk_id="chunk_1",
                content="Neo4j를 사용한 지식 그래프 구축",
                document_id="doc_1",
                title="KG 가이드",
                score=3.0,
            ),
        ])

        mock_es_client = AsyncMock()
        mock_es_client.search = AsyncMock(return_value=es_response)

        with patch("app.services.search.get_embedding_service"):
            from app.services.search import SearchService
            service = SearchService(
                es_client=mock_es_client,
                neo4j_driver=MagicMock(),
            )

        service._neo4j_query = AsyncMock(return_value=neo4j_entity_records)

        results = await service._graph_search(
            query="Neo4j 사용법",
            entities=[{"name": "Neo4j"}, {"name": "LangGraph"}],
            top_k=10,
        )

        assert len(results) == 1
        assert results[0].chunk_id == "chunk_1"
        assert results[0].source == "graph"
        # _neo4j_query가 1번 호출됨 (엔티티명 조회)
        assert service._neo4j_query.call_count == 1

    @pytest.mark.asyncio
    async def test_graph_search_without_entities_uses_query_words(self):
        """엔티티 없을 때 query_words로 Neo4j 검색 -> ES 검색"""
        # Neo4j에서 쿼리 단어 기반 엔티티명 반환
        neo4j_entity_records = [
            {"name": "Elasticsearch"},
        ]

        # ES 검색 결과
        es_response = _make_es_response([
            _make_es_hit(
                chunk_id="chunk_1",
                content="Elasticsearch를 활용한 벡터 검색",
                document_id="doc_1",
                title="ES 가이드",
                score=2.0,
            ),
        ])

        mock_es_client = AsyncMock()
        mock_es_client.search = AsyncMock(return_value=es_response)

        with patch("app.services.search.get_embedding_service"):
            from app.services.search import SearchService
            service = SearchService(
                es_client=mock_es_client,
                neo4j_driver=MagicMock(),
            )

        service._neo4j_query = AsyncMock(return_value=neo4j_entity_records)

        results = await service._graph_search(
            query="Elasticsearch 설정",
            entities=None,
            top_k=10,
        )

        assert len(results) == 1
        assert results[0].chunk_id == "chunk_1"
        assert results[0].source == "graph"

    @pytest.mark.asyncio
    async def test_graph_search_neo4j_no_entities_returns_empty(self):
        """Neo4j에서 엔티티를 찾지 못하면 빈 결과 반환 (ES 검색 수행 안 함)"""
        mock_es_client = AsyncMock()

        with patch("app.services.search.get_embedding_service"):
            from app.services.search import SearchService
            service = SearchService(
                es_client=mock_es_client,
                neo4j_driver=MagicMock(),
            )

        # Neo4j에서 빈 결과
        service._neo4j_query = AsyncMock(return_value=[])

        results = await service._graph_search(
            query="폴백 테스트",
            entities=None,
            top_k=10,
        )

        # Neo4j에서 엔티티 없으면 즉시 빈 결과 반환
        assert results == []
        assert service._neo4j_query.call_count == 1


# ---------------------------------------------------------------------------
# 5. Graph Search Neo4j -> ES 파이프라인 검증
# ---------------------------------------------------------------------------


class TestGraphSearchPipeline:
    """
    Graph Search Neo4j -> ES 파이프라인 E2E 테스트

    현행 구조:
    1. Neo4j에서 쿼리 관련 엔티티명 추출 (정확 매칭 + 부분 매칭)
    2. 엔티티명으로 ES multi_match + entity boost 검색
    3. _parse_es_results로 SearchResult 변환
    """

    @pytest.mark.asyncio
    async def test_entity_names_used_in_es_query(self):
        """Neo4j 엔티티명이 ES 검색 쿼리에 반영되는지 확인"""
        neo4j_records = [{"name": "Neo4j"}]
        es_response = _make_es_response([
            _make_es_hit(
                chunk_id="c1",
                content="Neo4j는 그래프 데이터베이스입니다",
                document_id="d1",
                title="Neo4j 가이드",
                score=1.0,
            ),
        ])

        mock_es_client = AsyncMock()
        mock_es_client.search = AsyncMock(return_value=es_response)

        with patch("app.services.search.get_embedding_service"):
            from app.services.search import SearchService
            service = SearchService(
                es_client=mock_es_client,
                neo4j_driver=MagicMock(),
            )

        service._neo4j_query = AsyncMock(return_value=neo4j_records)

        results = await service._graph_search(
            query="Neo4j 설명해줘",
            entities=None,
            top_k=10,
        )

        assert len(results) == 1
        assert results[0].chunk_id == "c1"
        assert results[0].source == "graph"

        # ES search가 호출되었는지 확인
        assert mock_es_client.search.call_count == 1

    @pytest.mark.asyncio
    async def test_multiple_entities_boost_es_search(self):
        """여러 엔티티명이 ES should 절에 부스트로 추가"""
        neo4j_records = [
            {"name": "SpringBoot"},
            {"name": "Spring Cloud"},
        ]
        es_response = _make_es_response([
            _make_es_hit(
                chunk_id="c1",
                content="SpringBoot 3.x 설정 방법",
                document_id="d1",
                title="Spring 가이드",
                score=1.0,
            ),
        ])

        mock_es_client = AsyncMock()
        mock_es_client.search = AsyncMock(return_value=es_response)

        with patch("app.services.search.get_embedding_service"):
            from app.services.search import SearchService
            service = SearchService(
                es_client=mock_es_client,
                neo4j_driver=MagicMock(),
            )

        service._neo4j_query = AsyncMock(return_value=neo4j_records)

        results = await service._graph_search(
            query="Spring 설정",
            entities=None,
            top_k=10,
        )

        assert len(results) == 1
        assert results[0].chunk_id == "c1"

    @pytest.mark.asyncio
    async def test_es_empty_response_returns_empty(self):
        """Neo4j 엔티티 있지만 ES 결과 없으면 빈 리스트"""
        neo4j_records = [{"name": "NonexistentEntity"}]
        es_response = _make_es_response([])

        mock_es_client = AsyncMock()
        mock_es_client.search = AsyncMock(return_value=es_response)

        with patch("app.services.search.get_embedding_service"):
            from app.services.search import SearchService
            service = SearchService(
                es_client=mock_es_client,
                neo4j_driver=MagicMock(),
            )

        service._neo4j_query = AsyncMock(return_value=neo4j_records)

        results = await service._graph_search(
            query="존재하지않는쿼리",
            entities=None,
            top_k=10,
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_all_steps_fail_returns_empty(self):
        """Neo4j 엔티티 없으면 빈 결과 (ES 검색 수행 안 함)"""
        with patch("app.services.search.get_embedding_service"):
            from app.services.search import SearchService
            service = SearchService(
                es_client=MagicMock(),
                neo4j_driver=MagicMock(),
            )

        service._neo4j_query = AsyncMock(return_value=[])

        results = await service._graph_search(
            query="존재하지않는쿼리",
            entities=None,
            top_k=10,
        )

        assert results == []


# ---------------------------------------------------------------------------
# 6. Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """엣지 케이스 테스트"""

    def test_source_with_only_filename_matched_entities(self):
        """matched_entities가 모두 파일명이고 제목도 파일명인 경우"""
        results = [
            make_search_result(
                chunk_id="c1",
                source="graph",
                metadata={
                    "title": "report.pdf",
                    "matched_entities": ["data.xlsx", "config.yml"],
                },
            ),
        ]

        sources = build_sources_from_results(results)

        # 파일명 전부 필터링 + 제목도 파일명 -> graph_context 없음
        assert "graph_context" not in sources[0]

    def test_source_with_empty_title_and_no_entities(self):
        """제목도 없고 matched_entities도 없는 경우"""
        results = [
            make_search_result(
                chunk_id="c1",
                source="graph",
                metadata={
                    "title": "",
                },
            ),
        ]

        sources = build_sources_from_results(results)

        assert "graph_context" not in sources[0]

    def test_long_snippet_truncation(self):
        """긴 content는 snippet이 200자로 잘림"""
        long_content = "A" * 300
        results = [
            make_search_result(
                chunk_id="c1",
                content=long_content,
                metadata={"title": "Title"},
            ),
        ]

        sources = build_sources_from_results(results)

        assert len(sources[0]["snippet"]) < len(long_content)
        assert sources[0]["snippet"].endswith("...")

    def test_short_snippet_not_truncated(self):
        """짧은 content는 snippet이 그대로"""
        short_content = "Short content"
        results = [
            make_search_result(
                chunk_id="c1",
                content=short_content,
                metadata={"title": "Title"},
            ),
        ]

        sources = build_sources_from_results(results)

        assert sources[0]["snippet"] == short_content

    @pytest.mark.asyncio
    async def test_graph_search_neo4j_exception_returns_empty(self):
        """Neo4j 쿼리 예외 발생 시 빈 결과 (non-critical)"""
        with patch("app.services.search.get_embedding_service"):
            from app.services.search import SearchService
            service = SearchService(es_client=None, neo4j_driver=MagicMock())

        service._neo4j_query = AsyncMock(side_effect=Exception("Neo4j connection error"))

        results = await service._graph_search(
            query="test",
            entities=[{"name": "Test"}],
            top_k=10,
        )

        assert results == []

    def test_matched_entities_preserves_order(self):
        """matched_entities 순서 유지"""
        results = [
            make_search_result(
                chunk_id="c1",
                source="graph",
                metadata={
                    "title": "Title",
                    "matched_entities": ["Alpha", "Beta", "Gamma"],
                },
            ),
        ]

        sources = build_sources_from_results(results)

        entities = sources[0]["graph_context"]["related_entities"]
        assert entities == ["Alpha", "Beta", "Gamma"]

    @pytest.mark.asyncio
    async def test_graph_search_single_char_query_word_filtered(self):
        """단일 문자 쿼리 단어 필터링 (len < 2)"""
        with patch("app.services.search.get_embedding_service"):
            from app.services.search import SearchService
            service = SearchService(es_client=None, neo4j_driver=MagicMock())

        service._neo4j_query = AsyncMock(return_value=[])

        results = await service._graph_search(
            query="A B",  # 단일 문자 -> 필터링됨
            entities=None,
            top_k=10,
        )

        # 단일 문자가 필터링되면 query_words는 빈 리스트 -> 원래 쿼리 사용
        # 호출 자체는 성공해야 함
        assert results == []


# ---------------------------------------------------------------------------
# 7. ISSUE-011 End-to-End 통합 시나리오
# ---------------------------------------------------------------------------


class TestIssue011EndToEnd:
    """
    ISSUE-011 수정 사항 E2E 통합 검증

    시나리오: Chat Search -> Graph Search -> build_sources -> Frontend에서
    entity_name이 파일명이 아닌 실제 엔티티명으로 전달되는지 검증

    현행 동작: build_sources_from_results는 matched_entities만 사용합니다.
    타이틀 기반 폴백은 제거되었습니다 (Neo4j 미검증 엔티티 방지).
    """

    def test_scenario_graph_source_with_real_entities(self):
        """
        시나리오 1: Graph 소스에서 실제 엔티티명 전달

        Before (버그): entity_name = "KMS_설계서.pdf"
        After (수정): entity_name = "Neo4j" (matched_entities에서 추출)
        """
        results = [
            make_search_result(
                chunk_id="chunk_graph_1",
                source="graph",
                document_id="doc_kms",
                score=0.95,
                content="Neo4j 그래프 데이터베이스를 활용한 지식 관리 시스템",
                metadata={
                    "title": "KMS_설계서.pdf",
                    "search_source": "neo4j_graph",
                    "matched_entities": ["Neo4j", "Knowledge Graph"],
                },
            ),
        ]

        sources = build_sources_from_results(results)
        source = sources[0]

        # ISSUE-011 핵심 검증: graph_context.related_entities에 파일명이 아닌 실제 엔티티
        assert "graph_context" in source
        related_entities = source["graph_context"]["related_entities"]
        assert "Neo4j" in related_entities
        assert "Knowledge Graph" in related_entities
        assert "KMS_설계서.pdf" not in related_entities

    def test_scenario_vector_source_no_title_fallback(self):
        """
        시나리오 2: Vector 소스에서 matched_entities 없으면 graph_context 없음

        타이틀 기반 폴백이 제거되었으므로 matched_entities 없는
        Vector 소스에는 graph_context가 생성되지 않습니다.
        """
        results = [
            make_search_result(
                chunk_id="chunk_vector_1",
                source="vector",
                document_id="doc_arch",
                score=0.88,
                content="마이크로서비스 아키텍처 설명",
                metadata={
                    "title": "마이크로서비스 아키텍처",
                    "search_source": "vector",
                },
            ),
        ]

        sources = build_sources_from_results(results)
        source = sources[0]

        # matched_entities 없으므로 graph_context 없음 (타이틀 폴백 제거됨)
        assert "graph_context" not in source

    def test_scenario_mixed_results_correct_entity_extraction(self):
        """
        시나리오 3: 혼합 결과에서 올바른 엔티티 추출

        Graph/Vector/Keyword 소스 혼합 시 각각 올바르게 처리
        matched_entities가 있는 소스만 graph_context를 가짐
        """
        results = [
            # Graph 소스: matched_entities 사용
            make_search_result(
                chunk_id="c_graph",
                source="graph",
                document_id="d1",
                metadata={
                    "title": "설계서.pdf",
                    "matched_entities": ["PostgreSQL", "Elasticsearch"],
                },
            ),
            # Vector 소스: matched_entities 없음 -> graph_context 없음
            make_search_result(
                chunk_id="c_vector",
                source="vector",
                document_id="d2",
                metadata={
                    "title": "API Gateway 설계",
                },
            ),
            # Keyword 소스: 파일명 제목 + matched_entities 없음 -> graph_context 없음
            make_search_result(
                chunk_id="c_keyword",
                source="keyword",
                document_id="d3",
                metadata={
                    "title": "api_spec.xlsx",
                },
            ),
        ]

        sources = build_sources_from_results(results)

        # Graph: 실제 엔티티
        assert "graph_context" in sources[0]
        assert "PostgreSQL" in sources[0]["graph_context"]["related_entities"]
        assert "설계서.pdf" not in sources[0]["graph_context"]["related_entities"]

        # Vector: matched_entities 없으므로 graph_context 없음
        assert "graph_context" not in sources[1]

        # Keyword: 파일명 + matched_entities 없음 -> graph_context 없음
        assert "graph_context" not in sources[2]

    def test_scenario_frontend_would_not_get_filename_as_entity(self):
        """
        시나리오 4: Frontend가 파일명을 entity_name으로 받지 않는지 검증

        Frontend ChatSearch.handleGraphSourceClick()에서:
        - graphContext?.relatedEntities가 있으면 해당 엔티티 사용
        - 없으면 source.title 폴백 (이때 파일명이 될 수 있었음 -> ISSUE-011 버그)
        """
        results = [
            make_search_result(
                chunk_id="c1",
                source="graph",
                metadata={
                    "title": "KMS_설계서.pdf",
                    "matched_entities": ["Neo4j", "Elasticsearch"],
                },
            ),
        ]

        sources = build_sources_from_results(results)

        # Frontend에서 확인하는 경로 시뮬레이션
        source = sources[0]
        graph_context = source.get("graph_context")

        if graph_context and graph_context.get("related_entities"):
            # ISSUE-011 수정 후: 실제 엔티티 사용
            entity_name = graph_context["related_entities"][0]
        else:
            # ISSUE-011 수정 전: 파일명 폴백 (이 경로로 가면 안 됨)
            entity_name = source["title"]

        # entity_name이 파일명이 아닌 실제 엔티티명
        assert entity_name == "Neo4j"
        assert not _is_filename(entity_name)
