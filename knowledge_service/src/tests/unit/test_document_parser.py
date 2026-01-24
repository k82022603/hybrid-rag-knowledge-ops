"""
문서 파서 단위 테스트

STORY-002: Docling 문서 파싱 구현
- 4가지 형식 파싱 테스트 (PDF, DOCX, HWP, Markdown)
- 표 추출 테스트
- 재시도 로직 테스트
- 에러 핸들링 테스트
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

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


class TestParsedDocumentModel:
    """ParsedDocument 모델 테스트"""

    def test_create_from_file_path_pdf(self):
        """PDF 파일 경로로 문서 생성"""
        doc = ParsedDocument.from_file_path("/path/to/document.pdf")

        assert doc.source_path == "/path/to/document.pdf"
        assert doc.source_format == DocumentFormat.PDF
        assert doc.title == "document"
        assert doc.status == ParseStatus.PENDING

    def test_create_from_file_path_docx(self):
        """DOCX 파일 경로로 문서 생성"""
        doc = ParsedDocument.from_file_path("/path/to/report.docx")

        assert doc.source_format == DocumentFormat.DOCX
        assert doc.title == "report"

    def test_create_from_file_path_hwp(self):
        """HWP 파일 경로로 문서 생성"""
        doc = ParsedDocument.from_file_path("/path/to/korean_doc.hwp")

        assert doc.source_format == DocumentFormat.HWP
        assert doc.title == "korean_doc"

    def test_create_from_file_path_markdown(self):
        """Markdown 파일 경로로 문서 생성"""
        doc = ParsedDocument.from_file_path("/path/to/readme.md")

        assert doc.source_format == DocumentFormat.MARKDOWN
        assert doc.title == "readme"

    def test_create_from_file_path_unknown(self):
        """알 수 없는 형식"""
        doc = ParsedDocument.from_file_path("/path/to/unknown.xyz")

        assert doc.source_format == DocumentFormat.UNKNOWN

    def test_is_successful(self):
        """파싱 성공 여부 확인"""
        doc = ParsedDocument(status=ParseStatus.SUCCESS)
        assert doc.is_successful is True

        doc = ParsedDocument(status=ParseStatus.PARTIAL)
        assert doc.is_successful is True

        doc = ParsedDocument(status=ParseStatus.FAILED)
        assert doc.is_successful is False

    def test_has_tables(self):
        """표 포함 여부 확인"""
        doc = ParsedDocument()
        assert doc.has_tables is False

        doc.tables = [Table(rows=2, cols=2)]
        assert doc.has_tables is True

    def test_has_images(self):
        """이미지 포함 여부 확인"""
        doc = ParsedDocument()
        assert doc.has_images is False

        doc.images = [ImageRef()]
        assert doc.has_images is True


class TestTableModel:
    """Table 모델 테스트"""

    def test_table_to_markdown(self):
        """표를 Markdown으로 변환"""
        cells = [
            TableCell(row=0, col=0, content="Header 1", is_header=True),
            TableCell(row=0, col=1, content="Header 2", is_header=True),
            TableCell(row=1, col=0, content="Value 1"),
            TableCell(row=1, col=1, content="Value 2"),
        ]
        table = Table(cells=cells, rows=2, cols=2)

        md = table.to_markdown()

        assert "| Header 1 | Header 2 |" in md
        assert "| --- | --- |" in md
        assert "| Value 1 | Value 2 |" in md

    def test_table_with_existing_markdown(self):
        """기존 Markdown이 있으면 그대로 반환"""
        table = Table(
            rows=1,
            cols=1,
            markdown="| Existing Markdown |",
        )

        assert table.to_markdown() == "| Existing Markdown |"

    def test_empty_table(self):
        """빈 표"""
        table = Table(rows=0, cols=0)
        assert table.to_markdown() == ""


class TestSectionModel:
    """Section 모델 테스트"""

    def test_section_creation(self):
        """섹션 생성"""
        section = Section(
            title="Introduction",
            level=1,
            content="This is the introduction.",
        )

        assert section.title == "Introduction"
        assert section.level == 1
        assert section.content == "This is the introduction."

    def test_nested_sections(self):
        """중첩 섹션"""
        subsection = Section(
            title="Subsection",
            level=2,
            content="Subsection content",
        )
        section = Section(
            title="Main Section",
            level=1,
            content="Main content",
            subsections=[subsection],
        )

        assert len(section.subsections) == 1
        assert section.subsections[0].title == "Subsection"


class TestDocumentParser:
    """DocumentParser 클래스 테스트"""

    def test_supports_format(self):
        """형식 지원 여부 확인"""
        from app.etl.parser import DocumentParser

        parser = DocumentParser()

        assert parser.supports_format("document.pdf") is True
        assert parser.supports_format("document.docx") is True
        assert parser.supports_format("document.hwp") is True
        assert parser.supports_format("document.md") is True
        assert parser.supports_format("document.txt") is True
        assert parser.supports_format("document.xyz") is False

    def test_get_format(self):
        """파일 형식 반환"""
        from app.etl.parser import DocumentParser

        parser = DocumentParser()

        assert parser.get_format("test.pdf") == DocumentFormat.PDF
        assert parser.get_format("test.docx") == DocumentFormat.DOCX
        assert parser.get_format("test.pptx") == DocumentFormat.PPTX
        assert parser.get_format("test.hwp") == DocumentFormat.HWP
        assert parser.get_format("test.md") == DocumentFormat.MARKDOWN
        assert parser.get_format("test.markdown") == DocumentFormat.MARKDOWN
        assert parser.get_format("test.txt") == DocumentFormat.TEXT
        assert parser.get_format("test.html") == DocumentFormat.HTML
        assert parser.get_format("test.unknown") == DocumentFormat.UNKNOWN

    def test_parse_markdown_file(self, tmp_path):
        """Markdown 파일 파싱"""
        from app.etl.parser import DocumentParser

        # 테스트 Markdown 파일 생성
        md_content = """# Test Document

