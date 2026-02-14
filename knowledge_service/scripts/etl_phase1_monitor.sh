#!/bin/bash
# ETL Phase 1 모니터링 + Slack 보고 (10분 간격)
# 사용법: nohup bash scripts/etl_phase1_monitor.sh > /tmp/etl_phase1_monitor.log 2>&1 &

set -uo pipefail

INTERVAL=900  # 15분
REPORT_NUM=1
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
SEND_SLACK="$PROJECT_ROOT/scripts/send_slack.sh"
TOTAL_FILES=1786
PREV_CHUNKS=0
LOG_FILE="/tmp/etl_phase1.log"

echo "[$(date +'%Y-%m-%d %H:%M KST')] ETL Phase 1 Monitor started (interval=${INTERVAL}s)"

while true; do
    sleep "$INTERVAL"

    NOW_FULL=$(date +'%Y-%m-%d %H:%M KST')

    # --- 데이터 수집 ---
    ES_COUNT=$(curl -s http://localhost:9200/knowledge_chunks/_count 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('count',0))" 2>/dev/null || echo "0")
    PG_COUNT=$(docker exec kp-postgresql psql -U knowledge -d knowledge -t -c "SELECT count(*) FROM documents;" 2>/dev/null | tr -d ' ' || echo "0")

    # 성공/실패/스킵 카운트
    SUCCESS=$(docker exec kp-ai-service grep -c "processed successfully" "$LOG_FILE" 2>/dev/null || echo "0")
    SKIPPED=$(docker exec kp-ai-service grep -c "Skipping duplicate" "$LOG_FILE" 2>/dev/null || echo "0")
    FAILED=$(docker exec kp-ai-service grep -c "failed after\|Parse error" "$LOG_FILE" 2>/dev/null || echo "0")

    # 현재 처리 중 파일
    CURRENT_FILE=$(docker exec kp-ai-service python3 -c "
import re
with open('$LOG_FILE') as f:
    lines = f.readlines()
for line in reversed(lines):
    cleaned = re.sub(r'\x1b\[[0-9;]*m', '', line.strip())
    if 'Processing file' in cleaned:
        m = re.search(r': (.+?) \(attempt', cleaned)
        if m: print(m.group(1)[:50]); break
" 2>/dev/null || echo "unknown")

    # 시스템 리소스
    STATS=$(docker stats kp-ai-service --no-stream --format "{{.CPUPerc}}|{{.MemUsage}}" 2>/dev/null || echo "?|?")
    CPU=$(echo "$STATS" | cut -d'|' -f1)
    MEM=$(echo "$STATS" | cut -d'|' -f2)

    # 진행률
    PROCESSED=$((SUCCESS + SKIPPED + FAILED))
    PCT=$(python3 -c "print(round($PROCESSED / $TOTAL_FILES * 100, 1))" 2>/dev/null || echo "?")
    BAR=$(python3 -c "
filled = int(float('$PCT') / 5)
empty = 20 - filled
print('█' * filled + '░' * empty)
" 2>/dev/null || echo "░░░░░░░░░░░░░░░░░░░░")

    # 증감량
    if [ "$PREV_CHUNKS" -gt 0 ] 2>/dev/null; then
        DELTA=$((ES_COUNT - PREV_CHUNKS))
        DELTA_STR="+${DELTA}"
    else
        DELTA_STR="--"
    fi
    PREV_CHUNKS=$ES_COUNT

    # ETL 종료 감지
    ETL_DONE=$(docker exec kp-ai-service python3 -c "
with open('$LOG_FILE') as f:
    content = f.read()
print('yes' if 'Phase 1 Completed' in content else 'no')
" 2>/dev/null || echo "no")

    # --- Slack 메시지 ---
    if [ "$ETL_DONE" = "yes" ]; then
        MSG=":tada: Phase 1 상태 리포트 #${REPORT_NUM} (${NOW_FULL})

*Phase 1 완료!*
\`\`\`
${BAR} ${PCT}%
\`\`\`
• 신규 성공: \`${SUCCESS}\` | 중복 skip: \`${SKIPPED}\` | 실패: \`${FAILED}\`
• ES 청크: \`${ES_COUNT}\` (${DELTA_STR})
• PG 문서: \`${PG_COUNT}\`
• CPU: \`${CPU}\` | 메모리: \`${MEM}\`

:white_check_mark: Phase 1 완료! → Phase 2 (Colab GPU 임베딩) 준비"
    else
        MSG=":bar_chart: Phase 1 상태 리포트 #${REPORT_NUM} (${NOW_FULL})

*Phase 1: 파싱 + 청킹 진행 중*
\`\`\`
${BAR} ${PCT}%
\`\`\`
• 신규 성공: \`${SUCCESS}\` | 중복 skip: \`${SKIPPED}\` | 실패: \`${FAILED}\`
• ES 청크: \`${ES_COUNT}\` (${DELTA_STR})
• PG 문서: \`${PG_COUNT}\`
• 현재 파일: \`${CURRENT_FILE}\`
• CPU: \`${CPU}\` | 메모리: \`${MEM}\`"
    fi

    # --- Slack 전송 ---
    bash "$SEND_SLACK" dev "클로드" "$MSG" 2>/dev/null
    SEND_RESULT=$?

    echo "[${NOW_FULL}] Report #${REPORT_NUM}: ES=${ES_COUNT}(${DELTA_STR}), PG=${PG_COUNT}, Success=${SUCCESS}, Skip=${SKIPPED}, Fail=${FAILED}, Send=${SEND_RESULT}"

    REPORT_NUM=$((REPORT_NUM + 1))

    # ETL 완료 시 모니터링 종료
    if [ "$ETL_DONE" = "yes" ]; then
        echo "[${NOW_FULL}] Phase 1 completed. Monitor stopping."
        break
    fi
done

echo "[$(date +'%Y-%m-%d %H:%M KST')] ETL Phase 1 Monitor stopped."
