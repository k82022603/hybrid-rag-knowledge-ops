"""
RAG Pipeline Integration Tests

ai_service <-> knowledge_service 통합 테스트

테스트 범위:
    1. LLMAdapter: LangGraph 노드 호환 시그니처 검증
    2. RetrieverAdapter: retrieve_fn 시그니처 검증
    3. RerankerAdapter: 리랭킹 어댑터 동작 검증
    4. KnowledgeServiceClient: Direct/HTTP 모드 검증
    5. Bootstrap: 파이프라인 조립 검증
    6. RAGWorkflow 통합: 전체 파이프라인 E2E 검증

STORY-051: RAG 파이프라인 통합
"""

import json
from typing import Any, AsyncIterator, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_service.src.adapters.knowledge_service_client import (
    ConnectionMode,
    KnowledgeServiceClient,
)
from ai_service.src.adapters.llm_adapter import LLMAdapter
from ai_service.src.adapters.reranker_adapter import RerankerAdapter
from ai_service.src.adapters.retriever_adapter import RetrieverAdapter
from ai_service.src.bootstrap import (
    PipelineConfig,
    PipelineComponents,
    bootstrap_rag_pipeline,
)
from ai_service.src.workflows.nodes.generator import GeneratorNode
from ai_service.src.workflows.nodes.planner import PlannerNode
from ai_service.src.workflows.nodes.retriever import RetrieverNode
from ai_service.src.workflows.nodes.validator import ValidatorNode
from ai_service.src.workflows.rag_workflow import RAGWorkflow


# ---------------------------------------------------------------------------
# Mock Fixtures
# ---------------------------------------------------------------------------

class MockLLMService:
    """LLMService 모의 객체"""

    async def generate_with_messages(
        self,
        messages: List[Dict[str, str]],
        use_reasoner: bool = False,
    ) -> str:
        """모의 LLM 응답 생성"""
        system_content = messages[0].get("content", "") if messages else ""
        user_content = messages[1].get("content", "") if len(messages) > 1 else ""

        # Planner 요청 감지
        if "검색 전략" in system_content or "search_strategy" in system_content:
            return json.dumps({
                "search_strategy": "hybrid",
                "refined_query": user_content[:100],
                "reasoning": "Mock: hybrid 전략 선택",
            }, ensure_ascii=False)

        # Validator 요청 감지
        if "검증기" in system_content or "품질 검증" in system_content:
            return json.dumps({
                "faithfulness_score": 0.92,
                "relevance_score": 0.88,
                "is_valid": True,
                "feedback": "Mock: 검증 통과",
            }, ensure_ascii=False)

        # Generator 기본 응답
        return "FastAPI는 Python 기반의 고성능 웹 프레임워크입니다. [1] [2]"

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        return "Mock response"


class MockHybridRetriever:
    """HybridRetriever 모의 객체"""

    def __init__(self) -> None:
        self._reranker = None

    async def retrieve(
        self,
        query: str,
        entities: Optional[List[Dict[str, Any]]] = None,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        use_reranking: bool = True,
    ) -> List[Any]:
        """모의 검색 결과 반환"""
        return [
            self._make_result(
                chunk_id=f"chunk-{i}",
                content=f"Mock document {i} about {query[:30]}",
                score=1.0 - i * 0.1,
            )
            for i in range(min(top_k, 5))
        ]

    async def retrieve_by_source(
        self,
        query: str,
        source: str = "vector",
        top_k: int = 10,
        **kwargs: Any,
    ) -> List[Any]:
        """소스별 검색"""
        return await self.retrieve(query=query, top_k=top_k)

    def _make_result(
        self,
        chunk_id: str,
        content: str,
        score: float,
    ) -> Any:
        """SearchResult 모의 객체 생성"""
        result = MagicMock()
        result.chunk_id = chunk_id
        result.document_id = f"doc-{chunk_id}"
        result.content = content
        result.score = score
        result.source = "vector"
        result.metadata = {"title": f"Title for {chunk_id}"}
        return result

    def health_check(self) -> Dict[str, Any]:
        return {"service": "MockHybridRetriever", "status": "healthy"}


class MockBGEReranker:
    """BGEReranker 모의 객체"""

    async def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: Optional[int] = None,
    ) -> List[Any]:
        """모의 리랭킹"""
        results = []
        for i, doc in enumerate(documents[:top_k or len(documents)]):
            result = MagicMock()
            result.doc_id = doc.get("chunk_id", doc.get("doc_id", f"doc-{i}"))
            result.content = doc.get("content", "")
            result.score = 0.95 - i * 0.05
            result.original_score = doc.get("score", 0.0)
            result.rank = i
            result.metadata = {"rerank_score": result.score}
            results.append(result)
        return results

    def health_check(self) -> Dict[str, Any]:
        return {"service": "MockBGEReranker", "is_loaded": True}


