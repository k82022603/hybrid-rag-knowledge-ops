# DevOps & ALM 통합 계획서
## Hybrid RAG Knowledge Platform - 개발 라이프사이클 관리

---

## 문서 정보

| 항목 | 내용 |
|------|------|
| **문서명** | DevOps & ALM 통합 계획서 |
| **버전** | 1.0 |
| **작성일** | 2026-01-14 |
| **작성자** | Claude Code (Opus 4.5) |
| **상태** | 초안 |
| **참조 문서** | [PLAN.md](../../../PLAN.md), [상세 설계서](../02_design/01_hybrid_rag_platform_detailed_design.md) |

---

## 변경 이력

| 버전 | 일자 | 작성자 | 변경 내용 |
|------|------|--------|----------|
| 1.0 | 2026-01-14 | Claude Code | 초안 작성 |

---

## 목차

1. [개요](#1-개요)
2. [ALM 도구 구성](#2-alm-도구-구성)
3. [GitHub 구성](#3-github-구성)
4. [JIRA Cloud 구성](#4-jira-cloud-구성)
5. [Slack 통합](#5-slack-통합)
6. [AI 에이전트 협업](#6-ai-에이전트-협업)
7. [CI/CD 파이프라인](#7-cicd-파이프라인)
8. [릴리즈 관리](#8-릴리즈-관리)
9. [MCP 통합](#9-mcp-통합)
10. [모니터링 및 운영](#10-모니터링-및-운영)

---

## 1. 개요

### 1.1 목적

본 문서는 Hybrid RAG Knowledge Platform 프로젝트의 개발 라이프사이클 관리(ALM)와 DevOps 전략을 정의합니다. GitHub, JIRA Cloud, Slack을 통합하여 AI 에이전트와 인간 개발자가 협업하는 환경을 구축합니다.

### 1.2 ALM 전체 구조

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ALM Toolchain Overview                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                        Communication Layer                           │   │
│   │                     Slack (AI Agent Hub)                            │   │
│   │         Claude-Code | Antigravity | DeepSeek | Human                │   │
│   └───────────────────────────────┬─────────────────────────────────────┘   │
│                                   │                                          │
│   ┌───────────────────────────────┼─────────────────────────────────────┐   │
│   │                               │                                      │   │
│   │   ┌───────────────┐   ┌──────▼───────┐   ┌───────────────┐        │   │
│   │   │    GitHub     │   │ Integration  │   │  JIRA Cloud   │        │   │
│   │   │               │   │     Hub      │   │               │        │   │
│   │   │ • Repository  │◄──┤              ├──►│ • Backlog     │        │   │
│   │   │ • PR/Review   │   │ • Webhooks   │   │ • Kanban      │        │   │
│   │   │ • Actions     │   │ • APIs       │   │ • Sprints     │        │   │
│   │   │ • Projects    │   │ • MCP        │   │ • Releases    │        │   │
│   │   │ • Releases    │   │              │   │ • Reports     │        │   │
│   │   └───────┬───────┘   └──────────────┘   └───────────────┘        │   │
│   │           │                                                         │   │
│   │   ┌───────▼───────────────────────────────────────────────────────┐│   │
│   │   │                    CI/CD Pipeline                              ││   │
│   │   │     Build → Test → Lint → Security → Deploy → Monitor         ││   │
│   │   └───────────────────────────────────────────────────────────────┘│   │
│   │                                                                     │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.3 핵심 가치

| 가치 | 설명 | 구현 방법 |
|------|------|----------|
| **자동화** | 반복 작업 최소화 | CI/CD, 자동 배포 |
| **가시성** | 전체 현황 파악 | JIRA 대시보드, Slack 알림 |
| **협업** | AI-Human 협업 | Slack AI Agent, MCP |
| **품질** | 일관된 품질 보장 | 자동 테스트, 코드 리뷰 |
| **추적성** | 이력 관리 | Git, JIRA 연동 |

---

## 2. ALM 도구 구성

### 2.1 도구 매핑

| 영역 | 도구 | 역할 | 연동 |
|------|------|------|------|
| **소스 관리** | GitHub | 코드, 이슈, PR, Actions | JIRA, Slack |
| **프로젝트 관리** | JIRA Cloud | 백로그, 칸반, 릴리즈 | GitHub, Slack |
| **커뮤니케이션** | Slack | 알림, AI Agent, 협업 | GitHub, JIRA |
| **CI/CD** | GitHub Actions | 빌드, 테스트, 배포 | Slack 알림 |
| **AI 개발** | Claude Code | 코드 생성, 리뷰 | MCP, Slack |
| **문서** | GitHub Wiki | 기술 문서 | - |
| **모니터링** | Grafana + Prometheus | 시스템 모니터링 | Slack 알림 |

### 2.2 연동 다이어그램

```
                  ┌──────────────────┐
                  │   Developer      │
                  │   (Human/AI)     │
                  └────────┬─────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │    GitHub    │ │  JIRA Cloud  │ │    Slack     │
    │              │ │              │ │              │
    │ ┌──────────┐ │ │ ┌──────────┐ │ │ ┌──────────┐ │
    │ │   Code   │ │ │ │ Backlog  │ │ │ │ Channels │ │
    │ │   PR     │ │ │ │ Kanban   │ │ │ │ Bots     │ │
    │ │ Actions  │ │ │ │ Sprint   │ │ │ │ Alerts   │ │
    │ └────┬─────┘ │ │ └────┬─────┘ │ │ └────┬─────┘ │
    │      │       │ │      │       │ │      │       │
    └──────┼───────┘ └──────┼───────┘ └──────┼───────┘
           │                │                │
           └────────────────┼────────────────┘
                            │
                    ┌───────▼───────┐
                    │  Webhooks &   │
                    │  API Gateway  │
                    └───────────────┘
```

### 2.3 데이터 흐름

```
[JIRA Issue] ──► [GitHub Branch] ──► [PR] ──► [Review] ──► [Merge] ──► [Deploy]
     │                │                │          │           │          │
     ▼                ▼                ▼          ▼           ▼          ▼
[Slack 알림]    [CI 자동 실행]   [리뷰 요청]  [승인 알림]  [릴리즈]  [모니터링]
```

---

## 3. GitHub 구성

### 3.1 Repository 구조

```
hybrid-rag-knowledge-ops/                    # Main Repository
├── .github/
│   ├── workflows/                           # CI/CD Workflows
│   │   ├── ci.yml                          # Build & Test
│   │   ├── cd-staging.yml                  # Deploy to Staging
│   │   ├── cd-production.yml               # Deploy to Production
│   │   ├── release.yml                     # Release Automation
│   │   ├── security-scan.yml               # Security Scanning
│   │   └── codeql.yml                      # Code Analysis
│   │
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   ├── feature_request.md
│   │   ├── task.md
│   │   └── config.yml
│   │
│   ├── PULL_REQUEST_TEMPLATE.md
│   ├── CODEOWNERS
│   └── dependabot.yml
│
├── frontend/                                # React Frontend
├── backend/                                 # SpringBoot Services
├── ai-service/                              # Python AI Service
├── infrastructure/                          # Docker, K8s configs
├── docs/                                    # Documentation
└── scripts/                                 # Utility Scripts
```

### 3.2 Branch 전략 (GitFlow 변형)

```
main ──────────────────────────────────────────────────────► Production
  │                                                     ▲
  │ hotfix/*   ┌─────────────────────────────────────────┤
  │ ◄──────────┤                                         │
  │            └───► fix ───► PR ───► merge ──────────────
  │
  │ release/*  ┌─────────────────────────────────────────┐
  │ ◄──────────┤                                         │
  │            └───► RC testing ───► tag ───► merge ─────┘
  │
develop ──────────────────────────────────────────────────► Staging
  │                     ▲           ▲           ▲
  │                     │           │           │
  │ feature/HRKP-xxx ───┤           │           │
  │ ◄───────────────────┤           │           │
  │                     └── PR ─────┘           │
  │                                             │
  │ fix/HRKP-xxx ───────────────────────────────┤
  │ ◄───────────────────────────────────────────┘
  │
```

### 3.3 Branch 명명 규칙

| 타입 | 패턴 | 예시 | 설명 |
|------|------|------|------|
| **Feature** | `feature/HRKP-xxx-description` | `feature/HRKP-123-add-search-api` | 새 기능 |
| **Fix** | `fix/HRKP-xxx-description` | `fix/HRKP-456-fix-null-pointer` | 버그 수정 |
| **Hotfix** | `hotfix/HRKP-xxx-description` | `hotfix/HRKP-789-security-patch` | 긴급 수정 |
| **Release** | `release/v{x.y.z}` | `release/v1.2.0` | 릴리즈 준비 |
| **Chore** | `chore/description` | `chore/update-dependencies` | 유지보수 |

### 3.4 Commit Convention

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type:**

| 타입 | 설명 | 예시 |
|------|------|------|
| `feat` | 새 기능 | `feat(search): add hybrid search endpoint` |
| `fix` | 버그 수정 | `fix(auth): resolve token refresh issue` |
| `docs` | 문서 변경 | `docs(readme): update installation guide` |
| `style` | 코드 스타일 | `style: apply black formatter` |
| `refactor` | 리팩토링 | `refactor(api): optimize query logic` |
| `test` | 테스트 | `test(search): add integration tests` |
| `chore` | 빌드/도구 | `chore: update dependencies` |

**Footer:**
- `HRKP-xxx` - JIRA 이슈 연결
- `BREAKING CHANGE:` - 호환성 변경

### 3.5 CODEOWNERS

```
# CODEOWNERS file

# Default owners
* @team-leads

# Frontend
/frontend/ @frontend-team @antigravity-agent

# Backend
/backend/ @backend-team @claude-code-agent

# AI Service
/ai-service/ @ai-team @claude-code-agent

# Infrastructure
/infrastructure/ @devops-team

# Documentation
/docs/ @tech-writers @claude-code-agent
```

### 3.6 Issue Templates

**Bug Report (bug_report.md):**

```markdown
---
name: Bug Report
about: 버그를 신고합니다
title: '[BUG] '
labels: bug
assignees: ''
---

## 버그 설명
<!-- 버그에 대한 명확한 설명 -->

## 재현 단계
1. '...'로 이동
2. '...' 클릭
3. '...'까지 스크롤
4. 오류 확인

## 예상 동작
<!-- 정상적으로 예상되는 동작 -->

## 스크린샷
<!-- 해당하는 경우 스크린샷 추가 -->

## 환경
- OS: [예: Windows 11]
- Browser: [예: Chrome 120]
- Version: [예: v1.2.0]

## 추가 컨텍스트
<!-- 기타 참고 사항 -->
```

**Feature Request (feature_request.md):**

```markdown
---
name: Feature Request
about: 새로운 기능을 제안합니다
title: '[FEAT] '
labels: enhancement
assignees: ''
---

## 기능 설명
<!-- 제안하는 기능에 대한 명확한 설명 -->

## 해결하려는 문제
<!-- 이 기능이 해결하는 문제 -->

## 제안하는 해결책
<!-- 구현 방법에 대한 아이디어 -->

## 대안
<!-- 고려한 다른 대안들 -->

## 우선순위
- [ ] High
- [ ] Medium
- [ ] Low

## 관련 JIRA
<!-- HRKP-xxx -->
```

### 3.7 PR Template

```markdown
## 변경 사항
<!-- 이 PR에서 변경된 내용을 설명하세요 -->

## 관련 이슈
<!-- JIRA 티켓 또는 GitHub 이슈 -->
Closes HRKP-xxx

## 변경 유형
- [ ] Bug fix (breaking change 없는 버그 수정)
- [ ] New feature (breaking change 없는 새 기능)
- [ ] Breaking change (기존 기능에 영향)
- [ ] Documentation update

## 체크리스트
- [ ] 코드가 프로젝트 스타일 가이드를 따름
- [ ] 셀프 리뷰 완료
- [ ] 주석 추가 (특히 복잡한 부분)
- [ ] 문서 업데이트 (필요시)
- [ ] 테스트 추가/수정
- [ ] 모든 테스트 통과

## 테스트 방법
<!-- 이 변경을 어떻게 테스트할 수 있는지 설명 -->

## 스크린샷 (UI 변경시)
<!-- 해당하는 경우 전후 스크린샷 추가 -->

## AI 리뷰어 참고사항
<!-- Claude Code 또는 다른 AI 리뷰어를 위한 컨텍스트 -->
```

---

## 4. JIRA Cloud 구성

### 4.1 프로젝트 설정

```
Project Key: HRKP
Project Name: Hybrid RAG Knowledge Platform
Project Type: Kanban (Software)
```

### 4.2 이슈 유형

| 이슈 유형 | 아이콘 | 용도 | 워크플로우 |
|----------|--------|------|-----------|
| **Epic** | 🟣 | 대규모 기능 묶음 | Standard |
| **Story** | 🟢 | 사용자 기능 | Standard |
| **Task** | 🔵 | 개발 작업 | Standard |
| **Bug** | 🔴 | 버그 | Bug Flow |
| **Subtask** | ⚪ | 하위 작업 | Simplified |

### 4.3 워크플로우

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Standard Workflow                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────┐   ┌──────────┐   ┌───────────┐   ┌──────────┐   ┌──────────┐│
│  │ BACKLOG  │──►│  TO DO   │──►│IN PROGRESS│──►│  REVIEW  │──►│   DONE   ││
│  └──────────┘   └──────────┘   └───────────┘   └──────────┘   └──────────┘│
│       │              │              │               │              ▲       │
│       │              │              │               │              │       │
│       │              ▼              │               ▼              │       │
│       │         ┌──────────┐       │          ┌──────────┐        │       │
│       └────────►│ BLOCKED  │◄──────┘          │ TESTING  │────────┘       │
│                 └──────────┘                  └──────────┘                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

Status Descriptions:
- BACKLOG: 우선순위 대기
- TO DO: 스프린트/작업 예정
- IN PROGRESS: 개발 진행 중
- BLOCKED: 차단됨 (외부 의존성)
- REVIEW: 코드 리뷰 중
- TESTING: QA 테스트 중
- DONE: 완료
```

### 4.4 Epic 구조

```
HRKP-E1: Frontend Development
├── HRKP-1: Setup React project
├── HRKP-2: Implement authentication
├── HRKP-3: Create search interface
├── HRKP-4: Build dashboard
└── HRKP-5: Add export features

HRKP-E2: Backend Development
├── HRKP-10: Setup Spring Cloud
├── HRKP-11: Knowledge Service
├── HRKP-12: Search Service
├── HRKP-13: User Service
└── HRKP-14: Export Service

HRKP-E3: AI Service Development
├── HRKP-20: Setup FastAPI
├── HRKP-21: Hybrid Search
├── HRKP-22: Entity Extraction
├── HRKP-23: Answer Synthesis
└── HRKP-24: ReAct Agent

HRKP-E4: Infrastructure/DevOps
├── HRKP-30: Docker setup
├── HRKP-31: CI/CD pipeline
├── HRKP-32: Kubernetes config
├── HRKP-33: Monitoring setup
└── HRKP-34: Security hardening

HRKP-E5: ALM Setup
├── HRKP-40: GitHub configuration
├── HRKP-41: JIRA setup
├── HRKP-42: Slack integration
├── HRKP-43: MCP configuration
└── HRKP-44: Release automation
```

### 4.5 칸반 보드 설정

**열 구성:**

| 열 | WIP 제한 | 설명 |
|----|---------|------|
| Backlog | - | 우선순위 대기 |
| To Do | 10 | 작업 준비 완료 |
| In Progress | 5 | 개발 진행 중 |
| Code Review | 5 | PR 리뷰 대기 |
| Testing | 3 | QA 테스트 중 |
| Done | - | 완료 |

**스윔레인:**

| 스윔레인 | 용도 |
|----------|------|
| Frontend | 프론트엔드 작업 |
| Backend | 백엔드 작업 |
| AI Service | AI 서비스 작업 |
| DevOps | 인프라/배포 작업 |
| Expedite | 긴급 작업 |

### 4.6 커스텀 필드

| 필드명 | 타입 | 용도 |
|--------|------|------|
| `Story Points` | Number | 작업량 추정 |
| `AI Agent` | Select | 담당 AI 에이전트 |
| `Priority Score` | Number | 우선순위 점수 |
| `Target Release` | Version | 목표 릴리즈 |
| `GitHub PR` | URL | 연결된 PR |
| `Test Coverage` | Percent | 테스트 커버리지 |

### 4.7 자동화 규칙

**Rule 1: PR 생성 시 상태 변경**
```
WHEN: GitHub PR created with JIRA key
THEN: Move issue to "Code Review"
AND: Add comment with PR link
```

**Rule 2: PR 머지 시 상태 변경**
```
WHEN: GitHub PR merged with JIRA key
THEN: Move issue to "Testing"
AND: Add comment "PR merged, ready for testing"
```

**Rule 3: 리뷰어 자동 할당**
```
WHEN: Issue moved to "Code Review"
AND: Component = "AI Service"
THEN: Add reviewer @claude-code-agent
```

---

## 5. Slack 통합

### 5.1 Workspace 구조

```
Workspace: hybrid-rag-dev
│
├── 공개 채널
│   ├── #general                 # 일반 공지
│   ├── #announcements          # 중요 공지 (읽기 전용)
│   ├── #random                  # 자유 대화
│   │
│   ├── #dev-frontend           # 프론트엔드 개발
│   ├── #dev-backend            # 백엔드 개발
│   ├── #dev-ai-service         # AI 서비스 개발
│   ├── #dev-infrastructure     # 인프라/DevOps
│   │
│   ├── #code-review            # 코드 리뷰 알림
│   ├── #ci-cd-alerts           # CI/CD 상태 알림
│   ├── #deployment             # 배포 알림
│   ├── #monitoring-alerts      # 시스템 알림
│   │
│   └── #ai-agents              # AI 에이전트 전용
│
└── 비공개 채널
    ├── #team-leads             # 팀 리드 전용
    ├── #security               # 보안 이슈
    └── #production-incidents   # 프로덕션 장애
```

### 5.2 채널별 목적 및 규칙

| 채널 | 목적 | 알림 설정 | 주요 연동 |
|------|------|----------|----------|
| `#general` | 일반 공지, 팀 소통 | 모든 메시지 | - |
| `#dev-frontend` | 프론트엔드 논의 | 멘션만 | GitHub (frontend/) |
| `#dev-backend` | 백엔드 논의 | 멘션만 | GitHub (backend/) |
| `#dev-ai-service` | AI 서비스 논의 | 멘션만 | GitHub (ai-service/) |
| `#code-review` | PR 리뷰 알림 | 모든 메시지 | GitHub PR |
| `#ci-cd-alerts` | 빌드/테스트 결과 | 모든 메시지 | GitHub Actions |
| `#deployment` | 배포 알림 | 모든 메시지 | GitHub Releases |
| `#monitoring-alerts` | 시스템 경고 | 모든 메시지 | Prometheus/Grafana |
| `#ai-agents` | AI 협업 허브 | 모든 메시지 | 모든 AI 봇 |

### 5.3 Bot 구성

#### 5.3.1 GitHub Bot

```
앱 이름: GitHub for Slack
연동 기능:
  - Repository 알림
  - PR 생성/머지/클로즈
  - Issue 생성/업데이트
  - Actions 상태
  - Release 게시

알림 라우팅:
  /frontend → #dev-frontend
  /backend → #dev-backend
  /ai-service → #dev-ai-service
  PR events → #code-review
  Actions → #ci-cd-alerts
  Release → #deployment
```

#### 5.3.2 JIRA Bot

```
앱 이름: Jira Cloud for Slack
연동 기능:
  - 이슈 생성/업데이트 알림
  - 이슈 검색 (/jira search)
  - 이슈 생성 (/jira create)
  - 이슈 상태 변경

Commands:
  /jira create [summary] - 새 이슈 생성
  /jira [HRKP-xxx] - 이슈 상세 조회
  /jira search [query] - 이슈 검색
  /jira assign [HRKP-xxx] [@user] - 담당자 지정
```

#### 5.3.3 Custom AI Agent Bots

**Claude-Code-Agent:**

```yaml
Name: Claude-Code-Agent
Trigger: @claude or /claude
Channels: #ai-agents, #code-review
Capabilities:
  - Code generation
  - Code review
  - Documentation
  - Architecture suggestions

Commands:
  /claude code <description>      # 코드 생성
  /claude review <PR#>            # PR 리뷰
  /claude explain <file>          # 코드 설명
  /claude suggest <topic>         # 아키텍처 제안
  /claude doc <component>         # 문서 생성
```

**Antigravity-Agent:**

```yaml
Name: Antigravity-Agent
Trigger: @antigravity or /antigravity
Channels: #ai-agents, #dev-frontend
Capabilities:
  - UI component generation
  - Styling assistance
  - UI testing
  - Accessibility check

Commands:
  /antigravity component <name>   # 컴포넌트 생성
  /antigravity style <component>  # 스타일링
  /antigravity test <component>   # UI 테스트
  /antigravity a11y <page>        # 접근성 검사
```

**DeepSeek-Agent:**

```yaml
Name: DeepSeek-Agent
Trigger: @deepseek or /deepseek
Channels: #ai-agents, #dev-ai-service
Capabilities:
  - Code analysis
  - Bulk operations
  - Cost-efficient tasks
  - Data processing

Commands:
  /deepseek analyze <code>        # 코드 분석
  /deepseek extract <document>    # 메타데이터 추출
  /deepseek bulk <operation>      # 대량 작업
  /deepseek report                # 비용/사용량 보고
```

### 5.4 알림 설정

**CI/CD 알림 (GitHub Actions → Slack):**

```yaml
# .github/workflows/ci.yml
- name: Slack Notification
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    channel: '#ci-cd-alerts'
    fields: repo,message,commit,author,action,eventName,ref,workflow
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
  if: always()
```

**배포 알림:**

```yaml
# .github/workflows/cd-production.yml
- name: Deployment Notification
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    channel: '#deployment'
    text: |
      🚀 *Production Deployment*
      Version: ${{ github.ref_name }}
      Status: ${{ job.status }}
      Deployer: ${{ github.actor }}
```

---

## 6. AI 에이전트 협업

### 6.1 역할 분담

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AI Agent Collaboration Model                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────────┐  │
│   │                      👤 Human (Orchestrator)                         │  │
│   │                요구사항 정의 / 최종 검토 / 의사결정                    │  │
│   └─────────────────────────────┬────────────────────────────────────────┘  │
│                                 │                                           │
│                    ┌────────────┴────────────┐                              │
│                    ▼                         ▼                              │
│          ┌────────────────┐         ┌────────────────┐                     │
│          │  Claude Code   │         │  Antigravity   │                     │
│          │  (Opus 4.5)    │         │  (UI Agent)    │                     │
│          ├────────────────┤         ├────────────────┤                     │
│          │ 핵심 담당:     │         │ 핵심 담당:     │                     │
│          │ • Backend      │         │ • UI 코딩      │                     │
│          │ • AI Service   │         │ • React 컴포넌트│                     │
│          │ • 설계/기획    │         │ • 스타일링     │                     │
│          │ • 코드 리뷰    │         │ • UI 테스트    │                     │
│          │ • MCP 연동     │         │ • 제3자 테스트 │                     │
│          │ • 통합 테스트  │         │ • 접근성 검증  │                     │
│          └────────────────┘         └────────────────┘                     │
│                                                                              │
│   ※ 런타임 LLM (DeepSeek V3.2)은 AI Service가 호출하는 API로,              │
│     개발 에이전트가 아닌 시스템 구성요소입니다.                              │
│     → backend_implementation_plan.md의 "AI Service 설계" 참조               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 협업 워크플로우

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Feature Development Workflow                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. JIRA Issue 생성 (Human)                                                 │
│     │                                                                        │
│     ▼                                                                        │
│  2. 설계 검토 (Claude Code)                                                 │
│     ├── 요구사항 분석                                                       │
│     ├── 아키텍처 검토                                                       │
│     └── 구현 계획 수립                                                      │
│     │                                                                        │
│     ▼                                                                        │
│  3. 역할 분배 (#ai-agents 공유)                                             │
│     ├── Claude Code → Backend / AI Service                                  │
│     └── Antigravity → Frontend UI                                           │
│     │                                                                        │
│     ▼                                                                        │
│  4. 병렬 구현                                                                │
│     │           │                                                            │
│     ▼           ▼                                                            │
│   [API]       [UI]                                                           │
│     │           │                                                            │
│     └─────┬─────┘                                                            │
│           ▼                                                                  │
│  5. 통합 (Claude Code)                                                       │
│     ├── 코드 리뷰                                                            │
│     ├── 통합 테스트                                                          │
│     └── PR 생성                                                              │
│     │                                                                        │
│     ▼                                                                        │
│  6. 제3자 테스트 (Antigravity)                                              │
│     ├── UI 테스트                                                            │
│     ├── 접근성 테스트                                                        │
│     └── 사용성 검증                                                          │
│     │                                                                        │
│     ▼                                                                        │
│  7. 최종 검토 (Human)                                                        │
│     ├── 코드 리뷰 승인                                                       │
│     └── PR 머지                                                              │
│     │                                                                        │
│     ▼                                                                        │
│  8. 배포 (GitHub Actions)                                                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.3 Slack 협업 채널 사용 예시

```
#ai-agents

@claude-code-agent
HRKP-123 구현을 시작합니다.
- Backend: Search API 구현
- AI Service: Hybrid Search 로직

---

@antigravity-agent
HRKP-123 Frontend 작업을 시작합니다.
- 검색 결과 컴포넌트
- 필터 패널
- 페이지네이션

---

@claude-code-agent
Backend API 구현 완료. PR #45 생성했습니다.
@antigravity-agent API 연동 준비되었습니다.

---

@antigravity-agent
Frontend 컴포넌트 완료. PR #46 생성.
@claude-code-agent 리뷰 부탁드립니다.

---

@claude-code-agent
PR #45, #46 리뷰 완료. 승인.
제3자 테스트 진행해주세요 @antigravity-agent

---

@antigravity-agent
제3자 테스트 완료.
- UI 테스트: ✅ PASS
- 접근성: ✅ PASS
- 사용성: ✅ PASS

@human 최종 검토 부탁드립니다.

---

@human
PR 승인. 머지 진행합니다. 🎉
```

---

## 7. CI/CD 파이프라인

### 7.1 파이프라인 개요

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CI/CD Pipeline Overview                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  [Push/PR] ──► [Build] ──► [Test] ──► [Lint] ──► [Security] ──► [Deploy]   │
│      │           │          │          │           │              │         │
│      │           ▼          ▼          ▼           ▼              ▼         │
│      │        Docker     Unit +     ESLint     Snyk/SAST     Staging/     │
│      │        Build      Integration  Black                   Production   │
│      │                   E2E          Prettier                             │
│      │                                                                      │
│      └────────────────── Slack Notifications ──────────────────────────────│
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 CI Workflow (ci.yml)

```yaml
name: CI Pipeline

on:
  push:
    branches: [develop, main]
  pull_request:
    branches: [develop, main]

env:
  JAVA_VERSION: '21'
  PYTHON_VERSION: '3.11'
  NODE_VERSION: '20'

jobs:
  # ========================================
  # Frontend CI
  # ========================================
  frontend-ci:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ./frontend

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: npm ci

      - name: Lint
        run: npm run lint

      - name: Type check
        run: npm run type-check

      - name: Unit tests
        run: npm run test -- --coverage

      - name: Build
        run: npm run build

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./frontend/coverage/lcov.info
          flags: frontend

  # ========================================
  # Backend CI
  # ========================================
  backend-ci:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: test
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Setup JDK
        uses: actions/setup-java@v4
        with:
          java-version: ${{ env.JAVA_VERSION }}
          distribution: 'temurin'
          cache: 'gradle'

      - name: Grant execute permission
        run: chmod +x ./backend/gradlew

      - name: Build with Gradle
        working-directory: ./backend
        run: ./gradlew build -x test

      - name: Run tests
        working-directory: ./backend
        run: ./gradlew test

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./backend/build/reports/jacoco/test/jacocoTestReport.xml
          flags: backend

  # ========================================
  # AI Service CI
  # ========================================
  ai-service-ci:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ./ai-service

    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Lint with ruff
        run: ruff check .

      - name: Format check with black
        run: black --check .

      - name: Type check with mypy
        run: mypy app --ignore-missing-imports

      - name: Run tests
        run: pytest --cov=app --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./ai-service/coverage.xml
          flags: ai-service

  # ========================================
  # Security Scan
  # ========================================
  security-scan:
    runs-on: ubuntu-latest
    needs: [frontend-ci, backend-ci, ai-service-ci]

    steps:
      - uses: actions/checkout@v4

      - name: Run Snyk to check for vulnerabilities
        uses: snyk/actions/node@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          args: --all-projects

      - name: Run CodeQL Analysis
        uses: github/codeql-action/analyze@v3

  # ========================================
  # Build Docker Images
  # ========================================
  docker-build:
    runs-on: ubuntu-latest
    needs: [security-scan]
    if: github.ref == 'refs/heads/develop' || github.ref == 'refs/heads/main'

    strategy:
      matrix:
        service: [frontend, backend, ai-service]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ secrets.REGISTRY_URL }}
          username: ${{ secrets.REGISTRY_USER }}
          password: ${{ secrets.REGISTRY_PASSWORD }}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: ./${{ matrix.service }}
          push: true
          tags: |
            ${{ secrets.REGISTRY_URL }}/${{ matrix.service }}:${{ github.sha }}
            ${{ secrets.REGISTRY_URL }}/${{ matrix.service }}:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max

  # ========================================
  # Slack Notification
  # ========================================
  notify:
    runs-on: ubuntu-latest
    needs: [docker-build]
    if: always()

    steps:
      - name: Notify Slack
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ needs.docker-build.result }}
          channel: '#ci-cd-alerts'
          fields: repo,message,commit,author,action,ref,workflow
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

### 7.3 CD Staging Workflow (cd-staging.yml)

```yaml
name: Deploy to Staging

on:
  push:
    branches: [develop]

jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    environment: staging

    steps:
      - uses: actions/checkout@v4

      - name: Deploy to Staging
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.STAGING_HOST }}
          username: ${{ secrets.STAGING_USER }}
          key: ${{ secrets.SSH_KEY }}
          script: |
            cd /app/hybrid-rag
            docker-compose -f docker-compose.staging.yml pull
            docker-compose -f docker-compose.staging.yml up -d
            docker system prune -f

      - name: Health Check
        run: |
          sleep 30
          curl -f ${{ secrets.STAGING_URL }}/api/health || exit 1

      - name: Notify Slack
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          channel: '#deployment'
          text: |
            🚀 *Staging Deployment*
            Branch: develop
            Status: ${{ job.status }}
            URL: ${{ secrets.STAGING_URL }}
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

### 7.4 CD Production Workflow (cd-production.yml)

```yaml
name: Deploy to Production

on:
  release:
    types: [published]

jobs:
  deploy-production:
    runs-on: ubuntu-latest
    environment: production

    steps:
      - uses: actions/checkout@v4

      - name: Extract version
        id: version
        run: echo "VERSION=${GITHUB_REF#refs/tags/v}" >> $GITHUB_OUTPUT

      - name: Deploy to Production
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.PROD_HOST }}
          username: ${{ secrets.PROD_USER }}
          key: ${{ secrets.SSH_KEY }}
          script: |
            cd /app/hybrid-rag
            export VERSION=${{ steps.version.outputs.VERSION }}
            docker-compose -f docker-compose.production.yml pull
            docker-compose -f docker-compose.production.yml up -d
            docker system prune -f

      - name: Health Check
        run: |
          sleep 60
          curl -f ${{ secrets.PROD_URL }}/api/health || exit 1

      - name: Notify Slack
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          channel: '#deployment'
          text: |
            🚀 *Production Deployment*
            Version: v${{ steps.version.outputs.VERSION }}
            Status: ${{ job.status }}
            Release: ${{ github.event.release.html_url }}
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}

      - name: Update JIRA Release
        run: |
          curl -X PUT \
            -H "Authorization: Basic ${{ secrets.JIRA_TOKEN }}" \
            -H "Content-Type: application/json" \
            -d '{"released": true, "releaseDate": "'$(date +%Y-%m-%d)'"}' \
            "${{ secrets.JIRA_URL }}/rest/api/3/version/${{ secrets.JIRA_VERSION_ID }}"
```

---

## 8. 릴리즈 관리

### 8.1 버전 전략 (Semantic Versioning)

```
MAJOR.MINOR.PATCH

예시: v1.2.3

MAJOR: 호환성이 깨지는 변경
MINOR: 하위 호환 기능 추가
PATCH: 하위 호환 버그 수정
```

### 8.2 릴리즈 흐름

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Release Management Flow                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Feature Complete                                                            │
│       │                                                                      │
│       ▼                                                                      │
│  ┌─────────────┐                                                            │
│  │ Create      │ develop → release/v{x.y.z}                                 │
│  │ Release     │                                                            │
│  │ Branch      │                                                            │
│  └──────┬──────┘                                                            │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────┐                                                            │
│  │ RC Testing  │ QA 테스트, 버그 수정                                       │
│  │             │ Staging 환경 검증                                          │
│  └──────┬──────┘                                                            │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────┐                                                            │
│  │ QA Sign-off │ 테스트 완료 승인                                           │
│  │             │ Release Notes 작성                                         │
│  └──────┬──────┘                                                            │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────┐                                                            │
│  │ Merge to    │ release → main                                             │
│  │ Main        │ 태그 생성: v{x.y.z}                                        │
│  └──────┬──────┘                                                            │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────┐                                                            │
│  │ GitHub      │ 자동 생성                                                   │
│  │ Release     │ Release Notes                                              │
│  └──────┬──────┘                                                            │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────┐                                                            │
│  │ Production  │ 자동 배포 트리거                                           │
│  │ Deploy      │                                                            │
│  └──────┬──────┘                                                            │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────┐                                                            │
│  │ JIRA        │ 릴리즈 완료 마킹                                           │
│  │ Release     │ 연결된 이슈 자동 종료                                      │
│  │ Update      │                                                            │
│  └─────────────┘                                                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.3 릴리즈 계획

| 버전 | 목표 | 주요 기능 | 상태 |
|------|------|----------|------|
| v0.1.0 | MVP | 기본 검색, 지식 CRUD | 계획 중 |
| v0.2.0 | Graph RAG | Hybrid Search, Graph 탐색 | 계획 중 |
| v0.3.0 | 시간 인식 | Temporal Reasoning | 계획 중 |
| v0.4.0 | 개인화 | 추천, 북마크, 히스토리 | 계획 중 |
| v0.5.0 | 문서 변환 | Excel, PPT, PDF | 계획 중 |
| v1.0.0 | 정식 출시 | 전체 기능, 최적화 | 계획 중 |

### 8.4 Release Notes 템플릿

```markdown
# Release v{x.y.z}

## Highlights
<!-- 주요 변경 사항 요약 -->

## What's New
### Features
- 새로운 기능 1 (#123)
- 새로운 기능 2 (#124)

### Improvements
- 개선 사항 1 (#125)
- 개선 사항 2 (#126)

### Bug Fixes
- 버그 수정 1 (#127)
- 버그 수정 2 (#128)

## Breaking Changes
<!-- 호환성이 깨지는 변경 사항 -->

## Upgrade Notes
<!-- 업그레이드 시 주의 사항 -->

## Contributors
@user1, @user2, @claude-code-agent

## Full Changelog
https://github.com/org/repo/compare/v{prev}...v{x.y.z}
```

---

## 9. MCP 통합

### 9.1 MCP 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Claude Code MCP Integration                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                          Claude Code                                 │   │
│   │                    (with Skills & Hooks)                            │   │
│   └──────────────────────────────┬──────────────────────────────────────┘   │
│                                  │                                          │
│          ┌───────────────────────┼───────────────────────┐                 │
│          │                       │                       │                 │
│          ▼                       ▼                       ▼                 │
│   ┌─────────────┐        ┌─────────────┐        ┌─────────────┐           │
│   │   GitHub    │        │ PostgreSQL  │        │Elasticsearch│           │
│   │ MCP Server  │        │ MCP Server  │        │ MCP Server  │           │
│   │   (HTTP)    │        │   (stdio)   │        │   (stdio)   │           │
│   └─────────────┘        └─────────────┘        └─────────────┘           │
│          │                       │                       │                 │
│          │                       ▼                       │                 │
│          │              ┌─────────────┐                  │                 │
│          │              │    Neo4j    │                  │                 │
│          │              │ MCP Server  │                  │                 │
│          │              │   (stdio)   │                  │                 │
│          │              └─────────────┘                  │                 │
│          │                       │                       │                 │
│          └───────────────────────┼───────────────────────┘                 │
│                                  │                                          │
│                         ┌────────▼────────┐                                │
│                         │  JIRA + Slack   │                                │
│                         │  MCP Servers    │                                │
│                         │    (HTTP)       │                                │
│                         └─────────────────┘                                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 9.2 MCP 서버 설정

**.mcp.json:**

```json
{
  "mcpServers": {
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/",
      "headers": {
        "Authorization": "Bearer ${GITHUB_TOKEN}"
      }
    },
    "postgres": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@bytebase/dbhub", "postgresql"],
      "env": {
        "DSN": "${POSTGRES_URL}"
      }
    },
    "elasticsearch": {
      "type": "stdio",
      "command": "python",
      "args": [".claude/mcp/elasticsearch_server.py"],
      "env": {
        "ES_URL": "${ELASTICSEARCH_URL}",
        "ES_INDEX": "knowledge-chunks"
      }
    },
    "neo4j": {
      "type": "stdio",
      "command": "python",
      "args": [".claude/mcp/neo4j_server.py"],
      "env": {
        "NEO4J_URI": "${NEO4J_URI}",
        "NEO4J_USER": "${NEO4J_USER}",
        "NEO4J_PASSWORD": "${NEO4J_PASSWORD}"
      }
    },
    "jira": {
      "type": "http",
      "url": "https://your-domain.atlassian.net/mcp/",
      "headers": {
        "Authorization": "Basic ${JIRA_TOKEN}"
      }
    },
    "slack": {
      "type": "http",
      "url": "https://slack.com/api/mcp/",
      "headers": {
        "Authorization": "Bearer ${SLACK_BOT_TOKEN}"
      }
    }
  }
}
```

### 9.3 Skills 구성

**.claude/skills/ 디렉토리:**

```
.claude/skills/
├── pr-review/
│   └── SKILL.md                # PR 코드 리뷰
├── knowledge-extraction/
│   └── SKILL.md                # 지식 요소 추출
├── elasticsearch-search/
│   └── SKILL.md                # ES 벡터/키워드 검색
├── jira-management/
│   └── SKILL.md                # JIRA 이슈 관리
├── graph-query/
│   └── SKILL.md                # Neo4j 그래프 쿼리
└── metadata-extraction/
    └── SKILL.md                # 문서 메타데이터 추출
```

**pr-review/SKILL.md:**

```markdown
# PR Review Skill

## Description
GitHub Pull Request를 자동으로 리뷰하고 피드백을 제공합니다.

## When to Use
- PR 리뷰 요청 시
- 코드 품질 검증 시
- 보안 취약점 검사 시

## Steps
1. GitHub MCP를 통해 PR diff 조회
2. 변경된 파일 분석
3. 코드 스타일, 보안, 성능 검토
4. 리뷰 코멘트 작성
5. 승인/변경 요청 결정

## Output Format
- Inline comments on specific lines
- Summary comment with overall assessment
- Approve/Request changes decision
```

**jira-management/SKILL.md:**

```markdown
# JIRA Management Skill

## Description
JIRA 이슈를 생성, 조회, 업데이트합니다.

## When to Use
- 새 기능 개발 시작 시
- 버그 보고 시
- 이슈 상태 업데이트 시

## Commands
- Create: `jira:create --summary "이슈 제목" --type Task --epic HRKP-E1`
- Search: `jira:search --jql "project=HRKP AND status='In Progress'"`
- Update: `jira:update --issue HRKP-123 --status "Code Review"`

## Integration
- GitHub PR과 자동 연결
- Slack 알림 발송
```

### 9.4 Hooks 구성

**.claude/settings.json (hooks):**

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "./.claude/hooks/auto_format.py"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "./.claude/hooks/validate_command.py"
          }
        ]
      }
    ],
    "Notification": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "./.claude/hooks/slack_notify.py"
          }
        ]
      }
    ]
  }
}
```

**.claude/hooks/auto_format.py:**

```python
#!/usr/bin/env python3
"""파일 수정 후 자동 포맷팅"""
import subprocess
import sys
import os

