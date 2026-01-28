"""
Generator Node

검색된 컨텍스트를 바탕으로 사용자 질문에 대한 답변을 생성합니다.
LLM을 호출하여 한국어로 답변을 생성하고, 출처 정보를 추출합니다.

STORY-033: LangGraph 기반 RAG 워크플로우 구현
"""

import json
import logging
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

from ai_service.src.workflows.state import RAGState

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# System Prompt for Generator
# --------------------------------------------------------------------------

GENERATOR_SYSTEM_PROMPT = """당신은 지식 검색 시스템의 답변 생성기입니다.
제공된 컨텍스트를 바탕으로 사용자의 질문에 정확하게 답변합니다.

규칙:
1. 반드시 제공된 컨텍스트에 기반하여 답변합니다.
2. 컨텍스트에 없는 내용은 추측하지 않습니다.
3. 한국어로 답변합니다.
4. 답변 끝에 참고한 출처를 [1], [2] 형식으로 표기합니다.
5. 컨텍스트가 부족하면 "제공된 정보만으로는 완전한 답변이 어렵습니다"라고 명시합니다.
6. 간결하고 명확한 답변을 작성합니다.
"""

GENERATOR_USER_TEMPLATE = """컨텍스트:
{context}

---

사용자 질문: {query}

위 컨텍스트를 참고하여 질문에 답변해 주세요."""