# ---------------------------------------------------------------------------
# Test: LLMAdapter
# ---------------------------------------------------------------------------

class TestLLMAdapter:
    """LLMAdapter 테스트"""

    @pytest.fixture
    def adapter(self) -> LLMAdapter:
        return LLMAdapter(
            llm_service=MockLLMService(),
            use_reasoner=False,
            fallback_enabled=True,
        )

    @pytest.mark.asyncio
    async def test_call_planner_prompt(self, adapter: LLMAdapter) -> None:
        """Planner 노드 시그니처로 LLM 호출 테스트"""
        response = await adapter.call(
            system_prompt="당신은 RAG 시스템의 쿼리 플래너입니다. 검색 전략을 결정합니다.",
            user_message="FastAPI 사용법은?",
        )

        assert response
        parsed = json.loads(response)
        assert "search_strategy" in parsed
        assert parsed["search_strategy"] in ("keyword", "semantic", "hybrid")

    @pytest.mark.asyncio
    async def test_call_generator_prompt(self, adapter: LLMAdapter) -> None:
        """Generator 노드 시그니처로 LLM 호출 테스트"""
        response = await adapter.call(
            system_prompt="당신은 지식 검색 시스템의 답변 생성기입니다.",
            user_message="컨텍스트: FastAPI는... 질문: FastAPI란?",
        )

        assert response
        assert len(response) > 10

    @pytest.mark.asyncio
    async def test_call_validator_prompt(self, adapter: LLMAdapter) -> None:
        """Validator 노드 시그니처로 LLM 호출 테스트"""
        response = await adapter.call(
            system_prompt="당신은 RAG 시스템의 답변 품질 검증기입니다.",
            user_message="[질문] FastAPI란? [답변] FastAPI는 웹 프레임워크입니다.",
        )

        assert response
        # Generator 기본 응답이 반환됨
        assert len(response) > 5

    @pytest.mark.asyncio
    async def test_fallback_on_error(self) -> None:
        """LLM 호출 실패 시 폴백 응답 테스트"""
        failing_service = MagicMock()
        failing_service.generate_with_messages = AsyncMock(
            side_effect=Exception("API Error")
        )

        adapter = LLMAdapter(
            llm_service=failing_service,
            fallback_enabled=True,
        )

        # Planner 폴백
        response = await adapter.call(
            system_prompt="검색 전략을 결정합니다. search_strategy",
            user_message="test query",
        )
        parsed = json.loads(response)
        assert parsed["search_strategy"] == "hybrid"

    @pytest.mark.asyncio
    async def test_no_fallback_raises(self) -> None:
        """fallback 비활성화 시 예외 전파 테스트"""
        failing_service = MagicMock()
        failing_service.generate_with_messages = AsyncMock(
            side_effect=Exception("API Error")
        )

        adapter = LLMAdapter(
            llm_service=failing_service,
            fallback_enabled=False,
        )

        with pytest.raises(RuntimeError, match="LLM call failed"):
            await adapter.call("system", "user")

    @pytest.mark.asyncio
    async def test_stream(self, adapter: LLMAdapter) -> None:
        """스트리밍 LLM 호출 테스트"""
        chunks = []
        async for chunk in adapter.stream("system prompt", "user message"):
            chunks.append(chunk)

        assert len(chunks) > 0
        full_text = " ".join(chunks)
        assert "FastAPI" in full_text

    def test_health_check(self, adapter: LLMAdapter) -> None:
        """상태 점검 테스트"""
        health = adapter.health_check()
        assert health["service"] == "LLMAdapter"
        assert health["llm_service_available"] is True


# ---------------------------------------------------------------------------
# Test: KnowledgeServiceClient
# ---------------------------------------------------------------------------

