# Jira & Slack & Claude Code 통합 가이드

Jira/Slack 계정 생성부터 Claude Code 연동, Sprint 자동화까지 종합 가이드

**Version**: 2.0 | **Updated**: 2026-01-22
**통합**: 초기설정 퀵스타트 가이드 + 실전 매뉴얼

---

## 목차

### Part 1: 초기 설정
1. [개요](#1-개요)
2. [Phase 1: 계정 생성](#2-phase-1-계정-생성)
3. [Phase 2: 프로젝트/워크스페이스 생성](#3-phase-2-프로젝트워크스페이스-생성)
4. [Phase 3: 초기 설정](#4-phase-3-초기-설정)
5. [Phase 4: 서비스 연동](#5-phase-4-서비스-연동)
6. [Phase 5: Claude Code 연동](#6-phase-5-claude-code-연동)
7. [Phase 6: 팀 온보딩](#7-phase-6-팀-온보딩)

### Part 2: 자동화 활용
8. [Jira 자동화 (REST API)](#8-jira-자동화-rest-api)
9. [백로그 → Jira 동기화](#9-백로그--jira-동기화)
10. [가상 팀원 Slack 자동화](#10-가상-팀원-slack-자동화)
11. [GitHub MCP 설정](#11-github-mcp-설정)
12. [Agent Mail & Beads 검토](#12-agent-mail--beads-검토)

### Part 3: Sprint 운영
13. [Sprint 실행 가이드](#13-sprint-실행-가이드)
14. [PM 중심 워크플로우](#14-pm-중심-워크플로우)

### Part 4: 참조
15. [트러블슈팅](#15-트러블슈팅)
16. [Quick Reference](#16-quick-reference)
17. [체크리스트](#17-체크리스트)

---

# Part 1: 초기 설정

## 1. 개요

### 1.1 이 문서의 목적

Jira/Slack 계정이 없는 상태에서 시작하여, Claude Code를 통해 Jira 이슈를 자동 생성하고 백로그를 동기화하는 전체 과정을 안내합니다.

### 1.2 대상 독자

- Jira/Slack 계정이 없는 신규 프로젝트 리더
- 협업 도구를 처음 도입하는 팀
- Claude Code와 연동하여 자동화하려는 개발자

### 1.3 전체 구축 로드맵

```mermaid
flowchart LR
    subgraph Phase1["Phase 1<br/>Day 1 오전"]
        A1["계정 생성"]
    end

    subgraph Phase2["Phase 2<br/>Day 1 오후"]
        A2["프로젝트/워크스페이스<br/>생성"]
    end

    subgraph Phase3["Phase 3<br/>Day 2 오전"]
        A3["초기 설정"]
    end

    subgraph Phase4["Phase 4<br/>Day 2 오후"]
        A4["서비스 연동"]
    end

    subgraph Phase5["Phase 5<br/>Day 3"]
        A5["Claude Code<br/>연동"]
    end

    subgraph Phase6["Phase 6<br/>Day 3-4"]
        A6["팀 온보딩"]
    end

    Phase1 --> Phase2 --> Phase3 --> Phase4 --> Phase5 --> Phase6
```

### 1.4 구축 아키텍처

```mermaid
flowchart TB
    subgraph Tools["협업 도구"]
        Jira["Jira Cloud<br/>이슈/스프린트 관리"]
        Slack["Slack<br/>팀 커뮤니케이션"]
    end

    subgraph Claude["Claude Code"]
        MCP["MCP Server<br/>(Jira, GitHub)"]
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

### 1.5 필요한 도구

| 도구 | 역할 | 비용 (소규모 팀) |
|------|------|-----------------|
| **Jira Software** | 이슈/스프린트 관리 | Free (10명까지) |
| **Slack** | 팀 커뮤니케이션 | Free |
| **GitHub** | 소스 코드 관리 | Free |
| **Claude Code** | AI 개발 지원 | 별도 |

---

## 2. Phase 1: 계정 생성

### 2.1 계정 생성 순서

```mermaid
flowchart TB
    A["1. Atlassian 계정<br/>(Jira용)"] --> B["2. Slack 계정"]
    B --> C["3. GitHub 계정<br/>(있으면 스킵)"]
```

### 2.2 Atlassian 계정 생성 (Jira)

**URL**: https://www.atlassian.com/try/cloud/signup

**절차**:
```
1. "Get it free" 클릭
2. 이메일 주소 입력 (업무용 권장)
3. 이메일 인증 완료
4. 이름, 비밀번호 설정
5. Site 이름 입력 (예: your-company)
   → your-company.atlassian.net 형태로 생성됨
6. 팀 규모 선택 (1-10명)
7. 제품 선택: "Jira Software" 체크
8. 완료
```

**주의사항**:
- Site 이름은 나중에 변경하기 어려우므로 신중하게 선택
- 업무용 이메일 사용 권장 (팀원 초대 시 신뢰도)
- Free 플랜은 10명까지 무료

### 2.3 Slack 계정 생성

**URL**: https://slack.com/get-started

**절차**:
```
1. "Create a new workspace" 선택
2. 이메일 주소 입력
3. 이메일로 받은 인증 코드 입력
4. 워크스페이스 이름 입력 (예: Hybrid RAG Team)
5. 프로젝트/팀 설명 입력
6. 팀원 초대 (나중에 가능, 스킵 가능)
7. 완료
```

**주의사항**:
- 워크스페이스 이름은 나중에 변경 가능
- 회사 도메인 이메일 사용 시 기존 워크스페이스 발견될 수 있음

### 2.4 GitHub 계정 생성 (선택)

**URL**: https://github.com/signup

이미 계정이 있다면 스킵합니다.

---

## 3. Phase 2: 프로젝트/워크스페이스 생성

### 3.1 Jira 프로젝트 생성

**접속**: https://your-company.atlassian.net

```mermaid
flowchart TB
    A["Jira 홈"] --> B["Projects 메뉴"]
    B --> C["Create project"]
    C --> D["템플릿 선택<br/>(Scrum/Kanban)"]
    D --> E["프로젝트 정보 입력"]
    E --> F["생성 완료"]
```

**상세 절차**:
```
1. Jira 홈 → 상단 "Projects" 클릭
2. "Create project" 버튼 클릭
3. 템플릿 선택:
   - Scrum: 스프린트 기반 개발 (권장)
   - Kanban: 연속적 흐름 관리
4. "Use template" 클릭
5. 프로젝트 정보 입력:
   - Name: Hybrid RAG Knowledge Ops
   - Key: HRKP (자동 생성, 수정 가능)
   - Access: Open (팀원 누구나 접근)
6. "Create project" 클릭
```

**프로젝트 키(Key) 선택 팁**:
- 3-4글자의 약어 사용
- 이슈 번호에 사용됨 (예: HRKP-123)
- 생성 후 변경 불가

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

### 3.2 Jira API 토큰 발급

**URL**: https://id.atlassian.com/manage-profile/security/api-tokens

```
1. "Create API token" 클릭
2. Label 입력: "Claude Code Integration"
3. "Create" 클릭
4. 토큰 복사 (한 번만 표시됨!)
```

**주의**: 토큰은 `ATATT3xFfGF0...` 형식이며, 절대 git에 커밋하지 마세요.

### 3.3 Slack 채널 구조 생성

**권장 채널 구조**:

```mermaid
flowchart TB
    subgraph Workspace["Hybrid RAG Team 워크스페이스"]
        subgraph Project["프로젝트 채널"]
            Ch1["#proj-hrkp-general<br/>일반 소통, 공지"]
            Ch2["#proj-hrkp-dev<br/>개발 논의"]
            Ch3["#proj-hrkp-standup<br/>데일리 스탠드업"]
            Ch4["#proj-hrkp-review<br/>PR/코드 리뷰"]
            Ch5["#proj-hrkp-alerts<br/>CI/CD 알림"]
        end

        subgraph Common["공통 채널"]
            Ch6["#general<br/>(기본)"]
            Ch7["#random<br/>(자유)"]
        end
    end
```

**채널 생성 절차**:
```
1. Slack 좌측 "Channels" 옆 "+" 클릭
2. "Create a channel" 선택
3. 채널 정보 입력:
   - Name: proj-hrkp-general
   - Description: HRKP 프로젝트 일반 소통 및 공지
   - Visibility: Public (팀원 누구나 참여)
4. "Create" 클릭
5. 나머지 채널도 동일하게 생성
```

**채널별 설정**:

| 채널 | 용도 | Visibility | 알림 설정 |
|------|------|------------|----------|
| #proj-hrkp-general | 일반 소통 | Public | All messages |
| #proj-hrkp-dev | 개발 논의 | Public | Mentions |
| #proj-hrkp-standup | 데일리 스탠드업 | Public | All messages |
| #proj-hrkp-review | PR 리뷰 알림 | Public | Mentions |
| #proj-hrkp-alerts | 자동화 알림 | Public | Nothing (필요시 확인) |

---

## 4. Phase 3: 초기 설정

### 4.1 Jira 프로젝트 설정

#### 4.1.1 Issue Types 설정

```
Project Settings → Issue types

활성화할 이슈 타입:
✅ Epic - 대규모 기능/목표
✅ Story - 사용자 기능
✅ Task - 기술 작업
✅ Bug - 결함
✅ Sub-task - 하위 작업
```

#### 4.1.2 Workflow 설정

```mermaid
stateDiagram-v2
    [*] --> ToDo
    ToDo --> InProgress: Start
    InProgress --> InReview: Submit
    InReview --> InProgress: Changes Requested
    InReview --> Done: Approve
    Done --> [*]
```

```
Project Settings → Workflows → Edit

상태 추가/수정:
1. To Do (시작 상태)
2. In Progress (진행 중)
3. In Review (리뷰 중)
4. Done (완료)

트랜지션 설정:
- To Do → In Progress: "Start Work"
- In Progress → In Review: "Submit for Review"
- In Review → In Progress: "Request Changes"
- In Review → Done: "Approve"
```

#### 4.1.3 Board 설정

```
Project Settings → Board → Columns

컬럼 구성:
| To Do | In Progress | In Review | Done |
|-------|-------------|-----------|------|
| 대기  | 진행 중     | 리뷰 중   | 완료 |

WIP 제한 (선택):
- In Progress: 3
- In Review: 2
```

#### 4.1.4 Components 추가

```
Project Settings → Components → Create

추가할 컴포넌트:
1. Backend - SpringBoot API 관련
2. Frontend - React UI 관련
3. AI-Service - Python/RAG 관련
4. Infrastructure - DevOps 관련
5. Documentation - 문서 관련
```

### 4.2 Slack 워크스페이스 설정

#### 4.2.1 워크스페이스 설정

```
Settings & administration → Workspace settings

권장 설정:
- Default channels: #general, #proj-hrkp-general
- Message retention: Keep all messages (Free 플랜 제한 있음)
- File sharing: Allow all file types
```

#### 4.2.2 사용자 그룹 생성

```
People & User Groups → User Groups → Create User Group

생성할 그룹:
1. @dev-team - 개발팀 전체
2. @backend-team - 백엔드 개발자
3. @frontend-team - 프론트엔드 개발자
4. @oncall - 당번 담당자
```

#### 4.2.3 채널 토픽 설정

각 채널에 토픽 설정:

```
#proj-hrkp-general:
📌 HRKP 프로젝트 일반 채널 | 스프린트: Sprint 01 | 기간: 01/20-01/31

#proj-hrkp-standup:
🌅 매일 09:00 스탠드업 | 형식: 어제/오늘/블로커 | 마감: 10:00

#proj-hrkp-review:
👀 PR 리뷰 채널 | 리뷰 SLA: 24시간 내 | 멘션: @dev-team
```

---

## 5. Phase 4: 서비스 연동

### 5.1 Jira ↔ Slack 연동

```mermaid
flowchart LR
    Jira["Jira Cloud"] --> |"이슈 알림"| Slack["Slack"]
    Slack --> |"/jira 명령어"| Jira
```

**설치 절차**:

```
1. Slack → Apps → 검색: "Jira Cloud"
2. "Add to Slack" 클릭
3. 권한 허용
4. Atlassian 계정 연결
   - "Connect to Jira" 클릭
   - Atlassian 로그인
   - 권한 허용
5. 기본 채널 설정: #proj-hrkp-alerts
```

**Slack에서 Jira 사용**:

```bash
# 프로젝트 연결
/jira connect

# 이슈 생성
/jira create HRKP

# 이슈 조회 (링크 붙여넣기로 자동 프리뷰)
HRKP-123
```

**알림 설정**:

```
Jira → Project Settings → Slack integration

알림 설정:
✅ Issue created
✅ Issue updated
✅ Issue commented
✅ Sprint started/completed
```

### 5.2 GitHub ↔ Slack 연동

**설치 절차**:

```
1. Slack → Apps → 검색: "GitHub"
2. "Add to Slack" 클릭
3. 권한 허용
4. GitHub 계정 연결
   - /github signin
   - GitHub 로그인 및 권한 허용
```

**Repository 구독**:

```bash
# 기본 구독 (PR, issues, deployments, releases)
/github subscribe owner/hybrid-rag-knowledge-ops

# 특정 이벤트만 구독
/github subscribe owner/hybrid-rag-knowledge-ops pulls commits releases

# 구독 상태 확인
/github subscribe list
```

**알림 채널 설정**:
- #proj-hrkp-review: PR, reviews, comments
- #proj-hrkp-alerts: deployments, releases

### 5.3 연동 문제 해결

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

---

## 6. Phase 5: Claude Code 연동

### 6.1 환경 변수 파일 생성

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
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_WORKSPACE=your-workspace
SLACK_CHANNEL_GENERAL=#proj-hrkp-general
SLACK_CHANNEL_DEV=#proj-hrkp-dev
SLACK_CHANNEL_ALERTS=#proj-hrkp-alerts

# ===========================================
# GitHub Configuration
# ===========================================
GITHUB_TOKEN=ghp_your-github-token
GITHUB_REPO=owner/hybrid-rag-knowledge-ops
```

**.gitignore에 추가**:
```
.env
.env.local
.claude/settings.local.json
```

### 6.2 MCP 설정

> ⚠️ **주의**: MCP 설정은 프로젝트 루트의 **`.mcp.json`** 파일에 작성합니다.

**.mcp.json 파일**:

```json
{
  "mcpServers": {
    "jira": {
      "command": "npx",
      "args": ["-y", "mcp-server-jira-cloud"],
      "env": {
        "JIRA_BASE_URL": "https://your-project.atlassian.net",
        "JIRA_EMAIL": "your-email@example.com",
        "JIRA_API_TOKEN": "your-jira-api-token"
      }
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"]
    },
    "slack": {
      "command": "npx",
      "args": ["-y", "mcp-server-slack"],
      "env": {
        "SLACK_TEAM_ID": "T0XXXXXXXXX",
        "SLACK_BOT_TOKEN": "xoxb-your-slack-bot-token"
      }
    }
  }
}
```

> ⚠️ **중요**: `JIRA_BASE_URL`은 `https://` 프로토콜을 포함해야 합니다.
> `.mcp.json`은 `.gitignore`에 포함되어 있어 토큰을 직접 입력해도 안전합니다.

### 6.3 환경 변수 로드

```bash
# 현재 세션에 환경 변수 로드
source .env

# 또는 direnv 사용 (권장)
echo "dotenv" > .envrc
direnv allow
```

### 6.4 연결 테스트

```bash
# Claude Code 실행
claude

# MCP 상태 확인
> /mcp status

# Jira 연결 테스트
> "HRKP 프로젝트 이슈 목록을 보여줘"

# GitHub 연결 테스트
> "최근 PR 목록을 보여줘"
```

---

## 7. Phase 6: 팀 온보딩

### 7.1 팀원 초대

#### 7.1.1 Jira 팀원 초대

```
1. Jira → 프로젝트 → Project settings
2. "People" 메뉴
3. "Add people" 클릭
4. 이메일 주소 입력
5. Role 선택:
   - Administrator: 프로젝트 설정 가능
   - Member: 이슈 생성/수정 가능
   - Viewer: 읽기만 가능
6. "Add" 클릭
```

#### 7.1.2 Slack 팀원 초대

```
1. Slack → 워크스페이스 이름 클릭
2. "Invite people to [workspace]"
3. 이메일 주소 입력 (여러 명 가능)
4. 기본 채널 선택
5. "Send" 클릭
```

#### 7.1.3 GitHub Collaborator 추가

```
1. GitHub → Repository → Settings
2. "Collaborators and teams"
3. "Add people"
4. 사용자명 또는 이메일 입력
5. Role 선택:
   - Read: 읽기만
   - Write: 푸시 가능
   - Maintain: 브랜치 관리 가능
   - Admin: 전체 관리
6. "Add" 클릭
```

### 7.2 온보딩 문서 공유

팀원에게 공유할 문서:

| 문서 | 용도 | 위치 |
|------|------|------|
| 이 가이드 | 전체 설정 | docs/07_Jira_Slack_Claude_통합가이드.md |
| Slack 가이드 | Slack 사용법 | docs/06_Slack_프로젝트_커뮤니케이션_가이드.md |
| 개발자 통합 가이드 | 연동 상세 | knowledge_service/docs/05_development/developer_integration_guide.md |

### 7.3 첫 스프린트 준비

#### 7.3.1 첫 Epic 생성

```
Jira → Backlog → Create Epic

Epic 정보:
- Summary: Document Processing Pipeline
- Description: 문서 업로드부터 벡터 저장까지 전체 파이프라인 구축
- Labels: phase-1
```

#### 7.3.2 첫 Story 생성

```
Jira → Backlog → Create

Story 정보:
- Issue Type: Story
- Summary: 문서 업로드 API 구현
- Description:
  As a 지식 관리자,
  I want 다양한 형식의 문서를 업로드,
  So that 문서가 자동으로 처리 대기열에 추가됨.
- Story Points: 3
- Epic Link: Document Processing Pipeline
```

#### 7.3.3 스프린트 생성 및 시작

```
1. Jira → Backlog
2. "Create sprint" 클릭
3. Sprint 이름: Sprint 01
4. 기간: 2주 (시작일 ~ 종료일)
5. 스프린트 목표: "문서 처리 파이프라인 1단계 완성"
6. 백로그에서 이슈들을 스프린트로 드래그
7. "Start sprint" 클릭
```

---

# Part 2: 자동화 활용

## 8. Jira 자동화 (REST API)

Claude Code에서 curl 명령어로 Jira API를 직접 호출할 수 있습니다.

### 8.1 Epic 생성

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

### 8.2 Story 생성 (Epic 하위)

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

### 8.3 Sprint 생성 및 이슈 할당

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

### 8.4 Claude Code 프롬프트 예시

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

## 9. 백로그 → Jira 동기화

### 9.1 백로그 파일 구조

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

### 9.2 백로그 파일 형식

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

### 9.3 동기화 프로세스

```mermaid
flowchart LR
    A["백로그 파일<br/>(Markdown)"] --> B["Claude Code<br/>파싱"]
    B --> C["Jira API<br/>이슈 생성"]
    C --> D["Jira Key<br/>반환"]
    D --> E["백로그 파일<br/>업데이트"]
```

### 9.4 동기화 후 업데이트

Claude Code가 이슈 생성 후 백로그 파일에 Jira ID를 자동 반영:

```markdown
# Before
| **Jira ID** | - (미등록) |

# After
| **Jira ID** | SCRUM-5 |
```

---

## 10. 가상 팀원 Slack 자동화

Claude Code 에이전트(가상 팀원)가 Slack에 메시지를 자동으로 전송하여 협업 기록을 남기는 방법입니다.

### 10.1 가상 팀원 개념

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

### 10.2 Slack Bot Token 발급

가상 팀원이 Slack에 메시지를 보내려면 Bot Token이 필요합니다.

#### Step 1: Slack App 생성

1. **https://api.slack.com/apps** 접속
2. **"Create New App"** → **"From scratch"** 선택
3. 설정:
   - App Name: `HRKP Virtual Team`
   - Workspace: 선택
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

### 10.3 Slack 메시지 전송

#### 표준화된 스크립트 사용 (권장)

```bash
# 스크립트 위치: scripts/send_slack.sh
# 사용법: ./scripts/send_slack.sh <채널> <에이전트> "메시지"

# PM 메시지
./scripts/send_slack.sh proj-hrkp-dev PM "Sprint 01 요구사항 정의 완료"

# Backend 메시지
./scripts/send_slack.sh proj-hrkp-dev Backend "STORY-001 착수합니다"

# 전체 에이전트 일괄 인사
./scripts/standup_all.sh
```

#### 기본 curl 방식

```bash
curl -s -X POST "https://slack.com/api/chat.postMessage" \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "proj-hrkp-dev",
    "text": "*[PM]* Sprint 01 요구사항 정의 완료"
  }'
```

### 10.4 가상 팀원 메시지 포맷 규칙

| 역할 | Slack 메시지 형식 | 작업 영역 |
|------|------------------|----------|
| PM | `*[PM]*` | specs/ |
| TechLead | `*[TechLead]*` | docs/ |
| Backend | `*[Backend]*` | backend/ |
| Frontend | `*[Frontend]*` | frontend/ |
| MLRag | `*[MLRag]*` | ai-service/ |
| Data | `*[Data]*` | etl/, graph/ |
| QA | `*[QA]*` | tests/ |
| DevOps | `*[DevOps]*` | infrastructure/ |

### 10.5 협업 워크플로우

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

---

## 11. GitHub MCP 설정

GitHub MCP를 설정하면 PR 생성, 이슈 관리, 코드 리뷰 등을 Claude Code에서 직접 수행할 수 있습니다.

### 11.1 MCP 서버 선택 기준

| MCP 서버 | 선택 | 사유 |
|---------|------|------|
| **Jira MCP** | ✅ 필수 | 이슈/스프린트 관리 자동화 |
| **GitHub MCP** | ✅ 필수 | PR 생성, 코드 리뷰, 이슈 연동 |
| **Slack MCP** | ⚠️ 선택 | Bot Token + REST API로도 가능 |
| **Filesystem MCP** | ❌ 불필요 | Claude Code 내장 도구로 대체 |

### 11.2 GitHub Personal Access Token 발급

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

### 11.3 GitHub MCP 사용 예시

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

## 12. Agent Mail & Beads 검토

MCP 기반 에이전트 간 통신 도구인 Agent Mail과 Beads의 적용 필요성을 검토한 결과입니다.

### 12.1 Agent Mail이란?

Jeffrey Emanuel이 개발한 **MCP Agent Mail**은 서로 다른 Claude Code 세션 간 비동기 메시징을 가능하게 합니다.

### 12.2 적용 필요성 판단

#### 결론: **현재 프로젝트에서는 불필요**

| 판단 기준 | Agent Mail 필요 조건 | 현재 상황 |
|----------|---------------------|----------|
| 세션 구조 | 여러 터미널에서 별도 세션 실행 | 단일 세션에서 모든 에이전트 실행 |
| 통신 방식 | 세션 간 비동기 메시징 필요 | 세션 내 동기 처리 가능 |
| 기록 방식 | 파일 기반 메일함 필요 | Jira/Slack API로 기록 |

### 12.3 현재 프로젝트의 통신 방식

| 통신 유형 | 도구 | 기록 위치 |
|----------|------|----------|
| 작업 상태 공유 | Jira REST API | Jira 이슈/코멘트 |
| 팀 내 알림 | Slack Bot API | Slack 채널 메시지 |
| 상세 기록 | 로컬 파일 | `work_logs/` 디렉토리 |
| 코드 협업 | GitHub MCP | PR, 코멘트 |

### 12.4 Agent Mail이 필요한 시나리오

향후 다음 상황에서는 Agent Mail 도입을 검토할 수 있습니다:

| 시나리오 | 설명 |
|---------|------|
| 다중 터미널 운영 | 각 터미널에서 별도 에이전트 실행 시 |
| 장기 실행 작업 | 한 에이전트의 작업 완료를 다른 에이전트가 대기 |
| 팀 규모 확대 | 여러 개발자가 각자 Claude Code 세션 운영 |
| 분산 처리 | 작업을 여러 세션에 분산하여 병렬 처리 |

---

# Part 3: Sprint 운영

## 13. Sprint 실행 가이드

Claude Code로 실제 Sprint를 실행하는 방법과 사용자 역할을 설명합니다.

### 13.1 역할 구조

```
┌─────────────────────────────────────────────────────┐
│  YOU (Project Owner / Product Owner)                │
│  └─→ Claude Code에 직접 지시                        │
│  └─→ 코드 리뷰 및 승인                              │
│  └─→ 의사결정 (기술 선택, 우선순위 등)               │
│  └─→ 결과물 테스트 및 피드백                        │
└─────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────┐
│  Claude Code (개발 실행자)                          │
│  └─→ 필요시 가상 에이전트(PM, Backend 등) 호출      │
│  └─→ Jira API로 이슈 상태 업데이트                  │
│  └─→ 코드 작성, 테스트 실행                         │
│  └─→ PR 생성, 문서 업데이트                         │
└─────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────┐
│  Jira: 작업 추적  │  Slack: 알림/로그 (선택)        │
└─────────────────────────────────────────────────────┘
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

### 13.4 Sprint 중 사용자 역할

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

### 13.5 Sprint 명령어 요약

| 명령 | 설명 |
|------|------|
| `"Sprint 01 시작해줘"` | Sprint 킥오프 |
| `"SCRUM-6 구현해줘"` | 특정 Story 착수 |
| `"현재 진행 상황 알려줘"` | 진행률 확인 |
| `"SCRUM-6 In Review로 변경해줘"` | Jira 상태 변경 |
| `/workflows:feature-development` | 전체 사이클 자동화 |
| `"PR 생성해줘"` | 코드 리뷰 요청 |

---

## 14. PM 중심 워크플로우

PM Agent가 Sprint를 관리하고 Slack에 알림을 보내는 워크플로우입니다.

### 14.1 PM Agent 실행 흐름

```mermaid
flowchart TB
    User["사용자: Sprint 01 확인해줘"] --> Claude["Claude Code"]
    Claude --> PM["PM Agent 호출<br/>(Task tool)"]
    PM --> Load["Sprint 백로그 로드<br/>backlog/sprints/sprint-01.md"]
    Load --> Analyze["Sprint 분석<br/>• 기간 확인<br/>• Story 목록 확인<br/>• SP 합계 계산"]
    Analyze --> Report["결과 보고"]
    Report --> Slack["Slack 알림 전송<br/>proj-hrkp-dev"]
```

### 14.2 PM 필수 Slack 알림 규칙

PM Agent는 다음 시점에 **반드시** Slack 알림을 보내야 합니다:

| 시점 | 채널 | 메시지 형식 |
|------|------|------------|
| Sprint 시작 | proj-hrkp-dev | `*[PM]* 🚀 Sprint XX 시작!` |
| Sprint 상태 확인 | proj-hrkp-dev | `*[PM]* 📋 Sprint XX 현황 보고` |
| Story 할당 | proj-hrkp-dev | `*[PM]* 📋 작업 할당: SCRUM-XX` |
| Story 완료 | proj-hrkp-dev | `*[PM]* ✅ Story 완료: SCRUM-XX` |
| Sprint 종료 | proj-hrkp-dev | `*[PM]* 🏁 Sprint XX 종료!` |
| 블로커 발생 | proj-hrkp-alerts | `*[PM]* ⚠️ 블로커 발생: SCRUM-XX` |

---

# Part 4: 참조

## 15. 트러블슈팅

### 15.1 Jira API 오류

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

### 15.2 Jira-Slack 연동 오류

| 오류 | 원인 | 해결 |
|------|------|------|
| No Jira sites found | 계정 미연결 | `/jira connect` 재실행 |
| Site not accessible | 권한 없음 | Jira 관리자 확인 |
| Integration app error | 앱 설정 오류 | 앱 재설치 |

### 15.3 Sprint 생성 오류

| 오류 | 원인 | 해결 |
|------|------|------|
| 이름 30자 초과 | Sprint 이름 제한 | 이름 축소 |
| Board not found | 잘못된 보드 ID | 보드 조회 후 재시도 |
| Invalid date | 날짜 형식 오류 | ISO 8601 형식 사용 |

### 15.4 Slack Bot API 오류

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

### 15.5 Claude Code MCP 오류

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

## 16. Quick Reference

### 16.1 URL 모음

| 서비스 | URL |
|--------|-----|
| Jira 가입 | https://www.atlassian.com/try/cloud/signup |
| Jira API 토큰 | https://id.atlassian.com/manage-profile/security/api-tokens |
| Slack 가입 | https://slack.com/get-started |
| Slack Jira App | https://slack.com/apps/A2RPP3NFR-jira-cloud |
| Slack App 생성 | https://api.slack.com/apps |
| GitHub Token | https://github.com/settings/tokens |

### 16.2 주요 API 엔드포인트

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

### 16.3 Claude Code 명령어

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

### 16.4 Quick Reference Card

```
┌─────────────────────────────────────────────────────────────┐
│                    Quick Reference Card                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  [가입 URL]                                                  │
│  • Jira: atlassian.com/try/cloud/signup                     │
│  • Slack: slack.com/get-started                             │
│  • GitHub: github.com/signup                                │
│                                                              │
│  [토큰 발급 URL]                                             │
│  • Jira: id.atlassian.com/manage-profile/security/api-tokens│
│  • Slack: api.slack.com/apps                                │
│  • GitHub: github.com/settings/tokens                       │
│                                                              │
│  [Slack 명령어]                                              │
│  • /jira connect          - Jira 연결                       │
│  • /jira create HRKP      - 이슈 생성                       │
│  • /github signin         - GitHub 로그인                   │
│  • /github subscribe repo - 저장소 구독                     │
│                                                              │
│  [Claude Code 명령어]                                        │
│  • /mcp status            - MCP 상태 확인                   │
│  • /daily:daily-close     - 일일 마무리                     │
│  • /workflows:feature-development - 기능 개발               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 17. 체크리스트

### 17.1 전체 체크리스트

**Phase 1: 계정 생성**
- [ ] Atlassian 계정 생성 완료
- [ ] Slack 계정 생성 완료
- [ ] GitHub 계정 생성/확인 완료

**Phase 2: 프로젝트/워크스페이스 생성**
- [ ] Jira Site 생성 완료
- [ ] 프로젝트 생성 완료
- [ ] Jira API 토큰 발급
- [ ] Slack 워크스페이스 생성 완료
- [ ] 채널 5개 생성 완료
  - [ ] #proj-hrkp-general
  - [ ] #proj-hrkp-dev
  - [ ] #proj-hrkp-standup
  - [ ] #proj-hrkp-review
  - [ ] #proj-hrkp-alerts

**Phase 3: 초기 설정**
- [ ] Jira Issue Types 설정
- [ ] Jira Workflow 설정
- [ ] Jira Board 설정
- [ ] Jira Components 추가
- [ ] Slack User Groups 생성
- [ ] Slack 채널 토픽 설정

**Phase 4: 서비스 연동**
- [ ] Jira-Slack 연동 완료
- [ ] GitHub-Slack 연동 완료
- [ ] 연동 테스트 완료

**Phase 5: Claude Code 연동**
- [ ] .env 파일 생성
- [ ] .mcp.json 설정
- [ ] MCP 연결 테스트

**Phase 6: 팀 온보딩**
- [ ] 팀원 Jira 초대
- [ ] 팀원 Slack 초대
- [ ] 팀원 GitHub 추가
- [ ] 온보딩 문서 공유
- [ ] 첫 Epic 생성
- [ ] 첫 Sprint 시작

**Slack Bot (가상 팀원 자동화)**
- [ ] Slack App 생성 (api.slack.com)
- [ ] Bot Token Scopes 설정
- [ ] 앱 설치 및 Bot Token 발급
- [ ] .env에 SLACK_BOT_TOKEN 추가

**GitHub MCP**
- [ ] GitHub Personal Access Token 발급
- [ ] .env에 GITHUB_TOKEN 추가
- [ ] .mcp.json에 GitHub MCP 설정 추가
- [ ] Claude Code 재시작 후 /mcp 확인

### 17.2 환경 변수 체크 스크립트

```bash
#!/bin/bash
# check_env.sh - 환경 변수 확인 스크립트

echo "=== Integration Environment Check ==="
echo ""

# Jira
echo "[Jira]"
[ -z "$JIRA_HOST" ] && echo "  [ ] JIRA_HOST - 미설정" || echo "  [x] JIRA_HOST"
[ -z "$JIRA_EMAIL" ] && echo "  [ ] JIRA_EMAIL - 미설정" || echo "  [x] JIRA_EMAIL"
[ -z "$JIRA_API_TOKEN" ] && echo "  [ ] JIRA_API_TOKEN - 미설정" || echo "  [x] JIRA_API_TOKEN"
echo ""

# Slack
echo "[Slack]"
[ -z "$SLACK_BOT_TOKEN" ] && echo "  [ ] SLACK_BOT_TOKEN - 미설정" || echo "  [x] SLACK_BOT_TOKEN"
echo ""

# GitHub
echo "[GitHub]"
[ -z "$GITHUB_TOKEN" ] && echo "  [ ] GITHUB_TOKEN - 미설정" || echo "  [x] GITHUB_TOKEN"
echo ""

echo "=== Check Complete ==="
```

---

## 참고 문서

### 프로젝트 내 문서
- [Slack 커뮤니케이션 가이드](./06_Slack_프로젝트_커뮤니케이션_가이드.md)
- [Jira & Agile 가이드](./05_Jira_Agile_프로젝트_관리_가이드.md)
- [개발자 통합 가이드](../knowledge_service/docs/05_development/developer_integration_guide.md)

### 공식 문서
- [Jira REST API v3](https://developer.atlassian.com/cloud/jira/platform/rest/v3/)
- [Jira Agile REST API](https://developer.atlassian.com/cloud/jira/software/rest/)
- [Slack API](https://api.slack.com/)
- [Claude Code MCP](https://docs.anthropic.com/claude-code/mcp)

---

**문서 버전**: 2.0
**작성일**: 2026-01-22
**통합 원본**:
- 07_Jira_Slack_초기설정_퀵스타트_가이드.md (v1.1)
- 08_Jira_Slack_Claude_Code_실전_매뉴얼.md (v1.6)
