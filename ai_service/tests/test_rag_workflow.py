"""
RAG Workflow 종합 테스트

STORY-033: LangGraph 기반 RAG 워크플로우 구현

테스트 범주:
1. AgentState (RAGState) 테스트 - 상태 생성/검증/직렬화
2. PlannerNode 테스트 - 전략 선택, 쿼리 정제, 에러 처리
3. RetrieverNode 테스트 - 검색 수행, 가중치 조정, 빈 결과
4. GeneratorNode 테스트 - 답변 생성, 출처 추출, 스트리밍
5. ValidatorNode 테스트 - 통과/실패 시나리오, 임계값, 재시도
6. RAGWorkflow 테스트 - 전체 파이프라인, 스트리밍, 에러 전파, 재시도
7. 통합 테스트 - Mock 서비스와 end-to-end 실행

총 50+ 테스트 케이스
"""

import asyncio
import json
import re
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_service.src.workflows.nodes.generator import (
    GENERATOR_SYSTEM_PROMPT,
    GENERATOR_USER_TEMPLATE,
    GeneratorNode,
)
from ai_service.src.workflows.nodes.planner import (
    PLANNER_SYSTEM_PROMPT,
    PlannerNode,
)
from ai_service.src.workflows.nodes.retriever import RetrieverNode
from ai_service.src.workflows.nodes.validator import (
    VALIDATOR_SYSTEM_PROMPT,
    ValidatorNode,
)
from ai_service.src.workflows.rag_workflow import RAGWorkflow, _should_retry
from ai_service.src.workflows.state import RAGState, ValidationResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(**overrides: Any) -> RAGState:
    """테스트용 기본 RAGState 생성"""
    state: RAGState = {
        "query": "FastAPI 사용법",
        "conversation_history": [],
        "search_strategy": "hybrid",
        "refined_query": "FastAPI 사용법 가이드",
        "documents": [],
        "context": "",
        "answer": "",
        "sources": [],
        "steps": [],
        "error": None,
        "validation_result": None,
        "retry_count": 0,
        "max_retries": 2,
    }
    state.update(overrides)
    return state


def _make_documents(count: int = 5) -> List[Dict[str, Any]]:
    """테스트용 문서 목록 생성"""
    return [
        {
            "chunk_id": f"chunk-{i}",
            "document_id": f"doc-{i}",
            "content": f"문서 {i}의 내용입니다. FastAPI는 Python 웹 프레임워크입니다. "
            f"비동기 처리를 지원하며 자동 API 문서를 생성합니다.",
            "score": round(0.95 - (i * 0.1), 2),
            "source": "vector",
            "metadata": {"page": i},
        }
        for i in range(count)
    ]


def _make_context(documents: Optional[List[Dict[str, Any]]] = None) -> str:
    """테스트용 컨텍스트 문자열 생성"""
    docs = documents or _make_documents(3)
    parts = []
    for i, doc in enumerate(docs):
        parts.append(
            f"[{i + 1}] (ID: {doc['chunk_id']}, Source: {doc['source']})\n"
            f"{doc['content']}"
        )
    return "\n\n".join(parts)


async def _mock_llm_planner(system_prompt: str, user_message: str) -> str:
    """Mock LLM: Planner 응답"""
    return json.dumps({
        "search_strategy": "hybrid",
        "refined_query": "FastAPI Python 웹 프레임워크 사용법",
        "reasoning": "기술 질문이므로 hybrid 전략 선택",
    })


async def _mock_llm_generator(system_prompt: str, user_message: str) -> str:
    """Mock LLM: Generator 응답"""
    return (
        "FastAPI는 Python 기반의 고성능 웹 프레임워크입니다. "
        "비동기 처리를 지원하며 자동으로 API 문서를 생성합니다. [1] [2]"
    )


async def _mock_llm_validator_pass(
    system_prompt: str, user_message: str
) -> str:
    """Mock LLM: Validator 통과 응답"""
    return json.dumps({
        "faithfulness_score": 0.92,
        "relevance_score": 0.88,
        "is_valid": True,
        "feedback": "답변이 컨텍스트에 충실하고 질문에 적절합니다.",
    })


async def _mock_llm_validator_fail(
    system_prompt: str, user_message: str
) -> str:
    """Mock LLM: Validator 실패 응답"""
    return json.dumps({
        "faithfulness_score": 0.3,
        "relevance_score": 0.4,
        "is_valid": False,
        "feedback": "답변이 컨텍스트에 충실하지 않습니다.",
    })


async def _mock_retrieve(
    query: str, top_k: int = 10, strategy: str = "hybrid"
) -> List[Dict[str, Any]]:
    """Mock 검색 함수"""
    return _make_documents(min(top_k, 5))


# ---------------------------------------------------------------------------
# 1. RAGState 테스트
# ---------------------------------------------------------------------------


