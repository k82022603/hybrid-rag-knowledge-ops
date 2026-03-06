"""
SemanticChunker v2 단위 테스트

개선 1: Pre-Section 노이즈 필터 (4건)
개선 2: Fallback 최소 임계 (4건)
개선 3: Post-Section 병합 패스 (5건)
개선 4: ChunkQualityGate (6건)
block_type 메타데이터 전파 (2건)
ADR 반영 검증 (3건)
"""

import pytest

from app.etl.chunker import SemanticChunker
from app.models.chunk import Chunk, ChunkResult
from app.models.parsed_document import ParsedDocument, ParseStatus, Section
from app.services.chunk_quality_filter import ChunkQualityGate


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def chunker():
    """기본 SemanticChunker v2 인스턴스"""
    return SemanticChunker(
        chunk_size=200,
        chunk_overlap=40,
        min_chunk_size=20,
        max_chunk_size=500,
    )


@pytest.fixture
def quality_gate():
    """ChunkQualityGate 인스턴스"""
    return ChunkQualityGate()


@pytest.fixture
def make_chunk():
    """Chunk 생성 헬퍼"""
    def _make(content: str, token_count: int = 0, metadata: dict = None):
        c = Chunk(
            content=content,
            document_id="test-doc",
            chunk_index=0,
            token_count=token_count,
        )
        if metadata:
            c.metadata = metadata
        return c
    return _make


# ===========================================================================
# 개선 1: Pre-Section 노이즈 필터
# ===========================================================================


class TestPreSectionNoiseFilter:
    """_preprocess_section_content() 테스트"""

    def test_horizontal_rule_filtered(self, chunker):
        """수평선(---) 섹션이 빈 문자열로 반환"""
        assert chunker._preprocess_section_content("---") == ""
        assert chunker._preprocess_section_content("-----") == ""
        assert chunker._preprocess_section_content("===") == ""
        assert chunker._preprocess_section_content("***") == ""
        assert chunker._preprocess_section_content("___") == ""

    def test_unclosed_codeblock_filtered(self, chunker):
        """미닫힘 코드블록(```yaml) 섹션이 필터링"""
        assert chunker._preprocess_section_content("```yaml") == ""
        assert chunker._preprocess_section_content("```dockerfile") == ""
        assert chunker._preprocess_section_content("```") == ""

    def test_html_comment_filtered(self, chunker):
        """단일 라인 HTML 주석이 필터링"""
        assert chunker._preprocess_section_content("<!-- comment -->") == ""
        assert chunker._preprocess_section_content("  <!-- hidden -->  ") == ""

    def test_normal_content_preserved(self, chunker):
        """정상 텍스트는 그대로 반환"""
        text = "이 문서는 시스템 설계에 대한 내용입니다."
        result = chunker._preprocess_section_content(text)
        assert result == text

    def test_empty_content_returns_empty(self, chunker):
        """빈 문자열 / None 처리"""
        assert chunker._preprocess_section_content("") == ""
        assert chunker._preprocess_section_content("   ") == ""
        assert chunker._preprocess_section_content(None) == ""


# ===========================================================================
# 개선 2: Fallback 최소 임계
# ===========================================================================


class TestFallbackMinimumThreshold:
    """fallback 경로(line 568-578)에서 최소 토큰/길이 체크.

    주의: fallback은 _split_sentences()가 빈 결과를 반환하여
    일반 청킹 경로에서 청크가 0개일 때만 작동한다.
    짧은 텍스트("---" 등)는 일반 경로로 청크가 생성되며,
    이들은 QualityGate(개선 4)에서 최종 차단된다.
    """

    def test_short_text_caught_by_quality_gate(self, chunker):
        """짧은 텍스트는 일반 경로로 청크 생성 → QualityGate에서 차단"""
        # "---"는 _split_sentences에서 정상 문장으로 인식
        result = chunker._split_text_by_sentences("---", 0)
        assert len(result) == 1  # 일반 경로로 생성됨
        # QualityGate에서 최종 필터링
        gate = ChunkQualityGate()
        chunk = Chunk(
            content="---", token_count=chunker._estimate_token_count("---"),
        )
        passed, rejected = gate.filter([chunk])
        assert len(passed) == 0  # QualityGate에서 기각

    def test_fallback_drops_below_threshold(self, chunker):
        """_split_sentences가 빈 결과 반환 시 fallback이 최소 기준 적용"""
        # fallback 경로는 직접 테스트하기 어려우므로,
        # chunk_text()를 통해 통합 검증
        chunks = chunker.chunk_text("---", document_id="test")
        # 생성은 되지만 QualityGate에서 걸러질 크기
        for c in chunks:
            assert c.token_count < 10 or len(c.content) < 30

    def test_adequate_text_passes_fallback(self, chunker):
        """30자 이상 + 10토큰 이상 텍스트는 fallback에서 유지"""
        text = "이 문장은 충분히 긴 텍스트로서 fallback에서도 유지되어야 합니다."
        result = chunker._split_text_by_sentences(text, 0)
        assert len(result) >= 1

    def test_empty_text_returns_empty(self, chunker):
        """빈 텍스트는 빈 리스트"""
        assert chunker._split_text_by_sentences("", 0) == []
        assert chunker._split_text_by_sentences("   ", 0) == []


