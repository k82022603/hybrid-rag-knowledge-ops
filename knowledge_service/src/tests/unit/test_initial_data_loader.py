"""
InitialDataLoader 및 DataValidator 단위 테스트

STORY-045: 초기 데이터 ETL 파이프라인 테스트

테스트 범위:
    - 파일 탐색 로직 (discover_files)
    - 메타데이터 추출 (_extract_metadata)
    - 문서 유형 분류 (_classify_doc_type)
    - ETL 파이프라인 전체 Mock 테스트 (load_all)
    - DataValidator 검증 로직
"""

import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.initial_data_loader import (
    DataSource,
    DocType,
    ETLSummary,
    FileInfo,
    InitialDataLoader,
    LoadResult,
    LoadStatus,
    get_initial_data_loader,
    reset_initial_data_loader,
)
from app.services.data_validator import (
    InitialDataValidation,
    ValidationCheck,
    ValidationLevel,
    ValidationReport,
    get_data_validator,
    reset_data_validator,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_data_dir():
    """임시 데이터 디렉토리 생성"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 데이터 구조 생성
        technical_dir = Path(tmpdir) / "knowledge_data" / "documents" / "technical"
        guides_dir = Path(tmpdir) / "knowledge_data" / "documents" / "guides"
        presentations_dir = Path(tmpdir) / "knowledge_data" / "documents" / "presentations"

        technical_dir.mkdir(parents=True)
        guides_dir.mkdir(parents=True)
        presentations_dir.mkdir(parents=True)

        # 샘플 Markdown 파일 생성
        (technical_dir / "design_doc.md").write_text(
            "# 시스템 설계서\n\n## 아키텍처\n\n"
            "이 문서는 Hybrid RAG 플랫폼의 아키텍처 설계를 설명합니다.\n"
            "Neo4j 그래프 데이터베이스와 Elasticsearch 벡터 검색을 활용합니다.\n\n"
            "## API 설계\n\nRESTful API를 사용합니다.\n"
            "### 엔드포인트\n- GET /api/v1/search\n- POST /api/v1/documents\n",
            encoding="utf-8",
        )
        (technical_dir / "api_spec.md").write_text(
            "# API 명세서\n\n## 인증\n\nJWT 토큰 기반 인증을 사용합니다.\n\n"
            "## 검색 API\n\n### POST /search\n\n"
            "쿼리 파라미터로 검색을 수행합니다.\n",
            encoding="utf-8",
        )
        (technical_dir / "schema.md").write_text(
            "# 데이터베이스 스키마\n\n## PostgreSQL\n\n"
            "documents 테이블, chunks 테이블을 사용합니다.\n\n"
            "## Neo4j\n\n"
            "Entity, Document, Chunk 노드와 RELATED_TO, PART_OF 관계를 사용합니다.\n",
            encoding="utf-8",
        )

        (guides_dir / "user_guide.md").write_text(
            "# 사용자 가이드\n\n## 설치 방법\n\n"
            "pip install -r requirements.txt\n\n"
            "## 실행 방법\n\n"
            "python main.py\n",
            encoding="utf-8",
        )
        (guides_dir / "dev_guide.md").write_text(
            "# 개발 가이드\n\n## 개발 환경 설정\n\n"
            "Python 3.11 이상이 필요합니다.\n\n"
            "## 테스트\n\n"
            "pytest를 사용하여 테스트를 실행합니다.\n",
            encoding="utf-8",
        )

        # 건너뛸 파일/디렉토리
        pycache_dir = technical_dir / "__pycache__"
        pycache_dir.mkdir()
        (pycache_dir / "cached.pyc").write_bytes(b"fake pyc")

        # 비지원 확장자 파일
        (technical_dir / "notes.log").write_text("log file", encoding="utf-8")

        # CLAUDE.md 파일 생성 (프로젝트 루트 감지용)
        (Path(tmpdir) / "CLAUDE.md").write_text("# CLAUDE", encoding="utf-8")

        yield tmpdir


@pytest.fixture
def loader(temp_data_dir):
    """테스트용 InitialDataLoader 인스턴스"""
    reset_initial_data_loader()
    return InitialDataLoader(
        project_root=temp_data_dir,
        chunk_size=200,
        chunk_overlap=50,
        batch_size=8,
        max_retries=2,
        continue_on_error=True,
        enable_embeddings=False,
        enable_entity_extraction=False,
    )


@pytest.fixture
def sample_etl_summary():
    """테스트용 ETL 요약 데이터"""
    results = [
        LoadResult(
            file_path="/data/doc1.md",
            file_name="doc1.md",
            status=LoadStatus.SUCCESS,
            document_id="uuid-1",
            chunk_count=5,
            entity_count=3,
            processing_time_ms=150.0,
        ),
        LoadResult(
            file_path="/data/doc2.md",
            file_name="doc2.md",
            status=LoadStatus.SUCCESS,
            document_id="uuid-2",
            chunk_count=8,
            entity_count=5,
            processing_time_ms=200.0,
        ),
        LoadResult(
            file_path="/data/doc3.md",
            file_name="doc3.md",
            status=LoadStatus.SUCCESS,
            document_id="uuid-3",
            chunk_count=3,
            entity_count=2,
            processing_time_ms=100.0,
        ),
    ]

    summary = ETLSummary(
        total_files=3,
        success_count=3,
        failed_count=0,
        skipped_count=0,
        total_chunks=16,
        total_entities=10,
        total_time_ms=450.0,
        results=results,
    )

    return summary


@pytest.fixture
def failed_etl_summary():
    """실패 케이스 ETL 요약"""
    results = [
        LoadResult(
            file_path="/data/doc1.md",
            file_name="doc1.md",
            status=LoadStatus.SUCCESS,
            document_id="uuid-1",
            chunk_count=5,
            entity_count=3,
            processing_time_ms=150.0,
        ),
        LoadResult(
            file_path="/data/doc2.md",
            file_name="doc2.md",
            status=LoadStatus.FAILED,
            error_message="Parse error",
            processing_time_ms=50.0,
        ),
        LoadResult(
            file_path="/data/doc3.md",
            file_name="doc3.md",
            status=LoadStatus.FAILED,
            error_message="Timeout",
            processing_time_ms=60000.0,
        ),
    ]

    summary = ETLSummary(
        total_files=3,
        success_count=1,
        failed_count=2,
        skipped_count=0,
        total_chunks=5,
        total_entities=3,
        total_time_ms=60200.0,
        results=results,
    )

    return summary


@pytest.fixture
def validator():
    """테스트용 DataValidator 인스턴스"""
    reset_data_validator()
    return InitialDataValidation(
        min_documents=3,
        min_chunks_per_doc=2.0,
        max_chunks_per_doc=50.0,
        min_entities=5,
        max_orphan_rate=0.01,
        max_empty_chunk_rate=0.05,
    )


# ===========================================================================
# InitialDataLoader Tests
# ===========================================================================


class TestDataSource:
    """DataSource 데이터클래스 테스트"""

    def test_default_extensions(self):
        """기본 확장자 목록 확인"""
        source = DataSource(name="test", path="/data")
        assert ".md" in source.extensions
        assert ".pdf" in source.extensions
        assert ".docx" in source.extensions
        assert ".pptx" in source.extensions

    def test_custom_extensions(self):
        """커스텀 확장자 목록 확인"""
        source = DataSource(
            name="test",
            path="/data",
            extensions=[".md", ".txt"],
        )
        assert source.extensions == [".md", ".txt"]

    def test_doc_type_default(self):
        """기본 문서 유형은 UNKNOWN"""
        source = DataSource(name="test", path="/data")
        assert source.doc_type == DocType.UNKNOWN

    def test_recursive_default(self):
        """기본 재귀 탐색은 True"""
        source = DataSource(name="test", path="/data")
        assert source.recursive is True


class TestFileDiscovery:
    """파일 탐색 로직 테스트"""

    def test_discover_markdown_files(self, loader, temp_data_dir):
        """Markdown 파일 탐색 확인"""
        source = DataSource(
            name="technical",
            path=str(Path(temp_data_dir) / "knowledge_data" / "documents" / "technical"),
            doc_type=DocType.TECHNICAL,
        )
        loader.add_source(source)

        files = loader._discover_files(source)

        # design_doc.md, api_spec.md, schema.md (3개)
        md_files = [f for f in files if f.extension == ".md"]
        assert len(md_files) == 3

    def test_skip_pycache(self, loader, temp_data_dir):
        """__pycache__ 디렉토리 건너뛰기"""
        source = DataSource(
            name="technical",
            path=str(Path(temp_data_dir) / "knowledge_data" / "documents" / "technical"),
            doc_type=DocType.TECHNICAL,
            extensions=[".md", ".pyc"],
        )

        files = loader._discover_files(source)

        # .pyc 파일은 __pycache__에 있으므로 건너뛰어야 함
        pyc_files = [f for f in files if f.extension == ".pyc"]
        assert len(pyc_files) == 0

    def test_extension_filter(self, loader, temp_data_dir):
        """확장자 필터링 확인"""
        source = DataSource(
            name="technical",
            path=str(Path(temp_data_dir) / "knowledge_data" / "documents" / "technical"),
            extensions=[".md"],
        )

        files = loader._discover_files(source)

        # .log 파일은 필터링되어야 함
        for f in files:
            assert f.extension == ".md"

    def test_nonexistent_path(self, loader):
        """존재하지 않는 경로 처리"""
        source = DataSource(
            name="nonexistent",
            path="/nonexistent/path",
        )

        files = loader._discover_files(source)
        assert len(files) == 0

    def test_file_info_fields(self, loader, temp_data_dir):
        """FileInfo 필드 값 확인"""
        source = DataSource(
            name="technical",
            path=str(Path(temp_data_dir) / "knowledge_data" / "documents" / "technical"),
            doc_type=DocType.TECHNICAL,
        )

        files = loader._discover_files(source)
        assert len(files) > 0

        for file_info in files:
            assert file_info.file_path.exists()
            assert file_info.file_name != ""
            assert file_info.file_size > 0
            assert file_info.extension == ".md"
            assert file_info.source_name == "technical"
            assert file_info.doc_type == DocType.TECHNICAL
            assert file_info.modified_at is not None

    def test_files_sorted_by_name(self, loader, temp_data_dir):
        """파일이 이름 순서로 정렬되는지 확인"""
        source = DataSource(
            name="technical",
            path=str(Path(temp_data_dir) / "knowledge_data" / "documents" / "technical"),
        )

        files = loader._discover_files(source)
        file_names = [f.file_name for f in files]

        assert file_names == sorted(file_names)

    def test_discover_all_sources(self, loader, temp_data_dir):
        """전체 소스에서 파일 탐색"""
        loader.add_source(DataSource(
            name="technical",
            path=str(Path(temp_data_dir) / "knowledge_data" / "documents" / "technical"),
            doc_type=DocType.TECHNICAL,
        ))
        loader.add_source(DataSource(
            name="guides",
            path=str(Path(temp_data_dir) / "knowledge_data" / "documents" / "guides"),
            doc_type=DocType.GUIDE,
        ))

        all_files = loader.discover_files()
        # technical: 3, guides: 2 = 5
        assert len(all_files) == 5

    def test_non_recursive_discovery(self, loader, temp_data_dir):
        """비재귀 탐색 확인"""
        # 중첩 디렉토리에 파일 생성
        nested_dir = Path(temp_data_dir) / "knowledge_data" / "documents" / "technical" / "sub"
        nested_dir.mkdir(parents=True)
        (nested_dir / "nested.md").write_text("# Nested doc", encoding="utf-8")

        source = DataSource(
            name="technical",
            path=str(Path(temp_data_dir) / "knowledge_data" / "documents" / "technical"),
            recursive=False,
        )

        files = loader._discover_files(source)
        file_names = [f.file_name for f in files]

        # 비재귀이므로 nested.md가 포함되면 안됨
        assert "nested.md" not in file_names


class TestMetadataExtraction:
    """메타데이터 추출 테스트"""

    def test_extract_basic_metadata(self, loader, temp_data_dir):
        """기본 메타데이터 추출"""
        file_path = Path(temp_data_dir) / "knowledge_data" / "documents" / "technical" / "design_doc.md"
        file_info = FileInfo(
            file_path=file_path,
            file_name="design_doc.md",
            file_size=500,
            extension=".md",
            source_name="technical",
            doc_type=DocType.TECHNICAL,
        )

        mock_parsed_doc = MagicMock()
        mock_parsed_doc.content = "# Design Document\nSome content here."
        mock_parsed_doc.title = "Design Document"
        mock_parsed_doc.sections = [MagicMock(title="Architecture")]
        mock_parsed_doc.tables = []
        mock_parsed_doc.images = []

        metadata = loader._extract_metadata(file_info, mock_parsed_doc)

        assert metadata["source_name"] == "technical"
        assert metadata["file_name"] == "design_doc.md"
        assert metadata["extension"] == ".md"
        assert metadata["file_size"] == 500
        assert metadata["title"] == "Design Document"
        assert metadata["content_length"] > 0
        assert metadata["section_count"] == 1

    def test_metadata_without_title(self, loader):
        """제목이 없는 문서의 메타데이터"""
        file_info = FileInfo(
            file_path=Path("/data/doc.md"),
            file_name="doc.md",
            file_size=100,
            extension=".md",
            source_name="test",
            doc_type=DocType.UNKNOWN,
        )

        mock_parsed_doc = MagicMock()
        mock_parsed_doc.content = "Some content"
        mock_parsed_doc.title = None
        mock_parsed_doc.sections = None
        mock_parsed_doc.tables = None
        mock_parsed_doc.images = None

        metadata = loader._extract_metadata(file_info, mock_parsed_doc)

        # 제목이 없으면 파일명 사용
        assert metadata["title"] == "doc.md"


class TestDocTypeClassification:
    """문서 유형 분류 테스트"""

    def test_classify_from_source_type(self, loader):
        """데이터 소스 유형으로 분류"""
        file_info = FileInfo(
            file_path=Path("/data/doc.md"),
            file_name="doc.md",
            file_size=100,
            extension=".md",
            source_name="technical",
            doc_type=DocType.TECHNICAL,
        )

        mock_doc = MagicMock()
        mock_doc.content = "Some content"

        doc_type = loader._classify_doc_type(file_info, mock_doc)
        assert doc_type == "technical"

    def test_classify_from_path(self, loader):
        """파일 경로 기반 분류"""
        file_info = FileInfo(
            file_path=Path("/data/design/architecture.md"),
            file_name="architecture.md",
            file_size=100,
            extension=".md",
            source_name="misc",
            doc_type=DocType.UNKNOWN,
        )

        mock_doc = MagicMock()
        mock_doc.content = "Some content"

        doc_type = loader._classify_doc_type(file_info, mock_doc)
        assert doc_type == "technical"

    def test_classify_from_content(self, loader):
        """내용 기반 분류"""
        file_info = FileInfo(
            file_path=Path("/data/misc/doc.md"),
            file_name="doc.md",
            file_size=100,
            extension=".md",
            source_name="misc",
            doc_type=DocType.UNKNOWN,
        )

        mock_doc = MagicMock()
        mock_doc.content = "이 문서는 사용자 가이드입니다. 매뉴얼에 따라 설치하세요."

        doc_type = loader._classify_doc_type(file_info, mock_doc)
        assert doc_type == "guide"

    def test_classify_unknown(self, loader):
        """분류 불가 시 unknown 반환"""
        file_info = FileInfo(
            file_path=Path("/data/random/doc.md"),
            file_name="doc.md",
            file_size=100,
            extension=".md",
            source_name="misc",
            doc_type=DocType.UNKNOWN,
        )

        mock_doc = MagicMock()
        mock_doc.content = "Random content without any keywords"

        doc_type = loader._classify_doc_type(file_info, mock_doc)
        assert doc_type == "unknown"

    def test_classify_guide_from_path(self, loader):
        """경로에 'guide'가 포함된 경우"""
        file_info = FileInfo(
            file_path=Path("/data/user_guide/howto.md"),
            file_name="howto.md",
            file_size=100,
            extension=".md",
            source_name="misc",
            doc_type=DocType.UNKNOWN,
        )

        mock_doc = MagicMock()
        mock_doc.content = "Some content"

        doc_type = loader._classify_doc_type(file_info, mock_doc)
        assert doc_type == "guide"


class TestShouldSkip:
    """건너뛰기 패턴 테스트"""

    def test_skip_pycache(self, loader):
        """__pycache__ 건너뛰기"""
        assert loader._should_skip(Path("/data/__pycache__/file.pyc")) is True

    def test_skip_git(self, loader):
        """/.git/ 건너뛰기"""
        assert loader._should_skip(Path("/data/.git/config")) is True

    def test_skip_node_modules(self, loader):
        """node_modules 건너뛰기"""
        assert loader._should_skip(Path("/data/node_modules/package.json")) is True

    def test_no_skip_normal(self, loader):
        """일반 파일은 건너뛰지 않음"""
        assert loader._should_skip(Path("/data/documents/design.md")) is False

    def test_skip_ds_store(self, loader):
        """.DS_Store 건너뛰기"""
        assert loader._should_skip(Path("/data/.DS_Store")) is True


class TestETLSummary:
    """ETLSummary 데이터클래스 테스트"""

    def test_success_rate_full(self, sample_etl_summary):
        """100% 성공률"""
        assert sample_etl_summary.success_rate == 1.0

    def test_success_rate_partial(self, failed_etl_summary):
        """부분 성공률"""
        assert failed_etl_summary.success_rate == pytest.approx(1 / 3, abs=0.01)

    def test_success_rate_empty(self):
        """빈 요약의 성공률"""
        summary = ETLSummary(total_files=0)
        assert summary.success_rate == 0.0

    def test_to_dict(self, sample_etl_summary):
        """딕셔너리 변환"""
        result = sample_etl_summary.to_dict()

        assert result["total_files"] == 3
        assert result["success_count"] == 3
        assert result["failed_count"] == 0
        assert result["total_chunks"] == 16
        assert result["total_entities"] == 10
        assert result["success_rate"] == 100.0


class TestInitialDataLoaderConfig:
    """InitialDataLoader 설정 테스트"""

    def test_default_config(self, temp_data_dir):
        """기본 설정값 확인"""
        reset_initial_data_loader()
        loader = InitialDataLoader(project_root=temp_data_dir)

        assert loader.chunk_size == 600
        assert loader.chunk_overlap == 100
        assert loader.batch_size == 32
        assert loader.max_retries == 3
        assert loader.continue_on_error is True
        assert loader.enable_embeddings is True
        assert loader.enable_entity_extraction is True

    def test_custom_config(self, temp_data_dir):
        """커스텀 설정값 확인"""
        reset_initial_data_loader()
        loader = InitialDataLoader(
            project_root=temp_data_dir,
            chunk_size=300,
            chunk_overlap=50,
            batch_size=16,
            max_retries=5,
            continue_on_error=False,
        )

        assert loader.chunk_size == 300
        assert loader.chunk_overlap == 50
        assert loader.batch_size == 16
        assert loader.max_retries == 5
        assert loader.continue_on_error is False

    def test_add_source(self, loader):
        """데이터 소스 추가"""
        source = DataSource(name="test", path="/data/test")
        loader.add_source(source)

        assert len(loader.data_sources) == 1
        assert loader.data_sources[0].name == "test"

    def test_add_default_sources(self, loader, temp_data_dir):
        """기본 데이터 소스 추가"""
        loader.add_default_sources()

        # 존재하는 디렉토리만 추가됨
        source_names = [s.name for s in loader.data_sources]
        assert "technical" in source_names
        assert "guides" in source_names
        assert "presentations" in source_names

    def test_get_status(self, loader, temp_data_dir):
        """로더 상태 정보 확인"""
        loader.add_source(DataSource(
            name="test",
            path=str(Path(temp_data_dir) / "knowledge_data" / "documents" / "technical"),
        ))

        status = loader.get_status()

        assert status["project_root"] == temp_data_dir
        assert len(status["data_sources"]) == 1
        assert status["config"]["chunk_size"] == 200

    def test_load_all_no_sources_raises(self, loader):
        """데이터 소스 없이 load_all 호출 시 ValueError"""
        with pytest.raises(ValueError, match="데이터 소스가 등록되지 않았습니다"):
            asyncio.get_event_loop().run_until_complete(loader.load_all())


class TestLoadAllMocked:
    """load_all 전체 파이프라인 Mock 테스트"""

    @pytest.mark.asyncio
    async def test_load_all_success(self, loader, temp_data_dir):
        """전체 ETL 파이프라인 성공 테스트 (Mock)"""
        loader.add_source(DataSource(
            name="technical",
            path=str(Path(temp_data_dir) / "knowledge_data" / "documents" / "technical"),
            doc_type=DocType.TECHNICAL,
        ))

        # Mock: 파싱 결과
        mock_parsed_doc = MagicMock()
        mock_parsed_doc.content = "# Test Document\n\nThis is test content with enough text."
        mock_parsed_doc.title = "Test Document"
        mock_parsed_doc.sections = [MagicMock(title="Section 1")]
        mock_parsed_doc.tables = []
        mock_parsed_doc.images = []
        mock_parsed_doc.id = "test-uuid"

        mock_parse_result = MagicMock()
        mock_parse_result.success = True
        mock_parse_result.document = mock_parsed_doc

        # Mock: 청킹 결과
        mock_chunk = MagicMock()
        mock_chunk.id = "chunk-1"
        mock_chunk.content = "Test chunk content with enough meaningful text for quality gate validation pass"
        mock_chunk.chunk_index = 0
        mock_chunk.heading = "Section 1"
        mock_chunk.token_count = 50

        mock_chunk_result = MagicMock()
        mock_chunk_result.chunks = [mock_chunk]
        mock_chunk_result.total_chunks = 1
        mock_chunk_result.avg_token_count = 50.0

        # Patch 서비스
        with patch.object(loader, "_parser", create=True) as mock_parser, \
             patch.object(loader, "_chunker", create=True) as mock_chunker:
            mock_parser.parse.return_value = mock_parse_result
            mock_chunker.chunk_document.return_value = mock_chunk_result

            # _store_document를 Mock으로 대체
            loader._store_document = AsyncMock()

            summary = await loader.load_all()

        assert summary.total_files == 3  # technical 폴더에 3개 파일
        assert summary.success_count == 3
        assert summary.failed_count == 0
        assert summary.total_chunks == 3  # 각 파일 1청크
        assert summary.success_rate == 1.0

    @pytest.mark.asyncio
    async def test_load_all_with_failures(self, loader, temp_data_dir):
        """파싱 실패 포함 ETL 테스트"""
        loader.add_source(DataSource(
            name="technical",
            path=str(Path(temp_data_dir) / "knowledge_data" / "documents" / "technical"),
            doc_type=DocType.TECHNICAL,
        ))

        call_count = 0

        def mock_parse(file_path):
            nonlocal call_count
            call_count += 1

            if call_count == 2:
                # 두 번째 파일 파싱 실패
                mock_result = MagicMock()
                mock_result.success = False
                mock_result.message = "Parse error"
                return mock_result

            mock_doc = MagicMock()
            mock_doc.content = "# Document\n\nContent here."
            mock_doc.title = "Test"
            mock_doc.sections = []
            mock_doc.tables = []
            mock_doc.images = []
            mock_doc.id = f"uuid-{call_count}"

            mock_result = MagicMock()
            mock_result.success = True
            mock_result.document = mock_doc
            return mock_result

        mock_chunk = MagicMock()
        mock_chunk.id = "chunk-1"
        mock_chunk.content = "Content with enough meaningful text for quality gate validation pass"
        mock_chunk.chunk_index = 0
        mock_chunk.heading = None
        mock_chunk.token_count = 50

        mock_chunk_result = MagicMock()
        mock_chunk_result.chunks = [mock_chunk]
        mock_chunk_result.total_chunks = 1
        mock_chunk_result.avg_token_count = 50.0

        with patch.object(loader, "_parser", create=True) as mock_parser, \
             patch.object(loader, "_chunker", create=True) as mock_chunker:
            mock_parser.parse.side_effect = mock_parse
            mock_chunker.chunk_document.return_value = mock_chunk_result

            loader._store_document = AsyncMock()

            summary = await loader.load_all()

        # 3개 파일 중 1개 실패 (파싱 실패 -> 건너뜀)
        assert summary.total_files == 3
        assert summary.success_count == 2
        # 파싱 실패 파일은 SKIPPED로 분류됨
        assert summary.skipped_count == 1

    @pytest.mark.asyncio
    async def test_load_all_continue_on_error(self, loader, temp_data_dir):
        """continue_on_error=True 시 에러 무시하고 계속 진행"""
        loader.continue_on_error = True
        loader.add_source(DataSource(
            name="technical",
            path=str(Path(temp_data_dir) / "knowledge_data" / "documents" / "technical"),
            doc_type=DocType.TECHNICAL,
        ))

        # 모든 파싱을 에러로 설정
        with patch.object(loader, "_parser", create=True) as mock_parser:
            mock_parser.parse.side_effect = Exception("Critical error")

            summary = await loader.load_all()

        # 모든 파일 실패하더라도 예외 발생하지 않음
        assert summary.total_files == 3
        assert summary.failed_count == 3


class TestSingletonFactory:
    """싱글톤 팩토리 테스트"""

    def test_singleton_creates_instance(self):
        """첫 호출 시 인스턴스 생성"""
        reset_initial_data_loader()
        loader1 = get_initial_data_loader()
        loader2 = get_initial_data_loader()
        assert loader1 is loader2

    def test_reset_clears_singleton(self):
        """reset 후 새 인스턴스 생성"""
        reset_initial_data_loader()
        loader1 = get_initial_data_loader()
        reset_initial_data_loader()
        loader2 = get_initial_data_loader()
        assert loader1 is not loader2


# ===========================================================================
# DataValidator Tests
# ===========================================================================


class TestValidationReport:
    """ValidationReport 테스트"""

    def test_empty_report(self):
        """빈 보고서"""
        report = ValidationReport()
        assert report.total_checks == 0
        assert report.is_valid is True  # SKIP level -> not FAIL
        assert report.overall_level == ValidationLevel.SKIP

    def test_add_pass_check(self):
        """통과 항목 추가"""
        report = ValidationReport()
        check = ValidationCheck(
            name="test",
            description="test check",
            level=ValidationLevel.PASS,
        )
        report.add_check(check)

        assert report.total_checks == 1
        assert report.passed_checks == 1
        assert report.overall_level == ValidationLevel.PASS
        assert report.is_valid is True

    def test_add_fail_check(self):
        """실패 항목 추가"""
        report = ValidationReport()
        report.add_check(ValidationCheck(
            name="pass_test",
            description="pass",
            level=ValidationLevel.PASS,
        ))
        report.add_check(ValidationCheck(
            name="fail_test",
            description="fail",
            level=ValidationLevel.FAIL,
        ))

        assert report.total_checks == 2
        assert report.passed_checks == 1
        assert report.failed_checks == 1
        assert report.overall_level == ValidationLevel.FAIL
        assert report.is_valid is False

    def test_to_dict(self):
        """딕셔너리 변환"""
        report = ValidationReport()
        report.add_check(ValidationCheck(
            name="test",
            description="desc",
            level=ValidationLevel.PASS,
        ))

        result = report.to_dict()
        assert result["overall_level"] == "pass"
        assert result["total_checks"] == 1
        assert len(result["checks"]) == 1

    def test_summary_string(self):
        """요약 문자열"""
        report = ValidationReport()
        report.add_check(ValidationCheck(
            name="test",
            description="desc",
            level=ValidationLevel.PASS,
        ))

        summary = report.summary()
        assert "PASS" in summary
        assert "total=1" in summary


class TestDocumentCountValidation:
    """문서 수 검증 테스트"""

    def test_pass_sufficient_docs(self, validator, sample_etl_summary):
        """충분한 문서 수 -> PASS"""
        check = validator._validate_document_count(sample_etl_summary)
        assert check.level == ValidationLevel.PASS

    def test_fail_insufficient_docs(self, validator):
        """부족한 문서 수 -> FAIL"""
        summary = ETLSummary(total_files=2, success_count=1)
        check = validator._validate_document_count(summary)
        assert check.level == ValidationLevel.FAIL

    def test_warning_partial_docs(self, validator):
        """50% 이상이면 WARNING"""
        summary = ETLSummary(total_files=3, success_count=2)
        check = validator._validate_document_count(summary)
        assert check.level == ValidationLevel.WARNING


class TestChunkCountValidation:
    """청크 수 검증 테스트"""

    def test_pass_sufficient_chunks(self, validator, sample_etl_summary):
        """충분한 청크 수 -> PASS"""
        check = validator._validate_chunk_count(sample_etl_summary)
        assert check.level == ValidationLevel.PASS

    def test_fail_zero_chunks(self, validator):
        """청크 0개 -> FAIL"""
        summary = ETLSummary(total_files=3, success_count=3, total_chunks=0)
        check = validator._validate_chunk_count(summary)
        assert check.level == ValidationLevel.FAIL


class TestEntityCountValidation:
    """엔티티 수 검증 테스트"""

    def test_pass_sufficient_entities(self, validator, sample_etl_summary):
        """충분한 엔티티 수 -> PASS"""
        check = validator._validate_entity_count(sample_etl_summary)
        assert check.level == ValidationLevel.PASS

    def test_warning_zero_entities(self, validator):
        """엔티티 0개 -> WARNING (비활성화 가능)"""
        summary = ETLSummary(total_files=3, success_count=3, total_entities=0)
        check = validator._validate_entity_count(summary)
        assert check.level == ValidationLevel.WARNING


class TestChunkRatioValidation:
    """문서당 청크 비율 검증 테스트"""

    def test_pass_good_ratio(self, validator, sample_etl_summary):
        """적절한 비율 -> PASS"""
        check = validator._validate_chunk_ratio(sample_etl_summary)
        assert check.level == ValidationLevel.PASS
        # 평균 16/3 = 5.33
        assert check.actual == pytest.approx(5.33, abs=0.01)

    def test_skip_no_success(self, validator):
        """성공 문서 없으면 SKIP"""
        summary = ETLSummary(total_files=0, success_count=0, total_chunks=0)
        check = validator._validate_chunk_ratio(summary)
        assert check.level == ValidationLevel.SKIP


class TestFailureRateValidation:
    """실패율 검증 테스트"""

    def test_pass_no_failures(self, validator, sample_etl_summary):
        """실패 없음 -> PASS"""
        check = validator._validate_failure_rate(sample_etl_summary)
        assert check.level == ValidationLevel.PASS

    def test_fail_high_failure_rate(self, validator, failed_etl_summary):
        """높은 실패율 -> FAIL"""
        check = validator._validate_failure_rate(failed_etl_summary)
        assert check.level == ValidationLevel.FAIL


class TestEmptyChunksValidation:
    """빈 청크 검증 테스트"""

    def test_pass_no_empty(self, validator, sample_etl_summary):
        """빈 청크 없음 -> PASS"""
        check = validator._validate_empty_chunks(sample_etl_summary)
        assert check.level == ValidationLevel.PASS


class TestSyncValidation:
    """동기 검증 테스트"""

    def test_validate_sync(self, validator, sample_etl_summary):
        """동기 검증 실행"""
        report = validator.validate_sync(sample_etl_summary)

        assert report.total_checks == 9
        assert report.is_valid is True

        # 샘플 쿼리와 고아 노드는 SKIP
        skip_checks = [c for c in report.checks if c.level == ValidationLevel.SKIP]
        assert len(skip_checks) == 2

    def test_validate_sync_with_failures(self, validator, failed_etl_summary):
        """실패 케이스 동기 검증"""
        report = validator.validate_sync(failed_etl_summary)

        # 실패율이 높으므로 FAIL
        assert report.is_valid is False
        assert report.failed_checks > 0


class TestValidatorSingleton:
    """DataValidator 싱글톤 테스트"""

    def test_singleton(self):
        """싱글톤 동작 확인"""
        reset_data_validator()
        v1 = get_data_validator()
        v2 = get_data_validator()
        assert v1 is v2

    def test_reset(self):
        """리셋 후 새 인스턴스"""
        reset_data_validator()
        v1 = get_data_validator()
        reset_data_validator()
        v2 = get_data_validator()
        assert v1 is not v2
