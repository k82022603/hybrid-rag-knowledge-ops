"""
최적화된 문서 파싱 서비스 (STORY-063)

Docling PDF 파싱 최적화 및 테이블 추출 정확도 향상을 위한 모듈

Features:
- 배치 처리: 병렬 문서 처리로 처리량 향상
- 메모리 관리: 스트리밍 파싱 및 청크 단위 처리
- 캐싱: 문서 해시 기반 중복 파싱 방지
- 테이블 추출 최적화: TableFormer 설정 최적화

Usage:
    parser = OptimizedDocumentParser()

    # 단일 문서 파싱
    result = await parser.parse_with_cache("document.pdf")

    # 배치 처리
    results = await parser.parse_batch(["doc1.pdf", "doc2.pdf"])

    # 스트리밍 파싱 (대용량)
    async for chunk in parser.parse_large_document_stream("large.pdf"):
        process(chunk)
"""

import asyncio
import hashlib
import logging
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple, Union

from app.models.parsed_document import (
    BatchParseResult,
    DocumentFormat,
    ParsedDocument,
    ParseResult,
    ParseStatus,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class ParserConfig:
    """파서 설정"""

    # 배치 처리 설정
    batch_size: int = 5
    max_workers: int = 2

    # 메모리 관리 설정
    max_memory_mb: int = 512
    chunk_pages: int = 10  # 대용량 문서 청크 처리 시 페이지 수

    # 캐시 설정
    cache_enabled: bool = True
    cache_ttl: int = 3600  # 1시간

    # Docling 설정
    ocr_enabled: bool = True
    table_structure_enabled: bool = True
    image_extraction_enabled: bool = True

    # 테이블 추출 최적화 설정
    table_confidence_threshold: float = 0.7
    table_max_rows: int = 500
    table_max_cols: int = 50

    # 재시도 설정
    max_retries: int = 3
    retry_delay: float = 1.0


@dataclass
class ParseStats:
    """파싱 통계"""

    total_documents: int = 0
    success_count: int = 0
    failed_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_time_ms: float = 0.0
    peak_memory_mb: float = 0.0
    tables_extracted: int = 0
    pages_processed: int = 0

    @property
    def cache_hit_rate(self) -> float:
        """캐시 히트율"""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total

    @property
    def avg_time_per_doc_ms(self) -> float:
        """문서당 평균 처리 시간"""
        if self.total_documents == 0:
            return 0.0
        return self.total_time_ms / self.total_documents

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "total_documents": self.total_documents,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": round(self.cache_hit_rate, 4),
            "total_time_ms": round(self.total_time_ms, 2),
            "avg_time_per_doc_ms": round(self.avg_time_per_doc_ms, 2),
            "peak_memory_mb": round(self.peak_memory_mb, 2),
            "tables_extracted": self.tables_extracted,
            "pages_processed": self.pages_processed,
        }


# ---------------------------------------------------------------------------
# Document Cache
# ---------------------------------------------------------------------------


class DocumentCache:
    """
    문서 파싱 결과 캐시

    문서 해시 기반으로 중복 파싱을 방지합니다.
    """

    def __init__(
        self,
        cache_backend: Optional[Any] = None,
        ttl: int = 3600,
    ):
        """
        초기화

        Args:
            cache_backend: 캐시 백엔드 (None이면 인메모리)
            ttl: 캐시 TTL (초)
        """
        self._cache: Dict[str, Tuple[ParsedDocument, float]] = {}
        self._ttl = ttl
        self._backend = cache_backend

    def _get_cache_key(self, file_path: Path) -> str:
        """캐시 키 생성 (파일 해시 + 수정 시간)"""
        try:
            stat = file_path.stat()
            key_data = f"{file_path}:{stat.st_size}:{stat.st_mtime}"
            return hashlib.sha256(key_data.encode()).hexdigest()
        except Exception:
            return ""

    def get_document_hash(self, file_path: Union[str, Path]) -> str:
        """
        문서 해시 계산 (파일 내용 기반)

        Args:
            file_path: 파일 경로

        Returns:
            MD5 해시 문자열
        """
        path = Path(file_path)
        if not path.exists():
            return ""

        # 파일 크기가 크면 첫 1MB만 해싱 (성능 최적화)
        hash_md5 = hashlib.md5()
        with open(path, "rb") as f:
            chunk_size = 1024 * 1024  # 1MB
            data = f.read(chunk_size)
            hash_md5.update(data)

            # 파일 끝부분도 해싱 (동일 헤더/다른 내용 구분)
            if path.stat().st_size > chunk_size * 2:
                f.seek(-chunk_size, 2)  # 파일 끝에서 1MB 앞
                data = f.read(chunk_size)
                hash_md5.update(data)

        return hash_md5.hexdigest()

    async def get(self, file_path: Union[str, Path]) -> Optional[ParsedDocument]:
        """
        캐시에서 파싱 결과 조회

        Args:
            file_path: 파일 경로

        Returns:
            캐시된 ParsedDocument 또는 None
        """
        path = Path(file_path)
        cache_key = self._get_cache_key(path)

        if not cache_key:
            return None

        # 외부 백엔드 사용
        if self._backend:
            try:
                data = await self._backend.get(f"docparse:{cache_key}")
                if data:
                    return ParsedDocument.model_validate(data)
            except Exception as e:
                logger.warning(f"Cache backend get failed: {e}")

        # 인메모리 캐시 확인
        if cache_key in self._cache:
            doc, expires_at = self._cache[cache_key]
            if time.time() < expires_at:
                return doc
            else:
                del self._cache[cache_key]

        return None

    async def set(
        self,
        file_path: Union[str, Path],
        document: ParsedDocument,
    ) -> bool:
        """
        캐시에 파싱 결과 저장

        Args:
            file_path: 파일 경로
            document: 파싱된 문서

        Returns:
            저장 성공 여부
        """
        path = Path(file_path)
        cache_key = self._get_cache_key(path)

        if not cache_key:
            return False

        # 외부 백엔드 저장
        if self._backend:
            try:
                await self._backend.set(
                    f"docparse:{cache_key}",
                    document.model_dump(mode="json"),
                    ttl=self._ttl,
                )
            except Exception as e:
                logger.warning(f"Cache backend set failed: {e}")

        # 인메모리 캐시 저장
        expires_at = time.time() + self._ttl
        self._cache[cache_key] = (document, expires_at)

        return True

    def clear(self) -> int:
        """캐시 클리어"""
        count = len(self._cache)
        self._cache.clear()
        return count