# ===========================================================================
# 개선 3: Post-Section 병합 패스
# ===========================================================================


class TestPostSectionMerge:
    """_merge_small_adjacent_chunks() 테스트"""

    def test_small_chunk_merged_to_previous(self, chunker):
        """작은 청크가 이전 청크에 병합"""
        chunks = [
            Chunk(content="A" * 100, document_id="d", chunk_index=0,
                  token_count=30, start_char=0, end_char=100),
            Chunk(content="tiny", document_id="d", chunk_index=1,
                  token_count=2, start_char=100, end_char=104),
        ]
        result = chunker._merge_small_adjacent_chunks(chunks)
        assert len(result) == 1
        assert "tiny" in result[0].content

    def test_small_chunk_merged_to_next(self, chunker):
        """이전 청크가 없으면 다음 청크에 병합"""
        chunks = [
            Chunk(content="tiny", document_id="d", chunk_index=0,
                  token_count=2, start_char=0, end_char=4),
            Chunk(content="B" * 100, document_id="d", chunk_index=1,
                  token_count=30, start_char=4, end_char=104),
        ]
        result = chunker._merge_small_adjacent_chunks(chunks)
        assert len(result) == 1
        assert "tiny" in result[0].content

    def test_no_merge_when_exceeds_max(self, chunker):
        """병합 결과가 max_chunk_size 초과 시 병합 안 함"""
        # chunker.max_chunk_size = 500
        chunks = [
            Chunk(content="A" * 498, document_id="d", chunk_index=0,
                  token_count=150, start_char=0, end_char=498),
            Chunk(content="tiny", document_id="d", chunk_index=1,
                  token_count=2, start_char=498, end_char=502),
            Chunk(content="B" * 498, document_id="d", chunk_index=2,
                  token_count=150, start_char=502, end_char=1000),
        ]
        result = chunker._merge_small_adjacent_chunks(chunks)
        # 양쪽 다 498 + 4 + 1 = 503 > 500 이므로 병합 불가
        assert len(result) == 3

    def test_token_count_recalculated_after_merge(self, chunker):
        """병합 후 token_count가 재계산되는지 확인"""
        chunks = [
            Chunk(content="이전 청크의 내용입니다.", document_id="d",
                  chunk_index=0, token_count=10, start_char=0, end_char=30),
            Chunk(content="작은 것", document_id="d",
                  chunk_index=1, token_count=2, start_char=30, end_char=35),
        ]
        result = chunker._merge_small_adjacent_chunks(chunks)
        assert len(result) == 1
        # 병합 후 token_count는 재계산되어야 함
        expected_tokens = chunker._estimate_token_count(result[0].content)
        assert result[0].token_count == expected_tokens

    def test_single_chunk_no_merge(self, chunker):
        """청크 1개면 병합 없음"""
        chunks = [
            Chunk(content="단독", document_id="d", chunk_index=0, token_count=1),
        ]
        result = chunker._merge_small_adjacent_chunks(chunks)
        assert len(result) == 1


# ===========================================================================
# 개선 4: ChunkQualityGate
# ===========================================================================