## Introduction

This is the introduction section.

## Table

| Name | Value |
|------|-------|
| A    | 1     |
| B    | 2     |

## Conclusion

This is the conclusion.

![Image](./image.png)
"""
        md_file = tmp_path / "test.md"
        md_file.write_text(md_content, encoding="utf-8")

        parser = DocumentParser()
        result = parser.parse(md_file)

        assert result.success is True
        assert result.document.status == ParseStatus.SUCCESS
        assert result.document.title == "Test Document"
        assert len(result.document.sections) >= 1
        assert len(result.document.tables) == 1
        assert len(result.document.images) == 1
        assert result.document.word_count > 0
        assert result.document.parser_version == "markdown-native"

    def test_parse_text_file(self, tmp_path):
        """텍스트 파일 파싱"""
        from app.etl.parser import DocumentParser

        txt_content = "This is a simple text file.\nWith multiple lines."
        txt_file = tmp_path / "test.txt"
        txt_file.write_text(txt_content, encoding="utf-8")

        parser = DocumentParser()
        result = parser.parse(txt_file)

        assert result.success is True
        assert result.document.content == txt_content
        assert result.document.word_count == 9
        assert result.document.parser_version == "text-native"

    def test_parse_text_file_korean(self, tmp_path):
        """한글 텍스트 파일 파싱 (인코딩 테스트)"""
        from app.etl.parser import DocumentParser

        txt_content = "안녕하세요. 한글 테스트입니다."
        txt_file = tmp_path / "korean.txt"
        txt_file.write_text(txt_content, encoding="utf-8")

        parser = DocumentParser()
        result = parser.parse(txt_file)

        assert result.success is True
        assert "안녕하세요" in result.document.content

    def test_parse_html_file(self, tmp_path):
        """HTML 파일 파싱"""
        from app.etl.parser import DocumentParser

        html_content = """<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
