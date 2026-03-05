#!/usr/bin/env python3
"""
ETL CLI -- 통합 ETL 파이프라인 명령행 도구 (STORY-125)

산재된 7개 ETL 스크립트를 단일 CLI로 통합합니다.

사용법 (호스트에서):
    python knowledge_service/scripts/etl_cli.py phase1 [--dry-run]
    python knowledge_service/scripts/etl_cli.py phase2
    python knowledge_service/scripts/etl_cli.py phase3 [--concurrency 3] [--resume]
    python knowledge_service/scripts/etl_cli.py all
    python knowledge_service/scripts/etl_cli.py status
    python knowledge_service/scripts/etl_cli.py cleanup [--dry-run] [--batch-size 200]

통합 대상 스크립트:
    - run_etl_phase1_chunks.py   (Phase 1: 파싱+청킹)
    - run_etl_phase2.py          (Phase 2: 바이너리 파일 처리)
    - run_etl_phase2_entities.py (Phase 3: 엔티티 추출)
    - batch_entity_extraction.py (Phase 3 대안: 청크 기반 엔티티 추출)
    - cleanup_orphan_nodes.py    (고아 노드 정리)
    - embedding_monitor.sh       (임베딩 모니터링)
    - etl_phase1_monitor.sh      (Phase 1 모니터링)
    - etl_v2_monitor.sh          (전체 ETL 모니터링)

3-Phase ETL 파이프라인:
    Phase 1 (CPU):   파싱 + 청킹 -> ES/PG/Neo4j 저장 (embedding=OFF, entity=OFF)
    Phase 2 (GPU):   Colab GPU 임베딩 (dense+sparse) -> ES 임포트
    Phase 3 (CPU):   엔티티 추출(DeepSeek) -> Neo4j HAS_ENTITY/RELATED_TO -> PG entity_count
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import click

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CONTAINER_NAME = "kp-ai-service"
PG_CONTAINER = "kp-postgresql"
NEO4J_CONTAINER = "kp-neo4j"
ES_URL = "http://localhost:9200"
ES_INDEX = "knowledge_chunks"
PG_DB = "knowledge"
PG_USER = "knowledge"

# Script paths (inside container)
PHASE1_SCRIPT = "/app/scripts/run_etl_phase1_chunks.py"
PHASE3_SCRIPT = "/app/scripts/batch_entity_extraction.py"
CLEANUP_SCRIPT = "/app/scripts/cleanup_orphan_nodes.py"

LOG_DIR = "/tmp"


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _log_path(phase: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{LOG_DIR}/etl_cli_{phase}_{ts}.log"


def _run_cmd(cmd: list[str], capture: bool = False) -> subprocess.CompletedProcess:
    """Run a shell command, streaming output to stdout unless capture=True."""
    if capture:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return subprocess.run(cmd, text=True)


def _docker_exec(container: str, cmd: str, capture: bool = False) -> subprocess.CompletedProcess:
    """Execute a command inside a Docker container."""
    full_cmd = ["docker", "exec", container, "bash", "-c", cmd]
    return _run_cmd(full_cmd, capture=capture)


def _docker_exec_detached(container: str, cmd: str, log_file: str) -> None:
    """Execute a command inside a Docker container in detached mode with nohup."""
    nohup_cmd = f"nohup {cmd} > {log_file} 2>&1 &"
    subprocess.run(
        ["docker", "exec", "-d", container, "bash", "-c", nohup_cmd],
        text=True,
    )


def _is_container_running(name: str) -> bool:
    """Check if a Docker container is running."""
    result = _run_cmd(
        ["docker", "inspect", "-f", "{{.State.Running}}", name],
        capture=True,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def _es_count() -> Optional[int]:
    """Get total chunk count from Elasticsearch."""
    try:
        import urllib.request
        req = urllib.request.Request(
            f"{ES_URL}/{ES_INDEX}/_count",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            return data.get("count", 0)
    except Exception:
        return None


def _es_embedding_count() -> Optional[int]:
    """Get count of chunks with dense_vector from Elasticsearch."""
    try:
        import urllib.request
        body = json.dumps({"query": {"exists": {"field": "dense_vector"}}}).encode()
        req = urllib.request.Request(
            f"{ES_URL}/{ES_INDEX}/_count",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            return data.get("count", 0)
    except Exception:
        return None


def _pg_query(sql: str) -> Optional[str]:
    """Execute a PostgreSQL query and return the result."""
    result = _docker_exec(
        PG_CONTAINER,
        f"psql -U {PG_USER} -d {PG_DB} -t -c \"{sql}\"",
        capture=True,
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def _neo4j_query(cypher: str) -> Optional[str]:
    """Execute a Neo4j Cypher query via the AI service container."""
    escaped = cypher.replace("'", "\\'")
    result = _docker_exec(
        CONTAINER_NAME,
        f"""python3 -c "