class TestRAGState:
    """RAGState TypedDict 테스트"""

    def test_create_basic_state(self):
        """기본 상태 생성"""
        state = _make_state()
        assert state["query"] == "FastAPI 사용법"
        assert state["search_strategy"] == "hybrid"
        assert state["retry_count"] == 0

    def test_create_state_with_overrides(self):
        """오버라이드로 상태 생성"""
        state = _make_state(
            query="다른 질문",
            search_strategy="keyword",
            retry_count=1,
        )
        assert state["query"] == "다른 질문"
        assert state["search_strategy"] == "keyword"
        assert state["retry_count"] == 1

    def test_state_documents_field(self):
        """문서 필드 저장"""
        docs = _make_documents(3)
        state = _make_state(documents=docs)
        assert len(state["documents"]) == 3
        assert state["documents"][0]["chunk_id"] == "chunk-0"

    def test_state_validation_result(self):
        """검증 결과 저장"""
        validation: ValidationResult = {
            "is_valid": True,
            "faithfulness_score": 0.9,
            "relevance_score": 0.85,
            "feedback": "통과",
        }
        state = _make_state(validation_result=validation)
        assert state["validation_result"]["is_valid"] is True

    def test_state_steps_tracking(self):
        """단계 기록 추적"""
        state = _make_state(steps=["planner:strategy=hybrid", "retriever:docs=5"])
        assert len(state["steps"]) == 2

    def test_state_error_field(self):
        """에러 필드"""
        state = _make_state(error="Something went wrong")
        assert state["error"] == "Something went wrong"

    def test_state_serializable(self):
        """JSON 직렬화 가능"""
        state = _make_state()
        serialized = json.dumps(state)
        deserialized = json.loads(serialized)
        assert deserialized["query"] == "FastAPI 사용법"

    def test_state_conversation_history(self):
        """대화 이력 저장"""
        history = [
            {"role": "user", "content": "이전 질문"},
            {"role": "assistant", "content": "이전 답변"},
        ]
        state = _make_state(conversation_history=history)
        assert len(state["conversation_history"]) == 2


# ---------------------------------------------------------------------------
# 2. PlannerNode 테스트
# ---------------------------------------------------------------------------


class TestPlannerNode:
    """PlannerNode 테스트"""

    @pytest.mark.asyncio
    async def test_planner_with_llm(self):
        """LLM 기반 전략 결정"""
        planner = PlannerNode(llm_call=_mock_llm_planner)
        state = _make_state()

        result = await planner(state)

        assert result["search_strategy"] == "hybrid"
        assert "FastAPI" in result["refined_query"]
        assert any("planner" in s for s in result["steps"])

    @pytest.mark.asyncio
    async def test_planner_rule_based_keyword(self):
        """규칙 기반: 키워드 전략"""
        planner = PlannerNode()  # LLM 없음
        state = _make_state(query="FileNotFoundError 에러 코드 해결")

        result = await planner(state)

        assert result["search_strategy"] in ("keyword", "hybrid")
        assert result["refined_query"]

    @pytest.mark.asyncio
    async def test_planner_rule_based_semantic(self):
        """규칙 기반: 의미 전략"""
        planner = PlannerNode()
        state = _make_state(query="마이크로서비스 아키텍처란 무엇인가 설명해주세요")

        result = await planner(state)

        assert result["search_strategy"] in ("semantic", "hybrid")

    @pytest.mark.asyncio
    async def test_planner_rule_based_hybrid(self):
        """규칙 기반: 하이브리드 전략"""
        planner = PlannerNode()
        state = _make_state(query="FastAPI API 사용 방법 설명")

        result = await planner(state)

        assert result["search_strategy"] == "hybrid"

    @pytest.mark.asyncio
    async def test_planner_empty_query(self):
        """빈 쿼리 처리"""
        planner = PlannerNode()
        state = _make_state(query="")

        result = await planner(state)

        assert result["error"] == "Empty query provided"
        assert result["search_strategy"] == "hybrid"

    @pytest.mark.asyncio
    async def test_planner_whitespace_query(self):
        """공백만 있는 쿼리"""
        planner = PlannerNode()
        state = _make_state(query="   ")

        result = await planner(state)

        assert result["error"] == "Empty query provided"

    @pytest.mark.asyncio
    async def test_planner_llm_error_fallback(self):
        """LLM 호출 실패 시 폴백"""
        async def failing_llm(system_prompt: str, user_message: str) -> str:
            raise RuntimeError("LLM API error")

        planner = PlannerNode(llm_call=failing_llm)
        state = _make_state()

        result = await planner(state)

        assert result["search_strategy"] == "hybrid"  # default
        assert result["error"] is not None

    @pytest.mark.asyncio
    async def test_planner_invalid_json_response(self):
        """LLM이 잘못된 JSON 반환 시"""
        async def bad_json_llm(system_prompt: str, user_message: str) -> str:
            return "This is not JSON at all"

        planner = PlannerNode(llm_call=bad_json_llm)
        state = _make_state()

        result = await planner(state)

        # JSON 파싱 실패 -> 에러와 함께 기본값
        assert result["search_strategy"] == "hybrid"
        assert result["error"] is not None

    @pytest.mark.asyncio
    async def test_planner_custom_default_strategy(self):
        """사용자 지정 기본 전략"""
        planner = PlannerNode(default_strategy="semantic")
        state = _make_state(query="")

        result = await planner(state)

        assert result["search_strategy"] == "semantic"

    @pytest.mark.asyncio
    async def test_planner_invalid_strategy_from_llm(self):
        """LLM이 잘못된 전략을 반환한 경우"""
        async def invalid_strategy_llm(
            system_prompt: str, user_message: str
        ) -> str:
            return json.dumps({
                "search_strategy": "invalid_strategy",
                "refined_query": "test",
                "reasoning": "test",
            })

        planner = PlannerNode(llm_call=invalid_strategy_llm)
        state = _make_state()

        result = await planner(state)

        assert result["search_strategy"] == "hybrid"  # fallback to default

    @pytest.mark.asyncio
    async def test_planner_json_in_code_fence(self):
        """LLM 응답이 코드 펜스로 감싸진 경우"""
        async def code_fence_llm(
            system_prompt: str, user_message: str
        ) -> str:
            return '```json\n{"search_strategy": "keyword", "refined_query": "test", "reasoning": "test"}\n```'

        planner = PlannerNode(llm_call=code_fence_llm)
        state = _make_state()

        result = await planner(state)

        assert result["search_strategy"] == "keyword"

    @pytest.mark.asyncio
    async def test_planner_preserves_existing_steps(self):
        """기존 steps를 보존"""
        planner = PlannerNode()
        state = _make_state(steps=["existing_step"])

        result = await planner(state)

        assert "existing_step" in result["steps"]
        assert len(result["steps"]) >= 2


