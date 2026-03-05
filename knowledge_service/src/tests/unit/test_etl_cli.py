"""
ETL CLI 단위 테스트 (STORY-125)

knowledge_service/scripts/etl_cli.py (Click 기반) 검증
- CLI 그룹 커맨드 등록 확인
- --dry-run 옵션 동작
- --concurrency 옵션
- 전제조건 체크 (_is_container_running)
- _es_count 함수
- --batch-size 옵션
- status 커맨드 출력 형식
- cleanup --dry-run
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

# etl_cli.py 경로 추가 (scripts/ 폴더)
scripts_dir = Path(__file__).parent.parent.parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

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


# ---------------------------------------------------------------------------
# U01: CLI 그룹 커맨드 등록
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
# U02: --dry-run 옵션 (실행 없이 계획 출력)
# ---------------------------------------------------------------------------


class TestDryRunOption:
    """U02: --dry-run 플래그는 실제 Docker exec 없이 계획만 출력"""

    def _make_successful_prereq(self, mock_run):
        """전제조건 체크를 통과시키는 mock 설정"""
        def run_side_effect(cmd, **kwargs):
            result = MagicMock()
            if "inspect" in cmd:
                result.returncode = 0
                result.stdout = "true\n"
            elif "urlopen" in str(cmd):
                result.returncode = 0
                result.stdout = ""
            else:
                result.returncode = 0
                result.stdout = "5\n"
            return result
        mock_run.side_effect = run_side_effect

    @patch("etl_cli._is_container_running", return_value=True)
    @patch("etl_cli._es_count", return_value=100)
    @patch("etl_cli._pg_query", return_value="1")
    @patch("etl_cli._neo4j_query", return_value="1")
    @patch("subprocess.run")
    def test_phase1_dry_run_no_exec(
        self, mock_run, mock_neo4j, mock_pg, mock_es, mock_container
    ):
        """phase1 --dry-run: DRY-RUN 출력, 실제 ETL 실행 없음"""
        # 파일 카운트용 docker exec 결과
        dry_run_result = MagicMock()
        dry_run_result.returncode = 0
        dry_run_result.stdout = "42\n"
        mock_run.return_value = dry_run_result

        runner = CliRunner()
        result = runner.invoke(cli, ["phase1", "--dry-run"])

        assert result.exit_code == 0
        assert "DRY-RUN" in result.output

    @patch("etl_cli._is_container_running", return_value=True)
    @patch("etl_cli._es_count", return_value=100)
    @patch("etl_cli._pg_query", return_value="1")
    @patch("etl_cli._neo4j_query", return_value="1")
    @patch("subprocess.run")
    def test_phase3_dry_run_shows_stats(
        self, mock_run, mock_neo4j, mock_pg, mock_es, mock_container
    ):
        """phase3 --dry-run: 통계 표시, 실제 엔티티 추출 없음"""
        runner = CliRunner()
        result = runner.invoke(cli, ["phase3", "--dry-run"])

        assert result.exit_code == 0
        assert "DRY-RUN" in result.output

    @patch("etl_cli._is_container_running", return_value=True)
    @patch("etl_cli._es_count", return_value=50)
    @patch("etl_cli._pg_query", return_value="1")
    @patch("etl_cli._neo4j_query", return_value="1")
    @patch("subprocess.run")
    def test_phase1_dry_run_shows_chunk_info(
        self, mock_run, mock_neo4j, mock_pg, mock_es, mock_container
    ):
        """phase1 --dry-run: 청크 크기, 오버랩 정보 출력"""
        dry_run_result = MagicMock()
        dry_run_result.returncode = 0
        dry_run_result.stdout = "10\n"
        mock_run.return_value = dry_run_result

        runner = CliRunner()
        result = runner.invoke(cli, ["phase1", "--dry-run", "--chunk-size", "500"])

        assert result.exit_code == 0
        assert "500" in result.output


# ---------------------------------------------------------------------------
# U03: --concurrency 옵션
# ---------------------------------------------------------------------------


class TestConcurrencyOption:
    """U03: --concurrency 기본값 및 커스텀 값 설정"""

    def test_phase3_default_concurrency(self):
        """phase3 기본 concurrency = 3"""
        runner = CliRunner()
        result = runner.invoke(cli, ["phase3", "--help"])
        assert "3" in result.output  # 기본값 3이 help에 표시됨

    @patch("etl_cli._is_container_running", return_value=True)
    @patch("etl_cli._es_count", return_value=100)
    @patch("etl_cli._pg_query", return_value="1")
    @patch("etl_cli._neo4j_query", return_value="5")
    def test_phase3_custom_concurrency_in_output(
        self, mock_neo4j, mock_pg, mock_es, mock_container
    ):
        """phase3 --concurrency 5 → 출력에 concurrency=5 포함"""
        runner = CliRunner()
        result = runner.invoke(cli, ["phase3", "--concurrency", "5", "--dry-run"])

        assert result.exit_code == 0
        assert "5" in result.output

    @patch("etl_cli._is_container_running", return_value=True)
    @patch("etl_cli._es_count", return_value=100)
    @patch("etl_cli._pg_query", return_value="1")
    @patch("etl_cli._neo4j_query", return_value="5")
    def test_phase3_short_flag_c(
        self, mock_neo4j, mock_pg, mock_es, mock_container
    ):
        """phase3 -c 2 (단축 플래그) 동작 확인"""
        runner = CliRunner()
        result = runner.invoke(cli, ["phase3", "-c", "2", "--dry-run"])

        assert result.exit_code == 0
        assert "2" in result.output


# ---------------------------------------------------------------------------
# U04: 전제조건 체크 (_is_container_running)
# ---------------------------------------------------------------------------


class TestPrerequisitesCheck:
    """U04: Docker 컨테이너 실행 상태 체크"""

    @patch("subprocess.run")
    def test_is_container_running_true(self, mock_run):
        """컨테이너가 실행 중이면 True 반환"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "true\n"
        mock_run.return_value = mock_result

        assert _is_container_running(CONTAINER_NAME) is True

    @patch("subprocess.run")
    def test_is_container_running_false(self, mock_run):
        """컨테이너가 중지 상태이면 False 반환"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "false\n"
        mock_run.return_value = mock_result

        assert _is_container_running(CONTAINER_NAME) is False

    @patch("subprocess.run")
    def test_is_container_not_found(self, mock_run):
        """컨테이너가 없으면 (returncode != 0) False 반환"""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        assert _is_container_running("nonexistent-container") is False

    @patch("etl_cli._is_container_running", return_value=False)
    @patch("etl_cli._es_count", return_value=None)
    def test_phase1_fails_when_container_not_running(
        self, mock_es, mock_container
    ):
        """컨테이너 미실행 → phase1 전제조건 실패 → exit code 1"""
        runner = CliRunner()
        result = runner.invoke(cli, ["phase1"])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# U05: _es_count 함수
# ---------------------------------------------------------------------------


class TestEsCount:
    """U05: Elasticsearch 문서 카운트 함수"""

    def test_es_count_returns_count(self):
        """ES 응답 정상 → 정수 count 반환"""
        mock_response_data = json.dumps({"count": 1234}).encode()

        mock_resp = MagicMock()
        mock_resp.read.return_value = mock_response_data
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = _es_count()

        assert result == 1234

    def test_es_count_returns_zero_when_empty(self):
        """ES 응답에 count=0 → 0 반환"""
        mock_response_data = json.dumps({"count": 0}).encode()

        mock_resp = MagicMock()
        mock_resp.read.return_value = mock_response_data
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = _es_count()

        assert result == 0

    def test_es_count_returns_none_on_error(self):
        """ES 연결 실패 → None 반환"""
        with patch("urllib.request.urlopen", side_effect=Exception("connection refused")):
            result = _es_count()

        assert result is None

    def test_es_count_uses_correct_index(self):
        """_es_count 호출 시 knowledge_chunks 인덱스 URL 사용"""
        mock_response_data = json.dumps({"count": 42}).encode()

        mock_resp = MagicMock()
        mock_resp.read.return_value = mock_response_data
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        captured_url = []

        def capture_urlopen(req, timeout=None):
            captured_url.append(req.full_url if hasattr(req, "full_url") else str(req))
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=capture_urlopen):
            _es_count()

        assert len(captured_url) == 1
        assert ES_INDEX in captured_url[0]


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

    @patch("etl_cli._is_container_running", return_value=True)
    @patch("etl_cli._es_count", return_value=100)
    @patch("etl_cli._pg_query", return_value="1")
    @patch("etl_cli._neo4j_query", return_value="1")
    @patch("subprocess.run")
    def test_cleanup_custom_batch_size_passed_to_cmd(
        self, mock_run, mock_neo4j, mock_pg, mock_es, mock_container
    ):
        """cleanup --batch-size 500 → 커맨드에 500 전달"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        runner = CliRunner()
        result = runner.invoke(cli, ["cleanup", "--batch-size", "500", "--dry-run"])

        assert result.exit_code == 0

        # subprocess.run 호출 확인
        assert mock_run.called
        # 전달된 커맨드에 500이 포함되어 있어야 함
        call_args = mock_run.call_args
        cmd_str = str(call_args)
        assert "500" in cmd_str


