#!/bin/bash
# ==============================================================================
# send_slack.sh - 표준화된 Slack 메시지 전송 스크립트
# ==============================================================================
# 사용법:
#   ./scripts/send_slack.sh <channel> <agent> <message>
#   ./scripts/send_slack.sh proj-hrkp-standup PM "인사말 내용"
#   ./scripts/send_slack.sh proj-hrkp-dev Backend "작업 시작: SCRUM-10"
#
# 환경 변수 필요:
#   SLACK_BOT_TOKEN - Slack Bot 토큰 (.env에서 로드)
# ==============================================================================

set -e

# 프로젝트 루트 찾기
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# .env 로드
if [ -f "$PROJECT_ROOT/.env" ]; then
    source "$PROJECT_ROOT/.env"
fi

# 인자 확인
if [ $# -lt 3 ]; then
    echo "사용법: $0 <channel> <agent> <message>"
    echo "예시: $0 proj-hrkp-standup PM '좋은 아침입니다!'"
    exit 1
fi

CHANNEL="$1"
AGENT="$2"
MESSAGE="$3"

# 토큰 확인
if [ -z "$SLACK_BOT_TOKEN" ]; then
    echo "오류: SLACK_BOT_TOKEN이 설정되지 않았습니다."
    exit 1
fi

# 구분자 추가 (실제 줄바꿈 문자 사용)
SEPARATOR="───────────────────────"
FULL_MESSAGE="${SEPARATOR}"$'\n'"*[${AGENT}]* ${MESSAGE}"

# JSON 이스케이프 (jq 없이)
escape_json() {
    local str="$1"
    str="${str//\\/\\\\}"      # 백슬래시
    str="${str//\"/\\\"}"      # 따옴표
    str="${str//$'\n'/\\n}"    # 줄바꿈
    str="${str//$'\t'/\\t}"    # 탭
    echo "$str"
}

ESCAPED_MESSAGE=$(escape_json "$FULL_MESSAGE")

# 임시 파일로 JSON 생성 (한글/이모지 안전)
TEMP_FILE=$(mktemp)
cat > "$TEMP_FILE" << EOF
{"channel": "${CHANNEL}", "text": "${ESCAPED_MESSAGE}"}
EOF

# Slack API 호출
RESPONSE=$(curl -s -X POST "https://slack.com/api/chat.postMessage" \
    -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
    -H "Content-Type: application/json; charset=utf-8" \
    -d @"$TEMP_FILE")

# 임시 파일 삭제
rm -f "$TEMP_FILE"

# 결과 확인 (jq 없이 grep 사용)
if echo "$RESPONSE" | grep -q '"ok":true'; then
    echo "✅ 메시지 전송 성공: #${CHANNEL}"
else
    echo "❌ 메시지 전송 실패"
    echo "$RESPONSE" | grep -o '"error":"[^"]*"' || echo "$RESPONSE"
    exit 1
fi
