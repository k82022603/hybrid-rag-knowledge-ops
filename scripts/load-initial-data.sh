#!/bin/bash
# scripts/load-initial-data.sh
# ETL 파이프라인 실행 스크립트
#
# STORY-045: 초기 데이터 ETL 파이프라인
#
# 사용법:
#   ./scripts/load-initial-data.sh                    # 기본 실행
#   ./scripts/load-initial-data.sh --no-embeddings    # 임베딩 생성 건너뛰기
#   ./scripts/load-initial-data.sh --no-entities      # 엔티티 추출 건너뛰기
#   ./scripts/load-initial-data.sh --validate-only    # 검증만 실행
#   ./scripts/load-initial-data.sh --dry-run          # 파일 탐색만 (실행 안함)
#
# 환경변수:
#   KNOWLEDGE_DATA_DIR   - 데이터 디렉토리 (기본: ./knowledge_data/documents)
#   CHUNK_SIZE           - 청크 크기 (기본: 600)
#   CHUNK_OVERLAP        - 청크 오버랩 (기본: 100)
#   BATCH_SIZE           - 임베딩 배치 크기 (기본: 32)
#   MAX_RETRIES          - 최대 재시도 횟수 (기본: 3)

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

# 기본 설정
KNOWLEDGE_DATA_DIR="${KNOWLEDGE_DATA_DIR:-./knowledge_data/documents}"
CHUNK_SIZE="${CHUNK_SIZE:-600}"
CHUNK_OVERLAP="${CHUNK_OVERLAP:-100}"
BATCH_SIZE="${BATCH_SIZE:-32}"
MAX_RETRIES="${MAX_RETRIES:-3}"

# 옵션 파싱
NO_EMBEDDINGS=false
NO_ENTITIES=false
VALIDATE_ONLY=false
DRY_RUN=false

for arg in "$@"; do
    case $arg in
        --no-embeddings)
            NO_EMBEDDINGS=true
            ;;
        --no-entities)
            NO_ENTITIES=true
            ;;
        --validate-only)
            VALIDATE_ONLY=true
            ;;
        --dry-run)
            DRY_RUN=true
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --no-embeddings    Skip embedding generation"
            echo "  --no-entities      Skip entity extraction"
            echo "  --validate-only    Run validation only (skip ETL)"
            echo "  --dry-run          Discover files only (no processing)"
            echo "  --help, -h         Show this help message"
            echo ""
            echo "Environment variables:"
            echo "  KNOWLEDGE_DATA_DIR   Data directory (default: ./knowledge_data/documents)"
            echo "  CHUNK_SIZE           Chunk size in chars (default: 600)"
            echo "  CHUNK_OVERLAP        Chunk overlap in chars (default: 100)"
            echo "  BATCH_SIZE           Embedding batch size (default: 32)"
            echo "  MAX_RETRIES          Max retries per file (default: 3)"
            exit 0
            ;;
    esac
done

echo "============================================================"
echo "  ETL Pipeline Runner v2.0 (STORY-045)"
echo "============================================================"
echo ""
echo "  Data directory:  $KNOWLEDGE_DATA_DIR"
echo "  Chunk size:      $CHUNK_SIZE"
echo "  Chunk overlap:   $CHUNK_OVERLAP"
echo "  Batch size:      $BATCH_SIZE"
echo "  Max retries:     $MAX_RETRIES"
echo "  Embeddings:      $([ "$NO_EMBEDDINGS" = true ] && echo 'DISABLED' || echo 'ENABLED')"
echo "  Entities:        $([ "$NO_ENTITIES" = true ] && echo 'DISABLED' || echo 'ENABLED')"
echo "  Mode:            $([ "$VALIDATE_ONLY" = true ] && echo 'VALIDATE ONLY' || ([ "$DRY_RUN" = true ] && echo 'DRY RUN' || echo 'FULL ETL'))"
echo ""

# 데이터 디렉토리 확인
if [ ! -d "$KNOWLEDGE_DATA_DIR" ]; then
    echo "[ERROR] Data directory not found: $KNOWLEDGE_DATA_DIR"
    echo ""
    echo "Please run seed script first:"
    echo "  ./scripts/seed-initial-data.sh"
    exit 1
fi

# 파일 수 확인
FILE_COUNT=$(find "$KNOWLEDGE_DATA_DIR" -type f \( -name "*.md" -o -name "*.pdf" -o -name "*.docx" -o -name "*.pptx" -o -name "*.txt" -o -name "*.html" \) 2>/dev/null | wc -l)
echo "[INFO] Found $FILE_COUNT documents in $KNOWLEDGE_DATA_DIR"
echo ""

if [ "$FILE_COUNT" -eq 0 ]; then
    echo "[ERROR] No documents found. Please run seed script first:"
    echo "  ./scripts/seed-initial-data.sh"
    exit 1
fi

# Python 환경 확인
PYTHON_CMD=""
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo "[ERROR] Python not found. Please install Python 3.11+"
    exit 1
fi

echo "[INFO] Using Python: $($PYTHON_CMD --version)"
echo ""

