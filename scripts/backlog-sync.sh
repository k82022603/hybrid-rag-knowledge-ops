#!/bin/bash
# PM Backlog Sync Script
# Story 상태 변경 시 Sprint 문서와 Story 파일을 동시에 업데이트
#
# Usage:
#   ./scripts/backlog-sync.sh <STORY_ID> <JIRA_ID> <STATUS> <SPRINT_NUM>
#   ./scripts/backlog-sync.sh STORY-010 SCRUM-10 Done 01
#
# Status: "To Do", "In Progress", "Done"

set -e

# 환경 변수 로드
if [ -f .env ]; then
    source .env
fi

# 인자 검증
if [ $# -lt 4 ]; then
    echo "Usage: $0 <STORY_ID> <JIRA_ID> <STATUS> <SPRINT_NUM>"
    echo "Example: $0 STORY-010 SCRUM-10 Done 01"
    exit 1
fi

STORY_ID=$1      # STORY-010
JIRA_ID=$2       # SCRUM-10
NEW_STATUS=$3    # "In Progress" or "Done"
SPRINT_NUM=$4    # 01

# 파일 경로
SPRINT_FILE="backlog/sprints/sprint-${SPRINT_NUM}.md"
STORY_FILE_PATTERN="backlog/stories/${STORY_ID}-*.md"

echo "=========================================="
echo "[PM] Backlog Sync: ${JIRA_ID} → ${NEW_STATUS}"
echo "=========================================="

# 1. Sprint 문서 존재 확인
if [ ! -f "$SPRINT_FILE" ]; then
    echo "[ERROR] Sprint file not found: $SPRINT_FILE"
    exit 1
fi

# 2. Story 파일 찾기
STORY_FILE_PATH=$(ls $STORY_FILE_PATTERN 2>/dev/null | head -1)
if [ -z "$STORY_FILE_PATH" ]; then
    echo "[WARNING] Story file not found: $STORY_FILE_PATTERN"
fi

# 3. Sprint 문서 업데이트
echo "[1/4] Updating Sprint document..."
if [ "$NEW_STATUS" = "Done" ]; then
    # To Do 또는 In Progress → Done
    sed -i "s/| ${JIRA_ID} |\(.*\)| To Do |/| ${JIRA_ID} |\1| **Done** |/g" "$SPRINT_FILE"
    sed -i "s/| ${JIRA_ID} |\(.*\)| In Progress |/| ${JIRA_ID} |\1| **Done** |/g" "$SPRINT_FILE"
    sed -i "s/| ${JIRA_ID} |\(.*\)| \*\*In Progress\*\* |/| ${JIRA_ID} |\1| **Done** |/g" "$SPRINT_FILE"
elif [ "$NEW_STATUS" = "In Progress" ]; then
    sed -i "s/| ${JIRA_ID} |\(.*\)| To Do |/| ${JIRA_ID} |\1| **In Progress** |/g" "$SPRINT_FILE"
fi
echo "  ✅ Sprint document updated: $SPRINT_FILE"

# 4. Story 파일 업데이트
echo "[2/4] Updating Story file..."
if [ -n "$STORY_FILE_PATH" ] && [ -f "$STORY_FILE_PATH" ]; then
    if [ "$NEW_STATUS" = "Done" ]; then
        sed -i 's/| \*\*Status\*\* | .* |/| **Status** | Done |/' "$STORY_FILE_PATH"
    elif [ "$NEW_STATUS" = "In Progress" ]; then
        sed -i 's/| \*\*Status\*\* | .* |/| **Status** | In Progress |/' "$STORY_FILE_PATH"
    elif [ "$NEW_STATUS" = "To Do" ]; then
        sed -i 's/| \*\*Status\*\* | .* |/| **Status** | To Do |/' "$STORY_FILE_PATH"
    fi
    echo "  ✅ Story file updated: $STORY_FILE_PATH"
else
    echo "  ⚠️ Story file not found, skipping"
fi

# 5. Jira 상태 업데이트 (환경변수가 있을 경우만)
echo "[3/4] Updating Jira status..."
if [ -n "$JIRA_EMAIL" ] && [ -n "$JIRA_API_TOKEN" ]; then
    JIRA_HOST="${JIRA_HOST:-hybridrag.atlassian.net}"

    if [ "$NEW_STATUS" = "In Progress" ]; then
        TRANSITION_ID="21"  # 진행 중
    elif [ "$NEW_STATUS" = "In Review" ]; then
        TRANSITION_ID="31"  # 검토 중
    elif [ "$NEW_STATUS" = "Done" ]; then
        TRANSITION_ID="41"  # 완료
    else
        TRANSITION_ID=""
    fi

    if [ -n "$TRANSITION_ID" ]; then
        RESPONSE=$(curl -sS --connect-timeout 10 -w "%{http_code}" -o /tmp/jira_response.json \
            -X POST "https://${JIRA_HOST}/rest/api/3/issue/${JIRA_ID}/transitions" \
            -u "${JIRA_EMAIL}:${JIRA_API_TOKEN}" \
            -H "Content-Type: application/json" \
            -d "{\"transition\": {\"id\": \"${TRANSITION_ID}\"}}")

        if [ "$RESPONSE" = "204" ] || [ "$RESPONSE" = "200" ]; then
            echo "  ✅ Jira updated: ${JIRA_ID} → ${NEW_STATUS}"
        else
            echo "  ⚠️ Jira update may have failed (HTTP ${RESPONSE})"
        fi
    fi
else
    echo "  ⏭️ Jira update skipped (no credentials)"
fi

# 6. Slack 알림 (환경변수가 있을 경우만)
echo "[4/4] Sending Slack notification..."
if [ -n "$SLACK_BOT_TOKEN" ]; then
    CHANNEL="${SLACK_CHANNEL:-proj-hrkp-dev}"

    if [ "$NEW_STATUS" = "Done" ]; then
        MESSAGE="*[PM]* ✅ Story 완료: ${JIRA_ID} (${STORY_ID})"
    elif [ "$NEW_STATUS" = "In Progress" ]; then
        MESSAGE="*[PM]* 🔄 Story 시작: ${JIRA_ID} (${STORY_ID})"
    else
        MESSAGE="*[PM]* 📋 Story 상태 변경: ${JIRA_ID} → ${NEW_STATUS}"
    fi

    curl -s -X POST "https://slack.com/api/chat.postMessage" \
        -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
        -H "Content-Type: application/json; charset=utf-8" \
        -d "{\"channel\": \"${CHANNEL}\", \"text\": \"${MESSAGE}\"}" > /dev/null

    echo "  ✅ Slack notification sent"
else
    echo "  ⏭️ Slack notification skipped (no token)"
fi

echo ""
echo "=========================================="
echo "[PM] Backlog Sync Complete!"
echo "  - Sprint: sprint-${SPRINT_NUM}.md"
echo "  - Story: ${STORY_ID}"
echo "  - Status: ${NEW_STATUS}"
echo "=========================================="
