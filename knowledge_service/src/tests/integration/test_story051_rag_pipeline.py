"""
STORY-051 RAG Pipeline Integration Tests (Day 2)

SearchService -> LangGraph RAG Workflow 통합 테스트
- LLM Adapter: 생성, 타임아웃, 에러 변환
- RAG Workflow: 전체 파이프라인 실행, 에러 핸들링
- Generator Node: reranked 문서 프롬프트 포맷
- 레거시 파이프라인 deprecation 경고
- Error translation (504/502/429/400)
"""

import asyncio
import sys
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from app.agents.state import SearchResult
from app.core.exceptions import LLMError, LLMRateLimitError, LLMTimeoutError


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
# LLM Adapter Tests
# ---------------------------------------------------------------------------


class TestLLMAdapter:
    """LLM Adapter 테스트"""

    def test_create_adapter(self):
        """LLMAdapter 생성"""
        from app.services.llm_adapter import LLMAdapter

        mock_service = MagicMock()
        adapter = LLMAdapter(llm_service=mock_service)

        assert adapter.llm_service == mock_service
        assert adapter._timeout == 60  # settings 기본값

    def test_create_adapter_with_custom_timeout(self):
        """사용자 지정 타임아웃"""
        from app.services.llm_adapter import LLMAdapter

        adapter = LLMAdapter(
            llm_service=MagicMock(),
            timeout_seconds=120,
        )
        assert adapter._timeout == 120

    def test_create_adapter_with_custom_system_prompt(self):
        """사용자 지정 시스템 프롬프트"""
        from app.services.llm_adapter import LLMAdapter

        adapter = LLMAdapter(
            llm_service=MagicMock(),
            system_prompt="Custom system prompt",
        )
        assert adapter._system_prompt == "Custom system prompt"

    def test_build_messages_with_context(self):
        """컨텍스트 포함 메시지 구성"""
        from app.services.llm_adapter import LLMAdapter

        adapter = LLMAdapter(llm_service=MagicMock())
        messages = adapter._build_messages(
            prompt="질문입니다",
            context="컨텍스트 정보",
        )

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "컨텍스트 정보" in messages[1]["content"]
        assert "질문입니다" in messages[1]["content"]

    def test_build_messages_without_context(self):
        """컨텍스트 없는 메시지 구성"""
        from app.services.llm_adapter import LLMAdapter

        adapter = LLMAdapter(llm_service=MagicMock())
        messages = adapter._build_messages(
            prompt="질문입니다",
            context="",
        )

        assert len(messages) == 2
        assert messages[1]["content"] == "질문입니다"

    @pytest.mark.asyncio
    async def test_generate_success(self):
        """정상 답변 생성"""
        from app.services.llm_adapter import LLMAdapter

        mock_service = MagicMock()
        mock_service.generate_with_messages = AsyncMock(
            return_value="RAG 시스템은 검색-증강-생성의 3단계입니다."
        )

        adapter = LLMAdapter(llm_service=mock_service)
        answer = await adapter.generate(
            prompt="RAG 시스템이란?",
            context="RAG는 Retrieval-Augmented Generation의 약자입니다.",
        )

        assert answer == "RAG 시스템은 검색-증강-생성의 3단계입니다."
        mock_service.generate_with_messages.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_empty_prompt_raises_validation_error(self):
        """빈 프롬프트 -> ServiceValidationError (400)"""
        from app.services.llm_adapter import LLMAdapter, ServiceValidationError

        adapter = LLMAdapter(llm_service=MagicMock())

        with pytest.raises(ServiceValidationError) as exc_info:
            await adapter.generate(prompt="", context="some context")

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_generate_timeout_raises_timeout_error(self):
        """타임아웃 -> ServiceTimeoutError (504)"""
        from app.services.llm_adapter import LLMAdapter, ServiceTimeoutError

        async def slow_generate(*args, **kwargs):
            await asyncio.sleep(10)  # 매우 느린 응답
            return "late answer"

        mock_service = MagicMock()
        mock_service.generate_with_messages = slow_generate

        adapter = LLMAdapter(
            llm_service=mock_service,
            timeout_seconds=0.1,  # 0.1초 타임아웃
        )

        with pytest.raises(ServiceTimeoutError) as exc_info:
            await adapter.generate(prompt="질문", context="컨텍스트")

        assert exc_info.value.status_code == 504

    @pytest.mark.asyncio
    async def test_generate_llm_error_raises_connection_error(self):
        """LLM 에러 -> ServiceConnectionError (502)"""
        from app.services.llm_adapter import LLMAdapter, ServiceConnectionError

        mock_service = MagicMock()
        mock_service.generate_with_messages = AsyncMock(
            side_effect=LLMError("LLM 호출 실패")
        )

        adapter = LLMAdapter(llm_service=mock_service)

        with pytest.raises(ServiceConnectionError) as exc_info:
            await adapter.generate(prompt="질문", context="컨텍스트")

        assert exc_info.value.status_code == 502

    @pytest.mark.asyncio
    async def test_generate_rate_limit_raises_rate_limit_error(self):
        """Rate Limit -> ServiceRateLimitError (429)"""
        from app.services.llm_adapter import LLMAdapter, ServiceRateLimitError

        mock_service = MagicMock()
        mock_service.generate_with_messages = AsyncMock(
            side_effect=LLMRateLimitError()
        )

        adapter = LLMAdapter(llm_service=mock_service)

        with pytest.raises(ServiceRateLimitError) as exc_info:
            await adapter.generate(prompt="질문", context="컨텍스트")

        assert exc_info.value.status_code == 429


