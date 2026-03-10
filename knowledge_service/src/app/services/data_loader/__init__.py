"""
초기 데이터 ETL 파이프라인 패키지

STORY-045: 프로젝트 문서를 Knowledge Graph 및 Vector Store에 적재하는 파이프라인.
STORY-128: 모듈 분리 리팩토링 (유지보수성 향상)

Pipeline:
    1. 데이터 소스 탐색 (파일 디스커버리)
    2. 문서 파싱 (Markdown, PDF, DOCX 등)
    3. 시맨틱 청킹 (SemanticChunker)
    4. 임베딩 생성 (BGE-M3)
    5. 메타데이터 추출 (LLM 기반 문서 분류)
    6. 저장소 적재 (Elasticsearch + Neo4j)

지원 형식:
    - Markdown (.md)
    - PDF (.pdf)
    - DOCX (.docx)
    - PPTX (.pptx)
    - TXT (.txt)
    - HTML (.html/.htm)

모듈 구조:
    - models.py: 데이터 모델 (DocType, LoadStatus, DataSource, FileInfo, LoadResult, ETLSummary)
    - loader_base.py: InitialDataLoader 코어 (오케스트레이터, 파일 탐색, 중복 검사)
    - document_loader.py: 문서 파싱, 청킹, 메타데이터 추출, 유형 분류
    - embedding_loader.py: 임베딩 생성, 엔티티 추출
    - es_loader.py: Elasticsearch 벌크 인덱싱
    - graph_loader.py: Neo4j 그래프 저장
    - pg_loader.py: PostgreSQL SSOT 저장, 전체 저장 오케스트레이션
"""

# Data Models
from app.services.data_loader.models import (
    DataSource,
    DocType,
    ETLSummary,
    FileInfo,
    LoadResult,
    LoadStatus,
)

# Main Loader Class & Singleton
from app.services.data_loader.loader_base import (
    InitialDataLoader,
    get_initial_data_loader,
    reset_initial_data_loader,
)

__all__ = [
    # Data Models
    "DocType",
    "LoadStatus",
    "DataSource",
    "FileInfo",
    "LoadResult",
    "ETLSummary",
    # Main Loader
    "InitialDataLoader",
    "get_initial_data_loader",
    "reset_initial_data_loader",
]
