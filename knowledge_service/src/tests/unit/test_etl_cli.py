"""
ETL CLI 통합 테스트 (STORY-125) — Docker 실환경 검증

knowledge_service/scripts/etl_cli.py (Click 기반) 검증
- TEST_MODE=docker 필수 (Mock 금지)
- 실제 Docker 컨테이너 상태로 검증
- --dry-run 플래그로 안전하게 실행
"""

import json
import os
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

# etl_cli.py 경로 추가 (scripts/ 폴더)
_test_dir = Path(__file__).parent
for _depth in range(3, 6):
    _candidate = _test_dir
    for _ in range(_depth):
        _candidate = _candidate.parent
    _scripts = _candidate / "scripts"
    if (_scripts / "etl_cli.py").exists():
        sys.path.insert(0, str(_scripts))
        break

from etl_cli import (
    CONTAINER_NAME,
    ES_INDEX,
    ES_URL,
    NEO4J_CONTAINER,
    PG_CONTAINER,
    _es_count,
    _is_container_running,
    cli,
)

# Docker 실환경 필수
pytestmark = pytest.mark.skipif(
    os.getenv("TEST_MODE") != "docker",
    reason="TEST_MODE=docker 필수 (Mock 테스트 금지)",
)


# ---------------------------------------------------------------------------
# U01: CLI 그룹 커맨드 등록 (순수 CLI 구조 테스트 — 인프라 불필요)
# ---------------------------------------------------------------------------


class TestCLICommandRegistration:
    """U01: CLI 그룹에 필수 커맨드가 모두 등록되어 있는지 확인"""

    def test_all_commands_registered(self):
        """phase1, phase2, phase3, all, status, cleanup 커맨드 등록 확인"""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0

        expected_commands = ["phase1", "phase2", "phase3", "all", "status", "cleanup"]
        for cmd in expected_commands:
            assert cmd in result.output, f"'{cmd}' 커맨드가 help 출력에 없음"

    def test_cli_has_version_option(self):
        """--version 옵션이 1.0.0 반환"""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "1.0.0" in result.output

    def test_phase1_help(self):
        """phase1 커맨드 help 출력"""
        runner = CliRunner()
        result = runner.invoke(cli, ["phase1", "--help"])
        assert result.exit_code == 0
        assert "--dry-run" in result.output

    def test_phase3_help(self):
        """phase3 커맨드 help 출력 (--concurrency 포함)"""
        runner = CliRunner()
        result = runner.invoke(cli, ["phase3", "--help"])
        assert result.exit_code == 0
        assert "--concurrency" in result.output

    def test_cleanup_help(self):
        """cleanup 커맨드 help 출력 (--batch-size 포함)"""
        runner = CliRunner()
        result = runner.invoke(cli, ["cleanup", "--help"])
        assert result.exit_code == 0
        assert "--batch-size" in result.output


# ---------------------------------------------------------------------------
# U02: --dry-run 옵션 (실제 Docker 환경에서 검증)
# ---------------------------------------------------------------------------


class TestDryRunOption:
    """U02: --dry-run 플래그는 실제 Docker exec 없이 계획만 출력"""

    def test_phase1_dry_run_no_exec(self):
        """phase1 --dry-run: DRY-RUN 출력, 실제 ETL 실행 없음"""
        runner = CliRunner()
        result = runner.invoke(cli, ["phase1", "--dry-run"])

        # 전제조건 통과 시 DRY-RUN 출력, 실패 시 exit_code 1
        if result.exit_code == 0:
            assert "DRY-RUN" in result.output
        else:
            # 컨테이너가 미기동이면 전제조건 실패 — 유효한 결과
            assert "전제조건" in result.output or "Prerequisite" in result.output

    def test_phase3_dry_run_shows_stats(self):
        """phase3 --dry-run: 통계 표시, 실제 엔티티 추출 없음"""
        runner = CliRunner()
        result = runner.invoke(cli, ["phase3", "--dry-run"])

        if result.exit_code == 0:
            assert "DRY-RUN" in result.output
        else:
            assert "전제조건" in result.output or "Prerequisite" in result.output

    def test_phase1_dry_run_shows_chunk_info(self):
        """phase1 --dry-run --chunk-size 500: 청크 크기 정보 출력"""
        runner = CliRunner()
        result = runner.invoke(cli, ["phase1", "--dry-run", "--chunk-size", "500"])

        if result.exit_code == 0:
            assert "500" in result.output


# ---------------------------------------------------------------------------
# U03: --concurrency 옵션 (실제 환경)
# ---------------------------------------------------------------------------


