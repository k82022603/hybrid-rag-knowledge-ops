"""
Retriever Node

Hybrid 검색을 수행하여 관련 문서를 가져오는 노드입니다.
HybridRetriever를 사용하며, Planner가 결정한 검색 전략에
따라 가중치를 조정합니다.

STORY-033: LangGraph 기반 RAG 워크플로우 구현
"""

import logging
from typing import Any, Callable, Dict, List, Optional

from ai_service.src.workflows.state import RAGState

logger = logging.getLogger(__name__)


class RetrieverNode:
    """
    Hybrid 검색 수행 노드

    HybridRetriever를 호출하여 검색을 수행하고, 검색 결과를
    문서 목록과 컨텍스트 문자열로 변환합니다. Planner가 결정한
    search_strategy에 따라 검색 가중치를 조정합니다.

    Args:
        retrieve_fn: 검색 함수 (async callable).
            입력: query (str), top_k (int), strategy (str)
            출력: List[Dict] (검색 결과)
        top_k: 반환할 검색 결과 수
        max_context_length: 컨텍스트 최대 문자 수

    Example:
        >>> async def search(query, top_k=10, strategy="hybrid"):
        ...     return [{"chunk_id": "c1", "content": "...", "score": 0.9}]
        >>> retriever = RetrieverNode(retrieve_fn=search, top_k=5)
        >>> state = await retriever({"refined_query": "...", "steps": []})
    """

    def __init__(
        self,
        retrieve_fn: Optional[Callable] = None,
        top_k: int = 10,
        max_context_length: int = 8000,
    ):
        """
        초기화

        Args:
            retrieve_fn: 비동기 검색 함수
            top_k: 반환할 결과 수
            max_context_length: 컨텍스트 최대 문자 수
        """
        self.retrieve_fn = retrieve_fn
        self.top_k = top_k
        self.max_context_length = max_context_length

    async def __call__(self, state: RAGState) -> Dict[str, Any]:
        """
        Retriever 노드 실행

        검색을 수행하고 결과를 상태에 반영합니다.

        Args:
            state: 현재 RAG 워크플로우 상태

        Returns:
            업데이트할 상태 딕셔너리:
                - documents: 검색된 문서 목록
                - context: 컨텍스트 문자열
                - steps: 실행 단계 기록 추가
                - error: 에러 발생 시 메시지
        """
        query = state.get("refined_query") or state.get("query", "")
        strategy = state.get("search_strategy", "hybrid")
        steps = list(state.get("steps", []))
        retry_count = state.get("retry_count", 0)

        logger.info(
            "RetrieverNode - Query: '%s', Strategy: %s, Retry: %d",
            query[:80], strategy, retry_count,
        )

        if not query or not query.strip():
            logger.warning("RetrieverNode - Empty query")
            steps.append("retriever:error:empty_query")
            return {
                "documents": [],
                "context": "",
                "steps": steps,
                "error": "Empty query for retrieval",
            }

        try:
            if self.retrieve_fn is not None:
                documents = await self.retrieve_fn(
                    query=query,
                    top_k=self.top_k,
                    strategy=strategy,
                )
            else:
                logger.warning("RetrieverNode - No retrieve_fn configured")
                documents = []

            # 문서를 딕셔너리로 정규화
            normalized_docs = self._normalize_documents(documents)

            # 컨텍스트 문자열 구성
            context = self._build_context(normalized_docs)

            steps.append(
                f"retriever:docs={len(normalized_docs)},strategy={strategy}"
            )
            logger.info(
                "RetrieverNode - Retrieved %d documents, context_len=%d",
                len(normalized_docs), len(context),
            )

            result: Dict[str, Any] = {
                "documents": normalized_docs,
                "context": context,
                "steps": steps,
            }

            if not normalized_docs:
                result["error"] = "No documents found"

            return result

        except Exception as e:
            logger.error("RetrieverNode - Error: %s", e)
            steps.append(f"retriever:error:{type(e).__name__}")
            return {
                "documents": [],
                "context": "",
                "steps": steps,
                "error": f"Retrieval error: {e}",
            }

    def _normalize_documents(
        self, documents: List[Any]
    ) -> List[Dict[str, Any]]:
        """
        검색 결과를 표준 딕셔너리 형태로 변환

        SearchResult 객체나 딕셔너리 등 다양한 형태를 통일합니다.

        Args:
            documents: 검색 결과 목록

        Returns:
            정규화된 문서 딕셔너리 목록
        """
        normalized: List[Dict[str, Any]] = []
        for i, doc in enumerate(documents):
            if isinstance(doc, dict):
                normalized.append({
                    "chunk_id": doc.get("chunk_id", doc.get("doc_id", f"doc-{i}")),
                    "document_id": doc.get("document_id", ""),
                    "content": doc.get("content", ""),
                    "score": doc.get("score", 0.0),
                    "source": doc.get("source", "unknown"),
                    "metadata": doc.get("metadata", {}),
                })
            elif hasattr(doc, "content"):
                # SearchResult-like 객체
                normalized.append({
                    "chunk_id": getattr(doc, "chunk_id", f"doc-{i}"),
                    "document_id": getattr(doc, "document_id", ""),
                    "content": getattr(doc, "content", ""),
                    "score": getattr(doc, "score", 0.0),
                    "source": getattr(doc, "source", "unknown"),
                    "metadata": getattr(doc, "metadata", {}),
                })
            else:
                normalized.append({
                    "chunk_id": f"doc-{i}",
                    "document_id": "",
                    "content": str(doc),
                    "score": 0.0,
                    "source": "unknown",
                    "metadata": {},
                })
        return normalized

    def _build_context(self, documents: List[Dict[str, Any]]) -> str:
        """
        문서 목록으로 컨텍스트 문자열 구성

        각 문서의 내용을 번호와 함께 결합하여 하나의 컨텍스트
        문자열로 만듭니다. max_context_length를 초과하면 잘라냅니다.

        Args:
            documents: 정규화된 문서 목록

        Returns:
            컨텍스트 문자열
        """
        if not documents:
            return ""

        parts: List[str] = []
        total_length = 0

        for i, doc in enumerate(documents):
            content = doc.get("content", "")
            source = doc.get("source", "unknown")
            chunk_id = doc.get("chunk_id", f"doc-{i}")

            part = f"[{i + 1}] (ID: {chunk_id}, Source: {source})\n{content}"

            if total_length + len(part) > self.max_context_length:
                remaining = self.max_context_length - total_length
                if remaining > 100:
                    parts.append(part[:remaining] + "...")
                break

            parts.append(part)
            total_length += len(part) + 2  # account for separator

        return "\n\n".join(parts)