# ---------------------------------------------------------------------------
# Error Translation Tests
# ---------------------------------------------------------------------------


class TestErrorTranslation:
    """에러 변환 테스트"""

    def test_translate_timeout_error(self):
        """LLMTimeoutError -> ServiceTimeoutError (504)"""
        from app.services.llm_adapter import translate_llm_error

        result = translate_llm_error(LLMTimeoutError(timeout=60))
        assert result.status_code == 504

    def test_translate_rate_limit_error(self):
        """LLMRateLimitError -> ServiceRateLimitError (429)"""
        from app.services.llm_adapter import translate_llm_error

        result = translate_llm_error(LLMRateLimitError())
        assert result.status_code == 429

    def test_translate_connection_error(self):
        """ConnectionError -> ServiceConnectionError (502)"""
        from app.services.llm_adapter import translate_llm_error

        result = translate_llm_error(ConnectionError("connection refused"))
        assert result.status_code == 502

    def test_translate_asyncio_timeout(self):
        """asyncio.TimeoutError -> ServiceTimeoutError (504)"""
        from app.services.llm_adapter import translate_llm_error

        result = translate_llm_error(asyncio.TimeoutError())
        assert result.status_code == 504

    def test_translate_generic_llm_error(self):
        """LLMError -> ServiceConnectionError (502)"""
        from app.services.llm_adapter import translate_llm_error

        result = translate_llm_error(LLMError("generic error"))
        assert result.status_code == 502

    def test_translate_unknown_error(self):
        """Unknown error -> KnowledgeServiceError (500)"""
        from app.services.llm_adapter import translate_llm_error

        result = translate_llm_error(ValueError("unexpected"))
        assert result.status_code == 500

    def test_translate_timeout_by_string_pattern(self):
        """문자열 패턴 'timeout' -> 504"""
        from app.services.llm_adapter import translate_llm_error

        result = translate_llm_error(Exception("Request timed out"))
        assert result.status_code == 504

    def test_translate_rate_limit_by_string_pattern(self):
        """문자열 패턴 '429' -> 429"""
        from app.services.llm_adapter import translate_llm_error

        result = translate_llm_error(Exception("Error 429 Too Many Requests"))
        assert result.status_code == 429

    def test_translate_connection_by_string_pattern(self):
        """문자열 패턴 'connection refused' -> 502"""
        from app.services.llm_adapter import translate_llm_error

        result = translate_llm_error(Exception("Connection refused"))
        assert result.status_code == 502


# ---------------------------------------------------------------------------
# Context Builder Tests
# ---------------------------------------------------------------------------


