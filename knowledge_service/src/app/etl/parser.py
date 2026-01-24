"""
통합 문서 파서 모듈

다양한 문서 형식을 지원하는 통합 파서
- Docling: PDF, DOCX, PPTX
- pyhwpx: HWP (폴백)
- 자체 구현: Markdown, Text
"""

import logging
import re
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.models.parsed_document import (
    BatchParseResult,
    DocumentFormat,
    ImageRef,
    ParsedDocument,
    ParseResult,
    ParseStatus,
    Section,
    Table,
    TableCell,
)

logger = logging.getLogger(__name__)


class DocumentParser:
    """
    통합 문서 파서

    다양한 문서 형식을 지원하며 자동으로 적절한 파서를 선택합니다.
    재시도 로직과 폴백 처리를 포함합니다.

    Attributes:
        max_retries: 최대 재시도 횟수
        retry_delay: 재시도 대기 시간 (초)

    Example:
        parser = DocumentParser()
        result = parser.parse("document.pdf")
        if result.success:
            print(result.document.content)
    """

    # 지원하는 형식 매핑
    SUPPORTED_FORMATS = {
        ".pdf": DocumentFormat.PDF,
        ".docx": DocumentFormat.DOCX,
        ".pptx": DocumentFormat.PPTX,
        ".hwp": DocumentFormat.HWP,
        ".md": DocumentFormat.MARKDOWN,
        ".markdown": DocumentFormat.MARKDOWN,
        ".txt": DocumentFormat.TEXT,
        ".html": DocumentFormat.HTML,
        ".htm": DocumentFormat.HTML,
    }

    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        ocr_enabled: bool = True,
        table_structure_enabled: bool = True,
    ):
        """
        DocumentParser 초기화

        Args:
            max_retries: 최대 재시도 횟수
            retry_delay: 재시도 대기 시간 (초)
            ocr_enabled: OCR 사용 여부
            table_structure_enabled: 표 구조 인식 사용 여부
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.ocr_enabled = ocr_enabled
        self.table_structure_enabled = table_structure_enabled

        # 어댑터 인스턴스 (지연 로딩)
        self._docling_adapter = None
        self._hwp_parser = None

    @property
    def docling_adapter(self):
        """Docling 어댑터 (지연 로딩)"""
        if self._docling_adapter is None:
            from app.etl.docling_adapter import DoclingAdapter

            self._docling_adapter = DoclingAdapter(
                ocr_enabled=self.ocr_enabled,
                table_structure_enabled=self.table_structure_enabled,
            )
        return self._docling_adapter

    def supports_format(self, file_path: Union[str, Path]) -> bool:
        """파일 형식 지원 여부 확인"""
        path = Path(file_path)
        return path.suffix.lower() in self.SUPPORTED_FORMATS

    def get_format(self, file_path: Union[str, Path]) -> DocumentFormat:
        """파일 형식 반환"""
        path = Path(file_path)
        return self.SUPPORTED_FORMATS.get(
            path.suffix.lower(), DocumentFormat.UNKNOWN
        )

    def parse(
        self,
        file_path: Union[str, Path],
        force_format: Optional[DocumentFormat] = None,
    ) -> ParseResult:
        """
        문서 파싱

        Args:
            file_path: 파싱할 파일 경로
            force_format: 강제 지정할 형식 (None이면 자동 감지)

        Returns:
            ParseResult: 파싱 결과
        """
        path = Path(file_path)
        doc_format = force_format or self.get_format(path)

        logger.info(f"Parsing document: {path.name} (format: {doc_format})")

        # 형식별 파서 선택
        if doc_format in (DocumentFormat.PDF, DocumentFormat.DOCX, DocumentFormat.PPTX):
            return self._parse_with_retry(
                file_path=path,
                parser_func=self._parse_with_docling,
                doc_format=doc_format,
            )
        elif doc_format == DocumentFormat.HWP:
            return self._parse_with_retry(
                file_path=path,
                parser_func=self._parse_hwp,
                doc_format=doc_format,
            )
        elif doc_format == DocumentFormat.MARKDOWN:
            return self._parse_with_retry(
                file_path=path,
                parser_func=self._parse_markdown,
                doc_format=doc_format,
            )
        elif doc_format == DocumentFormat.TEXT:
            return self._parse_with_retry(
                file_path=path,
                parser_func=self._parse_text,
                doc_format=doc_format,
            )
        elif doc_format == DocumentFormat.HTML:
            return self._parse_with_retry(
                file_path=path,
                parser_func=self._parse_html,
                doc_format=doc_format,
            )
        else:
            # 지원하지 않는 형식
            doc = ParsedDocument.from_file_path(str(path))
            doc.status = ParseStatus.FAILED
            doc.error_message = f"Unsupported format: {doc_format}"
            return ParseResult(
                document=doc,
                success=False,
                message=f"Unsupported format: {doc_format}",
            )

    def _parse_with_retry(
        self,
        file_path: Path,
        parser_func: Callable[[Path], ParseResult],
        doc_format: DocumentFormat,
    ) -> ParseResult:
        """재시도 로직이 포함된 파싱"""
        last_error: Optional[Exception] = None
        warnings: List[str] = []

        for attempt in range(self.max_retries):
            try:
                result = parser_func(file_path)

                # 성공 또는 부분 성공
                if result.success or result.document.status == ParseStatus.PARTIAL:
                    result.document.retry_count = attempt
                    return result

                # 실패했지만 재시도 가능
                last_error = Exception(result.message)
                warnings.append(f"Attempt {attempt + 1}: {result.message}")

            except Exception as e:
                last_error = e
                warnings.append(f"Attempt {attempt + 1}: {str(e)}")
                logger.warning(
                    f"Parse attempt {attempt + 1}/{self.max_retries} failed: {e}"
                )

            # 마지막 시도가 아니면 대기
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay * (attempt + 1))

        # 모든 재시도 실패
        doc = ParsedDocument.from_file_path(str(file_path))
        doc.status = ParseStatus.FAILED
        doc.error_message = str(last_error) if last_error else "Unknown error"
        doc.retry_count = self.max_retries
        doc.metadata["requires_manual_review"] = True  # 수동 검토 플래그

        logger.error(
            f"All {self.max_retries} parse attempts failed for {file_path.name}"
        )

        return ParseResult(
            document=doc,
            success=False,
            message=f"Failed after {self.max_retries} attempts: {doc.error_message}",
            warnings=warnings,
        )

    def _parse_with_docling(self, file_path: Path) -> ParseResult:
        """Docling으로 파싱"""
        return self.docling_adapter.parse(file_path)

    def _parse_hwp(self, file_path: Path) -> ParseResult:
        """HWP 파일 파싱 (pyhwpx 사용)"""
        doc = ParsedDocument.from_file_path(str(file_path))
        start_time = time.time()

        try:
            # pyhwpx import 시도
            try:
                from pyhwpx import Hwp
            except ImportError:
                # pyhwpx가 없으면 python-hwp 시도
                try:
                    import hwp5
                    return self._parse_hwp_with_hwp5(file_path, doc, start_time)
                except ImportError:
                    doc.status = ParseStatus.FAILED
                    doc.error_message = (
                        "HWP parser not available. "
                        "Install pyhwpx or python-hwp"
                    )
                    return ParseResult(
                        document=doc,
                        success=False,
                        message=doc.error_message,
                    )

            # pyhwpx로 파싱
            hwp = Hwp()
            hwp.open(str(file_path))

            # 텍스트 추출
            content = hwp.get_text()
            doc.content = content

            # 표 추출 시도
            tables = []
            try:
                for i, table_data in enumerate(hwp.get_tables()):
                    table = self._convert_hwp_table(table_data, i)
                    if table:
                        tables.append(table)
            except Exception as e:
                logger.warning(f"Error extracting tables from HWP: {e}")

            doc.tables = tables
            doc.word_count = len(content.split())
            doc.char_count = len(content)

            hwp.close()

            doc.status = ParseStatus.SUCCESS
            doc.parsing_time_ms = (time.time() - start_time) * 1000
            doc.parser_version = "pyhwpx"

            return ParseResult(
                document=doc,
                success=True,
                message=f"Successfully parsed HWP: {file_path.name}",
            )

        except Exception as e:
            doc.status = ParseStatus.FAILED
            doc.error_message = str(e)
            doc.parsing_time_ms = (time.time() - start_time) * 1000

            return ParseResult(
                document=doc,
                success=False,
                message=f"Failed to parse HWP: {e}",
            )

    def _parse_hwp_with_hwp5(
        self, file_path: Path, doc: ParsedDocument, start_time: float
    ) -> ParseResult:
        """python-hwp (hwp5) 로 파싱"""
        try:
            import hwp5
            from hwp5.hwp5html import HTMLTransform
            from hwp5.xmlmodel import Hwp5File

            hwp_file = Hwp5File(str(file_path))

            # 텍스트 추출
            texts = []
            for section in hwp_file.bodytext.sections:
                for para in section:
                    if hasattr(para, "text"):
                        texts.append(para.text)

            doc.content = "\n".join(texts)
            doc.word_count = len(doc.content.split())
            doc.char_count = len(doc.content)
            doc.status = ParseStatus.SUCCESS
            doc.parsing_time_ms = (time.time() - start_time) * 1000
            doc.parser_version = "hwp5"

            return ParseResult(
                document=doc,
                success=True,
                message=f"Successfully parsed HWP with hwp5: {file_path.name}",
            )

        except Exception as e:
            doc.status = ParseStatus.FAILED
            doc.error_message = str(e)
            doc.parsing_time_ms = (time.time() - start_time) * 1000

            return ParseResult(
                document=doc,
                success=False,
                message=f"Failed to parse HWP with hwp5: {e}",
            )

    def _convert_hwp_table(self, table_data: Any, index: int) -> Optional[Table]:
        """HWP 표 데이터를 Table 모델로 변환"""
        try:
            cells = []
            rows = 0
            cols = 0

            if isinstance(table_data, list):
                for row_idx, row in enumerate(table_data):
                    if isinstance(row, list):
                        for col_idx, cell_text in enumerate(row):
                            cells.append(
                                TableCell(
                                    row=row_idx,
                                    col=col_idx,
                                    content=str(cell_text) if cell_text else "",
                                    is_header=(row_idx == 0),
                                )
                            )
                            cols = max(cols, col_idx + 1)
                    rows = max(rows, row_idx + 1)

            return Table(cells=cells, rows=rows, cols=cols)

        except Exception as e:
            logger.warning(f"Error converting HWP table {index}: {e}")
            return None

    def _parse_markdown(self, file_path: Path) -> ParseResult:
        """Markdown 파일 파싱"""
        doc = ParsedDocument.from_file_path(str(file_path))
        start_time = time.time()

        try:
            # 파일 읽기
            content = file_path.read_text(encoding="utf-8")
            doc.content = content

            # 섹션 추출 (Markdown 헤딩 기반)
            doc.sections = self._extract_markdown_sections(content)

            # 표 추출
            doc.tables = self._extract_markdown_tables(content)

            # 이미지 참조 추출
            doc.images = self._extract_markdown_images(content)

            # 제목 추출 (첫 번째 H1)
            title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            if title_match:
                doc.title = title_match.group(1).strip()

            doc.word_count = len(content.split())
            doc.char_count = len(content)
            doc.status = ParseStatus.SUCCESS
            doc.parsing_time_ms = (time.time() - start_time) * 1000
            doc.parser_version = "markdown-native"

            return ParseResult(
                document=doc,
                success=True,
                message=f"Successfully parsed Markdown: {file_path.name}",
            )

        except Exception as e:
            doc.status = ParseStatus.FAILED
            doc.error_message = str(e)
            doc.parsing_time_ms = (time.time() - start_time) * 1000

            return ParseResult(
                document=doc,
                success=False,
                message=f"Failed to parse Markdown: {e}",
            )

    def _extract_markdown_sections(self, content: str) -> List[Section]:
        """Markdown에서 섹션 추출"""
        sections = []
        lines = content.split("\n")
        current_section = None
        current_content = []

        heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$")

        for line in lines:
            match = heading_pattern.match(line)
            if match:
                # 이전 섹션 저장
                if current_section is not None:
                    current_section.content = "\n".join(current_content).strip()
                    sections.append(current_section)

                # 새 섹션 시작
                level = len(match.group(1))
                title = match.group(2).strip()
                current_section = Section(title=title, level=level, content="")
                current_content = []
            else:
                current_content.append(line)

        # 마지막 섹션 저장
        if current_section is not None:
            current_section.content = "\n".join(current_content).strip()
            sections.append(current_section)

        return sections

    def _extract_markdown_tables(self, content: str) -> List[Table]:
        """Markdown에서 표 추출"""
        tables = []
        # Markdown 표 패턴: |...|로 시작하는 연속된 줄
        table_pattern = re.compile(
            r"((?:^\|.+\|$\n?)+)",
            re.MULTILINE,
        )

        for i, match in enumerate(table_pattern.finditer(content)):
            table_text = match.group(1).strip()
            table = self._parse_markdown_table(table_text, i)
            if table:
                tables.append(table)

        return tables

    def _parse_markdown_table(self, table_text: str, index: int) -> Optional[Table]:
        """Markdown 표 텍스트를 Table 모델로 변환"""
        try:
            lines = [l.strip() for l in table_text.split("\n") if l.strip()]
            if len(lines) < 2:
                return None

            cells = []
            rows = 0
            cols = 0

            for row_idx, line in enumerate(lines):
                # 구분선 건너뛰기 (|---|---|)
                if re.match(r"^\|[\s\-:]+\|$", line):
                    continue

                # 셀 파싱
                parts = [p.strip() for p in line.split("|")[1:-1]]
                for col_idx, cell_text in enumerate(parts):
                    cells.append(
                        TableCell(
                            row=rows,
                            col=col_idx,
                            content=cell_text,
                            is_header=(rows == 0),
                        )
                    )
                    cols = max(cols, col_idx + 1)
                rows += 1

            if cells:
                return Table(
                    cells=cells,
                    rows=rows,
                    cols=cols,
                    markdown=table_text,
                )
            return None

        except Exception as e:
            logger.warning(f"Error parsing Markdown table {index}: {e}")
            return None

    def _extract_markdown_images(self, content: str) -> List[ImageRef]:
        """Markdown에서 이미지 참조 추출"""
        images = []
        # ![alt](url) 패턴
        img_pattern = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")

        for match in img_pattern.finditer(content):
            alt_text = match.group(1)
            file_path = match.group(2)
            images.append(
                ImageRef(
                    alt_text=alt_text or None,
                    file_path=file_path,
                )
            )

        return images

    def _parse_text(self, file_path: Path) -> ParseResult:
        """일반 텍스트 파일 파싱"""
        doc = ParsedDocument.from_file_path(str(file_path))
        start_time = time.time()

        try:
            # 인코딩 자동 감지 시도
            encodings = ["utf-8", "cp949", "euc-kr", "latin-1"]
            content = None

            for encoding in encodings:
                try:
                    content = file_path.read_text(encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue

            if content is None:
                raise ValueError("Could not decode file with supported encodings")

            doc.content = content
            doc.word_count = len(content.split())
            doc.char_count = len(content)
            doc.status = ParseStatus.SUCCESS
            doc.parsing_time_ms = (time.time() - start_time) * 1000
            doc.parser_version = "text-native"

            return ParseResult(
                document=doc,
                success=True,
                message=f"Successfully parsed text: {file_path.name}",
            )

        except Exception as e:
            doc.status = ParseStatus.FAILED
            doc.error_message = str(e)
            doc.parsing_time_ms = (time.time() - start_time) * 1000

            return ParseResult(
                document=doc,
                success=False,
                message=f"Failed to parse text: {e}",
            )

    def _parse_html(self, file_path: Path) -> ParseResult:
        """HTML 파일 파싱"""
        doc = ParsedDocument.from_file_path(str(file_path))
        start_time = time.time()

        try:
            from html.parser import HTMLParser

            content = file_path.read_text(encoding="utf-8")

            # 간단한 HTML 텍스트 추출
            class TextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.texts = []
                    self.skip_tags = {"script", "style", "head", "meta"}
                    self.current_tag = None

                def handle_starttag(self, tag, attrs):
                    self.current_tag = tag.lower()

                def handle_endtag(self, tag):
                    self.current_tag = None

                def handle_data(self, data):
                    if self.current_tag not in self.skip_tags:
                        text = data.strip()
                        if text:
                            self.texts.append(text)

            extractor = TextExtractor()
            extractor.feed(content)

            doc.content = "\n".join(extractor.texts)
            doc.word_count = len(doc.content.split())
            doc.char_count = len(doc.content)
            doc.status = ParseStatus.SUCCESS
            doc.parsing_time_ms = (time.time() - start_time) * 1000
            doc.parser_version = "html-native"

            return ParseResult(
                document=doc,
                success=True,
                message=f"Successfully parsed HTML: {file_path.name}",
            )

        except Exception as e:
            doc.status = ParseStatus.FAILED
            doc.error_message = str(e)
            doc.parsing_time_ms = (time.time() - start_time) * 1000

            return ParseResult(
                document=doc,
                success=False,
                message=f"Failed to parse HTML: {e}",
            )

    def parse_batch(
        self,
        file_paths: List[Union[str, Path]],
        continue_on_error: bool = True,
    ) -> BatchParseResult:
        """
        여러 문서 일괄 파싱

        Args:
            file_paths: 파싱할 파일 경로 목록
            continue_on_error: 에러 발생 시 계속 진행 여부

        Returns:
            BatchParseResult: 배치 파싱 결과
        """
        start_time = time.time()
        results = []
        success_count = 0
        failed_count = 0

        for file_path in file_paths:
            try:
                result = self.parse(file_path)
                results.append(result)

                if result.success:
                    success_count += 1
                else:
                    failed_count += 1

            except Exception as e:
                logger.error(f"Error parsing {file_path}: {e}")
                failed_count += 1

                if not continue_on_error:
                    break

                # 에러 결과 추가
                doc = ParsedDocument.from_file_path(str(file_path))
                doc.status = ParseStatus.FAILED
                doc.error_message = str(e)
                results.append(
                    ParseResult(
                        document=doc,
                        success=False,
                        message=str(e),
                    )
                )

        total_time_ms = (time.time() - start_time) * 1000

        return BatchParseResult(
            total=len(file_paths),
            success_count=success_count,
            failed_count=failed_count,
            results=results,
            total_time_ms=total_time_ms,
        )


# 편의를 위한 싱글톤 인스턴스
_default_parser: Optional[DocumentParser] = None


def get_parser() -> DocumentParser:
    """기본 파서 인스턴스 반환"""
    global _default_parser
    if _default_parser is None:
        _default_parser = DocumentParser()
    return _default_parser


def parse_document(file_path: Union[str, Path]) -> ParseResult:
    """문서 파싱 편의 함수"""
    return get_parser().parse(file_path)
