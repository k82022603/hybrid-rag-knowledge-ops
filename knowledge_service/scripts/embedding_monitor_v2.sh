#!/bin/bash
# ============================================================================
# 임베딩 배치 v2.1 모니터링 스크립트 (threads=8 HyperThreading)
# ============================================================================
# 용도: run_embedding_backfill_v2.py 프로세스의 진행률을 /tmp/etl_progress.json에서 읽어
#       주기적으로 출력합니다. (Slack 알림은 제외)
#
# 사용법:
#   bash scripts/embedding_monitor_v2.sh
#
# 환경변수:
#   INTERVAL - 체크 간격 (초, 기본 60 = 1분, 빠른 피드백용)
#
# 종료 조건:
#   - status="completed"
#   - Ctrl+C (수동 종료)
#
# 작성: 2026-02-12, Data Agent
# ============================================================================

set -euo pipefail

INTERVAL="${INTERVAL:-60}"  # 기본 1분 (빠른 피드백)
PROGRESS_FILE="/tmp/etl_progress.json"

echo "================================================================"
echo "  임베딩 배치 v2.1 모니터링 시작 (threads=8)"
echo "  간격: ${INTERVAL}초"
echo "  Progress 파일: ${PROGRESS_FILE}"
echo "================================================================"

BASELINE_RATE=0.8  # v2 (threads=4) 기준선
TARGET_RATE=0.85   # v2.1 (threads=8) 목표

while true; do
    sleep "$INTERVAL"

    # 컨테이너 내부 progress 파일 읽기
    PROGRESS=$(docker exec kp-ai-service cat "$PROGRESS_FILE" 2>/dev/null || echo "{}")

    if [ "$PROGRESS" = "{}" ]; then
        echo "[$(date +%H:%M)] Progress 파일 없음 - 프로세스 미실행?"
        continue
    fi

    # JSON 파싱
    STATUS=$(echo "$PROGRESS" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('status','unknown'))")
    TOTAL=$(echo "$PROGRESS" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('total_chunks',0))")
    EMBEDDED=$(echo "$PROGRESS" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('embedded',0))")
    ERRORS=$(echo "$PROGRESS" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('errors',0))")
    RATE=$(echo "$PROGRESS" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('rate_texts_per_sec',0))")
    ETA=$(echo "$PROGRESS" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('eta_minutes',0))")
    VERSION=$(echo "$PROGRESS" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('version','unknown'))")

    # 퍼센트 계산
    if [ "$TOTAL" -gt 0 ]; then
        PCT=$(python3 -c "print(f'{${EMBEDDED}/${TOTAL}*100:.2f}')")
    else
        PCT="0.00"
    fi

    # 속도 개선율 계산
    if [ "$(echo "$RATE > 0" | bc -l)" -eq 1 ]; then
        IMPROVEMENT=$(python3 -c "print(f'{(${RATE}/${BASELINE_RATE}-1)*100:+.1f}')")
    else
        IMPROVEMENT="+0.0"
    fi

    # CPU 사용률 확인
    CPU_USAGE=$(docker stats kp-ai-service --no-stream --format "{{.CPUPerc}}" | sed 's/%//')
    MEM_USAGE=$(docker stats kp-ai-service --no-stream --format "{{.MemUsage}}")

    TIME_KST=$(date +"%H:%M:%S")

    echo "────────────────────────────────────────────────────────────────"
    echo "[${TIME_KST}] v2.1 Progress (${VERSION})"
    echo "  Status: ${STATUS}"
    echo "  Progress: ${EMBEDDED} / ${TOTAL} (${PCT}%)"
    echo "  Speed: ${RATE} t/s (baseline: ${BASELINE_RATE}, target: ${TARGET_RATE}) [${IMPROVEMENT}%]"
    echo "  ETA: ${ETA} min"
    echo "  Errors: ${ERRORS}"
    echo "  Resources: CPU=${CPU_USAGE}% (target: 600-800%), MEM=${MEM_USAGE}"

    # 성능 평가
    if [ "$(echo "$RATE >= $TARGET_RATE" | bc -l)" -eq 1 ]; then
        echo "  ✓ 목표 달성! (${RATE} >= ${TARGET_RATE})"
    elif [ "$(echo "$RATE >= $BASELINE_RATE" | bc -l)" -eq 1 ]; then
        echo "  △ 개선 중 (${RATE} >= ${BASELINE_RATE})"
    elif [ "$(echo "$RATE > 0" | bc -l)" -eq 1 ]; then
        echo "  ✗ 기준선 미달 (${RATE} < ${BASELINE_RATE})"
    fi

    # 완료 체크
    if [ "$STATUS" = "completed" ]; then
        echo "════════════════════════════════════════════════════════════════"
        echo "  임베딩 배치 완료!"
        echo "  최종: ${EMBEDDED} / ${TOTAL} (${PCT}%)"
        echo "  평균 속도: ${RATE} t/s"
        echo "  에러: ${ERRORS}"
        echo "════════════════════════════════════════════════════════════════"
        break
    fi
done
