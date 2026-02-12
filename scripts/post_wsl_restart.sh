#!/bin/bash
# ============================================================================
# WSL2 재시작 후 임베딩 파이프라인 복구 스크립트
# ============================================================================
# 사용법: bash scripts/post_wsl_restart.sh
#
# 실행 조건: WSL2 재시작 후 (.wslconfig 변경: 4코어→8코어, 12GB→14GB)
# 생성일: 2026-02-12 22:54 KST
# ============================================================================

set -uo pipefail

PROJECT_DIR="/mnt/d/Users/KTDS/Documents/06.과제/hybrid-rag-knowledge-ops"
SCRIPT_DIR="$PROJECT_DIR/scripts"
COMPOSE_DIR="$PROJECT_DIR/infrastructure/docker"

echo "━━━ WSL2 재시작 후 복구 시작 ━━━"
echo "시간: $(date '+%Y-%m-%d %H:%M:%S')"

# ============================================
# 1. WSL2 설정 확인
# ============================================
echo ""
echo "[1/6] WSL2 설정 확인..."
NPROC=$(nproc)
MEM_TOTAL=$(free -m | awk '/Mem:/{print $2}')
echo "  CPU 코어: ${NPROC}개"
echo "  메모리: ${MEM_TOTAL}MB"

if [ "$NPROC" -lt 6 ]; then
    echo "  [WARN] CPU가 ${NPROC}코어 — .wslconfig 적용 확인 필요"
fi

# ============================================
# 2. Docker 시작 대기
# ============================================
echo ""
echo "[2/6] Docker 데몬 대기..."
for i in $(seq 1 30); do
    if docker info &>/dev/null; then
        echo "  Docker 준비 완료 (${i}초)"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "  [ERROR] Docker 시작 실패 — Docker Desktop 확인 필요"
        exit 1
    fi
    sleep 2
done

# ============================================
# 3. 필수 컨테이너만 시작 (임베딩에 필요한 것만)
# ============================================
echo ""
echo "[3/6] 필수 컨테이너 시작 (ai-service, elasticsearch, postgresql)..."
cd "$COMPOSE_DIR"
docker compose up -d ai-service elasticsearch postgresql
echo "  컨테이너 헬스체크 대기 (최대 120초)..."

for i in $(seq 1 60); do
    ES_HEALTH=$(docker inspect --format='{{.State.Health.Status}}' kp-elasticsearch 2>/dev/null || echo "starting")
    AI_HEALTH=$(docker inspect --format='{{.State.Health.Status}}' kp-ai-service 2>/dev/null || echo "starting")

    if [ "$ES_HEALTH" = "healthy" ] && [ "$AI_HEALTH" = "healthy" ]; then
        echo "  모든 컨테이너 healthy (${i}x2초)"
        break
    fi

    if [ "$i" -eq 60 ]; then
        echo "  [WARN] 타임아웃 — 현재 상태: ES=$ES_HEALTH, AI=$AI_HEALTH"
        echo "  계속 진행합니다..."
    fi
    sleep 2
done

# ============================================
# 4. swappiness 설정
# ============================================
echo ""
echo "[4/6] 시스템 튜닝..."
echo "claude" | sudo -S sysctl vm.swappiness=1 2>/dev/null
echo "  swappiness=1 설정 완료"

# ============================================
# 5. 임베딩 프로세스 재시작
# ============================================
echo ""
echo "[5/6] 임베딩 프로세스 시작..."
EMBED_PROC=$(docker exec kp-ai-service bash -c 'for p in /proc/[0-9]*/cmdline; do cat "$p" 2>/dev/null | tr "\0" " "; echo; done' 2>/dev/null | grep "embedding_backfill" | grep -v grep | head -1)

if [ -n "$EMBED_PROC" ]; then
    echo "  이미 실행 중 — 스킵"
else
    docker exec -d kp-ai-service bash -c "cd /app && nohup python3 /app/scripts/run_embedding_backfill_v2.py > /tmp/embedding_backfill_v2.log 2>&1 &"
    sleep 15

    RECHECK=$(docker exec kp-ai-service bash -c 'for p in /proc/[0-9]*/cmdline; do cat "$p" 2>/dev/null | tr "\0" " "; echo; done' 2>/dev/null | grep "embedding_backfill" | head -1)
    if [ -n "$RECHECK" ]; then
        echo "  임베딩 프로세스 시작 성공"
    else
        echo "  [ERROR] 임베딩 프로세스 시작 실패 — 수동 확인 필요"
    fi
fi

# ============================================
# 6. 모니터링 스크립트 재시작
# ============================================
echo ""
echo "[6/6] 모니터링 스크립트 시작..."
cd "$PROJECT_DIR"

# 기존 모니터 프로세스 정리
pkill -f "etl_monitor_v3.sh" 2>/dev/null
pkill -f "embedding_health_check.sh" 2>/dev/null
sleep 2

# 모니터 재시작
nohup bash "${PROJECT_DIR}/knowledge_service/scripts/etl_monitor_v3.sh" > /tmp/etl_monitor_v3.log 2>&1 &
MON_PID=$!
echo "  ETL 모니터 시작: PID $MON_PID"

nohup bash "${PROJECT_DIR}/knowledge_service/scripts/embedding_health_check.sh" > /tmp/health_check.log 2>&1 &
HC_PID=$!
echo "  헬스체크 시작: PID $HC_PID"

# ============================================
# 결과 요약
# ============================================
echo ""
echo "━━━ 복구 완료 ━━━"
echo "시간: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
echo "CPU: $(nproc)코어 | RAM: $(free -m | awk '/Mem:/{print $2}')MB | Swap: $(free -m | awk '/Swap:/{print $3}')MB used"
echo ""
echo "다음 확인:"
echo "  docker exec kp-ai-service tail -5 /tmp/embedding_backfill_v2.log"
echo "  tail -5 /tmp/health_check.log"
echo ""
echo "임베딩 진행률은 약 30초 후부터 로그에 표시됩니다."
