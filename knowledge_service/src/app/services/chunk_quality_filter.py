"""
청크 품질 필터 (ChunkQualityGate)

SemanticChunker v2 최종 방어선으로, 임베딩 전에
의미 없는 청크를 걸러낸다.

검증 기준:
1. 최소 토큰 수 (10) / 최소 문자 수 (30)
2. 노이즈 패턴 매칭 (수평선, 빈 헤더, 테이블 구분선 등)
3. 의미있는 문자 비율 (30% 이상)
"""

import logging
import re
from typing import List, Tuple

from app.models.chunk import Chunk

logger = logging.getLogger(__name__)


class ChunkQualityGate:
    """청크 품질 최종 검증 게이트"""

    # 하드 기각 기준
    MIN_TOKEN_COUNT = 10
    MIN_CHAR_LENGTH = 30

    # 노이즈 패턴 (섹션 전처리를 통과한 잔여 노이즈)
    NOISE_PATTERNS = [
        re.compile(r'^[-=*_]{3,}$'),              # 수평선
        re.compile(r'^```\w*$'),                   # 미닫힘 코드블록
        re.compile(r'^#+\s*$'),                    # 빈 헤더
        re.compile(r'^\|[-:\s|]+\|$'),             # 테이블 구분선만
        re.compile(r'^>\s*$'),                     # 빈 인용블록
        re.compile(r'^\s*\[\^?\d+\]:\s*$'),        # 빈 각주
    ]

    def filter(self, chunks: List[Chunk]) -> Tuple[List[Chunk], List[Chunk]]:
        """
        청크 목록을 품질 기준으로 필터링

        Args:
            chunks: 원본 청크 목록

        Returns:
            (통과 청크 목록, 기각 청크 목록)
        """
        passed: List[Chunk] = []
        rejected: List[Chunk] = []

        for chunk in chunks:
            if self._is_quality(chunk):
                passed.append(chunk)
            else:
                rejected.append(chunk)
                logger.debug("Chunk rejected: %r", chunk.content[:50])

        total = len(chunks) or 1
        logger.info(
            "QualityGate: %d passed, %d rejected (%.1f%%)",
            len(passed),
            len(rejected),
            len(rejected) / total * 100,
        )
        return passed, rejected

    def _is_quality(self, chunk: Chunk) -> bool:
        """단일 청크 품질 평가"""
        # 코드/테이블 블록은 QualityGate bypass (TL 피드백: 구조적 의미 보존)
        block_type = chunk.metadata.get("block_type")
        if block_type in ("code", "table"):
            return True

        text = chunk.content.strip()

        # 1. 최소 길이 기준
        if chunk.token_count < self.MIN_TOKEN_COUNT:
            return False
        if len(text) < self.MIN_CHAR_LENGTH:
            return False

        # 2. 노이즈 패턴 매칭
        for pattern in self.NOISE_PATTERNS:
            if pattern.match(text):
                return False

        # 3. 의미있는 단어 비율 (alphanumeric + 한글)
        meaningful = len(re.findall(r'[\w\uac00-\ud7af]', text))
        if len(text) > 0 and meaningful / len(text) < 0.3:
            return False  # 특수문자가 70% 이상이면 기각

        return True