class TestKnowledgeServiceClient:
    """KnowledgeServiceClient 테스트"""

    @pytest.fixture
    def direct_client(self) -> KnowledgeServiceClient:
        return KnowledgeServiceClient(
            mode=ConnectionMode.DIRECT,
            hybrid_retriever=MockHybridRetriever(),
        )

    @pytest.mark.asyncio
    async def test_direct_hybrid_search(
        self, direct_client: KnowledgeServiceClient
    ) -> None:
        """Direct 모드 hybrid search 테스트"""
        results = await direct_client.hybrid_search(
            query="FastAPI 사용법",
            top_k=5,
            strategy="hybrid",
        )

        assert len(results) == 5
        assert all(isinstance(r, dict) for r in results)
        assert "chunk_id" in results[0]
        assert "content" in results[0]
        assert "score" in results[0]

    @pytest.mark.asyncio
    async def test_direct_keyword_search(
        self, direct_client: KnowledgeServiceClient
    ) -> None:
        """Direct 모드 keyword 검색 테스트"""
        results = await direct_client.hybrid_search(
            query="FastAPI",
            top_k=3,
            strategy="keyword",
        )

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_direct_semantic_search(
        self, direct_client: KnowledgeServiceClient
    ) -> None:
        """Direct 모드 semantic 검색 테스트"""
        results = await direct_client.hybrid_search(
            query="웹 프레임워크 설명",
            top_k=3,
            strategy="semantic",
        )

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_search_error_returns_empty(self) -> None:
        """검색 실패 시 빈 리스트 반환 테스트"""
        failing_retriever = MagicMock()
        failing_retriever.retrieve = AsyncMock(
            side_effect=Exception("Connection error")
        )

        client = KnowledgeServiceClient(
            mode=ConnectionMode.DIRECT,
            hybrid_retriever=failing_retriever,
        )

        results = await client.hybrid_search(query="test", top_k=5)
        assert results == []

    def test_health_check(
        self, direct_client: KnowledgeServiceClient
    ) -> None:
        """상태 점검 테스트"""
        health = direct_client.health_check()
        assert health["service"] == "KnowledgeServiceClient"
        assert health["mode"] == "direct"
        assert health["retriever_available"] is True


# ---------------------------------------------------------------------------
# Test: RetrieverAdapter
# ---------------------------------------------------------------------------

class TestRetrieverAdapter:
    """RetrieverAdapter 테스트"""

    @pytest.fixture
    def adapter(self) -> RetrieverAdapter:
        client = KnowledgeServiceClient(
            mode=ConnectionMode.DIRECT,
            hybrid_retriever=MockHybridRetriever(),
        )
        return RetrieverAdapter(
            client=client,
            default_top_k=10,
            default_strategy="hybrid",
        )

    @pytest.mark.asyncio
    async def test_retrieve_fn_signature(
        self, adapter: RetrieverAdapter
    ) -> None:
        """RetrieverNode.retrieve_fn 호환 시그니처 검증"""
        # RetrieverNode가 호출하는 정확한 시그니처
        results = await adapter.retrieve(
            query="FastAPI 사용법",
            top_k=5,
            strategy="hybrid",
        )

        assert len(results) == 5
        assert all(isinstance(r, dict) for r in results)
        assert "chunk_id" in results[0]
        assert "content" in results[0]
        assert "score" in results[0]

    @pytest.mark.asyncio
    async def test_as_retrieve_fn(self, adapter: RetrieverAdapter) -> None:
        """as_retrieve_fn() 반환값이 callable인지 확인"""
        fn = adapter.as_retrieve_fn()
        assert callable(fn)

        results = await fn(query="test", top_k=3, strategy="hybrid")
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_retrieve_with_retriever_node(
        self, adapter: RetrieverAdapter
    ) -> None:
        """RetrieverNode에 주입하여 동작 확인"""
        node = RetrieverNode(
            retrieve_fn=adapter.retrieve,
            top_k=5,
        )

        state = {
            "query": "FastAPI 사용법",
            "refined_query": "FastAPI 웹 프레임워크 사용법",
            "search_strategy": "hybrid",
            "steps": [],
            "retry_count": 0,
        }

        result = await node(state)

        assert "documents" in result
        assert len(result["documents"]) == 5
        assert "context" in result
        assert len(result["context"]) > 0
        assert "retriever:" in result["steps"][-1]

    def test_health_check(self, adapter: RetrieverAdapter) -> None:
        """상태 점검 테스트"""
        health = adapter.health_check()
        assert health["service"] == "RetrieverAdapter"
        assert health["client_mode"] == "direct"


# ---------------------------------------------------------------------------
# Test: RerankerAdapter
# ---------------------------------------------------------------------------