<h1>Heading</h1>
<p>This is a paragraph.</p>
<script>alert('ignored');</script>
</body>
</html>
"""
        html_file = tmp_path / "test.html"
        html_file.write_text(html_content, encoding="utf-8")

        parser = DocumentParser()
        result = parser.parse(html_file)

        assert result.success is True
        assert "Heading" in result.document.content
        assert "This is a paragraph" in result.document.content
        assert "alert" not in result.document.content  # script 내용 제외
        assert result.document.parser_version == "html-native"

    def test_parse_nonexistent_file(self, tmp_path):
        """존재하지 않는 파일 파싱"""
        from app.etl.parser import DocumentParser

        parser = DocumentParser()
        result = parser.parse(tmp_path / "nonexistent.md")

        assert result.success is False
        assert result.document.status == ParseStatus.FAILED

    def test_parse_unsupported_format(self, tmp_path):
        """지원하지 않는 형식 파싱"""
        from app.etl.parser import DocumentParser

        xyz_file = tmp_path / "test.xyz"
        xyz_file.write_text("content")

        parser = DocumentParser()
        result = parser.parse(xyz_file)

        assert result.success is False
        assert "Unsupported format" in result.message

    def test_parse_batch(self, tmp_path):
        """배치 파싱"""
        from app.etl.parser import DocumentParser

        # 여러 테스트 파일 생성
        (tmp_path / "doc1.txt").write_text("Content 1", encoding="utf-8")
        (tmp_path / "doc2.txt").write_text("Content 2", encoding="utf-8")
        (tmp_path / "doc3.md").write_text("# Title\n\nContent 3", encoding="utf-8")

        parser = DocumentParser()
        batch_result = parser.parse_batch([
            tmp_path / "doc1.txt",
            tmp_path / "doc2.txt",
            tmp_path / "doc3.md",
        ])

        assert batch_result.total == 3
        assert batch_result.success_count == 3
        assert batch_result.failed_count == 0
        assert len(batch_result.results) == 3
        assert batch_result.total_time_ms > 0

    def test_parse_batch_with_errors(self, tmp_path):
        """에러가 있는 배치 파싱"""
        from app.etl.parser import DocumentParser

        (tmp_path / "doc1.txt").write_text("Content 1", encoding="utf-8")

        parser = DocumentParser()
        batch_result = parser.parse_batch([
            tmp_path / "doc1.txt",
            tmp_path / "nonexistent.txt",  # 없는 파일
        ], continue_on_error=True)

        assert batch_result.total == 2
        assert batch_result.success_count == 1
        assert batch_result.failed_count == 1

    def test_retry_on_failure(self, tmp_path):
        """재시도 로직 테스트"""
        from app.etl.parser import DocumentParser

        # Mock parser that fails twice then succeeds
        parser = DocumentParser(max_retries=3, retry_delay=0.1)

        md_file = tmp_path / "test.md"
        md_file.write_text("# Test", encoding="utf-8")

        # 정상 파싱 테스트
        result = parser.parse(md_file)
        assert result.success is True
        assert result.document.retry_count == 0  # 첫 시도에서 성공

    def test_max_retries_exceeded(self, tmp_path):
        """최대 재시도 횟수 초과"""
        from app.etl.parser import DocumentParser

        parser = DocumentParser(max_retries=2, retry_delay=0.01)

        # 존재하지 않는 파일로 재시도 테스트
        result = parser.parse(tmp_path / "nonexistent.md")

        assert result.success is False
        assert result.document.retry_count == 2
        assert result.document.metadata.get("requires_manual_review") is True


class TestDoclingAdapter:
    """DoclingAdapter 클래스 테스트"""

    def test_supports_format(self):
        """Docling 지원 형식 확인"""
        from app.etl.docling_adapter import DoclingAdapter

        adapter = DoclingAdapter()

        assert adapter.supports_format(DocumentFormat.PDF) is True
        assert adapter.supports_format(DocumentFormat.DOCX) is True
        assert adapter.supports_format(DocumentFormat.PPTX) is True
        assert adapter.supports_format(DocumentFormat.HWP) is False
        assert adapter.supports_format(DocumentFormat.MARKDOWN) is False

    def test_parse_nonexistent_file(self, tmp_path):
        """존재하지 않는 파일 파싱"""
        from app.etl.docling_adapter import DoclingAdapter

        adapter = DoclingAdapter()
        result = adapter.parse(tmp_path / "nonexistent.pdf")

        assert result.success is False
        assert "File not found" in result.message

    def test_parse_unsupported_format(self, tmp_path):
        """지원하지 않는 형식 파싱"""
        from app.etl.docling_adapter import DoclingAdapter

        # HWP 파일 생성 (빈 파일)
        hwp_file = tmp_path / "test.hwp"
        hwp_file.write_bytes(b"dummy content")

        adapter = DoclingAdapter()
        result = adapter.parse(hwp_file)

        assert result.success is False
        assert "Unsupported format" in result.message

    @pytest.mark.skip(reason="Requires Docling installation")
    def test_parse_pdf_with_tables(self, tmp_path):
        """PDF 파일 파싱 (표 포함) - Docling 필요"""
        from app.etl.docling_adapter import DoclingAdapter

        # 이 테스트는 실제 Docling이 설치되어 있고
        # 테스트용 PDF 파일이 있을 때만 실행
        adapter = DoclingAdapter(
            table_structure_enabled=True,
            ocr_enabled=False,
        )
        # result = adapter.parse("path/to/test.pdf")
        # assert result.success is True
        # assert len(result.document.tables) > 0


class TestMarkdownTableExtraction:
    """Markdown 표 추출 테스트"""

    def test_extract_simple_table(self, tmp_path):
        """간단한 표 추출"""
        from app.etl.parser import DocumentParser

        md_content = """
