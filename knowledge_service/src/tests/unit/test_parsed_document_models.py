"""
ParsedDocument 모델 테스트 (커버리지 개선)

대상 파일: src/app/models/parsed_document.py
목표: 66% -> 80%+ 커버리지 달성

테스트 범주:
- DocumentFormat / ParseStatus Enum 테스트
- TableCell 모델 테스트 (rowspan, colspan)
- Table 모델 테스트 (to_markdown 엣지 케이스)
- ImageRef 모델 테스트 (전체 필드)
- Section 모델 테스트 (중첩, 표, 이미지)
- ParsedDocument 테스트 (to_markdown, _section_to_markdown)
- ParseResult / BatchParseResult 테스트
- 직렬화/역직렬화 테스트
- 필드 유효성 검사 테스트
"""

from datetime import datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

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


class TestDocumentFormatEnum:
    """DocumentFormat Enum 테스트"""

    def test_all_format_values(self):
        """모든 형식 값 확인"""
        assert DocumentFormat.PDF.value == "pdf"
        assert DocumentFormat.DOCX.value == "docx"
        assert DocumentFormat.PPTX.value == "pptx"
        assert DocumentFormat.HWP.value == "hwp"
        assert DocumentFormat.MARKDOWN.value == "md"
        assert DocumentFormat.TEXT.value == "txt"
        assert DocumentFormat.HTML.value == "html"
        assert DocumentFormat.UNKNOWN.value == "unknown"

    def test_enum_is_string_subclass(self):
        """Enum이 str 서브클래스인지 확인"""
        assert isinstance(DocumentFormat.PDF, str)
        assert DocumentFormat.PDF == "pdf"

    def test_enum_count(self):
        """Enum 개수 확인"""
        assert len(DocumentFormat) == 8


class TestParseStatusEnum:
    """ParseStatus Enum 테스트"""

    def test_all_status_values(self):
        """모든 상태 값 확인"""
        assert ParseStatus.SUCCESS.value == "success"
        assert ParseStatus.PARTIAL.value == "partial"
        assert ParseStatus.FAILED.value == "failed"
        assert ParseStatus.PENDING.value == "pending"

    def test_enum_is_string_subclass(self):
        """Enum이 str 서브클래스인지 확인"""
        assert isinstance(ParseStatus.SUCCESS, str)
        assert ParseStatus.SUCCESS == "success"


class TestTableCellModel:
    """TableCell 모델 테스트"""

    def test_basic_cell_creation(self):
        """기본 셀 생성"""
        cell = TableCell(row=0, col=0, content="Test")
        assert cell.row == 0
        assert cell.col == 0
        assert cell.content == "Test"
        assert cell.rowspan == 1
        assert cell.colspan == 1
        assert cell.is_header is False

    def test_cell_with_rowspan_colspan(self):
        """rowspan, colspan 설정"""
        cell = TableCell(
            row=1,
            col=2,
            content="Merged",
            rowspan=2,
            colspan=3,
            is_header=True,
        )
        assert cell.rowspan == 2
        assert cell.colspan == 3
        assert cell.is_header is True

    def test_cell_negative_row_fails(self):
        """음수 행 인덱스 실패"""
        with pytest.raises(ValidationError):
            TableCell(row=-1, col=0, content="Test")

    def test_cell_negative_col_fails(self):
        """음수 열 인덱스 실패"""
        with pytest.raises(ValidationError):
            TableCell(row=0, col=-1, content="Test")

    def test_cell_zero_rowspan_fails(self):
        """rowspan 0 실패"""
        with pytest.raises(ValidationError):
            TableCell(row=0, col=0, content="Test", rowspan=0)

    def test_cell_zero_colspan_fails(self):
        """colspan 0 실패"""
        with pytest.raises(ValidationError):
            TableCell(row=0, col=0, content="Test", colspan=0)

    def test_cell_serialization(self):
        """셀 직렬화"""
        cell = TableCell(row=0, col=0, content="Test", is_header=True)
        data = cell.model_dump()
        assert data["row"] == 0
        assert data["col"] == 0
        assert data["content"] == "Test"
        assert data["is_header"] is True

    def test_cell_deserialization(self):
        """셀 역직렬화"""
        data = {
            "row": 1,
            "col": 2,
            "content": "Restored",
            "rowspan": 2,
            "colspan": 2,
            "is_header": False,
        }
        cell = TableCell.model_validate(data)
        assert cell.row == 1
        assert cell.col == 2
        assert cell.content == "Restored"


