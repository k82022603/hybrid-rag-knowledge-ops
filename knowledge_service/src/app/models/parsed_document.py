"""
문서 파싱 결과 데이터 모델

Docling 파싱 결과를 표준화된 형식으로 변환하기 위한 모델
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class DocumentFormat(str, Enum):
    """지원하는 문서 형식"""

    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    HWP = "hwp"
    MARKDOWN = "md"
    TEXT = "txt"
    HTML = "html"
    UNKNOWN = "unknown"


class ParseStatus(str, Enum):
    """파싱 상태"""

    SUCCESS = "success"
    PARTIAL = "partial"  # 일부 성공 (예: 일부 페이지만 파싱)
    FAILED = "failed"
    PENDING = "pending"


class TableCell(BaseModel):
    """표 셀 모델"""

    row: int = Field(ge=0, description="행 인덱스")
    col: int = Field(ge=0, description="열 인덱스")
    content: str = Field(description="셀 내용")
    rowspan: int = Field(default=1, ge=1, description="행 병합 수")
    colspan: int = Field(default=1, ge=1, description="열 병합 수")
    is_header: bool = Field(default=False, description="헤더 셀 여부")


class Table(BaseModel):
    """표 모델"""

    id: str = Field(default_factory=lambda: str(uuid4())[:8], description="표 ID")
    title: Optional[str] = Field(default=None, description="표 제목/캡션")
    cells: List[TableCell] = Field(default_factory=list, description="셀 목록")
    rows: int = Field(ge=0, description="총 행 수")
    cols: int = Field(ge=0, description="총 열 수")
    page_number: Optional[int] = Field(default=None, description="페이지 번호")
    markdown: Optional[str] = Field(default=None, description="Markdown 형식 표")

    def to_markdown(self) -> str:
        """표를 Markdown 형식으로 변환"""
        if self.markdown:
            return self.markdown

        if not self.cells:
            return ""

        # 셀을 2D 배열로 변환
        grid = [[""] * self.cols for _ in range(self.rows)]
        for cell in self.cells:
            if 0 <= cell.row < self.rows and 0 <= cell.col < self.cols:
                grid[cell.row][cell.col] = cell.content

        # Markdown 테이블 생성
        lines = []
        for i, row in enumerate(grid):
            line = "| " + " | ".join(row) + " |"
            lines.append(line)
            if i == 0:  # 헤더 구분선
                separator = "| " + " | ".join(["---"] * self.cols) + " |"
                lines.append(separator)

        return "\n".join(lines)


class ImageRef(BaseModel):
    """이미지 참조 모델"""

    id: str = Field(default_factory=lambda: str(uuid4())[:8], description="이미지 ID")
    caption: Optional[str] = Field(default=None, description="이미지 캡션")
    alt_text: Optional[str] = Field(default=None, description="대체 텍스트")
    page_number: Optional[int] = Field(default=None, description="페이지 번호")
    position: Optional[Dict[str, float]] = Field(
        default=None, description="위치 정보 (x, y, width, height)"
    )
    file_path: Optional[str] = Field(default=None, description="추출된 이미지 파일 경로")


class Section(BaseModel):
    """문서 섹션 모델"""

    id: str = Field(default_factory=lambda: str(uuid4())[:8], description="섹션 ID")
    title: Optional[str] = Field(default=None, description="섹션 제목")
    level: int = Field(default=1, ge=1, le=6, description="섹션 레벨 (1-6)")
    content: str = Field(description="섹션 내용")
    page_start: Optional[int] = Field(default=None, description="시작 페이지")
    page_end: Optional[int] = Field(default=None, description="종료 페이지")
    subsections: List["Section"] = Field(default_factory=list, description="하위 섹션")
    tables: List[Table] = Field(default_factory=list, description="섹션 내 표")
    images: List[ImageRef] = Field(default_factory=list, description="섹션 내 이미지")


# Forward reference 해결
Section.model_rebuild()


class ParsedDocument(BaseModel):
    """
    파싱된 문서 모델

    Docling 파싱 결과를 표준화된 형식으로 저장
    """

    id: UUID = Field(default_factory=uuid4, description="문서 UUID")
    source_path: Optional[str] = Field(default=None, description="원본 파일 경로")
    source_format: DocumentFormat = Field(
        default=DocumentFormat.UNKNOWN, description="원본 파일 형식"
    )

    # 파싱 상태
    status: ParseStatus = Field(default=ParseStatus.PENDING, description="파싱 상태")
    error_message: Optional[str] = Field(default=None, description="에러 메시지")
    retry_count: int = Field(default=0, ge=0, description="재시도 횟수")

    # 콘텐츠
    content: str = Field(default="", description="전체 텍스트 내용")
    sections: List[Section] = Field(default_factory=list, description="섹션별 구조")
    tables: List[Table] = Field(default_factory=list, description="추출된 표 목록")
    images: List[ImageRef] = Field(default_factory=list, description="이미지 참조 목록")

    # 메타데이터
    title: Optional[str] = Field(default=None, description="문서 제목")
    author: Optional[str] = Field(default=None, description="작성자")
    created_date: Optional[datetime] = Field(default=None, description="문서 작성일")
    modified_date: Optional[datetime] = Field(default=None, description="문서 수정일")
    page_count: Optional[int] = Field(default=None, description="총 페이지 수")
    word_count: Optional[int] = Field(default=None, description="단어 수")
    char_count: Optional[int] = Field(default=None, description="문자 수")

    # 파싱 정보
    parsed_at: datetime = Field(default_factory=datetime.utcnow, description="파싱 시간")
    parser_version: Optional[str] = Field(default=None, description="파서 버전")
    parsing_time_ms: Optional[float] = Field(default=None, description="파싱 소요 시간(ms)")

    # 추가 메타데이터
    metadata: Dict[str, Any] = Field(default_factory=dict, description="추가 메타데이터")

    class Config:
        """Pydantic 설정"""

        from_attributes = True

    @classmethod
    def from_file_path(cls, file_path: str) -> "ParsedDocument":
        """파일 경로로부터 기본 ParsedDocument 생성"""
        path = Path(file_path)
        suffix = path.suffix.lower().lstrip(".")

        format_map = {
            "pdf": DocumentFormat.PDF,
            "docx": DocumentFormat.DOCX,
            "pptx": DocumentFormat.PPTX,
            "hwp": DocumentFormat.HWP,
            "md": DocumentFormat.MARKDOWN,
            "txt": DocumentFormat.TEXT,
            "html": DocumentFormat.HTML,
            "htm": DocumentFormat.HTML,
        }

        return cls(
            source_path=str(path),
            source_format=format_map.get(suffix, DocumentFormat.UNKNOWN),
            title=path.stem,
        )

    def to_markdown(self) -> str:
        """문서를 Markdown 형식으로 변환"""
        parts = []

        # 제목
        if self.title:
            parts.append(f"# {self.title}\n")

        # 섹션별 내용
        if self.sections:
            for section in self.sections:
                parts.append(self._section_to_markdown(section))
        else:
            parts.append(self.content)

        # 표 목록
        if self.tables:
            parts.append("\n## Tables\n")
            for i, table in enumerate(self.tables, 1):
                if table.title:
                    parts.append(f"\n### {table.title}\n")
                else:
                    parts.append(f"\n### Table {i}\n")
                parts.append(table.to_markdown())
                parts.append("")

        return "\n".join(parts)

    def _section_to_markdown(self, section: Section, base_level: int = 1) -> str:
        """섹션을 Markdown 형식으로 변환"""
        parts = []

        # 섹션 제목
        if section.title:
            level = min(section.level + base_level - 1, 6)
            parts.append(f"{'#' * level} {section.title}\n")

        # 섹션 내용
        if section.content:
            parts.append(section.content)

        # 섹션 내 표
        for table in section.tables:
            parts.append(f"\n{table.to_markdown()}\n")

        # 하위 섹션
        for subsection in section.subsections:
            parts.append(self._section_to_markdown(subsection, base_level + 1))

        return "\n".join(parts)

    @property
    def is_successful(self) -> bool:
        """파싱 성공 여부"""
        return self.status in (ParseStatus.SUCCESS, ParseStatus.PARTIAL)

    @property
    def has_tables(self) -> bool:
        """표 포함 여부"""
        return len(self.tables) > 0

    @property
    def has_images(self) -> bool:
        """이미지 포함 여부"""
        return len(self.images) > 0


class ParseResult(BaseModel):
    """파싱 결과 응답 모델"""

    document: ParsedDocument = Field(description="파싱된 문서")
    success: bool = Field(description="파싱 성공 여부")
    message: str = Field(default="", description="결과 메시지")
    warnings: List[str] = Field(default_factory=list, description="경고 목록")


class BatchParseResult(BaseModel):
    """배치 파싱 결과 모델"""

    total: int = Field(ge=0, description="총 문서 수")
    success_count: int = Field(ge=0, description="성공 수")
    failed_count: int = Field(ge=0, description="실패 수")
    results: List[ParseResult] = Field(default_factory=list, description="개별 결과 목록")
    total_time_ms: Optional[float] = Field(default=None, description="총 소요 시간(ms)")