# ---------------------------------------------------------------------------
# 3. RetrieverNode 테스트
# ---------------------------------------------------------------------------


class TestRetrieverNode:
    """RetrieverNode 테스트"""

    @pytest.mark.asyncio
    async def test_retrieve_with_function(self):
        """검색 함수로 문서 가져오기"""
        retriever = RetrieverNode(retrieve_fn=_mock_retrieve, top_k=5)
        state = _make_state(refined_query="FastAPI Python")

        result = await retriever(state)

        assert len(result["documents"]) == 5
        assert result["context"] != ""
        assert "retriever" in result["steps"][0]

    @pytest.mark.asyncio
    async def test_retrieve_empty_query(self):
        """빈 쿼리 검색"""
        retriever = RetrieverNode(retrieve_fn=_mock_retrieve)
        state = _make_state(refined_query="", query="")

        result = await retriever(state)

        assert result["documents"] == []
        assert result["error"] == "Empty query for retrieval"

    @pytest.mark.asyncio
    async def test_retrieve_no_function(self):
        """검색 함수 미설정"""
        retriever = RetrieverNode()
        state = _make_state()

        result = await retriever(state)

        assert result["documents"] == []

    @pytest.mark.asyncio
    async def test_retrieve_error_handling(self):
        """검색 중 에러 처리"""
        async def failing_retrieve(
            query: str, top_k: int = 10, strategy: str = "hybrid"
        ):
            raise ConnectionError("ES connection failed")

        retriever = RetrieverNode(retrieve_fn=failing_retrieve)
        state = _make_state()

        result = await retriever(state)

        assert result["documents"] == []
        assert "Retrieval error" in result["error"]

    @pytest.mark.asyncio
    async def test_retrieve_uses_refined_query(self):
        """refined_query를 우선 사용"""
        called_with = {}

        async def capture_retrieve(
            query: str, top_k: int = 10, strategy: str = "hybrid"
        ):
            called_with["query"] = query
            called_with["strategy"] = strategy
            return _make_documents(2)

        retriever = RetrieverNode(retrieve_fn=capture_retrieve)
        state = _make_state(
            query="original query",
            refined_query="refined query",
            search_strategy="keyword",
        )

        await retriever(state)

        assert called_with["query"] == "refined query"
        assert called_with["strategy"] == "keyword"

    @pytest.mark.asyncio
    async def test_retrieve_falls_back_to_query(self):
        """refined_query가 없으면 query 사용"""
        called_with = {}

        async def capture_retrieve(
            query: str, top_k: int = 10, strategy: str = "hybrid"
        ):
            called_with["query"] = query
            return _make_documents(1)

        retriever = RetrieverNode(retrieve_fn=capture_retrieve)
        state = _make_state(query="fallback query", refined_query="")

        await retriever(state)

        assert called_with["query"] == "fallback query"

    @pytest.mark.asyncio
    async def test_retrieve_normalizes_search_result_objects(self):
        """SearchResult-like 객체를 딕셔너리로 정규화"""

        class MockSearchResult:
            def __init__(self):
                self.chunk_id = "sr-1"
                self.document_id = "doc-1"
                self.content = "Search result content"
                self.score = 0.88
                self.source = "vector"
                self.metadata = {"page": 1}

        async def obj_retrieve(
            query: str, top_k: int = 10, strategy: str = "hybrid"
        ):
            return [MockSearchResult()]

        retriever = RetrieverNode(retrieve_fn=obj_retrieve)
        state = _make_state()

        result = await retriever(state)

        assert len(result["documents"]) == 1
        assert result["documents"][0]["chunk_id"] == "sr-1"
        assert result["documents"][0]["content"] == "Search result content"

    @pytest.mark.asyncio
    async def test_retrieve_context_length_limit(self):
        """컨텍스트 최대 길이 제한"""
        async def long_retrieve(
            query: str, top_k: int = 10, strategy: str = "hybrid"
        ):
            return [
                {
                    "chunk_id": f"chunk-{i}",
                    "content": "A" * 5000,
                    "score": 0.9,
                    "source": "vector",
                }
                for i in range(10)
            ]

        retriever = RetrieverNode(
            retrieve_fn=long_retrieve, max_context_length=1000
        )
        state = _make_state()

        result = await retriever(state)

        assert len(result["context"]) <= 1100  # some margin for truncation marker

    @pytest.mark.asyncio
    async def test_retrieve_no_documents_sets_error(self):
        """문서 없으면 에러 설정"""
        async def empty_retrieve(
            query: str, top_k: int = 10, strategy: str = "hybrid"
        ):
            return []

        retriever = RetrieverNode(retrieve_fn=empty_retrieve)
        state = _make_state()

        result = await retriever(state)

        assert result["documents"] == []
        assert result["error"] == "No documents found"

    @pytest.mark.asyncio
    async def test_retrieve_context_format(self):
        """컨텍스트 형식 검증"""
        retriever = RetrieverNode(retrieve_fn=_mock_retrieve, top_k=3)
        state = _make_state()

        result = await retriever(state)

        context = result["context"]
        assert "[1]" in context
        assert "chunk-0" in context


