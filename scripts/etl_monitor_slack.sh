#!/bin/bash
# ETL 모니터링 + Slack 알림 (15분 간격)
# Usage: ./scripts/etl_monitor_slack.sh

SLACK_CHANNEL="dev"
AGENT_NAME="클로드"
PROGRESS_FILE="/mnt/d/Users/KTDS/Documents/06.과제/hybrid-rag-knowledge-ops/knowledge_data/etl_progress.json"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SEND_SLACK="$SCRIPT_DIR/send_slack.sh"
INTERVAL=900  # 15분 (초)

echo "[ETL Monitor] Started - checking every ${INTERVAL}s (15min)"
echo "[ETL Monitor] Progress file: $PROGRESS_FILE"

check_count=0

while true; do
    check_count=$((check_count + 1))

    if [ ! -f "$PROGRESS_FILE" ]; then
        echo "[ETL Monitor] Progress file not found, waiting..."
        sleep 60
        continue
    fi

    # Read progress
    STATUS=$(python3 -c "import json; d=json.load(open('$PROGRESS_FILE')); print(d.get('status','unknown'))" 2>/dev/null)
    TOTAL=$(python3 -c "import json; d=json.load(open('$PROGRESS_FILE')); print(d.get('total_files',0))" 2>/dev/null)
    SUCCESS=$(python3 -c "import json; d=json.load(open('$PROGRESS_FILE')); print(d.get('success',0))" 2>/dev/null)
    FAILED=$(python3 -c "import json; d=json.load(open('$PROGRESS_FILE')); print(d.get('failed',0))" 2>/dev/null)
    SKIPPED=$(python3 -c "import json; d=json.load(open('$PROGRESS_FILE')); print(d.get('skipped',0))" 2>/dev/null)
    CHUNKS=$(python3 -c "import json; d=json.load(open('$PROGRESS_FILE')); print(d.get('chunks_total',0))" 2>/dev/null)
    ELAPSED=$(python3 -c "import json; d=json.load(open('$PROGRESS_FILE')); print(d.get('elapsed_seconds',0))" 2>/dev/null)
    RATE=$(python3 -c "import json; d=json.load(open('$PROGRESS_FILE')); print(d.get('rate_per_minute',0))" 2>/dev/null)

    PROCESSED=$((SUCCESS + FAILED + SKIPPED))

    if [ "$TOTAL" -gt 0 ] 2>/dev/null; then
        PCT=$((PROCESSED * 100 / TOTAL))
    else
        PCT=0
    fi

    ELAPSED_MIN=$((ELAPSED / 60))

    # DB stats
    PG_DOCS=$(docker-compose exec -T postgresql psql -U knowledge -d knowledge -tAc "SELECT count(*) FROM documents;" 2>/dev/null | tr -d '[:space:]')
    PG_CHUNKS=$(docker-compose exec -T postgresql psql -U knowledge -d knowledge -tAc "SELECT count(*) FROM chunks;" 2>/dev/null | tr -d '[:space:]')
    ES_CHUNKS=$(curl -s "http://localhost:9200/knowledge_chunks/_count" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('count',0))" 2>/dev/null || echo "0")
    NEO4J_NODES=$(curl -s -u neo4j:'neo4j_dev_2026!' -H "Content-Type: application/json" -d '{"statements":[{"statement":"MATCH (n) RETURN count(n) as cnt"}]}' http://localhost:7474/db/neo4j/tx/commit 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['results'][0]['data'][0]['row'][0])" 2>/dev/null || echo "0")

    # CPU/Memory
    CPU_MEM=$(docker stats kp-ai-service --no-stream --format "CPU: {{.CPUPerc}}, MEM: {{.MemUsage}}" 2>/dev/null)

    # Progress bar (20 chars)
    FILLED=$((PCT / 5))
    EMPTY=$((20 - FILLED))
    BAR=$(printf '█%.0s' $(seq 1 $FILLED 2>/dev/null) 2>/dev/null)$(printf '░%.0s' $(seq 1 $EMPTY 2>/dev/null) 2>/dev/null)

    # Format message
    MSG="*[${AGENT_NAME}]* ETL 모니터링 #${check_count} (${ELAPSED_MIN}분 경과)

*진행률*: [${BAR}] ${PCT}% (${PROCESSED}/${TOTAL})
• 성공: ${SUCCESS} | 실패: ${FAILED} | 건너뜀: ${SKIPPED}
• 속도: ${RATE} files/min | 청크: ${CHUNKS}개

*DB 현황*:
• PG: 문서 ${PG_DOCS:-0}건, 청크 ${PG_CHUNKS:-0}건
• ES: 청크 ${ES_CHUNKS:-0}건
• Neo4j: 노드 ${NEO4J_NODES:-0}개

*리소스*: ${CPU_MEM:-N/A}
*상태*: ${STATUS}"

    echo ""
    echo "========================================"
    echo "[ETL Monitor #${check_count}] $(date '+%H:%M:%S')"
    echo "  Status: ${STATUS} | ${PCT}% (${PROCESSED}/${TOTAL})"
    echo "  Success: ${SUCCESS} | Failed: ${FAILED} | Skipped: ${SKIPPED}"
    echo "  PG docs: ${PG_DOCS:-0} | ES chunks: ${ES_CHUNKS:-0} | Neo4j: ${NEO4J_NODES:-0}"
    echo "  ${CPU_MEM:-N/A}"
    echo "========================================"

    # Send Slack
    if [ -f "$SEND_SLACK" ]; then
        bash "$SEND_SLACK" "$SLACK_CHANNEL" "$AGENT_NAME" "$MSG"
    else
        echo "[ETL Monitor] send_slack.sh not found, skipping Slack notification"
    fi

    # Exit if completed
    if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
        echo "[ETL Monitor] ETL ${STATUS}. Final report sent. Exiting."
        break
    fi

    sleep $INTERVAL
done