class TestContextBuilder:
    """컨텍스트 빌더 테스트"""

    def test_build_context_empty(self):
        """빈 결과 -> 빈 컨텍스트"""
        from app.agents.rag_workflow import build_context_from_results

        context, selected = build_context_from_results([])
        assert context == ""
        assert selected == []

    def test_build_context_single_result(self):
        """단일 결과 컨텍스트 구성"""
        from app.agents.rag_workflow import build_context_from_results

        results = [make_search_result(content="RAG 시스템의 핵심 원리")]
        context, selected = build_context_from_results(results)

        assert "RAG 시스템의 핵심 원리" in context
        assert "[출처1]" in context
        assert len(selected) == 1

    def test_build_context_multiple_results(self):
        """여러 결과 컨텍스트 구성"""
        from app.agents.rag_workflow import build_context_from_results

        results = make_search_results(5)
        context, selected = build_context_from_results(results)

        assert len(selected) == 5
        assert "[출처1]" in context
        assert "[출처5]" in context

    def test_build_context_max_chunks(self):
        """최대 청크 수 제한"""
        from app.agents.rag_workflow import build_context_from_results

        results = make_search_results(20)
        context, selected = build_context_from_results(
            results, max_chunks=3
        )

        assert len(selected) == 3

    def test_build_context_max_length(self):
        """최대 길이 제한"""
        from app.agents.rag_workflow import build_context_from_results

        results = [
            make_search_result(
                chunk_id=f"chunk_{i}",
                content="A" * 200,
            )
            for i in range(10)
        ]

        context, selected = build_context_from_results(
            results, max_length=500, max_chunks=100
        )

        assert len(selected) < 10

    def test_build_sources_empty(self):
        """빈 결과 -> 빈 출처"""
        from app.agents.rag_workflow import build_sources_from_results

        sources = build_sources_from_results([])
        assert sources == []

    def test_build_sources_with_results(self):
        """출처 정보 생성"""
        from app.agents.rag_workflow import build_sources_from_results

        results = make_search_results(3)
        sources = build_sources_from_results(results)

        assert len(sources) == 3
        assert sources[0]["index"] == 1
        assert "chunk_id" in sources[0]
        assert "score" in sources[0]

    def test_build_sources_dedup_documents(self):
        """같은 문서의 여러 청크 처리"""
        from app.agents.rag_workflow import build_sources_from_results

        results = [
            make_search_result(chunk_id="c1", document_id="doc_1"),
            make_search_result(chunk_id="c2", document_id="doc_1"),
            make_search_result(chunk_id="c3", document_id="doc_2"),
        ]
        sources = build_sources_from_results(results)

        assert sources[0]["is_primary"] is True
        assert sources[1]["is_primary"] is False  # same doc
        assert sources[2]["is_primary"] is True


# ---------------------------------------------------------------------------
# RAG Workflow Tests
# ---------------------------------------------------------------------------


