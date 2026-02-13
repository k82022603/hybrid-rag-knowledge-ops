#!/bin/bash
# ============================================================================
# 임베딩 상태 리포트 (15분 간격 Slack 보고)
# ============================================================================
# 사용법:
#   nohup bash scripts/embedding_status_report.sh > /tmp/status_report.log 2>&1 &
# ============================================================================

set -uo pipefail

SCRIPT_DIR="/mnt/d/Users/KTDS/Documents/06.과제/hybrid-rag-knowledge-ops/scripts"
SEND_SLACK="$SCRIPT_DIR/send_slack.sh"
INTERVAL=900  # 15분
PYTHON_CMD="python3"
report_count=0

echo "[Status Report] Started - 15분 간격 Slack 상태 보고"

while true; do
    report_count=$((report_count + 1))
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M KST')

    # ── 1. 임베딩 진행 데이터 ──
    P3_DATA=$(docker exec kp-ai-service $PYTHON_CMD -c "
import json
try:
    with open('/tmp/etl_progress.json') as f:
        d = json.load(f)
    total = d.get('total_chunks', 0)
    embedded = d.get('embedded', 0)
    errors = d.get('errors', 0)
    rate = round(d.get('rate_texts_per_sec', 0), 1)
    eta = d.get('eta_minutes', 0)
    pct = round(embedded * 100 / total, 1) if total > 0 else 0
    print(f'{total}|{embedded}|{errors}|{rate}|{eta}|{pct}')
except:
    print('0|0|0|0|0|0')
" 2>/dev/null || echo "0|0|0|0|0|0")

    P3_TOTAL=$(echo "$P3_DATA" | cut -d'|' -f1 | tr -d '[:space:]')
    P3_EMBEDDED=$(echo "$P3_DATA" | cut -d'|' -f2 | tr -d '[:space:]')
    P3_ERRORS=$(echo "$P3_DATA" | cut -d'|' -f3 | tr -d '[:space:]')
    P3_RATE=$(echo "$P3_DATA" | cut -d'|' -f4 | tr -d '[:space:]')
    P3_ETA=$(echo "$P3_DATA" | cut -d'|' -f5 | tr -d '[:space:]')
    P3_PCT=$(echo "$P3_DATA" | cut -d'|' -f6 | tr -d '[:space:]')

    # ── 2. ES 임베딩 카운트 ──
    ES_EMBEDDED=$(docker exec kp-ai-service curl -s 'http://kp-elasticsearch:9200/knowledge_chunks/_count' -H 'Content-Type: application/json' -d '{"query":{"exists":{"field":"dense_vector"}}}' 2>/dev/null | $PYTHON_CMD -c "import sys,json; print(json.load(sys.stdin).get('count',0))" 2>/dev/null || echo "0")
    ES_TOTAL=$(docker exec kp-ai-service curl -s 'http://kp-elasticsearch:9200/knowledge_chunks/_count' 2>/dev/null | $PYTHON_CMD -c "import sys,json; print(json.load(sys.stdin).get('count',0))" 2>/dev/null || echo "0")
    ES_PCT=$($PYTHON_CMD -c "print(round(int('${ES_EMBEDDED}') * 100 / int('${ES_TOTAL}'), 1)) if int('${ES_TOTAL}') > 0 else print(0)" 2>/dev/null || echo "0")

    # ── 3. 최근 배치 속도 (마지막 5개 배치) ──
    RECENT_RATES=$(docker exec kp-ai-service bash -c 'grep "rate=" /tmp/embedding_backfill_v3.log 2>/dev/null | tail -5 | sed "s/.*rate=//;s/ texts.*//"' 2>/dev/null)
    RECENT_MIN=$($PYTHON_CMD -c "
rates = [float(r) for r in '''${RECENT_RATES}'''.strip().split('\n') if r.strip()]
if rates: print(f'{min(rates):.1f}~{max(rates):.1f}')
else: print('N/A')
" 2>/dev/null || echo "N/A")

    # ── 4. 시스템 리소스 ──
    CPU_MEM=$(docker stats kp-ai-service --no-stream --format "{{.CPUPerc}}|{{.MemUsage}}" 2>/dev/null || echo "N/A|N/A")
    CPU_PCT=$(echo "$CPU_MEM" | cut -d'|' -f1)
    MEM_USE=$(echo "$CPU_MEM" | cut -d'|' -f2)

    MEM_INFO=$(free -m 2>/dev/null)
    MEM_AVAIL=$(echo "$MEM_INFO" | grep Mem | awk '{print $7}')
    SWAP_USED=$(echo "$MEM_INFO" | grep Swap | awk '{print $3}')

    # ── 5. ETA 시간 계산 ──
    ETA_HOURS=$($PYTHON_CMD -c "m=int('${P3_ETA}'); print(f'{m/60:.1f}')" 2>/dev/null || echo "?")
    ETA_TIME=$($PYTHON_CMD -c "
from datetime import datetime, timedelta
now = datetime.now()
eta = now + timedelta(minutes=int('${P3_ETA}'))
print(eta.strftime('%H:%M'))
" 2>/dev/null || echo "??:??")

    # ── 6. 완료 체크 ──
    if [ "$ES_EMBEDDED" -ge "$ES_TOTAL" ] 2>/dev/null && [ "$ES_TOTAL" -gt 0 ] 2>/dev/null; then
        SLACK_MSG="*[클로드]* :tada: *Phase 3 임베딩 완료!*\n\n• ES: ${ES_EMBEDDED}/${ES_TOTAL} (100%)\n• 에러: ${P3_ERRORS}건"
        bash "$SEND_SLACK" dev "클로드" "$SLACK_MSG" 2>/dev/null
        echo "[${TIMESTAMP}] COMPLETE! Exiting."
        break
    fi

    DONE=$($PYTHON_CMD -c "print('yes' if int('${ES_EMBEDDED}') / int('${ES_TOTAL}') >= 0.995 else 'no')" 2>/dev/null || echo "no")
    if [ "$DONE" = "yes" ]; then
        SLACK_MSG="*[클로드]* :tada: *Phase 3 임베딩 거의 완료! (99.5%+)*\n\n• ES: ${ES_EMBEDDED}/${ES_TOTAL} (${ES_PCT}%)\n• 에러: ${P3_ERRORS}건"
        bash "$SEND_SLACK" dev "클로드" "$SLACK_MSG" 2>/dev/null
        echo "[${TIMESTAMP}] NEAR COMPLETE (99.5%+). Exiting."
        break
    fi

    # ── 7. 속도 상태 판별 ──
    SPEED_STATUS=$($PYTHON_CMD -c "
r = float('${P3_RATE}')
if r >= 1.0: print(':white_check_mark: 정상')
elif r >= 0.8: print(':warning: 약간 둔화')
else: print(':rotating_light: 둔화')
" 2>/dev/null || echo "N/A")

    # ── 8. 프로그레스 바 ──
    PROGRESS_BAR=$($PYTHON_CMD -c "
pct = float('${ES_PCT}')
filled = int(pct / 5)
bar = '█' * filled + '░' * (20 - filled)
print(bar)
" 2>/dev/null || echo "░░░░░░░░░░░░░░░░░░░░")

    # ── 9. Slack 전송 ──
    SLACK_MSG="*[클로드]* :bar_chart: 임베딩 상태 리포트 #${report_count} (${TIMESTAMP})

*임베딩 진행*
\`${PROGRESS_BAR}\` *${ES_PCT}%*
• ES 완료: *${ES_EMBEDDED} / ${ES_TOTAL}*
• 스크립트: ${P3_EMBEDDED} / ${P3_TOTAL} (${P3_PCT}%)
• 평균 속도: *${P3_RATE} t/s* ${SPEED_STATUS}
• 최근 속도: ${RECENT_MIN} t/s
• 에러: ${P3_ERRORS}건
• ETA: *~${P3_ETA}분 (~${ETA_HOURS}시간, ${ETA_TIME} 완료 예상)*

*시스템*
• CPU: ${CPU_PCT} | 메모리: ${MEM_USE}
• RAM 가용: ${MEM_AVAIL}MB | 스왑: ${SWAP_USED}MB"

    bash "$SEND_SLACK" dev "클로드" "$SLACK_MSG" 2>/dev/null
    echo "[${TIMESTAMP}] Report #${report_count} sent — ES ${ES_PCT}% | ${P3_RATE} t/s | swap ${SWAP_USED}MB"

    sleep $INTERVAL
done