class TestTableModel:
    """Table 모델 테스트"""

    def test_table_auto_id_generation(self):
        """테이블 ID 자동 생성"""
        table = Table(rows=2, cols=2)
        assert table.id is not None
        assert len(table.id) == 8

    def test_table_with_title(self):
        """테이블 제목 설정"""
        table = Table(rows=1, cols=1, title="Revenue Table")
        assert table.title == "Revenue Table"

    def test_table_with_page_number(self):
        """페이지 번호 설정"""
        table = Table(rows=1, cols=1, page_number=5)
        assert table.page_number == 5

    def test_to_markdown_with_preset_markdown(self):
        """사전 설정된 Markdown 반환"""
        preset_md = "| Custom | Markdown |"
        table = Table(rows=1, cols=2, markdown=preset_md)
        assert table.to_markdown() == preset_md

    def test_to_markdown_empty_table(self):
        """빈 테이블 Markdown"""
        table = Table(rows=0, cols=0)
        assert table.to_markdown() == ""

    def test_to_markdown_no_cells(self):
        """셀이 없는 테이블"""
        table = Table(rows=2, cols=2, cells=[])
        assert table.to_markdown() == ""

    def test_to_markdown_normal(self):
        """정상 테이블 Markdown 변환"""
        cells = [
            TableCell(row=0, col=0, content="A"),
            TableCell(row=0, col=1, content="B"),
            TableCell(row=1, col=0, content="1"),
            TableCell(row=1, col=1, content="2"),
        ]
        table = Table(rows=2, cols=2, cells=cells)
        md = table.to_markdown()

        assert "| A | B |" in md
        assert "| --- | --- |" in md
        assert "| 1 | 2 |" in md

    def test_to_markdown_out_of_bounds_cell(self):
        """범위 밖 셀 무시"""
        cells = [
            TableCell(row=0, col=0, content="Valid"),
            TableCell(row=10, col=10, content="Invalid"),  # 범위 밖
        ]
        table = Table(rows=2, cols=2, cells=cells)
        md = table.to_markdown()

        assert "Valid" in md
        assert "Invalid" not in md

    def test_to_markdown_single_row_table(self):
        """단일 행 테이블"""
        cells = [
            TableCell(row=0, col=0, content="Only"),
            TableCell(row=0, col=1, content="Header"),
        ]
        table = Table(rows=1, cols=2, cells=cells)
        md = table.to_markdown()

        assert "| Only | Header |" in md
        assert "| --- | --- |" in md

    def test_to_markdown_many_columns(self):
        """여러 열 테이블"""
        cells = [TableCell(row=0, col=i, content=f"Col{i}") for i in range(5)]
        table = Table(rows=1, cols=5, cells=cells)
        md = table.to_markdown()

        assert "| Col0 | Col1 | Col2 | Col3 | Col4 |" in md
        assert "| --- | --- | --- | --- | --- |" in md

    def test_table_serialization(self):
        """테이블 직렬화"""
        table = Table(
            id="test123",
            title="Test Table",
            rows=2,
            cols=2,
            page_number=1,
            cells=[TableCell(row=0, col=0, content="A")],
        )
        data = table.model_dump()
        assert data["id"] == "test123"
        assert data["title"] == "Test Table"
        assert len(data["cells"]) == 1


