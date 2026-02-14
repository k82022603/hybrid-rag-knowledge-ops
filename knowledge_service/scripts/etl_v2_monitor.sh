#!/bin/bash
# ETL v2 모니터링 + Slack 보고 (15분 간격)
# 사용법: nohup bash scripts/etl_v2_monitor.sh > /tmp/etl_v2_monitor.log 2>&1 &

set -uo pipefail

INTERVAL=900  # 15분
REPORT_NUM=2  # 시작 번호 (#1은 이미 보냄)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
SEND_SLACK="$PROJECT_ROOT/scripts/send_slack.sh"
START_TIME="02:48"
TOTAL_FILES=1786
PREV_CHUNKS=0

echo "[$(date +'%Y-%m-%d %H:%M KST')] ETL v2 Monitor started (interval=${INTERVAL}s)"

while true; do
    sleep "$INTERVAL"

    NOW=$(date +'%H:%M')
    NOW_FULL=$(date +'%Y-%m-%d %H:%M KST')

    # --- 데이터 수집 ---
    ES_COUNT=$(curl -s http://localhost:9200/knowledge_chunks/_count 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('count',0))" 2>/dev/null || echo "0")
    PG_COUNT=$(docker exec kp-postgresql psql -U knowledge -d knowledge -t -c "SELECT count(*) FROM documents;" 2>/dev/null | tr -d ' ' || echo "0")
    NEO4J_COUNT=$(docker exec kp-ai-service python3 -c "
from neo4j import GraphDatabase
d=GraphDatabase.driver('bolt://neo4j:7687',auth=('neo4j','neo4j_dev_2026!'))
with d.session() as s:
    print(s.run('MATCH (n) RETURN count(n) AS c').single()['c'])
d.close()
" 2>/dev/null || echo "0")

    # 에러 수
    ERROR_COUNT=$(docker exec kp-ai-service python3 -c "
with open('/tmp/etl_full_v2.log') as f:
    print(sum(1 for l in f if 'ERROR' in l))
" 2>/dev/null || echo "?")

    # 최근 속도
    LAST_RATE=$(docker exec kp-ai-service python3 -c "
import re
with open('/tmp/etl_full_v2.log') as f:
    lines = f.readlines()
embeds = [l for l in lines if 'Batch embed' in l]
if embeds:
    cleaned = re.sub(r'\x1b\[[0-9;]*m', '', embeds[-1])
    m = re.search(r'rate=([0-9.]+)', cleaned)
    print(m.group(1) if m else '?')
else:
    print('?')
" 2>/dev/null || echo "?")

    # 현재 처리 중 파일
    CURRENT_FILE=$(docker exec kp-ai-service python3 -c "
import re
with open('/tmp/etl_full_v2.log') as f:
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
    RAM_AVAIL=$(free -m 2>/dev/null | grep Mem | awk '{print $7}' || echo "?")
    SWAP=$(free -m 2>/dev/null | grep Swap | awk '{print $3}' || echo "?")

    # 진행률 계산
    PCT=$(python3 -c "print(round($PG_COUNT / $TOTAL_FILES * 100, 1))" 2>/dev/null || echo "?")

    # 프로그레스 바 (20칸)
    BAR=$(python3 -c "
filled = int($PCT / 5)
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
with open('/tmp/etl_full_v2.log') as f:
    content = f.read()
print('yes' if 'ETL Pipeline Completed' in content else 'no')
" 2>/dev/null || echo "no")

    # --- Slack 메시지 생성 ---
    if [ "$ETL_DONE" = "yes" ]; then
        MSG=":tada: ETL v2 상태 리포트 #${REPORT_NUM} (${NOW_FULL})

*ETL v2 완료!*
\`\`\`
${BAR} ${PCT}%
\`\`\`
• PG 파일: \`${PG_COUNT} / ${TOTAL_FILES}\`
• ES 청크: \`${ES_COUNT}\`
• Neo4j 엔티티: \`${NEO4J_COUNT}\` nodes
• 에러: \`${ERROR_COUNT}건\`

*시스템*
• CPU: \`${CPU}\` | 메모리: \`${MEM}\`

:white_check_mark: ETL v2 전체 완료!"
    else
        MSG=":bar_chart: ETL v2 상태 리포트 #${REPORT_NUM} (${NOW_FULL})

*ETL v2 진행*
\`\`\`
${BAR} ${PCT}%
\`\`\`
• PG 파일: \`${PG_COUNT} / ${TOTAL_FILES}\` (${PCT}%)
• ES 청크: \`${ES_COUNT}\` (${DELTA_STR})
• Neo4j 엔티티: \`${NEO4J_COUNT}\` nodes
• 최근 속도: \`${LAST_RATE} t/s\`
• 에러: \`${ERROR_COUNT}건\`
• 현재 파일: \`${CURRENT_FILE}\`

*시스템*
• CPU: \`${CPU}\` | 메모리: \`${MEM}\`
• RAM 가용: \`${RAM_AVAIL}MB\` | 스왑: \`${SWAP}MB\`"
    fi

    # --- Slack 전송 ---
    bash "$SEND_SLACK" dev "클로드" "$MSG" 2>/dev/null
    SEND_RESULT=$?

    echo "[${NOW_FULL}] Report #${REPORT_NUM}: ES=${ES_COUNT}(${DELTA_STR}), PG=${PG_COUNT}, Neo4j=${NEO4J_COUNT}, Err=${ERROR_COUNT}, Rate=${LAST_RATE}t/s, Send=${SEND_RESULT}"

    REPORT_NUM=$((REPORT_NUM + 1))

    # ETL 완료 시 모니터링 종료
    if [ "$ETL_DONE" = "yes" ]; then
        echo "[${NOW_FULL}] ETL completed. Monitor stopping."
        break
    fi
done

echo "[$(date +'%Y-%m-%d %H:%M KST')] ETL v2 Monitor stopped."