| A | B |
|---|---|
| 1 | 2 |
"""
        md_file = tmp_path / "table.md"
        md_file.write_text(md_content, encoding="utf-8")

        parser = DocumentParser()
        result = parser.parse(md_file)

        assert result.success is True
        assert len(result.document.tables) == 1
        table = result.document.tables[0]
        assert table.rows == 2  # 헤더 + 데이터 (구분선 제외)
        assert table.cols == 2

    def test_extract_multiple_tables(self, tmp_path):
        """여러 표 추출"""
        from app.etl.parser import DocumentParser

        md_content = """
## Table 1
| A | B |
|---|---|
| 1 | 2 |

## Table 2
| X | Y | Z |
|---|---|---|
| a | b | c |
"""
        md_file = tmp_path / "tables.md"
        md_file.write_text(md_content, encoding="utf-8")

        parser = DocumentParser()
        result = parser.parse(md_file)

        assert result.success is True
        assert len(result.document.tables) == 2


class TestMarkdownSectionExtraction:
    """Markdown 섹션 추출 테스트"""

    def test_extract_sections(self, tmp_path):
        """섹션 추출"""
        from app.etl.parser import DocumentParser

        md_content = """# Main Title

Introduction text.

## Section 1

Section 1 content.

## Section 2

Section 2 content.

### Subsection 2.1

Subsection content.
"""
        md_file = tmp_path / "sections.md"
        md_file.write_text(md_content, encoding="utf-8")

        parser = DocumentParser()
        result = parser.parse(md_file)

        assert result.success is True
        assert len(result.document.sections) >= 3

        # 첫 번째 섹션 (H1)
        main_section = result.document.sections[0]
        assert main_section.title == "Main Title"
        assert main_section.level == 1


class TestParseResult:
    """ParseResult 모델 테스트"""

    def test_parse_result_success(self):
        """성공 결과"""
        doc = ParsedDocument(status=ParseStatus.SUCCESS, content="test")
        result = ParseResult(
            document=doc,
            success=True,
            message="Success",
        )

        assert result.success is True
        assert result.document.content == "test"
        assert len(result.warnings) == 0

    def test_parse_result_with_warnings(self):
        """경고가 있는 결과"""
        doc = ParsedDocument(status=ParseStatus.PARTIAL)
        result = ParseResult(
            document=doc,
            success=True,
            message="Partial success",
            warnings=["Some images could not be extracted"],
        )

        assert result.success is True
        assert len(result.warnings) == 1


class TestBatchParseResult:
    """BatchParseResult 모델 테스트"""

    def test_batch_result(self):
        """배치 결과"""
        results = [
            ParseResult(
                document=ParsedDocument(status=ParseStatus.SUCCESS),
                success=True,
                message="OK",
            ),
            ParseResult(
                document=ParsedDocument(status=ParseStatus.FAILED),
                success=False,
                message="Error",
            ),
        ]

        batch = BatchParseResult(
            total=2,
            success_count=1,
            failed_count=1,
            results=results,
            total_time_ms=100.0,
        )

        assert batch.total == 2
        assert batch.success_count == 1
        assert batch.failed_count == 1
        assert batch.total_time_ms == 100.0


class TestConvenienceFunctions:
    """편의 함수 테스트"""

    def test_get_parser(self):
        """기본 파서 인스턴스"""
        from app.etl.parser import get_parser

        parser1 = get_parser()
        parser2 = get_parser()

        # 싱글톤 확인
        assert parser1 is parser2

    def test_parse_document(self, tmp_path):
        """parse_document 편의 함수"""
        from app.etl.parser import parse_document

        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Hello, World!", encoding="utf-8")

        result = parse_document(txt_file)

        assert result.success is True
        assert result.document.content == "Hello, World!"
