"""
RAG 파이프라인 서비스 모듈 [DEPRECATED]

.. deprecated:: STORY-051
    이 모듈은 레거시 RAG 파이프라인입니다.
    새로운 코드에서는 ``app.agents.rag_workflow.RAGWorkflow``를 사용하세요.
    LangGraph 기반 워크플로우가 Planner -> Retriever -> Reranker -> Generator
    파이프라인을 제공합니다.

기존 기능:
- 컨텍스트 구성 (검색 결과 -> 프롬프트 컨텍스트)
- 프롬프트 템플릿 관리
- LLM 기반 답변 생성 (DeepSeek V3.2)
- 스트리밍 응답 지원
- 출처 정보 생성
"""

import json
import time
import warnings
from typing import Any, AsyncIterator, Dict, List, Optional

from app.agents.state import SearchResult
from app.core.config import settings
from app.core.exceptions import LLMError
from app.core.logging import get_logger
from app.services.llm_service import get_llm_service

logger = get_logger(__name__)

# STORY-051: 레거시 파이프라인 비활성화 경고
_DEPRECATION_MSG = (
    "RAGPipeline은 레거시 파이프라인입니다. "
    "app.agents.rag_workflow.RAGWorkflow를 사용하세요. "
    "(STORY-051: LangGraph 통합)"
)


# ---------------------------------------------------------------------------
# 프롬프트 템플릿
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_KO = """당신은 사내 지식 검색 시스템의 AI 어시스턴트입니다.
주어진 컨텍스트 정보를 바탕으로 사용자의 질문에 정확하고 도움이 되는 답변을 제공합니다.

## 답변 규칙
1. **컨텍스트 기반**: 반드시 제공된 컨텍스트 내용에 근거하여 답변합니다.
2. **정확성**: 컨텍스트에 없는 내용은 추측하지 않고 "해당 정보를 찾을 수 없습니다"라고 안내합니다.
3. **출처 명시**: 답변에 사용한 문서나 청크의 출처를 [출처1], [출처2] 형태로 표기합니다.
4. **구조화**: 복잡한 답변은 목록, 소제목 등으로 구조화합니다.
5. **한국어**: 답변은 한국어로 제공합니다."""

RAG_PROMPT_TEMPLATE = """## 컨텍스트 정보

{context}

---

## 사용자 질문

{query}

---

위 컨텍스트를 참고하여 사용자 질문에 답변해주세요.
답변에 사용한 출처를 [출처N] 형태로 표기해주세요."""


CONTEXT_CHUNK_TEMPLATE = """### [출처{index}] {title}
- 문서 ID: {document_id}
- 관련성 점수: {score}

{content}
"""


# ---------------------------------------------------------------------------
# RAG 응답 모델
# ---------------------------------------------------------------------------

class RAGResponse:
    """RAG 파이프라인 응답"""

    def __init__(
        self,
        answer: str,
        sources: List[Dict[str, Any]],
        query: str,
        context_length: int = 0,
        latency_ms: float = 0.0,
        model: str = "",
        token_usage: Optional[Dict[str, int]] = None,
    ):
        self.answer = answer
        self.sources = sources
        self.query = query
        self.context_length = context_length
        self.latency_ms = latency_ms
        self.model = model
        self.token_usage = token_usage or {}

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "answer": self.answer,
            "sources": self.sources,
            "query": self.query,
            "context_length": self.context_length,
            "latency_ms": round(self.latency_ms, 2),
            "model": self.model,
            "token_usage": self.token_usage,
        }


# ---------------------------------------------------------------------------
# RAGPipeline
# ---------------------------------------------------------------------------