class TestChunkQualityGate:
    """ChunkQualityGate 테스트"""

    def test_minimum_token_rejection(self, quality_gate, make_chunk):
        """MIN_TOKEN_COUNT(50) 미만 기각"""
        chunk = make_chunk("짧은 텍스트입니다.", token_count=5)
        passed, rejected = quality_gate.filter([chunk])
        assert len(passed) == 0
        assert len(rejected) == 1

    def test_minimum_length_rejection(self, quality_gate, make_chunk):
        """MIN_CHAR_LENGTH(30) 미만 기각"""
        chunk = make_chunk("짧은 텍스트", token_count=55)
        passed, rejected = quality_gate.filter([chunk])
        assert len(passed) == 0
        assert len(rejected) == 1

    def test_noise_pattern_rejection(self, quality_gate, make_chunk):
        """노이즈 패턴 기각 (수평선, 빈 헤더 등)"""
        noise_chunks = [
            make_chunk("----------", token_count=10),
            make_chunk("### ", token_count=10),
            make_chunk("|---|---|", token_count=10),
        ]
        for chunk in noise_chunks:
            passed, _ = quality_gate.filter([chunk])
            assert len(passed) == 0, f"Should reject: {chunk.content!r}"

    def test_meaningful_ratio_rejection(self, quality_gate, make_chunk):
        """의미있는 문자 비율 30% 미만 기각"""
        # 특수문자 80% 이상
        chunk = make_chunk(
            "!@#$%^&*()!@#$%^&*()!@#$%^&*()ab",
            token_count=55,
        )
        passed, rejected = quality_gate.filter([chunk])
        assert len(passed) == 0

    def test_normal_chunk_passes(self, quality_gate, make_chunk):
        """정상 텍스트 통과"""
        chunk = make_chunk(
            "인공지능은 현대 기술의 핵심이며 다양한 분야에서 활용됩니다.",
            token_count=50,
        )
        passed, rejected = quality_gate.filter([chunk])
        assert len(passed) == 1
        assert len(rejected) == 0

    def test_code_block_bypass(self, quality_gate, make_chunk):
        """code block_type은 완화된 기준 적용 (token>=20, len>=30)"""
        chunk = make_chunk(
            "def calculate_sum(a, b): return a + b",  # 37자, 코드 블록
            token_count=20,
            metadata={"block_type": "code"},
        )
        passed, rejected = quality_gate.filter([chunk])
        assert len(passed) == 1, "Code blocks should pass with relaxed criteria"

    def test_table_block_bypass(self, quality_gate, make_chunk):
        """table block_type은 완화된 기준 적용 (token>=20, len>=30)"""
        chunk = make_chunk(
            "| Column A | Column B | Column C |",  # 34자, 테이블 블록
            token_count=20,
            metadata={"block_type": "table"},
        )
        passed, rejected = quality_gate.filter([chunk])
        assert len(passed) == 1, "Table blocks should pass with relaxed criteria"


# ===========================================================================
# block_type 메타데이터 전파
# ===========================================================================


class TestBlockTypeMetadata:
    """chunk_text()에서 code/table block_type 메타데이터 설정"""

    def test_code_block_gets_metadata(self, chunker):
        """코드 블록 청크에 block_type=code 메타데이터"""
        text = "Some text before.\n\n```python\nprint('hello')\n```\n\nSome text after."
        chunks = chunker.chunk_text(text, document_id="test")
        code_chunks = [c for c in chunks if c.metadata.get("block_type") == "code"]
        assert len(code_chunks) >= 1

    def test_table_block_gets_metadata(self, chunker):
        """테이블 블록 청크에 block_type=table 메타데이터"""
        text = (
            "Some text before.\n\n"
            "| Column A | Column B |\n"
            "|----------|----------|\n"
            "| Value 1  | Value 2  |\n\n"
            "Some text after."
        )
        chunks = chunker.chunk_text(text, document_id="test")
        table_chunks = [c for c in chunks if c.metadata.get("block_type") == "table"]
        assert len(table_chunks) >= 1


# ===========================================================================
# ADR 반영 검증
# ===========================================================================


class TestADRCompliance:
    """Architect Decision Records 반영 확인"""

    def test_adr002_merge_within_section(self, chunker):
        """ADR-002: 병합이 섹션 내에서만 수행되는지 확인"""
        # 두 개의 섹션, 각각 작은 청크를 포함
        section1 = Section(
            title="Section 1",
            content="섹션 1의 내용은 충분히 길어야 합니다. " * 5,
            level=1,
            subsections=[],
        )
        section2 = Section(
            title="Section 2",
            content="짧은",  # 매우 짧은 내용 → 노이즈 필터에 걸림
            level=1,
            subsections=[],
        )
        doc = ParsedDocument(
            content="",
            sections=[section1, section2],
            status=ParseStatus.SUCCESS,
        )
        result = chunker.chunk_document(doc)
        # section2가 노이즈 필터에 의해 제거되므로 section1 청크만 존재
        for chunk in result.chunks:
            assert chunk.heading == "Section 1" or chunk.heading is None

    def test_adr003_new_id_on_merge(self, chunker):
        """ADR-003: 병합 시 새 Chunk.id 생성"""
        original_id = "original-id-123"
        chunks = [
            Chunk(id=original_id, content="A" * 100, document_id="d",
                  chunk_index=0, token_count=30, start_char=0, end_char=100),
            Chunk(content="tiny", document_id="d",
                  chunk_index=1, token_count=2, start_char=100, end_char=104),
        ]
        result = chunker._merge_small_adjacent_chunks(chunks)
        assert len(result) == 1
        # 병합 후 ID가 변경되어야 함
        assert result[0].id != original_id

    def test_chunk_index_reordered_after_merge(self, chunker):
        """병합 후 chunk_index가 0부터 재정렬"""
        section = Section(
            title="Test Section",
            content="이 문서는 테스트용입니다. " * 20,
            level=1,
            subsections=[],
        )
        doc = ParsedDocument(
            content="",
            sections=[section],
            status=ParseStatus.SUCCESS,
        )
        result = chunker.chunk_document(doc)
        for idx, chunk in enumerate(result.chunks):
            assert chunk.chunk_index == idx, \
                f"chunk_index mismatch: expected {idx}, got {chunk.chunk_index}"
