#!/bin/bash
# ============================================================================
# 임베딩 헬스체크 + 자동 대응 (30분 간격)
# ============================================================================
# 전문가 3인(Infra/ETL/RAG) 진단 로직을 자동화한 스크립트
#
# 점검 항목:
#   1. 프로세스 생존 여부 → 죽었으면 자동 재시작
#   2. 속도 저하 감지 → swappiness/캐시 자동 조정
#   3. OOM 위험 감지 → 메모리 임계치 알림
#   4. 스왑 과다 사용 → 캐시 클리어
#   5. ES 임베딩 증분 확인 → 정체 시 알림
#
# 사용법:
#   nohup bash scripts/embedding_health_check.sh > /tmp/health_check.log 2>&1 &
#
# 히스토리:
#   2026-02-12 v1.0  전문가 3인 합의 기반 자동 대응 로직
# ============================================================================

set -uo pipefail

SCRIPT_DIR="/mnt/d/Users/KTDS/Documents/06.과제/hybrid-rag-knowledge-ops/scripts"
SEND_SLACK="$SCRIPT_DIR/send_slack.sh"
EMBED_SCRIPT="/app/scripts/run_embedding_backfill_v2.py"
INTERVAL=1800  # 30분
PYTHON_CMD="python3"

# 임계치 설정 (전문가 합의)
SWAP_THRESHOLD_MB=2500    # 스왑 2.5GB 초과 시 캐시 클리어
MEM_AVAIL_MIN_MB=2000     # 가용 메모리 2GB 미만 시 경고
SPEED_MIN=0.3             # 0.3 t/s 미만이면 속도 저하
ES_INCREMENT_MIN=50       # 30분간 임베딩 증분 50건 미만이면 정체

PREV_ES_EMBEDDED=0
check_count=0

echo "[Health Check] Started - 30분 간격 자동 진단/대응"
echo "[Health Check] 임계치: swap>${SWAP_THRESHOLD_MB}MB, avail<${MEM_AVAIL_MIN_MB}MB, speed<${SPEED_MIN}t/s"