# ---------------------------------------------------------------------------
# 4. GeneratorNode 테스트
# ---------------------------------------------------------------------------


class TestGeneratorNode:
    """GeneratorNode 테스트"""

    @pytest.mark.asyncio
    async def test_generate_with_llm(self):
        """LLM 기반 답변 생성"""
        generator = GeneratorNode(llm_call=_mock_llm_generator)
        docs = _make_documents(3)
        state = _make_state(
            context=_make_context(docs),
            documents=docs,
        )

        result = await generator(state)

        assert "FastAPI" in result["answer"]
        assert len(result["sources"]) > 0
        assert any("generator" in s for s in result["steps"])

    @pytest.mark.asyncio
    async def test_generate_no_context(self):
        """컨텍스트 없이 생성"""
        generator = GeneratorNode(llm_call=_mock_llm_generator)
        state = _make_state(context="")

        result = await generator(state)

        assert "검색된 문서가 없어" in result["answer"]
        assert result["sources"] == []

    @pytest.mark.asyncio
    async def test_generate_fallback_no_llm(self):
        """LLM 없이 폴백 답변"""
        generator = GeneratorNode()
        docs = _make_documents(3)
        state = _make_state(
            context=_make_context(docs),
            documents=docs,
        )

        result = await generator(state)

        assert "검색 결과" in result["answer"]

    @pytest.mark.asyncio
    async def test_generate_error_handling(self):
        """생성 중 에러 처리"""
        async def failing_llm(system_prompt: str, user_message: str) -> str:
            raise RuntimeError("LLM timeout")

        generator = GeneratorNode(llm_call=failing_llm)
        state = _make_state(
            context="Some context",
            documents=_make_documents(1),
        )

        result = await generator(state)

        assert "오류" in result["answer"]
        assert result["error"] is not None

    @pytest.mark.asyncio
    async def test_generate_source_extraction_with_refs(self):
        """출처 참조 추출 ([1], [2])"""
        async def llm_with_refs(system_prompt: str, user_message: str) -> str:
            return "답변입니다 [1]. 추가 내용입니다 [3]."

        generator = GeneratorNode(llm_call=llm_with_refs)
        docs = _make_documents(5)
        state = _make_state(
            context=_make_context(docs),
            documents=docs,
        )

        result = await generator(state)

        source_indices = [s["index"] for s in result["sources"]]
        assert 1 in source_indices
        assert 3 in source_indices

    @pytest.mark.asyncio
    async def test_generate_source_extraction_no_refs(self):
        """출처 참조 없으면 상위 문서 포함"""
        async def llm_no_refs(system_prompt: str, user_message: str) -> str:
            return "답변입니다. 참조 번호 없이."

        generator = GeneratorNode(llm_call=llm_no_refs)
        docs = _make_documents(5)
        state = _make_state(
            context=_make_context(docs),
            documents=docs,
        )

        result = await generator(state)

        # 상위 3개 문서가 기본 출처로 포함
        assert len(result["sources"]) == 3

    @pytest.mark.asyncio
    async def test_generate_streaming(self):
        """스트리밍 답변 생성"""

        async def mock_stream(system_prompt: str, user_message: str):
            tokens = ["FastAPI", "는 ", "Python ", "프레임워크", "입니다."]
            for token in tokens:
                yield token

        generator = GeneratorNode(
            llm_call=_mock_llm_generator,
            llm_stream=mock_stream,
        )
        docs = _make_documents(3)
        state = _make_state(
            context=_make_context(docs),
            documents=docs,
        )

        tokens = []
        async for token in generator.stream(state):
            tokens.append(token)

        assert len(tokens) == 5
        assert "".join(tokens) == "FastAPI는 Python 프레임워크입니다."

    @pytest.mark.asyncio
    async def test_generate_streaming_no_stream_fn(self):
        """스트리밍 함수 미설정 시 전체 답변 반환"""
        generator = GeneratorNode(llm_call=_mock_llm_generator)
        docs = _make_documents(3)
        state = _make_state(
            context=_make_context(docs),
            documents=docs,
        )

        tokens = []
        async for token in generator.stream(state):
            tokens.append(token)

        assert len(tokens) == 1
        assert "FastAPI" in tokens[0]

    @pytest.mark.asyncio
    async def test_generate_fallback_no_documents(self):
        """LLM 없고 문서도 없는 경우"""
        generator = GeneratorNode()
        state = _make_state(context="some context", documents=[])

        result = await generator(state)

        assert "관련 문서를 찾을 수 없습니다" in result["answer"]


# ---------------------------------------------------------------------------
# 5. ValidatorNode 테스트
# ---------------------------------------------------------------------------