class TestImageRefModel:
    """ImageRef 모델 테스트"""

    def test_image_auto_id_generation(self):
        """이미지 ID 자동 생성"""
        img = ImageRef()
        assert img.id is not None
        assert len(img.id) == 8

    def test_image_with_caption(self):
        """캡션 설정"""
        img = ImageRef(caption="Figure 1: System Architecture")
        assert img.caption == "Figure 1: System Architecture"

    def test_image_with_alt_text(self):
        """대체 텍스트 설정"""
        img = ImageRef(alt_text="Architecture diagram")
        assert img.alt_text == "Architecture diagram"

    def test_image_with_page_number(self):
        """페이지 번호 설정"""
        img = ImageRef(page_number=3)
        assert img.page_number == 3

    def test_image_with_position(self):
        """위치 정보 설정"""
        position = {"x": 100.0, "y": 200.0, "width": 300.0, "height": 150.0}
        img = ImageRef(position=position)
        assert img.position == position
        assert img.position["x"] == 100.0

    def test_image_with_file_path(self):
        """파일 경로 설정"""
        img = ImageRef(file_path="/images/figure1.png")
        assert img.file_path == "/images/figure1.png"

    def test_image_full_fields(self):
        """모든 필드 설정"""
        img = ImageRef(
            id="img001",
            caption="Test Image",
            alt_text="Test alt",
            page_number=5,
            position={"x": 0.0, "y": 0.0, "width": 100.0, "height": 100.0},
            file_path="/test/image.png",
        )
        assert img.id == "img001"
        assert img.caption == "Test Image"
        assert img.alt_text == "Test alt"
        assert img.page_number == 5
        assert img.position is not None
        assert img.file_path == "/test/image.png"

    def test_image_serialization(self):
        """이미지 직렬화"""
        img = ImageRef(
            caption="Test",
            position={"x": 10.0, "y": 20.0, "width": 30.0, "height": 40.0},
        )
        data = img.model_dump()
        assert data["caption"] == "Test"
        assert data["position"]["x"] == 10.0


class TestSectionModel:
    """Section 모델 테스트"""

    def test_section_auto_id_generation(self):
        """섹션 ID 자동 생성"""
        section = Section(content="Test content")
        assert section.id is not None
        assert len(section.id) == 8

    def test_section_with_title(self):
        """섹션 제목 설정"""
        section = Section(title="Introduction", content="This is intro")
        assert section.title == "Introduction"

    def test_section_level_default(self):
        """기본 레벨 확인"""
        section = Section(content="Test")
        assert section.level == 1

    def test_section_level_range(self):
        """레벨 범위 1-6"""
        for level in range(1, 7):
            section = Section(level=level, content="Test")
            assert section.level == level

    def test_section_level_out_of_range_fails(self):
        """레벨 범위 초과 실패"""
        with pytest.raises(ValidationError):
            Section(level=0, content="Test")

        with pytest.raises(ValidationError):
            Section(level=7, content="Test")

    def test_section_with_page_info(self):
        """페이지 정보 설정"""
        section = Section(content="Test", page_start=1, page_end=5)
        assert section.page_start == 1
        assert section.page_end == 5

    def test_section_with_subsections(self):
        """하위 섹션 설정"""
        sub1 = Section(title="Sub 1", level=2, content="Sub content 1")
        sub2 = Section(title="Sub 2", level=2, content="Sub content 2")
        section = Section(
            title="Main",
            level=1,
            content="Main content",
            subsections=[sub1, sub2],
        )
        assert len(section.subsections) == 2
        assert section.subsections[0].title == "Sub 1"

    def test_section_with_tables(self):
        """섹션 내 테이블 설정"""
        table = Table(rows=2, cols=2, title="Section Table")
        section = Section(content="Test", tables=[table])
        assert len(section.tables) == 1
        assert section.tables[0].title == "Section Table"

    def test_section_with_images(self):
        """섹션 내 이미지 설정"""
        img = ImageRef(caption="Section Image")
        section = Section(content="Test", images=[img])
        assert len(section.images) == 1
        assert section.images[0].caption == "Section Image"

    def test_section_serialization(self):
        """섹션 직렬화"""
        section = Section(
            title="Test Section",
            level=2,
            content="Test content",
            page_start=1,
            page_end=3,
        )
        data = section.model_dump()
        assert data["title"] == "Test Section"
        assert data["level"] == 2


