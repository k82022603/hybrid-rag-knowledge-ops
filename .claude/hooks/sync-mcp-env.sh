#!/bin/bash
# .env 파일의 토큰을 .mcp.json에 자동 동기화
# Usage: .claude/hooks/sync-mcp-env.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"
MCP_FILE="$PROJECT_ROOT/.mcp.json"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "❌ .env 파일이 없습니다"
    exit 1
fi

if [[ ! -f "$MCP_FILE" ]]; then
    echo "❌ .mcp.json 파일이 없습니다"
    exit 1
fi

# .env에서 토큰 읽기
source "$ENV_FILE"

# jq가 있으면 사용, 없으면 sed 사용
if command -v jq &> /dev/null; then
    # jq로 JSON 업데이트
    TMP_FILE=$(mktemp)

    jq --arg token "$JIRA_API_TOKEN" \
       --arg slack_token "${SLACK_BOT_TOKEN:-}" \
       '
       .mcpServers.jira.env.JIRA_API_TOKEN = $token |
       if $slack_token != "" then .mcpServers.slack.env.SLACK_BOT_TOKEN = $slack_token else . end
       ' "$MCP_FILE" > "$TMP_FILE"

    mv "$TMP_FILE" "$MCP_FILE"
    echo "✅ .mcp.json 토큰 동기화 완료 (jq)"
else
    # sed로 간단히 교체 (JIRA만)
    if [[ -n "$JIRA_API_TOKEN" ]]; then
        # 기존 토큰이 있으면 교체, 없으면 추가
        if grep -q "JIRA_API_TOKEN" "$MCP_FILE"; then
            sed -i "s|\"JIRA_API_TOKEN\":.*|\"JIRA_API_TOKEN\": \"$JIRA_API_TOKEN\"|" "$MCP_FILE"
        fi
        echo "✅ JIRA 토큰 동기화 완료 (sed)"
    fi
fi

echo "📋 동기화된 서버: jira"