# ETL 실행 Python 스크립트
ETL_SCRIPT=$(cat <<'PYTHON_SCRIPT'
"""초기 데이터 ETL 파이프라인 실행 스크립트"""

import asyncio
import json
import os
import sys
import time

# 프로젝트 패키지 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "knowledge_service", "src"))

async def run_etl():
    """ETL 파이프라인 실행"""
    from app.services.initial_data_loader import (
        InitialDataLoader,
        DataSource,
        DocType,
    )
    from app.services.data_validator import InitialDataValidation

    # 환경변수에서 설정 읽기
    chunk_size = int(os.getenv("CHUNK_SIZE", "600"))
    chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "100"))
    batch_size = int(os.getenv("BATCH_SIZE", "32"))
    max_retries = int(os.getenv("MAX_RETRIES", "3"))
    no_embeddings = os.getenv("NO_EMBEDDINGS", "false").lower() == "true"
    no_entities = os.getenv("NO_ENTITIES", "false").lower() == "true"
    validate_only = os.getenv("VALIDATE_ONLY", "false").lower() == "true"
    dry_run = os.getenv("DRY_RUN", "false").lower() == "true"

    print("[ETL] Initializing InitialDataLoader...")

    loader = InitialDataLoader(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        batch_size=batch_size,
        max_retries=max_retries,
        enable_embeddings=not no_embeddings,
        enable_entity_extraction=not no_entities,
    )

    # 기본 데이터 소스 등록
    loader.add_default_sources()

    # 상태 출력
    status = loader.get_status()
    print(f"[ETL] Project root: {status['project_root']}")
    print(f"[ETL] Data sources: {len(status['data_sources'])}")
    for ds in status["data_sources"]:
        exists_str = "OK" if ds["exists"] else "NOT FOUND"
        print(f"  - {ds['name']}: {ds['path']} [{exists_str}]")

    # Dry run 모드
    if dry_run:
        print("\n[ETL] DRY RUN: Discovering files only...")
        files = loader.discover_files()
        print(f"[ETL] Total files: {len(files)}")
        for f in files:
            print(f"  - [{f.source_name}] {f.file_name} ({f.file_size} bytes)")
        return

    # Validate only 모드
    if validate_only:
        print("\n[ETL] VALIDATE ONLY mode - skipping ETL, running validation...")
        # 이전 실행 결과가 필요하므로 빈 summary로 검증
        print("[WARN] No previous ETL summary available for validation")
        return

    # ETL 실행
    print("\n[ETL] Starting ETL pipeline...")
    start_time = time.time()

    try:
        summary = await loader.load_all()
    except Exception as e:
        print(f"[ERROR] ETL pipeline failed: {e}")
        sys.exit(1)

    elapsed = time.time() - start_time

    # 결과 출력
    print("\n============================================================")
    print("  ETL Pipeline Results")
    print("============================================================")
    print(f"  Total files:      {summary.total_files}")
    print(f"  Successful:       {summary.success_count}")
    print(f"  Failed:           {summary.failed_count}")
    print(f"  Skipped:          {summary.skipped_count}")
    print(f"  Total chunks:     {summary.total_chunks}")
    print(f"  Total entities:   {summary.total_entities}")
    print(f"  Success rate:     {summary.success_rate * 100:.1f}%")
    print(f"  Total time:       {elapsed:.1f}s")
    print("")

    # 실패한 파일 목록
    failed = [r for r in summary.results if r.status.value == "failed"]
    if failed:
        print("  Failed files:")
        for r in failed:
            print(f"    - {r.file_name}: {r.error_message}")
        print("")

    # 검증 실행
    print("[ETL] Running validation...")
    validator = InitialDataValidation(
        min_documents=max(1, summary.total_files // 2),
        min_chunks_per_doc=2.0,
        min_entities=0 if no_entities else 5,
    )

    report = validator.validate_sync(summary)

    print("\n============================================================")
    print("  Validation Results")
    print("============================================================")
    print(f"  Overall: {report.overall_level.value.upper()}")
    print(f"  Checks:  {report.total_checks} total, "
          f"{report.passed_checks} pass, "
          f"{report.warning_checks} warn, "
          f"{report.failed_checks} fail, "
          f"{report.skipped_checks} skip")
    print("")

    for check in report.checks:
        icon = {
            "pass": "[PASS]",
            "warning": "[WARN]",
            "fail": "[FAIL]",
            "skip": "[SKIP]",
        }.get(check.level.value, "[????]")
        print(f"  {icon} {check.name}: {check.message}")

    print("")

    if report.is_valid:
        print("[DONE] ETL pipeline completed successfully!")
    else:
        print("[WARN] ETL pipeline completed with validation failures.")
        sys.exit(1)

    # 결과를 JSON으로 저장
    results_dir = os.path.join(os.path.dirname(__file__), "..", "knowledge_data", "exports")
    os.makedirs(results_dir, exist_ok=True)

    results_file = os.path.join(results_dir, "etl_results.json")
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump({
            "summary": summary.to_dict(),
            "validation": report.to_dict(),
        }, f, ensure_ascii=False, indent=2)

    print(f"[INFO] Results saved to: {results_file}")


if __name__ == "__main__":
    asyncio.run(run_etl())
PYTHON_SCRIPT
)

# 환경변수 설정
export CHUNK_SIZE="$CHUNK_SIZE"
export CHUNK_OVERLAP="$CHUNK_OVERLAP"
export BATCH_SIZE="$BATCH_SIZE"
export MAX_RETRIES="$MAX_RETRIES"
export NO_EMBEDDINGS="$NO_EMBEDDINGS"
export NO_ENTITIES="$NO_ENTITIES"
export VALIDATE_ONLY="$VALIDATE_ONLY"
export DRY_RUN="$DRY_RUN"

# Python 스크립트 실행
echo "$ETL_SCRIPT" | $PYTHON_CMD -

echo ""
echo "============================================================"
echo "  Done!"
echo "============================================================"
