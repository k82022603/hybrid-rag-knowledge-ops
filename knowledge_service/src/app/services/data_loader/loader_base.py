"""
InitialDataLoader 코어 모듈

ETL 파이프라인의 메인 오케스트레이터 클래스를 정의합니다.
파일 탐색, 중복 검사, 파이프라인 실행 등 핵심 로직을 담당하며,
실제 파싱/임베딩/저장 작업은 각 서브 모듈에 위임합니다.

Classes:
    InitialDataLoader: 초기 데이터 ETL 파이프라인 오케스트레이터
"""

import asyncio
import hashlib
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.core.config import settings
from app.core.logging import get_logger
from app.services.data_loader.document_loader import (
    chunk_document,
    extract_metadata,
    parse_file,
)
from app.services.data_loader.embedding_loader import (
    extract_entities,
    generate_embeddings,
)
from app.services.data_loader.models import (
    DataSource,
    DocType,
    ETLSummary,
    FileInfo,
    LoadResult,
    LoadStatus,
)
from app.services.data_loader.pg_loader import store_document

logger = get_logger(__name__)


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
        self._es_client = None  # ES 클라이언트 싱글톤 (P0 수정: 매번 재생성 방지)

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

        # ES 클라이언트 정리
        if self._es_client is not None:
            try:
                await self._es_client.close()
            except Exception:
                pass
            self._es_client = None

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
    # Internal: Dedup (STORY-108)
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_file_hash(file_path: Path) -> str:
        """파일 SHA-256 해시 계산

        Args:
            file_path: 파일 경로

        Returns:
            SHA-256 해시 문자열 (64자 hex)
        """
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for block in iter(lambda: f.read(8192), b""):
                sha256.update(block)
        return sha256.hexdigest()

    async def _check_duplicate(self, file_hash: str, file_path: str) -> Optional[str]:
        """PG에서 file_hash 기반 중복 문서 확인

        Args:
            file_hash: 파일 SHA-256 해시
            file_path: 파일 경로 (로깅용)

        Returns:
            기존 document_id (중복 시) 또는 None (신규 시)
        """
        try:
            from app.services.document_repository import get_document_repository

            repo = await get_document_repository()

            if repo._pool is None:
                logger.warning("PG pool not available, skipping dedup check")
                return None

            async with repo._pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT id, file_path, processing_status
                    FROM documents
                    WHERE file_hash = $1
                    LIMIT 1
                    """,
                    file_hash,
                )

                if row:
                    logger.info(
                        "Duplicate detected: file_hash=%s, existing_doc=%s, "
                        "existing_path=%s, new_path=%s",
                        file_hash[:16],
                        str(row["id"])[:8],
                        row["file_path"],
                        file_path,
                    )
                    return str(row["id"])

                return None

        except Exception as e:
            logger.warning("Dedup check failed (proceeding without): %s", e)
            return None

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

        # Step 0: 중복 검사 (STORY-108)
        file_hash = self._compute_file_hash(file_info.file_path)
        existing_doc_id = await self._check_duplicate(
            file_hash=file_hash,
            file_path=str(file_info.file_path),
        )
        if existing_doc_id:
            result.status = LoadStatus.SKIPPED
            result.document_id = existing_doc_id
            result.error_message = f"Duplicate: file_hash matches doc {existing_doc_id[:8]}"
            result.processing_time_ms = (time.monotonic() - start_time) * 1000
            logger.info(
                "Skipping duplicate file: %s (existing doc_id=%s, hash=%s)",
                file_info.file_name,
                existing_doc_id[:8],
                file_hash[:16],
            )
            return result

        for attempt in range(self.max_retries):
            try:
                logger.info(
                    "Processing file [%d/%d]: %s (attempt %d)",
                    attempt + 1,
                    self.max_retries,
                    file_info.file_name,
                    attempt + 1,
                )

                # Step 1: 파싱 (document_loader 모듈 위임)
                parsed_doc = self._parse_file(file_info)
                if parsed_doc is None:
                    result.status = LoadStatus.SKIPPED
                    result.error_message = "Parser returned empty result"
                    logger.warning("Skipping file (empty parse): %s", file_info.file_name)
                    break

                # Step 2: 청킹 (document_loader 모듈 위임)
                chunks = self._chunk_document(parsed_doc)

                if not chunks:
                    result.status = LoadStatus.SKIPPED
                    result.error_message = "No chunks generated"
                    logger.warning("Skipping file (no chunks): %s", file_info.file_name)
                    break

                # Step 2.5: 청크 품질 게이트 (P0 수정: 2026-02-14)
                from app.services.chunk_quality_filter import ChunkQualityGate
                quality_gate = ChunkQualityGate()
                chunks, rejected_chunks = quality_gate.filter(chunks)

                if rejected_chunks:
                    logger.info(
                        "Quality gate for %s: %d passed, %d rejected",
                        file_info.file_name,
                        len(chunks),
                        len(rejected_chunks),
                    )

                result.chunk_count = len(chunks)

                if not chunks:
                    result.status = LoadStatus.SKIPPED
                    result.error_message = "All chunks rejected by quality gate"
                    logger.warning(
                        "Skipping file (all chunks rejected): %s", file_info.file_name
                    )
                    break

                # Step 3: 메타데이터 추출 (document_loader 모듈 위임)
                metadata = self._extract_metadata(file_info, parsed_doc)

                # Step 4+5: 임베딩 + 엔티티 병렬 실행 (v2.1 최적화)
                # CPU-bound(임베딩) + IO-bound(엔티티 API) -> asyncio.gather로 동시 실행
                embeddings = None
                entities = []

                async def _safe_embed():
                    if self.enable_embeddings:
                        try:
                            return await generate_embeddings(self.embedding_service, chunks)
                        except Exception as e:
                            logger.warning(
                                "Embedding generation failed for %s: %s (continuing without embeddings)",
                                file_info.file_name,
                                e,
                            )
                    return None

                async def _safe_entity():
                    if self.enable_entity_extraction:
                        try:
                            return await extract_entities(self.entity_extractor, parsed_doc)
                        except Exception as e:
                            logger.warning(
                                "Entity extraction failed for %s: %s (continuing without entities)",
                                file_info.file_name,
                                e,
                            )
                    return []

                embeddings, entities = await asyncio.gather(
                    _safe_embed(), _safe_entity()
                )
                result.entity_count = len(entities) if entities else 0

                # Step 6: 저장 (PostgreSQL -> Elasticsearch -> Neo4j)
                document_id = str(uuid4())
                effective_doc_id = await self._store_document(
                    document_id=document_id,
                    file_info=file_info,
                    parsed_doc=parsed_doc,
                    chunks=chunks,
                    embeddings=embeddings,
                    entities=entities,
                    metadata=metadata,
                    file_hash=file_hash,
                )

                result.document_id = effective_doc_id
                result.status = LoadStatus.SUCCESS
                result.processing_time_ms = (time.monotonic() - start_time) * 1000

                logger.info(
                    "File processed successfully: %s (doc_id=%s, chunks=%d, entities=%d, time=%.1fms)",
                    file_info.file_name,
                    effective_doc_id[:8],
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
    # Internal: Pipeline Steps (delegate to sub-modules)
    # ------------------------------------------------------------------

    def _parse_file(self, file_info: FileInfo) -> Optional[Any]:
        """파일 파싱 (document_loader 모듈에 위임)"""
        return parse_file(self.parser, file_info)

    def _chunk_document(self, parsed_doc: Any) -> List[Any]:
        """문서 청킹 (document_loader 모듈에 위임)"""
        return chunk_document(self.chunker, parsed_doc)

    def _extract_metadata(
        self,
        file_info: FileInfo,
        parsed_doc: Any,
    ) -> Dict[str, Any]:
        """메타데이터 추출 (document_loader 모듈에 위임)"""
        return extract_metadata(file_info, parsed_doc)

    def _classify_doc_type(
        self,
        file_info: FileInfo,
        parsed_doc: Any,
    ) -> str:
        """문서 유형 분류 (document_loader 모듈에 위임)

        backward compatibility를 위해 유지합니다.
        """
        from app.services.data_loader.document_loader import classify_doc_type
        return classify_doc_type(file_info, parsed_doc)

    async def _generate_embeddings(
        self,
        chunks: List[Any],
    ) -> Optional[List[Any]]:
        """임베딩 생성 (embedding_loader 모듈에 위임)

        backward compatibility를 위해 유지합니다.
        """
        return await generate_embeddings(self.embedding_service, chunks)

    async def _extract_entities(self, parsed_doc: Any) -> List[Any]:
        """엔티티 추출 (embedding_loader 모듈에 위임)

        backward compatibility를 위해 유지합니다.
        """
        return await extract_entities(self.entity_extractor, parsed_doc)

    async def _store_document(
        self,
        document_id: str,
        file_info: FileInfo,
        parsed_doc: Any,
        chunks: List[Any],
        embeddings: Optional[List[Any]],
        entities: List[Any],
        metadata: Dict[str, Any],
        file_hash: Optional[str] = None,
    ) -> str:
        """문서 저장 (pg_loader 모듈에 위임)"""
        return await store_document(
            document_id=document_id,
            file_info=file_info,
            parsed_doc=parsed_doc,
            chunks=chunks,
            embeddings=embeddings,
            entities=entities,
            metadata=metadata,
            file_hash=file_hash,
            es_client_holder=self,
        )

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

        # knowledge_service/src/app/services/data_loader/ -> 5단계 위
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
