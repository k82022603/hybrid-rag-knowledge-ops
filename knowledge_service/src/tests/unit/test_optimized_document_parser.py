"""
최적화된 문서 파서 단위 테스트 (STORY-063)

테스트 항목:
- 배치 처리 테스트
- 메모리 사용량 테스트
- 캐싱 테스트
- 스트리밍 파싱 테스트
- 테이블 추출 테스트
- 통계 테스트
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.parsed_document import (
    DocumentFormat,
    ParsedDocument,
    ParseResult,
    ParseStatus,
    Section,
    Table,
    TableCell,
)
from app.services.document_parser import (
    DocumentCache,
    OptimizedDocumentParser,
    ParserConfig,
    ParseStats,
    get_optimized_parser,
    reset_parser_instance,
)


class TestParserConfig:
    """ParserConfig 테스트"""

    def test_default_config(self):
        """기본 설정 확인"""
        config = ParserConfig()

        assert config.batch_size == 5
        assert config.max_workers == 2
        assert config.cache_enabled is True
        assert config.ocr_enabled is True
        assert config.table_structure_enabled is True

    def test_custom_config(self):
        """커스텀 설정"""
        config = ParserConfig(
            batch_size=10,
            max_workers=4,
            cache_enabled=False,
            max_memory_mb=1024,
        )

        assert config.batch_size == 10
        assert config.max_workers == 4
        assert config.cache_enabled is False
        assert config.max_memory_mb == 1024


class TestParseStats:
    """ParseStats 테스트"""

    def test_initial_stats(self):
        """초기 통계"""
        stats = ParseStats()

        assert stats.total_documents == 0
        assert stats.cache_hit_rate == 0.0
        assert stats.avg_time_per_doc_ms == 0.0

    def test_cache_hit_rate(self):
        """캐시 히트율 계산"""
        stats = ParseStats(cache_hits=75, cache_misses=25)

        assert stats.cache_hit_rate == 0.75

    def test_avg_time_per_doc(self):
        """문서당 평균 시간"""
        stats = ParseStats(
            total_documents=10,
            total_time_ms=5000.0,
        )

        assert stats.avg_time_per_doc_ms == 500.0

    def test_to_dict(self):
        """딕셔너리 변환"""
        stats = ParseStats(
            total_documents=5,
            success_count=4,
            failed_count=1,
            cache_hits=3,
            cache_misses=2,
            total_time_ms=1000.0,
            tables_extracted=10,
        )

        result = stats.to_dict()

        assert result["total_documents"] == 5
        assert result["success_count"] == 4
        assert result["cache_hit_rate"] == 0.6
        assert result["avg_time_per_doc_ms"] == 200.0
        assert result["tables_extracted"] == 10


class TestDocumentCache:
    """DocumentCache 테스트"""

    def test_get_document_hash(self, tmp_path):
        """문서 해시 생성"""
        cache = DocumentCache()

        # 테스트 파일 생성
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"test content" * 1000)

        hash1 = cache.get_document_hash(test_file)
        hash2 = cache.get_document_hash(test_file)

        assert hash1 != ""
        assert hash1 == hash2  # 동일 파일은 같은 해시

    def test_hash_different_files(self, tmp_path):
        """다른 파일은 다른 해시"""
        cache = DocumentCache()

        file1 = tmp_path / "test1.pdf"
        file2 = tmp_path / "test2.pdf"
        file1.write_bytes(b"content 1" * 1000)
        file2.write_bytes(b"content 2" * 1000)

        hash1 = cache.get_document_hash(file1)
        hash2 = cache.get_document_hash(file2)

        assert hash1 != hash2

    def test_hash_nonexistent_file(self):
        """존재하지 않는 파일"""
        cache = DocumentCache()

        hash_val = cache.get_document_hash("/nonexistent/file.pdf")

        assert hash_val == ""

    @pytest.mark.asyncio
    async def test_cache_set_get(self, tmp_path):
        """캐시 저장/조회"""
        cache = DocumentCache(ttl=3600)

        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"test content")

        doc = ParsedDocument(
            source_path=str(test_file),
            source_format=DocumentFormat.PDF,
            status=ParseStatus.SUCCESS,
            content="Test content",
        )

        # 저장
        success = await cache.set(test_file, doc)
        assert success is True

        # 조회
        cached_doc = await cache.get(test_file)
        assert cached_doc is not None
        assert cached_doc.content == "Test content"

    @pytest.mark.asyncio
    async def test_cache_miss(self, tmp_path):
        """캐시 미스"""
        cache = DocumentCache()

        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"test content")

        # 캐시에 없는 파일 조회
        cached_doc = await cache.get(test_file)

        assert cached_doc is None

    def test_cache_clear(self, tmp_path):
        """캐시 클리어"""
        cache = DocumentCache()

        # 수동으로 캐시 추가
        cache._cache["key1"] = (MagicMock(), float("inf"))
        cache._cache["key2"] = (MagicMock(), float("inf"))

        count = cache.clear()

        assert count == 2
        assert len(cache._cache) == 0


class TestOptimizedDocumentParser:
    """OptimizedDocumentParser 테스트"""

    def test_initialization(self):
        """파서 초기화"""
        config = ParserConfig(
            batch_size=10,
            max_workers=2,
        )
        parser = OptimizedDocumentParser(config=config)

        assert parser.config.batch_size == 10
        assert parser.config.max_workers == 2

    def test_default_initialization(self):
        """기본 설정으로 초기화"""
        parser = OptimizedDocumentParser()

        assert parser.config is not None
        assert parser.stats.total_documents == 0

    @pytest.mark.asyncio
    async def test_parse_with_cache_miss(self, tmp_path):
        """캐시 미스 시 파싱"""
        config = ParserConfig(cache_enabled=True)
        parser = OptimizedDocumentParser(config=config)

        # 테스트 Markdown 파일 생성
        md_file = tmp_path / "test.md"
        md_file.write_text("# Test\n\nContent", encoding="utf-8")

        # DoclingAdapter를 mock
        with patch("app.etl.docling_adapter.DoclingAdapter") as MockAdapter:
            mock_adapter = MockAdapter.return_value
            mock_adapter.parse.return_value = ParseResult(
                document=ParsedDocument(
                    source_path=str(md_file),
                    source_format=DocumentFormat.MARKDOWN,
                    status=ParseStatus.SUCCESS,
                    content="# Test\n\nContent",
                ),
                success=True,
                message="OK",
            )

            result = await parser.parse_with_cache(md_file)

            assert result.success is True
            assert parser.stats.cache_misses == 1

    @pytest.mark.asyncio
    async def test_parse_with_cache_hit(self, tmp_path):
        """캐시 히트"""
        config = ParserConfig(cache_enabled=True)
        parser = OptimizedDocumentParser(config=config)

        # 테스트 파일 생성
        md_file = tmp_path / "test.md"
        md_file.write_text("# Test", encoding="utf-8")

        # 캐시에 미리 저장
        cached_doc = ParsedDocument(
            source_path=str(md_file),
            source_format=DocumentFormat.MARKDOWN,
            status=ParseStatus.SUCCESS,
            content="Cached content",
        )
        await parser._cache.set(md_file, cached_doc)

        result = await parser.parse_with_cache(md_file)

        assert result.success is True
        assert "cache" in result.message.lower()
        assert parser.stats.cache_hits == 1

    @pytest.mark.asyncio
    async def test_parse_batch(self, tmp_path):
        """배치 파싱"""
        config = ParserConfig(batch_size=2, cache_enabled=False)
        parser = OptimizedDocumentParser(config=config)

        # 여러 테스트 파일 생성
        files = []
        for i in range(3):
            f = tmp_path / f"test{i}.md"
            f.write_text(f"# Test {i}", encoding="utf-8")
            files.append(f)

        # DoclingAdapter mock
        with patch("app.etl.docling_adapter.DoclingAdapter") as MockAdapter:
            mock_adapter = MockAdapter.return_value
            mock_adapter.parse.return_value = ParseResult(
                document=ParsedDocument(
                    status=ParseStatus.SUCCESS,
                    content="Test",
                ),
                success=True,
                message="OK",
            )

            result = await parser.parse_batch(files)

            assert result.total == 3
            assert result.success_count == 3
            assert result.total_time_ms > 0

    @pytest.mark.asyncio
    async def test_parse_batch_with_progress(self, tmp_path):
        """배치 파싱 진행 콜백"""
        parser = OptimizedDocumentParser()

        files = []
        for i in range(4):
            f = tmp_path / f"test{i}.md"
            f.write_text(f"# Test {i}", encoding="utf-8")
            files.append(f)

        progress_calls = []

        def progress_callback(current, total):
            progress_calls.append((current, total))

        with patch("app.etl.docling_adapter.DoclingAdapter") as MockAdapter:
            mock_adapter = MockAdapter.return_value
            mock_adapter.parse.return_value = ParseResult(
                document=ParsedDocument(status=ParseStatus.SUCCESS),
                success=True,
                message="OK",
            )

            await parser.parse_batch(files, progress_callback=progress_callback)

            assert len(progress_calls) > 0

    @pytest.mark.asyncio
    async def test_parse_batch_continue_on_error(self, tmp_path):
        """에러 발생 시 계속 진행"""
        config = ParserConfig(batch_size=2)
        parser = OptimizedDocumentParser(config=config)

        # 일부 파일만 생성
        existing_file = tmp_path / "exists.md"
        existing_file.write_text("# Test", encoding="utf-8")

        files = [
            existing_file,
            tmp_path / "nonexistent.md",
            existing_file,
        ]

        with patch("app.etl.docling_adapter.DoclingAdapter") as MockAdapter:
            mock_adapter = MockAdapter.return_value

            def mock_parse(path, **kwargs):
                if Path(path).exists():
                    return ParseResult(
                        document=ParsedDocument(status=ParseStatus.SUCCESS),
                        success=True,
                        message="OK",
                    )
                else:
                    return ParseResult(
                        document=ParsedDocument(status=ParseStatus.FAILED),
                        success=False,
                        message="File not found",
                    )

            mock_adapter.parse.side_effect = mock_parse

            result = await parser.parse_batch(files, continue_on_error=True)

            assert result.total == 3
            assert result.success_count == 2
            assert result.failed_count == 1

    @pytest.mark.asyncio
    async def test_stream_parse(self, tmp_path):
        """스트리밍 파싱"""
        parser = OptimizedDocumentParser()

        # 테스트 파일 생성
        md_file = tmp_path / "large.md"
        sections = [f"# Section {i}\n\nContent {i}\n" for i in range(20)]
        md_file.write_text("\n".join(sections), encoding="utf-8")

        # 캐시에 문서 저장 (스트리밍 테스트를 위해)
        doc = ParsedDocument(
            source_path=str(md_file),
            source_format=DocumentFormat.MARKDOWN,
            status=ParseStatus.SUCCESS,
            content="\n".join(sections),
            sections=[
                Section(title=f"Section {i}", level=1, content=f"Content {i}")
                for i in range(20)
            ],
            title="Large Document",
        )
        await parser._cache.set(md_file, doc)

        chunks = []
        async for chunk in parser.parse_large_document_stream(md_file, pages_per_chunk=5):
            chunks.append(chunk)

        assert len(chunks) == 4  # 20 sections / 5 per chunk

    def test_get_document_hash(self, tmp_path):
        """문서 해시"""
        parser = OptimizedDocumentParser()

        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"test content" * 1000)

        hash_val = parser.get_document_hash(test_file)

        assert hash_val != ""
        assert len(hash_val) == 32  # MD5 hex length

    def test_reset_stats(self):
        """통계 초기화"""
        parser = OptimizedDocumentParser()

        parser._stats.total_documents = 10
        parser._stats.cache_hits = 5

        parser.reset_stats()

        assert parser.stats.total_documents == 0
        assert parser.stats.cache_hits == 0

    def test_clear_cache(self, tmp_path):
        """캐시 클리어"""
        parser = OptimizedDocumentParser()

        # 캐시에 데이터 추가
        parser._cache._cache["key1"] = (MagicMock(), float("inf"))

        count = parser.clear_cache()

        assert count == 1

    def test_shutdown(self):
        """파서 종료"""
        parser = OptimizedDocumentParser()

        # shutdown 호출 시 에러 없어야 함
        parser.shutdown()


class TestSingletonParser:
    """싱글톤 파서 테스트"""

    def test_get_optimized_parser(self):
        """싱글톤 인스턴스"""
        reset_parser_instance()

        parser1 = get_optimized_parser()
        parser2 = get_optimized_parser()

        assert parser1 is parser2

        reset_parser_instance()

    def test_reset_parser_instance(self):
        """인스턴스 리셋"""
        reset_parser_instance()

        parser1 = get_optimized_parser()
        reset_parser_instance()
        parser2 = get_optimized_parser()

        assert parser1 is not parser2

        reset_parser_instance()

    def test_custom_config_singleton(self):
        """커스텀 설정으로 싱글톤 생성"""
        reset_parser_instance()

        config = ParserConfig(batch_size=20)
        parser = get_optimized_parser(config=config)

        assert parser.config.batch_size == 20

        reset_parser_instance()


class TestMemoryManagement:
    """메모리 관리 테스트"""

    @pytest.mark.asyncio
    async def test_memory_tracking(self, tmp_path):
        """메모리 추적"""
        config = ParserConfig(max_memory_mb=1024)
        parser = OptimizedDocumentParser(config=config)

        files = []
        for i in range(5):
            f = tmp_path / f"test{i}.md"
            f.write_text(f"# Test {i}\n" + "content " * 1000, encoding="utf-8")
            files.append(f)

        with patch("app.etl.docling_adapter.DoclingAdapter") as MockAdapter:
            mock_adapter = MockAdapter.return_value
            mock_adapter.parse.return_value = ParseResult(
                document=ParsedDocument(status=ParseStatus.SUCCESS),
                success=True,
                message="OK",
            )

            result = await parser.parse_batch(files)

            # 메모리 추적이 실행됨
            assert result.total_time_ms > 0


class TestTableExtraction:
    """테이블 추출 테스트"""

    @pytest.mark.asyncio
    async def test_table_count_stats(self, tmp_path):
        """테이블 카운트 통계"""
        parser = OptimizedDocumentParser()

        md_file = tmp_path / "tables.md"
        md_file.write_text("# Test\n\n| A | B |\n|---|---|\n| 1 | 2 |", encoding="utf-8")

        # DoclingAdapter mock
        with patch("app.etl.docling_adapter.DoclingAdapter") as MockAdapter:
            mock_adapter = MockAdapter.return_value
            mock_adapter.parse.return_value = ParseResult(
                document=ParsedDocument(
                    status=ParseStatus.SUCCESS,
                    tables=[
                        Table(cells=[], rows=2, cols=2),
                        Table(cells=[], rows=3, cols=2),
                    ],
                ),
                success=True,
                message="OK",
            )

            await parser.parse_with_cache(md_file)

            assert parser.stats.tables_extracted == 2


class TestForceReparse:
    """강제 재파싱 테스트"""

    @pytest.mark.asyncio
    async def test_force_reparse(self, tmp_path):
        """강제 재파싱으로 캐시 우회"""
        parser = OptimizedDocumentParser()

        md_file = tmp_path / "test.md"
        md_file.write_text("# Test", encoding="utf-8")

        # 캐시에 저장
        cached_doc = ParsedDocument(
            status=ParseStatus.SUCCESS,
            content="Cached",
        )
        await parser._cache.set(md_file, cached_doc)

        # DoclingAdapter mock
        with patch("app.etl.docling_adapter.DoclingAdapter") as MockAdapter:
            mock_adapter = MockAdapter.return_value
            mock_adapter.parse.return_value = ParseResult(
                document=ParsedDocument(
                    status=ParseStatus.SUCCESS,
                    content="Fresh",
                ),
                success=True,
                message="OK",
            )

            # force_reparse=True로 호출
            result = await parser.parse_with_cache(md_file, force_reparse=True)

            # 새로 파싱된 내용
            assert result.document.content == "Fresh"
            assert parser.stats.cache_misses == 1
