# 개발자 통합 가이드
## Developer Integration Guide - Jira, Slack, GitHub, Claude Code

**버전**: 1.0
**작성일**: 2026-01-18
**목적**: 개발 도구(Jira, Slack, GitHub) 연동 및 Claude Code Agent 활용 가이드

---

## 목차

1. [개요](#1-개요)
2. [GitHub 브랜치 전략](#2-github-브랜치-전략)
3. [Jira 연동 가이드](#3-jira-연동-가이드)
4. [Slack 연동 가이드](#4-slack-연동-가이드)
5. [Claude Code Agent 활용](#5-claude-code-agent-활용)
6. [통합 워크플로우](#6-통합-워크플로우)
7. [트러블슈팅](#7-트러블슈팅)

---

## 1. 개요

### 1.1 통합 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Development Integration                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐               │
│   │    Jira      │     │    GitHub    │     │    Slack     │               │
│   │  (이슈 관리)  │     │  (코드 관리)  │     │   (알림)     │               │
│   └──────┬───────┘     └──────┬───────┘     └──────┬───────┘               │
│          │                    │                    │                        │
│          └────────────────────┼────────────────────┘                        │
│                               │                                             │
│                    ┌──────────┴──────────┐                                  │
│                    │   Claude Code       │                                  │
│                    │   (AI Assistant)    │                                  │
│                    │                     │                                  │
│                    │  ┌───────────────┐  │                                  │
│                    │  │  MCP Servers  │  │                                  │
│                    │  │ - jira        │  │                                  │
│                    │  │ - github      │  │                                  │
│                    │  │ - slack       │  │                                  │
│                    │  └───────────────┘  │                                  │
│                    └─────────────────────┘                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 도구별 역할

| 도구 | 역할 | 연동 방식 |
|------|------|----------|
| **Jira** | 이슈/스프린트 관리 | MCP Server, REST API |
| **GitHub** | 소스 코드 관리, PR, CI/CD | MCP Server, Git CLI |
| **Slack** | 팀 커뮤니케이션, 알림 | MCP Server, Webhook |
| **Claude Code** | AI 개발 지원, 자동화 | CLI, MCP 통합 |

---

## 2. GitHub 브랜치 전략

### 2.1 브랜치 구조

```
main (production)
│
├── develop (integration)
│   │
│   ├── feature/HRKP-123-add-search-api
│   ├── feature/HRKP-124-user-auth
│   └── feature/HRKP-125-dashboard-ui
│
├── release/v1.0.0
├── release/v1.1.0
│
└── hotfix/HRKP-999-critical-fix
```

### 2.2 브랜치 설명

| 브랜치 | 용도 | 소스 | 병합 대상 | 보호 |
|--------|------|------|----------|------|
| `main` | 프로덕션 배포 | release, hotfix | - | Yes |
| `develop` | 개발 통합 | feature | release | Yes |
| `feature/*` | 기능 개발 | develop | develop | No |
| `release/*` | 릴리스 준비 | develop | main, develop | Yes |
| `hotfix/*` | 긴급 버그 수정 | main | main, develop | No |

### 2.3 브랜치 명명 규칙

```bash
# 기능 개발
feature/HRKP-{이슈번호}-{간단한-설명}
feature/HRKP-123-add-vector-search

# 버그 수정
fix/HRKP-{이슈번호}-{간단한-설명}
fix/HRKP-456-search-timeout

# 핫픽스 (긴급)
hotfix/HRKP-{이슈번호}-{간단한-설명}
hotfix/HRKP-999-auth-bypass

# 릴리스
release/v{major}.{minor}.{patch}
release/v1.2.0

# 리팩토링
refactor/HRKP-{이슈번호}-{간단한-설명}
refactor/HRKP-789-cleanup-search-module

# 문서
docs/HRKP-{이슈번호}-{간단한-설명}
docs/HRKP-101-api-documentation
```

### 2.4 워크플로우

#### Feature 개발 플로우

```bash
# 1. develop에서 feature 브랜치 생성
git checkout develop
git pull origin develop
git checkout -b feature/HRKP-123-add-search-api

# 2. 개발 및 커밋
git add .
git commit -m "[FEAT] HRKP-123: Hybrid Search API 구현

- Elasticsearch vector search 추가
- Neo4j graph search 연동
- RRF fusion 알고리즘 적용

관련 이슈: HRKP-123"

# 3. 원격 저장소에 푸시
git push -u origin feature/HRKP-123-add-search-api

# 4. Pull Request 생성 (GitHub 또는 CLI)
gh pr create --base develop --title "[FEAT] HRKP-123: Hybrid Search API" --body "..."

# 5. 코드 리뷰 후 머지
# (GitHub에서 Squash and Merge 권장)

# 6. 로컬 정리
git checkout develop
git pull origin develop
git branch -d feature/HRKP-123-add-search-api
```

#### Release 플로우

```bash
# 1. develop에서 release 브랜치 생성
git checkout develop
git pull origin develop
git checkout -b release/v1.2.0

# 2. 버전 업데이트 및 최종 테스트
# pyproject.toml, package.json 등 버전 수정

# 3. main에 머지
git checkout main
git merge --no-ff release/v1.2.0
git tag -a v1.2.0 -m "Release v1.2.0"
git push origin main --tags

# 4. develop에도 머지 (버전 정보 반영)
git checkout develop
git merge --no-ff release/v1.2.0
git push origin develop

# 5. release 브랜치 삭제
git branch -d release/v1.2.0
git push origin --delete release/v1.2.0
```

#### Hotfix 플로우

```bash
# 1. main에서 hotfix 브랜치 생성
git checkout main
git pull origin main
git checkout -b hotfix/HRKP-999-critical-auth-fix

# 2. 긴급 수정 및 커밋
git add .
git commit -m "[HOTFIX] HRKP-999: 인증 우회 취약점 수정

- JWT 검증 로직 강화
- 세션 타임아웃 추가

관련 이슈: HRKP-999"

# 3. main에 머지 및 태그
git checkout main
git merge --no-ff hotfix/HRKP-999-critical-auth-fix
git tag -a v1.1.1 -m "Hotfix v1.1.1 - Auth vulnerability fix"
git push origin main --tags

# 4. develop에도 머지
git checkout develop
git merge --no-ff hotfix/HRKP-999-critical-auth-fix
git push origin develop

# 5. hotfix 브랜치 삭제
git branch -d hotfix/HRKP-999-critical-auth-fix
```

### 2.5 커밋 메시지 규칙

```
[TYPE] JIRA-ID: 간단한 설명 (50자 이내)

- 상세 변경 사항 1
- 상세 변경 사항 2
- 상세 변경 사항 3

관련 이슈: JIRA-ID
```

**TYPE 종류:**

| Type | 설명 | 예시 |
|------|------|------|
| `[FEAT]` | 새 기능 | 검색 API 추가 |
| `[FIX]` | 버그 수정 | 타임아웃 오류 수정 |
| `[HOTFIX]` | 긴급 수정 | 보안 취약점 패치 |
| `[REFACTOR]` | 리팩토링 | 검색 모듈 재구성 |
| `[DOCS]` | 문서 | API 문서 업데이트 |
| `[TEST]` | 테스트 | 단위 테스트 추가 |
| `[CHORE]` | 빌드/설정 | 의존성 업데이트 |
| `[STYLE]` | 코드 스타일 | 포맷팅 적용 |

### 2.6 Branch Protection Rules

**main 브랜치:**
```yaml
protection_rules:
  - require_pull_request_reviews:
      required_approving_review_count: 2
  - require_status_checks:
      strict: true
      contexts:
        - "CI / test"
        - "CI / build"
        - "CI / security-scan"
  - require_conversation_resolution: true
  - require_signed_commits: false
  - enforce_admins: true
  - allow_force_pushes: false
  - allow_deletions: false
```

**develop 브랜치:**
```yaml
protection_rules:
  - require_pull_request_reviews:
      required_approving_review_count: 1
  - require_status_checks:
      strict: true
      contexts:
        - "CI / test"
        - "CI / lint"
  - require_conversation_resolution: true
```

---

## 3. Jira 연동 가이드

### 3.1 Jira 설정

#### 3.1.1 API 토큰 생성

1. [Atlassian Account](https://id.atlassian.com/manage-profile/security/api-tokens) 접속
2. "Create API token" 클릭
3. 토큰 이름 입력 (예: "Claude Code Integration")
4. 생성된 토큰 복사 및 안전하게 보관

#### 3.1.2 환경 변수 설정

```bash
# .env 파일
JIRA_HOST=your-company.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-api-token
JIRA_PROJECT_KEY=HRKP
```

### 3.2 MCP Server 설정

#### 3.2.1 Claude Code MCP 설정

**~/.claude/settings.json** 또는 **프로젝트/.mcp.json**:

```json
{
  "mcpServers": {
    "jira": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-jira"],
      "env": {
        "JIRA_HOST": "${JIRA_HOST}",
        "JIRA_EMAIL": "${JIRA_EMAIL}",
        "JIRA_API_TOKEN": "${JIRA_API_TOKEN}"
      }
    }
  }
}
```

#### 3.2.2 연결 확인

```bash
# Claude Code에서 Jira 연결 테스트
claude
> /mcp status
> Jira 프로젝트 HRKP의 이슈 목록을 보여줘
```

### 3.3 Jira 사용 가이드

#### 3.3.1 이슈 조회

```bash
# Claude Code 프롬프트 예시

# 이슈 상세 조회
"HRKP-123 이슈 상세 내용을 보여줘"

# 스프린트 이슈 목록
"현재 스프린트의 To Do 이슈들을 보여줘"

# 내 담당 이슈
"내가 담당자인 이슈 목록 조회해줘"

# 검색
"HRKP 프로젝트에서 'search' 관련 이슈 검색해줘"
```

#### 3.3.2 이슈 생성

```bash
# Claude Code 프롬프트 예시

"HRKP 프로젝트에 다음 이슈를 생성해줘:
- 유형: Task
- 제목: Hybrid Search API 구현
- 설명: Elasticsearch와 Neo4j를 통합한 하이브리드 검색 API
- 우선순위: High
- 컴포넌트: Backend"
```

#### 3.3.3 이슈 업데이트

```bash
# 상태 변경
"HRKP-123 이슈 상태를 'In Progress'로 변경해줘"

# 코멘트 추가
"HRKP-123에 다음 코멘트 추가해줘: 'API 설계 완료, 구현 시작'"

# 담당자 변경
"HRKP-123 담당자를 kim@company.com으로 변경해줘"
```

### 3.4 Jira-GitHub 연동

#### 3.4.1 Smart Commits

커밋 메시지에 Jira 이슈 키를 포함하면 자동 연동:

```bash
# 이슈에 커밋 연결
git commit -m "HRKP-123 Implement search API"

# 이슈 상태 변경 (전환 ID 필요)
git commit -m "HRKP-123 #done Implement search API"

# 작업 시간 기록
git commit -m "HRKP-123 #time 2h 30m Implement search API"

# 코멘트 추가
git commit -m "HRKP-123 #comment API 구현 완료"
```

#### 3.4.2 PR 템플릿

**.github/PULL_REQUEST_TEMPLATE.md:**

```markdown
## Summary
<!-- 변경 사항 요약 -->

## Related Issues
<!-- Jira 이슈 링크 -->
- [HRKP-XXX](https://your-company.atlassian.net/browse/HRKP-XXX)

## Changes
- [ ] Feature implementation
- [ ] Unit tests
- [ ] Documentation
- [ ] Integration tests

## Test Plan
<!-- 테스트 방법 -->

## Checklist
- [ ] 코드 리뷰 요청
- [ ] 테스트 통과
- [ ] 문서 업데이트
```

---

## 4. Slack 연동 가이드

### 4.1 Slack App 설정

#### 4.1.1 Slack App 생성

1. [Slack API](https://api.slack.com/apps) 접속
2. "Create New App" > "From scratch"
3. App 이름: "Hybrid RAG Notifications"
4. Workspace 선택

#### 4.1.2 권한 설정 (OAuth Scopes)

**Bot Token Scopes:**
```
chat:write          # 메시지 전송
chat:write.public   # 퍼블릭 채널 메시지
files:write         # 파일 업로드
users:read          # 사용자 정보 조회
channels:read       # 채널 정보 조회
```

#### 4.1.3 토큰 발급

1. "OAuth & Permissions" 메뉴
2. "Install to Workspace" 클릭
3. Bot User OAuth Token 복사 (xoxb-...)

### 4.2 환경 변수 설정

```bash
# .env 파일
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token  # Socket Mode 사용 시
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_CHANNEL_DEV=#dev-notifications
SLACK_CHANNEL_ALERTS=#alerts
```

### 4.3 MCP Server 설정

**~/.claude/settings.json**:

```json
{
  "mcpServers": {
    "slack": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-slack"],
      "env": {
        "SLACK_BOT_TOKEN": "${SLACK_BOT_TOKEN}"
      }
    }
  }
}
```

### 4.4 Slack 사용 가이드

#### 4.4.1 메시지 전송

```bash
# Claude Code 프롬프트 예시

# 간단한 메시지
"#dev-notifications 채널에 '빌드 완료' 메시지 보내줘"

# 포맷팅된 메시지
"#dev-notifications에 다음 내용으로 메시지 보내줘:
- 제목: 배포 완료
- 환경: Staging
- 버전: v1.2.0
- 상태: 성공"
```

#### 4.4.2 알림 자동화

```python
# 빌드 알림 예시 (Python)
import os
from slack_sdk import WebClient

client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])

def send_build_notification(status: str, version: str, details: str):
    """빌드 상태 알림 전송"""
    emoji = ":white_check_mark:" if status == "success" else ":x:"
    color = "#36a64f" if status == "success" else "#ff0000"

    client.chat_postMessage(
        channel=os.environ["SLACK_CHANNEL_DEV"],
        text=f"{emoji} Build {status}: {version}",
        attachments=[
            {
                "color": color,
                "fields": [
                    {"title": "Version", "value": version, "short": True},
                    {"title": "Status", "value": status, "short": True},
                    {"title": "Details", "value": details, "short": False}
                ]
            }
        ]
    )
```

### 4.5 Webhook 설정

#### 4.5.1 Incoming Webhook

1. Slack App > "Incoming Webhooks" 활성화
2. "Add New Webhook to Workspace"
3. 채널 선택
4. Webhook URL 복사

```bash
# .env
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXX
```

#### 4.5.2 Webhook 사용

```bash
# 간단한 알림 전송
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Hello, World!"}' \
  $SLACK_WEBHOOK_URL

# 포맷팅된 메시지
curl -X POST -H 'Content-type: application/json' \
  --data '{
    "blocks": [
      {
        "type": "header",
        "text": {"type": "plain_text", "text": "배포 알림"}
      },
      {
        "type": "section",
        "fields": [
          {"type": "mrkdwn", "text": "*환경:*\nProduction"},
          {"type": "mrkdwn", "text": "*버전:*\nv1.2.0"}
        ]
      }
    ]
  }' \
  $SLACK_WEBHOOK_URL
```

### 4.6 GitHub + Slack 통합

#### 4.6.1 GitHub Slack App

1. Slack에서 GitHub App 설치
2. `/github subscribe owner/repo` 명령어로 구독

```
# Slack에서 GitHub 알림 구독
/github subscribe company/hybrid-rag-knowledge-ops

# 특정 이벤트만 구독
/github subscribe company/hybrid-rag-knowledge-ops pulls,releases,deployments

# 구독 해제
/github unsubscribe company/hybrid-rag-knowledge-ops
```

---

## 5. Claude Code Agent 활용

### 5.1 Agent 목록

| Agent | 역할 | 모델 |
|-------|------|------|
| PM | 요구사항 분석, 스펙 작성 | claude-opus-4-5 |
| TechLead | 아키텍처 검토, 코드 리뷰 | claude-opus-4-5 |
| Backend | SpringBoot 개발 | claude-opus-4-5 |
| Frontend | React UI 개발 | claude-opus-4-5 |
| MLRag | RAG 파이프라인 개발 | claude-opus-4-5 |
| Data | ETL, Knowledge Graph | claude-opus-4-5 |
| QA | 테스트, RAG 평가 | claude-opus-4-5 |
| DevOps | CI/CD, Observability | claude-opus-4-5 |
| Infra | Docker 인프라 | claude-opus-4-5 |

### 5.2 통합 워크플로우 활용

#### 5.2.1 기능 개발 전체 사이클

```bash
# Claude Code에서 실행
/workflows:feature-development HRKP-123 사용자 인증 기능

# 또는 직접 프롬프트
"HRKP-123 사용자 인증 기능을 개발해줘.
1. Jira에서 이슈 상세 정보 확인
2. 기술 설계 검토
3. 코드 구현
4. 테스트 작성
5. PR 생성
6. Slack 알림"
```

#### 5.2.2 코드 리뷰

```bash
/workflows:full-review src/app/services/search_service.py

# 또는
"src/app/services/search_service.py 파일 리뷰해줘.
- 코드 품질
- 보안 취약점
- 성능 문제
- 테스트 커버리지"
```

#### 5.2.3 이슈 기반 작업

```bash
/tools:issue HRKP-123

# 또는
"HRKP-123 이슈를 분석하고 구현해줘.
Jira에서 이슈 정보를 가져와서 작업 계획을 세우고,
완료 후 상태 업데이트와 Slack 알림까지 해줘."
```

### 5.3 MCP 통합 활용

#### 5.3.1 전체 MCP 설정

**~/.claude/settings.json** 또는 **.mcp.json**:

```json
{
  "mcpServers": {
    "jira": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-jira"],
      "env": {
        "JIRA_HOST": "${JIRA_HOST}",
        "JIRA_EMAIL": "${JIRA_EMAIL}",
        "JIRA_API_TOKEN": "${JIRA_API_TOKEN}"
      }
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-github"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    },
    "slack": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-slack"],
      "env": {
        "SLACK_BOT_TOKEN": "${SLACK_BOT_TOKEN}"
      }
    },
    "postgres": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-postgres"],
      "env": {
        "DATABASE_URL": "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:5432/${POSTGRES_DB}"
      }
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-filesystem"],
      "env": {
        "ALLOWED_PATHS": "${PWD}"
      }
    }
  }
}
```

#### 5.3.2 MCP 상태 확인

```bash
# Claude Code에서
/mcp status

# 특정 서버 테스트
"Jira MCP 서버 연결 상태 확인해줘"
"GitHub에서 최근 PR 목록 조회해줘"
"Slack #dev-notifications 채널 접근 가능한지 확인해줘"
```

---

## 6. 통합 워크플로우

### 6.1 스프린트 시작

```bash
# 1. Jira 스프린트 정보 확인
"현재 스프린트 정보와 이슈 목록을 보여줘"

# 2. 담당 이슈 확인
"내가 담당한 이슈 목록과 우선순위를 정리해줘"

# 3. 작업 계획 수립
"이번 스프린트 작업 계획을 세워줘"

# 4. Slack 알림
"#dev-notifications에 스프린트 시작 알림 보내줘"
```

### 6.2 기능 개발

```bash
# 1. 이슈에서 브랜치 생성
"HRKP-123 이슈를 위한 feature 브랜치 생성해줘"

# 2. Jira 상태 업데이트
"HRKP-123 상태를 'In Progress'로 변경해줘"

# 3. 개발 작업
"HRKP-123 요구사항에 맞게 검색 API를 구현해줘"

# 4. 테스트 작성
"구현한 API에 대한 테스트 코드 작성해줘"

# 5. PR 생성
"HRKP-123에 대한 PR을 생성해줘"

# 6. 리뷰 요청 알림
"#code-review 채널에 PR 리뷰 요청 메시지 보내줘"
```

### 6.3 코드 리뷰

```bash
# 1. PR 정보 확인
"PR #42의 변경 사항을 요약해줘"

# 2. 코드 리뷰 수행
"PR #42 코드를 리뷰하고 피드백 코멘트 작성해줘"

# 3. 리뷰 결과 알림
"리뷰 완료 후 Slack으로 결과 알림 보내줘"
```

### 6.4 배포

```bash
# 1. 릴리스 브랜치 생성
"release/v1.2.0 브랜치를 생성하고 버전 업데이트해줘"

# 2. 릴리스 노트 생성
"이번 릴리스 변경 사항으로 릴리스 노트 작성해줘"

# 3. 머지 및 태그
"main에 머지하고 v1.2.0 태그 생성해줘"

# 4. 배포 알림
"#releases 채널에 v1.2.0 배포 완료 알림 보내줘"

# 5. Jira 업데이트
"이번 릴리스에 포함된 이슈들 상태를 'Done'으로 변경해줘"
```

### 6.5 일일 마무리

```bash
# 전체 마무리 워크플로우
/daily:daily-close

# 또는 개별 실행
"오늘 작업 내용을 정리하고:
1. 작업 일지 작성
2. Git 커밋/푸시
3. Jira 이슈 상태 업데이트
4. #dev-daily 채널에 일일 요약 공유"
```

---

## 7. 트러블슈팅

### 7.1 Jira 연결 문제

| 문제 | 원인 | 해결 |
|------|------|------|
| 401 Unauthorized | API 토큰 만료 | 새 토큰 발급 후 환경 변수 업데이트 |
| 403 Forbidden | 권한 부족 | Jira 프로젝트 권한 확인 |
| Connection timeout | 네트워크 문제 | VPN 연결 확인, 프록시 설정 |
| Invalid host | 잘못된 호스트 | JIRA_HOST 형식 확인 (https:// 제외) |

```bash
# 연결 테스트
curl -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  "https://$JIRA_HOST/rest/api/3/myself"
```

### 7.2 Slack 연결 문제

| 문제 | 원인 | 해결 |
|------|------|------|
| invalid_auth | 잘못된 토큰 | 토큰 재발급, Bot Token 사용 확인 |
| channel_not_found | 채널 미존재 | 채널명 확인, Bot 채널 초대 |
| not_in_channel | Bot 미초대 | `/invite @bot-name` 실행 |
| rate_limited | API 제한 | 재시도 로직 구현, 호출 간격 조정 |

```bash
# 연결 테스트
curl -X POST -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"channel":"#test","text":"Hello"}' \
  https://slack.com/api/chat.postMessage
```

### 7.3 GitHub 연결 문제

| 문제 | 원인 | 해결 |
|------|------|------|
| Bad credentials | 토큰 만료 | 새 PAT 발급 |
| Not found | 저장소 접근 권한 | 토큰 scope 확인 |
| Rate limit | API 제한 | 대기 후 재시도 |

```bash
# 연결 테스트
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/user
```

### 7.4 MCP Server 문제

```bash
# MCP 로그 확인
claude --mcp-debug

# 서버 재시작
/mcp restart jira

# 설정 확인
cat ~/.claude/settings.json | jq '.mcpServers'
```

---

## 부록

### A. 환경 변수 체크리스트

```bash
# 필수 환경 변수 확인 스크립트
#!/bin/bash

echo "=== Integration Environment Check ==="

# Jira
[ -z "$JIRA_HOST" ] && echo "[ ] JIRA_HOST" || echo "[x] JIRA_HOST"
[ -z "$JIRA_EMAIL" ] && echo "[ ] JIRA_EMAIL" || echo "[x] JIRA_EMAIL"
[ -z "$JIRA_API_TOKEN" ] && echo "[ ] JIRA_API_TOKEN" || echo "[x] JIRA_API_TOKEN"

# Slack
[ -z "$SLACK_BOT_TOKEN" ] && echo "[ ] SLACK_BOT_TOKEN" || echo "[x] SLACK_BOT_TOKEN"

# GitHub
[ -z "$GITHUB_TOKEN" ] && echo "[ ] GITHUB_TOKEN" || echo "[x] GITHUB_TOKEN"

echo "=== Check Complete ==="
```

### B. 빠른 참조

```bash
# Jira 이슈 조회
"HRKP-123 이슈 보여줘"

# GitHub PR 생성
"feature/HRKP-123 브랜치로 PR 생성해줘"

# Slack 알림
"#dev 채널에 '작업 완료' 메시지 보내줘"

# 통합 작업
"HRKP-123 이슈 작업 완료하고 PR 생성하고 Slack 알림까지 해줘"
```

### C. 참고 자료

- [Jira REST API 문서](https://developer.atlassian.com/cloud/jira/platform/rest/v3/)
- [Slack API 문서](https://api.slack.com/methods)
- [GitHub REST API 문서](https://docs.github.com/en/rest)
- [Claude Code 문서](https://code.claude.com/docs)
- [MCP 문서](https://code.claude.com/docs/en/mcp)

---

**문서 버전**: 1.0
**최종 수정**: 2026-01-18
**관련 문서**:
- [개발 환경 구축 계획서](../01_planning/dev_environment_plan.md)
- [도구 가이드](../../../docs/03_도구_가이드.md)
- [CLAUDE.md](../../../CLAUDE.md)