class TestRAGWorkflow:
    """RAG Workflow 테스트"""

    def test_create_workflow(self):
        """RAGWorkflow 생성"""
        from app.agents.rag_workflow import RAGWorkflow

        workflow = RAGWorkflow(
            search_service=MagicMock(),
            llm_adapter=MagicMock(),
        )
        assert workflow._search_service is not None
        assert workflow._llm_adapter is not None

    @pytest.mark.asyncio
    async def test_workflow_run_no_results(self):
        """검색 결과 없음 -> 폴백 답변"""
        from app.agents.rag_workflow import RAGWorkflow

        mock_search = MagicMock()
        mock_search.hybrid_search = AsyncMock(
            return_value={"results": [], "total": 0}
        )

        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value="답변")

        workflow = RAGWorkflow(
            search_service=mock_search,
            llm_adapter=mock_llm,
        )

        response = await workflow.run(query="검색 결과 없는 질문")

        assert "찾을 수 없습니다" in response.answer
        assert response.sources == []

    @pytest.mark.asyncio
    async def test_workflow_run_with_results(self):
        """검색 결과 있음 -> LLM 답변 생성"""
        from app.agents.rag_workflow import RAGWorkflow

        search_results = make_search_results(3)

        mock_search = MagicMock()
        mock_search.hybrid_search = AsyncMock(
            return_value={"results": search_results, "total": 3}
        )

        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(
            return_value="RAG 파이프라인은 검색과 생성을 결합합니다."
        )

        workflow = RAGWorkflow(
            search_service=mock_search,
            llm_adapter=mock_llm,
        )

        response = await workflow.run(query="RAG 파이프라인이란?", top_k=3)

        assert response.answer == "RAG 파이프라인은 검색과 생성을 결합합니다."
        assert len(response.sources) == 3
        assert response.latency_ms > 0
        mock_llm.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_workflow_run_validation_error(self):
        """빈 질의 -> ServiceValidationError (400)"""
        from app.agents.rag_workflow import RAGWorkflow
        from app.services.llm_adapter import ServiceValidationError

        workflow = RAGWorkflow(search_service=MagicMock())

        with pytest.raises(ServiceValidationError):
            await workflow.run(query="")

    @pytest.mark.asyncio
    async def test_workflow_run_retrieval_failure_graceful(self):
        """검색 실패 -> graceful 에러 처리"""
        from app.agents.rag_workflow import RAGWorkflow

        mock_search = MagicMock()
        mock_search.hybrid_search = AsyncMock(
            side_effect=Exception("ES connection failed")
        )

        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value="답변")

        workflow = RAGWorkflow(
            search_service=mock_search,
            llm_adapter=mock_llm,
        )

        response = await workflow.run(query="질문")

        # 검색 실패하면 빈 결과 + 폴백 답변
        assert "찾을 수 없습니다" in response.answer

    @pytest.mark.asyncio
    async def test_workflow_run_generation_failure_fallback(self):
        """LLM 생성 실패 -> 검색 결과 폴백"""
        from app.agents.rag_workflow import RAGWorkflow

        search_results = make_search_results(3)

        mock_search = MagicMock()
        mock_search.hybrid_search = AsyncMock(
            return_value={"results": search_results, "total": 3}
        )

        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(
            side_effect=Exception("LLM service down")
        )

        workflow = RAGWorkflow(
            search_service=mock_search,
            llm_adapter=mock_llm,
        )

        response = await workflow.run(query="질문")

        # 생성 실패하면 검색 결과 요약 반환
        assert "답변 생성에 실패" in response.answer

    @pytest.mark.asyncio
    async def test_workflow_with_hybrid_retriever(self):
        """HybridRetriever 사용 경로"""
        from app.agents.rag_workflow import RAGWorkflow

        search_results = make_search_results(5)

        mock_retriever = MagicMock()
        mock_retriever.retrieve = AsyncMock(return_value=search_results)

        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value="Retriever 기반 답변")

        workflow = RAGWorkflow(
            hybrid_retriever=mock_retriever,
            llm_adapter=mock_llm,
        )

        response = await workflow.run(query="테스트 질문", top_k=5)

        assert response.answer == "Retriever 기반 답변"
        mock_retriever.retrieve.assert_called_once()


# ---------------------------------------------------------------------------
# RAG Workflow Response Tests
# ---------------------------------------------------------------------------


class TestRAGWorkflowResponse:
    """RAGWorkflowResponse 테스트"""

    def test_to_dict(self):
        """딕셔너리 변환"""
        from app.agents.rag_workflow import RAGWorkflowResponse

        response = RAGWorkflowResponse(
            answer="테스트 답변",
            sources=[{"index": 1, "title": "문서"}],
            query="테스트 질문",
            context_length=500,
            latency_ms=150.5,
            model="deepseek-chat",
        )

        data = response.to_dict()
        assert data["answer"] == "테스트 답변"
        assert data["query"] == "테스트 질문"
        assert data["context_length"] == 500
        assert data["latency_ms"] == 150.5
        assert data["model"] == "deepseek-chat"
        assert len(data["sources"]) == 1

    def test_default_values(self):
        """기본값 확인"""
        from app.agents.rag_workflow import RAGWorkflowResponse

        response = RAGWorkflowResponse(answer="답변")

        assert response.sources == []
        assert response.query == ""
        assert response.context_length == 0
        assert response.latency_ms == 0.0
        assert response.error is None