# ---------------------------------------------------------------------------
# U07: status 커맨드 출력 형식
# ---------------------------------------------------------------------------


class TestStatusCommandOutput:
    """U07: status 커맨드 출력에 필수 섹션 포함 확인"""

    @patch("etl_cli._es_count", return_value=500)
    @patch("etl_cli._es_embedding_count", return_value=300)
    @patch("etl_cli._pg_query", return_value="10")
    @patch("etl_cli._neo4j_query", return_value="50")
    @patch("subprocess.run")
    def test_status_includes_es_section(
        self, mock_run, mock_neo4j, mock_pg, mock_embed, mock_es
    ):
        """status 출력에 Elasticsearch 섹션 포함"""
        mock_result = MagicMock()
        mock_result.returncode = 1  # progress file not found
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        runner = CliRunner()
        result = runner.invoke(cli, ["status"])

        assert result.exit_code == 0
        assert "Elasticsearch" in result.output

    @patch("etl_cli._es_count", return_value=500)
    @patch("etl_cli._es_embedding_count", return_value=300)
    @patch("etl_cli._pg_query", return_value="10")
    @patch("etl_cli._neo4j_query", return_value="50")
    @patch("subprocess.run")
    def test_status_includes_pg_section(
        self, mock_run, mock_neo4j, mock_pg, mock_embed, mock_es
    ):
        """status 출력에 PostgreSQL 섹션 포함"""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        runner = CliRunner()
        result = runner.invoke(cli, ["status"])

        assert result.exit_code == 0
        assert "PostgreSQL" in result.output

    @patch("etl_cli._es_count", return_value=500)
    @patch("etl_cli._es_embedding_count", return_value=300)
    @patch("etl_cli._pg_query", return_value="10")
    @patch("etl_cli._neo4j_query", return_value="50")
    @patch("subprocess.run")
    def test_status_includes_neo4j_section(
        self, mock_run, mock_neo4j, mock_pg, mock_embed, mock_es
    ):
        """status 출력에 Neo4j 섹션 포함"""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        runner = CliRunner()
        result = runner.invoke(cli, ["status"])

        assert result.exit_code == 0
        assert "Neo4j" in result.output

    @patch("etl_cli._es_count", return_value=None)
    @patch("etl_cli._es_embedding_count", return_value=None)
    @patch("etl_cli._pg_query", return_value=None)
    @patch("etl_cli._neo4j_query", return_value=None)
    @patch("subprocess.run")
    def test_status_handles_connection_failure(
        self, mock_run, mock_neo4j, mock_pg, mock_embed, mock_es
    ):
        """모든 DB 연결 실패 시에도 status가 에러 없이 실행"""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        runner = CliRunner()
        result = runner.invoke(cli, ["status"])

        # 연결 실패해도 exit_code 0 (status 명령 자체는 성공)
        assert result.exit_code == 0
        assert "연결 실패" in result.output