from neo4j import GraphDatabase
d=GraphDatabase.driver('bolt://neo4j:7687',auth=('neo4j','neo4j_dev_2026!'))
with d.session() as s:
    r=s.run('{escaped}')
    rec=r.single()
    print(rec[0] if rec else 0)
d.close()
" """,
        capture=True,
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return None


# ---------------------------------------------------------------------------
# Prerequisite checks
# ---------------------------------------------------------------------------


def check_prerequisites(phases: list[str] | None = None) -> bool:
    """Check Docker containers and DB connectivity.

    Args:
        phases: list of phases to check for (e.g. ['phase1', 'phase3']).
                If None, checks all.

    Returns:
        True if all prerequisites are met.
    """
    all_ok = True
    checks = []

    # Always check AI service container
    containers = [CONTAINER_NAME]

    # Phase-specific containers
    if phases is None or any(p in (phases or []) for p in ["phase1", "phase3", "status", "cleanup"]):
        containers.extend([PG_CONTAINER, NEO4J_CONTAINER])

    seen = set()
    for c in containers:
        if c in seen:
            continue
        seen.add(c)
        running = _is_container_running(c)
        status = "OK" if running else "FAIL"
        checks.append((f"Container {c}", status))
        if not running:
            all_ok = False

    # ES connectivity
    es_count = _es_count()
    if es_count is not None:
        checks.append((f"Elasticsearch ({ES_INDEX})", f"OK ({es_count} chunks)"))
    else:
        checks.append(("Elasticsearch", "FAIL (unreachable)"))
        all_ok = False

    # PG connectivity
    if PG_CONTAINER in seen:
        pg_result = _pg_query("SELECT 1")
        if pg_result and "1" in pg_result:
            doc_count = _pg_query("SELECT count(*) FROM documents") or "?"
            checks.append(("PostgreSQL", f"OK ({doc_count} docs)"))
        else:
            checks.append(("PostgreSQL", "FAIL"))
            all_ok = False

    # Neo4j connectivity
    if NEO4J_CONTAINER in seen:
        neo4j_result = _neo4j_query("RETURN 1")
        if neo4j_result and "1" in neo4j_result:
            entity_count = _neo4j_query("MATCH (e:Entity) RETURN count(e)") or "?"
            checks.append(("Neo4j", f"OK ({entity_count} entities)"))
        else:
            checks.append(("Neo4j", "FAIL"))
            all_ok = False

    # Display results
    click.echo()
    click.echo("=" * 55)
    click.echo("  Prerequisite Check")
    click.echo("=" * 55)
    for name, status in checks:
        marker = "[OK]  " if "OK" in status else "[FAIL]"
        click.echo(f"  {marker} {name}: {status}")
    click.echo("=" * 55)
    click.echo()

    return all_ok


# ---------------------------------------------------------------------------
# CLI Group
# ---------------------------------------------------------------------------