class TestValidatorNode:
    """ValidatorNode 테스트"""

    @pytest.mark.asyncio
    async def test_validator_pass(self):
        """검증 통과"""
        validator = ValidatorNode(llm_call=_mock_llm_validator_pass)
        state = _make_state(
            context="FastAPI는 Python 프레임워크입니다.",
            answer="FastAPI는 Python 기반 웹 프레임워크입니다.",
        )

        result = await validator(state)

        assert result["validation_result"]["is_valid"] is True
        assert result["validation_result"]["faithfulness_score"] >= 0.7
        assert result["validation_result"]["relevance_score"] >= 0.7

    @pytest.mark.asyncio
    async def test_validator_fail(self):
        """검증 실패"""
        validator = ValidatorNode(llm_call=_mock_llm_validator_fail)
        state = _make_state(
            context="FastAPI 관련 문서",
            answer="완전히 다른 답변",
        )

        result = await validator(state)

        assert result["validation_result"]["is_valid"] is False

    @pytest.mark.asyncio
    async def test_validator_fail_increments_retry(self):
        """검증 실패 시 retry_count 증가"""
        validator = ValidatorNode(llm_call=_mock_llm_validator_fail)
        state = _make_state(retry_count=0)

        result = await validator(state)

        assert result["retry_count"] == 1

    @pytest.mark.asyncio
    async def test_validator_pass_no_retry_increment(self):
        """검증 통과 시 retry_count 미증가"""
        validator = ValidatorNode(llm_call=_mock_llm_validator_pass)
        state = _make_state(
            context="Test context",
            answer="Test answer",
            retry_count=0,
        )

        result = await validator(state)

        assert "retry_count" not in result  # not updated

    @pytest.mark.asyncio
    async def test_validator_empty_answer(self):
        """빈 답변"""
        validator = ValidatorNode()
        state = _make_state(answer="")

        result = await validator(state)

        assert result["validation_result"]["is_valid"] is False
        assert result["retry_count"] == 1

    @pytest.mark.asyncio
    async def test_validator_rule_based(self):
        """규칙 기반 검증 (LLM 없음)"""
        validator = ValidatorNode()
        state = _make_state(
            query="FastAPI Python 사용법",
            context="FastAPI는 Python 웹 프레임워크입니다. 비동기 처리를 지원합니다.",
            answer="FastAPI는 Python 기반의 웹 프레임워크이며 비동기 처리를 지원합니다.",
        )

        result = await validator(state)

        vr = result["validation_result"]
        assert vr["faithfulness_score"] > 0
        assert vr["relevance_score"] > 0

    @pytest.mark.asyncio
    async def test_validator_error_handling(self):
        """검증 중 에러"""
        async def failing_llm(system_prompt: str, user_message: str) -> str:
            raise TimeoutError("LLM timeout")

        validator = ValidatorNode(llm_call=failing_llm)
        state = _make_state(
            context="ctx", answer="ans", retry_count=0,
        )

        result = await validator(state)

        assert result["validation_result"]["is_valid"] is False
        assert result["error"] is not None
        assert result["retry_count"] == 1

    @pytest.mark.asyncio
    async def test_validator_custom_thresholds(self):
        """사용자 지정 임계값"""
        async def mid_score_llm(system_prompt: str, user_message: str) -> str:
            return json.dumps({
                "faithfulness_score": 0.6,
                "relevance_score": 0.6,
                "is_valid": True,
                "feedback": "보통",
            })

        # 높은 임계값
        strict_validator = ValidatorNode(
            llm_call=mid_score_llm,
            faithfulness_threshold=0.8,
            relevance_threshold=0.8,
        )
        state = _make_state(context="ctx", answer="ans")
        result = await strict_validator(state)
        assert result["validation_result"]["is_valid"] is False

        # 낮은 임계값
        lenient_validator = ValidatorNode(
            llm_call=mid_score_llm,
            faithfulness_threshold=0.5,
            relevance_threshold=0.5,
        )
        result = await lenient_validator(state)
        assert result["validation_result"]["is_valid"] is True

    @pytest.mark.asyncio
    async def test_validator_score_clamping(self):
        """점수 범위 클램핑 (0~1)"""
        async def extreme_score_llm(
            system_prompt: str, user_message: str
        ) -> str:
            return json.dumps({
                "faithfulness_score": 1.5,
                "relevance_score": -0.3,
                "is_valid": True,
                "feedback": "극단값",
            })

        validator = ValidatorNode(llm_call=extreme_score_llm)
        state = _make_state(context="ctx", answer="ans")

        result = await validator(state)

        vr = result["validation_result"]
        assert vr["faithfulness_score"] == 1.0
        assert vr["relevance_score"] == 0.0

    @pytest.mark.asyncio
    async def test_validator_json_code_fence(self):
        """코드 펜스 응답 파싱"""
        async def code_fence_llm(
            system_prompt: str, user_message: str
        ) -> str:
            return '```json\n{"faithfulness_score": 0.85, "relevance_score": 0.9, "is_valid": true, "feedback": "Good"}\n```'

        validator = ValidatorNode(llm_call=code_fence_llm)
        state = _make_state(context="ctx", answer="ans")

        result = await validator(state)

        assert result["validation_result"]["faithfulness_score"] == 0.85


# ---------------------------------------------------------------------------
# 6. _should_retry 라우팅 함수 테스트
# ---------------------------------------------------------------------------