# ---------------------------------------------------------------------------
# Generator Node (Prompt Formatting) Tests
# ---------------------------------------------------------------------------


class TestGeneratorNode:
    """Generator Node 테스트 - reranked 문서가 프롬프트에 포함되는지 확인"""

    @pytest.mark.asyncio
    async def test_generator_uses_reranked_documents(self):
        """Generator가 reranked 문서를 프롬프트에 포함"""
        from app.agents.rag_workflow import RAGWorkflow

        reranked_results = [
            make_search_result(
                chunk_id="reranked_1",
                content="Reranked 첫 번째 문서 내용",
                score=0.99,
                title="Reranked Doc 1",
            ),
            make_search_result(
                chunk_id="reranked_2",
                content="Reranked 두 번째 문서 내용",
                score=0.95,
                title="Reranked Doc 2",
            ),
        ]

        mock_search = MagicMock()
        mock_search.hybrid_search = AsyncMock(
            return_value={"results": reranked_results, "total": 2}
        )

        # LLM generate 호출 시 context 내용 캡처
        captured_calls: list = []

        async def capture_generate(prompt, context="", **kwargs):
            captured_calls.append({"prompt": prompt, "context": context})
            return "생성된 답변"

        mock_llm = MagicMock()
        mock_llm.generate = capture_generate

        workflow = RAGWorkflow(
            search_service=mock_search,
            llm_adapter=mock_llm,
        )

        response = await workflow.run(query="테스트 질문", top_k=5)

        # LLM이 호출되었는지 확인
        assert len(captured_calls) == 1

        # 컨텍스트에 reranked 문서 내용이 포함되었는지 확인
        context = captured_calls[0]["context"]
        assert "Reranked 첫 번째 문서 내용" in context
        assert "Reranked 두 번째 문서 내용" in context
        assert "[출처1]" in context
        assert "[출처2]" in context

    @pytest.mark.asyncio
    async def test_generator_formats_document_metadata(self):
        """Generator가 문서 메타데이터 (제목, 점수, ID)를 포맷"""
        from app.agents.rag_workflow import RAGWorkflow

        results = [
            make_search_result(
                chunk_id="c1",
                content="중요한 내용",
                score=0.98,
                document_id="abc-123-def",
                title="설계 문서",
            ),
        ]

        mock_search = MagicMock()
        mock_search.hybrid_search = AsyncMock(
            return_value={"results": results, "total": 1}
        )

        captured_context = []

        async def capture(prompt, context="", **kwargs):
            captured_context.append(context)
            return "답변"

        mock_llm = MagicMock()
        mock_llm.generate = capture

        workflow = RAGWorkflow(
            search_service=mock_search,
            llm_adapter=mock_llm,
        )

        await workflow.run(query="질문")

        context = captured_context[0]
        assert "설계 문서" in context  # title
        assert "abc-123-" in context  # document_id[:8]
        assert "0.98" in context  # score


# ---------------------------------------------------------------------------
# Legacy Pipeline Deprecation Tests
# ---------------------------------------------------------------------------


class TestLegacyPipelineDeprecation:
    """레거시 RAGPipeline 비활성화 테스트"""

    def test_rag_pipeline_emits_deprecation_warning(self):
        """RAGPipeline 생성 시 DeprecationWarning"""
        with patch("app.services.rag_pipeline.get_llm_service"):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")

                from app.services.rag_pipeline import RAGPipeline
                pipeline = RAGPipeline()

                # DeprecationWarning이 발생해야 함
                deprecation_warnings = [
                    x for x in w if issubclass(x.category, DeprecationWarning)
                ]
                assert len(deprecation_warnings) >= 1
                assert "레거시" in str(deprecation_warnings[0].message)

    def test_legacy_pipeline_still_works(self):
        """레거시 파이프라인이 여전히 동작 (하위 호환성)"""
        with patch("app.services.rag_pipeline.get_llm_service"):
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")

                from app.services.rag_pipeline import RAGPipeline
                pipeline = RAGPipeline()

                # 내부 메서드 호출 확인
                context, selected = pipeline._build_context([])
                assert context == ""
                assert selected == []


