#!/bin/bash
# ==============================================================================
# 엔티티 추출 배치 모니터링 + Slack 알림 (15분 간격)
# ==============================================================================
# 사용법:
#   ./scripts/entity_monitor_slack.sh &
#   # 종료: kill $(cat /tmp/entity_monitor.pid)
# ==============================================================================

INTERVAL=900  # 15분
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TOTAL_CHUNKS=16185

echo $$ > /tmp/entity_monitor.pid
echo "[Monitor] Started (PID: $$, interval: ${INTERVAL}s)"

while true; do
    # 진행 상황 수집
    STATS=$(docker exec kp-ai-service python3 -c "
import json, sys
all_ids = set()
total_entities = 0
total_rels = 0
total_errors = 0
for wid in [0, 1]:
    try:
        with open(f'/tmp/entity_checkpoint_tc100_w{wid}.json') as f:
            d = json.load(f)
        all_ids |= set(d['processed_ids'])
        total_entities += d['stats']['total_entities']
        total_rels += d['stats']['total_relationships']
        total_errors += d['stats']['total_errors']
    except:
        pass
unique = len(all_ids)
pct = unique / ${TOTAL_CHUNKS} * 100
remaining = ${TOTAL_CHUNKS} - unique
print(f'{unique}|{pct:.1f}|{remaining}|{total_entities}|{total_rels}|{total_errors}')
" 2>/dev/null)

    if [ -z "$STATS" ]; then
        echo "[Monitor] Failed to get stats"
        sleep $INTERVAL
        continue
    fi

    IFS='|' read -r PROCESSED PCT REMAINING ENTITIES RELS ERRORS <<< "$STATS"

    # Neo4j 메모리
    NEO4J_MEM=$(docker stats --no-stream --format "{{.MemUsage}}" kp-neo4j 2>/dev/null)

    # 프로세스 확인
    RUNNING=$(docker exec kp-ai-service python3 -c "
import os
count = 0
for pid_dir in os.listdir('/proc'):
    if not pid_dir.isdigit(): continue
    try:
        with open(f'/proc/{pid_dir}/cmdline', 'r') as f:
            if 'batch_entity' in f.read():
                count += 1
    except: pass
print(count)
" 2>/dev/null)

    TIMESTAMP=$(date +"%H:%M")
    MSG="*[클로드]* Entity Extraction 진행 (${TIMESTAMP})
> 처리: ${PROCESSED}/${TOTAL_CHUNKS} (${PCT}%) | 잔여: ${REMAINING}
> 엔티티: ${ENTITIES} | 관계: ${RELS} | 에러: ${ERRORS}
> Workers: ${RUNNING} | Neo4j: ${NEO4J_MEM}"

    # Slack 전송
    "$SCRIPT_DIR/send_slack.sh" dev "클로드" "$MSG" 2>/dev/null

    echo "[Monitor] ${TIMESTAMP} - ${PROCESSED}/${TOTAL_CHUNKS} (${PCT}%)"

    # 완료 체크
    if [ "$PROCESSED" -ge "$TOTAL_CHUNKS" ] 2>/dev/null; then
        DONE_MSG="*[클로드]* Entity Extraction 완료!
> 총 처리: ${PROCESSED}건 | 엔티티: ${ENTITIES} | 관계: ${RELS} | 에러: ${ERRORS}"
        "$SCRIPT_DIR/send_slack.sh" dev "클로드" "$DONE_MSG" 2>/dev/null
        echo "[Monitor] COMPLETE! Exiting."
        rm -f /tmp/entity_monitor.pid
        exit 0
    fi

    # 워커 사망 감지
    if [ "$RUNNING" = "0" ] && [ "$PROCESSED" -lt "$TOTAL_CHUNKS" ] 2>/dev/null; then
        ALERT_MSG="*[클로드]* :warning: Entity Extraction 워커 중단 감지!
> 처리: ${PROCESSED}/${TOTAL_CHUNKS} (${PCT}%) | 워커: 0개 실행 중"
        "$SCRIPT_DIR/send_slack.sh" alerts "클로드" "$ALERT_MSG" 2>/dev/null
        echo "[Monitor] WARNING: No workers running!"
    fi

    sleep $INTERVAL
done