class TestParsedDocumentModel:
    """ParsedDocument 모델 테스트 (추가)"""

    def test_document_auto_id_generation(self):
        """문서 ID 자동 생성"""
        doc = ParsedDocument()
        assert isinstance(doc.id, UUID)

    def test_document_default_status(self):
        """기본 상태 PENDING"""
        doc = ParsedDocument()
        assert doc.status == ParseStatus.PENDING

    def test_document_parsed_at_auto(self):
        """파싱 시간 자동 설정"""
        doc = ParsedDocument()
        assert doc.parsed_at is not None
        assert isinstance(doc.parsed_at, datetime)

    def test_document_all_metadata_fields(self):
        """모든 메타데이터 필드"""
        now = datetime.utcnow()
        doc = ParsedDocument(
            title="Test Document",
            author="Test Author",
            created_date=now,
            modified_date=now,
            page_count=10,
            word_count=1000,
            char_count=5000,
            parser_version="1.0.0",
            parsing_time_ms=150.5,
            metadata={"custom": "value"},
        )
        assert doc.title == "Test Document"
        assert doc.author == "Test Author"
        assert doc.page_count == 10
        assert doc.word_count == 1000
        assert doc.char_count == 5000
        assert doc.parser_version == "1.0.0"
        assert doc.parsing_time_ms == 150.5
        assert doc.metadata["custom"] == "value"

    def test_from_file_path_markdown(self):
        """Markdown 파일 형식 인식"""
        doc = ParsedDocument.from_file_path("/test/readme.md")
        assert doc.source_format == DocumentFormat.MARKDOWN

    def test_from_file_path_uppercase_extension(self):
        """대문자 확장자 처리"""
        doc = ParsedDocument.from_file_path("/test/doc.PDF")
        assert doc.source_format == DocumentFormat.PDF

    def test_to_markdown_without_title(self):
        """제목 없이 Markdown 변환"""
        doc = ParsedDocument(content="Just content")
        md = doc.to_markdown()
        assert "Just content" in md
        assert "# " not in md

    def test_to_markdown_with_sections_no_content(self):
        """섹션이 있고 내용이 없는 경우"""
        section = Section(title="Only Section", level=1, content="Section text")
        doc = ParsedDocument(sections=[section])
        md = doc.to_markdown()
        assert "# Only Section" in md
        assert "Section text" in md

    def test_to_markdown_with_titled_table(self):
        """제목 있는 테이블"""
        table = Table(
            rows=1,
            cols=1,
            title="Revenue Report",
            cells=[TableCell(row=0, col=0, content="100")],
        )
        doc = ParsedDocument(tables=[table])
        md = doc.to_markdown()
        assert "### Revenue Report" in md

    def test_to_markdown_with_untitled_table(self):
        """제목 없는 테이블"""
        table = Table(
            rows=1,
            cols=1,
            cells=[TableCell(row=0, col=0, content="100")],
        )
        doc = ParsedDocument(tables=[table])
        md = doc.to_markdown()
        assert "### Table 1" in md

    def test_to_markdown_multiple_tables(self):
        """여러 테이블"""
        tables = [
            Table(rows=1, cols=1, cells=[TableCell(row=0, col=0, content="A")]),
            Table(rows=1, cols=1, cells=[TableCell(row=0, col=0, content="B")]),
            Table(rows=1, cols=1, cells=[TableCell(row=0, col=0, content="C")]),
        ]
        doc = ParsedDocument(tables=tables)
        md = doc.to_markdown()
        assert "Table 1" in md
        assert "Table 2" in md
        assert "Table 3" in md

    def test_section_to_markdown_without_title(self):
        """제목 없는 섹션 Markdown"""
        section = Section(content="No title section")
        doc = ParsedDocument()
        md = doc._section_to_markdown(section)
        assert "No title section" in md
        assert "#" not in md

    def test_section_to_markdown_without_content(self):
        """내용 없는 섹션 Markdown"""
        section = Section(title="Empty Section", level=1, content="")
        doc = ParsedDocument()
        md = doc._section_to_markdown(section)
        assert "# Empty Section" in md

    def test_section_to_markdown_deep_level(self):
        """깊은 레벨 섹션 (6 제한)"""
        section = Section(title="Deep", level=6, content="Deep content")
        doc = ParsedDocument()
        # base_level=3이면 level=6+3-1=8이지만 최대 6으로 제한
        md = doc._section_to_markdown(section, base_level=3)
        assert "###### Deep" in md  # 최대 6개

    def test_section_to_markdown_with_tables(self):
        """테이블이 있는 섹션"""
        table = Table(
            rows=1,
            cols=2,
            cells=[
                TableCell(row=0, col=0, content="X"),
                TableCell(row=0, col=1, content="Y"),
            ],
        )
        section = Section(title="With Table", level=1, content="Text", tables=[table])
        doc = ParsedDocument()
        md = doc._section_to_markdown(section)
        assert "| X | Y |" in md

    def test_section_to_markdown_with_subsections(self):
        """하위 섹션이 있는 섹션"""
        sub = Section(title="Subsection", level=2, content="Sub content")
        section = Section(
            title="Parent",
            level=1,
            content="Parent content",
            subsections=[sub],
        )
        doc = ParsedDocument()
        md = doc._section_to_markdown(section)
        assert "# Parent" in md
        assert "## Subsection" in md

    def test_is_successful_with_pending(self):
        """PENDING 상태는 실패"""
        doc = ParsedDocument(status=ParseStatus.PENDING)
        assert doc.is_successful is False

    def test_is_successful_with_failed(self):
        """FAILED 상태는 실패"""
        doc = ParsedDocument(status=ParseStatus.FAILED)
        assert doc.is_successful is False

    def test_document_serialization_roundtrip(self):
        """문서 직렬화/역직렬화 왕복"""
        section = Section(title="Test", level=1, content="Content")
        table = Table(rows=1, cols=1, cells=[TableCell(row=0, col=0, content="A")])
        img = ImageRef(caption="Image")

        doc = ParsedDocument(
            source_path="/test/doc.pdf",
            source_format=DocumentFormat.PDF,
            status=ParseStatus.SUCCESS,
            content="Full content",
            title="Test Doc",
            sections=[section],
            tables=[table],
            images=[img],
            metadata={"key": "value"},
        )

        # 직렬화
        data = doc.model_dump()

        # 역직렬화
        restored = ParsedDocument.model_validate(data)

        assert restored.source_path == "/test/doc.pdf"
        assert restored.source_format == DocumentFormat.PDF
        assert restored.status == ParseStatus.SUCCESS
        assert restored.title == "Test Doc"
        assert len(restored.sections) == 1
        assert len(restored.tables) == 1
        assert len(restored.images) == 1
        assert restored.metadata["key"] == "value"

    def test_document_json_roundtrip(self):
        """JSON 직렬화/역직렬화"""
        doc = ParsedDocument(
            title="JSON Test",
            content="Content",
            status=ParseStatus.SUCCESS,
        )

        # JSON으로 변환
        json_str = doc.model_dump_json()
        assert isinstance(json_str, str)

        # JSON에서 복원
        restored = ParsedDocument.model_validate_json(json_str)
        assert restored.title == "JSON Test"


