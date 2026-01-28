"""
초기 데이터 ETL 파이프라인

STORY-045: 프로젝트 문서를 Knowledge Graph 및 Vector Store에 적재하는 파이프라인.

Pipeline:
    1. 데이터 소스 탐색 (파일 디스커버리)
    2. 문서 파싱 (Markdown, PDF, DOCX 등)
    3. 시맨틱 청킹 (SemanticChunker)
    4. 임베딩 생성 (BGE-M3)
    5. 메타데이터 추출 (LLM 기반 문서 분류)
    6. 저장소 적재 (Elasticsearch + Neo4j)

지원 형식:
    - Markdown (.md)
    - PDF (.pdf)
    - DOCX (.docx)
    - PPTX (.pptx)
    - TXT (.txt)
    - HTML (.html/.htm)
"""

import asyncio
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


class DocType(str, Enum):
    """문서 유형 분류"""

    TECHNICAL = "technical"
    GUIDE = "guide"
    PRESENTATION = "presentation"
    POLICY = "policy"
    STANDARD = "standard"
    REPORT = "report"
    UNKNOWN = "unknown"


class LoadStatus(str, Enum):
    """로드 상태"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class DataSource:
    """데이터 소스 정의

    ETL 파이프라인에서 처리할 데이터 소스를 정의합니다.
    각 소스는 파일 경로, 문서 유형, 파일 확장자 필터를 포함합니다.

    Attributes:
        name: 데이터 소스 이름 (예: "technical", "guides")
        path: 데이터 소스 디렉토리 경로
        doc_type: 문서 유형 분류
        extensions: 허용할 파일 확장자 목록
        recursive: 하위 디렉토리 재귀 탐색 여부
        description: 데이터 소스 설명
    """

    name: str
    path: str
    doc_type: DocType = DocType.UNKNOWN
    extensions: List[str] = field(
        default_factory=lambda: [".md", ".pdf", ".docx", ".pptx", ".txt", ".html", ".htm"]
    )
    recursive: bool = True
    description: str = ""


@dataclass
class FileInfo:
    """탐색된 파일 정보

    Attributes:
        file_path: 파일 절대 경로
        file_name: 파일명 (확장자 포함)
        file_size: 파일 크기 (바이트)
        extension: 파일 확장자
        source_name: 소속 데이터 소스 이름
        doc_type: 문서 유형 분류
        modified_at: 최종 수정 시간
    """

    file_path: Path
    file_name: str
    file_size: int
    extension: str
    source_name: str
    doc_type: DocType
    modified_at: Optional[datetime] = None


@dataclass
class LoadResult:
    """개별 파일 로드 결과

    Attributes:
        file_path: 파일 경로
        file_name: 파일명
        status: 로드 상태
        document_id: 생성된 문서 ID (성공 시)
        chunk_count: 생성된 청크 수
        entity_count: 추출된 엔티티 수
        error_message: 에러 메시지 (실패 시)
        processing_time_ms: 처리 소요 시간 (밀리초)
    """

    file_path: str
    file_name: str
    status: LoadStatus = LoadStatus.PENDING
    document_id: Optional[str] = None
    chunk_count: int = 0
    entity_count: int = 0
    error_message: Optional[str] = None
    processing_time_ms: float = 0.0


@dataclass
class ETLSummary:
    """ETL 전체 실행 요약

    Attributes:
        total_files: 전체 파일 수
        success_count: 성공 파일 수
        failed_count: 실패 파일 수
        skipped_count: 건너뛴 파일 수
        total_chunks: 전체 생성 청크 수
        total_entities: 전체 추출 엔티티 수
        total_time_ms: 전체 소요 시간 (밀리초)
        results: 개별 파일 로드 결과 목록
        started_at: 시작 시간
        completed_at: 완료 시간
    """

    total_files: int = 0
    success_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    total_chunks: int = 0
    total_entities: int = 0
    total_time_ms: float = 0.0
    results: List[LoadResult] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def success_rate(self) -> float:
        """성공률 (0.0 ~ 1.0)"""
        if self.total_files == 0:
            return 0.0
        return self.success_count / self.total_files

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "total_files": self.total_files,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "skipped_count": self.skipped_count,
            "total_chunks": self.total_chunks,
            "total_entities": self.total_entities,
            "total_time_ms": round(self.total_time_ms, 2),
            "success_rate": round(self.success_rate * 100, 1),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


# ---------------------------------------------------------------------------
# InitialDataLoader
# ---------------------------------------------------------------------------


class InitialDataLoader:
    """초기 데이터 ETL 파이프라인

    프로젝트 문서를 Knowledge Graph(Neo4j) 및 Vector Store(Elasticsearch)에
    적재하는 전체 ETL 파이프라인을 수행합니다.

    Pipeline 단계:
        1. discover_files(): 데이터 소스에서 파일 탐색
        2. parse_document(): 문서 파싱 (DocumentParser)
        3. chunk_document(): 시맨틱 청킹 (SemanticChunker)
        4. generate_embeddings(): 임베딩 생성 (EmbeddingService)
        5. extract_metadata(): 메타데이터 추출 (LLM)
        6. store_to_elasticsearch(): ES 저장
        7. store_to_neo4j(): Neo4j 그래프 저장

    Features:
        - 배치 처리 지원
        - 재시도 로직 (최대 3회)
        - 상세 진행 로깅
        - 파일별 에러 격리 (continue_on_error)
        - 중복 문서 건너뛰기

    Example:
        loader = InitialDataLoader()
        loader.add_source(DataSource(
            name="technical",
            path="/data/documents/technical",
            doc_type=DocType.TECHNICAL,
        ))
        summary = await loader.load_all()
        print(f"Loaded {summary.success_count}/{summary.total_files} documents")

    Attributes:
        data_sources: 등록된 데이터 소스 목록
        chunk_size: 청크 크기 (문자 수)
        chunk_overlap: 청크 오버랩 (문자 수)
        batch_size: 임베딩 배치 크기
        max_retries: 최대 재시도 횟수
        continue_on_error: 에러 발생 시 계속 진행 여부
    """

    # 기본 데이터 소스 경로 (프로젝트 루트 기준)
    DEFAULT_DATA_DIR = "knowledge_data/documents"

    # 건너뛸 파일/디렉토리 패턴
    SKIP_PATTERNS = [
        r"__pycache__",
        r"\.git",
        r"node_modules",
        r"\.pytest_cache",
        r"\.vscode",
        r"\.idea",
        r"\.DS_Store",
        r"Thumbs\.db",
    ]

    def __init__(
        self,
        project_root: Optional[str] = None,
        chunk_size: int = 600,
        chunk_overlap: int = 100,
        batch_size: int = 32,
        max_retries: int = 3,
        continue_on_error: bool = True,
        enable_embeddings: bool = True,
        enable_entity_extraction: bool = True,
    ):
        """InitialDataLoader 초기화

        Args:
            project_root: 프로젝트 루트 경로 (None이면 자동 감지)
            chunk_size: 청크 크기 (문자 수)
            chunk_overlap: 청크 오버랩 (문자 수)
            batch_size: 임베딩 배치 크기
            max_retries: 최대 재시도 횟수
            continue_on_error: 에러 발생 시 계속 진행 여부
            enable_embeddings: 임베딩 생성 활성화 여부
            enable_entity_extraction: 엔티티 추출 활성화 여부
        """
        self.project_root = Path(project_root) if project_root else self._detect_project_root()
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.continue_on_error = continue_on_error
        self.enable_embeddings = enable_embeddings
        self.enable_entity_extraction = enable_entity_extraction

        self.data_sources: List[DataSource] = []
        self._skip_regex = re.compile("|".join(self.SKIP_PATTERNS))

        # 지연 초기화 서비스
        self._parser = None
        self._chunker = None
        self._embedding_service = None
        self._entity_extractor = None

        logger.info(
            "InitialDataLoader initialized: project_root=%s, chunk_size=%d, "
            "chunk_overlap=%d, batch_size=%d, max_retries=%d",
            self.project_root,
            self.chunk_size,
            self.chunk_overlap,
            self.batch_size,
            self.max_retries,
        )

    # ------------------------------------------------------------------
    # Properties (Lazy initialization)
    # ------------------------------------------------------------------

    @property
    def parser(self):
        """DocumentParser 인스턴스 (지연 로딩)"""
        if self._parser is None:
            from app.etl.parser import DocumentParser

            self._parser = DocumentParser(max_retries=self.max_retries)
        return self._parser

    @property
    def chunker(self):
        """SemanticChunker 인스턴스 (지연 로딩)"""
        if self._chunker is None:
            from app.etl.chunker import SemanticChunker

            self._chunker = SemanticChunker(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
            )
        return self._chunker

    @property
    def embedding_service(self):
        """EmbeddingService 인스턴스 (지연 로딩)"""
        if self._embedding_service is None:
            from app.services.embedding import get_embedding_service

            self._embedding_service = get_embedding_service()
        return self._embedding_service

    @property
    def entity_extractor(self):
        """EntityExtractionService 인스턴스 (지연 로딩)"""
        if self._entity_extractor is None:
            from app.services.entity_extraction import get_entity_extraction_service

            self._entity_extractor = get_entity_extraction_service()
        return self._entity_extractor

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_source(self, source: DataSource) -> None:
        """데이터 소스 추가

        Args:
            source: 추가할 데이터 소스
        """
        self.data_sources.append(source)
        logger.info(
            "Data source added: name=%s, path=%s, doc_type=%s",
            source.name,
            source.path,
            source.doc_type.value,
        )

    def add_default_sources(self) -> None:
        """기본 데이터 소스 추가

        knowledge_data/documents/ 하위의 표준 디렉토리를 데이터 소스로 등록합니다.
        """
        data_dir = self.project_root / self.DEFAULT_DATA_DIR

        default_sources = [
            DataSource(
                name="technical",
                path=str(data_dir / "technical"),
                doc_type=DocType.TECHNICAL,
                description="기술 문서 (설계서, 계획서 등)",
            ),
            DataSource(
                name="guides",
                path=str(data_dir / "guides"),
                doc_type=DocType.GUIDE,
                description="가이드/매뉴얼 문서",
            ),
            DataSource(
                name="presentations",
                path=str(data_dir / "presentations"),
                doc_type=DocType.PRESENTATION,
                extensions=[".pptx", ".pdf", ".md"],
                description="발표 자료",
            ),
            DataSource(
                name="policies",
                path=str(data_dir / "policies"),
                doc_type=DocType.POLICY,
                description="정책/규정 문서",
            ),
            DataSource(
                name="standards",
                path=str(data_dir / "standards"),
                doc_type=DocType.STANDARD,
                description="표준/기준 문서",
            ),
        ]

        for source in default_sources:
            if Path(source.path).exists():
                self.add_source(source)
            else:
                logger.debug(
                    "Default source path does not exist, skipping: %s", source.path
                )

    async def load_all(self) -> ETLSummary:
        """전체 데이터 로드 실행

        등록된 모든 데이터 소스에서 파일을 탐색하고 ETL 파이프라인을 실행합니다.

        Returns:
            ETLSummary: 전체 ETL 실행 결과 요약

        Raises:
            ValueError: 데이터 소스가 등록되지 않은 경우
        """
        if not self.data_sources:
            raise ValueError(
                "데이터 소스가 등록되지 않았습니다. "
                "add_source() 또는 add_default_sources()를 먼저 호출하세요."
            )

        summary = ETLSummary(started_at=datetime.utcnow())
        start_time = time.monotonic()

        logger.info(
            "ETL pipeline started: %d data sources", len(self.data_sources)
        )

        for source in self.data_sources:
            try:
                source_results = await self._load_source(source)
                summary.results.extend(source_results)
            except Exception as e:
                logger.error(
                    "Failed to process data source '%s': %s", source.name, e
                )
                if not self.continue_on_error:
                    raise

        # 요약 집계
        for result in summary.results:
            summary.total_files += 1
            if result.status == LoadStatus.SUCCESS:
                summary.success_count += 1
                summary.total_chunks += result.chunk_count
                summary.total_entities += result.entity_count
            elif result.status == LoadStatus.FAILED:
                summary.failed_count += 1
            elif result.status == LoadStatus.SKIPPED:
                summary.skipped_count += 1

        summary.total_time_ms = (time.monotonic() - start_time) * 1000
        summary.completed_at = datetime.utcnow()

        logger.info(
            "ETL pipeline completed: files=%d, success=%d, failed=%d, "
            "skipped=%d, chunks=%d, entities=%d, time=%.1fms, rate=%.1f%%",
            summary.total_files,
            summary.success_count,
            summary.failed_count,
            summary.skipped_count,
            summary.total_chunks,
            summary.total_entities,
            summary.total_time_ms,
            summary.success_rate * 100,
        )

        return summary

    def discover_files(self) -> List[FileInfo]:
        """모든 데이터 소스에서 파일 탐색

        Returns:
            탐색된 FileInfo 목록
        """
        all_files: List[FileInfo] = []

        for source in self.data_sources:
            files = self._discover_files(source)
            all_files.extend(files)

        logger.info("Total files discovered: %d", len(all_files))
        return all_files

    # ------------------------------------------------------------------
    # Internal: Source Processing
    # ------------------------------------------------------------------

    async def _load_source(self, source: DataSource) -> List[LoadResult]:
        """개별 데이터 소스 처리

        Args:
            source: 처리할 데이터 소스

        Returns:
            LoadResult 리스트
        """
        logger.info(
            "Processing data source: name=%s, path=%s",
            source.name,
            source.path,
        )

        files = self._discover_files(source)
        if not files:
            logger.warning("No files found in data source: %s", source.name)
            return []

        logger.info(
            "Found %d files in data source '%s'", len(files), source.name
        )

        results: List[LoadResult] = []

        for file_info in files:
            result = await self._process_file(file_info)
            results.append(result)

            if result.status == LoadStatus.FAILED and not self.continue_on_error:
                logger.error(
                    "Stopping due to error in file: %s", file_info.file_name
                )
                break

        success = sum(1 for r in results if r.status == LoadStatus.SUCCESS)
        failed = sum(1 for r in results if r.status == LoadStatus.FAILED)
        logger.info(
            "Data source '%s' completed: total=%d, success=%d, failed=%d",
            source.name,
            len(results),
            success,
            failed,
        )

        return results

    def _discover_files(self, source: DataSource) -> List[FileInfo]:
        """데이터 소스에서 파일 탐색

        지정된 경로에서 허용된 확장자의 파일을 재귀적으로 탐색합니다.
        건너뛸 패턴에 해당하는 파일/디렉토리는 제외합니다.

        Args:
            source: 데이터 소스

        Returns:
            탐색된 FileInfo 목록
        """
        source_path = Path(source.path)
        if not source_path.exists():
            logger.warning("Source path does not exist: %s", source.path)
            return []

        if not source_path.is_dir():
            logger.warning("Source path is not a directory: %s", source.path)
            return []

        files: List[FileInfo] = []

        if source.recursive:
            file_iter = source_path.rglob("*")
        else:
            file_iter = source_path.glob("*")

        for file_path in file_iter:
            # 디렉토리 건너뛰기
            if not file_path.is_file():
                continue

            # 건너뛸 패턴 확인
            if self._should_skip(file_path):
                continue

            # 확장자 필터
            ext = file_path.suffix.lower()
            if ext not in source.extensions:
                continue

            try:
                stat = file_path.stat()
                file_info = FileInfo(
                    file_path=file_path,
                    file_name=file_path.name,
                    file_size=stat.st_size,
                    extension=ext,
                    source_name=source.name,
                    doc_type=source.doc_type,
                    modified_at=datetime.fromtimestamp(stat.st_mtime),
                )
                files.append(file_info)
            except OSError as e:
                logger.warning("Cannot stat file %s: %s", file_path, e)

        # 파일명 기준 정렬 (재현 가능한 순서)
        files.sort(key=lambda f: f.file_name)

        logger.info(
            "Discovered %d files in source '%s' (%s)",
            len(files),
            source.name,
            source.path,
        )

        return files

    def _should_skip(self, file_path: Path) -> bool:
        """파일을 건너뛸지 결정

        Args:
            file_path: 확인할 파일 경로

        Returns:
            건너뛰어야 하면 True
        """
        path_str = str(file_path)
        return bool(self._skip_regex.search(path_str))

    # ------------------------------------------------------------------
    # Internal: File Processing Pipeline
    # ------------------------------------------------------------------

    async def _process_file(self, file_info: FileInfo) -> LoadResult:
        """개별 파일 ETL 처리

        재시도 로직이 포함된 전체 ETL 파이프라인을 개별 파일에 대해 수행합니다.

        Args:
            file_info: 처리할 파일 정보

        Returns:
            LoadResult: 처리 결과
        """
        result = LoadResult(
            file_path=str(file_info.file_path),
            file_name=file_info.file_name,
            status=LoadStatus.IN_PROGRESS,
        )

        start_time = time.monotonic()

        for attempt in range(self.max_retries):
            try:
                logger.info(
                    "Processing file [%d/%d]: %s (attempt %d)",
                    attempt + 1,
                    self.max_retries,
                    file_info.file_name,
                    attempt + 1,
                )

                # Step 1: 파싱
                parsed_doc = self._parse_file(file_info)
                if parsed_doc is None:
                    result.status = LoadStatus.SKIPPED
                    result.error_message = "Parser returned empty result"
                    logger.warning("Skipping file (empty parse): %s", file_info.file_name)
                    break

                # Step 2: 청킹
                chunks = self._chunk_document(parsed_doc)
                result.chunk_count = len(chunks)

                if not chunks:
                    result.status = LoadStatus.SKIPPED
                    result.error_message = "No chunks generated"
                    logger.warning("Skipping file (no chunks): %s", file_info.file_name)
                    break

                # Step 3: 메타데이터 추출
                metadata = self._extract_metadata(file_info, parsed_doc)

                # Step 4: 임베딩 생성 (선택적)
                embeddings = None
                if self.enable_embeddings:
                    try:
                        embeddings = await self._generate_embeddings(chunks)
                    except Exception as e:
                        logger.warning(
                            "Embedding generation failed for %s: %s (continuing without embeddings)",
                            file_info.file_name,
                            e,
                        )

                # Step 5: 엔티티 추출 (선택적)
                entities = []
                if self.enable_entity_extraction:
                    try:
                        entities = await self._extract_entities(parsed_doc)
                        result.entity_count = len(entities)
                    except Exception as e:
                        logger.warning(
                            "Entity extraction failed for %s: %s (continuing without entities)",
                            file_info.file_name,
                            e,
                        )

                # Step 6: 저장 (Elasticsearch + Neo4j)
                document_id = str(uuid4())
                await self._store_document(
                    document_id=document_id,
                    file_info=file_info,
                    parsed_doc=parsed_doc,
                    chunks=chunks,
                    embeddings=embeddings,
                    entities=entities,
                    metadata=metadata,
                )

                result.document_id = document_id
                result.status = LoadStatus.SUCCESS
                result.processing_time_ms = (time.monotonic() - start_time) * 1000

                logger.info(
                    "File processed successfully: %s (doc_id=%s, chunks=%d, entities=%d, time=%.1fms)",
                    file_info.file_name,
                    document_id[:8],
                    result.chunk_count,
                    result.entity_count,
                    result.processing_time_ms,
                )
                break

            except Exception as e:
                logger.warning(
                    "File processing failed [attempt %d/%d]: %s - %s",
                    attempt + 1,
                    self.max_retries,
                    file_info.file_name,
                    str(e),
                )
                result.error_message = str(e)

                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.info("Retrying in %ds...", wait_time)
                    await asyncio.sleep(wait_time)
                else:
                    result.status = LoadStatus.FAILED
                    result.processing_time_ms = (time.monotonic() - start_time) * 1000
                    logger.error(
                        "File processing failed after %d attempts: %s - %s",
                        self.max_retries,
                        file_info.file_name,
                        result.error_message,
                    )

        return result

    # ------------------------------------------------------------------
    # Internal: Pipeline Steps
    # ------------------------------------------------------------------

    def _parse_file(self, file_info: FileInfo) -> Optional[Any]:
        """파일 파싱

        DocumentParser를 사용하여 파일을 파싱합니다.

        Args:
            file_info: 파일 정보

        Returns:
            ParsedDocument 또는 None (파싱 실패 시)
        """
        try:
            parse_result = self.parser.parse(file_info.file_path)

            if not parse_result.success:
                logger.warning(
                    "Parse failed for %s: %s",
                    file_info.file_name,
                    parse_result.message,
                )
                return None

            parsed_doc = parse_result.document

            # 빈 문서 체크
            if not parsed_doc.content or not parsed_doc.content.strip():
                logger.warning("Empty content after parsing: %s", file_info.file_name)
                return None

            logger.debug(
                "Parsed %s: content_length=%d, sections=%d",
                file_info.file_name,
                len(parsed_doc.content),
                len(parsed_doc.sections) if parsed_doc.sections else 0,
            )

            return parsed_doc

        except Exception as e:
            logger.error("Parse error for %s: %s", file_info.file_name, e)
            raise

    def _chunk_document(self, parsed_doc: Any) -> List[Any]:
        """문서 청킹

        SemanticChunker를 사용하여 문서를 청크로 분할합니다.

        Args:
            parsed_doc: 파싱된 문서

        Returns:
            Chunk 객체 리스트
        """
        try:
            chunk_result = self.chunker.chunk_document(parsed_doc)
            chunks = chunk_result.chunks

            logger.debug(
                "Chunked document: total_chunks=%d, avg_tokens=%.1f",
                chunk_result.total_chunks,
                chunk_result.avg_token_count,
            )

            return chunks

        except Exception as e:
            logger.error("Chunking error: %s", e)
            raise

    def _extract_metadata(
        self,
        file_info: FileInfo,
        parsed_doc: Any,
    ) -> Dict[str, Any]:
        """파일 및 문서에서 메타데이터 추출

        파일 경로, 확장자, 문서 내용 등에서 메타데이터를 추출합니다.
        LLM 기반 추출은 선택적으로 수행합니다.

        Args:
            file_info: 파일 정보
            parsed_doc: 파싱된 문서

        Returns:
            메타데이터 딕셔너리
        """
        metadata: Dict[str, Any] = {
            "source_name": file_info.source_name,
            "doc_type": self._classify_doc_type(file_info, parsed_doc),
            "file_name": file_info.file_name,
            "file_path": str(file_info.file_path),
            "file_size": file_info.file_size,
            "extension": file_info.extension,
            "modified_at": file_info.modified_at.isoformat() if file_info.modified_at else None,
            "content_length": len(parsed_doc.content) if parsed_doc.content else 0,
            "title": getattr(parsed_doc, "title", None) or file_info.file_name,
        }

        # 섹션 정보 추가
        if hasattr(parsed_doc, "sections") and parsed_doc.sections:
            metadata["section_count"] = len(parsed_doc.sections)
            metadata["section_titles"] = [
                s.title for s in parsed_doc.sections if s.title
            ][:10]  # 최대 10개 섹션 제목

        # 표/이미지 정보
        if hasattr(parsed_doc, "tables") and parsed_doc.tables:
            metadata["table_count"] = len(parsed_doc.tables)
        if hasattr(parsed_doc, "images") and parsed_doc.images:
            metadata["image_count"] = len(parsed_doc.images)

        return metadata

    def _classify_doc_type(
        self,
        file_info: FileInfo,
        parsed_doc: Any,
    ) -> str:
        """문서 유형 분류

        파일 경로와 내용을 기반으로 문서 유형을 분류합니다.

        Args:
            file_info: 파일 정보
            parsed_doc: 파싱된 문서

        Returns:
            문서 유형 문자열
        """
        # 데이터 소스에서 지정한 유형이 있으면 사용
        if file_info.doc_type != DocType.UNKNOWN:
            return file_info.doc_type.value

        # 파일 경로 기반 분류
        path_str = str(file_info.file_path).lower()

        path_type_map = {
            "design": "technical",
            "planning": "technical",
            "implementation": "technical",
            "testing": "technical",
            "development": "guide",
            "deployment": "guide",
            "maintenance": "guide",
            "guide": "guide",
            "manual": "guide",
            "presentation": "presentation",
            "policy": "policy",
            "standard": "standard",
            "report": "report",
        }

        for keyword, doc_type in path_type_map.items():
            if keyword in path_str:
                return doc_type

        # 내용 기반 분류 (간단한 규칙)
        if parsed_doc and parsed_doc.content:
            content_preview = parsed_doc.content[:2000].lower()

            if any(kw in content_preview for kw in ["설계", "아키텍처", "스키마", "api"]):
                return "technical"
            if any(kw in content_preview for kw in ["가이드", "매뉴얼", "사용법", "설치"]):
                return "guide"
            if any(kw in content_preview for kw in ["보고", "결과", "분석"]):
                return "report"

        return "unknown"

    async def _generate_embeddings(
        self,
        chunks: List[Any],
    ) -> Optional[List[Any]]:
        """청크에 대한 임베딩 생성

        BGE-M3 임베딩 서비스를 사용하여 벡터를 생성합니다.

        Args:
            chunks: Chunk 객체 리스트

        Returns:
            ChunkEmbedding 리스트 또는 None
        """
        if not chunks:
            return None

        try:
            chunk_ids = [chunk.id for chunk in chunks]
            texts = [chunk.content for chunk in chunks]

            embeddings = await self.embedding_service.aembed_chunks(
                chunk_ids=chunk_ids,
                texts=texts,
                return_sparse=True,
            )

            logger.debug(
                "Generated embeddings: %d chunks, dimension=%d",
                len(embeddings),
                self.embedding_service.vector_dimension,
            )

            return embeddings

        except Exception as e:
            logger.error("Embedding generation failed: %s", e)
            raise

    async def _extract_entities(self, parsed_doc: Any) -> List[Any]:
        """엔티티 추출

        LLM 기반 엔티티 추출 서비스를 사용합니다.

        Args:
            parsed_doc: 파싱된 문서

        Returns:
            Entity 리스트
        """
        if not parsed_doc or not parsed_doc.content:
            return []

        try:
            entities = await self.entity_extractor.extract_entities(
                text=parsed_doc.content,
                enable_gleaning=True,
            )

            logger.debug("Extracted %d entities", len(entities))
            return entities

        except Exception as e:
            logger.error("Entity extraction failed: %s", e)
            raise

    async def _store_document(
        self,
        document_id: str,
        file_info: FileInfo,
        parsed_doc: Any,
        chunks: List[Any],
        embeddings: Optional[List[Any]],
        entities: List[Any],
        metadata: Dict[str, Any],
    ) -> None:
        """문서 데이터를 저장소에 적재

        Elasticsearch (청크 + 벡터) 및 Neo4j (엔티티 + 관계)에 저장합니다.
        저장소가 사용 불가능한 경우 로깅 후 건너뜁니다.

        Args:
            document_id: 문서 ID
            file_info: 파일 정보
            parsed_doc: 파싱된 문서
            chunks: 청크 리스트
            embeddings: 임베딩 리스트 (선택)
            entities: 엔티티 리스트
            metadata: 메타데이터 딕셔너리
        """
        # Elasticsearch 저장
        await self._store_to_elasticsearch(
            document_id=document_id,
            chunks=chunks,
            embeddings=embeddings,
            metadata=metadata,
        )

        # Neo4j 저장
        await self._store_to_neo4j(
            document_id=document_id,
            file_info=file_info,
            chunks=chunks,
            entities=entities,
            metadata=metadata,
        )

    async def _store_to_elasticsearch(
        self,
        document_id: str,
        chunks: List[Any],
        embeddings: Optional[List[Any]],
        metadata: Dict[str, Any],
    ) -> None:
        """Elasticsearch에 청크 및 벡터 저장

        Args:
            document_id: 문서 ID
            chunks: 청크 리스트
            embeddings: 임베딩 리스트
            metadata: 메타데이터
        """
        try:
            # Elasticsearch 클라이언트 확인
            es_url = settings.elasticsearch_url
            index_name = settings.elasticsearch_index

            logger.info(
                "Storing to Elasticsearch: doc_id=%s, chunks=%d, index=%s",
                document_id[:8],
                len(chunks),
                index_name,
            )

            # 벌크 인덱싱 문서 준비
            bulk_docs = []
            for i, chunk in enumerate(chunks):
                doc = {
                    "document_id": document_id,
                    "chunk_id": chunk.id,
                    "chunk_index": i,
                    "content": chunk.content,
                    "heading": chunk.heading,
                    "token_count": chunk.token_count,
                    "metadata": metadata,
                    "created_at": datetime.utcnow().isoformat(),
                }

                # 임베딩 벡터 추가
                if embeddings and i < len(embeddings):
                    doc["dense_vector"] = embeddings[i].dense_vector
                    if embeddings[i].sparse_vector:
                        doc["sparse_vector"] = embeddings[i].sparse_vector

                bulk_docs.append(doc)

            # 실제 ES 클라이언트 호출 (연결 가능 시)
            try:
                from elasticsearch import AsyncElasticsearch

                es = AsyncElasticsearch(es_url)
                try:
                    # 벌크 인덱싱
                    actions = []
                    for doc in bulk_docs:
                        actions.append({"index": {"_index": index_name, "_id": doc["chunk_id"]}})
                        actions.append(doc)

                    if actions:
                        await es.bulk(operations=actions, refresh="wait_for")
                        logger.info(
                            "Elasticsearch bulk indexed: %d documents", len(bulk_docs)
                        )
                finally:
                    await es.close()

            except ImportError:
                logger.warning(
                    "elasticsearch package not installed, skipping ES storage "
                    "(prepared %d documents for indexing)",
                    len(bulk_docs),
                )
            except Exception as e:
                logger.warning(
                    "Elasticsearch storage failed (non-critical): %s", e
                )

        except Exception as e:
            logger.error("Elasticsearch storage error: %s", e)
            # 비치명적 에러 - 계속 진행

    async def _store_to_neo4j(
        self,
        document_id: str,
        file_info: FileInfo,
        chunks: List[Any],
        entities: List[Any],
        metadata: Dict[str, Any],
    ) -> None:
        """Neo4j에 그래프 데이터 저장

        Args:
            document_id: 문서 ID
            file_info: 파일 정보
            chunks: 청크 리스트
            entities: 엔티티 리스트
            metadata: 메타데이터
        """
        try:
            logger.info(
                "Storing to Neo4j: doc_id=%s, chunks=%d, entities=%d",
                document_id[:8],
                len(chunks),
                len(entities),
            )

            try:
                from neo4j import AsyncGraphDatabase

                driver = AsyncGraphDatabase.driver(
                    settings.neo4j_uri,
                    auth=(settings.neo4j_user, settings.neo4j_password or ""),
                )

                try:
                    async with driver.session() as session:
                        # Document 노드 생성
                        await session.run(
                            """
                            MERGE (d:Document {id: $doc_id})
                            SET d.title = $title,
                                d.file_path = $file_path,
                                d.doc_type = $doc_type,
                                d.created_at = datetime()
                            """,
                            doc_id=document_id,
                            title=metadata.get("title", file_info.file_name),
                            file_path=str(file_info.file_path),
                            doc_type=metadata.get("doc_type", "unknown"),
                        )

                        # Chunk 노드 및 PART_OF 관계 생성
                        for chunk in chunks:
                            await session.run(
                                """
                                MERGE (c:Chunk {id: $chunk_id})
                                SET c.content = $content,
                                    c.chunk_index = $chunk_index,
                                    c.heading = $heading
                                WITH c
                                MATCH (d:Document {id: $doc_id})
                                MERGE (c)-[:PART_OF]->(d)
                                """,
                                chunk_id=chunk.id,
                                content=chunk.content[:500],  # 저장 시 내용 제한
                                chunk_index=chunk.chunk_index,
                                heading=chunk.heading,
                                doc_id=document_id,
                            )

                        # Entity 노드 및 MENTIONED_IN 관계 생성
                        for entity in entities:
                            await session.run(
                                """
                                MERGE (e:Entity {name: $name})
                                SET e.type = $type,
                                    e.description = $description
                                """,
                                name=entity.name,
                                type=entity.type,
                                description=getattr(entity, "description", None),
                            )

                        logger.info(
                            "Neo4j storage completed: doc=%s, chunks=%d, entities=%d",
                            document_id[:8],
                            len(chunks),
                            len(entities),
                        )

                finally:
                    await driver.close()

            except ImportError:
                logger.warning(
                    "neo4j package not installed, skipping Neo4j storage "
                    "(prepared doc=%s, chunks=%d, entities=%d)",
                    document_id[:8],
                    len(chunks),
                    len(entities),
                )
            except Exception as e:
                logger.warning(
                    "Neo4j storage failed (non-critical): %s", e
                )

        except Exception as e:
            logger.error("Neo4j storage error: %s", e)

    # ------------------------------------------------------------------
    # Utility Methods
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_project_root() -> Path:
        """프로젝트 루트 디렉토리 자동 감지

        Returns:
            프로젝트 루트 Path
        """
        # 현재 파일 기준으로 프로젝트 루트 탐색
        current = Path(__file__).resolve()

        # knowledge_service/src/app/services/ -> 4단계 위
        for _ in range(10):
            if (current / "CLAUDE.md").exists() or (current / "knowledge_service").exists():
                return current
            current = current.parent

        # 폴백: CWD
        return Path.cwd()

    def get_status(self) -> Dict[str, Any]:
        """로더 상태 정보 반환

        Returns:
            상태 딕셔너리
        """
        return {
            "project_root": str(self.project_root),
            "data_sources": [
                {
                    "name": s.name,
                    "path": s.path,
                    "doc_type": s.doc_type.value,
                    "exists": Path(s.path).exists(),
                }
                for s in self.data_sources
            ],
            "config": {
                "chunk_size": self.chunk_size,
                "chunk_overlap": self.chunk_overlap,
                "batch_size": self.batch_size,
                "max_retries": self.max_retries,
                "continue_on_error": self.continue_on_error,
                "enable_embeddings": self.enable_embeddings,
                "enable_entity_extraction": self.enable_entity_extraction,
            },
        }


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------

_initial_data_loader: Optional[InitialDataLoader] = None


def get_initial_data_loader(**kwargs: Any) -> InitialDataLoader:
    """InitialDataLoader 싱글톤 팩토리

    Args:
        **kwargs: InitialDataLoader 생성자 인자

    Returns:
        InitialDataLoader 인스턴스 (싱글톤)
    """
    global _initial_data_loader
    if _initial_data_loader is None:
        _initial_data_loader = InitialDataLoader(**kwargs)
    return _initial_data_loader


def reset_initial_data_loader() -> None:
    """싱글톤 인스턴스 초기화 (테스트용)"""
    global _initial_data_loader
    _initial_data_loader = None
