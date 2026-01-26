#!/bin/bash
# ==============================================================================
# Slack 메시지 전송 스크립트 (서브 에이전트용)
# ==============================================================================
#
# 용도: Task 서브 에이전트가 MCP Slack에 접근할 수 없을 때 사용
#       메인 클로드는 MCP Slack 도구를 직접 사용
#
# 사용법:
#   ./scripts/send_slack.sh <channel_name> <agent_name> <message>
#
# 예시:
#   ./scripts/send_slack.sh dev Backend "작업 시작: STORY-022 JWT Auth Filter"
#   ./scripts/send_slack.sh standup QA "안녕하세요! 테스트 준비 완료"
#   ./scripts/send_slack.sh alerts Infra "컨테이너 장애 감지: kp-backend"
#
# 채널 매핑:
#   dev     → proj-hrkp-dev     (C0A9WGCD733)
#   standup → proj-hrkp-standup (C0A9B7HDEUB)
#   alerts  → proj-hrkp-alerts  (C0A9WGEVB97)
#   general → proj-hrkp-general (C0AABTM716U)
#
# Updated: 2026-01-26 v2.0 - 혼합 방식 (MCP + Shell)
# ==============================================================================

set -euo pipefail

# --- UTF-8 인코딩 강제 (Windows Git Bash 한글 깨짐 방지) ---
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export PYTHONIOENCODING=utf-8

# --- 인자 확인 ---
if [ $# -lt 3 ]; then
    echo "Usage: $0 <channel> <agent_name> <message>"
    echo ""
    echo "Channels: dev, standup, alerts, general"
    echo "Example: $0 dev Backend \"작업 완료: AuthController 구현\""
    exit 1
fi

CHANNEL_NAME="$1"
AGENT_NAME="$2"
MESSAGE="$3"

# --- .env 로드 ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

if [ -f "$PROJECT_ROOT/.env" ]; then
    # shellcheck source=/dev/null
    source "$PROJECT_ROOT/.env"
fi

if [ -z "${SLACK_BOT_TOKEN:-}" ]; then
    echo "ERROR: SLACK_BOT_TOKEN not set. Check .env file."
    exit 1
fi

# --- 채널 매핑 ---
declare -A CHANNELS=(
    ["dev"]="C0A9WGCD733"
    ["standup"]="C0A9B7HDEUB"
    ["alerts"]="C0A9WGEVB97"
    ["general"]="C0AABTM716U"
)

CHANNEL_ID="${CHANNELS[$CHANNEL_NAME]:-}"

if [ -z "$CHANNEL_ID" ]; then
    echo "ERROR: Unknown channel '$CHANNEL_NAME'. Use: dev, standup, alerts, general"
    exit 1
fi

# --- 메시지 포맷팅 ---
FORMATTED_TEXT="*[$AGENT_NAME]* $MESSAGE"

# --- JSON 안전 이스케이프 (Windows/Linux 호환) ---
# python 또는 python3 자동 감지
PYTHON_CMD=""
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
fi

# JSON payload를 임시 파일로 작성 (인코딩 안전)
TMPFILE=$(mktemp /tmp/slack_msg_XXXXXX.json 2>/dev/null || mktemp)

if [ -n "$PYTHON_CMD" ]; then
    $PYTHON_CMD -c "
import json, sys
text = sys.argv[1]
# literal \n을 실제 줄바꿈으로 변환
text = text.replace(r'\n', '\n')
payload = json.dumps({'channel': sys.argv[2], 'text': text}, ensure_ascii=False)
with open(sys.argv[3], 'w', encoding='utf-8') as f:
    f.write(payload)
" "$FORMATTED_TEXT" "$CHANNEL_ID" "$TMPFILE"
else
    # python 없을 경우 fallback (sed 기반)
    ESCAPED_TEXT=$(printf '%s' "$FORMATTED_TEXT" | sed 's/\\/\\\\/g; s/"/\\"/g; s/\t/\\t/g' | tr '\n' ' ')
    printf '{"channel": "%s", "text": "%s"}' "$CHANNEL_ID" "$ESCAPED_TEXT" > "$TMPFILE"
fi

# --- Slack API 호출 (파일에서 payload 읽기) ---
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "https://slack.com/api/chat.postMessage" \
    -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
    -H "Content-Type: application/json; charset=utf-8" \
    -d @"$TMPFILE")

# 임시 파일 정리
rm -f "$TMPFILE"

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -n -1)

# --- 결과 확인 ---
if [ "$HTTP_CODE" = "200" ]; then
    OK=$(echo "$BODY" | $PYTHON_CMD -c "import sys,json; print(json.loads(sys.stdin.read()).get('ok', False))" 2>/dev/null || echo "unknown")
    if [ "$OK" = "True" ]; then
        echo "OK: Message sent to #proj-hrkp-$CHANNEL_NAME"
    else
        ERROR=$(echo "$BODY" | $PYTHON_CMD -c "import sys,json; print(json.loads(sys.stdin.read()).get('error', 'unknown'))" 2>/dev/null || echo "unknown")
        echo "ERROR: Slack API error: $ERROR"
        exit 1
    fi
else
    echo "ERROR: HTTP $HTTP_CODE"
    exit 1
fi