class TestShouldRetry:
    """조건부 분기 함수 테스트"""

    def test_pass_goes_to_end(self):
        """검증 통과 -> END"""
        state = _make_state(
            validation_result={
                "is_valid": True,
                "faithfulness_score": 0.9,
                "relevance_score": 0.9,
                "feedback": "OK",
            },
            retry_count=0,
            max_retries=2,
        )
        assert _should_retry(state) == "__end__"

    def test_fail_retries(self):
        """검증 실패 + 재시도 가능 -> retriever"""
        state = _make_state(
            validation_result={
                "is_valid": False,
                "faithfulness_score": 0.3,
                "relevance_score": 0.4,
                "feedback": "Fail",
            },
            retry_count=0,
            max_retries=2,
        )
        assert _should_retry(state) == "retriever"

    def test_max_retries_reached_goes_to_end(self):
        """최대 재시도 도달 -> END"""
        state = _make_state(
            validation_result={
                "is_valid": False,
                "faithfulness_score": 0.3,
                "relevance_score": 0.4,
                "feedback": "Fail",
            },
            retry_count=2,
            max_retries=2,
        )
        assert _should_retry(state) == "__end__"

    def test_no_validation_result_retries(self):
        """검증 결과 없음 -> retriever (재시도)"""
        state = _make_state(
            validation_result=None,
            retry_count=0,
            max_retries=2,
        )
        assert _should_retry(state) == "retriever"

    def test_retry_count_equals_max(self):
        """retry_count == max_retries -> END"""
        state = _make_state(
            validation_result={
                "is_valid": False,
                "faithfulness_score": 0.5,
                "relevance_score": 0.5,
                "feedback": "Moderate",
            },
            retry_count=3,
            max_retries=3,
        )
        assert _should_retry(state) == "__end__"


# ---------------------------------------------------------------------------
# 7. RAGWorkflow 테스트
# ---------------------------------------------------------------------------


class TestRAGWorkflow:
    """RAGWorkflow 종합 테스트"""

    @pytest.mark.asyncio
    async def test_full_pipeline_pass(self):
        """전체 파이프라인 실행 (검증 통과)"""
        workflow = RAGWorkflow(
            planner=PlannerNode(llm_call=_mock_llm_planner),
            retriever=RetrieverNode(retrieve_fn=_mock_retrieve, top_k=5),
            generator=GeneratorNode(llm_call=_mock_llm_generator),
            validator=ValidatorNode(llm_call=_mock_llm_validator_pass),
            max_retries=2,
        )

        result = await workflow.invoke("FastAPI 사용법")

        assert result["answer"] != ""
        assert result["search_strategy"] == "hybrid"
        assert len(result["documents"]) > 0
        assert result["validation_result"]["is_valid"] is True
        assert result["retry_count"] == 0

    @pytest.mark.asyncio
    async def test_full_pipeline_fail_with_retry(self):
        """전체 파이프라인 - 검증 실패 후 재시도"""
        call_count = {"validator": 0}

        async def validator_fails_then_passes(
            system_prompt: str, user_message: str
        ) -> str:
            call_count["validator"] += 1
            if call_count["validator"] <= 1:
                return json.dumps({
                    "faithfulness_score": 0.3,
                    "relevance_score": 0.4,
                    "is_valid": False,
                    "feedback": "부족",
                })
            return json.dumps({
                "faithfulness_score": 0.9,
                "relevance_score": 0.85,
                "is_valid": True,
                "feedback": "통과",
            })

        workflow = RAGWorkflow(
            planner=PlannerNode(llm_call=_mock_llm_planner),
            retriever=RetrieverNode(retrieve_fn=_mock_retrieve, top_k=5),
            generator=GeneratorNode(llm_call=_mock_llm_generator),
            validator=ValidatorNode(llm_call=validator_fails_then_passes),
            max_retries=2,
        )

        result = await workflow.invoke("FastAPI 사용법")

        assert result["validation_result"]["is_valid"] is True
        assert result["retry_count"] == 1  # 1회 실패 후 재시도

    @pytest.mark.asyncio
    async def test_full_pipeline_max_retries_exhausted(self):
        """최대 재시도 초과 시 종료"""
        workflow = RAGWorkflow(
            planner=PlannerNode(llm_call=_mock_llm_planner),
            retriever=RetrieverNode(retrieve_fn=_mock_retrieve, top_k=5),
            generator=GeneratorNode(llm_call=_mock_llm_generator),
            validator=ValidatorNode(llm_call=_mock_llm_validator_fail),
            max_retries=2,
        )

        result = await workflow.invoke("FastAPI 사용법")

        # 2회 재시도 후 종료 (최초 1 + 재시도 2 = validator 3회)
        assert result["validation_result"]["is_valid"] is False
        assert result["retry_count"] >= 2

    @pytest.mark.asyncio
    async def test_invoke_empty_query_raises(self):
        """빈 쿼리 시 ValueError"""
        workflow = RAGWorkflow()

        with pytest.raises(ValueError, match="Query must not be empty"):
            await workflow.invoke("")

    @pytest.mark.asyncio
    async def test_invoke_whitespace_query_raises(self):
        """공백 쿼리 시 ValueError"""
        workflow = RAGWorkflow()

        with pytest.raises(ValueError, match="Query must not be empty"):
            await workflow.invoke("   ")

    @pytest.mark.asyncio
    async def test_streaming_execution(self):
        """스트리밍 실행"""
        workflow = RAGWorkflow(
            planner=PlannerNode(llm_call=_mock_llm_planner),
            retriever=RetrieverNode(retrieve_fn=_mock_retrieve, top_k=3),
            generator=GeneratorNode(llm_call=_mock_llm_generator),
            validator=ValidatorNode(llm_call=_mock_llm_validator_pass),
            max_retries=0,
        )

        events = []
        async for event in workflow.astream("FastAPI 사용법"):
            events.append(event)

        assert len(events) > 0
        # 각 노드의 출력이 이벤트로 나옴
        node_names = set()
        for event in events:
            node_names.update(event.keys())
        assert "planner" in node_names or "retriever" in node_names

    @pytest.mark.asyncio
    async def test_stream_empty_query_raises(self):
        """스트리밍 빈 쿼리 시 ValueError"""
        workflow = RAGWorkflow()

        with pytest.raises(ValueError):
            async for _ in workflow.astream(""):
                pass

    @pytest.mark.asyncio
    async def test_workflow_default_nodes(self):
        """기본 노드로 워크플로우 생성"""
        workflow = RAGWorkflow()

        assert workflow.planner is not None
        assert workflow.retriever is not None
        assert workflow.generator is not None
        assert workflow.validator is not None

    def test_graph_info(self):
        """그래프 정보 조회"""
        workflow = RAGWorkflow(max_retries=3)

        info = workflow.get_graph_info()

        assert info["name"] == "RAGWorkflow"
        assert "planner" in info["nodes"]
        assert "retriever" in info["nodes"]
        assert "generator" in info["nodes"]
        assert "validator" in info["nodes"]
        assert info["max_retries"] == 3

    @pytest.mark.asyncio
    async def test_workflow_with_conversation_history(self):
        """대화 이력 전달"""
        workflow = RAGWorkflow(
            planner=PlannerNode(llm_call=_mock_llm_planner),
            retriever=RetrieverNode(retrieve_fn=_mock_retrieve, top_k=3),
            generator=GeneratorNode(llm_call=_mock_llm_generator),
            validator=ValidatorNode(llm_call=_mock_llm_validator_pass),
        )

        history = [
            {"role": "user", "content": "이전 질문"},
            {"role": "assistant", "content": "이전 답변"},
        ]

        result = await workflow.invoke(
            "FastAPI 사용법",
            conversation_history=history,
        )

        assert len(result["conversation_history"]) == 2

    @pytest.mark.asyncio
    async def test_workflow_steps_recorded(self):
        """실행 단계 기록"""
        workflow = RAGWorkflow(
            planner=PlannerNode(llm_call=_mock_llm_planner),
            retriever=RetrieverNode(retrieve_fn=_mock_retrieve, top_k=3),
            generator=GeneratorNode(llm_call=_mock_llm_generator),
            validator=ValidatorNode(llm_call=_mock_llm_validator_pass),
        )

        result = await workflow.invoke("FastAPI 사용법")

        steps = result["steps"]
        assert len(steps) >= 4  # planner + retriever + generator + validator
        assert any("planner" in s for s in steps)
        assert any("retriever" in s for s in steps)
        assert any("generator" in s for s in steps)
        assert any("validator" in s for s in steps)


