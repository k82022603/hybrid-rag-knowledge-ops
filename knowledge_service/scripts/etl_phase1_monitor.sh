#!/bin/bash
# ETL Phase 1 v2 모니터링 + Slack 보고 (15분 간격)
# 사용법: nohup bash knowledge_service/scripts/etl_phase1_monitor.sh > /tmp/etl_phase1_monitor.log 2>&1 &

INTERVAL=900  # 15분
REPORT_NUM=1
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
SEND_SLACK="$PROJECT_ROOT/scripts/send_slack.sh"
TOTAL_FILES=1786
PREV_CHUNKS=0
STALE_COUNT=0
LOG_FILE="/tmp/etl_phase1.log"
START_TIME=""

echo "[$(date +'%Y-%m-%d %H:%M KST')] ETL Phase 1 Monitor v2 started (interval=${INTERVAL}s)"

# ETL 시작 시간 추출
START_TIME=$(docker exec kp-ai-service python3 -c "
import re
with open('$LOG_FILE') as f:
    for line in f:
        m = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2})', line)
        if m:
            print(m.group(1))
            break
" 2>/dev/null || echo "")

collect_and_report() {
    local NOW_FULL
    NOW_FULL=$(date +'%H:%M KST')
    local NOW_DATE
    NOW_DATE=$(date +'%Y-%m-%d %H:%M KST')

    # --- 데이터 수집 ---
    local ES_COUNT PG_COUNT SUCCESS SKIPPED FAILED

    ES_COUNT=$(curl -s http://localhost:9200/knowledge_chunks/_count 2>/dev/null \
        | python3 -c "import sys,json; print(json.load(sys.stdin).get('count',0))" 2>/dev/null \
        | tr -d '\n\r ' || echo "0")
    PG_COUNT=$(docker exec kp-postgresql psql -U knowledge -d knowledge -t -c \
        "SELECT count(*) FROM documents;" 2>/dev/null | tr -d '\n\r ' || echo "0")

    SUCCESS=$(docker exec kp-ai-service grep -c "processed successfully" "$LOG_FILE" 2>/dev/null | tr -d '\n\r ' || echo "0")
    SKIPPED=$(docker exec kp-ai-service grep -c "Skipping duplicate" "$LOG_FILE" 2>/dev/null | tr -d '\n\r ' || echo "0")
    FAILED=$(docker exec kp-ai-service grep -c -E "failed after|Parse error" "$LOG_FILE" 2>/dev/null | tr -d '\n\r ' || echo "0")

    SUCCESS=${SUCCESS:-0}; SKIPPED=${SKIPPED:-0}; FAILED=${FAILED:-0}
    ES_COUNT=${ES_COUNT:-0}; PG_COUNT=${PG_COUNT:-0}

    # 현재 처리 중 파일
    local CURRENT_FILE
    CURRENT_FILE=$(docker exec kp-ai-service python3 -c "
import re
with open('$LOG_FILE') as f:
    lines = f.readlines()
for line in reversed(lines):
    cleaned = re.sub(r'\x1b\[[0-9;]*m', '', line.strip())
    if 'Processing file' in cleaned:
        m = re.search(r': (.+?) \(attempt', cleaned)
        if m: print(m.group(1)[:40]); break
" 2>/dev/null || echo "unknown")

    # 시스템 리소스
    local STATS CPU MEM
    STATS=$(docker stats kp-ai-service --no-stream --format "{{.CPUPerc}}|{{.MemUsage}}" 2>/dev/null || echo "?|?")
    CPU=$(echo "$STATS" | cut -d'|' -f1 | tr -d ' ')
    MEM=$(echo "$STATS" | cut -d'|' -f2 | tr -d ' ')
    # MEM을 간결하게 (예: 3.4GiB/10GiB)
    local MEM_USED MEM_TOTAL
    MEM_USED=$(echo "$MEM" | cut -d'/' -f1 | tr -d ' ')
    MEM_TOTAL=$(echo "$MEM" | cut -d'/' -f2 | tr -d ' ')

    # 진행률 계산
    local PROCESSED PCT
    PROCESSED=$((SUCCESS + SKIPPED + FAILED))
    PCT=$(python3 -c "print(round($PROCESSED / $TOTAL_FILES * 100, 1))" 2>/dev/null || echo "0")

    # 프로그레스바 (블록 문자)
    local BAR
    BAR=$(python3 -c "
pct = float('$PCT')
filled = int(pct / 10)
empty = 10 - filled
bar = chr(9608) * filled + chr(9617) * empty
print(bar)
" 2>/dev/null || echo "----------")

    # 경과 시간
    local ELAPSED_STR=""
    if [ -n "$START_TIME" ]; then
        ELAPSED_STR=$(python3 -c "
from datetime import datetime
try:
    start = datetime.strptime('$START_TIME', '%Y-%m-%dT%H:%M')
    now = datetime.now()
    diff = now - start
    hours = int(diff.total_seconds() // 3600)
    mins = int((diff.total_seconds() % 3600) // 60)
    if hours > 0:
        print(f'{hours}h {mins}m')
    else:
        print(f'{mins}m')
except:
    print('?')
" 2>/dev/null || echo "?")
    fi

    # 속도 계산 (files/min)
    local SPEED_STR=""
    if [ -n "$START_TIME" ]; then
        SPEED_STR=$(python3 -c "
from datetime import datetime
try:
    start = datetime.strptime('$START_TIME', '%Y-%m-%dT%H:%M')
    now = datetime.now()
    mins = (now - start).total_seconds() / 60
    if mins > 0:
        speed = $PROCESSED / mins
        print(f'{speed:.1f} files/min')
    else:
        print('calculating...')
except:
    print('?')
" 2>/dev/null || echo "?")
    fi

    # 예상 완료 시간
    local ETA_STR=""
    if [ -n "$START_TIME" ] && [ "$PROCESSED" -gt 0 ] 2>/dev/null; then
        ETA_STR=$(python3 -c "
from datetime import datetime, timedelta
try:
    start = datetime.strptime('$START_TIME', '%Y-%m-%dT%H:%M')
    now = datetime.now()
    elapsed = (now - start).total_seconds()
    remaining = ($TOTAL_FILES - $PROCESSED) * elapsed / $PROCESSED
    eta = now + timedelta(seconds=remaining)
    print(eta.strftime('%H:%M KST'))
except:
    print('?')
" 2>/dev/null || echo "?")
    fi

    # 증감량 + 정체 감지
    local DELTA_STR="--"
    if [ "$PREV_CHUNKS" -gt 0 ] 2>/dev/null; then
        local DELTA=$((ES_COUNT - PREV_CHUNKS))
        DELTA_STR="+${DELTA}"
        if [ "$DELTA" -eq 0 ]; then
            STALE_COUNT=$((STALE_COUNT + 1))
        else
            STALE_COUNT=0
        fi
    fi
    PREV_CHUNKS=$ES_COUNT

    # 3회 연속 변화 없으면 ETL 프로세스 생존 확인
    if [ "$STALE_COUNT" -ge 3 ]; then
        local ETL_ALIVE
        ETL_ALIVE=$(docker top kp-ai-service 2>/dev/null | grep -c "run_etl" || echo "0")
        if [ "$ETL_ALIVE" = "0" ]; then
            local ALERT_MSG=":rotating_light: *[ETL-Monitor]* ETL 프로세스 사망 감지! (${STALE_COUNT}회 연속 변화 없음)\n- ES: ${ES_COUNT} | PG: ${PG_COUNT} | 성공: ${SUCCESS}\n- :warning: ETL 재시작 필요!"
            bash "$SEND_SLACK" alerts "ETL-Monitor" "$ALERT_MSG" 2>/dev/null
            echo "[${NOW_DATE}] ALERT: ETL process dead!"
        fi
    fi

    # ETL 종료 감지
    local ETL_DONE
    ETL_DONE=$(docker exec kp-ai-service python3 -c "
with open('$LOG_FILE') as f:
    content = f.read()
print('yes' if 'Phase 1 Completed' in content or 'ETL Phase 1 complete' in content else 'no')
" 2>/dev/null || echo "no")

    # --- Slack 메시지 구성 ---
    local MSG
    if [ "$ETL_DONE" = "yes" ]; then
        MSG="ETL Phase 1 v2 상태 보고 (${NOW_FULL}) - Report #${REPORT_NUM}\n\n:white_check_mark: *Phase 1 완료!*\n${BAR} 100%  (${PROCESSED}/${TOTAL_FILES})\n:white_check_mark: 성공: ${SUCCESS} | :fast_forward: 스킵: ${SKIPPED} | :x: 실패: ${FAILED}\n:package: ES 청크: ${ES_COUNT} (${DELTA_STR}) | :clipboard: PG 문서: ${PG_COUNT}\n\n:stopwatch: 경과: ${ELAPSED_STR} | 속도: ${SPEED_STR}\n:floppy_disk: 메모리: ${MEM_USED}/${MEM_TOTAL} | CPU: ${CPU}\n\n:tada: Phase 1 완료 -> Phase 2 (Colab GPU 임베딩) 준비"
    else
        MSG="ETL Phase 1 v2 상태 보고 (${NOW_FULL}) - Report #${REPORT_NUM}\n\n:bar_chart: *진행률*: ${BAR} ${PCT}% (${PROCESSED}/${TOTAL_FILES})\n:white_check_mark: 성공: ${SUCCESS} | :fast_forward: 스킵: ${SKIPPED} | :x: 실패: ${FAILED}\n:package: ES 청크: ${ES_COUNT} (${DELTA_STR}) | :clipboard: PG 문서: ${PG_COUNT}\n\n:stopwatch: 경과: ${ELAPSED_STR} | 속도: ${SPEED_STR}\n:crystal_ball: 예상 완료: ${ETA_STR}\n\n:floppy_disk: 메모리: ${MEM_USED}/${MEM_TOTAL} | CPU: ${CPU}\n:page_facing_up: 현재: ${CURRENT_FILE}"
    fi

    # --- Slack 전송 ---
    bash "$SEND_SLACK" dev "Monitor" "$MSG" 2>/dev/null
    local SEND_RESULT=$?

    echo "[${NOW_DATE}] Report #${REPORT_NUM}: ES=${ES_COUNT}(${DELTA_STR}), PG=${PG_COUNT}, ${SUCCESS}ok/${SKIPPED}skip/${FAILED}fail, Send=${SEND_RESULT}"

    REPORT_NUM=$((REPORT_NUM + 1))

    # ETL 완료 시 모니터링 종료
    if [ "$ETL_DONE" = "yes" ]; then
        echo "[${NOW_DATE}] Phase 1 completed. Monitor stopping."
        return 1  # signal to break
    fi
    return 0
}

# 즉시 첫 번째 리포트 전송
collect_and_report
FIRST_RESULT=$?

if [ "$FIRST_RESULT" -ne 0 ]; then
    echo "[$(date +'%Y-%m-%d %H:%M KST')] ETL already completed. Monitor exiting."
    exit 0
fi

# 이후 15분 간격 반복
while true; do
    sleep "$INTERVAL"
    collect_and_report || break
done

echo "[$(date +'%Y-%m-%d %H:%M KST')] ETL Phase 1 Monitor v2 stopped."