# ---------------------------------------------------------------------------
# Singleton Management Tests
# ---------------------------------------------------------------------------


class TestSingletonManagement:
    """싱글톤 관리 테스트"""

    def test_llm_adapter_singleton(self):
        """LLMAdapter 싱글톤"""
        from app.services.llm_adapter import (
            get_llm_adapter,
            reset_llm_adapter,
        )

        reset_llm_adapter()

        adapter1 = get_llm_adapter()
        adapter2 = get_llm_adapter()

        assert adapter1 is adapter2

        reset_llm_adapter()

    def test_rag_workflow_singleton(self):
        """RAGWorkflow 싱글톤"""
        from app.agents.rag_workflow import (
            get_rag_workflow,
            reset_rag_workflow,
        )

        reset_rag_workflow()

        wf1 = get_rag_workflow(search_service=MagicMock())
        wf2 = get_rag_workflow()

        assert wf1 is wf2

        reset_rag_workflow()


# ---------------------------------------------------------------------------
# Pipeline Stages Detail Tests
# ---------------------------------------------------------------------------


class TestPipelineStages:
    """파이프라인 단계별 상세 테스트"""

    @pytest.mark.asyncio
    async def test_plan_stage_returns_hybrid(self):
        """Plan 단계는 hybrid 전략 반환"""
        from app.agents.rag_workflow import RAGWorkflow

        workflow = RAGWorkflow()
        strategy = workflow._plan("어떤 질문이든")
        assert strategy == "hybrid"

    @pytest.mark.asyncio
    async def test_retrieve_stage_with_search_service(self):
        """Retrieve 단계 - SearchService 사용"""
        from app.agents.rag_workflow import RAGWorkflow

        results = make_search_results(3)
        mock_search = MagicMock()
        mock_search.hybrid_search = AsyncMock(
            return_value={"results": results, "total": 3}
        )

        workflow = RAGWorkflow(search_service=mock_search)
        retrieved = await workflow._retrieve(query="질문", top_k=5)

        assert len(retrieved) == 3
        mock_search.hybrid_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_retrieve_stage_with_hybrid_retriever(self):
        """Retrieve 단계 - HybridRetriever 우선 사용"""
        from app.agents.rag_workflow import RAGWorkflow

        results = make_search_results(5)
        mock_retriever = MagicMock()
        mock_retriever.retrieve = AsyncMock(return_value=results)

        mock_search = MagicMock()  # 사용되면 안 됨

        workflow = RAGWorkflow(
            search_service=mock_search,
            hybrid_retriever=mock_retriever,
        )

        retrieved = await workflow._retrieve(query="질문", top_k=5)

        assert len(retrieved) == 5
        mock_retriever.retrieve.assert_called_once()
        mock_search.hybrid_search.assert_not_called()

    @pytest.mark.asyncio
    async def test_retrieve_stage_no_service(self):
        """Retrieve 단계 - 서비스 없음"""
        from app.agents.rag_workflow import RAGWorkflow

        workflow = RAGWorkflow()  # no search_service or retriever
        retrieved = await workflow._retrieve(query="질문")

        assert retrieved == []

    @pytest.mark.asyncio
    async def test_generate_stage_no_context(self):
        """Generate 단계 - 컨텍스트 없음"""
        from app.agents.rag_workflow import RAGWorkflow

        workflow = RAGWorkflow(llm_adapter=MagicMock())
        answer, context, selected = await workflow._generate(
            query="질문",
            search_results=[],
        )

        assert "찾을 수 없습니다" in answer
        assert context == ""
        assert selected == []

    @pytest.mark.asyncio
    async def test_generate_stage_with_context(self):
        """Generate 단계 - 컨텍스트 있음"""
        from app.agents.rag_workflow import RAGWorkflow

        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value="LLM이 생성한 답변")

        workflow = RAGWorkflow(llm_adapter=mock_llm)
        results = make_search_results(3)

        answer, context, selected = await workflow._generate(
            query="질문",
            search_results=results,
        )

        assert answer == "LLM이 생성한 답변"
        assert len(context) > 0
        assert len(selected) == 3

    def test_fallback_answer_no_results(self):
        """폴백 답변 - 검색 결과 없음"""
        from app.agents.rag_workflow import RAGWorkflow

        answer = RAGWorkflow._fallback_answer([])
        assert "찾을 수 없습니다" in answer

    def test_fallback_answer_with_results(self):
        """폴백 답변 - 검색 결과 있음"""
        from app.agents.rag_workflow import RAGWorkflow

        results = make_search_results(3)
        answer = RAGWorkflow._fallback_answer(results)

        assert "답변 생성에 실패" in answer
        assert "1." in answer  # 번호 매긴 목록