def main():
    file_path = os.environ.get("CLAUDE_FILE_PATH", "")

    if file_path.endswith(".py"):
        subprocess.run(["black", file_path], check=True)
        subprocess.run(["ruff", "check", "--fix", file_path], check=True)

    elif file_path.endswith((".ts", ".tsx", ".js", ".jsx")):
        subprocess.run(["prettier", "--write", file_path], check=True)
        subprocess.run(["eslint", "--fix", file_path], check=True)

    elif file_path.endswith(".md"):
        subprocess.run(["prettier", "--write", file_path], check=True)

if __name__ == "__main__":
    main()
```

### 9.5 자동화 워크플로우

```
1. JIRA 이슈 기반 개발
   Human: "HRKP-123 구현해줘"
   Claude: [JIRA MCP] 이슈 조회
           → [설계 분석]
           → [코드 작성]
           → [GitHub MCP] PR 생성
           → [JIRA MCP] 상태 업데이트

2. PR 자동 리뷰
   Trigger: PR 생성 이벤트
   Claude: [GitHub MCP] PR diff 조회
           → [pr-review Skill] 코드 분석
           → [GitHub MCP] 리뷰 코멘트 작성
           → [Slack MCP] 결과 알림

3. 지식 추출 및 저장
   Human: "이 문서 분석해서 저장해"
   Claude: [knowledge-extraction Skill] 문서 분석
           → [PostgreSQL MCP] 메타데이터 저장
           → [Elasticsearch MCP] 벡터 인덱싱
           → [Neo4j MCP] 그래프 생성