class TestRerankerAdapter:
    """RerankerAdapter 테스트"""

    @pytest.fixture
    def adapter(self) -> RerankerAdapter:
        return RerankerAdapter(
            reranker=MockBGEReranker(),
            default_top_k=5,
        )

    @pytest.mark.asyncio
    async def test_rerank(self, adapter: RerankerAdapter) -> None:
        """기본 리랭킹 테스트"""
        documents = [
            {"chunk_id": f"c{i}", "content": f"Document {i}", "score": 0.5}
            for i in range(10)
        ]

        results = await adapter.rerank(
            query="test query",
            documents=documents,
            top_k=5,
        )

        assert len(results) == 5
        # 리랭킹 점수가 내림차순인지 확인
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_rerank_empty_documents(
        self, adapter: RerankerAdapter
    ) -> None:
        """빈 문서 목록 리랭킹 테스트"""
        results = await adapter.rerank(
            query="test",
            documents=[],
        )
        assert results == []

    @pytest.mark.asyncio
    async def test_no_reranker_returns_original(self) -> None:
        """리랭커 없을 때 원본 순서 반환 테스트"""
        adapter = RerankerAdapter(reranker=None, client=None)

        documents = [
            {"chunk_id": "c1", "content": "Doc 1", "score": 0.9},
            {"chunk_id": "c2", "content": "Doc 2", "score": 0.8},
        ]

        results = await adapter.rerank(
            query="test",
            documents=documents,
            top_k=2,
        )

        assert len(results) == 2
        assert results[0]["chunk_id"] == "c1"

    def test_is_available(self, adapter: RerankerAdapter) -> None:
        """리랭킹 가능 여부 확인"""
        assert adapter.is_available is True

        empty_adapter = RerankerAdapter(reranker=None, client=None)
        assert empty_adapter.is_available is False


# ---------------------------------------------------------------------------
# Test: Bootstrap
# ---------------------------------------------------------------------------

class TestBootstrap:
    """파이프라인 부트스트랩 테스트"""

    def test_pipeline_config_defaults(self) -> None:
        """기본 설정 테스트"""
        config = PipelineConfig()

        assert config.connection_mode == ConnectionMode.DIRECT
        assert config.retrieval_top_k == 10
        assert config.max_retries == 2
        assert config.reranking_enabled is True
        assert config.llm_fallback_enabled is True

    def test_pipeline_config_custom(self) -> None:
        """커스텀 설정 테스트"""
        config = PipelineConfig(
            connection_mode="http",
            ks_base_url="http://custom:9000",
            retrieval_top_k=20,
            max_retries=3,
        )

        assert config.connection_mode == ConnectionMode.HTTP
        assert config.ks_base_url == "http://custom:9000"
        assert config.retrieval_top_k == 20
        assert config.max_retries == 3

    def test_bootstrap_creates_all_components(self) -> None:
        """부트스트랩이 모든 구성 요소를 생성하는지 확인"""
        config = PipelineConfig(
            connection_mode="direct",
            reranking_enabled=True,
        )

        components = bootstrap_rag_pipeline(
            config=config,
            llm_service=MockLLMService(),
            hybrid_retriever=MockHybridRetriever(),
            reranker=MockBGEReranker(),
        )

        assert isinstance(components, PipelineComponents)
        assert isinstance(components.workflow, RAGWorkflow)
        assert isinstance(components.llm_adapter, LLMAdapter)
        assert isinstance(components.ks_client, KnowledgeServiceClient)
        assert isinstance(components.retriever_adapter, RetrieverAdapter)
        assert isinstance(components.reranker_adapter, RerankerAdapter)

    def test_bootstrap_without_reranker(self) -> None:
        """리랭커 없이 부트스트랩 테스트"""
        components = bootstrap_rag_pipeline(
            llm_service=MockLLMService(),
            hybrid_retriever=MockHybridRetriever(),
            reranker=None,
        )

        assert components.reranker_adapter is None
        assert components.workflow is not None

    def test_health_check(self) -> None:
        """파이프라인 상태 점검 테스트"""
        components = bootstrap_rag_pipeline(
            llm_service=MockLLMService(),
            hybrid_retriever=MockHybridRetriever(),
        )

        health = components.health_check()

        assert health["service"] == "RAGPipeline"
        assert health["status"] == "healthy"
        assert "llm_adapter" in health
        assert "ks_client" in health
        assert "retriever_adapter" in health
        assert "workflow" in health


# ---------------------------------------------------------------------------
# Test: Full Pipeline E2E (with mocks)
# ---------------------------------------------------------------------------

