#!/bin/bash
# Jira Sync Script - Sprint 재수립 및 이슈 등록
# 실행 전 환경 변수 설정 필요:
#   export JIRA_API_TOKEN="your-api-token"

set -e

# 환경 설정
JIRA_HOST="hybrid-rag-knowledge-ops.atlassian.net"
JIRA_EMAIL="k82022603@gmail.com"
JIRA_PROJECT_KEY="SCRUM"
BOARD_ID="1"

# API Token 확인
if [ -z "$JIRA_API_TOKEN" ]; then
    echo "❌ Error: JIRA_API_TOKEN 환경 변수가 설정되지 않았습니다."
    echo "   export JIRA_API_TOKEN='your-api-token'"
    exit 1
fi

# Base64 인코딩 (인증)
AUTH=$(echo -n "${JIRA_EMAIL}:${JIRA_API_TOKEN}" | base64)

# API 호출 함수
call_jira() {
    local method=$1
    local endpoint=$2
    local data=$3
    
    if [ -z "$data" ]; then
        curl -s -X "$method" \
            -H "Authorization: Basic $AUTH" \
            -H "Content-Type: application/json" \
            "https://${JIRA_HOST}/rest/api/3/${endpoint}"
    else
        curl -s -X "$method" \
            -H "Authorization: Basic $AUTH" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "https://${JIRA_HOST}/rest/api/3/${endpoint}"
    fi
}

# Agile API 호출 함수
call_jira_agile() {
    local method=$1
    local endpoint=$2
    local data=$3
    
    if [ -z "$data" ]; then
        curl -s -X "$method" \
            -H "Authorization: Basic $AUTH" \
            -H "Content-Type: application/json" \
            "https://${JIRA_HOST}/rest/agile/1.0/${endpoint}"
    else
        curl -s -X "$method" \
            -H "Authorization: Basic $AUTH" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "https://${JIRA_HOST}/rest/agile/1.0/${endpoint}"
    fi
}

echo "╔════════════════════════════════════════════════╗"
echo "║       Jira Sprint 재수립 및 이슈 동기화          ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

# Step 1: SCRUM-9 (Epic) - Infrastructure Setup 생성
echo "📦 Step 1: Infrastructure Epic 생성..."
EPIC_RESPONSE=$(call_jira POST "issue" '{
    "fields": {
        "project": {"key": "SCRUM"},
        "summary": "Infrastructure Setup",
        "description": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "Docker Compose 기반 18개 컨테이너 환경 구축. Keycloak 인증, PostgreSQL/Neo4j/Elasticsearch 데이터베이스 초기화, 프로젝트 골격 생성까지 개발 환경 전체 구성."
                        }
                    ]
                }
            ]
        },
        "issuetype": {"name": "Epic"}
    }
}')
EPIC_KEY=$(echo $EPIC_RESPONSE | jq -r '.key')
echo "   ✅ Created: $EPIC_KEY (Infrastructure Setup)"

# Step 2: SCRUM-10 (Story) - Docker Compose 환경 구성
echo ""
echo "📝 Step 2: Infrastructure Stories 생성..."
STORY_10=$(call_jira POST "issue" '{
    "fields": {
        "project": {"key": "SCRUM"},
        "summary": "Docker Compose 환경 구성",
        "description": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "As a 개발자, I want 단일 명령어로 전체 개발 환경을 기동할 수 있기를, So that 로컬에서 통합 테스트를 수행할 수 있다"
                        }
                    ]
                }
            ]
        },
        "issuetype": {"name": "Story"},
        "customfield_10014": "'$EPIC_KEY'"
    }
}')
STORY_10_KEY=$(echo $STORY_10 | jq -r '.key')
echo "   ✅ Created: $STORY_10_KEY (Docker Compose 환경 구성)"

# Step 3: SCRUM-11 (Story) - 데이터베이스 초기화
STORY_11=$(call_jira POST "issue" '{
    "fields": {
        "project": {"key": "SCRUM"},
        "summary": "데이터베이스 초기화",
        "description": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "As a 개발자, I want 데이터베이스 스키마가 자동으로 초기화되기를, So that 별도 설정 없이 개발을 시작할 수 있다"
                        }
                    ]
                }
            ]
        },
        "issuetype": {"name": "Story"},
        "customfield_10014": "'$EPIC_KEY'"
    }
}')
STORY_11_KEY=$(echo $STORY_11 | jq -r '.key')
echo "   ✅ Created: $STORY_11_KEY (데이터베이스 초기화)"

# Step 4: SCRUM-12 (Story) - 인증 인프라 (Keycloak)
STORY_12=$(call_jira POST "issue" '{
    "fields": {
        "project": {"key": "SCRUM"},
        "summary": "인증 인프라 (Keycloak)",
        "description": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "As a 개발자, I want OAuth 2.0 기반 인증 시스템이 설정되어 있기를, So that 보안이 적용된 API를 개발할 수 있다"
                        }
                    ]
                }
            ]
        },
        "issuetype": {"name": "Story"},
        "customfield_10014": "'$EPIC_KEY'"
    }
}')
STORY_12_KEY=$(echo $STORY_12 | jq -r '.key')
echo "   ✅ Created: $STORY_12_KEY (인증 인프라)"