```

---

## 10. 모니터링 및 운영

### 10.1 모니터링 스택

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Monitoring Stack                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                 │
│   │  Prometheus  │───►│   Grafana    │───►│    Slack     │                 │
│   │  (Metrics)   │    │ (Dashboard)  │    │  (Alerts)    │                 │
│   └──────────────┘    └──────────────┘    └──────────────┘                 │
│          ▲                                                                   │
│          │                                                                   │
│   ┌──────┴───────────────────────────────────────────┐                     │
│   │                   Applications                    │                     │
│   │  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  │                     │
│   │  │Frontend│  │Backend │  │   AI   │  │  DBs   │  │                     │
│   │  │        │  │        │  │Service │  │        │  │                     │
│   │  └────────┘  └────────┘  └────────┘  └────────┘  │                     │
│   └──────────────────────────────────────────────────┘                     │
│                                                                              │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                 │
│   │   Loki       │◄───│  Promtail    │───►│  Grafana     │                 │
│   │   (Logs)     │    │ (Log Agent)  │    │  (Explore)   │                 │
│   └──────────────┘    └──────────────┘    └──────────────┘                 │
│                                                                              │
│   ┌──────────────┐    ┌──────────────┐                                      │
│   │   Jaeger     │◄───│   OpenTel    │                                      │
│   │  (Tracing)   │    │   (Traces)   │                                      │
│   └──────────────┘    └──────────────┘                                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 10.2 주요 메트릭

| 카테고리 | 메트릭 | 임계값 | 알림 |
|----------|--------|--------|------|
| **가용성** | Uptime | < 99.9% | Critical |
| **응답시간** | P95 Latency | > 1s | Warning |
| **응답시간** | P99 Latency | > 3s | Critical |
| **에러율** | 5xx Rate | > 1% | Critical |
| **리소스** | CPU Usage | > 80% | Warning |
| **리소스** | Memory Usage | > 85% | Warning |
| **DB** | Connection Pool | > 80% | Warning |
| **AI** | LLM Latency | > 5s | Warning |
| **검색** | Search Latency | > 2s | Warning |

### 10.3 Grafana 대시보드

**대시보드 구성:**

| 대시보드 | 내용 |
|----------|------|
| **Overview** | 전체 시스템 상태, 핵심 KPI |
| **Frontend** | React 앱 성능, 에러율 |
| **Backend** | Spring 서비스 메트릭 |
| **AI Service** | LLM 호출, 검색 성능 |
| **Databases** | PostgreSQL, ES, Neo4j 상태 |
| **CI/CD** | 파이프라인 성공률, 배포 빈도 |

### 10.4 알림 규칙

**Prometheus Alertmanager:**

```yaml
groups:
  - name: application
    rules:
      - alert: HighErrorRate
        expr: sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) > 0.01
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }}"

      - alert: SlowResponseTime
        expr: histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le)) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Slow response time"
          description: "P95 latency is {{ $value | humanizeDuration }}"

      - alert: HighMemoryUsage
        expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes > 0.85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "Memory usage is {{ $value | humanizePercentage }}"
