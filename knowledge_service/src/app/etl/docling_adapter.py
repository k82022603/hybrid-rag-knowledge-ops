"""
Docling 어댑터 모듈

Docling 라이브러리를 사용하여 문서를 파싱하고
ParsedDocument 형식으로 변환하는 어댑터
"""

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from app.models.parsed_document import (
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


class DoclingAdapter:
    """
    Docling 문서 파싱 어댑터

    Docling 라이브러리를 래핑하여 PDF, DOCX, PPTX 문서를 파싱하고
    표준 ParsedDocument 형식으로 변환합니다.

    Attributes:
        allowed_formats: 지원하는 파일 형식 목록
        ocr_enabled: OCR 사용 여부
    """

    # Docling 지원 형식
    DOCLING_SUPPORTED_FORMATS = {
        DocumentFormat.PDF,
        DocumentFormat.DOCX,
        DocumentFormat.PPTX,
    }

    def __init__(
        self,
        ocr_enabled: bool = True,
        table_structure_enabled: bool = True,
        image_extraction_enabled: bool = True,
    ):
        """
        DoclingAdapter 초기화

        Args:
            ocr_enabled: OCR 사용 여부 (스캔된 문서 처리)
            table_structure_enabled: 표 구조 인식 사용 여부
            image_extraction_enabled: 이미지 추출 사용 여부
        """
        self.ocr_enabled = ocr_enabled
        self.table_structure_enabled = table_structure_enabled
        self.image_extraction_enabled = image_extraction_enabled
        self._converter = None
        self._version = None

    @property
    def converter(self):
        """Docling DocumentConverter 인스턴스 (지연 로딩)"""
        if self._converter is None:
            self._converter = self._create_converter()
        return self._converter

    @property
    def version(self) -> str:
        """Docling 버전 반환"""
        if self._version is None:
            try:
                import docling

                self._version = getattr(docling, "__version__", "unknown")
            except ImportError:
                self._version = "not installed"
        return self._version

    def _create_converter(self):
        """Docling DocumentConverter 생성"""
        try:
            from docling.datamodel.base_models import InputFormat
            from docling.document_converter import DocumentConverter, PdfFormatOption
            from docling.datamodel.pipeline_options import PdfPipelineOptions

            # PDF 파이프라인 옵션 설정
            pipeline_options = PdfPipelineOptions(
                do_ocr=self.ocr_enabled,
                do_table_structure=self.table_structure_enabled,
            )

            # DocumentConverter 생성
            converter = DocumentConverter(
                allowed_formats=[
                    InputFormat.PDF,
                    InputFormat.DOCX,
                    InputFormat.PPTX,
                ],
                format_options={
                    InputFormat.PDF: PdfFormatOption(
                        pipeline_options=pipeline_options,
                    ),
                },
            )

            logger.info(f"Docling converter initialized (version: {self.version})")
            return converter

        except ImportError as e:
            logger.error(f"Failed to import Docling: {e}")
            raise ImportError(
                "Docling is not installed. "
                "Please install it with: pip install docling"
            ) from e
        except Exception as e:
            logger.error(f"Failed to create Docling converter: {e}")
            raise

    def supports_format(self, file_format: DocumentFormat) -> bool:
        """지정된 형식을 지원하는지 확인"""
        return file_format in self.DOCLING_SUPPORTED_FORMATS

    def parse(
        self,
        file_path: Union[str, Path],
        timeout: Optional[float] = None,
    ) -> ParseResult:
        """
        문서 파싱

        Args:
            file_path: 파싱할 파일 경로
            timeout: 타임아웃 (초)

        Returns:
            ParseResult: 파싱 결과
        """
        path = Path(file_path)
        start_time = time.time()

        # 기본 문서 객체 생성
        doc = ParsedDocument.from_file_path(str(path))
        doc.parser_version = f"docling-{self.version}"

        # 파일 존재 확인
        if not path.exists():
            doc.status = ParseStatus.FAILED
            doc.error_message = f"File not found: {path}"
            return ParseResult(
                document=doc,
                success=False,
                message=doc.error_message,
            )

        # 형식 지원 확인
        if not self.supports_format(doc.source_format):
            doc.status = ParseStatus.FAILED
            doc.error_message = f"Unsupported format for Docling: {doc.source_format}"
            return ParseResult(
                document=doc,
                success=False,
                message=doc.error_message,
            )

        try:
            # Docling으로 파싱
            result = self.converter.convert(str(path))

            # 결과 변환
            doc = self._convert_result(doc, result)
            doc.status = ParseStatus.SUCCESS

            # 소요 시간 기록
            elapsed_ms = (time.time() - start_time) * 1000
            doc.parsing_time_ms = elapsed_ms

            logger.info(
                f"Document parsed successfully: {path.name} "
                f"(pages: {doc.page_count}, tables: {len(doc.tables)}, "
                f"time: {elapsed_ms:.0f}ms)"
            )

            return ParseResult(
                document=doc,
                success=True,
                message=f"Successfully parsed {path.name}",
            )

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            doc.parsing_time_ms = elapsed_ms
            doc.status = ParseStatus.FAILED
            doc.error_message = str(e)

            logger.error(f"Failed to parse document {path.name}: {e}")

            return ParseResult(
                document=doc,
                success=False,
                message=f"Failed to parse: {e}",
            )

    def _convert_result(
        self, doc: ParsedDocument, result: Any
    ) -> ParsedDocument:
        """Docling 결과를 ParsedDocument로 변환"""
        try:
            # 문서 객체 접근
            docling_doc = result.document

            # 텍스트 추출
            doc.content = self._extract_text(docling_doc)

            # 메타데이터 추출
            doc = self._extract_metadata(doc, docling_doc)

            # 섹션 추출
            doc.sections = self._extract_sections(docling_doc)

            # 표 추출
            doc.tables = self._extract_tables(docling_doc)

            # 이미지 추출
            if self.image_extraction_enabled:
                doc.images = self._extract_images(docling_doc)

            # 통계 계산
            doc.word_count = len(doc.content.split())
            doc.char_count = len(doc.content)

            return doc

        except Exception as e:
            logger.warning(f"Error converting Docling result: {e}")
            # 부분 성공으로 처리
            if doc.content:
                doc.status = ParseStatus.PARTIAL
            else:
                raise
            return doc

    def _extract_text(self, docling_doc: Any) -> str:
        """텍스트 추출"""
        try:
            # Docling Document의 export_to_text() 또는 text 속성 사용
            if hasattr(docling_doc, "export_to_text"):
                return docling_doc.export_to_text()
            elif hasattr(docling_doc, "text"):
                return docling_doc.text
            elif hasattr(docling_doc, "export_to_markdown"):
                return docling_doc.export_to_markdown()
            else:
                # 대체 방법: 모든 텍스트 요소 추출
                texts = []
                if hasattr(docling_doc, "texts"):
                    for text_item in docling_doc.texts:
                        if hasattr(text_item, "text"):
                            texts.append(text_item.text)
                return "\n".join(texts)
        except Exception as e:
            logger.warning(f"Error extracting text: {e}")
            return ""

    def _extract_metadata(
        self, doc: ParsedDocument, docling_doc: Any
    ) -> ParsedDocument:
        """메타데이터 추출"""
        try:
            # 문서 메타데이터 접근
            if hasattr(docling_doc, "metadata"):
                meta = docling_doc.metadata
                if hasattr(meta, "title"):
                    doc.title = meta.title or doc.title
                if hasattr(meta, "author"):
                    doc.author = meta.author
                if hasattr(meta, "creation_date"):
                    doc.created_date = meta.creation_date
                if hasattr(meta, "modification_date"):
                    doc.modified_date = meta.modification_date

            # 페이지 수 추출
            if hasattr(docling_doc, "pages"):
                doc.page_count = len(list(docling_doc.pages))
            elif hasattr(docling_doc, "page_count"):
                doc.page_count = docling_doc.page_count

        except Exception as e:
            logger.warning(f"Error extracting metadata: {e}")

        return doc

    def _extract_sections(self, docling_doc: Any) -> List[Section]:
        """섹션 추출"""
        sections = []
        try:
            if hasattr(docling_doc, "body"):
                body = docling_doc.body
                if hasattr(body, "iterate_items"):
                    current_section = None
                    current_content = []

                    for item, level in body.iterate_items():
                        item_type = type(item).__name__

                        if "heading" in item_type.lower() or "title" in item_type.lower():
                            # 이전 섹션 저장
                            if current_section is not None:
                                current_section.content = "\n".join(current_content)
                                sections.append(current_section)

                            # 새 섹션 시작
                            title = getattr(item, "text", str(item))
                            current_section = Section(
                                title=title,
                                level=min(level + 1, 6),
                                content="",
                            )
                            current_content = []

                        elif hasattr(item, "text"):
                            current_content.append(item.text)

                    # 마지막 섹션 저장
                    if current_section is not None:
                        current_section.content = "\n".join(current_content)
                        sections.append(current_section)

        except Exception as e:
            logger.warning(f"Error extracting sections: {e}")

        return sections

    def _extract_tables(self, docling_doc: Any) -> List[Table]:
        """표 추출"""
        tables = []
        try:
            # tables 속성 접근
            if hasattr(docling_doc, "tables"):
                for i, docling_table in enumerate(docling_doc.tables):
                    table = self._convert_table(docling_table, i)
                    if table:
                        tables.append(table)

        except Exception as e:
            logger.warning(f"Error extracting tables: {e}")

        return tables

    def _convert_table(self, docling_table: Any, index: int) -> Optional[Table]:
        """Docling 표를 Table 모델로 변환"""
        try:
            cells = []
            max_row = 0
            max_col = 0

            # 셀 추출
            if hasattr(docling_table, "cells"):
                for cell in docling_table.cells:
                    row = getattr(cell, "row", 0)
                    col = getattr(cell, "col", 0)
                    text = getattr(cell, "text", str(cell))
                    is_header = getattr(cell, "is_header", row == 0)

                    cells.append(
                        TableCell(
                            row=row,
                            col=col,
                            content=text,
                            is_header=is_header,
                            rowspan=getattr(cell, "rowspan", 1),
                            colspan=getattr(cell, "colspan", 1),
                        )
                    )

                    max_row = max(max_row, row)
                    max_col = max(max_col, col)

            # Markdown 형식 추출
            markdown = None
            if hasattr(docling_table, "export_to_markdown"):
                markdown = docling_table.export_to_markdown()

            # 캡션 추출
            caption = None
            if hasattr(docling_table, "caption"):
                caption = docling_table.caption

            return Table(
                title=caption,
                cells=cells,
                rows=max_row + 1,
                cols=max_col + 1,
                markdown=markdown,
            )

        except Exception as e:
            logger.warning(f"Error converting table {index}: {e}")
            return None

    def _extract_images(self, docling_doc: Any) -> List[ImageRef]:
        """이미지 참조 추출"""
        images = []
        try:
            if hasattr(docling_doc, "pictures") or hasattr(docling_doc, "images"):
                picture_list = getattr(
                    docling_doc, "pictures", getattr(docling_doc, "images", [])
                )
                for i, picture in enumerate(picture_list):
                    image_ref = ImageRef(
                        caption=getattr(picture, "caption", None),
                        alt_text=getattr(picture, "alt_text", f"Image {i+1}"),
                        page_number=getattr(picture, "page_number", None),
                    )

                    # 위치 정보 추출
                    if hasattr(picture, "bbox") or hasattr(picture, "bounding_box"):
                        bbox = getattr(
                            picture, "bbox", getattr(picture, "bounding_box", None)
                        )
                        if bbox:
                            image_ref.position = {
                                "x": getattr(bbox, "x", getattr(bbox, "left", 0)),
                                "y": getattr(bbox, "y", getattr(bbox, "top", 0)),
                                "width": getattr(bbox, "width", 0),
                                "height": getattr(bbox, "height", 0),
                            }

                    images.append(image_ref)

        except Exception as e:
            logger.warning(f"Error extracting images: {e}")

        return images


class DoclingAdapterError(Exception):
    """Docling 어댑터 예외"""

    pass
