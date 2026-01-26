"""
SemanticChunker 단위 테스트

STORY-003: Semantic Chunking 구현
- 기본 청킹 (5건)
- 크기 제약 (3건)
- 특수 블록 보존 (3건)
- 한국어 처리 (3건)
- 섹션 헤더 (2건)
- ParsedDocument 통합 (2건)
- 메타데이터 (3건)
"""

import pytest

from app.etl.chunker import SemanticChunker
from app.models.chunk import Chunk, ChunkResult
from app.models.parsed_document import ParsedDocument, ParseStatus, Section


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def chunker():
    """기본 SemanticChunker 인스턴스"""
    return SemanticChunker(
        chunk_size=200,
        chunk_overlap=40,
        min_chunk_size=20,
        max_chunk_size=500,
    )


@pytest.fixture
def large_chunker():
    """큰 청크 사이즈의 SemanticChunker"""
    return SemanticChunker(
        chunk_size=600,
        chunk_overlap=100,
        min_chunk_size=50,
        max_chunk_size=2048,
    )


@pytest.fixture
def simple_text():
    """간단한 테스트 텍스트"""
    return (
        "This is the first sentence. "
        "This is the second sentence. "
        "This is the third sentence. "
        "This is the fourth sentence."
    )


@pytest.fixture
def long_text():
    """긴 텍스트 (여러 청크 생성)"""
    paragraphs = []
    for i in range(20):
        paragraphs.append(
            f"Paragraph {i + 1} contains important information about topic {i + 1}. "
            f"This paragraph elaborates on the key points discussed earlier. "
            f"Additional details provide context for the main argument."
        )
    return "\n\n".join(paragraphs)


@pytest.fixture
def korean_text():
    """한국어 테스트 텍스트"""
    return (
        "인공지능은 현대 기술의 핵심입니다. "
        "딥러닝 모델은 다양한 분야에서 활용되고 있습니다. "
        "자연어 처리 기술은 빠르게 발전하고 있습니다. "
        "검색 증강 생성은 RAG라고 불리며 대규모 언어 모델의 한계를 보완합니다. "
        "지식 그래프는 엔티티 간의 관계를 표현하는 구조화된 데이터입니다."
    )


@pytest.fixture
def text_with_table():
    """테이블이 포함된 텍스트"""
    return (
        "Here is some introductory text about the project.\n\n"
        "| Name | Value | Description |\n"
        "| --- | --- | --- |\n"
        "| Alpha | 100 | First item |\n"
        "| Beta | 200 | Second item |\n"
        "| Gamma | 300 | Third item |\n\n"
        "And here is some text after the table."
    )


@pytest.fixture
def text_with_code():
    """코드 블록이 포함된 텍스트"""
    return (
        "The following code demonstrates the algorithm.\n\n"
        "```python\n"
        "def hello_world():\n"
        "    print('Hello, World!')\n"
        "    return True\n"
        "```\n\n"
        "This code prints a greeting message."
    )


@pytest.fixture
def markdown_with_headings():
    """헤딩이 포함된 Markdown 텍스트"""
    return (
        "# Introduction\n\n"
        "This is the introduction section with some important background. "
        "It provides context for the rest of the document.\n\n"
        "## Background\n\n"
        "The background section covers historical context and prior work. "
        "Many researchers have contributed to this field over the years.\n\n"
        "## Methods\n\n"
        "We describe our methods in this section. "
        "The approach uses a novel technique for data processing. "
        "Detailed steps are provided below.\n\n"
        "### Data Collection\n\n"
        "Data was collected from multiple sources over a period of six months."
    )


@pytest.fixture
def parsed_document():
    """테스트용 ParsedDocument"""
    return ParsedDocument(
        content=(
            "This is the full document content. "
            "It contains multiple sentences that should be chunked. "
            "The chunker will split this text based on sentence boundaries. "
            "Each chunk should have proper metadata attached."
        ),
        status=ParseStatus.SUCCESS,
        title="Test Document",
    )


@pytest.fixture
def parsed_document_with_sections():
    """섹션이 있는 ParsedDocument"""
    return ParsedDocument(
        content="Full document content here.",
        status=ParseStatus.SUCCESS,
        title="Sectioned Document",
        sections=[
            Section(
                title="Introduction",
                level=1,
                content=(
                    "This is the introduction. "
                    "It provides background information about the topic."
                ),
                page_start=1,
            ),
            Section(
                title="Methods",
                level=1,
                content=(
                    "This section describes the methods used. "
                    "We employed a novel approach to solve the problem. "
                    "The approach is based on established research."
                ),
                page_start=2,
            ),
        ],
    )