# ---------------------------------------------------------------------------
# 8. 통합 테스트 (End-to-End with Mocks)
# ---------------------------------------------------------------------------


class TestEndToEnd:
    """End-to-End 통합 테스트"""

    @pytest.mark.asyncio
    async def test_korean_query_e2e(self):
        """한국어 질문 E2E 테스트"""
        workflow = RAGWorkflow(
            planner=PlannerNode(llm_call=_mock_llm_planner),
            retriever=RetrieverNode(retrieve_fn=_mock_retrieve, top_k=5),
            generator=GeneratorNode(llm_call=_mock_llm_generator),
            validator=ValidatorNode(llm_call=_mock_llm_validator_pass),
        )

        result = await workflow.invoke("인공지능 기반 지식 검색 시스템이란?")

        assert result["answer"] != ""
        assert result["validation_result"]["is_valid"] is True

    @pytest.mark.asyncio
    async def test_rule_based_e2e(self):
        """규칙 기반 (LLM 없음) E2E 테스트"""
        workflow = RAGWorkflow(
            planner=PlannerNode(),
            retriever=RetrieverNode(retrieve_fn=_mock_retrieve, top_k=5),
            generator=GeneratorNode(),
            validator=ValidatorNode(),
        )

        result = await workflow.invoke("FastAPI Python 사용법 설명")

        # LLM 없이도 파이프라인이 동작
        assert result["answer"] != ""
        assert result["search_strategy"] in ("keyword", "semantic", "hybrid")
        assert len(result["steps"]) >= 4

    @pytest.mark.asyncio
    async def test_retriever_failure_propagation(self):
        """Retriever 실패 시 파이프라인 계속 진행"""
        async def failing_retrieve(
            query: str, top_k: int = 10, strategy: str = "hybrid"
        ):
            raise ConnectionError("DB down")

        workflow = RAGWorkflow(
            planner=PlannerNode(llm_call=_mock_llm_planner),
            retriever=RetrieverNode(retrieve_fn=failing_retrieve),
            generator=GeneratorNode(llm_call=_mock_llm_generator),
            validator=ValidatorNode(llm_call=_mock_llm_validator_pass),
        )

        result = await workflow.invoke("테스트 질문")

        # 에러가 있지만 파이프라인은 계속 진행
        assert "error" in result
        assert result["documents"] == []

    @pytest.mark.asyncio
    async def test_retry_flow_with_different_results(self):
        """재시도 시 다른 검색 결과"""
        retrieve_count = {"calls": 0}

        async def varying_retrieve(
            query: str, top_k: int = 10, strategy: str = "hybrid"
        ):
            retrieve_count["calls"] += 1
            return _make_documents(retrieve_count["calls"] + 2)

        call_count = {"validator": 0}

        async def validator_eventually_passes(
            system_prompt: str, user_message: str
        ) -> str:
            call_count["validator"] += 1
            if call_count["validator"] <= 1:
                return json.dumps({
                    "faithfulness_score": 0.3,
                    "relevance_score": 0.4,
                    "is_valid": False,
                    "feedback": "Needs improvement",
                })
            return json.dumps({
                "faithfulness_score": 0.92,
                "relevance_score": 0.88,
                "is_valid": True,
                "feedback": "Good",
            })

        workflow = RAGWorkflow(
            planner=PlannerNode(llm_call=_mock_llm_planner),
            retriever=RetrieverNode(
                retrieve_fn=varying_retrieve, top_k=5
            ),
            generator=GeneratorNode(llm_call=_mock_llm_generator),
            validator=ValidatorNode(
                llm_call=validator_eventually_passes
            ),
            max_retries=2,
        )

        result = await workflow.invoke("FastAPI 사용법")

        assert retrieve_count["calls"] >= 2  # At least 2 retrieval calls
        assert result["validation_result"]["is_valid"] is True

    @pytest.mark.asyncio
    async def test_max_retries_zero(self):
        """max_retries=0 시 재시도 없음"""
        workflow = RAGWorkflow(
            planner=PlannerNode(llm_call=_mock_llm_planner),
            retriever=RetrieverNode(retrieve_fn=_mock_retrieve, top_k=3),
            generator=GeneratorNode(llm_call=_mock_llm_generator),
            validator=ValidatorNode(llm_call=_mock_llm_validator_fail),
            max_retries=0,
        )

        result = await workflow.invoke("테스트")

        # 재시도 없이 바로 종료
        assert result["validation_result"]["is_valid"] is False

    @pytest.mark.asyncio
    async def test_concurrent_workflows(self):
        """동시 워크플로우 실행"""
        workflow = RAGWorkflow(
            planner=PlannerNode(llm_call=_mock_llm_planner),
            retriever=RetrieverNode(retrieve_fn=_mock_retrieve, top_k=3),
            generator=GeneratorNode(llm_call=_mock_llm_generator),
            validator=ValidatorNode(llm_call=_mock_llm_validator_pass),
        )

        tasks = [
            workflow.invoke(f"질문 {i}")
            for i in range(3)
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 3
        for result in results:
            assert result["answer"] != ""


# ---------------------------------------------------------------------------
# 9. 모듈 Import 테스트
# ---------------------------------------------------------------------------


class TestModuleImports:
    """모듈 import 검증"""

    def test_import_workflow_package(self):
        """workflows 패키지 import"""
        from ai_service.src.workflows import RAGWorkflow, RAGState

        assert RAGWorkflow is not None
        assert RAGState is not None

    def test_import_nodes_package(self):
        """nodes 패키지 import"""
        from ai_service.src.workflows.nodes import (
            GeneratorNode,
            PlannerNode,
            RetrieverNode,
            ValidatorNode,
        )

        assert PlannerNode is not None
        assert RetrieverNode is not None
        assert GeneratorNode is not None
        assert ValidatorNode is not None

    def test_import_state_module(self):
        """state 모듈 import"""
        from ai_service.src.workflows.state import RAGState, ValidationResult

        assert RAGState is not None
        assert ValidationResult is not None

    def test_import_rag_workflow_module(self):
        """rag_workflow 모듈 import"""
        from ai_service.src.workflows.rag_workflow import (
            RAGWorkflow,
            _should_retry,
        )

        assert RAGWorkflow is not None
        assert callable(_should_retry)


# ---------------------------------------------------------------------------
# 10. Prompt 테스트
# ---------------------------------------------------------------------------


class TestPrompts:
    """프롬프트 내용 검증"""

    def test_planner_system_prompt(self):
        """Planner 시스템 프롬프트"""
        assert "keyword" in PLANNER_SYSTEM_PROMPT
        assert "semantic" in PLANNER_SYSTEM_PROMPT
        assert "hybrid" in PLANNER_SYSTEM_PROMPT
        assert "JSON" in PLANNER_SYSTEM_PROMPT

    def test_generator_system_prompt(self):
        """Generator 시스템 프롬프트"""
        assert "컨텍스트" in GENERATOR_SYSTEM_PROMPT
        assert "한국어" in GENERATOR_SYSTEM_PROMPT
        assert "[1]" in GENERATOR_SYSTEM_PROMPT

    def test_validator_system_prompt(self):
        """Validator 시스템 프롬프트"""
        assert "Faithfulness" in VALIDATOR_SYSTEM_PROMPT
        assert "Relevance" in VALIDATOR_SYSTEM_PROMPT
        assert "0.7" in VALIDATOR_SYSTEM_PROMPT

    def test_generator_user_template_format(self):
        """Generator 사용자 템플릿 포맷"""
        formatted = GENERATOR_USER_TEMPLATE.format(
            context="test context",
            query="test query",
        )
        assert "test context" in formatted
        assert "test query" in formatted