```

### 10.5 운영 절차

**장애 대응 프로세스:**

```
1. 알림 수신 (Slack #monitoring-alerts)
   │
   ▼
2. 심각도 판단
   ├── Critical → 즉시 대응, 에스컬레이션
   └── Warning → 모니터링, 계획된 대응
   │
   ▼
3. 원인 분석
   ├── 로그 확인 (Grafana Loki)
   ├── 메트릭 분석 (Grafana Dashboard)
   └── 트레이스 확인 (Jaeger)
   │
   ▼
4. 해결 조치
   ├── 롤백 (필요시)
   ├── 스케일 조정
   └── 핫픽스 배포
   │
   ▼
5. 포스트모템
   ├── 근본 원인 분석
   ├── 재발 방지 대책
   └── 문서화
```

---

## 부록

### A. 환경 변수 목록

```bash
# GitHub
GITHUB_TOKEN=ghp_xxx
GITHUB_WEBHOOK_SECRET=xxx

# JIRA
JIRA_URL=https://your-domain.atlassian.net
JIRA_TOKEN=xxx (base64 encoded email:api_token)
JIRA_PROJECT_KEY=HRKP

# Slack
SLACK_BOT_TOKEN=xoxb-xxx
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx

# Database
POSTGRES_URL=postgresql://user:pass@host:5432/db
ELASTICSEARCH_URL=http://localhost:9200
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=xxx

# Registry
REGISTRY_URL=registry.example.com
REGISTRY_USER=xxx
REGISTRY_PASSWORD=xxx

# Monitoring
PROMETHEUS_URL=http://localhost:9090
GRAFANA_URL=http://localhost:3000
SENTRY_DSN=https://xxx@sentry.io/xxx
```

### B. 참고 자료

- [PLAN.md](../../../PLAN.md) - 프로젝트 전체 계획
- [상세 설계서](../02_design/01_hybrid_rag_platform_detailed_design.md)
- [백엔드 구현 계획서](./backend_implementation_plan.md)
- [프론트엔드 구현 계획서](./frontend_implementation_plan.md)
- [GitHub Actions 문서](https://docs.github.com/en/actions)
- [JIRA Cloud API](https://developer.atlassian.com/cloud/jira/platform/rest/v3/)
- [Slack API](https://api.slack.com/)
- [Claude Code MCP](https://docs.anthropic.com/claude/docs/claude-code)

---

**문서 작성 완료: 2026-01-14**