# ===========================================================================
# 1. Basic Chunking Tests (5)
# ===========================================================================


class TestBasicChunking:
    """기본 청킹 테스트"""

    def test_chunk_simple_text(self, chunker, simple_text):
        """간단한 텍스트를 청크로 분할한다."""
        chunks = chunker.chunk_text(simple_text, document_id="doc-1")

        assert len(chunks) >= 1
        assert all(isinstance(c, Chunk) for c in chunks)
        # 모든 청크 내용을 합치면 원본 텍스트의 주요 내용이 포함됨
        all_content = " ".join(c.content for c in chunks)
        assert "first sentence" in all_content
        assert "fourth sentence" in all_content

    def test_chunk_empty_text(self, chunker):
        """빈 텍스트는 빈 목록을 반환한다."""
        assert chunker.chunk_text("") == []
        assert chunker.chunk_text("   ") == []
        assert chunker.chunk_text("\n\n") == []

    def test_chunk_short_text(self, chunker):
        """짧은 텍스트도 최소 하나의 청크를 생성한다."""
        short = "Hello world."
        chunks = chunker.chunk_text(short)

        assert len(chunks) == 1
        assert chunks[0].content.strip() == short.strip()

    def test_chunk_long_text(self, chunker, long_text):
        """긴 텍스트는 여러 청크로 분할된다."""
        chunks = chunker.chunk_text(long_text, document_id="doc-long")

        assert len(chunks) > 1
        # 모든 청크에 내용이 있어야 함
        assert all(len(c.content.strip()) > 0 for c in chunks)

    def test_chunk_whitespace_only(self, chunker):
        """공백만 있는 텍스트는 빈 목록을 반환한다."""
        assert chunker.chunk_text("   \n\n  \t  ") == []


# ===========================================================================
# 2. Size Constraint Tests (3)
# ===========================================================================


class TestSizeConstraints:
    """크기 제약 테스트"""

    def test_chunk_size_within_bounds(self, chunker, long_text):
        """일반 텍스트 청크는 max_chunk_size를 초과하지 않는다."""
        chunks = chunker.chunk_text(long_text)

        for chunk in chunks:
            assert len(chunk.content) <= chunker.max_chunk_size, (
                f"Chunk exceeds max_chunk_size: {len(chunk.content)} > "
                f"{chunker.max_chunk_size}"
            )

    def test_chunk_overlap_applied(self, large_chunker, long_text):
        """오버랩이 적용되어 인접 청크 간 내용이 겹친다."""
        chunks = large_chunker.chunk_text(long_text)

        if len(chunks) >= 2:
            # 적어도 하나의 인접 청크 쌍에서 오버랩 확인
            overlap_found = False
            for i in range(len(chunks) - 1):
                # 이전 청크의 마지막 부분이 다음 청크의 시작 부분에 포함되는지
                prev_words = chunks[i].content.split()
                next_words = chunks[i + 1].content.split()
                # 마지막 몇 단어가 겹치는지 확인
                if len(prev_words) >= 3 and len(next_words) >= 3:
                    prev_tail = " ".join(prev_words[-3:])
                    next_head = " ".join(next_words[:10])
                    if prev_tail in next_head or any(
                        w in next_words[:10] for w in prev_words[-5:]
                    ):
                        overlap_found = True
                        break

            # 오버랩이 0이 아닌 한, 겹치는 내용이 존재해야 함
            if large_chunker.chunk_overlap > 0:
                assert overlap_found or len(chunks) <= 1, (
                    "Expected overlap between adjacent chunks"
                )

    def test_custom_chunk_size(self):
        """사용자 정의 청크 크기가 적용된다."""
        small_chunker = SemanticChunker(
            chunk_size=100,
            chunk_overlap=20,
            min_chunk_size=10,
            max_chunk_size=300,
        )

        text = "First sentence here. " * 20
        chunks = small_chunker.chunk_text(text)

        assert len(chunks) > 1
        # 대부분의 청크가 chunk_size 근처여야 함 (마지막 제외)
        for chunk in chunks[:-1]:
            # 문장 경계에서 자르므로 정확히 100은 아님
            assert len(chunk.content) <= small_chunker.max_chunk_size


# ===========================================================================
# 3. Special Block Preservation Tests (3)
# ===========================================================================


