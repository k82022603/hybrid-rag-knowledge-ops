"""
LangGraph 에이전트 상태 정의

TypedDict 기반 상태 스키마 정의
"""

from typing import Any, Dict, List, Optional, TypedDict

from pydantic import BaseModel, Field


class Entity(BaseModel):
    """추출된 엔티티"""

    id: str = Field(description="엔티티 고유 ID")
    name: str = Field(description="엔티티명")
    type: str = Field(description="엔티티 유형 (Person, Project, Technology, Organization, Concept)")
    description: Optional[str] = Field(default=None, description="엔티티 설명")


class Relationship(BaseModel):
    """추출된 관계"""

    source: str = Field(description="소스 엔티티 ID")
    target: str = Field(description="타겟 엔티티 ID")
    type: str = Field(description="관계 유형 (CREATED, PARTICIPATED, USES, BELONGS_TO, RELATED_TO)")
    description: Optional[str] = Field(default=None, description="관계 설명")


class CategoryMetadata(BaseModel):
    """카테고리 메타데이터"""

    level1: str = Field(description="대분류")
    level2: str = Field(description="중분류")
    level3: Optional[str] = Field(default=None, description="소분류")


class DocumentMetadata(BaseModel):
    """문서 메타데이터"""

    document_type: str = Field(description="문서 유형")
    project_name: str = Field(default="", description="프로젝트명")
    valid_start_date: Optional[str] = Field(default=None, description="유효 시작일")
    valid_end_date: Optional[str] = Field(default=None, description="유효 종료일")
    categories: Optional[CategoryMetadata] = Field(default=None, description="계층적 카테고리")
    summary: str = Field(default="", description="문서 요약")


class ExtractionResult(BaseModel):
    """엔티티/관계 추출 결과"""

    entities: List[Entity] = Field(default_factory=list, description="추출된 엔티티 목록")
    relationships: List[Relationship] = Field(default_factory=list, description="추출된 관계 목록")
    metadata: Optional[DocumentMetadata] = Field(default=None, description="문서 메타데이터")


class SearchResult(BaseModel):
    """검색 결과"""

    chunk_id: str = Field(description="청크 ID")
    document_id: str = Field(description="문서 ID")
    content: str = Field(description="청크 내용")
    score: float = Field(description="관련성 점수")
    source: str = Field(description="검색 소스 (vector, graph)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="메타데이터")


class AgentState(TypedDict, total=False):
    """
    LangGraph 에이전트 상태

    VIP 3단계 파이프라인에서 공유되는 상태
    """

    # 입력
    query: str  # 사용자 질의
    document_text: Optional[str]  # 처리할 문서 텍스트

    # Stage 1: Value (엔티티 추출)
    extracted_entities: List[Entity]  # 추출된 엔티티
    extracted_relationships: List[Relationship]  # 추출된 관계
    document_metadata: Optional[DocumentMetadata]  # 문서 메타데이터
    gleaning_count: int  # Gleaning 반복 횟수

    # Stage 2: Intelligent (오케스트레이션)
    search_strategy: str  # 검색 전략 (vector, graph, hybrid)
    vector_results: List[SearchResult]  # Vector Search 결과
    graph_results: List[SearchResult]  # Graph Search 결과
    fused_results: List[SearchResult]  # RRF 융합 결과
    reranked_results: List[SearchResult]  # Reranking 결과

    # Stage 3: Planning (답변 합성)
    context: str  # 합성용 컨텍스트
    answer: str  # 생성된 답변
    sources: List[Dict[str, Any]]  # 출처 정보

    # 메타 정보
    error: Optional[str]  # 에러 메시지
    messages: List[Dict[str, Any]]  # LangGraph 메시지 히스토리