@click.group()
@click.version_option(version="1.0.0", prog_name="etl-cli")
def cli():
    """ETL CLI -- 통합 ETL 파이프라인 명령행 도구

    3-Phase ETL 파이프라인을 단일 CLI로 관리합니다.

    \b
    Phase 1: 파싱+청킹 (CPU)
    Phase 2: GPU 임베딩 (Colab)
    Phase 3: 엔티티 추출 (CPU + DeepSeek)
    """
    pass


# ---------------------------------------------------------------------------
# phase1 -- 파싱 + 청킹
# ---------------------------------------------------------------------------


@cli.command()
@click.option("--dry-run", is_flag=True, help="실행하지 않고 계획만 표시")
@click.option("--chunk-size", type=int, default=1000, help="청크 크기 (기본: 1000)")
@click.option("--chunk-overlap", type=int, default=200, help="청크 오버랩 (기본: 200)")
def phase1(dry_run: bool, chunk_size: int, chunk_overlap: int):
    """Phase 1: 문서 파싱 + 청킹 -> ES/PG/Neo4j 저장

    임베딩과 엔티티 추출은 비활성화됩니다.
    """
    click.echo("[Phase 1] 문서 파싱 + 청킹 (임베딩 OFF, 엔티티 OFF)")

    if not check_prerequisites(["phase1"]):
        click.echo("전제조건 미충족. 중단합니다.")
        sys.exit(1)

    if dry_run:
        # Show what would be processed
        result = _docker_exec(
            CONTAINER_NAME,
            "find /app/knowledge_data/documents -type f | wc -l",
            capture=True,
        )
        file_count = result.stdout.strip() if result.returncode == 0 else "?"
        click.echo(f"[DRY-RUN] 처리 대상 파일: {file_count}개")
        click.echo(f"[DRY-RUN] 청크 크기: {chunk_size}, 오버랩: {chunk_overlap}")
        click.echo(f"[DRY-RUN] 실행 명령: docker exec {CONTAINER_NAME} python3 {PHASE1_SCRIPT}")
        click.echo("[DRY-RUN] 실제 실행은 --dry-run 플래그를 제거하세요.")
        return

    log_file = _log_path("phase1")
    container_log = "/tmp/etl_phase1.log"

    click.echo(f"로그 파일: {container_log} (컨테이너 내부)")
    click.echo(f"모니터링: docker exec {CONTAINER_NAME} tail -f {container_log}")
    click.echo()

    # Run Phase 1 inside the container
    cmd = f"python3 {PHASE1_SCRIPT}"
    click.echo(f"실행: docker exec {CONTAINER_NAME} {cmd}")
    click.echo("-" * 55)

    result = _docker_exec(CONTAINER_NAME, f"{cmd} 2>&1 | tee {container_log}")

    if result.returncode == 0:
        click.echo()
        click.echo("[Phase 1] 완료!")
        click.echo("다음 단계: etl_cli.py phase2 (GPU 임베딩)")
    else:
        click.echo()
        click.echo(f"[Phase 1] 오류 발생 (exit code: {result.returncode})")
        click.echo(f"로그 확인: docker exec {CONTAINER_NAME} tail -100 {container_log}")
        sys.exit(result.returncode)


# ---------------------------------------------------------------------------
# phase2 -- GPU 임베딩 (Colab 안내)
# ---------------------------------------------------------------------------