class TestParseResultModel:
    """ParseResult 모델 테스트"""

    def test_parse_result_failure(self):
        """실패 결과"""
        doc = ParsedDocument(status=ParseStatus.FAILED, error_message="Parse error")
        result = ParseResult(
            document=doc,
            success=False,
            message="Failed to parse document",
        )
        assert result.success is False
        assert "Failed" in result.message

    def test_parse_result_multiple_warnings(self):
        """여러 경고"""
        doc = ParsedDocument(status=ParseStatus.PARTIAL)
        result = ParseResult(
            document=doc,
            success=True,
            message="Completed with warnings",
            warnings=[
                "Image extraction failed",
                "Some tables may be incomplete",
                "OCR quality low",
            ],
        )
        assert len(result.warnings) == 3

    def test_parse_result_serialization(self):
        """ParseResult 직렬화"""
        doc = ParsedDocument(status=ParseStatus.SUCCESS)
        result = ParseResult(
            document=doc,
            success=True,
            message="OK",
            warnings=["Minor warning"],
        )
        data = result.model_dump()
        assert data["success"] is True
        assert len(data["warnings"]) == 1


class TestBatchParseResultModel:
    """BatchParseResult 모델 테스트"""

    def test_batch_result_empty(self):
        """빈 배치 결과"""
        batch = BatchParseResult(
            total=0,
            success_count=0,
            failed_count=0,
        )
        assert batch.total == 0
        assert len(batch.results) == 0

    def test_batch_result_mixed(self):
        """혼합 결과"""
        success_doc = ParsedDocument(status=ParseStatus.SUCCESS)
        failed_doc = ParsedDocument(status=ParseStatus.FAILED)
        partial_doc = ParsedDocument(status=ParseStatus.PARTIAL)

        results = [
            ParseResult(document=success_doc, success=True, message="OK"),
            ParseResult(document=failed_doc, success=False, message="Failed"),
            ParseResult(document=partial_doc, success=True, message="Partial"),
        ]

        batch = BatchParseResult(
            total=3,
            success_count=2,
            failed_count=1,
            results=results,
            total_time_ms=500.0,
        )

        assert batch.total == 3
        assert batch.success_count == 2
        assert batch.failed_count == 1
        assert batch.total_time_ms == 500.0
        assert len(batch.results) == 3

    def test_batch_result_validation(self):
        """배치 결과 유효성 검사"""
        with pytest.raises(ValidationError):
            BatchParseResult(total=-1, success_count=0, failed_count=0)

        with pytest.raises(ValidationError):
            BatchParseResult(total=0, success_count=-1, failed_count=0)

    def test_batch_result_serialization(self):
        """배치 결과 직렬화"""
        batch = BatchParseResult(
            total=2,
            success_count=2,
            failed_count=0,
            total_time_ms=100.0,
        )
        data = batch.model_dump()
        assert data["total"] == 2
        assert data["total_time_ms"] == 100.0


