"""
초기 데이터 ETL 파이프라인 (Backward Compatibility Wrapper)

STORY-045: 프로젝트 문서를 Knowledge Graph 및 Vector Store에 적재하는 파이프라인.
STORY-128: 모듈 분리 리팩토링 — 실제 구현은 data_loader/ 패키지로 이동.

이 파일은 기존 import 경로 호환성을 위해 유지됩니다.
모든 심볼을 app.services.data_loader 패키지에서 re-export합니다.

Example:
    # 기존 방식 (계속 동작)
    from app.services.initial_data_loader import InitialDataLoader, DataSource, DocType

    # 새로운 방식 (권장)
    from app.services.data_loader import InitialDataLoader, DataSource, DocType
"""

# Re-export all public symbols from data_loader package
from app.services.data_loader import (  # noqa: F401
    DataSource,
    DocType,
    ETLSummary,
    FileInfo,
    InitialDataLoader,
    LoadResult,
    LoadStatus,
    get_initial_data_loader,
    reset_initial_data_loader,
)

__all__ = [
    "DocType",
    "LoadStatus",
    "DataSource",
    "FileInfo",
    "LoadResult",
    "ETLSummary",
    "InitialDataLoader",
    "get_initial_data_loader",
    "reset_initial_data_loader",
]