@cli.command()
@click.option("--export", "export_chunks", is_flag=True, help="GPU 임베딩용 청크 JSONL 내보내기")
def phase2(export_chunks: bool):
    """Phase 2: GPU 임베딩 (Colab 가이드 안내)

    GPU가 필요하므로 CLI에서 직접 실행하지 않고 Colab 가이드를 안내합니다.
    --export 옵션으로 JSONL 파일을 내보낼 수 있습니다.
    """
    click.echo("[Phase 2] GPU 임베딩 (Colab)")
    click.echo()

    if export_chunks:
        click.echo("임베딩 대기 청크를 JSONL로 내보내는 중...")
        # Query ES for chunks without dense_vector
        result = _docker_exec(
            CONTAINER_NAME,
            """python3 -c "
import json
from elasticsearch import Elasticsearch
es = Elasticsearch('http://elasticsearch:9200')
resp = es.search(
    index='knowledge_chunks',
    body={
        'size': 0,
        'query': {'bool': {'must_not': [{'exists': {'field': 'dense_vector'}}]}},
    },
)
total = resp['hits']['total']['value']
print(f'임베딩 대기 청크: {total}개')
" """,
            capture=True,
        )
        if result.returncode == 0:
            click.echo(result.stdout.strip())
        else:
            click.echo("ES 조회 실패. 컨테이너 상태를 확인하세요.")

        click.echo()

    # Print Colab guide
    click.echo("=" * 55)
    click.echo("  Phase 2 GPU 임베딩 가이드")
    click.echo("=" * 55)
    click.echo()
    click.echo("Phase 2는 GPU가 필요하므로 Colab에서 실행합니다.")
    click.echo()
    click.echo("  1. Colab 노트북 열기:")
    click.echo("     knowledge_service/scripts/gpu_embedding_colab.ipynb")
    click.echo()
    click.echo("  2. ES에서 pending 청크 추출:")
    click.echo("     dense_vector가 없는 청크를 JSONL로 내보내기")
    click.echo()
    click.echo("  3. GPU 임베딩 실행 (BGE-M3):")
    click.echo("     dense + sparse 벡터 생성")
    click.echo()
    click.echo("  4. 결과 ES로 임포트:")
    click.echo("     import_embeddings.py 사용")
    click.echo()
    click.echo("완료 후: etl_cli.py phase3 (엔티티 추출)")
    click.echo("=" * 55)


# ---------------------------------------------------------------------------
# phase3 -- 엔티티 추출
# ---------------------------------------------------------------------------


@cli.command()
@click.option("--dry-run", is_flag=True, help="실행하지 않고 대상 통계만 표시")
@click.option("--concurrency", "-c", type=int, default=3, help="동시 처리 수 (기본: 3)")
@click.option("--resume", is_flag=True, help="이전 체크포인트에서 재개")
@click.option("--max-chunks", type=int, default=0, help="최대 처리 청크 수 (0=전체)")
def phase3(dry_run: bool, concurrency: int, resume: bool, max_chunks: int):
    """Phase 3: 엔티티 추출 (DeepSeek) -> Neo4j

    Neo4j 청크에서 엔티티/관계를 추출하여 저장합니다.
    """
    click.echo(f"[Phase 3] 엔티티 추출 (concurrency={concurrency}, resume={resume})")

    if not check_prerequisites(["phase3"]):
        click.echo("전제조건 미충족. 중단합니다.")
        sys.exit(1)

    if dry_run:
        # Show entity extraction targets
        total_chunks = _neo4j_query(
            "MATCH (c:Chunk) WHERE c.token_count >= 150 RETURN count(c)"
        ) or "?"
        extracted = _neo4j_query(
            "MATCH (c:Chunk) WHERE c.entity_extracted = true RETURN count(c)"
        ) or "?"
        entities = _neo4j_query("MATCH (e:Entity) RETURN count(e)") or "?"
        rels = _neo4j_query("MATCH ()-[r:RELATED_TO]->() RETURN count(r)") or "?"

        click.echo()
        click.echo(f"[DRY-RUN] 대상 청크 (>= 150 tokens): {total_chunks}개")
        click.echo(f"[DRY-RUN] 추출 완료: {extracted}개")
        click.echo(f"[DRY-RUN] 현재 엔티티: {entities}개")
        click.echo(f"[DRY-RUN] 현재 관계: {rels}개")
        click.echo(f"[DRY-RUN] 동시 처리: {concurrency}")
        click.echo(f"[DRY-RUN] 실행 명령: docker exec {CONTAINER_NAME} python3 {PHASE3_SCRIPT}")
        return

    container_log = "/tmp/etl_phase3.log"

    # Build command
    env_vars = f"ENTITY_CONCURRENCY={concurrency}"
    if max_chunks > 0:
        env_vars += f" ENTITY_MAX_CHUNKS={max_chunks}"
    cmd = f"{env_vars} python3 {PHASE3_SCRIPT}"

    click.echo(f"로그 파일: {container_log} (컨테이너 내부)")
    click.echo(f"모니터링: docker exec {CONTAINER_NAME} tail -f {container_log}")
    click.echo()
    click.echo(f"실행: docker exec {CONTAINER_NAME} {cmd}")
    click.echo("-" * 55)

    result = _docker_exec(CONTAINER_NAME, f"{cmd} 2>&1 | tee {container_log}")

    if result.returncode == 0:
        click.echo()
        click.echo("[Phase 3] 완료!")
        click.echo("다음 단계: etl_cli.py cleanup (고아 노드 정리)")
    else:
        click.echo()
        click.echo(f"[Phase 3] 오류 발생 (exit code: {result.returncode})")
        click.echo(f"로그 확인: docker exec {CONTAINER_NAME} tail -100 {container_log}")
        sys.exit(result.returncode)


