# Jira & Slack 초기 설정 퀵스타트 가이드

Jira와 Slack을 처음부터 설정하여 개발팀 협업을 시작하는 종합 가이드

**Version**: 1.1 | **Updated**: 2026-01-20

---

## 목차

1. [개요](#1-개요)
2. [Phase 1: 계정 생성](#2-phase-1-계정-생성)
3. [Phase 2: 워크스페이스 및 프로젝트 생성](#3-phase-2-워크스페이스-및-프로젝트-생성)
4. [Phase 3: 초기 설정](#4-phase-3-초기-설정)
5. [Phase 4: 서비스 연동](#5-phase-4-서비스-연동)
6. [Phase 5: Claude Code 연동](#6-phase-5-claude-code-연동)
7. [Phase 6: 팀 온보딩](#7-phase-6-팀-온보딩)
8. [체크리스트](#8-체크리스트)
9. [트러블슈팅](#9-트러블슈팅)

---

## 1. 개요

### 1.1 이 가이드의 목적

계정이 없는 상태에서 Jira/Slack 기반 개발팀 협업 환경을 처음부터 구축하는 방법을 안내합니다.

### 1.2 대상 독자

- Jira/Slack 계정이 없는 신규 프로젝트 리더
- 협업 도구를 처음 도입하는 팀
- 개발팀 협업 환경을 새로 구축해야 하는 담당자

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

### 1.4 필요한 도구

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

    A -.-> |"5분"| A
    B -.-> |"5분"| B
    C -.-> |"5분"| C
```

### 2.2 Atlassian 계정 생성 (Jira)

**URL**: https://www.atlassian.com/try/cloud/signup

**절차**:

```
1. 위 URL 접속
2. "Get it free" 클릭
3. 이메일 주소 입력 (업무용 권장)
4. 이메일 인증 완료
5. 이름, 비밀번호 설정
6. Site 이름 입력 (예: your-company)
   → your-company.atlassian.net 형태로 생성됨
7. 팀 규모 선택 (1-10명)
8. 제품 선택: "Jira Software" 체크
9. 완료
```

**주의사항**:
- Site 이름은 나중에 변경하기 어려우므로 신중하게 선택
- 업무용 이메일 사용 권장 (팀원 초대 시 신뢰도)
- Free 플랜은 10명까지 무료

### 2.3 Slack 계정 생성

**URL**: https://slack.com/get-started

**절차**:

```
1. 위 URL 접속
2. "Create a new workspace" 선택
3. 이메일 주소 입력
4. 이메일로 받은 인증 코드 입력
5. 워크스페이스 이름 입력 (예: Hybrid RAG Team)
6. 프로젝트/팀 설명 입력
7. 팀원 초대 (나중에 가능, 스킵 가능)
8. 완료
```

**주의사항**:
- 워크스페이스 이름은 나중에 변경 가능
- 회사 도메인 이메일 사용 시 기존 워크스페이스 발견될 수 있음

### 2.4 GitHub 계정 생성 (선택)

**URL**: https://github.com/signup

이미 계정이 있다면 스킵합니다.

**절차**:

```
1. 위 URL 접속
2. 이메일 주소 입력
3. 비밀번호 설정
4. 사용자명 입력 (공개됨)
5. 이메일 수신 여부 선택
6. 보안 퍼즐 완료
7. 이메일 인증
8. 완료
```

---

## 3. Phase 2: 워크스페이스 및 프로젝트 생성

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

### 3.2 Slack 채널 구조 생성

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

### 3.3 GitHub Repository 생성 (선택)

```
1. github.com → "+" → "New repository"
2. Repository name: hybrid-rag-knowledge-ops
3. Description: Graph RAG 기반 지식 검색 시스템
4. Visibility: Private (또는 Public)
5. Initialize with README 체크
6. Add .gitignore: Python
7. "Create repository" 클릭
```

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

# 구독 해제
/github unsubscribe owner/hybrid-rag-knowledge-ops
```

**알림 채널 설정**:
- #proj-hrkp-review: PR, reviews, comments
- #proj-hrkp-alerts: deployments, releases

### 5.3 연동 테스트

**Jira 연동 테스트**:
```
1. Jira에서 테스트 이슈 생성
2. Slack #proj-hrkp-alerts 채널에서 알림 확인
3. Slack에서 /jira create 명령어 테스트
```

**GitHub 연동 테스트**:
```
1. GitHub에서 테스트 PR 생성
2. Slack #proj-hrkp-review 채널에서 알림 확인
3. PR 링크 붙여넣기로 프리뷰 확인
```

---

## 6. Phase 5: Claude Code 연동

### 6.1 API 토큰 발급

#### 6.1.1 Jira API 토큰

```
1. https://id.atlassian.com/manage-profile/security/api-tokens 접속
2. "Create API token" 클릭
3. Label: "Claude Code Integration"
4. "Create" 클릭
5. 토큰 복사 (한 번만 표시됨!)
```

#### 6.1.2 Slack Bot 토큰

```
1. https://api.slack.com/apps 접속
2. "Create New App" → "From scratch"
3. App Name: "HRKP Bot"
4. Workspace 선택
5. "OAuth & Permissions" 메뉴
6. Bot Token Scopes 추가:
   - chat:write
   - chat:write.public
   - channels:read
   - users:read
7. "Install to Workspace"
8. Bot User OAuth Token 복사 (xoxb-...)
```

#### 6.1.3 GitHub Personal Access Token

```
1. github.com → Settings → Developer settings
2. Personal access tokens → Tokens (classic)
3. "Generate new token (classic)"
4. Note: "Claude Code Integration"
5. Expiration: 90 days (또는 원하는 기간)
6. Scopes 선택:
   - repo (전체)
   - workflow
7. "Generate token"
8. 토큰 복사 (한 번만 표시됨!)
```

### 6.2 환경 변수 설정

**.env 파일 생성**:

```bash
# 프로젝트 루트에 .env 파일 생성
cat << 'EOF' > .env
# ===================
# Jira Configuration
# ===================
JIRA_HOST=your-company.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-jira-api-token
JIRA_PROJECT_KEY=HRKP

# ===================
# Slack Configuration
# ===================
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_CHANNEL_DEV=#proj-hrkp-dev
SLACK_CHANNEL_ALERTS=#proj-hrkp-alerts

# ===================
# GitHub Configuration
# ===================
GITHUB_TOKEN=ghp_your-github-token
GITHUB_REPO=owner/hybrid-rag-knowledge-ops
EOF
```

**.gitignore에 추가**:
```bash
echo ".env" >> .gitignore
```

### 6.3 MCP Server 설정

> ⚠️ **주의**: MCP 설정은 `.mcp.json`이 아닌 **`.claude/settings.json`** 파일에 작성해야 합니다. Claude Code는 `.mcp.json`을 읽지 않습니다.

**`.claude/settings.json` 파일**에 `mcpServers` 섹션 추가:

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

> 📝 **참고**:
> - Slack은 공식 MCP 서버가 없어 Bot Token + REST API 방식 사용 (섹션 6.1.2 참조)
> - API 토큰은 `${환경변수}` 형식으로 참조하여 보안 유지
> - 기존 `.claude/settings.json`에 다른 설정이 있다면 `mcpServers` 키만 추가

### 6.4 연결 테스트

```bash
# Claude Code 실행
claude

# MCP 상태 확인
> /mcp status

# Jira 연결 테스트
> "HRKP 프로젝트 이슈 목록을 보여줘"

# Slack 연결 테스트
> "#proj-hrkp-dev 채널에 테스트 메시지 보내줘"

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
| 이 가이드 | 초기 설정 | docs/07_Jira_Slack_초기설정_퀵스타트_가이드.md |
| Jira 가이드 | Jira 사용법 | docs/05_Jira_Agile_프로젝트_관리_가이드.md |
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

### 7.4 데일리 스탠드업 시작

**Slack 스탠드업 봇 설정** (Workflow Builder 사용):

```
1. Slack → Tools → Workflow Builder
2. "Create Workflow"
3. Trigger: Scheduled (매일 09:00)
4. Action: Send a message to #proj-hrkp-standup

메시지 내용:
🌅 **Daily Standup - {{date}}**
━━━━━━━━━━━━━━━━━━━━━━━

아래 형식으로 스레드에 답글 남겨주세요:

**어제 한 일**:
-

**오늘 할 일**:
-

**블로커/도움 필요**:
-

━━━━━━━━━━━━━━━━━━━━━━━
⏰ 마감: 오전 10:00
```

---

## 8. 체크리스트

### 8.1 전체 체크리스트

**Phase 1: 계정 생성**
- [ ] Atlassian 계정 생성 완료
- [ ] Slack 계정 생성 완료
- [ ] GitHub 계정 생성/확인 완료

**Phase 2: 프로젝트/워크스페이스 생성**
- [ ] Jira Site 생성 완료
- [ ] HRKP 프로젝트 생성 완료
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
- [ ] Jira API 토큰 발급
- [ ] Slack Bot 토큰 발급
- [ ] GitHub PAT 발급
- [ ] .env 파일 생성
- [ ] .claude/settings.json에 mcpServers 설정
- [ ] MCP 연결 테스트

**Phase 6: 팀 온보딩**
- [ ] 팀원 Jira 초대
- [ ] 팀원 Slack 초대
- [ ] 팀원 GitHub 추가
- [ ] 온보딩 문서 공유
- [ ] 첫 Epic 생성
- [ ] 첫 Sprint 시작
- [ ] 데일리 스탠드업 설정

### 8.2 환경 변수 체크 스크립트

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

## 9. 트러블슈팅

### 9.1 일반적인 문제

| 문제 | 원인 | 해결 |
|------|------|------|
| Jira 로그인 안됨 | 이메일 미인증 | 가입 시 받은 인증 이메일 확인 |
| Slack 워크스페이스 안보임 | 다른 계정으로 로그인 | 계정 확인 후 재로그인 |
| GitHub 연동 실패 | 권한 부족 | 토큰 Scope 확인 |
| MCP 연결 실패 | 환경 변수 미설정 | .env 파일 및 환경 변수 확인 |

### 9.2 Jira 연동 문제

```bash
# Jira API 연결 테스트
curl -u "${JIRA_EMAIL}:${JIRA_API_TOKEN}" \
  "https://${JIRA_HOST}/rest/api/3/myself"

# 성공 시: 사용자 정보 JSON 반환
# 실패 시: 401/403 에러
```

| 에러 코드 | 원인 | 해결 |
|----------|------|------|
| 401 | 인증 실패 | 이메일/토큰 확인 |
| 403 | 권한 없음 | 프로젝트 권한 확인 |
| 404 | 리소스 없음 | Host/프로젝트 키 확인 |

### 9.3 Slack 연동 문제

```bash
# Slack API 연결 테스트
curl -X POST -H "Authorization: Bearer ${SLACK_BOT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"channel":"#general","text":"Test"}' \
  https://slack.com/api/chat.postMessage
```

| 에러 | 원인 | 해결 |
|------|------|------|
| invalid_auth | 잘못된 토큰 | Bot Token 재확인 |
| channel_not_found | 채널 없음 | 채널명 확인 |
| not_in_channel | Bot 미초대 | `/invite @bot` 실행 |

### 9.4 GitHub 연동 문제

```bash
# GitHub API 연결 테스트
curl -H "Authorization: token ${GITHUB_TOKEN}" \
  https://api.github.com/user
```

| 에러 | 원인 | 해결 |
|------|------|------|
| Bad credentials | 토큰 오류 | 새 토큰 발급 |
| Not found | 접근 권한 없음 | 토큰 Scope 확인 |

---

## 참고 자료

### 공식 문서
- [Atlassian 시작하기](https://www.atlassian.com/software/jira/guides/getting-started)
- [Slack 시작하기](https://slack.com/help/articles/206845317-Create-a-Slack-workspace)
- [GitHub Docs](https://docs.github.com/en/get-started)

### 프로젝트 내 문서
- [Jira & Agile 가이드](./05_Jira_Agile_프로젝트_관리_가이드.md)
- [Slack 커뮤니케이션 가이드](./06_Slack_프로젝트_커뮤니케이션_가이드.md)
- [개발자 통합 가이드](../knowledge_service/docs/05_development/developer_integration_guide.md)
- [CLAUDE.md](../CLAUDE.md)

---

## Quick Reference Card

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