class TestFullPipelineE2E:
    """RAG 파이프라인 E2E 통합 테스트 (모의 객체 사용)"""

    @pytest.fixture
    def pipeline(self) -> PipelineComponents:
        return bootstrap_rag_pipeline(
            llm_service=MockLLMService(),
            hybrid_retriever=MockHybridRetriever(),
            reranker=MockBGEReranker(),
        )

    @pytest.mark.asyncio
    async def test_full_pipeline_invoke(
        self, pipeline: PipelineComponents
    ) -> None:
        """전체 파이프라인 실행 테스트"""
        result = await pipeline.workflow.invoke(
            query="FastAPI 사용법은 무엇인가요?"
        )

        # 상태 검증
        assert "query" in result
        assert result["query"] == "FastAPI 사용법은 무엇인가요?"

        # Planner 출력 검증
        assert "search_strategy" in result
        assert result["search_strategy"] in ("keyword", "semantic", "hybrid")
        assert "refined_query" in result

        # Retriever 출력 검증
        assert "documents" in result
        assert len(result["documents"]) > 0
        assert "context" in result
        assert len(result["context"]) > 0

        # Generator 출력 검증
        assert "answer" in result
        assert len(result["answer"]) > 0

        # Validator 출력 검증
        assert "validation_result" in result

        # Steps 추적
        assert "steps" in result
        steps = result["steps"]
        assert any("planner:" in s for s in steps)
        assert any("retriever:" in s for s in steps)
        assert any("generator:" in s for s in steps)
        assert any("validator:" in s for s in steps)

    @pytest.mark.asyncio
    async def test_full_pipeline_stream(
        self, pipeline: PipelineComponents
    ) -> None:
        """전체 파이프라인 스트리밍 실행 테스트"""
        events = []
        async for event in pipeline.workflow.astream(
            query="FastAPI 사용법은?"
        ):
            events.append(event)

        assert len(events) > 0
        # 각 노드에서 이벤트가 발생해야 함
        all_keys = set()
        for event in events:
            all_keys.update(event.keys())

        # 최소한 planner, retriever, generator, validator 노드가 실행
        assert len(events) >= 4

    @pytest.mark.asyncio
    async def test_empty_query_raises(
        self, pipeline: PipelineComponents
    ) -> None:
        """빈 쿼리 예외 테스트"""
        with pytest.raises(ValueError, match="Query must not be empty"):
            await pipeline.workflow.invoke(query="")

    @pytest.mark.asyncio
    async def test_pipeline_with_conversation_history(
        self, pipeline: PipelineComponents
    ) -> None:
        """대화 이력 포함 파이프라인 테스트"""
        history = [
            {"role": "user", "content": "FastAPI란?"},
            {"role": "assistant", "content": "FastAPI는 웹 프레임워크입니다."},
        ]

        result = await pipeline.workflow.invoke(
            query="더 자세히 설명해줘",
            conversation_history=history,
        )

        assert result["answer"]
        assert result["conversation_history"] == history


# ---------------------------------------------------------------------------
# Test: Error Handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    """에러 핸들링 테스트"""

    @pytest.mark.asyncio
    async def test_retriever_failure_graceful(self) -> None:
        """검색 실패 시 graceful degradation"""
        failing_retriever = MagicMock()
        failing_retriever.retrieve = AsyncMock(
            side_effect=Exception("ES connection failed")
        )
        failing_retriever.retrieve_by_source = AsyncMock(
            side_effect=Exception("ES connection failed")
        )

        client = KnowledgeServiceClient(
            mode=ConnectionMode.DIRECT,
            hybrid_retriever=failing_retriever,
        )
        adapter = RetrieverAdapter(client=client)
        node = RetrieverNode(retrieve_fn=adapter.retrieve, top_k=5)

        state = {
            "query": "test",
            "refined_query": "test",
            "search_strategy": "hybrid",
            "steps": [],
            "retry_count": 0,
        }

        result = await node(state)

        # 에러가 발생해도 상태는 반환됨
        assert "documents" in result
        assert result["documents"] == []
        # 에러 메시지 없음 (빈 리스트 반환은 에러가 아님)

    @pytest.mark.asyncio
    async def test_llm_failure_with_fallback(self) -> None:
        """LLM 실패 시 폴백 동작"""
        failing_service = MagicMock()
        failing_service.generate_with_messages = AsyncMock(
            side_effect=Exception("Rate limit exceeded")
        )

        adapter = LLMAdapter(
            llm_service=failing_service,
            fallback_enabled=True,
        )

        # Generator 폴백: 오류 안내
        response = await adapter.call(
            system_prompt="답변을 생성합니다.",
            user_message="질문",
        )
        assert "오류" in response or "장애" in response