# ---------------------------------------------------------------------------
# all -- 순차 실행
# ---------------------------------------------------------------------------


@cli.command()
@click.option("--dry-run", is_flag=True, help="실행하지 않고 계획만 표시")
@click.option("--concurrency", "-c", type=int, default=3, help="Phase 3 동시 처리 수")
def all(dry_run: bool, concurrency: int):
    """Phase 1 -> Phase 3 순차 실행 (Phase 2는 GPU 안내)

    Phase 2는 GPU가 필요하므로 Colab 가이드만 출력합니다.
    """
    click.echo("=" * 55)
    click.echo("  ETL 전체 파이프라인 (Phase 1 -> 2 안내 -> 3)")
    click.echo("=" * 55)
    click.echo()

    if not check_prerequisites():
        click.echo("전제조건 미충족. 중단합니다.")
        sys.exit(1)

    start_time = time.monotonic()

    # Phase 1
    click.echo()
    click.echo("=" * 55)
    click.echo("  [1/3] Phase 1: 파싱 + 청킹")
    click.echo("=" * 55)

    if dry_run:
        result = _docker_exec(
            CONTAINER_NAME,
            "find /app/knowledge_data/documents -type f | wc -l",
            capture=True,
        )
        file_count = result.stdout.strip() if result.returncode == 0 else "?"
        click.echo(f"[DRY-RUN] Phase 1: {file_count}개 파일 처리 예정")
    else:
        container_log = "/tmp/etl_phase1.log"
        result = _docker_exec(
            CONTAINER_NAME,
            f"python3 {PHASE1_SCRIPT} 2>&1 | tee {container_log}",
        )
        if result.returncode != 0:
            click.echo("[Phase 1] 실패. 파이프라인 중단.")
            sys.exit(1)
        click.echo("[Phase 1] 완료!")

    # Phase 2 -- 안내만
    click.echo()
    click.echo("=" * 55)
    click.echo("  [2/3] Phase 2: GPU 임베딩 (안내)")
    click.echo("=" * 55)
    click.echo()
    click.echo("Phase 2는 GPU가 필요하므로 Colab에서 별도 실행하세요.")
    click.echo("Colab 노트북: knowledge_service/scripts/gpu_embedding_colab.ipynb")
    click.echo()
    click.echo("GPU 임베딩 완료 후 Phase 3이 자동으로 계속됩니다.")
    click.echo("(--dry-run 모드에서는 Phase 3도 표시만 합니다)")

    if not dry_run:
        click.echo()
        click.echo("Phase 2 임베딩이 이미 완료되었다면 Enter를 누르세요.")
        click.echo("건너뛰려면 's' 입력 후 Enter:")
        try:
            user_input = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            user_input = "s"

        if user_input == "s":
            click.echo("Phase 2 건너뜀.")

    # Phase 3
    click.echo()
    click.echo("=" * 55)
    click.echo(f"  [3/3] Phase 3: 엔티티 추출 (concurrency={concurrency})")
    click.echo("=" * 55)

    if dry_run:
        total_chunks = _neo4j_query(
            "MATCH (c:Chunk) WHERE c.token_count >= 150 RETURN count(c)"
        ) or "?"
        click.echo(f"[DRY-RUN] Phase 3: {total_chunks}개 청크 엔티티 추출 예정")
    else:
        container_log = "/tmp/etl_phase3.log"
        env_vars = f"ENTITY_CONCURRENCY={concurrency}"
        result = _docker_exec(
            CONTAINER_NAME,
            f"{env_vars} python3 {PHASE3_SCRIPT} 2>&1 | tee {container_log}",
        )
        if result.returncode != 0:
            click.echo("[Phase 3] 실패.")
            sys.exit(1)
        click.echo("[Phase 3] 완료!")

    # Summary
    elapsed = time.monotonic() - start_time
    click.echo()
    click.echo("=" * 55)
    click.echo("  ETL 파이프라인 완료")
    click.echo("=" * 55)
    click.echo(f"  소요 시간: {int(elapsed)}s ({elapsed/60:.1f}m)")

    if not dry_run:
        # Show final status
        _print_status()