class TestEdgeCases:
    """엣지 케이스 테스트"""

    def test_empty_content(self):
        """빈 내용"""
        doc = ParsedDocument(content="")
        assert doc.content == ""
        md = doc.to_markdown()
        assert md is not None

    def test_unicode_content(self):
        """유니코드 내용"""
        doc = ParsedDocument(
            title="한글 제목",
            content="한글 내용입니다. 日本語もOK。",
        )
        md = doc.to_markdown()
        assert "한글 제목" in md
        assert "한글 내용" in md
        assert "日本語" in md

    def test_special_characters_in_table(self):
        """테이블 내 특수문자"""
        cells = [
            TableCell(row=0, col=0, content="<script>"),
            TableCell(row=0, col=1, content="| pipe |"),
            TableCell(row=1, col=0, content="# hash"),
            TableCell(row=1, col=1, content="**bold**"),
        ]
        table = Table(rows=2, cols=2, cells=cells)
        md = table.to_markdown()
        assert "<script>" in md
        assert "# hash" in md

    def test_very_large_table(self):
        """큰 테이블"""
        rows, cols = 100, 10
        cells = [
            TableCell(row=r, col=c, content=f"R{r}C{c}")
            for r in range(rows)
            for c in range(cols)
        ]
        table = Table(rows=rows, cols=cols, cells=cells)
        md = table.to_markdown()
        assert "R0C0" in md
        assert "R99C9" in md

    def test_deeply_nested_sections(self):
        """깊게 중첩된 섹션"""
        # 5단계 중첩
        level5 = Section(title="Level 5", level=5, content="L5")
        level4 = Section(title="Level 4", level=4, content="L4", subsections=[level5])
        level3 = Section(title="Level 3", level=3, content="L3", subsections=[level4])
        level2 = Section(title="Level 2", level=2, content="L2", subsections=[level3])
        level1 = Section(title="Level 1", level=1, content="L1", subsections=[level2])

        doc = ParsedDocument(sections=[level1])
        md = doc.to_markdown()

        assert "# Level 1" in md
        assert "## Level 2" in md

    def test_retry_count_validation(self):
        """재시도 횟수 유효성"""
        doc = ParsedDocument(retry_count=5)
        assert doc.retry_count == 5

        with pytest.raises(ValidationError):
            ParsedDocument(retry_count=-1)

    def test_document_with_error_message(self):
        """에러 메시지 설정"""
        doc = ParsedDocument(
            status=ParseStatus.FAILED,
            error_message="Failed to open file: permission denied",
        )
        assert doc.error_message == "Failed to open file: permission denied"
