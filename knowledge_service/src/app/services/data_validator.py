"""
초기 데이터 검증 서비스

STORY-045: ETL 파이프라인 실행 결과를 검증합니다.

검증 항목:
    1. 문서 수 검증 (최소 기대치 대비)
    2. 청크 수 검증 (문서 대비 합리적 비율)
    3. 엔티티 수 검증 (최소 기대치)
    4. 샘플 쿼리 테스트 (관련 문서 검색 확인)
    5. 데이터 무결성 검증 (고아 노드, 빈 청크 등)
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Validation Models
# ---------------------------------------------------------------------------


class ValidationLevel(str, Enum):
    """검증 수준"""

    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"
    SKIP = "skip"


@dataclass
class ValidationCheck:
    """개별 검증 항목 결과

    Attributes:
        name: 검증 항목 이름
        description: 검증 항목 설명
        level: 검증 결과 수준
        expected: 기대값
        actual: 실제값
        message: 상세 메시지
        details: 추가 세부 정보
    """

    name: str
    description: str
    level: ValidationLevel = ValidationLevel.SKIP
    expected: Optional[Any] = None
    actual: Optional[Any] = None
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "name": self.name,
            "description": self.description,
            "level": self.level.value,
            "expected": self.expected,
            "actual": self.actual,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class ValidationReport:
    """검증 결과 보고서

    Attributes:
        checks: 개별 검증 항목 결과 목록
        overall_level: 전체 검증 수준
        total_checks: 전체 검증 항목 수
        passed_checks: 통과 항목 수
        warning_checks: 경고 항목 수
        failed_checks: 실패 항목 수
        skipped_checks: 건너뛴 항목 수
        validation_time_ms: 검증 소요 시간 (밀리초)
        validated_at: 검증 시간
    """

    checks: List[ValidationCheck] = field(default_factory=list)
    overall_level: ValidationLevel = ValidationLevel.SKIP
    total_checks: int = 0
    passed_checks: int = 0
    warning_checks: int = 0
    failed_checks: int = 0
    skipped_checks: int = 0
    validation_time_ms: float = 0.0
    validated_at: Optional[datetime] = None

    def add_check(self, check: ValidationCheck) -> None:
        """검증 항목 추가 및 카운터 업데이트

        Args:
            check: 추가할 검증 항목
        """
        self.checks.append(check)
        self.total_checks += 1

        if check.level == ValidationLevel.PASS:
            self.passed_checks += 1
        elif check.level == ValidationLevel.WARNING:
            self.warning_checks += 1
        elif check.level == ValidationLevel.FAIL:
            self.failed_checks += 1
        elif check.level == ValidationLevel.SKIP:
            self.skipped_checks += 1

        # 전체 수준 업데이트 (가장 심각한 수준으로)
        if check.level == ValidationLevel.FAIL:
            self.overall_level = ValidationLevel.FAIL
        elif check.level == ValidationLevel.WARNING and self.overall_level != ValidationLevel.FAIL:
            self.overall_level = ValidationLevel.WARNING
        elif check.level == ValidationLevel.PASS and self.overall_level == ValidationLevel.SKIP:
            self.overall_level = ValidationLevel.PASS

    @property
    def is_valid(self) -> bool:
        """검증 통과 여부 (FAIL이 없으면 통과)"""
        return self.overall_level != ValidationLevel.FAIL

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "overall_level": self.overall_level.value,
            "is_valid": self.is_valid,
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "warning_checks": self.warning_checks,
            "failed_checks": self.failed_checks,
            "skipped_checks": self.skipped_checks,
            "validation_time_ms": round(self.validation_time_ms, 2),
            "validated_at": self.validated_at.isoformat() if self.validated_at else None,
            "checks": [c.to_dict() for c in self.checks],
        }

    def summary(self) -> str:
        """결과 요약 문자열"""
        return (
            f"Validation {self.overall_level.value.upper()}: "
            f"total={self.total_checks}, pass={self.passed_checks}, "
            f"warn={self.warning_checks}, fail={self.failed_checks}, "
            f"skip={self.skipped_checks}, time={self.validation_time_ms:.1f}ms"
        )


# ---------------------------------------------------------------------------
# InitialDataValidation
# ---------------------------------------------------------------------------


class InitialDataValidation:
    """초기 데이터 ETL 결과 검증 서비스

    ETL 파이프라인 실행 후 데이터 품질을 검증합니다.

    검증 항목:
        1. document_count: 문서 수 검증
        2. chunk_count: 청크 수 검증
        3. entity_count: 엔티티 수 검증
        4. chunk_ratio: 문서당 청크 비율 검증
        5. empty_chunks: 빈 청크 검증
        6. orphan_nodes: 고아 노드 검증
        7. sample_query: 샘플 쿼리 테스트

    Example:
        from app.services.initial_data_loader import ETLSummary

        validator = InitialDataValidation(
            min_documents=50,
            min_chunks_per_doc=3,
        )
        report = await validator.validate(etl_summary)
        print(report.summary())

    Attributes:
        min_documents: 최소 기대 문서 수
        min_chunks_per_doc: 문서당 최소 기대 청크 수
        max_chunks_per_doc: 문서당 최대 허용 청크 수
        min_entities: 최소 기대 엔티티 수
        max_orphan_rate: 최대 허용 고아 노드 비율
        max_empty_chunk_rate: 최대 허용 빈 청크 비율
        sample_queries: 검증용 샘플 쿼리 목록
    """

    # 기본 샘플 쿼리
    DEFAULT_SAMPLE_QUERIES = [
        "Hybrid RAG 플랫폼의 아키텍처는?",
        "Neo4j 그래프 스키마 설계 방법은?",
        "BGE-M3 임베딩 모델 사용법은?",
    ]

    def __init__(
        self,
        min_documents: int = 10,
        min_chunks_per_doc: float = 2.0,
        max_chunks_per_doc: float = 100.0,
        min_entities: int = 5,
        max_orphan_rate: float = 0.01,
        max_empty_chunk_rate: float = 0.05,
        sample_queries: Optional[List[str]] = None,
    ):
        """InitialDataValidation 초기화

        Args:
            min_documents: 최소 기대 문서 수
            min_chunks_per_doc: 문서당 최소 기대 평균 청크 수
            max_chunks_per_doc: 문서당 최대 허용 평균 청크 수
            min_entities: 최소 기대 엔티티 수
            max_orphan_rate: 최대 허용 고아 노드 비율 (0.0 ~ 1.0)
            max_empty_chunk_rate: 최대 허용 빈 청크 비율 (0.0 ~ 1.0)
            sample_queries: 검증용 샘플 쿼리 목록
        """
        self.min_documents = min_documents
        self.min_chunks_per_doc = min_chunks_per_doc
        self.max_chunks_per_doc = max_chunks_per_doc
        self.min_entities = min_entities
        self.max_orphan_rate = max_orphan_rate
        self.max_empty_chunk_rate = max_empty_chunk_rate
        self.sample_queries = sample_queries or self.DEFAULT_SAMPLE_QUERIES

        logger.info(
            "InitialDataValidation initialized: min_docs=%d, "
            "min_chunks_per_doc=%.1f, min_entities=%d",
            self.min_documents,
            self.min_chunks_per_doc,
            self.min_entities,
        )

    async def validate(self, etl_summary: Any) -> ValidationReport:
        """ETL 결과 전체 검증

        Args:
            etl_summary: ETLSummary 객체

        Returns:
            ValidationReport: 검증 결과 보고서
        """
        start_time = time.monotonic()
        report = ValidationReport(validated_at=datetime.utcnow())

        logger.info("Starting validation of ETL results...")

        # 1. 문서 수 검증
        report.add_check(self._validate_document_count(etl_summary))

        # 2. 청크 수 검증
        report.add_check(self._validate_chunk_count(etl_summary))

        # 3. 엔티티 수 검증
        report.add_check(self._validate_entity_count(etl_summary))

        # 4. 문서당 청크 비율 검증
        report.add_check(self._validate_chunk_ratio(etl_summary))

        # 5. 실패율 검증
        report.add_check(self._validate_failure_rate(etl_summary))

        # 6. 처리 시간 검증
        report.add_check(self._validate_processing_time(etl_summary))

        # 7. 빈 청크 검증
        report.add_check(self._validate_empty_chunks(etl_summary))

        # 8. 샘플 쿼리 테스트
        sample_check = await self._validate_sample_queries()
        report.add_check(sample_check)

        # 9. 고아 노드 검증
        orphan_check = await self._validate_orphan_nodes()
        report.add_check(orphan_check)

        report.validation_time_ms = (time.monotonic() - start_time) * 1000

        logger.info(report.summary())

        return report

    # ------------------------------------------------------------------
    # Individual Validation Checks
    # ------------------------------------------------------------------

    def _validate_document_count(self, etl_summary: Any) -> ValidationCheck:
        """문서 수 검증

        Args:
            etl_summary: ETL 실행 요약

        Returns:
            ValidationCheck 결과
        """
        check = ValidationCheck(
            name="document_count",
            description="처리된 문서 수가 최소 기대치를 충족하는지 검증",
            expected=f">= {self.min_documents}",
            actual=etl_summary.success_count,
        )

        if etl_summary.success_count >= self.min_documents:
            check.level = ValidationLevel.PASS
            check.message = (
                f"문서 수 검증 통과: {etl_summary.success_count}개 "
                f"(최소 {self.min_documents}개)"
            )
        elif etl_summary.success_count >= self.min_documents * 0.5:
            check.level = ValidationLevel.WARNING
            check.message = (
                f"문서 수 부족 (경고): {etl_summary.success_count}개 "
                f"(최소 {self.min_documents}개, 50% 이상은 처리됨)"
            )
        else:
            check.level = ValidationLevel.FAIL
            check.message = (
                f"문서 수 검증 실패: {etl_summary.success_count}개 "
                f"(최소 {self.min_documents}개 필요)"
            )

        return check

    def _validate_chunk_count(self, etl_summary: Any) -> ValidationCheck:
        """청크 수 검증

        Args:
            etl_summary: ETL 실행 요약

        Returns:
            ValidationCheck 결과
        """
        expected_min = int(etl_summary.success_count * self.min_chunks_per_doc)

        check = ValidationCheck(
            name="chunk_count",
            description="생성된 청크 수가 기대 범위 내인지 검증",
            expected=f">= {expected_min}",
            actual=etl_summary.total_chunks,
        )

        if etl_summary.total_chunks >= expected_min:
            check.level = ValidationLevel.PASS
            check.message = (
                f"청크 수 검증 통과: {etl_summary.total_chunks}개 "
                f"(최소 {expected_min}개)"
            )
        elif etl_summary.total_chunks > 0:
            check.level = ValidationLevel.WARNING
            check.message = (
                f"청크 수 부족 (경고): {etl_summary.total_chunks}개 "
                f"(최소 {expected_min}개)"
            )
        else:
            check.level = ValidationLevel.FAIL
            check.message = "청크가 생성되지 않았습니다"

        return check

    def _validate_entity_count(self, etl_summary: Any) -> ValidationCheck:
        """엔티티 수 검증

        Args:
            etl_summary: ETL 실행 요약

        Returns:
            ValidationCheck 결과
        """
        check = ValidationCheck(
            name="entity_count",
            description="추출된 엔티티 수가 최소 기대치를 충족하는지 검증",
            expected=f">= {self.min_entities}",
            actual=etl_summary.total_entities,
        )

        if etl_summary.total_entities >= self.min_entities:
            check.level = ValidationLevel.PASS
            check.message = (
                f"엔티티 수 검증 통과: {etl_summary.total_entities}개 "
                f"(최소 {self.min_entities}개)"
            )
        elif etl_summary.total_entities > 0:
            check.level = ValidationLevel.WARNING
            check.message = (
                f"엔티티 수 부족 (경고): {etl_summary.total_entities}개 "
                f"(최소 {self.min_entities}개)"
            )
        else:
            # 엔티티 추출이 비활성화된 경우도 있으므로 경고만
            check.level = ValidationLevel.WARNING
            check.message = "엔티티가 추출되지 않았습니다 (엔티티 추출 비활성화 가능)"

        return check

    def _validate_chunk_ratio(self, etl_summary: Any) -> ValidationCheck:
        """문서당 청크 비율 검증

        Args:
            etl_summary: ETL 실행 요약

        Returns:
            ValidationCheck 결과
        """
        check = ValidationCheck(
            name="chunk_ratio",
            description="문서당 평균 청크 수가 합리적 범위 내인지 검증",
            expected=f"{self.min_chunks_per_doc:.1f} ~ {self.max_chunks_per_doc:.1f}",
        )

        if etl_summary.success_count == 0:
            check.level = ValidationLevel.SKIP
            check.actual = 0
            check.message = "성공한 문서가 없어 비율 계산 불가"
            return check

        avg_chunks = etl_summary.total_chunks / etl_summary.success_count
        check.actual = round(avg_chunks, 2)

        if self.min_chunks_per_doc <= avg_chunks <= self.max_chunks_per_doc:
            check.level = ValidationLevel.PASS
            check.message = (
                f"문서당 평균 청크 수 적정: {avg_chunks:.1f}개 "
                f"(범위: {self.min_chunks_per_doc:.1f} ~ {self.max_chunks_per_doc:.1f})"
            )
        elif avg_chunks < self.min_chunks_per_doc:
            check.level = ValidationLevel.WARNING
            check.message = (
                f"문서당 평균 청크 수 부족: {avg_chunks:.1f}개 "
                f"(최소 {self.min_chunks_per_doc:.1f}개)"
            )
        else:
            check.level = ValidationLevel.WARNING
            check.message = (
                f"문서당 평균 청크 수 과다: {avg_chunks:.1f}개 "
                f"(최대 {self.max_chunks_per_doc:.1f}개)"
            )

        return check

    def _validate_failure_rate(self, etl_summary: Any) -> ValidationCheck:
        """실패율 검증

        Args:
            etl_summary: ETL 실행 요약

        Returns:
            ValidationCheck 결과
        """
        check = ValidationCheck(
            name="failure_rate",
            description="ETL 실패율이 허용 범위 내인지 검증",
            expected="< 10%",
        )

        if etl_summary.total_files == 0:
            check.level = ValidationLevel.SKIP
            check.actual = "N/A"
            check.message = "처리할 파일이 없었습니다"
            return check

        failure_rate = etl_summary.failed_count / etl_summary.total_files
        check.actual = f"{failure_rate * 100:.1f}%"

        if failure_rate == 0:
            check.level = ValidationLevel.PASS
            check.message = "실패 없이 모든 파일 처리 완료"
        elif failure_rate < 0.1:
            check.level = ValidationLevel.PASS
            check.message = (
                f"실패율 허용 범위: {failure_rate * 100:.1f}% "
                f"({etl_summary.failed_count}개 실패)"
            )
        elif failure_rate < 0.3:
            check.level = ValidationLevel.WARNING
            check.message = (
                f"실패율 경고: {failure_rate * 100:.1f}% "
                f"({etl_summary.failed_count}개 실패)"
            )
        else:
            check.level = ValidationLevel.FAIL
            check.message = (
                f"실패율 초과: {failure_rate * 100:.1f}% "
                f"({etl_summary.failed_count}개 실패)"
            )

        # 실패한 파일 목록 추가
        failed_files = [
            r.file_name
            for r in etl_summary.results
            if hasattr(r, "status") and str(r.status) == "failed"
        ]
        if failed_files:
            check.details["failed_files"] = failed_files[:20]  # 최대 20개

        return check

    def _validate_processing_time(self, etl_summary: Any) -> ValidationCheck:
        """처리 시간 검증

        Args:
            etl_summary: ETL 실행 요약

        Returns:
            ValidationCheck 결과
        """
        check = ValidationCheck(
            name="processing_time",
            description="전체 처리 시간이 합리적 범위 내인지 검증",
        )

        total_time_s = etl_summary.total_time_ms / 1000
        check.actual = f"{total_time_s:.1f}s"

        if etl_summary.total_files == 0:
            check.level = ValidationLevel.SKIP
            check.message = "처리할 파일이 없었습니다"
            return check

        avg_time_s = total_time_s / etl_summary.total_files
        check.expected = f"< 60s per file"

        if avg_time_s < 60:
            check.level = ValidationLevel.PASS
            check.message = (
                f"처리 속도 양호: 파일당 평균 {avg_time_s:.1f}초 "
                f"(총 {total_time_s:.1f}초)"
            )
        elif avg_time_s < 120:
            check.level = ValidationLevel.WARNING
            check.message = (
                f"처리 속도 느림 (경고): 파일당 평균 {avg_time_s:.1f}초 "
                f"(총 {total_time_s:.1f}초)"
            )
        else:
            check.level = ValidationLevel.WARNING
            check.message = (
                f"처리 속도 매우 느림: 파일당 평균 {avg_time_s:.1f}초 "
                f"(총 {total_time_s:.1f}초)"
            )

        check.details["avg_time_per_file_s"] = round(avg_time_s, 2)
        check.details["total_time_s"] = round(total_time_s, 2)

        return check

    def _validate_empty_chunks(self, etl_summary: Any) -> ValidationCheck:
        """빈 청크 검증

        ETL 결과에서 빈 청크가 없는지 확인합니다.

        Args:
            etl_summary: ETL 실행 요약

        Returns:
            ValidationCheck 결과
        """
        check = ValidationCheck(
            name="empty_chunks",
            description="빈 청크가 허용 비율 이내인지 검증",
            expected=f"< {self.max_empty_chunk_rate * 100:.0f}%",
        )

        # ETL summary에서는 개별 청크에 접근하기 어려우므로
        # 청크 수가 0인 성공 문서를 확인
        zero_chunk_docs = [
            r.file_name
            for r in etl_summary.results
            if hasattr(r, "status")
            and str(r.status) == "success"
            and hasattr(r, "chunk_count")
            and r.chunk_count == 0
        ]

        if etl_summary.success_count == 0:
            check.level = ValidationLevel.SKIP
            check.actual = "N/A"
            check.message = "성공한 문서가 없어 검증 불가"
            return check

        empty_rate = len(zero_chunk_docs) / etl_summary.success_count
        check.actual = f"{empty_rate * 100:.1f}%"

        if empty_rate == 0:
            check.level = ValidationLevel.PASS
            check.message = "빈 청크 문서 없음"
        elif empty_rate <= self.max_empty_chunk_rate:
            check.level = ValidationLevel.WARNING
            check.message = (
                f"빈 청크 문서 존재 (허용 범위): {len(zero_chunk_docs)}개 "
                f"({empty_rate * 100:.1f}%)"
            )
        else:
            check.level = ValidationLevel.FAIL
            check.message = (
                f"빈 청크 문서 과다: {len(zero_chunk_docs)}개 "
                f"({empty_rate * 100:.1f}%)"
            )
            check.details["zero_chunk_documents"] = zero_chunk_docs[:10]

        return check

    async def _validate_sample_queries(self) -> ValidationCheck:
        """샘플 쿼리 테스트

        Elasticsearch에 샘플 쿼리를 실행하여 관련 문서가 검색되는지 확인합니다.

        Returns:
            ValidationCheck 결과
        """
        check = ValidationCheck(
            name="sample_queries",
            description="샘플 쿼리로 관련 문서 검색이 동작하는지 검증",
            expected=f"{len(self.sample_queries)}개 쿼리 중 1개 이상 결과 반환",
        )

        try:
            from elasticsearch import AsyncElasticsearch

            es = AsyncElasticsearch(settings.elasticsearch_url)

            try:
                successful_queries = 0
                query_results = {}

                for query in self.sample_queries:
                    try:
                        result = await es.search(
                            index=settings.elasticsearch_index,
                            body={
                                "query": {
                                    "match": {
                                        "content": {
                                            "query": query,
                                            "minimum_should_match": "30%",
                                        }
                                    }
                                },
                                "size": 3,
                            },
                        )

                        hits = result.get("hits", {}).get("total", {}).get("value", 0)
                        query_results[query] = hits

                        if hits > 0:
                            successful_queries += 1

                    except Exception as e:
                        query_results[query] = f"Error: {str(e)}"

                check.actual = f"{successful_queries}/{len(self.sample_queries)} queries returned results"
                check.details["query_results"] = query_results

                if successful_queries == len(self.sample_queries):
                    check.level = ValidationLevel.PASS
                    check.message = f"모든 샘플 쿼리({successful_queries}개)에서 결과 반환"
                elif successful_queries > 0:
                    check.level = ValidationLevel.WARNING
                    check.message = (
                        f"일부 샘플 쿼리에서만 결과 반환: "
                        f"{successful_queries}/{len(self.sample_queries)}"
                    )
                else:
                    check.level = ValidationLevel.FAIL
                    check.message = "모든 샘플 쿼리에서 결과 없음"

            finally:
                await es.close()

        except ImportError:
            check.level = ValidationLevel.SKIP
            check.actual = "N/A"
            check.message = "elasticsearch 패키지가 설치되지 않아 건너뜀"

        except Exception as e:
            check.level = ValidationLevel.SKIP
            check.actual = "N/A"
            check.message = f"Elasticsearch 연결 불가 - 건너뜀: {str(e)}"

        return check

    async def _validate_orphan_nodes(self) -> ValidationCheck:
        """고아 노드 검증

        Neo4j에서 연결이 없는 고아 노드 비율을 확인합니다.

        Returns:
            ValidationCheck 결과
        """
        check = ValidationCheck(
            name="orphan_nodes",
            description="Neo4j 고아 노드 비율이 허용 범위 내인지 검증",
            expected=f"< {self.max_orphan_rate * 100:.0f}%",
        )

        try:
            from neo4j import AsyncGraphDatabase

            driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password or ""),
            )

            try:
                async with driver.session() as session:
                    # 전체 노드 수
                    total_result = await session.run(
                        "MATCH (n) RETURN count(n) AS total"
                    )
                    total_record = await total_result.single()
                    total_nodes = total_record["total"] if total_record else 0

                    if total_nodes == 0:
                        check.level = ValidationLevel.SKIP
                        check.actual = "N/A"
                        check.message = "Neo4j에 노드가 없습니다"
                        return check

                    # 고아 노드 수 (관계가 없는 노드)
                    orphan_result = await session.run(
                        "MATCH (n) WHERE NOT (n)--() RETURN count(n) AS orphans"
                    )
                    orphan_record = await orphan_result.single()
                    orphan_count = orphan_record["orphans"] if orphan_record else 0

                    orphan_rate = orphan_count / total_nodes
                    check.actual = f"{orphan_rate * 100:.2f}% ({orphan_count}/{total_nodes})"
                    check.details["total_nodes"] = total_nodes
                    check.details["orphan_count"] = orphan_count

                    if orphan_rate <= self.max_orphan_rate:
                        check.level = ValidationLevel.PASS
                        check.message = (
                            f"고아 노드 비율 양호: {orphan_rate * 100:.2f}% "
                            f"(허용: {self.max_orphan_rate * 100:.0f}%)"
                        )
                    elif orphan_rate <= self.max_orphan_rate * 5:
                        check.level = ValidationLevel.WARNING
                        check.message = (
                            f"고아 노드 비율 경고: {orphan_rate * 100:.2f}% "
                            f"(허용: {self.max_orphan_rate * 100:.0f}%)"
                        )
                    else:
                        check.level = ValidationLevel.FAIL
                        check.message = (
                            f"고아 노드 비율 초과: {orphan_rate * 100:.2f}% "
                            f"(허용: {self.max_orphan_rate * 100:.0f}%)"
                        )

            finally:
                await driver.close()

        except ImportError:
            check.level = ValidationLevel.SKIP
            check.actual = "N/A"
            check.message = "neo4j 패키지가 설치되지 않아 건너뜀"

        except Exception as e:
            check.level = ValidationLevel.SKIP
            check.actual = "N/A"
            check.message = f"Neo4j 연결 불가 - 건너뜀: {str(e)}"

        return check

    def validate_sync(self, etl_summary: Any) -> ValidationReport:
        """동기 검증 (비동기 환경이 아닌 경우)

        외부 서비스 연결 검증(샘플 쿼리, 고아 노드)을 건너뛰고
        ETL 통계 기반 검증만 수행합니다.

        Args:
            etl_summary: ETLSummary 객체

        Returns:
            ValidationReport: 검증 결과 보고서
        """
        start_time = time.monotonic()
        report = ValidationReport(validated_at=datetime.utcnow())

        report.add_check(self._validate_document_count(etl_summary))
        report.add_check(self._validate_chunk_count(etl_summary))
        report.add_check(self._validate_entity_count(etl_summary))
        report.add_check(self._validate_chunk_ratio(etl_summary))
        report.add_check(self._validate_failure_rate(etl_summary))
        report.add_check(self._validate_processing_time(etl_summary))
        report.add_check(self._validate_empty_chunks(etl_summary))

        # 샘플 쿼리 및 고아 노드는 SKIP
        skip_query = ValidationCheck(
            name="sample_queries",
            description="샘플 쿼리 검증 (동기 모드에서 건너뜀)",
            level=ValidationLevel.SKIP,
            message="동기 모드에서 건너뜀 (async validate() 사용 권장)",
        )
        report.add_check(skip_query)

        skip_orphan = ValidationCheck(
            name="orphan_nodes",
            description="고아 노드 검증 (동기 모드에서 건너뜀)",
            level=ValidationLevel.SKIP,
            message="동기 모드에서 건너뜀 (async validate() 사용 권장)",
        )
        report.add_check(skip_orphan)

        report.validation_time_ms = (time.monotonic() - start_time) * 1000

        logger.info(report.summary())

        return report


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------

_data_validator: Optional[InitialDataValidation] = None


def get_data_validator(**kwargs: Any) -> InitialDataValidation:
    """InitialDataValidation 싱글톤 팩토리

    Args:
        **kwargs: InitialDataValidation 생성자 인자

    Returns:
        InitialDataValidation 인스턴스 (싱글톤)
    """
    global _data_validator
    if _data_validator is None:
        _data_validator = InitialDataValidation(**kwargs)
    return _data_validator


def reset_data_validator() -> None:
    """싱글톤 인스턴스 초기화 (테스트용)"""
    global _data_validator
    _data_validator = None