# ---------------------------------------------------------------------------
# status -- 진행률 조회
# ---------------------------------------------------------------------------


def _print_status():
    """Print ETL status from all data stores."""
    click.echo()
    click.echo("=" * 55)
    click.echo("  ETL 파이프라인 상태")
    click.echo("=" * 55)

    # ES stats
    es_total = _es_count()
    es_embedded = _es_embedding_count()
    if es_total is not None:
        embed_pct = (
            f"{es_embedded / es_total * 100:.1f}%" if es_total > 0 and es_embedded is not None else "N/A"
        )
        click.echo(f"\n  [Elasticsearch]")
        click.echo(f"    총 청크:     {es_total}")
        click.echo(f"    임베딩 완료: {es_embedded or '?'} ({embed_pct})")
        pending = (es_total - es_embedded) if es_total and es_embedded else "?"
        click.echo(f"    임베딩 대기: {pending}")
    else:
        click.echo(f"\n  [Elasticsearch] 연결 실패")

    # PG stats
    pg_docs = _pg_query("SELECT count(*) FROM documents")
    if pg_docs:
        pg_completed = _pg_query(
            "SELECT count(*) FROM documents WHERE status = 'completed'"
        ) or "?"
        pg_failed = _pg_query(
            "SELECT count(*) FROM documents WHERE status = 'failed'"
        ) or "?"
        click.echo(f"\n  [PostgreSQL]")
        click.echo(f"    총 문서:  {pg_docs}")
        click.echo(f"    완료:     {pg_completed}")
        click.echo(f"    실패:     {pg_failed}")
    else:
        click.echo(f"\n  [PostgreSQL] 연결 실패")

    # Neo4j stats
    neo4j_entities = _neo4j_query("MATCH (e:Entity) RETURN count(e)")
    if neo4j_entities:
        neo4j_chunks = _neo4j_query("MATCH (c:Chunk) RETURN count(c)") or "?"
        neo4j_docs = _neo4j_query("MATCH (d:Document) RETURN count(d)") or "?"
        neo4j_rels = _neo4j_query("MATCH ()-[r:RELATED_TO]->() RETURN count(r)") or "?"
        neo4j_mentions = _neo4j_query("MATCH ()-[r:MENTIONS]->() RETURN count(r)") or "?"

        # Orphan ratio
        neo4j_orphan = _neo4j_query(
            "MATCH (e:Entity) WHERE NOT (e)<-[:MENTIONS]-() RETURN count(e)"
        ) or "0"
        total_e = int(neo4j_entities) if neo4j_entities.isdigit() else 0
        orphan_e = int(neo4j_orphan) if neo4j_orphan.isdigit() else 0
        orphan_pct = f"{orphan_e / total_e * 100:.1f}%" if total_e > 0 else "N/A"

        click.echo(f"\n  [Neo4j]")
        click.echo(f"    문서:     {neo4j_docs}")
        click.echo(f"    청크:     {neo4j_chunks}")
        click.echo(f"    엔티티:   {neo4j_entities}")
        click.echo(f"    관계:     {neo4j_rels}")
        click.echo(f"    MENTIONS: {neo4j_mentions}")
        click.echo(f"    고아 엔티티: {neo4j_orphan} ({orphan_pct})")
    else:
        click.echo(f"\n  [Neo4j] 연결 실패")

    # Progress files (if exist)
    for pf_name, pf_path in [
        ("Phase 1", "/app/knowledge_data/etl_phase1_progress.json"),
        ("Phase 3 (entity)", "/app/knowledge_data/etl_phase2_progress.json"),
        ("Phase 3 (batch)", "/tmp/entity_checkpoint.json"),
    ]:
        result = _docker_exec(
            CONTAINER_NAME,
            f"cat {pf_path} 2>/dev/null",
            capture=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            try:
                progress = json.loads(result.stdout)
                status = progress.get("status", "unknown")
                click.echo(f"\n  [Progress: {pf_name}]")
                click.echo(f"    상태: {status}")
                if "success" in progress:
                    click.echo(f"    성공: {progress['success']}")
                if "failed" in progress:
                    click.echo(f"    실패: {progress['failed']}")
                if "elapsed_seconds" in progress:
                    elapsed = progress["elapsed_seconds"]
                    click.echo(f"    소요: {elapsed}s ({elapsed/60:.1f}m)")
            except json.JSONDecodeError:
                pass

    click.echo()
    click.echo("=" * 55)


@cli.command()
def status():
    """각 Phase 진행률 조회 (PG/ES/Neo4j 상태)"""
    _print_status()


# ---------------------------------------------------------------------------
# cleanup -- 고아 노드 정리
# ---------------------------------------------------------------------------


@cli.command()
@click.option("--dry-run", is_flag=True, help="삭제하지 않고 고아 노드 목록만 확인")
@click.option("--batch-size", type=int, default=200, help="배치 삭제 단위 (기본: 200)")
def cleanup(dry_run: bool, batch_size: int):
    """Neo4j 고아 Entity 노드 정리

    Chunk와 연결되지 않은 Entity 노드(MENTIONS 관계 없음)를 삭제합니다.
    목표: 고아 비율 1% 미만 유지.
    """
    mode = "DRY-RUN" if dry_run else "DELETE"
    click.echo(f"[Cleanup] 고아 Entity 노드 정리 (모드: {mode}, 배치: {batch_size})")

    if not check_prerequisites(["cleanup"]):
        click.echo("전제조건 미충족. 중단합니다.")
        sys.exit(1)

    # Build command
    args = []
    if dry_run:
        args.append("--dry-run")
    args.append(f"--batch-size {batch_size}")

    cmd = f"python3 {CLEANUP_SCRIPT} {' '.join(args)}"

    click.echo()
    click.echo(f"실행: docker exec {CONTAINER_NAME} {cmd}")
    click.echo("-" * 55)

    result = _docker_exec(CONTAINER_NAME, cmd)

    if result.returncode == 0:
        click.echo()
        click.echo("[Cleanup] 완료!")
    else:
        click.echo()
        click.echo(f"[Cleanup] 경고: 고아 비율이 기준(1%)을 초과합니다.")
        sys.exit(result.returncode)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