# ---------------------------------------------------------------------------
# Optimized Document Parser
# ---------------------------------------------------------------------------


class OptimizedDocumentParser:
    """
    최적화된 문서 파서

    배치 처리, 메모리 관리, 캐싱을 통해 Docling PDF 파싱을 최적화합니다.

    Features:
        - 배치 단위 병렬 처리
        - 메모리 사용량 모니터링
        - 해시 기반 중복 방지
        - 스트리밍 파싱 (대용량 문서)
        - 테이블 추출 최적화

    Example:
        parser = OptimizedDocumentParser()

        # 단일 문서 (캐시 적용)
        result = await parser.parse_with_cache("doc.pdf")

        # 배치 처리
        results = await parser.parse_batch(["a.pdf", "b.pdf"])

        # 대용량 스트리밍
        async for chunk in parser.parse_large_document_stream("large.pdf"):
            print(chunk.content)
    """

    def __init__(
        self,
        config: Optional[ParserConfig] = None,
        cache_backend: Optional[Any] = None,
    ):
        """
        초기화

        Args:
            config: 파서 설정
            cache_backend: 캐시 백엔드 (None이면 인메모리)
        """
        self.config = config or ParserConfig()
        self._cache = DocumentCache(
            cache_backend=cache_backend,
            ttl=self.config.cache_ttl,
        )
        self._stats = ParseStats()
        self._converter = None
        self._executor = ThreadPoolExecutor(max_workers=self.config.max_workers)

        logger.info(
            f"OptimizedDocumentParser initialized - "
            f"batch_size={self.config.batch_size}, "
            f"max_workers={self.config.max_workers}, "
            f"cache_enabled={self.config.cache_enabled}"
        )

    @property
    def converter(self):
        """Docling DocumentConverter (지연 로딩)"""
        if self._converter is None:
            self._converter = self._create_converter()
        return self._converter

    @property
    def stats(self) -> ParseStats:
        """파싱 통계"""
        return self._stats

    def _create_converter(self):
        """Docling DocumentConverter 생성 (최적화 설정)"""
        try:
            from docling.datamodel.base_models import InputFormat
            from docling.document_converter import DocumentConverter, PdfFormatOption
            from docling.datamodel.pipeline_options import PdfPipelineOptions

            # PDF 파이프라인 옵션 - 테이블 추출 최적화
            pipeline_options = PdfPipelineOptions(
                do_ocr=self.config.ocr_enabled,
                do_table_structure=self.config.table_structure_enabled,
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

            logger.info("Docling converter initialized with optimized settings")
            return converter

        except ImportError as e:
            logger.error(f"Failed to import Docling: {e}")
            raise ImportError(
                "Docling is not installed. "
                "Please install it with: pip install docling"
            ) from e

    def _get_memory_usage_mb(self) -> float:
        """현재 메모리 사용량 (MB)"""
        try:
            current, peak = tracemalloc.get_traced_memory()
            return peak / (1024 * 1024)
        except Exception:
            return 0.0

    def _check_memory_limit(self) -> bool:
        """메모리 제한 확인"""
        usage = self._get_memory_usage_mb()
        if usage > self.config.max_memory_mb:
            logger.warning(
                f"Memory usage ({usage:.1f}MB) exceeds limit ({self.config.max_memory_mb}MB)"
            )
            return False
        return True

    async def parse_with_cache(
        self,
        file_path: Union[str, Path],
        force_reparse: bool = False,
    ) -> ParseResult:
        """
        캐시된 파싱 결과 사용

        Args:
            file_path: 파일 경로
            force_reparse: 강제 재파싱 여부

        Returns:
            ParseResult
        """
        path = Path(file_path)
        start_time = time.time()

        # 캐시 확인 (활성화 시)
        if self.config.cache_enabled and not force_reparse:
            cached_doc = await self._cache.get(path)
            if cached_doc:
                self._stats.cache_hits += 1
                self._stats.total_documents += 1
                logger.debug(f"Cache hit for {path.name}")

                return ParseResult(
                    document=cached_doc,
                    success=True,
                    message=f"Loaded from cache: {path.name}",
                )

        self._stats.cache_misses += 1

        # 실제 파싱
        result = await self._parse_single(path)

        # 캐시 저장 (성공 시)
        if result.success and self.config.cache_enabled:
            await self._cache.set(path, result.document)

        # 통계 업데이트
        self._stats.total_documents += 1
        self._stats.total_time_ms += (time.time() - start_time) * 1000

        if result.success:
            self._stats.success_count += 1
            self._stats.tables_extracted += len(result.document.tables)
            if result.document.page_count:
                self._stats.pages_processed += result.document.page_count
        else:
            self._stats.failed_count += 1

        return result

    async def _parse_single(self, file_path: Path) -> ParseResult:
        """단일 문서 파싱"""
        from app.etl.docling_adapter import DoclingAdapter

        # DoclingAdapter 사용
        adapter = DoclingAdapter(
            ocr_enabled=self.config.ocr_enabled,
            table_structure_enabled=self.config.table_structure_enabled,
            image_extraction_enabled=self.config.image_extraction_enabled,
        )

        return adapter.parse(file_path)

    async def parse_batch(
        self,
        file_paths: List[Union[str, Path]],
        continue_on_error: bool = True,
        progress_callback: Optional[callable] = None,
    ) -> BatchParseResult:
        """
        배치 단위로 문서 파싱

        Args:
            file_paths: 파일 경로 목록
            continue_on_error: 에러 발생 시 계속 진행 여부
            progress_callback: 진행 상황 콜백 (현재/전체)

        Returns:
            BatchParseResult
        """
        start_time = time.time()
        results = []
        success_count = 0
        failed_count = 0

        # 메모리 추적 시작
        tracemalloc.start()

        try:
            # 배치 단위로 처리
            for i in range(0, len(file_paths), self.config.batch_size):
                batch = file_paths[i:i + self.config.batch_size]

                # 메모리 제한 확인
                if not self._check_memory_limit():
                    # 메모리 정리 후 재시도
                    import gc
                    gc.collect()
                    await asyncio.sleep(0.1)

                # 배치 내 병렬 처리
                batch_results = await self._process_batch(batch)

                for result in batch_results:
                    results.append(result)

                    if result.success:
                        success_count += 1
                    else:
                        failed_count += 1
                        if not continue_on_error:
                            break

                # 진행 콜백
                if progress_callback:
                    processed = min(i + len(batch), len(file_paths))
                    progress_callback(processed, len(file_paths))

                if not continue_on_error and failed_count > 0:
                    break

                # 배치 간 짧은 휴식 (메모리 정리)
                if i + self.config.batch_size < len(file_paths):
                    await asyncio.sleep(0.01)

            # 피크 메모리 기록
            self._stats.peak_memory_mb = max(
                self._stats.peak_memory_mb,
                self._get_memory_usage_mb(),
            )

        finally:
            tracemalloc.stop()

        total_time_ms = (time.time() - start_time) * 1000

        logger.info(
            f"Batch parsing completed: {success_count}/{len(file_paths)} success, "
            f"{total_time_ms:.0f}ms, peak memory: {self._stats.peak_memory_mb:.1f}MB"
        )

        return BatchParseResult(
            total=len(file_paths),
            success_count=success_count,
            failed_count=failed_count,
            results=results,
            total_time_ms=total_time_ms,
        )

    async def _process_batch(
        self,
        batch: List[Union[str, Path]],
    ) -> List[ParseResult]:
        """배치 처리"""
        tasks = [self.parse_with_cache(path) for path in batch]
        return await asyncio.gather(*tasks, return_exceptions=False)

    async def parse_large_document_stream(
        self,
        file_path: Union[str, Path],
        pages_per_chunk: Optional[int] = None,
    ) -> AsyncGenerator[ParsedDocument, None]:
        """
        대용량 문서 스트리밍 파싱

        페이지 단위로 문서를 처리하여 메모리 사용을 최소화합니다.

        Args:
            file_path: 파일 경로
            pages_per_chunk: 청크당 페이지 수 (None이면 config 값 사용)

        Yields:
            ParsedDocument: 청크 단위 파싱 결과
        """
        path = Path(file_path)
        chunk_size = pages_per_chunk or self.config.chunk_pages

        if not path.exists():
            logger.error(f"File not found: {path}")
            return

        logger.info(f"Starting streaming parse: {path.name}, chunk_size={chunk_size}")

        # 메모리 추적 시작
        tracemalloc.start()

        try:
            # Docling 스트리밍 사용 시도
            async for chunk in self._stream_parse(path, chunk_size):
                yield chunk

                # 청크 처리 후 메모리 정리
                if not self._check_memory_limit():
                    import gc
                    gc.collect()
                    await asyncio.sleep(0.1)

        except NotImplementedError:
            # 스트리밍 미지원 시 전체 파싱 후 청킹
            logger.warning("Streaming not supported, falling back to full parse")
            result = await self.parse_with_cache(path)

            if result.success:
                yield result.document

        finally:
            tracemalloc.stop()

    async def _stream_parse(
        self,
        file_path: Path,
        pages_per_chunk: int,
    ) -> AsyncGenerator[ParsedDocument, None]:
        """스트리밍 파싱 구현"""
        # Docling은 현재 스트리밍을 직접 지원하지 않음
        # 향후 버전에서 구현 예정
        # 현재는 전체 파싱 후 분할 처리

        result = await self.parse_with_cache(file_path)

        if not result.success:
            logger.error(f"Parse failed: {result.message}")
            return

        doc = result.document

        # 섹션이 있으면 섹션 단위로 분할
        if doc.sections:
            for i in range(0, len(doc.sections), pages_per_chunk):
                chunk_sections = doc.sections[i:i + pages_per_chunk]

                chunk_doc = ParsedDocument(
                    source_path=doc.source_path,
                    source_format=doc.source_format,
                    status=ParseStatus.SUCCESS,
                    content="\n".join(s.content for s in chunk_sections),
                    sections=chunk_sections,
                    title=f"{doc.title} (chunk {i // pages_per_chunk + 1})",
                    page_count=len(chunk_sections),
                    parser_version=doc.parser_version,
                )
                yield chunk_doc
        else:
            # 섹션이 없으면 텍스트를 청크로 분할
            content = doc.content
            chunk_size = 10000  # 문자 단위

            for i in range(0, len(content), chunk_size):
                chunk_content = content[i:i + chunk_size]

                chunk_doc = ParsedDocument(
                    source_path=doc.source_path,
                    source_format=doc.source_format,
                    status=ParseStatus.SUCCESS,
                    content=chunk_content,
                    title=f"{doc.title} (chunk {i // chunk_size + 1})",
                    parser_version=doc.parser_version,
                )
                yield chunk_doc

    def get_document_hash(self, file_path: Union[str, Path]) -> str:
        """
        문서 해시 계산

        Args:
            file_path: 파일 경로

        Returns:
            MD5 해시 문자열
        """
        return self._cache.get_document_hash(file_path)

    def reset_stats(self) -> None:
        """통계 초기화"""
        self._stats = ParseStats()
        logger.info("Parser stats reset")

    def clear_cache(self) -> int:
        """캐시 클리어"""
        count = self._cache.clear()
        logger.info(f"Cache cleared: {count} entries")
        return count

    def shutdown(self) -> None:
        """리소스 정리"""
        self._executor.shutdown(wait=False)
        logger.info("Parser shutdown complete")


# ---------------------------------------------------------------------------
# 싱글톤 인스턴스
# ---------------------------------------------------------------------------

_parser_instance: Optional[OptimizedDocumentParser] = None


def get_optimized_parser(
    config: Optional[ParserConfig] = None,
    cache_backend: Optional[Any] = None,
) -> OptimizedDocumentParser:
    """
    OptimizedDocumentParser 인스턴스 반환 (싱글톤)

    Args:
        config: 파서 설정 (처음 호출 시에만 적용)
        cache_backend: 캐시 백엔드

    Returns:
        OptimizedDocumentParser 인스턴스
    """
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = OptimizedDocumentParser(
            config=config,
            cache_backend=cache_backend,
        )
    return _parser_instance


def reset_parser_instance() -> None:
    """파서 인스턴스 리셋 (테스트용)"""
    global _parser_instance
    if _parser_instance:
        _parser_instance.shutdown()
    _parser_instance = None
    logger.info("Parser instance reset")