# ---------------------------------------------------------------------------
# Pipeline Stages Info Tests
# ---------------------------------------------------------------------------


class TestPipelineStagesInfo:
    """파이프라인 실행 시 stages 정보 포함 테스트"""

    @pytest.mark.asyncio
    async def test_workflow_response_includes_stages(self):
        """응답에 pipeline_stages 정보 포함"""
        from app.agents.rag_workflow import RAGWorkflow

        results = make_search_results(2)
        mock_search = MagicMock()
        mock_search.hybrid_search = AsyncMock(
            return_value={"results": results, "total": 2}
        )

        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value="답변")

        workflow = RAGWorkflow(
            search_service=mock_search,
            llm_adapter=mock_llm,
        )

        response = await workflow.run(query="질문")

        assert "plan" in response.pipeline_stages
        assert "retrieve" in response.pipeline_stages
        assert "generate" in response.pipeline_stages

        # plan 단계 정보
        assert response.pipeline_stages["plan"]["strategy"] == "hybrid"
        assert "latency_ms" in response.pipeline_stages["plan"]

        # retrieve 단계 정보
        assert response.pipeline_stages["retrieve"]["result_count"] == 2


# ---------------------------------------------------------------------------
# Integration: Search Route -> LangGraph Tests
# ---------------------------------------------------------------------------


class TestSearchRouteLangGraphIntegration:
    """Search API Route가 LangGraph Workflow를 호출하는지 확인"""

    def test_chat_route_imports_rag_workflow(self):
        """chat_search 함수가 rag_workflow를 import"""
        from app.api.routes.search import chat_search

        # 함수가 존재하는지 확인
        assert callable(chat_search)

    def test_search_route_has_error_translation(self):
        """search route에 에러 변환 헬퍼 존재"""
        from app.api.routes.search import _translate_service_error
        from app.services.llm_adapter import ServiceTimeoutError

        error = ServiceTimeoutError(
            service_name="test", timeout_seconds=60
        )
        http_error = _translate_service_error(error)
        assert http_error.status_code == 504

    def test_error_translation_502(self):
        """502 Bad Gateway 변환"""
        from app.api.routes.search import _translate_service_error
        from app.services.llm_adapter import ServiceConnectionError

        error = ServiceConnectionError(service_name="test")
        http_error = _translate_service_error(error)
        assert http_error.status_code == 502

    def test_error_translation_429(self):
        """429 Too Many Requests 변환"""
        from app.api.routes.search import _translate_service_error
        from app.services.llm_adapter import ServiceRateLimitError

        error = ServiceRateLimitError(service_name="test")
        http_error = _translate_service_error(error)
        assert http_error.status_code == 429

    def test_error_translation_400(self):
        """400 Bad Request 변환"""
        from app.api.routes.search import _translate_service_error
        from app.services.llm_adapter import ServiceValidationError

        error = ServiceValidationError(message="invalid")
        http_error = _translate_service_error(error)
        assert http_error.status_code == 400

    def test_error_translation_500_fallback(self):
        """500 Internal Server Error 폴백"""
        from app.api.routes.search import _translate_service_error

        error = Exception("unexpected error")
        http_error = _translate_service_error(error)
        assert http_error.status_code == 500
