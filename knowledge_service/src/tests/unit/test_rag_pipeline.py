"""
RAG Pipeline 단위 테스트

Retrieval-Augmentation-Generation 파이프라인 테스트
- 컨텍스트 구성
- 출처 정보 생성
- 프롬프트 구성
- 에러 핸들링
"""

import sys
from pathlib import Path
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from app.agents.state import SearchResult
from app.services.rag_pipeline import (
    CONTEXT_CHUNK_TEMPLATE,
    RAG_PROMPT_TEMPLATE,
    RAGPipeline,
    RAGResponse,
    SYSTEM_PROMPT_KO,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_search_result(
    chunk_id: str = "chunk_1",
    content: str = "테스트 컨텐츠입니다.",
    score: float = 0.95,
    document_id: str = "doc_1",
    title: str = "테스트 문서",
    source: str = "vector",
) -> SearchResult:
    """테스트용 SearchResult 생성"""
    return SearchResult(
        chunk_id=chunk_id,
        document_id=document_id,
        content=content,
        score=score,
        source=source,
        metadata={"title": title},
    )


def make_search_results(count: int = 5) -> List[SearchResult]:
    """여러 개의 테스트 SearchResult 생성"""
    return [
        make_search_result(
            chunk_id=f"chunk_{i}",
            content=f"청크 {i}의 내용입니다. RAG 파이프라인에서 사용됩니다.",
            score=1.0 - i * 0.1,
            document_id=f"doc_{i // 2}",
            title=f"문서 {i // 2}",
        )
        for i in range(count)
    ]


# ---------------------------------------------------------------------------
# RAGResponse 테스트
# ---------------------------------------------------------------------------


class TestRAGResponse:
    """RAGResponse 모델 테스트"""

    def test_to_dict(self):
        """딕셔너리 변환"""
        response = RAGResponse(
            answer="테스트 답변입니다.",
            sources=[{"index": 1, "title": "문서1"}],
            query="테스트 질문",
            context_length=1000,
            latency_ms=150.5,
            model="deepseek-chat",
        )

        data = response.to_dict()
        assert data["answer"] == "테스트 답변입니다."
        assert data["query"] == "테스트 질문"
        assert data["context_length"] == 1000
        assert data["latency_ms"] == 150.5
        assert data["model"] == "deepseek-chat"
        assert len(data["sources"]) == 1

    def test_default_values(self):
        """기본값 확인"""
        response = RAGResponse(
            answer="답변",
            sources=[],
            query="질문",
        )

        assert response.context_length == 0
        assert response.latency_ms == 0.0
        assert response.model == ""
        assert response.token_usage == {}


# ---------------------------------------------------------------------------
# RAGPipeline - 컨텍스트 구성 테스트
# ---------------------------------------------------------------------------


class TestBuildContext:
    """컨텍스트 구성 테스트"""

    def setup_method(self):
        """테스트 설정"""
        with patch("app.services.rag_pipeline.get_llm_service"):
            self.pipeline = RAGPipeline(
                max_context_length=8000,
                max_context_chunks=10,
            )

    def test_empty_results(self):
        """빈 검색 결과 → 빈 컨텍스트"""
        context, selected = self.pipeline._build_context([])
        assert context == ""
        assert selected == []

    def test_single_result(self):
        """단일 검색 결과 컨텍스트 구성"""
        results = [make_search_result(content="RAG 시스템의 핵심 원리입니다.")]

        context, selected = self.pipeline._build_context(results)

        assert "RAG 시스템의 핵심 원리입니다." in context
        assert "[출처1]" in context
        assert len(selected) == 1

    def test_multiple_results(self):
        """여러 검색 결과 컨텍스트 구성"""
        results = make_search_results(5)

        context, selected = self.pipeline._build_context(results)

        assert len(selected) == 5
        assert "[출처1]" in context
        assert "[출처5]" in context

    def test_max_context_chunks(self):
        """최대 청크 수 제한"""
        with patch("app.services.rag_pipeline.get_llm_service"):
            pipeline = RAGPipeline(
                max_context_chunks=3,
            )

        results = make_search_results(10)
        context, selected = pipeline._build_context(results)

        assert len(selected) == 3

    def test_max_context_length(self):
        """최대 컨텍스트 길이 제한"""
        with patch("app.services.rag_pipeline.get_llm_service"):
            pipeline = RAGPipeline(
                max_context_length=500,  # 매우 짧은 제한
                max_context_chunks=100,
            )

        results = [
            make_search_result(
                chunk_id=f"chunk_{i}",
                content="A" * 200,  # 각 청크가 200자
            )
            for i in range(10)
        ]

        context, selected = pipeline._build_context(results)

        # 500자 제한으로 인해 전부 포함 불가
        assert len(selected) < 10
        assert len(context) <= 600  # 약간의 오차 허용 (템플릿 오버헤드)

    def test_context_contains_metadata(self):
        """컨텍스트에 메타데이터 포함"""
        result = make_search_result(
            content="중요한 내용입니다.",
            document_id="abc-123-def",
            title="설계 문서",
            score=0.95,
        )

        context, _ = self.pipeline._build_context([result])

        assert "설계 문서" in context  # title
        assert "abc-123-" in context  # document_id[:8]
        assert "0.95" in context  # score


# ---------------------------------------------------------------------------
# RAGPipeline - 출처 정보 테스트
# ---------------------------------------------------------------------------


class TestBuildSources:
    """출처 정보 생성 테스트"""

    def setup_method(self):
        """테스트 설정"""
        with patch("app.services.rag_pipeline.get_llm_service"):
            self.pipeline = RAGPipeline()

    def test_empty_results(self):
        """빈 결과 → 빈 출처"""
        sources = self.pipeline._build_sources([])
        assert sources == []

    def test_single_source(self):
        """단일 출처 생성"""
        result = make_search_result(
            chunk_id="chunk_001",
            document_id="doc_001",
            content="중요 내용입니다.",
            score=0.9,
        )

        sources = self.pipeline._build_sources([result])

        assert len(sources) == 1
        assert sources[0]["index"] == 1
        assert sources[0]["chunk_id"] == "chunk_001"
        assert sources[0]["document_id"] == "doc_001"
        assert sources[0]["score"] == 0.9
        assert sources[0]["is_primary"] is True

    def test_same_document_multiple_chunks(self):
        """같은 문서의 여러 청크"""
        results = [
            make_search_result(chunk_id="chunk_1", document_id="doc_1"),
            make_search_result(chunk_id="chunk_2", document_id="doc_1"),
            make_search_result(chunk_id="chunk_3", document_id="doc_2"),
        ]

        sources = self.pipeline._build_sources(results)

        assert len(sources) == 3
        assert sources[0]["is_primary"] is True  # doc_1 첫 번째
        assert sources[1]["is_primary"] is False  # doc_1 두 번째
        assert sources[2]["is_primary"] is True  # doc_2 첫 번째

    def test_snippet_truncation(self):
        """긴 내용의 스니펫 잘림"""
        long_content = "A" * 500

        result = make_search_result(content=long_content)
        sources = self.pipeline._build_sources([result])

        # 200자 이후 "..." 추가
        assert len(sources[0]["snippet"]) < len(long_content)
        assert sources[0]["snippet"].endswith("...")

    def test_short_snippet_no_truncation(self):
        """짧은 내용은 잘리지 않음"""
        short_content = "짧은 내용"

        result = make_search_result(content=short_content)
        sources = self.pipeline._build_sources([result])

        assert sources[0]["snippet"] == short_content


# ---------------------------------------------------------------------------
# RAGPipeline - 문장 분할 테스트
# ---------------------------------------------------------------------------


class TestSplitIntoSentences:
    """문장 분할 테스트"""

    def test_single_sentence(self):
        """단일 문장"""
        sentences = RAGPipeline._split_into_sentences("한 문장입니다.")
        assert len(sentences) == 1

    def test_multiple_sentences(self):
        """여러 문장 분할"""
        text = "첫 번째 문장입니다. 두 번째 문장입니다. 세 번째 문장입니다."
        sentences = RAGPipeline._split_into_sentences(text)
        assert len(sentences) == 3

    def test_mixed_punctuation(self):
        """혼합 문장부호"""
        text = "질문이 있나요? 네, 있습니다! 그것은 중요합니다."
        sentences = RAGPipeline._split_into_sentences(text)
        assert len(sentences) == 3

    def test_empty_text(self):
        """빈 텍스트"""
        sentences = RAGPipeline._split_into_sentences("")
        assert len(sentences) == 0

    def test_whitespace_handling(self):
        """공백 처리"""
        text = "  문장 1.   문장 2.  "
        sentences = RAGPipeline._split_into_sentences(text)
        # 빈 문장이 제거되어야 함
        for s in sentences:
            assert s.strip() != ""


# ---------------------------------------------------------------------------
# RAGPipeline - process_query 테스트
# ---------------------------------------------------------------------------


class TestProcessQuery:
    """process_query 통합 테스트"""

    @pytest.mark.asyncio
    async def test_no_search_results(self):
        """검색 결과 없음 → 폴백 답변"""
        with patch("app.services.rag_pipeline.get_llm_service"):
            pipeline = RAGPipeline()

        response = await pipeline.process_query(
            query="검색 결과 없는 질문",
            search_results=[],
        )

        assert "찾을 수 없습니다" in response.answer
        assert response.sources == []
        assert response.query == "검색 결과 없는 질문"
        assert response.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_with_search_results(self):
        """검색 결과 있음 → LLM 답변"""
        mock_llm = MagicMock()
        mock_llm.generate_with_messages = AsyncMock(
            return_value="RAG 파이프라인은 검색-증강-생성의 3단계로 구성됩니다."
        )

        with patch("app.services.rag_pipeline.get_llm_service", return_value=mock_llm):
            pipeline = RAGPipeline()

        results = make_search_results(3)
        response = await pipeline.process_query(
            query="RAG 파이프라인이란?",
            search_results=results,
        )

        assert response.answer == "RAG 파이프라인은 검색-증강-생성의 3단계로 구성됩니다."
        assert len(response.sources) == 3
        assert response.query == "RAG 파이프라인이란?"
        assert response.latency_ms > 0


# ---------------------------------------------------------------------------
# 프롬프트 템플릿 테스트
# ---------------------------------------------------------------------------


class TestPromptTemplates:
    """프롬프트 템플릿 검증"""

    def test_system_prompt_exists(self):
        """시스템 프롬프트 존재"""
        assert len(SYSTEM_PROMPT_KO) > 100
        assert "컨텍스트" in SYSTEM_PROMPT_KO
        assert "출처" in SYSTEM_PROMPT_KO

    def test_rag_prompt_template(self):
        """RAG 프롬프트 템플릿 포맷"""
        formatted = RAG_PROMPT_TEMPLATE.format(
            context="테스트 컨텍스트",
            query="테스트 질문",
        )

        assert "테스트 컨텍스트" in formatted
        assert "테스트 질문" in formatted

    def test_context_chunk_template(self):
        """컨텍스트 청크 템플릿 포맷"""
        formatted = CONTEXT_CHUNK_TEMPLATE.format(
            index=1,
            title="문서 제목",
            document_id="abc-123",
            score=0.95,
            content="청크 내용입니다.",
        )

        assert "[출처1]" in formatted
        assert "문서 제목" in formatted
        assert "abc-123" in formatted
        assert "0.95" in formatted
        assert "청크 내용입니다." in formatted