# ---------------------------------------------------------------------------
# U08: cleanup --dry-run
# ---------------------------------------------------------------------------


class TestCleanupDryRun:
    """U08: cleanup --dry-run 모드"""

    @patch("etl_cli._is_container_running", return_value=True)
    @patch("etl_cli._es_count", return_value=100)
    @patch("etl_cli._pg_query", return_value="1")
    @patch("etl_cli._neo4j_query", return_value="1")
    @patch("subprocess.run")
    def test_cleanup_dry_run_includes_dry_run_flag(
        self, mock_run, mock_neo4j, mock_pg, mock_es, mock_container
    ):
        """cleanup --dry-run → docker exec 커맨드에 --dry-run 전달"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        runner = CliRunner()
        result = runner.invoke(cli, ["cleanup", "--dry-run"])

        assert result.exit_code == 0
        # subprocess.run이 호출되었을 때 --dry-run이 포함되어 있는지 확인
        assert mock_run.called
        call_args_list = mock_run.call_args_list
        # 마지막 subprocess.run 호출 (cleanup 스크립트 실행)에 --dry-run 포함
        last_call = call_args_list[-1]
        cmd_arg = str(last_call)
        assert "--dry-run" in cmd_arg

    @patch("etl_cli._is_container_running", return_value=True)
    @patch("etl_cli._es_count", return_value=100)
    @patch("etl_cli._pg_query", return_value="1")
    @patch("etl_cli._neo4j_query", return_value="1")
    @patch("subprocess.run")
    def test_cleanup_dry_run_mode_label_in_output(
        self, mock_run, mock_neo4j, mock_pg, mock_es, mock_container
    ):
        """cleanup --dry-run → 출력에 DRY-RUN 모드 레이블"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        runner = CliRunner()
        result = runner.invoke(cli, ["cleanup", "--dry-run"])

        assert result.exit_code == 0
        assert "DRY-RUN" in result.output

    @patch("etl_cli._is_container_running", return_value=False)
    @patch("etl_cli._es_count", return_value=None)
    def test_cleanup_fails_prereq_exits_nonzero(self, mock_es, mock_container):
        """컨테이너 미실행 시 cleanup 전제조건 실패 → exit 1"""
        runner = CliRunner()
        result = runner.invoke(cli, ["cleanup"])
        assert result.exit_code == 1