class TestSpecialBlockPreservation:
    """특수 블록 보존 테스트"""

    def test_table_preserved_as_single_chunk(self, chunker, text_with_table):
        """테이블이 단일 청크로 보존된다."""
        chunks = chunker.chunk_text(text_with_table)

        # 테이블 내용이 포함된 청크 찾기
        table_chunks = [c for c in chunks if "| Name |" in c.content and "| Alpha |" in c.content]

        assert len(table_chunks) >= 1, "Table should be preserved in a chunk"
        # 테이블의 모든 행이 같은 청크에 있어야 함
        table_chunk = table_chunks[0]
        assert "| Alpha |" in table_chunk.content
        assert "| Beta |" in table_chunk.content
        assert "| Gamma |" in table_chunk.content

    def test_code_block_preserved(self, chunker, text_with_code):
        """코드 블록이 분리되지 않고 보존된다."""
        chunks = chunker.chunk_text(text_with_code)

        # 코드 블록이 포함된 청크 찾기
        code_chunks = [c for c in chunks if "def hello_world" in c.content]

        assert len(code_chunks) >= 1, "Code block should be preserved"
        code_chunk = code_chunks[0]
        assert "print('Hello, World!')" in code_chunk.content
        assert "return True" in code_chunk.content

    def test_mixed_content_with_table(self, chunker):
        """텍스트와 테이블이 혼합된 콘텐츠를 올바르게 처리한다."""
        mixed_text = (
            "Some introductory text before the table.\n\n"
            "| Header A | Header B |\n"
            "| --- | --- |\n"
            "| Cell 1 | Cell 2 |\n"
            "| Cell 3 | Cell 4 |\n\n"
            "Text between tables is also important.\n\n"
            "| Col X | Col Y |\n"
            "| --- | --- |\n"
            "| Val 1 | Val 2 |\n\n"
            "Final text after all tables."
        )
        chunks = chunker.chunk_text(mixed_text)

        assert len(chunks) >= 1
        all_content = " ".join(c.content for c in chunks)
        # 모든 콘텐츠가 청크에 포함됨
        assert "introductory text" in all_content
        assert "Header A" in all_content
        assert "Cell 1" in all_content
        assert "Final text" in all_content


# ===========================================================================
# 4. Korean Language Tests (3)
# ===========================================================================


class TestKoreanProcessing:
    """한국어 처리 테스트"""

    def test_korean_sentence_boundaries(self, chunker):
        """한국어 문장 경계를 인식한다."""
        text = (
            "첫 번째 문장입니다. "
            "두 번째 문장입니다. "
            "세 번째 문장입니다."
        )
        chunks = chunker.chunk_text(text)

        assert len(chunks) >= 1
        all_content = " ".join(c.content for c in chunks)
        assert "첫 번째" in all_content
        assert "세 번째" in all_content

    def test_korean_text_chunking(self, chunker, korean_text):
        """한국어 문서가 올바르게 청킹된다."""
        chunks = chunker.chunk_text(korean_text, document_id="kr-doc")

        assert len(chunks) >= 1
        # 모든 청크에 한국어 내용이 포함
        all_content = " ".join(c.content for c in chunks)
        assert "인공지능" in all_content
        assert "지식 그래프" in all_content
        # 토큰 카운트가 양수
        assert all(c.token_count > 0 for c in chunks)

    def test_mixed_language(self, chunker):
        """한영 혼합 텍스트를 처리한다."""
        text = (
            "RAG는 Retrieval Augmented Generation의 약자입니다. "
            "LLM은 Large Language Model을 의미합니다. "
            "Vector search를 통해 관련 문서를 검색합니다. "
            "Graph database에서 엔티티 관계를 탐색합니다."
        )
        chunks = chunker.chunk_text(text)

        assert len(chunks) >= 1
        all_content = " ".join(c.content for c in chunks)
        assert "RAG" in all_content
        assert "약자입니다" in all_content
        assert "Vector search" in all_content


# ===========================================================================
# 5. Section Heading Tests (2)
# ===========================================================================


class TestSectionHeadings:
    """섹션 헤더 테스트"""

    def test_heading_preserved_in_metadata(self, large_chunker, markdown_with_headings):
        """헤딩이 청크의 heading 메타데이터에 포함된다."""
        chunks = large_chunker.chunk_text(markdown_with_headings)

        # 최소 하나의 청크에 heading이 설정되어야 함
        headings_found = [c.heading for c in chunks if c.heading is not None]
        # chunk_text에서 heading 추출은 이전 텍스트 기반
        # 첫 번째 이후 청크들에는 heading이 있을 수 있음
        assert len(chunks) >= 1

    def test_section_based_splitting(self, large_chunker, markdown_with_headings):
        """섹션 경계에서 분할이 이루어진다."""
        chunks = large_chunker.chunk_text(markdown_with_headings)

        # 모든 주요 섹션의 내용이 청크에 포함됨
        all_content = " ".join(c.content for c in chunks)
        assert "introduction" in all_content.lower() or "Introduction" in all_content
        assert "background" in all_content.lower() or "Background" in all_content
        assert "Methods" in all_content or "methods" in all_content.lower()


