#!/bin/bash
# Phase 3 Entity Extraction Monitor - 15분 간격 Slack 알림 (v2: checkpoint 기반)
# Usage: nohup bash scripts/phase3_monitor_slack.sh > /tmp/phase3_slack_monitor.log 2>&1 &

INTERVAL=900  # 15분 = 900초
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
SLACK_SCRIPT="${PROJECT_ROOT}/scripts/send_slack.sh"

SEED_COUNT=16171  # Phase 1에서 시드된 체크포인트 수
TARGET=23074      # Phase 2 신규 처리 대상
PREV_TOTAL=0

while true; do
    # 체크포인트 기반 정확한 진행률
    W0=$(docker exec kp-ai-service python3 -c "
import json
with open('/tmp/entity_checkpoint_w0.json') as f:
    d = json.load(f)
print(len(d.get('processed_ids',[])) - ${SEED_COUNT})
" 2>/dev/null || echo "0")

    W1=$(docker exec kp-ai-service python3 -c "
import json
with open('/tmp/entity_checkpoint_w1.json') as f:
    d = json.load(f)
print(len(d.get('processed_ids',[])) - ${SEED_COUNT})
" 2>/dev/null || echo "0")

    W2=$(docker exec kp-ai-service python3 -c "
import json
with open('/tmp/entity_checkpoint_w2.json') as f:
    d = json.load(f)
print(len(d.get('processed_ids',[])) - ${SEED_COUNT})
" 2>/dev/null || echo "0")

    W0=${W0:-0}; W1=${W1:-0}; W2=${W2:-0}
    TOTAL=$((W0 + W1 + W2))
    PCT=$(echo "scale=1; $TOTAL * 100 / $TARGET" | bc 2>/dev/null || echo "0")

    # 15분 증분 및 속도
    DELTA=$((TOTAL - PREV_TOTAL))
    SPEED=$(echo "scale=1; $DELTA / 15" | bc 2>/dev/null || echo "0")
    PREV_TOTAL=$TOTAL

    # ETA
    REMAINING=$((TARGET - TOTAL))
    if [ "$SPEED" != "0" ] && [ "$SPEED" != "0.0" ] && [ -n "$SPEED" ]; then
        ETA_MIN=$(echo "scale=0; $REMAINING / $SPEED" | bc 2>/dev/null || echo "0")
        ETA_HR=$(echo "scale=1; $ETA_MIN / 60" | bc 2>/dev/null || echo "?")
    else
        ETA_HR="measuring..."
    fi

    # 워커 프로세스 확인 (정확한 방법)
    ALIVE=$(docker exec kp-ai-service bash -c 'cat /proc/*/cmdline 2>/dev/null | tr "\0" " "' 2>/dev/null | grep -c "batch_entity_extraction" || echo "0")
    # grep 자체와 bash 명령 제외 보정
    if [ "$ALIVE" -gt 3 ]; then ALIVE=3; fi

    NOW=$(date '+%H:%M')
    # send_slack.sh가 [클로드] prefix를 자동 추가하므로 여기선 제외
    MSG=":bar_chart: Phase 3 모니터링 (${NOW})
• 진행: *${TOTAL}/${TARGET}* (${PCT}%)
• W0: ${W0} | W1: ${W1} | W2: ${W2}
• 속도: ~${SPEED}/min | 워커: ${ALIVE}/3
• 잔여: ${REMAINING}건 | ETA: ~${ETA_HR}h
• 15분 증분: +${DELTA}건"

    echo "[$(date)] $MSG"

    # Slack 전송
    if [ -f "$SLACK_SCRIPT" ]; then
        bash "$SLACK_SCRIPT" dev "클로드" "$MSG" 2>/dev/null
    fi

    # 완료 확인
    if [ "$TOTAL" -ge "$TARGET" ]; then
        bash "$SLACK_SCRIPT" dev "클로드" ":white_check_mark: Phase 3 완료! ${TOTAL}/${TARGET} (100%)" 2>/dev/null
        echo "[$(date)] Phase 3 COMPLETED!"
        break
    fi

    # 워커 전부 중단
    if [ "$ALIVE" -eq 0 ] && [ "$TOTAL" -gt 0 ]; then
        bash "$SLACK_SCRIPT" alerts "클로드" ":warning: Phase 3 워커 전부 중단! 처리: ${TOTAL}/${TARGET} (${PCT}%) - 잔액 소진 가능" 2>/dev/null
        echo "[$(date)] All workers stopped!"
        break
    fi

    sleep $INTERVAL
done