# Step 5: SCRUM-13 (Story) - 프로젝트 골격 생성
STORY_13=$(call_jira POST "issue" '{
    "fields": {
        "project": {"key": "SCRUM"},
        "summary": "프로젝트 골격 생성",
        "description": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "As a 개발자, I want 각 서비스의 프로젝트 골격이 미리 준비되어 있기를, So that 즉시 기능 개발을 시작할 수 있다"
                        }
                    ]
                }
            ]
        },
        "issuetype": {"name": "Story"},
        "customfield_10014": "'$EPIC_KEY'"
    }
}')
STORY_13_KEY=$(echo $STORY_13 | jq -r '.key')
echo "   ✅ Created: $STORY_13_KEY (프로젝트 골격 생성)"

# Step 6: SCRUM-14 (Story) - 개발 환경 가이드
STORY_14=$(call_jira POST "issue" '{
    "fields": {
        "project": {"key": "SCRUM"},
        "summary": "개발 환경 가이드",
        "description": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "As a 신규 개발자, I want 상세한 개발 환경 설정 가이드가 있기를, So that 빠르게 개발 환경을 구축하고 프로젝트에 참여할 수 있다"
                        }
                    ]
                }
            ]
        },
        "issuetype": {"name": "Story"},
        "customfield_10014": "'$EPIC_KEY'"
    }
}')
STORY_14_KEY=$(echo $STORY_14 | jq -r '.key')
echo "   ✅ Created: $STORY_14_KEY (개발 환경 가이드)"

# Step 7: Sprint 02 생성
echo ""
echo "🏃 Step 3: Sprint 02 생성..."
SPRINT_02=$(call_jira_agile POST "sprint" '{
    "name": "Sprint 02",
    "startDate": "2026-02-03T09:00:00.000+09:00",
    "endDate": "2026-02-14T18:00:00.000+09:00",
    "originBoardId": '$BOARD_ID',
    "goal": "문서 업로드부터 Semantic Chunking까지의 ETL 파이프라인 1단계 완성"
}')
SPRINT_02_ID=$(echo $SPRINT_02 | jq -r '.id')
echo "   ✅ Created: Sprint 02 (ID: $SPRINT_02_ID)"

# Step 8: SCRUM-6, 7, 8을 Sprint 01에서 제거하고 Sprint 02로 이동
echo ""
echo "🔄 Step 4: 문서처리 Story를 Sprint 02로 이동..."
# Sprint 01 ID = 3
call_jira_agile POST "sprint/$SPRINT_02_ID/issue" '{"issues": ["SCRUM-6", "SCRUM-7", "SCRUM-8"]}' > /dev/null
echo "   ✅ Moved: SCRUM-6, SCRUM-7, SCRUM-8 → Sprint 02"

# Step 9: 인프라 Story들을 Sprint 01에 할당
echo ""
echo "📌 Step 5: 인프라 Story를 Sprint 01에 할당..."
call_jira_agile POST "sprint/3/issue" '{"issues": ["'$STORY_10_KEY'", "'$STORY_11_KEY'", "'$STORY_12_KEY'", "'$STORY_13_KEY'", "'$STORY_14_KEY'"]}' > /dev/null
echo "   ✅ Assigned to Sprint 01: $STORY_10_KEY, $STORY_11_KEY, $STORY_12_KEY, $STORY_13_KEY, $STORY_14_KEY"

# 결과 요약
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "                        📊 결과 요약                             "
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📦 생성된 Epic:"
echo "   - $EPIC_KEY: Infrastructure Setup"
echo ""
echo "📝 생성된 Story:"
echo "   - $STORY_10_KEY: Docker Compose 환경 구성"
echo "   - $STORY_11_KEY: 데이터베이스 초기화"
echo "   - $STORY_12_KEY: 인증 인프라 (Keycloak)"
echo "   - $STORY_13_KEY: 프로젝트 골격 생성"
echo "   - $STORY_14_KEY: 개발 환경 가이드"
echo ""
echo "🏃 Sprint 할당:"
echo "   Sprint 01 (2026-01-20 ~ 01-31): 인프라"
echo "     - $STORY_10_KEY, $STORY_11_KEY, $STORY_12_KEY, $STORY_13_KEY, $STORY_14_KEY"
echo ""
echo "   Sprint 02 (2026-02-03 ~ 02-14): 문서처리"
echo "     - SCRUM-6, SCRUM-7, SCRUM-8"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 생성된 ID 출력 (문서 동기화용)
echo ""
echo "📋 문서 동기화용 정보:"
echo "EPIC_KEY=$EPIC_KEY"
echo "STORY_10_KEY=$STORY_10_KEY"
echo "STORY_11_KEY=$STORY_11_KEY"
echo "STORY_12_KEY=$STORY_12_KEY"
echo "STORY_13_KEY=$STORY_13_KEY"
echo "STORY_14_KEY=$STORY_14_KEY"
echo "SPRINT_02_ID=$SPRINT_02_ID"
