"""
데이터 모델 정의

ETL 파이프라인에서 사용하는 데이터 모델 클래스들을 정의합니다.

Classes:
    DocType: 문서 유형 분류 Enum
    LoadStatus: 로드 상태 Enum
    DataSource: 데이터 소스 정의
    FileInfo: 탐색된 파일 정보
    LoadResult: 개별 파일 로드 결과
    ETLSummary: ETL 전체 실행 요약
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class DocType(str, Enum):
    """문서 유형 분류"""

    TECHNICAL = "technical"
    GUIDE = "guide"
    PRESENTATION = "presentation"
    POLICY = "policy"
    STANDARD = "standard"
    REPORT = "report"
    UNKNOWN = "unknown"


class LoadStatus(str, Enum):
    """로드 상태"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class DataSource:
    """데이터 소스 정의

    ETL 파이프라인에서 처리할 데이터 소스를 정의합니다.
    각 소스는 파일 경로, 문서 유형, 파일 확장자 필터를 포함합니다.

    Attributes:
        name: 데이터 소스 이름 (예: "technical", "guides")
        path: 데이터 소스 디렉토리 경로
        doc_type: 문서 유형 분류
        extensions: 허용할 파일 확장자 목록
        recursive: 하위 디렉토리 재귀 탐색 여부
        description: 데이터 소스 설명
    """

    name: str
    path: str
    doc_type: DocType = DocType.UNKNOWN
    extensions: List[str] = field(
        default_factory=lambda: [".md", ".pdf", ".docx", ".pptx", ".txt", ".html", ".htm"]
    )
    recursive: bool = True
    description: str = ""


@dataclass
class FileInfo:
    """탐색된 파일 정보

    Attributes:
        file_path: 파일 절대 경로
        file_name: 파일명 (확장자 포함)
        file_size: 파일 크기 (바이트)
        extension: 파일 확장자
        source_name: 소속 데이터 소스 이름
        doc_type: 문서 유형 분류
        modified_at: 최종 수정 시간
    """

    file_path: Path
    file_name: str
    file_size: int
    extension: str
    source_name: str
    doc_type: DocType
    modified_at: Optional[datetime] = None


@dataclass
class LoadResult:
    """개별 파일 로드 결과

    Attributes:
        file_path: 파일 경로
        file_name: 파일명
        status: 로드 상태
        document_id: 생성된 문서 ID (성공 시)
        chunk_count: 생성된 청크 수
        entity_count: 추출된 엔티티 수
        error_message: 에러 메시지 (실패 시)
        processing_time_ms: 처리 소요 시간 (밀리초)
    """

    file_path: str
    file_name: str
    status: LoadStatus = LoadStatus.PENDING
    document_id: Optional[str] = None
    chunk_count: int = 0
    entity_count: int = 0
    error_message: Optional[str] = None
    processing_time_ms: float = 0.0


@dataclass
class ETLSummary:
    """ETL 전체 실행 요약

    Attributes:
        total_files: 전체 파일 수
        success_count: 성공 파일 수
        failed_count: 실패 파일 수
        skipped_count: 건너뛴 파일 수
        total_chunks: 전체 생성 청크 수
        total_entities: 전체 추출 엔티티 수
        total_time_ms: 전체 소요 시간 (밀리초)
        results: 개별 파일 로드 결과 목록
        started_at: 시작 시간
        completed_at: 완료 시간
    """

    total_files: int = 0
    success_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    total_chunks: int = 0
    total_entities: int = 0
    total_time_ms: float = 0.0
    results: List[LoadResult] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def success_rate(self) -> float:
        """성공률 (0.0 ~ 1.0)"""
        if self.total_files == 0:
            return 0.0
        return self.success_count / self.total_files

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "total_files": self.total_files,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "skipped_count": self.skipped_count,
            "total_chunks": self.total_chunks,
            "total_entities": self.total_entities,
            "total_time_ms": round(self.total_time_ms, 2),
            "success_rate": round(self.success_rate * 100, 1),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
