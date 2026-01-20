#!/bin/bash
# Slack Notification Hook
# 이벤트: Notification
# 용도: 에이전트 작업 알림을 Slack으로 전송

set -e

# stdin에서 JSON 입력 읽기
INPUT=$(cat)

# 환경 변수 확인
if [ -z "$SLACK_WEBHOOK_URL" ]; then
    # Webhook URL이 없으면 조용히 종료 (오류 아님)
    echo '{"continue": true}'
    exit 0
fi

# JSON에서 필요한 정보 추출
TITLE=$(echo "$INPUT" | jq -r '.title // "Claude Code"')
MESSAGE=$(echo "$INPUT" | jq -r '.message // ""')
TYPE=$(echo "$INPUT" | jq -r '.type // "info"')

# 메시지가 없으면 종료
if [ -z "$MESSAGE" ] || [ "$MESSAGE" = "null" ]; then
    echo '{"continue": true}'
    exit 0
fi

# 타입에 따른 이모지 선택
case $TYPE in
    "success") EMOJI=":white_check_mark:" ;;
    "error")   EMOJI=":x:" ;;
    "warning") EMOJI=":warning:" ;;
    *)         EMOJI=":robot_face:" ;;
esac

# Slack 메시지 전송 (백그라운드로 실행하여 블로킹 방지)
send_slack() {
    curl -s -X POST "$SLACK_WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d "{
            \"text\": \"$EMOJI *$TITLE*\n$MESSAGE\",
            \"unfurl_links\": false
        }" > /dev/null 2>&1
}

# 비동기로 전송 (Hook 응답 지연 방지)
send_slack &

# Hook 응답 - 계속 진행
echo '{"continue": true}'
