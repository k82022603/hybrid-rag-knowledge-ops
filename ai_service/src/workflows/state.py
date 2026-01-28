"""
RAG Workflow Agent State

LangGraph StateGraph에서 사용하는 상태 스키마 정의입니다.
각 노드(Planner, Retriever, Generator, Validator)가 공유하는
상태를 TypedDict로 정의합니다.

STORY-033: LangGraph 기반 RAG 워크플로우 구현
"""

from typing import Any, Dict, List, Literal, Optional, TypedDict


class ValidationResult(TypedDict, total=False):
    """
    Validator 검증 결과

    Attributes:
        is_valid: 검증 통과 여부
        faithfulness_score: 충실도 점수 (0~1)
        relevance_score: 관련성 점수 (0~1)
        feedback: 검증 피드백 메시지
    """

    is_valid: bool
    faithfulness_score: float
    relevance_score: float
    feedback: str


class RAGState(TypedDict, total=False):
    """
    RAG 워크플로우 에이전트 상태

    LangGraph StateGraph 전체 파이프라인에서 공유되는 상태입니다.
    각 노드는 이 상태의 일부를 읽고 업데이트합니다.

    Flow: Planner -> Retriever -> Generator -> Validator -> (END or retry)

    Attributes:
        query: 사용자 원본 질의
        conversation_history: 대화 이력 (멀티턴 지원)
        search_strategy: 검색 전략 (keyword/semantic/hybrid)
        refined_query: 플래너가 정제한 검색용 쿼리
        documents: 검색된 문서 목록
        context: 생성기에 전달할 컨텍스트 문자열
        answer: 생성된 답변
        sources: 출처 정보 목록
        steps: 워크플로우 실행 단계 기록
        error: 에러 메시지 (None이면 에러 없음)
        validation_result: Validator 검증 결과
        retry_count: 재검색 시도 횟수
        max_retries: 최대 재시도 횟수
    """

    # 입력
    query: str
    conversation_history: List[Dict[str, Any]]

    # Planner 출력
    search_strategy: Literal["keyword", "semantic", "hybrid"]
    refined_query: str

    # Retriever 출력
    documents: List[Dict[str, Any]]
    context: str

    # Generator 출력
    answer: str
    sources: List[Dict[str, Any]]

    # Validator 출력
    validation_result: Optional[ValidationResult]

    # 메타
    steps: List[str]
    error: Optional[str]
    retry_count: int
    max_retries: int
