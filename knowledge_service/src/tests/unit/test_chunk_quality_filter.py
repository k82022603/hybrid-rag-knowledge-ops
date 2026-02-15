"""
ChunkQualityGate 단위 테스트

TEST_MODE=docker pytest src/tests/unit/test_chunk_quality_filter.py -v
"""

import pytest

from app.models.chunk import Chunk
from app.services.chunk_quality_filter import ChunkQualityGate


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def gate():
    """ChunkQualityGate 인스턴스"""
    return ChunkQualityGate()


def make_chunk(content: str, token_count: int = 50, metadata: dict = None) -> Chunk:
    """테스트용 청크 생성 헬퍼"""
    return Chunk(
        content=content,
        token_count=token_count,
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# 정상 통과 테스트
# ---------------------------------------------------------------------------


class TestPassCases:
    """품질 통과 케이스"""

    def test_normal_text(self, gate):
        chunk = make_chunk("이것은 정상적인 한국어 텍스트입니다. 충분한 길이를 가지고 있습니다.", 20)
        passed, rejected = gate.filter([chunk])
        assert len(passed) == 1
        assert len(rejected) == 0

    def test_english_text(self, gate):
        chunk = make_chunk(
            "This is a normal English text with enough tokens and meaningful content.",
            15,
        )
        passed, rejected = gate.filter([chunk])
        assert len(passed) == 1

    def test_mixed_content(self, gate):
        chunk = make_chunk("API 게이트웨이 설정: SpringBoot에서 /api/v1/** 경로 라우팅", 15)
        passed, rejected = gate.filter([chunk])
        assert len(passed) == 1

    def test_code_block_passes(self, gate):
        """코드 블록: 완화된 기준 적용 (token>=3, len>=10)"""
        chunk = make_chunk(
            "def hello():\n    return 'world'",
            5,
            metadata={"block_type": "code"},
        )
        passed, rejected = gate.filter([chunk])
        assert len(passed) == 1

    def test_table_block_passes(self, gate):
        """테이블 블록: 완화된 기준 적용"""
        chunk = make_chunk(
            "| Name | Value |\n| --- | --- |\n| key | 123 |",
            8,
            metadata={"block_type": "table"},
        )
        passed, rejected = gate.filter([chunk])
        assert len(passed) == 1


# ---------------------------------------------------------------------------
# 기각 테스트 - 최소 길이
# ---------------------------------------------------------------------------


class TestMinimumLength:
    """최소 길이 기준 테스트"""

    def test_empty_text(self, gate):
        chunk = make_chunk("", 0)
        passed, rejected = gate.filter([chunk])
        assert len(passed) == 0
        assert len(rejected) == 1

    def test_whitespace_only(self, gate):
        chunk = make_chunk("   \n\t  ", 0)
        passed, rejected = gate.filter([chunk])
        assert len(passed) == 0

    def test_below_min_tokens(self, gate):
        """token_count < 10 기각"""
        chunk = make_chunk("짧은 텍스트입니다", 5)
        passed, rejected = gate.filter([chunk])
        assert len(passed) == 0

    def test_below_min_chars(self, gate):
        """len(text) < 30 기각"""
        chunk = make_chunk("a" * 29, 15)  # 29자 < 30
        passed, rejected = gate.filter([chunk])
        assert len(passed) == 0

    def test_exact_minimum(self, gate):
        """정확히 최소 기준"""
        text = "한" * 30  # 30자, 한글
        chunk = make_chunk(text, 10)
        passed, rejected = gate.filter([chunk])
        assert len(passed) == 1


# ---------------------------------------------------------------------------
# 기각 테스트 - 노이즈 패턴
# ---------------------------------------------------------------------------


class TestNoisePatterns:
    """노이즈 패턴 매칭 테스트"""

    def test_horizontal_rule_dashes(self, gate):
        chunk = make_chunk("---", 10)
        passed, rejected = gate.filter([chunk])
        assert len(passed) == 0

    def test_horizontal_rule_equals(self, gate):
        chunk = make_chunk("====", 10)
        passed, rejected = gate.filter([chunk])
        assert len(passed) == 0

    def test_horizontal_rule_asterisks(self, gate):
        chunk = make_chunk("***", 10)
        passed, rejected = gate.filter([chunk])
        assert len(passed) == 0

    def test_unclosed_code_block(self, gate):
        chunk = make_chunk("```python", 10)
        passed, rejected = gate.filter([chunk])
        assert len(passed) == 0

    def test_empty_header(self, gate):
        chunk = make_chunk("## ", 10)
        passed, rejected = gate.filter([chunk])
        assert len(passed) == 0

    def test_table_separator_only(self, gate):
        chunk = make_chunk("|---|---|", 10)
        passed, rejected = gate.filter([chunk])
        assert len(passed) == 0

    def test_empty_blockquote(self, gate):
        chunk = make_chunk("> ", 10)
        passed, rejected = gate.filter([chunk])
        assert len(passed) == 0


# ---------------------------------------------------------------------------
# 기각 테스트 - 의미있는 문자 비율
# ---------------------------------------------------------------------------


class TestMeaningfulRatio:
    """의미있는 문자 비율 테스트 (30% 이상)"""

    def test_mostly_special_chars(self, gate):
        """특수문자 70% 이상이면 기각"""
        text = "!@#$%^&*()!@#$%^&*()!@#$%^&*()!!" + "a" * 5  # 약 14% 의미
        chunk = make_chunk(text, 15)
        passed, rejected = gate.filter([chunk])
        assert len(passed) == 0

    def test_enough_meaningful_chars(self, gate):
        """의미있는 문자 30% 이상이면 통과"""
        text = "abc가나다" + "!@#" * 3  # 6/15 = 40%
        chunk = make_chunk(text * 3, 15)  # 길이 충족
        passed, rejected = gate.filter([chunk])
        assert len(passed) == 1


# ---------------------------------------------------------------------------
# 배치 필터링 테스트
# ---------------------------------------------------------------------------


class TestBatchFilter:
    """배치 처리 테스트"""

    def test_mixed_quality(self, gate):
        """양호/불량 혼합 필터링"""
        chunks = [
            make_chunk("정상적인 텍스트입니다. 충분한 길이와 토큰을 가지고 있습니다.", 20),
            make_chunk("", 0),
            make_chunk("---", 10),
            make_chunk("또 다른 정상 텍스트. 이것도 충분히 길고 의미가 있는 문장입니다.", 25),
        ]
        passed, rejected = gate.filter(chunks)
        assert len(passed) == 2
        assert len(rejected) == 2

    def test_empty_list(self, gate):
        passed, rejected = gate.filter([])
        assert len(passed) == 0
        assert len(rejected) == 0

    def test_all_pass(self, gate):
        chunks = [
            make_chunk(f"정상 텍스트 번호 {i}. 충분한 길이를 가진 의미있는 문장입니다.", 20)
            for i in range(5)
        ]
        passed, rejected = gate.filter(chunks)
        assert len(passed) == 5
        assert len(rejected) == 0

    def test_all_reject(self, gate):
        chunks = [make_chunk("", 0), make_chunk("---", 10), make_chunk("***", 10)]
        passed, rejected = gate.filter(chunks)
        assert len(passed) == 0
        assert len(rejected) == 3


# ---------------------------------------------------------------------------
# 코드/테이블 블록 경계 테스트
# ---------------------------------------------------------------------------


class TestBlockTypeEdgeCases:
    """코드/테이블 블록 특수 기준"""

    def test_code_block_too_short(self, gate):
        """코드 블록이라도 token<3 또는 len<10이면 기각"""
        chunk = make_chunk("x=1", 2, metadata={"block_type": "code"})
        passed, rejected = gate.filter([chunk])
        assert len(passed) == 0

    def test_code_block_exactly_minimum(self, gate):
        """코드 블록 최소 기준 충족"""
        chunk = make_chunk("x = 10 + 1", 3, metadata={"block_type": "code"})
        passed, rejected = gate.filter([chunk])
        assert len(passed) == 1

    def test_table_too_short(self, gate):
        chunk = make_chunk("| a |", 2, metadata={"block_type": "table"})
        passed, rejected = gate.filter([chunk])
        assert len(passed) == 0

    def test_normal_block_not_relaxed(self, gate):
        """일반 블록은 완화 기준 미적용"""
        chunk = make_chunk("short", 5, metadata={"block_type": "text"})
        passed, rejected = gate.filter([chunk])
        assert len(passed) == 0