class RAGPipeline:
    """
    RAG (Retrieval-Augmented Generation) 파이프라인

    .. deprecated:: STORY-051
        이 클래스는 레거시 파이프라인입니다.
        새로운 코드에서는 ``app.agents.rag_workflow.RAGWorkflow``를 사용하세요.

    검색 결과를 컨텍스트로 구성하고 LLM을 통해 답변을 생성합니다.

    Pipeline:
        1. 검색 결과 -> 컨텍스트 구성 (Augmentation)
        2. 프롬프트 템플릿 적용
        3. LLM 호출 (Generation)
        4. 출처 정보 생성
        5. 응답 반환
    """

    def __init__(
        self,
        system_prompt: Optional[str] = None,
        max_context_length: int = 8000,
        max_context_chunks: int = 10,
    ):
        """
        초기화

        Args:
            system_prompt: 시스템 프롬프트 (None이면 기본 프롬프트 사용)
            max_context_length: 컨텍스트 최대 문자 수
            max_context_chunks: 컨텍스트에 포함할 최대 청크 수
        """
        warnings.warn(_DEPRECATION_MSG, DeprecationWarning, stacklevel=2)
        logger.warning(_DEPRECATION_MSG)

        self.system_prompt = system_prompt or SYSTEM_PROMPT_KO
        self.max_context_length = max_context_length
        self.max_context_chunks = max_context_chunks
        self._llm_service = get_llm_service()

    async def process_query(
        self,
        query: str,
        search_results: List[SearchResult],
        use_reasoner: bool = False,
    ) -> RAGResponse:
        """
        RAG 파이프라인 실행

        검색 결과를 기반으로 컨텍스트를 구성하고 LLM 답변을 생성합니다.

        Args:
            query: 사용자 질의
            search_results: 검색 결과 리스트
            use_reasoner: Reasoner 모델 사용 여부 (복잡한 추론용)

        Returns:
            RAGResponse 객체

        Raises:
            LLMError: LLM 호출 실패
        """
        start_time = time.monotonic()

        logger.info(
            f"RAG pipeline - Query: '{query[:80]}...', "
            f"Results: {len(search_results)}, "
            f"Reasoner: {use_reasoner}"
        )

        # 1. 컨텍스트 구성
        context, selected_results = self._build_context(search_results)

        if not context.strip():
            logger.warning("No context available for RAG - returning fallback answer")
            return RAGResponse(
                answer="죄송합니다. 질문과 관련된 정보를 찾을 수 없습니다. "
                       "다른 키워드로 검색해 주시거나, 질문을 더 구체적으로 작성해 주세요.",
                sources=[],
                query=query,
                context_length=0,
                latency_ms=(time.monotonic() - start_time) * 1000,
                model="none",
            )

        # 2. 프롬프트 구성
        user_prompt = RAG_PROMPT_TEMPLATE.format(
            context=context,
            query=query,
        )

        # 3. LLM 호출
        answer = await self.generate_answer(
            query=query,
            context=context,
            use_reasoner=use_reasoner,
        )

        # 4. 출처 정보 생성
        sources = self._build_sources(selected_results)

        latency_ms = (time.monotonic() - start_time) * 1000

        logger.info(
            f"RAG pipeline complete - "
            f"Context length: {len(context)}, "
            f"Answer length: {len(answer)}, "
            f"Sources: {len(sources)}, "
            f"Latency: {latency_ms:.1f}ms"
        )

        return RAGResponse(
            answer=answer,
            sources=sources,
            query=query,
            context_length=len(context),
            latency_ms=latency_ms,
            model=settings.deepseek_chat_model,
        )

    async def generate_answer(
        self,
        query: str,
        context: str,
        use_reasoner: bool = False,
    ) -> str:
        """
        LLM 기반 답변 생성

        Args:
            query: 사용자 질의
            context: 컨텍스트 문자열
            use_reasoner: Reasoner 모델 사용 여부

        Returns:
            생성된 답변 문자열

        Raises:
            LLMError: LLM 호출 실패
        """
        logger.info(
            f"Generating answer - Context length: {len(context)}, "
            f"Reasoner: {use_reasoner}"
        )

        messages = [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "user",
                "content": RAG_PROMPT_TEMPLATE.format(
                    context=context,
                    query=query,
                ),
            },
        ]

        try:
            answer = await self._llm_service.generate_with_messages(
                messages=messages,
                use_reasoner=use_reasoner,
            )

            logger.info(f"Answer generated - Length: {len(answer)}")
            return answer

        except LLMError:
            raise
        except Exception as e:
            logger.exception(f"Answer generation failed: {e}")
            raise LLMError(f"답변 생성 실패: {str(e)}")

    async def generate_stream(
        self,
        query: str,
        search_results: List[SearchResult],
    ) -> AsyncIterator[str]:
        """
        스트리밍 답변 생성

        SSE (Server-Sent Events) 형식으로 답변을 청크 단위로 스트리밍합니다.

        Args:
            query: 사용자 질의
            search_results: 검색 결과 리스트

        Yields:
            SSE 형식의 이벤트 문자열
        """
        # 1. 컨텍스트 구성
        context, selected_results = self._build_context(search_results)

        # 2. 시작 이벤트
        sources = self._build_sources(selected_results)
        start_event = json.dumps({
            "type": "start",
            "sources": sources,
            "context_length": len(context),
        }, ensure_ascii=False)
        yield f"data: {start_event}\n\n"

        if not context.strip():
            fallback_event = json.dumps({
                "type": "chunk",
                "content": "죄송합니다. 질문과 관련된 정보를 찾을 수 없습니다.",
            }, ensure_ascii=False)
            yield f"data: {fallback_event}\n\n"

            end_event = json.dumps({"type": "end"})
            yield f"data: {end_event}\n\n"
            return

        # 3. LLM 호출 (비스트리밍으로 전체 생성 후 청크 분할)
        try:
            answer = await self.generate_answer(
                query=query,
                context=context,
            )

            # 답변을 문장 단위로 분할하여 스트리밍
            sentences = self._split_into_sentences(answer)
            for sentence in sentences:
                chunk_event = json.dumps({
                    "type": "chunk",
                    "content": sentence,
                }, ensure_ascii=False)
                yield f"data: {chunk_event}\n\n"

        except Exception as e:
            error_event = json.dumps({
                "type": "error",
                "message": f"답변 생성 중 오류가 발생했습니다: {str(e)}",
            }, ensure_ascii=False)
            yield f"data: {error_event}\n\n"

        # 4. 종료 이벤트
        end_event = json.dumps({"type": "end"})
        yield f"data: {end_event}\n\n"

    # ------------------------------------------------------------------
    # Internal methods
    # ------------------------------------------------------------------

    def _build_context(
        self,
        search_results: List[SearchResult],
    ) -> tuple:
        """
        검색 결과에서 컨텍스트 문자열 구성

        Args:
            search_results: 검색 결과 리스트

        Returns:
            (컨텍스트 문자열, 선택된 검색 결과 리스트)
        """
        if not search_results:
            return "", []

        context_parts: List[str] = []
        selected_results: List[SearchResult] = []
        total_length = 0

        for idx, result in enumerate(search_results):
            if idx >= self.max_context_chunks:
                break

            chunk_text = CONTEXT_CHUNK_TEMPLATE.format(
                index=idx + 1,
                title=result.metadata.get("title", "문서"),
                document_id=result.document_id[:8] if result.document_id else "N/A",
                score=round(result.score, 4),
                content=result.content,
            )

            # 최대 길이 확인
            if total_length + len(chunk_text) > self.max_context_length:
                # 남은 공간에 맞게 잘라서 포함
                remaining = self.max_context_length - total_length
                if remaining > 200:  # 최소 200자 이상이어야 포함
                    truncated = chunk_text[:remaining] + "\n...(잘림)"
                    context_parts.append(truncated)
                    selected_results.append(result)
                break

            context_parts.append(chunk_text)
            selected_results.append(result)
            total_length += len(chunk_text)

        context = "\n".join(context_parts)

        logger.debug(
            f"Context built - Chunks: {len(selected_results)}/{len(search_results)}, "
            f"Length: {len(context)}"
        )

        return context, selected_results

    def _build_sources(
        self,
        search_results: List[SearchResult],
    ) -> List[Dict[str, Any]]:
        """
        출처 정보 생성

        Args:
            search_results: 선택된 검색 결과 리스트

        Returns:
            출처 정보 딕셔너리 리스트
        """
        sources: List[Dict[str, Any]] = []
        seen_doc_ids: set = set()

        for idx, result in enumerate(search_results):
            doc_id = result.document_id

            source_info: Dict[str, Any] = {
                "index": idx + 1,
                "chunk_id": result.chunk_id,
                "document_id": doc_id,
                "title": result.metadata.get("title", "문서"),
                "score": round(result.score, 4),
                "source_type": result.source,
                "snippet": result.content[:200] + "..."
                if len(result.content) > 200
                else result.content,
            }

            # 문서 중복이라도 청크는 각각 표시
            if doc_id not in seen_doc_ids:
                source_info["is_primary"] = True
                seen_doc_ids.add(doc_id)
            else:
                source_info["is_primary"] = False

            sources.append(source_info)

        return sources

    @staticmethod
    def _split_into_sentences(text: str) -> List[str]:
        """
        텍스트를 문장 단위로 분할

        Args:
            text: 분할할 텍스트

        Returns:
            문장 리스트
        """
        import re

        # 한국어/영어 문장 종결 패턴
        sentences = re.split(r'(?<=[.!?。])\s+', text)

        # 빈 문장 제거
        return [s.strip() for s in sentences if s.strip()]


# ---------------------------------------------------------------------------
# 싱글톤 인스턴스
# ---------------------------------------------------------------------------

_rag_pipeline: Optional[RAGPipeline] = None


def get_rag_pipeline() -> RAGPipeline:
    """RAGPipeline 인스턴스 반환 (싱글톤)"""
    global _rag_pipeline
    if _rag_pipeline is None:
        _rag_pipeline = RAGPipeline()
    return _rag_pipeline