class GeneratorNode:
    """
    컨텍스트 기반 답변 생성 노드

    LLM을 호출하여 검색된 컨텍스트를 바탕으로 사용자 질문에
    대한 답변을 생성합니다. 출처 정보를 추출하여 상태에 반영합니다.

    Args:
        llm_call: LLM 호출 함수 (async callable).
            입력: system_prompt (str), user_message (str)
            출력: str (생성된 답변 텍스트)
        llm_stream: 스트리밍 LLM 호출 함수 (async generator, 선택).
            입력: system_prompt (str), user_message (str)
            출력: AsyncIterator[str] (토큰 스트림)

    Example:
        >>> async def my_llm(system_prompt, user_message):
        ...     return "FastAPI는 Python 웹 프레임워크입니다. [1]"
        >>> generator = GeneratorNode(llm_call=my_llm)
        >>> state = await generator({
        ...     "query": "FastAPI란?",
        ...     "context": "[1] FastAPI는...",
        ...     "documents": [...],
        ...     "steps": [],
        ... })
    """

    def __init__(
        self,
        llm_call: Optional[Callable] = None,
        llm_stream: Optional[Callable] = None,
    ):
        """
        초기화

        Args:
            llm_call: LLM 호출 비동기 함수
            llm_stream: 스트리밍 LLM 호출 비동기 제너레이터
        """
        self.llm_call = llm_call
        self.llm_stream = llm_stream

    async def __call__(self, state: RAGState) -> Dict[str, Any]:
        """
        Generator 노드 실행

        컨텍스트를 바탕으로 답변을 생성합니다.

        Args:
            state: 현재 RAG 워크플로우 상태

        Returns:
            업데이트할 상태 딕셔너리:
                - answer: 생성된 답변
                - sources: 출처 정보 목록
                - steps: 실행 단계 기록 추가
                - error: 에러 발생 시 메시지
        """
        query = state.get("query", "")
        context = state.get("context", "")
        documents = state.get("documents", [])
        steps = list(state.get("steps", []))

        logger.info(
            "GeneratorNode - Query: '%s', Context length: %d, Docs: %d",
            query[:80], len(context), len(documents),
        )

        if not context:
            logger.warning("GeneratorNode - Empty context")
            steps.append("generator:no_context")
            return {
                "answer": "검색된 문서가 없어 답변을 생성할 수 없습니다. 다른 질문을 시도해 주세요.",
                "sources": [],
                "steps": steps,
            }

        try:
            if self.llm_call is not None:
                user_message = GENERATOR_USER_TEMPLATE.format(
                    context=context,
                    query=query,
                )
                answer = await self.llm_call(
                    GENERATOR_SYSTEM_PROMPT,
                    user_message,
                )
            else:
                # LLM 미설정 시 컨텍스트 요약 반환
                answer = self._fallback_answer(query, documents)

            # 출처 정보 추출
            sources = self._extract_sources(answer, documents)

            steps.append(f"generator:answer_len={len(answer)},sources={len(sources)}")
            logger.info(
                "GeneratorNode - Answer length: %d, Sources: %d",
                len(answer), len(sources),
            )

            return {
                "answer": answer,
                "sources": sources,
                "steps": steps,
            }

        except Exception as e:
            logger.error("GeneratorNode - Error: %s", e)
            steps.append(f"generator:error:{type(e).__name__}")
            return {
                "answer": f"답변 생성 중 오류가 발생했습니다: {e}",
                "sources": [],
                "steps": steps,
                "error": f"Generation error: {e}",
            }

    async def stream(self, state: RAGState) -> AsyncIterator[str]:
        """
        스트리밍 답변 생성

        토큰 단위로 답변을 스트리밍합니다.

        Args:
            state: 현재 RAG 워크플로우 상태

        Yields:
            str: 생성된 토큰

        Raises:
            RuntimeError: 스트리밍 LLM이 설정되지 않은 경우
        """
        query = state.get("query", "")
        context = state.get("context", "")

        if self.llm_stream is None:
            # 스트리밍 미지원 시 전체 답변을 한 번에 반환
            result = await self(state)
            answer = result.get("answer", "")
            yield answer
            return

        user_message = GENERATOR_USER_TEMPLATE.format(
            context=context,
            query=query,
        )

        async for token in self.llm_stream(
            GENERATOR_SYSTEM_PROMPT,
            user_message,
        ):
            yield token

    def _extract_sources(
        self, answer: str, documents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        답변에서 출처 정보 추출

        답변에 포함된 [1], [2] 등의 인용 번호를 기반으로
        해당 문서의 출처 정보를 추출합니다.

        Args:
            answer: 생성된 답변
            documents: 검색된 문서 목록

        Returns:
            출처 정보 딕셔너리 목록
        """
        sources: List[Dict[str, Any]] = []
        referenced_indices: set = set()

        # [1], [2] 등의 패턴 찾기
        import re
        refs = re.findall(r"\[(\d+)\]", answer)
        for ref in refs:
            idx = int(ref) - 1  # 1-based to 0-based
            if 0 <= idx < len(documents):
                referenced_indices.add(idx)

        # 참조된 문서가 없으면 상위 문서를 출처로 포함
        if not referenced_indices and documents:
            referenced_indices = set(range(min(3, len(documents))))

        for idx in sorted(referenced_indices):
            doc = documents[idx]
            sources.append({
                "index": idx + 1,
                "chunk_id": doc.get("chunk_id", ""),
                "document_id": doc.get("document_id", ""),
                "source": doc.get("source", "unknown"),
                "score": doc.get("score", 0.0),
                "content_preview": doc.get("content", "")[:200],
            })

        return sources

    def _fallback_answer(
        self, query: str, documents: List[Dict[str, Any]]
    ) -> str:
        """
        LLM 미사용 시 폴백 답변 생성

        검색된 문서 내용을 간단히 요약하여 반환합니다.

        Args:
            query: 사용자 쿼리
            documents: 검색된 문서 목록

        Returns:
            폴백 답변 문자열
        """
        if not documents:
            return "관련 문서를 찾을 수 없습니다."

        parts = [f"'{query}'에 대한 검색 결과입니다:\n"]
        for i, doc in enumerate(documents[:5]):
            content = doc.get("content", "")
            preview = content[:300] if content else "(내용 없음)"
            parts.append(f"[{i + 1}] {preview}")

        return "\n\n".join(parts)
