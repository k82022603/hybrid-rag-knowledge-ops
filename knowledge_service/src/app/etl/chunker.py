"""
Semantic Chunker 모듈

의미 기반 문서 청킹을 수행한다.
- Phase 1 (현재): Rule-based 청킹 (문장/섹션 경계 + 특수 블록 보존)
- Phase 2 (향후): 임베딩 기반 Semantic 청킹

주요 기능:
- 문장 경계 감지 (한국어/영어)
- 섹션 헤더 기반 분할
- 특수 블록 보존 (테이블, 코드 블록)
- 청크 크기 제약 (min/max) 적용
- 오버랩 처리
"""

import logging
import re
import time
from typing import Dict, List, Optional, Tuple

from app.models.chunk import Chunk, ChunkResult
from app.models.parsed_document import ParsedDocument

logger = logging.getLogger(__name__)


class SemanticChunker:
    """
    의미 기반 문서 청킹

    문서를 의미 단위로 분할하여 검색 품질을 최적화한다.
    Phase 1에서는 규칙 기반(문장/섹션 경계)으로 동작하며,
    Phase 2에서 임베딩 기반 시맨틱 분할로 전환 가능하다.

    Attributes:
        chunk_size: 목표 청크 크기 (문자 수)
        chunk_overlap: 청크 간 오버랩 크기 (문자 수)
        min_chunk_size: 최소 청크 크기
        max_chunk_size: 최대 청크 크기

    Example:
        chunker = SemanticChunker(chunk_size=600, chunk_overlap=100)
        result = chunker.chunk_document(parsed_doc)
        for chunk in result.chunks:
            print(chunk.content[:80])
    """

    # 한국어 문장 종결어미 패턴
    KOREAN_SENTENCE_ENDINGS = re.compile(
        r"(?<=[다요임함됨음습까니죠세지])[.!?]"
        r"|(?<=[다요임함됨음습까니죠세지])\s*\n"
    )

    # Markdown 헤더 패턴
    HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

    # 코드 블록 패턴 (```...```)
    CODE_BLOCK_PATTERN = re.compile(r"```[\s\S]*?```", re.MULTILINE)

    # 테이블 블록 패턴 (| 로 시작하는 연속 라인)
    TABLE_BLOCK_PATTERN = re.compile(
        r"(?:^\|.+\|$\n?)+", re.MULTILINE
    )

    # 문장 경계 패턴 (일반적인 문장 종결)
    SENTENCE_BOUNDARY_PATTERN = re.compile(
        r"(?<=[.!?])\s+"
        r"|(?<=[.!?])\n"
        r"|(?<=\n)\n"  # 빈 줄 (단락 경계)
    )

    def __init__(
        self,
        chunk_size: int = 600,
        chunk_overlap: int = 100,
        min_chunk_size: int = 100,
        max_chunk_size: int = 2048,
    ):
        """
        SemanticChunker 초기화

        Args:
            chunk_size: 목표 청크 크기 (문자 수). 기본값 600.
            chunk_overlap: 청크 간 오버랩 크기 (문자 수). 기본값 100.
            min_chunk_size: 최소 청크 크기. 기본값 100.
            max_chunk_size: 최대 청크 크기. 기본값 2048.

        Raises:
            ValueError: 잘못된 파라미터 조합
        """
        if chunk_size <= 0:
            raise ValueError(f"chunk_size must be positive, got {chunk_size}")
        if chunk_overlap < 0:
            raise ValueError(f"chunk_overlap must be non-negative, got {chunk_overlap}")
        if chunk_overlap >= chunk_size:
            raise ValueError(
                f"chunk_overlap ({chunk_overlap}) must be less than "
                f"chunk_size ({chunk_size})"
            )
        if min_chunk_size < 0:
            raise ValueError(f"min_chunk_size must be non-negative, got {min_chunk_size}")
        if max_chunk_size < chunk_size:
            raise ValueError(
                f"max_chunk_size ({max_chunk_size}) must be >= "
                f"chunk_size ({chunk_size})"
            )

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size

        # Phase 2 시맨틱 모드 플래그 (향후 활성화)
        self._use_semantic = False

        logger.info(
            f"SemanticChunker initialized: "
            f"chunk_size={chunk_size}, overlap={chunk_overlap}, "
            f"min={min_chunk_size}, max={max_chunk_size}"
        )

    def chunk_document(self, parsed_document: ParsedDocument) -> ChunkResult:
        """
        ParsedDocument를 청크로 분할

        문서의 content 필드를 사용하여 청킹을 수행한다.
        섹션 정보가 있으면 섹션 경계를 우선적으로 활용한다.

        Args:
            parsed_document: 파싱된 문서 객체

        Returns:
            ChunkResult: 청킹 결과

        Example:
            result = chunker.chunk_document(parsed_doc)
            print(f"Total chunks: {result.total_chunks}")
        """
        start_time = time.time()
        document_id = str(parsed_document.id)

        # 섹션이 있으면 섹션 기반 청킹
        if parsed_document.sections:
            chunks = self._chunk_with_sections(parsed_document, document_id)
        else:
            chunks = self.chunk_text(
                text=parsed_document.content,
                document_id=document_id,
            )

        processing_time_ms = (time.time() - start_time) * 1000

        # 통계 계산
        total_chunks = len(chunks)
        avg_token_count = (
            sum(c.token_count for c in chunks) / total_chunks
            if total_chunks > 0
            else 0.0
        )

        result = ChunkResult(
            document_id=document_id,
            chunks=chunks,
            total_chunks=total_chunks,
            avg_token_count=avg_token_count,
            processing_time_ms=processing_time_ms,
        )

        logger.info(
            f"Document chunked: {total_chunks} chunks, "
            f"avg tokens: {avg_token_count:.1f}, "
            f"time: {processing_time_ms:.1f}ms"
        )

        return result

    def chunk_text(self, text: str, document_id: str = "") -> List[Chunk]:
        """
        텍스트를 청크로 분할 (핵심 메서드)

        1. 특수 블록(테이블, 코드)을 식별하여 보존
        2. 일반 텍스트를 문장/단락 경계에서 분할
        3. 청크 크기 제약 적용
        4. 오버랩 처리

        Args:
            text: 분할할 텍스트
            document_id: 원본 문서 ID

        Returns:
            List[Chunk]: 생성된 청크 목록
        """
        if not text or not text.strip():
            return []

        # 1. 특수 블록 식별
        special_blocks = self._identify_special_blocks(text)

        # 2. 텍스트를 세그먼트로 분할 (특수 블록과 일반 텍스트)
        segments = self._split_into_segments(text, special_blocks)

        # 3. 세그먼트를 청크로 조합
        raw_chunks = self._assemble_chunks(segments)

        # 4. 청크 객체 생성
        chunks = []
        current_heading = None

        for idx, (content, start_char, end_char) in enumerate(raw_chunks):
            # 헤딩 추적
            heading = self._extract_heading(text[:start_char])
            if heading:
                current_heading = heading

            token_count = self._estimate_token_count(content)

            chunk = Chunk(
                content=content,
                document_id=document_id,
                chunk_index=idx,
                start_char=start_char,
                end_char=end_char,
                token_count=token_count,
                heading=current_heading,
            )
            chunks.append(chunk)

        return chunks

    def _chunk_with_sections(
        self, parsed_document: ParsedDocument, document_id: str
    ) -> List[Chunk]:
        """
        섹션 정보를 활용한 청킹

        각 섹션의 content를 개별적으로 청킹하되,
        섹션 제목을 heading 메타데이터에 포함시킨다.

        Args:
            parsed_document: 파싱된 문서
            document_id: 문서 ID

        Returns:
            List[Chunk]: 청크 목록
        """
        all_chunks: List[Chunk] = []
        global_index = 0
        # 전체 텍스트에서 현재까지의 오프셋 추적
        global_offset = 0

        for section in parsed_document.sections:
            section_chunks = self._chunk_section_recursive(
                section=section,
                document_id=document_id,
                global_index=global_index,
                global_offset=global_offset,
            )

            for chunk in section_chunks:
                chunk.chunk_index = global_index
                global_index += 1
                all_chunks.append(chunk)

            # 섹션 내용 길이만큼 오프셋 이동
            if section.content:
                global_offset += len(section.content)

        return all_chunks

    def _chunk_section_recursive(
        self,
        section,
        document_id: str,
        global_index: int,
        global_offset: int,
        parent_heading: Optional[str] = None,
    ) -> List[Chunk]:
        """
        섹션을 재귀적으로 청킹

        Args:
            section: 섹션 객체
            document_id: 문서 ID
            global_index: 전역 청크 인덱스
            global_offset: 전역 문자 오프셋
            parent_heading: 부모 섹션 헤딩

        Returns:
            List[Chunk]: 청크 목록
        """
        chunks: List[Chunk] = []
        heading = section.title or parent_heading

        # 섹션 본문 청킹
        if section.content and section.content.strip():
            text_chunks = self.chunk_text(
                text=section.content,
                document_id=document_id,
            )
            for chunk in text_chunks:
                chunk.heading = heading
                chunk.start_char += global_offset
                chunk.end_char += global_offset
                if section.page_start is not None:
                    chunk.page_number = section.page_start
                chunks.append(chunk)

        # 하위 섹션 재귀 처리
        sub_offset = global_offset
        if section.content:
            sub_offset += len(section.content)

        for subsection in section.subsections:
            sub_chunks = self._chunk_section_recursive(
                section=subsection,
                document_id=document_id,
                global_index=global_index + len(chunks),
                global_offset=sub_offset,
                parent_heading=heading,
            )
            chunks.extend(sub_chunks)
            if subsection.content:
                sub_offset += len(subsection.content)

        return chunks

    def _identify_special_blocks(self, text: str) -> List[Tuple[int, int, str]]:
        """
        특수 블록(테이블, 코드) 위치 식별

        테이블과 코드 블록은 분할하지 않고 단일 청크로 유지해야 한다.

        Args:
            text: 원본 텍스트

        Returns:
            List[Tuple[int, int, str]]: (시작위치, 끝위치, 블록타입) 목록
        """
        blocks: List[Tuple[int, int, str]] = []

        # 코드 블록 식별
        for match in self.CODE_BLOCK_PATTERN.finditer(text):
            blocks.append((match.start(), match.end(), "code"))

        # 테이블 블록 식별
        for match in self.TABLE_BLOCK_PATTERN.finditer(text):
            table_text = match.group()
            # 최소 2줄 이상이고 파이프 문자가 포함된 경우에만 테이블로 인식
            lines = [l for l in table_text.strip().split("\n") if l.strip()]
            if len(lines) >= 2 and all("|" in l for l in lines):
                blocks.append((match.start(), match.end(), "table"))

        # 시작 위치 기준 정렬
        blocks.sort(key=lambda b: b[0])

        # 중복 제거 (코드 블록 내 테이블 등)
        filtered: List[Tuple[int, int, str]] = []
        for block in blocks:
            if not filtered:
                filtered.append(block)
            else:
                last = filtered[-1]
                # 현재 블록이 이전 블록에 포함되면 건너뛰기
                if block[0] >= last[0] and block[1] <= last[1]:
                    continue
                # 겹치는 경우 이전 블록 유지
                if block[0] < last[1]:
                    continue
                filtered.append(block)

        return filtered

    def _split_into_segments(
        self, text: str, special_blocks: List[Tuple[int, int, str]]
    ) -> List[Tuple[str, int, int, str]]:
        """
        텍스트를 세그먼트로 분할

        특수 블록과 일반 텍스트를 구분하여 세그먼트 목록을 생성한다.

        Args:
            text: 원본 텍스트
            special_blocks: 특수 블록 위치 목록

        Returns:
            List[Tuple[str, int, int, str]]: (내용, 시작위치, 끝위치, 타입) 목록
                타입: "text", "code", "table"
        """
        segments: List[Tuple[str, int, int, str]] = []
        current_pos = 0

        for start, end, block_type in special_blocks:
            # 특수 블록 전의 일반 텍스트
            if current_pos < start:
                normal_text = text[current_pos:start]
                if normal_text.strip():
                    segments.append((normal_text, current_pos, start, "text"))

            # 특수 블록 자체
            block_text = text[start:end]
            if block_text.strip():
                segments.append((block_text, start, end, block_type))

            current_pos = end

        # 마지막 특수 블록 이후의 일반 텍스트
        if current_pos < len(text):
            remaining = text[current_pos:]
            if remaining.strip():
                segments.append((remaining, current_pos, len(text), "text"))

        # 특수 블록이 없으면 전체를 하나의 세그먼트로
        if not segments and text.strip():
            segments.append((text, 0, len(text), "text"))

        return segments

    def _assemble_chunks(
        self, segments: List[Tuple[str, int, int, str]]
    ) -> List[Tuple[str, int, int]]:
        """
        세그먼트를 청크로 조합

        일반 텍스트는 문장 경계에서 분할하고,
        특수 블록은 분리하지 않고 단일 청크로 유지한다.

        Args:
            segments: 세그먼트 목록

        Returns:
            List[Tuple[str, int, int]]: (내용, 시작위치, 끝위치) 목록
        """
        raw_chunks: List[Tuple[str, int, int]] = []

        for content, seg_start, seg_end, seg_type in segments:
            if seg_type in ("code", "table"):
                # 특수 블록: 그대로 하나의 청크로
                # max_chunk_size 초과해도 분할하지 않음
                raw_chunks.append((content.strip(), seg_start, seg_end))
            else:
                # 일반 텍스트: 문장 경계 기반 분할
                text_chunks = self._split_text_by_sentences(
                    content, seg_start
                )
                raw_chunks.extend(text_chunks)

        return raw_chunks

    def _split_text_by_sentences(
        self, text: str, offset: int
    ) -> List[Tuple[str, int, int]]:
        """
        텍스트를 문장 경계에서 분할

        chunk_size를 목표로 문장 단위로 텍스트를 분할한다.
        오버랩 처리도 수행한다.

        Args:
            text: 분할할 텍스트
            offset: 원본 텍스트에서의 오프셋

        Returns:
            List[Tuple[str, int, int]]: (내용, 시작위치, 끝위치) 목록
        """
        if not text.strip():
            return []

        # 문장 분리
        sentences = self._split_sentences(text)

        if not sentences:
            return []

        chunks: List[Tuple[str, int, int]] = []
        current_sentences: List[str] = []
        current_length = 0
        chunk_start_in_text = 0  # 현재 청크의 text 내 시작 위치

        for sentence in sentences:
            sentence_len = len(sentence)

            # 현재 청크에 추가하면 chunk_size 초과하는지 확인
            if current_length + sentence_len > self.chunk_size and current_sentences:
                # 현재 청크 저장
                chunk_content = "".join(current_sentences).strip()
                if len(chunk_content) >= self.min_chunk_size:
                    chunk_end_in_text = chunk_start_in_text + len(
                        "".join(current_sentences)
                    )
                    chunks.append((
                        chunk_content,
                        offset + chunk_start_in_text,
                        offset + chunk_end_in_text,
                    ))

                # 오버랩 처리: 마지막 몇 문장을 다음 청크에 포함
                overlap_sentences, overlap_length = self._get_overlap_sentences(
                    current_sentences
                )
                # 새 청크 시작 위치 계산
                consumed = "".join(current_sentences)
                chunk_start_in_text += len(consumed) - overlap_length

                current_sentences = list(overlap_sentences)
                current_length = overlap_length

            current_sentences.append(sentence)
            current_length += sentence_len

        # 마지막 청크 처리
        if current_sentences:
            chunk_content = "".join(current_sentences).strip()
            if chunk_content:
                # min_chunk_size 미만이면 이전 청크에 병합 시도
                if len(chunk_content) < self.min_chunk_size and chunks:
                    # 이전 청크와 병합
                    prev_content, prev_start, prev_end = chunks[-1]
                    merged = prev_content + " " + chunk_content
                    if len(merged) <= self.max_chunk_size:
                        chunks[-1] = (merged, prev_start, offset + len(text))
                    else:
                        # 병합하면 max 초과 -> 별도 청크로
                        chunk_end_in_text = chunk_start_in_text + len(
                            "".join(current_sentences)
                        )
                        chunks.append((
                            chunk_content,
                            offset + chunk_start_in_text,
                            offset + chunk_end_in_text,
                        ))
                else:
                    chunk_end_in_text = chunk_start_in_text + len(
                        "".join(current_sentences)
                    )
                    chunks.append((
                        chunk_content,
                        offset + chunk_start_in_text,
                        offset + chunk_end_in_text,
                    ))

        # 텍스트가 너무 짧아서 청크가 안 만들어진 경우
        if not chunks and text.strip():
            chunks.append((text.strip(), offset, offset + len(text)))

        return chunks

    def _split_sentences(self, text: str) -> List[str]:
        """
        텍스트를 문장 단위로 분리

        한국어와 영어 문장 경계를 모두 인식한다.

        Args:
            text: 분리할 텍스트

        Returns:
            List[str]: 문장 목록 (구분자 포함)
        """
        if not text:
            return []

        # 복합 패턴으로 문장 경계 분할
        # 마침표/물음표/느낌표 뒤의 공백 또는 줄바꿈에서 분할
        # 한국어 종결어미(다, 요, 임, 함 등) 뒤의 마침표도 인식
        pattern = re.compile(
            r"(?<=[.!?])\s+"          # 기본 문장 종결 + 공백
            r"|(?<=[.!?])\n"          # 기본 문장 종결 + 줄바꿈
            r"|(?<=\n)\n"             # 빈 줄 (단락 경계)
            r"|(?<=\n)(?=#{1,6}\s)"   # Markdown 헤더 앞
        )

        # split 대신 finditer로 위치를 추적하여 구분자를 포함한 분할
        parts = []
        last_end = 0

        for match in pattern.finditer(text):
            start = match.start()
            end = match.end()
            # 문장 + 구분자를 하나의 단위로
            part = text[last_end:end]
            if part:
                parts.append(part)
            last_end = end

        # 나머지 부분
        if last_end < len(text):
            remaining = text[last_end:]
            if remaining:
                parts.append(remaining)

        # 빈 문장 제거하되, 공백만 있는 것도 유지 (위치 추적 정확도)
        return [p for p in parts if p.strip()]

    def _get_overlap_sentences(
        self, sentences: List[str]
    ) -> Tuple[List[str], int]:
        """
        오버랩에 포함될 문장 결정

        뒤에서부터 chunk_overlap 크기만큼의 문장을 선택한다.

        Args:
            sentences: 현재 청크의 문장 목록

        Returns:
            Tuple[List[str], int]: (오버랩 문장 목록, 총 길이)
        """
        if not sentences or self.chunk_overlap <= 0:
            return [], 0

        overlap_sentences: List[str] = []
        overlap_length = 0

        for sentence in reversed(sentences):
            if overlap_length + len(sentence) > self.chunk_overlap:
                break
            overlap_sentences.insert(0, sentence)
            overlap_length += len(sentence)

        # 최소 1문장은 오버랩에 포함하지 않음 (무한 루프 방지)
        if len(overlap_sentences) == len(sentences):
            if len(overlap_sentences) > 1:
                overlap_sentences = overlap_sentences[1:]
                overlap_length -= len(sentences[0])
            else:
                return [], 0

        return overlap_sentences, overlap_length

    def _extract_heading(self, text_before: str) -> Optional[str]:
        """
        텍스트 이전 부분에서 가장 마지막 헤딩 추출

        Markdown # 헤더 패턴을 매칭하여 현재 위치의 섹션 헤더를 결정한다.

        Args:
            text_before: 현재 위치 이전의 텍스트

        Returns:
            Optional[str]: 헤딩 텍스트 또는 None
        """
        if not text_before:
            return None

        matches = list(self.HEADING_PATTERN.finditer(text_before))
        if matches:
            last_match = matches[-1]
            return last_match.group(2).strip()

        return None

    def _estimate_token_count(self, text: str) -> int:
        """
        토큰 수 추정

        정확한 토큰 카운팅 대신 근사치를 사용한다.
        - 영어: 단어 수 기반 (단어당 약 1.3 토큰)
        - 한국어: 문자 수 기반 (약 3문자당 1토큰)
        - 혼합: 가중 평균

        Args:
            text: 토큰 수를 추정할 텍스트

        Returns:
            int: 추정 토큰 수
        """
        if not text:
            return 0

        # 한국어 문자 수
        korean_chars = len(re.findall(r"[\uac00-\ud7af]", text))
        # 비한국어 단어 수
        non_korean_text = re.sub(r"[\uac00-\ud7af]", " ", text)
        english_words = len(non_korean_text.split())

        # 한국어: ~3문자당 1토큰, 영어: ~1.3단어당 1토큰
        korean_tokens = korean_chars / 3.0
        english_tokens = english_words * 1.3

        return max(1, int(korean_tokens + english_tokens))