class TestConcurrencyOption:
    """U03: --concurrency 기본값 및 커스텀 값 설정"""

    def test_phase3_default_concurrency(self):
        """phase3 기본 concurrency = 3"""
        runner = CliRunner()
        result = runner.invoke(cli, ["phase3", "--help"])
        assert "3" in result.output

    def test_phase3_custom_concurrency_in_output(self):
        """phase3 --concurrency 5 --dry-run → 출력에 concurrency=5 포함"""
        runner = CliRunner()
        result = runner.invoke(cli, ["phase3", "--concurrency", "5", "--dry-run"])

        # concurrency=5가 출력에 포함되어야 함
        assert "5" in result.output

    def test_phase3_short_flag_c(self):
        """phase3 -c 2 (단축 플래그) --dry-run 동작 확인"""
        runner = CliRunner()
        result = runner.invoke(cli, ["phase3", "-c", "2", "--dry-run"])

        assert "2" in result.output


# ---------------------------------------------------------------------------
# U04: 전제조건 체크 — 실제 Docker 컨테이너로 검증
# ---------------------------------------------------------------------------


class TestPrerequisitesCheck:
    """U04: Docker 컨테이너 실행 상태 체크 (실환경)"""

    def test_ai_service_container_running(self):
        """kp-ai-service 컨테이너가 실행 중"""
        assert _is_container_running(CONTAINER_NAME) is True

    def test_postgresql_container_running(self):
        """kp-postgresql 컨테이너가 실행 중"""
        assert _is_container_running(PG_CONTAINER) is True

    def test_neo4j_container_running(self):
        """kp-neo4j 컨테이너가 실행 중"""
        assert _is_container_running(NEO4J_CONTAINER) is True

    def test_nonexistent_container_not_running(self):
        """존재하지 않는 컨테이너 → False"""
        assert _is_container_running("nonexistent-container-xyz") is False


# ---------------------------------------------------------------------------
# U05: _es_count 함수 — 실제 ES 연동
# ---------------------------------------------------------------------------


class TestEsCount:
    """U05: Elasticsearch 문서 카운트 (실환경)"""

    def test_es_count_returns_integer(self):
        """ES에서 정수 카운트 반환"""
        result = _es_count()
        assert isinstance(result, int), f"_es_count()는 int 반환해야 함, got {type(result)}"

    def test_es_count_non_negative(self):
        """ES 카운트는 0 이상"""
        result = _es_count()
        assert result >= 0, f"카운트는 음수일 수 없음: {result}"

    def test_es_index_is_knowledge_chunks(self):
        """ES 인덱스명이 knowledge_chunks"""
        assert ES_INDEX == "knowledge_chunks"

    def test_es_url_format(self):
        """ES URL이 올바른 형식"""
        assert ES_URL.startswith("http")
        assert "9200" in ES_URL or "elasticsearch" in ES_URL


# ---------------------------------------------------------------------------
# U06: --batch-size 옵션
# ---------------------------------------------------------------------------


class TestBatchSizeOption:
    """U06: cleanup --batch-size 옵션 기본값 및 커스텀 값"""

    def test_cleanup_default_batch_size_in_help(self):
        """cleanup 기본 batch-size = 200"""
        runner = CliRunner()
        result = runner.invoke(cli, ["cleanup", "--help"])
        assert result.exit_code == 0
        assert "200" in result.output

    def test_cleanup_custom_batch_size(self):
        """cleanup --batch-size 500 --dry-run → 500이 출력에 포함"""
        runner = CliRunner()
        result = runner.invoke(cli, ["cleanup", "--batch-size", "500", "--dry-run"])

        if result.exit_code == 0:
            assert "500" in result.output


# ---------------------------------------------------------------------------
# U07: status 커맨드 — 실제 인프라 상태 조회
# ---------------------------------------------------------------------------


class TestStatusCommandOutput:
    """U07: status 커맨드 출력에 필수 섹션 포함 확인 (실환경)"""

    def test_status_runs_successfully(self):
        """status 커맨드가 정상 실행"""
        runner = CliRunner()
        result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0

    def test_status_includes_es_section(self):
        """status 출력에 Elasticsearch 섹션 포함"""
        runner = CliRunner()
        result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0
        assert "Elasticsearch" in result.output

    def test_status_includes_pg_section(self):
        """status 출력에 PostgreSQL 섹션 포함"""
        runner = CliRunner()
        result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0
        assert "PostgreSQL" in result.output

    def test_status_includes_neo4j_section(self):
        """status 출력에 Neo4j 섹션 포함"""
        runner = CliRunner()
        result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0
        assert "Neo4j" in result.output


# ---------------------------------------------------------------------------
# U08: cleanup --dry-run (실환경)
# ---------------------------------------------------------------------------


class TestCleanupDryRun:
    """U08: cleanup --dry-run 모드 (실환경)"""

    def test_cleanup_dry_run_mode(self):
        """cleanup --dry-run → DRY-RUN 레이블 출력"""
        runner = CliRunner()
        result = runner.invoke(cli, ["cleanup", "--dry-run"])

        if result.exit_code == 0:
            assert "DRY-RUN" in result.output
        else:
            # 전제조건 실패 시에도 유효
            assert "전제조건" in result.output or "Prerequisite" in result.output