while true; do
    check_count=$((check_count + 1))
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    ACTIONS=""
    ALERTS=""

    echo ""
    echo "━━━ [Health Check #${check_count}] ${TIMESTAMP} ━━━"

    # ============================================
    # 1. 프로세스 생존 체크
    # ============================================
    EMBED_PROC=$(docker exec kp-ai-service bash -c 'for p in /proc/[0-9]*/cmdline; do cat "$p" 2>/dev/null | tr "\0" " "; echo; done' 2>/dev/null | grep "embedding_backfill" | grep -v grep | head -1)

    if [ -z "$EMBED_PROC" ]; then
        echo "[ALERT] 임베딩 프로세스 없음! 자동 재시작..."
        ALERTS="${ALERTS}\n:rotating_light: 프로세스 중단 감지 → 자동 재시작"

        # 자동 재시작
        docker exec -d kp-ai-service bash -c "cd /app && nohup python ${EMBED_SCRIPT} > /tmp/embedding_backfill_v2.log 2>&1 &"
        sleep 15

        # 재시작 확인
        RECHECK=$(docker exec kp-ai-service bash -c 'for p in /proc/[0-9]*/cmdline; do cat "$p" 2>/dev/null | tr "\0" " "; echo; done' 2>/dev/null | grep "embedding_backfill" | head -1)
        if [ -n "$RECHECK" ]; then
            ACTIONS="${ACTIONS}\n:white_check_mark: 프로세스 자동 재시작 성공"
            echo "[OK] 재시작 성공"
        else
            ACTIONS="${ACTIONS}\n:x: 프로세스 재시작 실패 - 수동 확인 필요"
            echo "[FAIL] 재시작 실패!"
        fi
    else
        echo "[OK] 프로세스 실행중"
    fi

    # ============================================
    # 2. 메모리/스왑 체크
    # ============================================
    MEM_INFO=$(free -m | grep Mem)
    SWAP_INFO=$(free -m | grep Swap)
    MEM_AVAIL=$(echo "$MEM_INFO" | awk '{print $7}')
    SWAP_USED=$(echo "$SWAP_INFO" | awk '{print $3}')

    echo "[MEM] 가용: ${MEM_AVAIL}MB, 스왑 사용: ${SWAP_USED}MB"

    # 스왑 과다 사용 → 캐시 클리어
    if [ "$SWAP_USED" -gt "$SWAP_THRESHOLD_MB" ] 2>/dev/null; then
        echo "[ACTION] 스왑 ${SWAP_USED}MB > ${SWAP_THRESHOLD_MB}MB → 캐시 클리어"
        echo "claude" | sudo -S sh -c 'sync && echo 3 > /proc/sys/vm/drop_caches' 2>/dev/null
        ACTIONS="${ACTIONS}\n:broom: 스왑 ${SWAP_USED}MB 초과 → 캐시 클리어 실행"
    fi

    # 가용 메모리 부족 경고
    if [ "$MEM_AVAIL" -lt "$MEM_AVAIL_MIN_MB" ] 2>/dev/null; then
        ALERTS="${ALERTS}\n:warning: 가용 메모리 ${MEM_AVAIL}MB < ${MEM_AVAIL_MIN_MB}MB"
        echo "[ALERT] 가용 메모리 부족: ${MEM_AVAIL}MB"
    fi

    # swappiness 체크
    SWAPPINESS=$(cat /proc/sys/vm/swappiness)
    if [ "$SWAPPINESS" -gt 10 ] 2>/dev/null; then
        echo "[ACTION] swappiness=$SWAPPINESS > 10 → 재설정"
        echo "claude" | sudo -S sysctl vm.swappiness=10 2>/dev/null
        ACTIONS="${ACTIONS}\n:gear: swappiness ${SWAPPINESS} → 10 재설정"
    fi

    # ============================================
    # 3. 속도 체크 (etl_progress.json)
    # ============================================
    P3_DATA=$(docker exec kp-ai-service $PYTHON_CMD -c "
import json
try:
    with open('/tmp/etl_progress.json') as f:
        d = json.load(f)
    total = d.get('total_chunks', 0)
    embedded = d.get('embedded', 0)
    errors = d.get('errors', 0)
    rate = round(d.get('rate_texts_per_sec', 0), 2)
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

    echo "[SPEED] ${P3_RATE} t/s | ${P3_EMBEDDED}/${P3_TOTAL} (${P3_PCT}%) | ETA: ${P3_ETA}min | err: ${P3_ERRORS}"

    # 속도 저하 감지
    SLOW=$($PYTHON_CMD -c "print('yes' if float('${P3_RATE}') < ${SPEED_MIN} and float('${P3_RATE}') > 0 else 'no')" 2>/dev/null || echo "no")
    if [ "$SLOW" = "yes" ]; then
        ALERTS="${ALERTS}\n:snail: 속도 저하: ${P3_RATE} t/s < ${SPEED_MIN} t/s"
        echo "[ALERT] 속도 저하 감지: ${P3_RATE} t/s"
    fi

    # ============================================
    # 4. ES 임베딩 증분 체크
    # ============================================
    ES_EMBEDDED=$(docker exec kp-elasticsearch curl -s 'localhost:9200/knowledge_chunks/_count' -H 'Content-Type: application/json' -d '{"query":{"exists":{"field":"dense_vector"}}}' 2>/dev/null | $PYTHON_CMD -c "import sys,json; print(json.load(sys.stdin).get('count',0))" 2>/dev/null || echo "0")
    ES_TOTAL=$(docker exec kp-elasticsearch curl -s 'localhost:9200/knowledge_chunks/_count' 2>/dev/null | $PYTHON_CMD -c "import sys,json; print(json.load(sys.stdin).get('count',0))" 2>/dev/null || echo "0")

    INCREMENT=$((ES_EMBEDDED - PREV_ES_EMBEDDED))
    if [ "$PREV_ES_EMBEDDED" -gt 0 ] && [ "$INCREMENT" -lt "$ES_INCREMENT_MIN" ] 2>/dev/null; then
        ALERTS="${ALERTS}\n:chart_with_downwards_trend: ES 임베딩 증분 ${INCREMENT}건 < ${ES_INCREMENT_MIN}건 (30분간)"
        echo "[ALERT] ES 임베딩 정체: +${INCREMENT}건"
    fi
    PREV_ES_EMBEDDED=$ES_EMBEDDED

    echo "[ES] 임베딩: ${ES_EMBEDDED}/${ES_TOTAL} | 증분: +${INCREMENT}건"

    # ============================================
    # 5. 리소스
    # ============================================
    CPU_MEM=$(docker stats kp-ai-service --no-stream --format "CPU: {{.CPUPerc}}, MEM: {{.MemUsage}}" 2>/dev/null || echo "N/A")
    echo "[RES] ${CPU_MEM}"

    # ============================================
    # 6. 완료 체크
    # ============================================
    if [ "$P3_TOTAL" -gt 0 ] 2>/dev/null; then
        DONE=$($PYTHON_CMD -c "print('yes' if int('${P3_EMBEDDED}') / int('${P3_TOTAL}') >= 0.995 else 'no')" 2>/dev/null || echo "no")
        if [ "$DONE" = "yes" ]; then
            echo "[COMPLETE] Phase 3 완료! (99.5%+)"
            bash "$SEND_SLACK" dev "클로드" ":tada: *Phase 3 임베딩 완료!*\n• 진행: ${P3_EMBEDDED}/${P3_TOTAL}\n• ES: ${ES_EMBEDDED}/${ES_TOTAL}\n• 에러: ${P3_ERRORS}건" 2>/dev/null
            break
        fi
    fi

    # ============================================
    # 7. Slack 보고 (이슈 있을 때만)
    # ============================================
    ES_PCT=$($PYTHON_CMD -c "print(round(int('${ES_EMBEDDED}') * 100 / int('${ES_TOTAL}'), 1)) if int('${ES_TOTAL}') > 0 else print(0)" 2>/dev/null || echo "0")

    if [ -n "$ALERTS" ] || [ -n "$ACTIONS" ]; then
        SLACK_MSG="*[클로드]* :stethoscope: 헬스체크 #${check_count} — 이슈 감지\n\n*상태*: ${P3_RATE} t/s | ${P3_PCT}% | ES ${ES_EMBEDDED}/${ES_TOTAL} (${ES_PCT}%)\n*리소스*: ${CPU_MEM} | 스왑: ${SWAP_USED}MB | 가용: ${MEM_AVAIL}MB"
        [ -n "$ALERTS" ] && SLACK_MSG="${SLACK_MSG}\n\n*알림*:${ALERTS}"
        [ -n "$ACTIONS" ] && SLACK_MSG="${SLACK_MSG}\n\n*자동 대응*:${ACTIONS}"
        bash "$SEND_SLACK" dev "클로드" "$SLACK_MSG" 2>/dev/null
        echo "  Slack alert sent"
    else
        echo "[OK] 이상 없음 - Slack 보고 생략"
    fi

    sleep $INTERVAL
done