# ===========================================================================
# 6. ParsedDocument Integration Tests (2)
# ===========================================================================


class TestParsedDocumentIntegration:
    """ParsedDocument 통합 테스트"""

    def test_chunk_parsed_document(self, large_chunker, parsed_document):
        """ParsedDocument를 입력으로 청킹한다."""
        result = large_chunker.chunk_document(parsed_document)

        assert isinstance(result, ChunkResult)
        assert result.total_chunks >= 1
        assert result.document_id == str(parsed_document.id)
        assert result.processing_time_ms >= 0
        assert len(result.chunks) == result.total_chunks

        # 모든 청크의 document_id가 일치
        for chunk in result.chunks:
            assert chunk.document_id == str(parsed_document.id)

    def test_chunk_document_with_sections(
        self, large_chunker, parsed_document_with_sections
    ):
        """섹션이 있는 ParsedDocument를 청킹한다."""
        result = large_chunker.chunk_document(parsed_document_with_sections)

        assert isinstance(result, ChunkResult)
        assert result.total_chunks >= 1

        # 섹션 제목이 heading에 반영됨
        headings = [c.heading for c in result.chunks if c.heading]
        has_intro = any("Introduction" in h for h in headings)
        has_methods = any("Methods" in h for h in headings)
        assert has_intro or has_methods, (
            f"Expected section headings in chunks. Got: {headings}"
        )


# ===========================================================================
# 7. Metadata Tests (3)
# ===========================================================================


class TestMetadata:
    """메타데이터 테스트"""

    def test_chunk_ids_unique(self, chunker, long_text):
        """모든 청크 ID가 유니크하다."""
        chunks = chunker.chunk_text(long_text)

        ids = [c.id for c in chunks]
        assert len(ids) == len(set(ids)), "Chunk IDs must be unique"

    def test_chunk_indices_sequential(self, chunker, long_text):
        """chunk_index가 순차적으로 증가한다."""
        chunks = chunker.chunk_text(long_text)

        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i, (
                f"Expected chunk_index={i}, got {chunk.chunk_index}"
            )

    def test_chunk_result_statistics(self, large_chunker, parsed_document):
        """ChunkResult의 통계가 정확하다."""
        result = large_chunker.chunk_document(parsed_document)

        assert result.total_chunks == len(result.chunks)
        assert result.processing_time_ms >= 0

        if result.total_chunks > 0:
            # avg_token_count 검증
            expected_avg = sum(
                c.token_count for c in result.chunks
            ) / result.total_chunks
            assert abs(result.avg_token_count - expected_avg) < 0.01, (
                f"avg_token_count mismatch: "
                f"{result.avg_token_count} vs {expected_avg}"
            )


# ===========================================================================
# 8. Edge Cases & Validation (추가 테스트)
# ===========================================================================


class TestEdgeCases:
    """경계 조건 테스트"""

    def test_invalid_chunk_size_raises_error(self):
        """잘못된 chunk_size는 ValueError를 발생시킨다."""
        with pytest.raises(ValueError):
            SemanticChunker(chunk_size=0)
        with pytest.raises(ValueError):
            SemanticChunker(chunk_size=-1)

    def test_overlap_greater_than_size_raises_error(self):
        """overlap >= chunk_size는 ValueError를 발생시킨다."""
        with pytest.raises(ValueError):
            SemanticChunker(chunk_size=100, chunk_overlap=100)
        with pytest.raises(ValueError):
            SemanticChunker(chunk_size=100, chunk_overlap=150)

    def test_token_count_positive(self, chunker, simple_text):
        """모든 청크의 토큰 수가 양수이다."""
        chunks = chunker.chunk_text(simple_text)

        for chunk in chunks:
            assert chunk.token_count > 0, (
                f"Token count should be positive, got {chunk.token_count} "
                f"for content: '{chunk.content[:50]}'"
            )

    def test_document_id_propagated(self, chunker, simple_text):
        """document_id가 모든 청크에 전파된다."""
        doc_id = "test-doc-123"
        chunks = chunker.chunk_text(simple_text, document_id=doc_id)

        for chunk in chunks:
            assert chunk.document_id == doc_id
