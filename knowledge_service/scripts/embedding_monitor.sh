#!/bin/bash
# ============================================================================
# 임베딩 배치 모니터링 스크립트
# ============================================================================
# 용도: embedding_full_cycle.py 배치 프로세스의 진행률을 주기적으로 체크하고
#       Slack으로 자동 보고합니다. OOM Kill 등으로 프로세스가 중단되면 즉시 감지.
#
# 사용법:
#   # 기본 (10분 간격)
#   bash scripts/embedding_monitor.sh
#
#   # 커스텀 간격 (5분)
#   INTERVAL=300 bash scripts/embedding_monitor.sh
#
#   # 백그라운드 실행
#   nohup bash scripts/embedding_monitor.sh > /tmp/embedding_monitor.log 2>&1 &
#
# 환경변수:
#   INTERVAL       - 체크 간격 (초, 기본 600 = 10분)
#   SLACK_CHANNEL  - Slack 채널 ID (기본 C0A9WGCD733 = proj-hrkp-dev)
#   TOTAL_CHUNKS   - 전체 청크 수 (기본 13430)
#   ES_CONTAINER   - ES 접근용 Docker 컨테이너 (기본 kp-ai-service)
#
# 종료 조건:
#   - 임베딩 완료율 >= 99.6% (잔여 50개 미만)
#   - Ctrl+C (수동 종료)
#
# 히스토리:
#   2026-02-09  v1.0  30분 간격 초기 버전 (임시 /tmp/embedding_monitor.sh)
#   2026-02-10  v2.0  10분 간격, 정식 스크립트 등록, OOM 인시던트 대응
# ============================================================================

set -euo pipefail

# --- 설정 ---
INTERVAL="${INTERVAL:-600}"  # 기본 10분
SLACK_TOKEN="${SLACK_BOT_TOKEN:-${SLACK_TOKEN:-}}"
SLACK_CHANNEL="${SLACK_CHANNEL:-C0A9WGCD733}"
TOTAL="${TOTAL_CHUNKS:-13430}"
ES_CONTAINER="${ES_CONTAINER:-kp-ai-service}"

# .env에서 토큰 로드 시도
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
if [ -z "$SLACK_TOKEN" ] && [ -f "${PROJECT_ROOT}/../.env" ]; then
    SLACK_TOKEN=$(grep -E '^SLACK_BOT_TOKEN=' "${PROJECT_ROOT}/../.env" 2>/dev/null | cut -d'=' -f2- || true)
fi

if [ -z "$SLACK_TOKEN" ]; then
    echo "[WARN] SLACK_BOT_TOKEN이 설정되지 않았습니다. Slack 알림이 비활성화됩니다."
    SLACK_ENABLED=false
else
    SLACK_ENABLED=true
fi

# --- 초기 카운트 ---
get_embedding_count() {
    docker exec "$ES_CONTAINER" curl -s "http://elasticsearch:9200/knowledge_chunks/_count" \
        -H 'Content-Type: application/json' \
        -d '{"query":{"exists":{"field":"dense_vector"}}}' 2>/dev/null \
        | python3 -c "import json,sys; print(json.load(sys.stdin)['count'])" 2>/dev/null
}

check_process() {
    # ps가 없는 컨테이너에서도 동작하는 프로세스 체크
    docker exec "$ES_CONTAINER" bash -c '
        for f in /proc/*/cmdline; do
            if cat "$f" 2>/dev/null | tr "\0" " " | grep -q "embedding_full_cycle"; then
                echo "running"
                exit 0
            fi
        done
        echo "stopped"
    ' 2>/dev/null || echo "unknown"
}

send_slack() {
    local msg="$1"
    if [ "$SLACK_ENABLED" = true ]; then
        curl -s -X POST "https://slack.com/api/chat.postMessage" \
            -H "Authorization: Bearer ${SLACK_TOKEN}" \
            -H "Content-Type: application/json; charset=utf-8" \
            -d "{\"channel\": \"${SLACK_CHANNEL}\", \"text\": $(python3 -c "import json; print(json.dumps('''${msg}'''))")}" > /dev/null 2>&1
    fi
}

# --- 시작 ---
PREV_COUNT=$(get_embedding_count 2>/dev/null || echo "0")
INTERVAL_MIN=$((INTERVAL / 60))

echo "================================================================"
echo "  임베딩 배치 모니터링 시작"
echo "  간격: ${INTERVAL_MIN}분 | 전체: ${TOTAL} | 현재: ${PREV_COUNT}"
echo "  Slack: ${SLACK_ENABLED} | 채널: ${SLACK_CHANNEL}"
echo "================================================================"

while true; do
    sleep "$INTERVAL"

    # ES 카운트 조회
    COUNT=$(get_embedding_count 2>/dev/null || echo "")
    if [ -z "$COUNT" ]; then
        echo "[$(date +%H:%M)] ES 조회 실패"
        continue
    fi

    PCT=$(python3 -c "print(f'{${COUNT}/${TOTAL}*100:.1f}')")
    DELTA=$((COUNT - PREV_COUNT))
    REMAIN=$((TOTAL - COUNT))
    TIME_KST=$(date +"%H:%M KST")

    # 프로세스 상태 확인
    PROC_STATUS=$(check_process)
    if [ "$PROC_STATUS" = "running" ]; then
        STATUS="정상 가동 중"
    else
        STATUS="프로세스 중단됨!"
    fi

    # 예상 잔여 시간 계산
    if [ "$DELTA" -gt 0 ]; then
        RATE=$(python3 -c "print(f'{${DELTA}/${INTERVAL}:.1f}')")
        ETA_MIN=$(python3 -c "print(f'{${REMAIN}/(${DELTA}/${INTERVAL})/60:.0f}')")
        ETA_MSG="${ETA_MIN}분 후"
    else
        RATE="0.0"
        ETA_MSG="계산 불가 (증분 없음)"
    fi

    MSG="*[클로드]* 임베딩 배치 진행률 (${TIME_KST})
• ES: *${COUNT} / ${TOTAL}* (${PCT}%) | ${INTERVAL_MIN}분 증분: +${DELTA}
• 속도: ${RATE} chunks/s | 잔여: ${REMAIN}개
• 예상 완료: ${ETA_MSG}
• 상태: ${STATUS}"

    # Slack 전송
    send_slack "$MSG"
    echo "[${TIME_KST}] ES=${COUNT} (+${DELTA}) ${PCT}% - ${STATUS}"

    PREV_COUNT=$COUNT

    # 완료 체크 (99.6% 이상이면 종료)
    if [ "$COUNT" -ge "$((TOTAL - 50))" ]; then
        FINAL_MSG="*[클로드]* 임베딩 배치 거의 완료! (${TIME_KST})
• ES: *${COUNT} / ${TOTAL}* (${PCT}%)
• 모니터링 종료합니다."
        send_slack "$FINAL_MSG"
        echo "[${TIME_KST}] 배치 거의 완료 - 모니터링 종료"
        break
    fi
done
