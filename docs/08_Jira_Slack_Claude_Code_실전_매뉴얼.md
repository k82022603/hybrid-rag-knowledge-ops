# Jira & Slack & Claude Code 실전 매뉴얼

Jira/Slack 계정 생성부터 Claude Code를 통한 자동화까지 실전 과정 가이드

**Version**: 1.6 | **Updated**: 2026-01-20
**기반**: 2026-01-19~20 실제 구축 세션

---

## 목차

1. [개요](#1-개요)
2. [Jira 계정 및 프로젝트 생성](#2-jira-계정-및-프로젝트-생성)
3. [Slack 워크스페이스 생성](#3-slack-워크스페이스-생성)
4. [Jira-Slack 연동](#4-jira-slack-연동)
5. [Claude Code 환경 설정](#5-claude-code-환경-설정)
6. [Claude Code로 Jira 자동화](#6-claude-code로-jira-자동화)
7. [백로그 → Jira 동기화](#7-백로그--jira-동기화)
8. [가상 팀원 Slack 자동화](#8-가상-팀원-slack-자동화)
9. [GitHub MCP 설정](#9-github-mcp-설정)
10. [Agent Mail & Beads 검토](#10-agent-mail--beads-검토)
11. [트러블슈팅](#11-트러블슈팅)
12. [Quick Reference](#12-quick-reference)
13. [Sprint 실행 가이드](#13-sprint-실행-가이드)
14. [PM 중심 워크플로우 테스트](#14-pm-중심-워크플로우-테스트) ⭐ NEW

---

## 1. 개요

### 1.1 이 문서의 목적

Jira/Slack 계정이 없는 상태에서 시작하여, Claude Code를 통해 Jira 이슈를 자동 생성하고 백로그를 동기화하는 전체 과정을 실전 경험 기반으로 안내합니다.

### 1.2 구축 아키텍처

```mermaid
flowchart TB
    subgraph Tools["협업 도구"]
        Jira["Jira Cloud<br/>이슈/스프린트 관리"]
        Slack["Slack<br/>팀 커뮤니케이션"]
    end

    subgraph Claude["Claude Code"]
        MCP["MCP Server<br/>(Jira)"]
        API["Direct API<br/>(curl)"]
        Env[".env<br/>환경 변수"]
    end

    subgraph Local["로컬 백로그"]
        Epics["backlog/epics/"]
        Stories["backlog/stories/"]
        Sprints["backlog/sprints/"]
    end

    Jira <--> |"Jira Cloud App"| Slack
    MCP --> Jira
    API --> Jira
    Env --> MCP
    Env --> API
    Local --> |"동기화"| Jira
```

### 1.3 최종 구축 결과

| 항목 | 값 |
|------|-----|
| Jira Site | hybrid-rag-knowledge-ops.atlassian.net |
| 프로젝트 Key | SCRUM |
| Slack 워크스페이스 | hybrid-rag-knowledge-ops |
| 채널 수 | 5개 (proj-hrkp-*) |
| 생성된 이슈 | Epic 1개, Story 3개, Sprint 1개 |

---

## 2. Jira 계정 및 프로젝트 생성

### 2.1 Atlassian 계정 생성

**URL**: https://www.atlassian.com/try/cloud/signup

**절차**:
1. "Get it free" 클릭
2. 이메일 주소 입력 (업무용 권장)
3. 이메일 인증 완료
4. Site 이름 입력 → `{your-project}.atlassian.net` 생성

### 2.2 프로젝트 생성 시 설정

#### 업무 유형 선택
```
What kind of work do you do?
→ "Software development" 선택
```

#### 작업 방식 선택 (다중 선택)
```
✅ Run sprints (스프린트 실행)
✅ Work in scrum (스크럼 방식)
✅ Track bugs (버그 추적)
✅ Prioritize work (작업 우선순위)
```

#### Issue Types 선택
```
✅ Task
✅ Story
✅ Bug
```

#### Workflow 설정
```
To Do → In Progress → In Review → Done
```

### 2.3 API 토큰 발급

**URL**: https://id.atlassian.com/manage-profile/security/api-tokens

```
1. "Create API token" 클릭
2. Label 입력: "Claude Code Integration"
3. "Create" 클릭
4. 토큰 복사 (한 번만 표시됨!)
```

**주의**: 토큰은 `ATATT3xFfGF0...` 형식이며, 절대 git에 커밋하지 마세요.

---

## 3. Slack 워크스페이스 생성

### 3.1 워크스페이스 생성

**URL**: https://slack.com/get-started

```
1. "Create a new workspace" 선택
2. 이메일 주소 입력
3. 인증 코드 입력
4. 워크스페이스 이름 입력
5. 완료
```

### 3.2 프로젝트 채널 생성

**권장 채널 구조**:

| 채널 | 용도 | 알림 설정 |
|------|------|----------|
| #proj-hrkp-general | 일반 소통, 공지 | All messages |
| #proj-hrkp-dev | 개발 논의 | Mentions only |
| #proj-hrkp-standup | 데일리 스탠드업 | All messages |
| #proj-hrkp-review | PR/코드 리뷰 | Mentions only |
| #proj-hrkp-alerts | CI/CD 알림 | Nothing |

**생성 방법**:
```
Slack 좌측 → "채널" 옆 "+" → "채널 만들기" → 정보 입력 → "만들기"
```

---

## 4. Jira-Slack 연동

### 4.1 Slack에서 Jira Cloud 앱 설치

**방법 1: Slack App Directory**
```
Slack → 앱 → 앱 추가 → "Jira Cloud" 검색 → 설치
```

**방법 2: 직접 URL**
```
https://slack.com/apps/A2RPP3NFR-jira-cloud
```

### 4.2 Jira 계정 연결

Slack에서 `/jira connect` 명령어 실행 후 Atlassian 계정 로그인

### 4.3 연동 문제 해결

**문제**: "We didn't find any Jira sites associated with your account"

**해결 방법**:

1. **Jira Cloud 앱 재설치**
   - Slack → 앱 → Jira → 앱 제거
   - 다시 설치 및 계정 연결

2. **Slack Integration+ 사용 (대안)**
   - Jira Marketplace에서 "Slack Integration+" 설치
   - Jira → 설정 → 앱 → Slack Integration+ → Configure

3. **계정 확인**
   - Slack과 Jira에 동일한 이메일로 로그인했는지 확인

### 4.4 연동 확인

```bash
# Slack에서 테스트
/jira SCRUM-1

# 또는 Jira 앱에서 "Your work from Jira" 확인
```

---

## 5. Claude Code 환경 설정

### 5.1 환경 변수 파일 생성

**.env 파일** (프로젝트 루트):

```bash
# ===========================================
# Jira Configuration
# ===========================================
JIRA_HOST=your-project.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=ATATT3xFfGF0...your-token...
JIRA_PROJECT_KEY=SCRUM

# ===========================================
# Slack Configuration
# ===========================================
SLACK_WORKSPACE=your-workspace
SLACK_CHANNEL_GENERAL=#proj-hrkp-general
SLACK_CHANNEL_DEV=#proj-hrkp-dev
SLACK_CHANNEL_ALERTS=#proj-hrkp-alerts
```

### 5.2 MCP 설정 파일 생성

**`.claude/settings.json` 파일**에 `mcpServers` 섹션 추가:

> ⚠️ **주의**: `.mcp.json`이 아닌 **`.claude/settings.json`**에 설정해야 합니다. Claude Code는 `.mcp.json`을 읽지 않습니다.

```json
{
  "mcpServers": {
    "jira": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-jira"],
      "env": {
        "JIRA_HOST": "your-project.atlassian.net",
        "JIRA_EMAIL": "your-email@example.com",
        "JIRA_API_TOKEN": "${JIRA_API_TOKEN}"
      }
    }
  }
}
```

기존 `.claude/settings.json`에 다른 설정이 있다면 `mcpServers` 키만 추가하면 됩니다.

### 5.3 보안 설정

**.gitignore에 추가**:
```
.env
.env.local
.claude/settings.local.json
```

> 📝 **참고**: `.claude/settings.json`은 git에 커밋해도 됩니다. API 토큰은 `${JIRA_API_TOKEN}` 형식으로 환경 변수를 참조하므로 실제 토큰이 노출되지 않습니다.

### 5.4 환경 변수 로드

```bash
# 현재 세션에 환경 변수 로드
source .env

# 또는 direnv 사용 (권장)
echo "dotenv" > .envrc
direnv allow
```

---

## 6. Claude Code로 Jira 자동화

### 6.1 Jira REST API 직접 호출

Claude Code에서 curl 명령어로 Jira API를 직접 호출할 수 있습니다.

#### Epic 생성

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -X POST \
  -H "Content-Type: application/json" \
  --data '{
    "fields": {
      "project": {"key": "SCRUM"},
      "summary": "Document Processing Pipeline",
      "description": {
        "type": "doc",
        "version": 1,
        "content": [
          {
            "type": "paragraph",
            "content": [
              {"type": "text", "text": "Epic 설명"}
            ]
          }
        ]
      },
      "issuetype": {"name": "Epic"},
      "priority": {"name": "Highest"}
    }
  }' \
  "https://$JIRA_HOST/rest/api/3/issue"
```

**응답**:
```json
{"id":"10004","key":"SCRUM-5","self":"https://..."}
```

#### Story 생성 (Epic 하위)

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -X POST \
  -H "Content-Type: application/json" \
  --data '{
    "fields": {
      "project": {"key": "SCRUM"},
      "summary": "문서 업로드 API 구현",
      "description": {
        "type": "doc",
        "version": 1,
        "content": [
          {
            "type": "paragraph",
            "content": [
              {"type": "text", "text": "Story 설명"}
            ]
          }
        ]
      },
      "issuetype": {"name": "Story"},
      "priority": {"name": "Highest"},
      "parent": {"key": "SCRUM-5"}
    }
  }' \
  "https://$JIRA_HOST/rest/api/3/issue"
```

### 6.2 Sprint 생성 및 이슈 할당

#### 보드 ID 조회

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  "https://$JIRA_HOST/rest/agile/1.0/board"
```

#### Sprint 생성

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -X POST \
  -H "Content-Type: application/json" \
  --data '{
    "name": "Sprint 01",
    "startDate": "2026-01-20T09:00:00.000+09:00",
    "endDate": "2026-01-31T18:00:00.000+09:00",
    "originBoardId": 1,
    "goal": "스프린트 목표"
  }' \
  "https://$JIRA_HOST/rest/agile/1.0/sprint"
```

**주의**: Sprint 이름은 30자 이내

#### 이슈를 Sprint에 할당

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -X POST \
  -H "Content-Type: application/json" \
  --data '{
    "issues": ["SCRUM-6", "SCRUM-7", "SCRUM-8"]
  }' \
  "https://$JIRA_HOST/rest/agile/1.0/sprint/3/issue"
```

### 6.3 Claude Code 프롬프트 예시

```
"백로그 폴더의 EPIC-001과 STORY-001~003을 Jira에 생성해줘.
Sprint 01도 생성하고 Story들을 할당해줘."
```

Claude Code가 자동으로:
1. 백로그 파일 읽기
2. Jira API 호출하여 이슈 생성
3. Sprint 생성 및 이슈 할당
4. 백로그 문서에 Jira ID 업데이트

---

## 7. 백로그 → Jira 동기화

### 7.1 백로그 파일 구조

```
backlog/
├── epics/
│   └── EPIC-001-document-processing.md
├── stories/
│   ├── STORY-001-document-upload-api.md
│   ├── STORY-002-docling-parser.md
│   └── STORY-003-semantic-chunking.md
└── sprints/
    └── sprint-01.md
```

### 7.2 백로그 파일 형식

**Epic 파일 예시** (`EPIC-001-document-processing.md`):

```markdown
# EPIC-001: Document Processing Pipeline

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-5 |
| **Status** | ready |
| **Priority** | Critical |

## 요약

문서 업로드부터 Knowledge Graph 생성까지의 전체 ETL 파이프라인 구축.

## User Stories

| ID | Jira | 제목 | Points | Status |
|----|------|------|--------|--------|
| STORY-001 | SCRUM-6 | 문서 업로드 API | 3 | To Do |
| STORY-002 | SCRUM-7 | Docling 문서 파싱 | 8 | To Do |
| STORY-003 | SCRUM-8 | Semantic Chunking | 8 | To Do |
```

### 7.3 동기화 프로세스

```mermaid
flowchart LR
    A["백로그 파일<br/>(Markdown)"] --> B["Claude Code<br/>파싱"]
    B --> C["Jira API<br/>이슈 생성"]
    C --> D["Jira Key<br/>반환"]
    D --> E["백로그 파일<br/>업데이트"]
```

### 7.4 동기화 후 업데이트

Claude Code가 이슈 생성 후 백로그 파일에 Jira ID를 자동 반영:

```markdown
# Before
| **Jira ID** | - (미등록) |

# After
| **Jira ID** | SCRUM-5 |
```

---

## 8. 가상 팀원 Slack 자동화

Claude Code 에이전트(가상 팀원)가 Slack에 메시지를 자동으로 전송하여 협업 기록을 남기는 방법입니다.

### 8.1 가상 팀원 개념

```
당신(1명) + 가상 팀원(7명) = 완전 자동화된 개발팀

┌─────────────────────────────────────────────────────┐
│                   Claude Code 세션                   │
├─────────────────────────────────────────────────────┤
│  [PM]       요구사항 → 스펙 변환      specs/        │
│  [TechLead] 아키텍처 검토, 코드 리뷰  docs/         │
│  [Backend]  SpringBoot, API Gateway  backend/       │
│  [Frontend] React, UI/UX             frontend/      │
│  [MLRag]    RAG 파이프라인, 평가     ai-service/   │
│  [Data]     ETL, Graph, DB           etl/, graph/   │
│  [QA]       테스트, Ragas 평가       tests/        │
│  [DevOps]   Docker, CI/CD            infrastructure/│
└─────────────────────────────────────────────────────┘
```

**핵심**: 모든 가상 팀원은 하나의 Claude Code 세션에서 실행되며, 동일한 API 토큰을 사용합니다.

### 8.2 Slack Bot Token 발급

가상 팀원이 Slack에 메시지를 보내려면 Bot Token이 필요합니다.

#### Step 1: Slack App 생성

1. **https://api.slack.com/apps** 접속
2. **"Create New App"** → **"From scratch"** 선택
3. 설정:
   - App Name: `HRKP Virtual Team`
   - Workspace: `hybrid-rag-knowledge-ops`
4. **"Create App"** 클릭

#### Step 2: Bot Token Scopes 설정

1. 좌측 사이드바 → **"OAuth & Permissions"** 클릭
2. **"Bot Token Scopes"** 섹션에서 **"Add an OAuth Scope"** 클릭
3. 다음 4개 권한 추가:

| Scope | 용도 |
|-------|------|
| `chat:write` | 메시지 전송 |
| `chat:write.public` | 참여하지 않은 채널에도 전송 |
| `channels:read` | 채널 목록 조회 |
| `users:read` | 사용자 정보 조회 |

#### Step 3: 앱 설치 및 토큰 발급

1. 같은 페이지에서 위로 스크롤
2. **"Install to {workspace}"** 버튼 클릭
3. 권한 요청 화면에서 **"허용"** 클릭
4. **"Bot User OAuth Token"** 복사 (xoxb-... 형식)

### 8.3 환경 변수에 토큰 추가

**.env 파일 업데이트**:

```bash
# ===========================================
# Slack Configuration
# ===========================================
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_WORKSPACE=hybrid-rag-knowledge-ops
SLACK_CHANNEL_GENERAL=#proj-hrkp-general
SLACK_CHANNEL_DEV=#proj-hrkp-dev
SLACK_CHANNEL_ALERTS=#proj-hrkp-alerts
```

### 8.4 Claude Code에서 Slack 메시지 전송

#### 표준화된 스크립트 사용 (권장)

> ✅ **2026-01-20 업데이트**: 표준화된 `send_slack.sh` 스크립트 도입
> - 자동 구분자 (`───────────────────────`) 추가
> - jq 불필요 (의존성 최소화)
> - 한글/이모지 안전 처리

```bash
# 스크립트 위치: scripts/send_slack.sh
# 사용법: ./scripts/send_slack.sh <채널> <에이전트> "메시지"

# PM 메시지
./scripts/send_slack.sh proj-hrkp-dev PM "Sprint 01 요구사항 정의 완료"

# Backend 메시지
./scripts/send_slack.sh proj-hrkp-dev Backend "STORY-001 착수합니다"

# TechLead 메시지
./scripts/send_slack.sh proj-hrkp-review TechLead "아키텍처 검토 완료"
```

**전체 에이전트 일괄 인사**:
```bash
# 9개 에이전트 일괄 인사 전송
./scripts/standup_all.sh
```

#### 기본 curl 방식 (참고용)

직접 curl을 사용해야 하는 경우:

```bash
curl -s -X POST "https://slack.com/api/chat.postMessage" \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "proj-hrkp-dev",
    "text": "[HRKP Virtual Team] 연동 테스트 메시지입니다."
  }'
```

#### 가상 팀원별 메시지 전송 (curl 직접 사용)

```bash
# PM 메시지
curl -s -X POST "https://slack.com/api/chat.postMessage" \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "proj-hrkp-dev",
    "text": "*[PM]* Sprint 01 요구사항 정의 완료 - STORY-001, 002, 003"
  }'

# TechLead 메시지
curl -s -X POST "https://slack.com/api/chat.postMessage" \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "proj-hrkp-dev",
    "text": "*[TechLead]* 아키텍처 검토 완료. FastAPI + Celery 구조 승인합니다."
  }'

# Backend 메시지
curl -s -X POST "https://slack.com/api/chat.postMessage" \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "proj-hrkp-dev",
    "text": "*[Backend]* STORY-001 착수합니다. /api/v1/documents 엔드포인트 구현 시작."
  }'
```

> ⚠️ **주의**: curl 직접 사용 시 한글/이모지가 포함된 메시지는 JSON 인코딩 문제가 발생할 수 있습니다. `send_slack.sh` 스크립트를 사용하면 이 문제가 자동으로 해결됩니다.

### 8.5 가상 팀원 메시지 포맷 규칙

| 역할 | Slack 메시지 형식 | Jira Label | 작업 영역 |
|------|------------------|------------|----------|
| PM | `*[PM]*` | `PM` | specs/ |
| TechLead | `*[TechLead]*` | `TechLead` | docs/ |
| Backend | `*[Backend]*` | `Backend` | backend/ |
| Frontend | `*[Frontend]*` | `Frontend` | frontend/ |
| MLRag | `*[MLRag]*` | `MLRag` | ai-service/ |
| Data | `*[Data]*` | `Data` | etl/, graph/ |
| QA | `*[QA]*` | `QA` | tests/ |
| DevOps | `*[DevOps]*` | `DevOps` | infrastructure/ |

### 8.6 협업 워크플로우

```mermaid
flowchart TB
    subgraph Phase1["Phase 1: 순차"]
        PM["[PM]<br/>요구사항 정의"] --> TechLead["[TechLead]<br/>아키텍처 검토"]
        TechLead --> Approval["승인"]
    end

    subgraph Phase2["Phase 2: 병렬"]
        Backend["[Backend]<br/>API 구현"]
        Frontend["[Frontend]<br/>UI 구현"]
        MLRag["[MLRag]<br/>RAG 구현"]
        Data["[Data]<br/>ETL 구현"]
        DevOps["[DevOps]<br/>인프라 구성"]
    end

    subgraph Phase3["Phase 3: 검증"]
        QA["[QA]<br/>테스트 검증"]
        TechReview["[TechLead]<br/>코드 리뷰"]
        Deploy["배포 승인"]
    end

    Approval --> Phase2
    Phase2 --> QA
    QA --> TechReview
    TechReview --> Deploy
```

### 8.7 실전 예시: Sprint 시작

Claude Code에서 Sprint 시작 시 자동으로 전송되는 메시지들:

```bash
# 1. PM이 스프린트 목표 공유
"*[PM]* 🎯 Sprint 01 시작합니다!
목표: 문서 업로드부터 Semantic Chunking까지 ETL 파이프라인 1단계 완성
• STORY-001: 문서 업로드 API (3pts)
• STORY-002: Docling 파싱 (8pts)
• STORY-003: Semantic Chunking (8pts)"

# 2. TechLead가 기술 방향 제시
"*[TechLead]* 📋 기술 스택 확정:
• Framework: FastAPI + Celery
• Storage: MinIO
• Parser: Docling (97%+ 정확도)
• Chunker: LangChain SemanticChunker"

# 3. Backend가 작업 시작 알림
"*[Backend]* 🚀 STORY-001 착수합니다.
POST /api/v1/documents 엔드포인트 구현 시작."

# 4. QA가 테스트 준비 알림
"*[QA]* 🧪 테스트 케이스 준비 중.
STORY-001 완료되면 검증 시작하겠습니다."
```

### 8.8 Slack Bot 설정 정보

| 항목 | 값 |
|------|-----|
| App Name | HRKP Virtual Team |
| App ID | A0A929PJ7RD |
| Bot ID | B0A9WMEEC0Z |
| Token 형식 | xoxb-... |
| 권한 | chat:write, chat:write.public, channels:read, users:read |

---

## 9. GitHub MCP 설정

GitHub MCP를 설정하면 PR 생성, 이슈 관리, 코드 리뷰 등을 Claude Code에서 직접 수행할 수 있습니다.

### 9.1 MCP 서버 선택 기준

현재 프로젝트에서 필요한 MCP 서버를 선별한 결과입니다.

| MCP 서버 | 선택 | 사유 |
|---------|------|------|
| **Jira MCP** | ✅ 필수 | 이슈/스프린트 관리 자동화. 이미 설정됨 |
| **GitHub MCP** | ✅ 필수 | PR 생성, 코드 리뷰, 이슈 연동. `gh` CLI보다 통합성 우수 |
| **Slack MCP** | ❌ 불필요 | 공식 MCP 서버 없음. Bot Token + REST API로 충분 |
| **Filesystem MCP** | ❌ 불필요 | Claude Code 내장 도구 (Read, Write, Edit)로 대체 |
| **Agent Mail MCP** | ❌ 불필요 | 단일 세션 운영 시 불필요 (섹션 10 참조) |

### 9.2 GitHub Personal Access Token 발급

**URL**: https://github.com/settings/tokens

**발급 절차**:
1. **"Generate new token (classic)"** 클릭
2. Note: `Claude Code Integration`
3. Expiration: 적절한 기간 선택 (90일 권장)
4. 권한 선택:

| 권한 | 용도 |
|------|------|
| `repo` | 저장소 전체 접근 (필수) |
| `workflow` | GitHub Actions 실행 |
| `read:org` | 조직 정보 읽기 |
| `read:user` | 사용자 정보 읽기 |

5. **"Generate token"** 클릭 후 토큰 복사

### 9.3 환경 변수 설정

**.env 파일**:
```bash
# ===================
# GitHub Configuration
# ===================
GITHUB_TOKEN=ghp_your-github-token-here
```

### 9.4 MCP 설정 파일

**`.claude/settings.json` 파일**에 GitHub MCP 추가:

> ⚠️ **주의**: `.mcp.json`이 아닌 **`.claude/settings.json`**에 설정해야 합니다.

```json
{
  "mcpServers": {
    "jira": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-jira"],
      "env": {
        "JIRA_HOST": "hybrid-rag-knowledge-ops.atlassian.net",
        "JIRA_EMAIL": "your-email@example.com",
        "JIRA_API_TOKEN": "${JIRA_API_TOKEN}"
      }
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

### 9.5 MCP 적용 및 확인

```bash
# Claude Code 재시작 (MCP 로드)
exit
claude

# MCP 상태 확인
/mcp
```

### 9.6 GitHub MCP 사용 예시

```bash
# PR 목록 조회
"현재 열려있는 PR 목록 보여줘"

# PR 생성
"현재 브랜치로 PR 생성해줘. 제목은 'SCRUM-6 문서 업로드 API 구현'"

# 이슈 생성
"GitHub 이슈 생성해줘: 버그 - 파일 업로드 시 한글 파일명 깨짐"

# 코드 리뷰 요청
"PR #12에 코드 리뷰 코멘트 추가해줘"
```

---

## 10. Agent Mail & Beads 검토

MCP 기반 에이전트 간 통신 도구인 Agent Mail과 Beads의 적용 필요성을 검토한 결과입니다.

### 10.1 Agent Mail이란?

Jeffrey Emanuel이 개발한 **MCP Agent Mail**은 서로 다른 Claude Code 세션 간 비동기 메시징을 가능하게 합니다.

```
┌─────────────────────────────────────────────────────────────┐
│                  Agent Mail 시스템                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Agent A                    Mail Directory                   │
│  ┌──────────┐              ┌────────────────┐               │
│  │ Inbox    │◄─────────────│ /shared/mail/  │               │
│  │ Outbox   │─────────────►│ agents/        │               │
│  └──────────┘              │  ├─ agent-a/   │               │
│                            │  ├─ agent-b/   │               │
│  Agent B                    │  └─ agent-c/   │               │
│  ┌──────────┐              └────────────────┘               │
│  │ Inbox    │◄──────────┐                                   │
│  │ Outbox   │───────────┘                                   │
│  └──────────┘                                               │
└─────────────────────────────────────────────────────────────┘
```

### 10.2 Beads란?

Steve Yegge의 **Beads**는 Git + SQLite를 사용한 에이전트 메모리 시스템입니다. 구조화된 데이터를 에이전트 간에 공유할 수 있습니다.

### 10.3 적용 필요성 판단

#### 결론: **현재 프로젝트에서는 불필요**

| 판단 기준 | Agent Mail 필요 조건 | 현재 상황 |
|----------|---------------------|----------|
| 세션 구조 | 여러 터미널에서 별도 세션 실행 | 단일 세션에서 모든 에이전트 실행 |
| 통신 방식 | 세션 간 비동기 메시징 필요 | 세션 내 동기 처리 가능 |
| 기록 방식 | 파일 기반 메일함 필요 | Jira/Slack API로 기록 |

#### 비교 다이어그램

```
[Agent Mail이 필요한 경우]
┌─────────────────────────────────────────────────────────────┐
│  터미널 1              터미널 2              터미널 3        │
│  ┌──────────┐        ┌──────────┐        ┌──────────┐      │
│  │ Claude   │        │ Claude   │        │ Claude   │      │
│  │ Session  │◄──────►│ Session  │◄──────►│ Session  │      │
│  │(Backend) │  Mail  │(Frontend)│  Mail  │  (QA)    │      │
│  └──────────┘        └──────────┘        └──────────┘      │
│       ↓                   ↓                   ↓            │
│  서로 다른 세션 간 통신 → Agent Mail 필요                    │
└─────────────────────────────────────────────────────────────┘

[현재 프로젝트 구조 - Agent Mail 불필요]
┌─────────────────────────────────────────────────────────────┐
│  터미널 1 (단일 세션)                                        │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                  Claude Code 세션                      │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐     │  │
│  │  │   PM    │ │ Backend │ │Frontend │ │   QA    │     │  │
│  │  │  Agent  │ │  Agent  │ │  Agent  │ │  Agent  │     │  │
│  │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘     │  │
│  │       └───────────┴───────────┴───────────┘          │  │
│  │                      ↓                                │  │
│  │            동일 세션 내 동기 처리                        │  │
│  └───────────────────────────────────────────────────────┘  │
│       ↓                   ↓                   ↓            │
│   Jira API           Slack API          로컬 파일          │
│   (이슈 기록)         (메시지 기록)       (work_logs/)       │
└─────────────────────────────────────────────────────────────┘
```

### 10.4 현재 프로젝트의 통신 방식

| 통신 유형 | 도구 | 기록 위치 |
|----------|------|----------|
| 작업 상태 공유 | Jira REST API | Jira 이슈/코멘트 |
| 팀 내 알림 | Slack Bot API | Slack 채널 메시지 |
| 상세 기록 | 로컬 파일 | `work_logs/` 디렉토리 |
| 코드 협업 | GitHub MCP | PR, 코멘트 |

### 10.5 Agent Mail이 필요한 시나리오

향후 다음 상황에서는 Agent Mail 도입을 검토할 수 있습니다:

| 시나리오 | 설명 |
|---------|------|
| 다중 터미널 운영 | 각 터미널에서 별도 에이전트 실행 시 |
| 장기 실행 작업 | 한 에이전트의 작업 완료를 다른 에이전트가 대기 |
| 팀 규모 확대 | 여러 개발자가 각자 Claude Code 세션 운영 |
| 분산 처리 | 작업을 여러 세션에 분산하여 병렬 처리 |

### 10.6 Agent Mail 설치 방법 (참고용)

필요 시 아래와 같이 설치할 수 있습니다:

```bash
# Agent Mail MCP 서버 설치
npm install -g mcp-agent-mail

# 메일 디렉토리 생성
mkdir -p ~/agent-workspace/.agent-mail
```

**`.claude/settings.json`에 추가**:
```json
{
  "mcpServers": {
    "agent-mail": {
      "command": "npx",
      "args": ["-y", "mcp-agent-mail"],
      "env": {
        "MAIL_DIR": "/absolute/path/to/.agent-mail",
        "AGENT_NAME": "main-agent"
      }
    }
  }
}
```

---

## 11. 트러블슈팅

### 11.1 Jira API 오류

| 오류 | 원인 | 해결 |
|------|------|------|
| 401 Unauthorized | 인증 실패 | 이메일/토큰 확인 |
| 403 Forbidden | 권한 없음 | 프로젝트 권한 확인 |
| 400 Bad Request | 잘못된 요청 | 필드명, 값 확인 |
| 404 Not Found | 리소스 없음 | 프로젝트 키, 이슈 키 확인 |

**디버깅**:
```bash
# 연결 테스트
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  "https://$JIRA_HOST/rest/api/3/myself"

# 프로젝트 확인
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  "https://$JIRA_HOST/rest/api/3/project/SCRUM"
```

### 11.2 Jira-Slack 연동 오류

| 오류 | 원인 | 해결 |
|------|------|------|
| No Jira sites found | 계정 미연결 | `/jira connect` 재실행 |
| Site not accessible | 권한 없음 | Jira 관리자 확인 |
| Integration app error | 앱 설정 오류 | 앱 재설치 |

### 11.3 Sprint 생성 오류

| 오류 | 원인 | 해결 |
|------|------|------|
| 이름 30자 초과 | Sprint 이름 제한 | 이름 축소 |
| Board not found | 잘못된 보드 ID | 보드 조회 후 재시도 |
| Invalid date | 날짜 형식 오류 | ISO 8601 형식 사용 |

### 11.4 Claude Code MCP 오류

```bash
# MCP 상태 확인
/mcp status

# MCP 재시작
/mcp restart jira

# 환경 변수 확인
echo $JIRA_HOST
echo $JIRA_EMAIL
```

---

### 11.5 Slack Bot API 오류

| 오류 | 원인 | 해결 |
|------|------|------|
| invalid_auth | 토큰 오류 | Bot Token 확인 |
| channel_not_found | 채널 없음 | 채널명 확인 (# 제외) |
| not_in_channel | 봇이 채널에 없음 | chat:write.public 권한 추가 |
| missing_scope | 권한 부족 | OAuth Scopes 추가 후 재설치 |

**디버깅**:
```bash
# 인증 테스트
curl -s -X POST "https://slack.com/api/auth.test" \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN"

# 채널 목록 조회
curl -s -X GET "https://slack.com/api/conversations.list" \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN"
```

---

## 12. Quick Reference

### 12.1 URL 모음

| 서비스 | URL |
|--------|-----|
| Jira 가입 | https://www.atlassian.com/try/cloud/signup |
| Jira API 토큰 | https://id.atlassian.com/manage-profile/security/api-tokens |
| Slack 가입 | https://slack.com/get-started |
| Slack Jira App | https://slack.com/apps/A2RPP3NFR-jira-cloud |
| Slack App 생성 | https://api.slack.com/apps |
| GitHub Token | https://github.com/settings/tokens |

### 12.2 주요 API 엔드포인트

**Jira API**:

| 작업 | 엔드포인트 |
|------|-----------|
| 이슈 생성 | `POST /rest/api/3/issue` |
| 이슈 조회 | `GET /rest/api/3/issue/{issueKey}` |
| 보드 목록 | `GET /rest/agile/1.0/board` |
| Sprint 생성 | `POST /rest/agile/1.0/sprint` |
| Sprint에 이슈 할당 | `POST /rest/agile/1.0/sprint/{sprintId}/issue` |

**Slack API**:

| 작업 | 엔드포인트 |
|------|-----------|
| 메시지 전송 | `POST https://slack.com/api/chat.postMessage` |
| 인증 테스트 | `POST https://slack.com/api/auth.test` |
| 채널 목록 | `GET https://slack.com/api/conversations.list` |

### 12.3 Claude Code 명령어

```bash
# Jira 이슈 조회
"SCRUM-5 이슈 상세 정보 보여줘"

# Jira 이슈 생성
"SCRUM 프로젝트에 Story 이슈 생성해줘: 문서 업로드 API"

# 백로그 동기화
"backlog/epics/EPIC-001 파일을 읽고 Jira에 생성해줘"

# Sprint 생성
"Sprint 01을 생성하고 SCRUM-6, 7, 8 이슈를 할당해줘"
```

### 12.4 체크리스트

```markdown
## 초기 설정 체크리스트

### 계정 생성
- [ ] Atlassian 계정 생성
- [ ] Jira 프로젝트 생성
- [ ] Jira API 토큰 발급
- [ ] Slack 워크스페이스 생성

### 연동
- [ ] Jira-Slack 연동
- [ ] .env 파일 생성
- [ ] .claude/settings.json에 mcpServers 추가
- [ ] .gitignore 업데이트

### Slack Bot (가상 팀원 자동화)
- [ ] Slack App 생성 (api.slack.com)
- [ ] Bot Token Scopes 설정 (chat:write, chat:write.public, channels:read, users:read)
- [ ] 앱 설치 및 Bot Token 발급
- [ ] .env에 SLACK_BOT_TOKEN 추가

### GitHub MCP
- [ ] GitHub Personal Access Token 발급
- [ ] .env에 GITHUB_TOKEN 추가
- [ ] .claude/settings.json에 GitHub MCP 설정 추가
- [ ] Claude Code 재시작 후 /mcp 확인

### 테스트
- [ ] Jira API 연결 테스트
- [ ] Slack 연동 테스트
- [ ] 이슈 생성 테스트
- [ ] Slack Bot 메시지 전송 테스트
- [ ] GitHub MCP 연결 테스트
```

---

## 13. Sprint 실행 가이드

Claude Code로 실제 Sprint를 실행하는 방법과 사용자 역할을 설명합니다.

### 13.1 역할 구조

```
┌─────────────────────────────────────────────────────────┐
│  YOU (Project Owner / Product Owner)                    │
│  └─→ Claude Code에 직접 지시                            │
│  └─→ 코드 리뷰 및 승인                                  │
│  └─→ 의사결정 (기술 선택, 우선순위 등)                   │
│  └─→ 결과물 테스트 및 피드백                            │
└─────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────┐
│  Claude Code (개발 실행자)                              │
│  └─→ 필요시 가상 에이전트(PM, Backend 등) 호출          │
│  └─→ Jira API로 이슈 상태 업데이트                      │
│  └─→ 코드 작성, 테스트 실행                             │
│  └─→ PR 생성, 문서 업데이트                             │
└─────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────┐
│  Jira: 작업 추적  │  Slack: 알림/로그 (선택)            │
└─────────────────────────────────────────────────────────┘
```

### 13.2 Slack의 역할 (오해 주의)

| 오해 | 실제 |
|------|------|
| Slack으로 Claude Code에 지시한다 | ❌ Claude Code는 Slack을 읽지 않음 |
| Slack에 명령어를 입력하면 실행된다 | ❌ Claude Code CLI에서 직접 대화 |
| 가상 팀원이 Slack에서 대화한다 | ⚠️ 메시지 전송만 가능 (로깅용) |

**Slack의 실제 용도**:
- 작업 진행 상황 **기록** (알림 채널)
- 가상 팀원 활동 **로그** 남기기
- CI/CD, 모니터링 **알림** 수신
- 다른 인간 팀원과의 **협업** (있는 경우)

### 13.3 Sprint 시작 방법

#### 방법 1: 직접 지시 (권장)

```bash
# Claude Code CLI에서:
"Sprint 01 시작해줘. SCRUM-6 (문서 업로드 API) 먼저 구현하자"
```

Claude Code가 자동으로:
1. Jira에서 SCRUM-6을 "In Progress"로 변경
2. 코드 구현 시작
3. 테스트 작성 및 실행
4. 완료 시 Jira 상태 업데이트
5. (설정 시) Slack에 진행 상황 알림

#### 방법 2: PM 에이전트 활용

```bash
"PM 에이전트로 Sprint 01 킥오프 미팅 진행해줘"
```

PM 에이전트가:
1. Sprint 목표 확인
2. 백로그 검토
3. 기술 의존성 체크
4. 킥오프 요약 생성

#### 방법 3: 워크플로우 사용

```bash
/workflows:feature-development SCRUM-6
```

전체 사이클 자동화:
1. 요구사항 분석
2. 설계 검토
3. 구현
4. 테스트
5. 코드 리뷰
6. 완료 처리

### 13.4 Sprint 중 사용자 역할 (할 일 있음!)

**❌ 오해**: "Sprint 시작하면 나는 할 일 없어"

**✅ 실제**: 사용자는 **Product Owner + 최종 검토자** 역할

| 상황 | 사용자 역할 |
|------|------------|
| 기술 결정 필요 | Claude Code가 질문 → 사용자 결정 |
| 구현 방향 선택 | 여러 옵션 중 선택 |
| 코드 리뷰 요청 | PR 승인/거절/피드백 |
| 테스트 결과 확인 | 기대 결과 검증 |
| 예외 상황 발생 | 우선순위 재조정 |
| 완료 확인 | Acceptance Criteria 충족 확인 |

### 13.5 Sprint 01에서 구현할 것

**중요**: Sprint 01은 프로그램을 **만드는** 것입니다. 아직 프로그램이 없습니다!

#### 현재 상태
```
┌──────────────────────────────────────────────┐
│  현재: 설계 문서만 존재                        │
│  - 상세 설계서 v2.4                           │
│  - API 설계서                                 │
│  - 백로그 (요구사항)                          │
│  ※ 실행 가능한 코드 없음!                     │
└──────────────────────────────────────────────┘
```

#### Sprint 01 목표: ETL 파이프라인 1단계 구현

```mermaid
flowchart LR
    subgraph STORY001["STORY-001: 문서 업로드 API"]
        Upload["POST /api/v1/documents"]
        Validate["파일 검증"]
        Store["MinIO 저장"]
    end

    subgraph STORY002["STORY-002: Docling 파싱"]
        Parse["문서 파싱"]
        Extract["텍스트/테이블 추출"]
        Normalize["결과 표준화"]
    end

    subgraph STORY003["STORY-003: Semantic Chunking"]
        Chunk["의미 단위 분할"]
        Preserve["특수 블록 보존"]
        Output["청크 출력"]
    end

    Upload --> Validate --> Store
    Store --> Parse --> Extract --> Normalize
    Normalize --> Chunk --> Preserve --> Output
```

| Story | 구현 내용 | 결과물 |
|-------|----------|--------|
| **STORY-001** | 문서 업로드 API | `POST /api/v1/documents` 엔드포인트 |
| **STORY-002** | Docling 파싱 | PDF/DOCX/HWP → 구조화된 텍스트 |
| **STORY-003** | Semantic Chunking | 텍스트 → 의미 단위 청크 |

### 13.6 Docling 파싱이란?

**Docling**: IBM 오픈소스 문서 파서 (97%+ 정확도)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────────┐
│  PDF 파일   │     │  Docling    │     │  구조화된 데이터     │
│  DOCX 파일  │ ──► │  Parser     │ ──► │  - 텍스트           │
│  HWP 파일   │     │  (Python)   │     │  - 테이블           │
└─────────────┘     └─────────────┘     │  - 이미지 위치      │
                                        │  - 메타데이터       │
                                        └─────────────────────┘
```

**Sprint 01에서**: Docling을 FastAPI 서비스로 래핑하여 API로 호출 가능하게 만듦

### 13.7 Semantic Chunking이란?

**문제**: 긴 문서를 AI가 처리하려면 적절한 크기로 분할 필요

**일반 청킹** vs **Semantic Chunking**:

```
[일반 청킹 - 고정 크기]
"서론: 본 프로젝트는 RAG 시스템을 | 구축한다. 1장: 시스템 아키텍처..."
                              ↑
                    문장 중간에서 잘림 (품질 저하)

[Semantic Chunking - 의미 단위]
"서론: 본 프로젝트는 RAG 시스템을 구축한다."
"1장: 시스템 아키텍처..."
     ↑
  의미 단위로 분할 (검색 품질 향상)
```

**Sprint 01에서**: LangChain SemanticChunker + BGE-M3 임베딩으로 구현

### 13.8 Sprint 진행 예시

```bash
# 1. Sprint 시작
사용자: "Sprint 01 시작해줘"

# 2. Claude Code 작업
Claude: "SCRUM-6 착수합니다. 먼저 FastAPI 엔드포인트를 설계하겠습니다."
        [코드 작성 중...]
        "파일 검증 로직을 추가했습니다. 확인해주세요."

# 3. 사용자 검토
사용자: "HWP 파일도 지원해야 하는데, 확장자 검증에 포함됐어?"

# 4. Claude Code 수정
Claude: "HWP 확장자를 ALLOWED_EXTENSIONS에 추가했습니다."

# 5. 테스트 확인
Claude: "단위 테스트 8개 통과했습니다. PR 생성할까요?"

# 6. 사용자 승인
사용자: "응, PR 생성해줘"
```

### 13.9 Sprint 명령어 요약

| 명령 | 설명 |
|------|------|
| `"Sprint 01 시작해줘"` | Sprint 킥오프 |
| `"SCRUM-6 구현해줘"` | 특정 Story 착수 |
| `"현재 진행 상황 알려줘"` | 진행률 확인 |
| `"SCRUM-6 In Review로 변경해줘"` | Jira 상태 변경 |
| `/workflows:feature-development` | 전체 사이클 자동화 |
| `"PR 생성해줘"` | 코드 리뷰 요청 |

---

## 14. PM 중심 워크플로우 테스트

PM Agent가 Sprint를 관리하고 Slack에 알림을 보내는 워크플로우를 검증한 테스트 결과입니다.

### 14.1 테스트 개요

**테스트 일시**: 2026-01-19
**테스트 목적**: PM Agent의 Sprint 확인 및 Slack 알림 기능 검증

| 테스트 항목 | 결과 |
|------------|------|
| PM Agent Sprint 상태 확인 | ✅ 성공 |
| PM Agent Slack 알림 전송 | ✅ 성공 |
| Slack Bot Token 인증 | ✅ 성공 |

### 14.2 환경 설정

#### SLACK_BOT_TOKEN 설정

`.env` 파일에 Slack Bot Token을 추가해야 PM Agent가 Slack 알림을 보낼 수 있습니다.

```bash
# .env 파일
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
```

**토큰 형식**: Slack Bot Token은 반드시 `xoxb-`로 시작해야 합니다.

### 14.3 PM Agent Sprint 확인

#### 사용자 명령

```
"PM이 Sprint 01 확인하고 결과 알려줘"
```

#### PM Agent 실행 흐름

```mermaid
flowchart TB
    User["사용자: Sprint 01 확인해줘"] --> Claude["Claude Code"]
    Claude --> PM["PM Agent 호출<br/>(Task tool)"]
    PM --> Load["Sprint 백로그 로드<br/>backlog/sprints/sprint-01.md"]
    Load --> Analyze["Sprint 분석<br/>• 기간 확인<br/>• Story 목록 확인<br/>• SP 합계 계산"]
    Analyze --> Report["결과 보고"]
    Report --> Slack["Slack 알림 전송<br/>proj-hrkp-dev"]
```

#### 실제 테스트 결과

PM Agent가 확인한 Sprint 01 상태:

| 항목 | 값 |
|------|-----|
| Sprint 이름 | Sprint 01 |
| 기간 | 2026-01-20 ~ 2026-02-02 (2주) |
| Story 수 | 5개 |
| 총 Story Points | 21 SP |
| 상태 | Ready (시작 대기) |

**Story 목록**:

| Story | 내용 | SP | 담당 |
|-------|------|-----|------|
| SCRUM-10 | Docker Compose 18개 컨테이너 구성 | 5 | Infra |
| SCRUM-11 | GitHub Actions CI/CD 파이프라인 | 3 | DevOps |
| SCRUM-12 | Prometheus/Grafana 모니터링 | 3 | DevOps |
| SCRUM-13 | PostgreSQL 스키마 초기화 | 5 | Data |
| SCRUM-14 | Neo4j Knowledge Graph 스키마 | 5 | Data |

### 14.4 PM Agent Slack 알림 테스트

#### 알림 전송 명령

```bash
source .env

curl -s -X POST "https://slack.com/api/chat.postMessage" \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "proj-hrkp-dev",
    "text": "*[PM]* 📋 Sprint 01 현황 보고\n\n• 기간: 2026-01-20 ~ 2026-02-02 (2주)\n• Story: 5개 (21 SP)\n• 상태: Ready (시작 대기)\n\n*Stories*:\n1. SCRUM-10: Docker Compose 구성 (5 SP) - Infra\n2. SCRUM-11: CI/CD 파이프라인 (3 SP) - DevOps\n3. SCRUM-12: 모니터링 설정 (3 SP) - DevOps\n4. SCRUM-13: PostgreSQL 스키마 (5 SP) - Data\n5. SCRUM-14: Neo4j 스키마 (5 SP) - Data"
  }'
```

#### 성공 응답

```json
{
  "ok": true,
  "channel": "C0A9ABM9EJN",
  "ts": "1737297844.749529",
  "message": {
    "user": "U0A9G0Q1T91",
    "type": "message",
    "ts": "1737297844.749529",
    "bot_id": "B0A9WMEEC0Z",
    "app_id": "A0A929PJ7RD",
    "text": "*[PM]* 📋 Sprint 01 현황 보고..."
  }
}
```

### 14.5 트러블슈팅: Slack 인증 오류

#### 오류 상황

```json
{"ok":false,"error":"not_authed"}
```

#### 원인

`.env` 파일에 `SLACK_BOT_TOKEN`이 설정되지 않았거나, 토큰이 올바르지 않음.

#### 해결 방법

1. **토큰 확인**: Slack App 관리 페이지에서 Bot Token 확인
   - https://api.slack.com/apps → 앱 선택 → OAuth & Permissions
   - **Bot User OAuth Token** (xoxb-... 형식) 복사

2. **.env 파일 업데이트**:
   ```bash
   echo "SLACK_BOT_TOKEN=xoxb-your-token-here" >> .env
   ```

3. **환경 변수 로드**:
   ```bash
   source .env
   echo $SLACK_BOT_TOKEN  # 확인
   ```

4. **인증 테스트**:
   ```bash
   curl -s -X POST "https://slack.com/api/auth.test" \
     -H "Authorization: Bearer $SLACK_BOT_TOKEN" | jq
   ```

   성공 응답:
   ```json
   {
     "ok": true,
     "url": "https://your-workspace.slack.com/",
     "team": "your-workspace",
     "user": "your-bot-name",
     "team_id": "T0...",
     "user_id": "U0...",
     "bot_id": "B0..."
   }
   ```

### 14.6 PM 필수 Slack 알림 규칙

PM Agent는 다음 시점에 **반드시** Slack 알림을 보내야 합니다:

| 시점 | 채널 | 메시지 형식 |
|------|------|------------|
| Sprint 시작 | proj-hrkp-dev | `*[PM]* 🚀 Sprint XX 시작!` |
| Sprint 상태 확인 | proj-hrkp-dev | `*[PM]* 📋 Sprint XX 현황 보고` |
| Story 할당 | proj-hrkp-dev | `*[PM]* 📋 작업 할당: SCRUM-XX` |
| Story 완료 | proj-hrkp-dev | `*[PM]* ✅ Story 완료: SCRUM-XX` |
| Sprint 종료 | proj-hrkp-dev | `*[PM]* 🏁 Sprint XX 종료!` |
| 블로커 발생 | proj-hrkp-alerts | `*[PM]* ⚠️ 블로커 발생: SCRUM-XX` |

### 14.7 관련 문서

- [PM 중심 워크플로우 가이드](./09_PM_중심_워크플로우_가이드.md)
- [PM Agent 정의](.claude/agents/pm.md)
- [Sprint 01 백로그](../backlog/sprints/sprint-01.md)

---

## 참고 문서

### 프로젝트 내 문서
- [Jira & Agile 가이드](./05_Jira_Agile_프로젝트_관리_가이드.md)
- [Slack 커뮤니케이션 가이드](./06_Slack_프로젝트_커뮤니케이션_가이드.md)
- [초기 설정 퀵스타트 가이드](./07_Jira_Slack_초기설정_퀵스타트_가이드.md)
- [개발자 통합 가이드](../knowledge_service/docs/05_development/developer_integration_guide.md)

### 공식 문서
- [Jira REST API v3](https://developer.atlassian.com/cloud/jira/platform/rest/v3/)
- [Jira Agile REST API](https://developer.atlassian.com/cloud/jira/software/rest/)
- [Slack API](https://api.slack.com/)
- [Claude Code MCP](https://docs.anthropic.com/claude-code/mcp)

### 세션 로그
- [2026-01-19 세션 로그](../work_logs/session_logs/2026-01-19_jira_slack_setup.md)

---

**문서 버전**: 1.6
**작성일**: 2026-01-19
**최종 업데이트**: 2026-01-20
**업데이트**:
- v1.1: 가상 팀원 Slack 자동화 섹션 추가
- v1.2: GitHub MCP 설정, Agent Mail & Beads 검토 섹션 추가
- v1.3: MCP 설정 파일 위치 수정 (`.mcp.json` → `.claude/settings.json`)
- v1.4: Sprint 실행 가이드 섹션 추가 (역할 구조, Slack 오해, 구현 내용 설명)
- v1.5: PM 중심 워크플로우 테스트 섹션 추가 (Sprint 확인, Slack 알림, 트러블슈팅)
- v1.6: 표준화된 Slack 메시지 스크립트 (`send_slack.sh`) 반영, 한글/이모지 인코딩 해결책 추가
**기반**: 실제 구축 세션
