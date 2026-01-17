# Hybrid RAG Knowledge Platform - Project Plan

> Claude Code 세션 간 컨텍스트 유지를 위한 계획 문서
>
> **Last Updated**: 2026-01-17
> **Current Phase**: Phase 2 - 설계 완료 (100%) ✅

---

## Current Status

```
[Phase 1: 기획]     ████████████████████ 100% ✅ 완료
[Phase 2: 설계]     ████████████████████ 100% ✅ 완료 (종합 9.1/10, 탁월 5개 문서)
[Phase 3: 구현]     ░░░░░░░░░░░░░░░░░░░░   0% 🔜 준비 완료 (인력 소싱 후 착수)
[Phase 4: 테스트]   ░░░░░░░░░░░░░░░░░░░░   0%
[Phase 5: 배포]     ░░░░░░░░░░░░░░░░░░░░   0%
```

---

## 전체 프로젝트 범위

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Hybrid RAG Knowledge Platform                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │   Frontend   │  │   Backend    │  │  AI Service  │  │Infrastructure│ │
│  │   (React)    │  │ (SpringBoot) │  │   (Python)   │  │  (DevOps)   │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └─────────────┘ │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                         ALM & Collaboration                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │    GitHub    │  │  JIRA Cloud  │  │    Slack     │  │   Release   │ │
│  │   (Source)   │  │  (Backlog)   │  │  (AI Agent)  │  │ Management  │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └─────────────┘ │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## AI 에이전트 협업 구조

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      AI Agent Collaboration                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    👤 Human (Orchestrator)                         │ │
│  │         요구사항 정의 / 최종 검토 / 의사결정                          │ │
│  └──────────────────────────────┬─────────────────────────────────────┘ │
│                                 │                                        │
│                  ┌──────────────┴──────────────┐                        │
│                  ▼                             ▼                        │
│       ┌─────────────────────┐       ┌─────────────────────┐            │
│       │    Claude Code      │       │    Antigravity      │            │
│       │    (Opus 4.5)       │       │    (UI Agent)       │            │
│       ├─────────────────────┤       ├─────────────────────┤            │
│       │ [아키텍트 역할]     │       │ [UI 전문 역할]      │            │
│       │ • 아키텍처 설계     │       │ • UI 코딩           │            │
│       │ • 개발표준 산출물   │       │ • React 컴포넌트    │            │
│       │ • 디자인 가이드     │       │ • 스타일링          │            │
│       │                     │       │ • 접근성 검증       │            │
│       │ [개발자 역할]       │       │                     │            │
│       │ • Backend 구현      │       │ [테스터 역할]       │            │
│       │ • AI Service 구현   │       │ • UI 테스트         │            │
│       │ • 코드 리뷰         │       │ • 제3자 테스트      │            │
│       │ • 통합 테스트       │       │ • 사용성 검증       │            │
│       │ • MCP 연동          │       │                     │            │
│       └──────────┬──────────┘       └──────────┬──────────┘            │
│                  │                             │                        │
│                  └──────────────┬──────────────┘                        │
│                                 │                                        │
│                    ┌────────────▼────────────┐                          │
│                    │      Slack 채널         │                          │
│                    │   (#ai-agents 협업)     │                          │
│                    └─────────────────────────┘                          │
│                                                                          │
│  ※ 런타임 LLM (DeepSeek V3.2)은 AI Service가 호출하는 API로,           │
│    개발 에이전트가 아닌 시스템 구성요소입니다.                            │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### AI 에이전트 역할 분담

| 에이전트 | 역할 | 담당 영역 | 비고 |
|----------|------|----------|------|
| **Claude Code (Opus 4.5)** | 아키텍트 + 개발 | 아키텍처 설계, 개발표준 산출물, 디자인 가이드, Backend, AI Service, 코드 리뷰 | MCP/Skills 연동 |
| **Antigravity** | UI 전문 + 테스터 | React 컴포넌트, 스타일링, UI 테스트, 제3자 테스트, 접근성 검증 | UI 품질 담당 |
| **Human** | 오케스트레이터 | 요구사항 정의, 최종 검토, 의사결정 | 품질 게이트 |

> **참고**: DeepSeek V3.2는 개발 에이전트가 아닌 **런타임 LLM**입니다. AI Service가 엔티티 추출, 답변 합성 등에 API로 호출합니다.

### 협업 워크플로우

```
[기능 개발 사이클]

1. Human: JIRA에 이슈 생성 (HRKP-xxx)
           ↓
2. Claude Code: 아키텍처 검토 + 설계 + 구현 계획 수립
           ↓
3. Claude Code: 개발표준 산출물 / 디자인 가이드 작성 (필요시)
           ↓
4. 역할 분배:
   ├─ Claude Code → Backend / AI Service 구현
   └─ Antigravity → Frontend UI 구현
           ↓
5. Slack #ai-agents에서 진행상황 공유
           ↓
6. Claude Code: 코드 리뷰 + 통합
           ↓
7. Antigravity: 제3자 테스트 수행
           ↓
8. Human: 최종 검토 + PR 승인
           ↓
9. GitHub Actions: 자동 배포
```

### Slack 채널 구성 (AI Agent 협업)

```
#ai-agents
├── Claude-Code-Agent
│   ├── 아키텍처/설계 문서 공유
│   ├── 개발표준 산출물 공유
│   ├── 디자인 가이드 공유
│   ├── 코드 리뷰 결과 공유
│   └── Backend/AI Service 구현 진행상황
│
├── Antigravity-Agent
│   ├── UI 컴포넌트 완료 알림
│   ├── 테스트 결과 보고
│   ├── 접근성 검증 결과
│   └── 디자인 이슈 공유
│
└── Bot Commands:
    ├── /task assign @agent <task>
    ├── /status <task-id>
    └── /review request @claude-code
```

---

## Phase 1: Planning (기획) - 100% ✅ 완료

### 완료된 작업
- [x] 구축 계획서 작성 (`docs/01_planning/hybrid_rag_knowledge_platform_plan.md`)
- [x] 요구사항 정의 (`docs/01_planning/requirements_specification.md`)
- [x] 기술 스택 선정
- [x] 프론트엔드 구현 계획서 (`docs/01_planning/frontend_implementation_plan.md`)
- [x] **백엔드 구현 계획서** (`docs/01_planning/backend_implementation_plan.md`) ✅
- [x] **AI Service 구현 계획서 v2.0** (`docs/01_planning/ai_service_implementation_plan.md`) ✅
- [x] **개발환경 구축 계획** (`docs/01_planning/dev_environment_plan.md`) ✅
- [x] **테스트 전략 및 계획** (`docs/01_planning/test_plan.md`) ✅
- [x] **DevOps + ALM 통합 계획** (`docs/01_planning/devops_alm_plan.md`) ✅
- [x] **기획 문서 리뷰 완료** (`docs/01_planning/review/2026-01-14_planning_review_report.md`) ✅
- [x] **AI 에이전트 역할 명확화** (개발 에이전트 vs 런타임 LLM) ✅
- [x] **문서 일관성 확보** (PLAN.md, CLAUDE.md, devops_alm_plan.md) ✅

## Phase 2: Design (설계) - 100% ✅ 완료

### 완료된 작업
- [x] **상세 설계서 v2.4** (`docs/02_design/hybrid_rag_platform_detailed_design.md`) ✅ Gleaning 통합
- [x] **서비스 분리 아키텍처** (SpringBoot ↔ AI Service) ✅
- [x] **설계서 리뷰 완료** (`docs/02_design/review/`) ✅
- [x] VIP 3단계 LLM 아키텍처
- [x] 제로 조인 아키텍처
- [x] Hybrid 검색 엔진 설계
- [x] 데이터 모델 설계 (PostgreSQL, Neo4j, Elasticsearch)
- [x] 비용 분석
- [x] **Frontend 상세 설계서** (`docs/02_design/frontend_detailed_design.md`) ✅
- [x] **인증/권한 관리 설계서** (`docs/02_design/authentication_authorization_detailed_design.md`) ✅
- [x] **UI Storyboard** (`docs/02_design/ui_storyboard/`) ✅
- [x] **프레젠테이션 자료 생성** (6개 PPT, 58장) ✅
- [x] **통합 API 설계서** (`docs/02_design/api_integration_design.md`) ✅
- [x] **Backend 상세 설계서** (`docs/02_design/backend_detailed_design.md`) ✅
- [x] **민감 데이터 암호화 설계서** (`docs/02_design/data_encryption_design.md`) ✅
- [x] **인프라 상세 설계서** (`docs/02_design/infrastructure_detailed_design.md`) ✅ 2026-01-16
  - Docker Compose 기반 (K8s에서 변경, 86% 비용 절감)
- [x] **DevOps 상세 설계서** (`docs/02_design/devops_detailed_design.md`) ✅ 2026-01-16
- [x] **에러 코드 표준** (`docs/02_design/error_code_standards.md`) ✅ 2026-01-16
- [x] **용어사전 v2.1** (`docs/02_design/glossary.md`) ✅ Gleaning 용어 추가
- [x] **UI 디자인 시스템 가이드** (`docs/02_design/ui_design_system_guide.md`) ✅ 2026-01-16
- [x] **RAG 성능 테스트 설계** (`docs/02_design/rag_performance_test_design.md`) ✅ 2026-01-16
- [x] **기술 검토 문서** (`docs/02_design/technical_assessment/`) ✅ 2026-01-16
  - Gleaning 지식 그래프 품질 검토 (+33% Entity Recall)
  - K8s 참조 설계서 백업 (향후 확장용)
  - API 아키텍처 설계 검토 (Option A/B/C 분석)
  - TLS 인증서 구현 검토

### 마일스톤 달성 (2026-01-17)
- [x] **설계 완료 선언** - 종합 점수 9.1/10, 탁월 5개 문서 달성
- [x] **Backend 설계서 95%** - SSE, Prometheus, Saga, Rate Limiting, Liquibase, Grafana
- [x] **Frontend 설계서 95%** - WebSocket, MSW, Bundle 최적화, Storybook, PWA
- [x] **UI Design System 95%** - 복합 컴포넌트, 반응형 패턴, 차트 시각화

### 선택 작업 (Phase 3 착수 후 필요시)
- [ ] **통합 아키텍처 설계서** (`docs/02_design/integrated_architecture_design.md`) - 선택
  - 모든 설계서 통합 리뷰
  - 시스템 전체 아키텍처 다이어그램

## Phase 3: Implementation (구현) - 0% ⏸️ 대기 중

### 시작 조건 (Prerequisites)
- [ ] Phase 2 설계 완료 (통합 아키텍처 설계서 포함)
- [ ] 개발 에이전트 소싱 완료
- [ ] 개발 환경 셋업 (Docker Compose, 로컬 환경)

### 다음 단계 (Phase 2 완료 후)
- [ ] 개발 환경 구축 (Docker Compose)
- [ ] AI Service Phase 1 구현 (기반 구축)
- [ ] SpringBoot Backend Phase 1 구현
- [ ] 데이터베이스 초기화 스크립트
- [ ] API 엔드포인트 구현

---

## ALM (Application Lifecycle Management) 전략

### 도구 구성

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           ALM Toolchain                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  [Source Control]     [Project Management]    [Communication]            │
│  ┌─────────────┐      ┌─────────────────┐     ┌─────────────────┐       │
│  │   GitHub    │      │   JIRA Cloud    │     │     Slack       │       │
│  │ - Repository│      │ - Backlog       │     │ - AI Agents     │       │
│  │ - PR Review │      │ - Kanban Board  │     │ - Notifications │       │
│  │ - Actions   │      │ - Sprint        │     │ - Collaboration │       │
│  │ - Projects  │      │ - Release       │     │ - Bot Commands  │       │
│  └──────┬──────┘      └────────┬────────┘     └────────┬────────┘       │
│         │                      │                       │                 │
│         └──────────────────────┼───────────────────────┘                 │
│                                │                                         │
│                    ┌───────────▼───────────┐                            │
│                    │   Integration Hub     │                            │
│                    │ - GitHub ↔ JIRA       │                            │
│                    │ - JIRA ↔ Slack        │                            │
│                    │ - GitHub ↔ Slack      │                            │
│                    └───────────────────────┘                            │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### GitHub 프로젝트 구성
```
hybrid-rag-knowledge-ops/
├── .github/
│   ├── workflows/           # CI/CD Pipelines
│   │   ├── ci.yml          # Build, Test, Lint
│   │   ├── cd-staging.yml  # Deploy to Staging
│   │   ├── cd-prod.yml     # Deploy to Production
│   │   └── release.yml     # Release Automation
│   ├── ISSUE_TEMPLATE/     # Issue Templates
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── CODEOWNERS
├── projects/                # GitHub Projects (Kanban)
└── releases/               # Release Notes
```

### JIRA Cloud 구성
```
Project: HRKP (Hybrid RAG Knowledge Platform)
├── Board: Kanban
│   ├── Backlog
│   ├── To Do
│   ├── In Progress
│   ├── Code Review
│   ├── Testing
│   └── Done
├── Epics:
│   ├── HRKP-E1: Frontend Development
│   ├── HRKP-E2: Backend Development
│   ├── HRKP-E3: AI Service Development
│   ├── HRKP-E4: Infrastructure/DevOps
│   └── HRKP-E5: ALM Setup
└── Releases:
    ├── v0.1.0 - MVP (기본 검색)
    ├── v0.2.0 - Graph RAG 통합
    ├── v0.3.0 - 시간 인식 추론
    └── v1.0.0 - 정식 출시
```

### Slack AI Agent 구성
```
Workspace: hybrid-rag-dev
├── Channels:
│   ├── #general              # 일반 공지
│   ├── #dev-frontend         # 프론트엔드 개발
│   ├── #dev-backend          # 백엔드 개발
│   ├── #dev-ai-service       # AI 서비스 개발
│   ├── #devops               # 인프라/배포
│   ├── #code-review          # 코드 리뷰 알림
│   ├── #ci-cd-alerts         # CI/CD 알림
│   └── #ai-agents            # AI Agent 전용 채널
│
├── AI Agents (Bots):
│   ├── Claude-Code-Agent     # 아키텍트 + 개발
│   │   └── Commands:
│   │       ├── /claude code <task>
│   │       ├── /claude review <PR#>
│   │       ├── /claude design <feature>     # 아키텍처 설계
│   │       ├── /claude standard <type>      # 개발표준 산출물
│   │       └── /claude guide <component>    # 디자인 가이드
│   │
│   ├── Antigravity-Agent     # UI 전문 + 테스터
│   │   └── Commands:
│   │       ├── /antigravity component <name>
│   │       ├── /antigravity test <component>
│   │       └── /antigravity a11y <page>     # 접근성 검증
│   │
│   ├── JIRA-Bot              # JIRA 연동
│   │   └── Commands:
│   │       ├── /jira create <summary>
│   │       ├── /jira status <ticket>
│   │       └── /jira assign <ticket> <user>
│   │
│   └── GitHub-Bot            # GitHub 연동
│       └── Auto Notifications:
│           ├── PR Created/Merged
│           ├── CI/CD Status
│           └── Release Published
│
└── Integrations:
    ├── GitHub App
    ├── JIRA Cloud for Slack
    └── Custom Claude Bot (API)
```

### 릴리즈 관리 전략

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       Release Management Flow                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Feature Branch    →    Develop    →    Release    →    Main            │
│       │                    │               │              │              │
│       ▼                    ▼               ▼              ▼              │
│  [PR Created]      [Auto Deploy]    [RC Testing]   [Production]         │
│       │            to Staging            │          Release              │
│       ▼                                  ▼              │                │
│  [Code Review]                     [QA Sign-off]       ▼                │
│  [CI Tests]                              │         [Tag v1.x.x]         │
│       │                                  ▼              │                │
│       ▼                            [Merge to Main]     ▼                │
│  [Merge to Dev]                          │         [Release Notes]      │
│                                          ▼         [JIRA Release]       │
│                                   [Deploy to Prod]                       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

Versioning: Semantic Versioning (SemVer)
- MAJOR.MINOR.PATCH (예: v1.2.3)
- v0.x.x: 초기 개발 단계
- v1.0.0: 첫 정식 릴리즈
```

---

## 현재 작업 큐 (Priority Order)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. [P0-HIGH] DevOps 설계서 기반 역할별 Skills 생성                       │
│    └─ 자동화 워크플로우 구성                                             │
├─────────────────────────────────────────────────────────────────────────┤
│ 2. [P0-HIGH] 설계서 기반 통합테스트 계획서 작성                           │
│    └─ E2E 테스트 시나리오, 품질 기준 정의                                │
├─────────────────────────────────────────────────────────────────────────┤
│ 3. [P0-HIGH] Claude Code Agent 구성 계획 수립                            │
│    └─ MCP/Skills/Hooks 구성 설계                                        │
├─────────────────────────────────────────────────────────────────────────┤
│ 4. [P1-MEDIUM] 개발 환경 구축 (Phase 3 시작 시)                          │
│    └─ Docker Compose, DB 초기화, 로컬 환경 설정                          │
├─────────────────────────────────────────────────────────────────────────┤
│ 5. [P1-MEDIUM] AI Service 프로젝트 초기화                                │
│    └─ FastAPI + Poetry, 디렉토리 구조, VIP 파이프라인 기본 구조          │
├─────────────────────────────────────────────────────────────────────────┤
│ 6. [P1-MEDIUM] Keycloak 인증 서버 설정                                   │
│    └─ OAuth 2.0 + PKCE 구성                                             │
├─────────────────────────────────────────────────────────────────────────┤
│ 7. [P2-LOW] SpringBoot 프로젝트 초기화                                   │
│    └─ Spring Initializr, 기본 의존성, API Gateway 설정                  │
├─────────────────────────────────────────────────────────────────────────┤
│ 8. [P2-LOW] Frontend 프로젝트 초기화                                     │
│    └─ Vite + React + TypeScript                                        │
└─────────────────────────────────────────────────────────────────────────┘

✅ 완료된 P0 작업 (2026-01-16):
- API 상세 설계서 (api_integration_design.md)
- Backend 상세 설계서 (backend_detailed_design.md)
- 민감 데이터 암호화 설계서 (data_encryption_design.md)
- 인프라 설계서 (infrastructure_detailed_design.md) - K8s→Docker Compose
- DevOps 설계서 (devops_detailed_design.md)
- Gleaning 기술 통합 (hybrid_rag_platform v2.4)
- 18개 신규 문서, 6개 업데이트
```

---

## 문서 구조 (확장)

```
docs/
├── 01_planning/                         # 기획 문서
│   ├── hybrid_rag_knowledge_platform_plan.md    ✅ 완료
│   ├── frontend_implementation_plan.md          ✅ 완료
│   ├── backend_implementation_plan.md           ✅ 완료
│   ├── ai_service_implementation_plan.md        ✅ 완료 v2.0
│   ├── dev_environment_plan.md                  ✅ 완료
│   ├── test_plan.md                             ✅ 완료
│   ├── devops_alm_plan.md                       ✅ 완료
│   └── review/
│       └── 2026-01-14_planning_review_report.md ✅ 완료
│
├── 02_design/                           # 설계 문서 (18개 신규, 6개 업데이트)
│   ├── hybrid_rag_platform_detailed_design.md   ✅ v2.4 완료 (Gleaning 통합)
│   ├── frontend_detailed_design.md              ✅ 완료
│   ├── authentication_authorization_detailed_design.md  ✅ 완료
│   ├── api_integration_design.md                ✅ 완료 (External + Internal API)
│   ├── backend_detailed_design.md               ✅ 완료 (17개 섹션)
│   ├── data_encryption_design.md                ✅ 완료
│   ├── infrastructure_detailed_design.md        ✅ 완료 (Docker Compose 기반)
│   ├── devops_detailed_design.md                ✅ 완료 (CI/CD, 모니터링)
│   ├── error_code_standards.md                  ✅ 완료 (E1xxx~E9xxx)
│   ├── glossary.md                              ✅ 완료 v2.1 (Gleaning 포함)
│   ├── ui_design_system_guide.md                ✅ 완료
│   ├── rag_performance_test_design.md           ✅ 완료
│   ├── integrated_detailed_design.md            ✅ 완료 (목차)
│   ├── integrated_architecture_design.md        🔜 선택 (통합 아키텍처)
│   ├── technical_assessment/                    ✅ 완료
│   │   ├── gleaning_knowledge_graph_quality_assessment.md  ✅ 신규
│   │   ├── infrastructure_k8s_reference_design.md          ✅ K8s 백업
│   │   ├── 01.API_architecture_design_review.md
│   │   └── 02.TLS_certificate_implementation_review.md
│   ├── ui_storyboard/                           ✅ 완료 (4개 문서 + 2개 PPT)
│   └── review/                                  ✅ 완료
│       ├── REVIEW_SUMMARY.md
│       ├── 2026-01-16_design_2nd_review.md
│       ├── 2026-01-16_infrastructure_change_review.md
│       └── (8개 개별 검토 문서)
│
├── work_logs/                           # 작업 일지
│   ├── daily_logs/2026/01-January/
│   └── vibe_logs/2026/01-January/
│
└── presentations/                       # 프레젠테이션 자료
    └── docs/ (GitHub 외부 저장)
```

---

## Key Decisions Made

| 영역 | 결정 | 선택 | 이유 |
|------|------|------|------|
| **AI** | LLM | DeepSeek-Chat V3.2 | 95% 비용 절감 |
| **AI** | 임베딩 | BGE-M3 | Dense + Sparse 단일 모델 |
| **AI** | Agent | LangGraph ReAct | 검증된 라이브러리 |
| **AI** | Gleaning | 1회 적용 | +33% Entity Recall, +60% 비용 (최적) |
| **Frontend** | Framework | React 18 + TypeScript | 최신 기술, 타입 안정성 |
| **Backend** | Framework | SpringBoot 3.x | 기업 표준, MSA |
| **AI Service** | Framework | Python + FastAPI | LangChain 생태계 |
| **Infra** | 플랫폼 | Docker Compose | K8s 대비 86% 비용 절감 (YAGNI) |
| **Infra** | 확장 경로 | DC → Swarm → K8s | 단계적 마이그레이션 |
| **ALM** | Source | GitHub | 코드 + Projects + Actions |
| **ALM** | Project Mgmt | JIRA Cloud | 백로그, 칸반, 릴리즈 |
| **ALM** | Communication | Slack | AI Agent 통합 |

---

## Architecture Overview

### 시스템 구성 (확장)
```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Slack Workspace                                 │
│              (AI Agents: Claude Code, Antigravity, JIRA Bot, GitHub Bot)│
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────────┐
│                        Frontend (React)                                  │
│                    React 18 + TypeScript + MUI                          │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────────┐
│                     Spring Cloud Gateway                                 │
│                (인증, 라우팅, 로드밸런싱)                                 │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
         ┌──────────────────────┼──────────────────────┐
         ▼                      ▼                      ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│ Knowledge       │   │ Search          │   │ User            │
│ Service         │   │ Service         │   │ Service         │
│ (SpringBoot)    │   │ (SpringBoot)    │   │ (SpringBoot)    │
└────────┬────────┘   └────────┬────────┘   └─────────────────┘
         │                     │
         └─────────┬───────────┘
                   ▼
        ┌──────────────────────┐
        │  AI Service (Python) │
        │  FastAPI + LangGraph │
        │  - RAG Pipeline      │
        │  - ReAct Agent       │
        │  - Embedding         │
        └──────────┬───────────┘
                   │
     ┌─────────────┼─────────────┐
     ▼             ▼             ▼
┌──────────┐ ┌────────────┐ ┌─────────┐
│PostgreSQL│ │Elasticsearch│ │  Neo4j  │
│  (SSOT)  │ │  (Vector)   │ │ (Graph) │
└──────────┘ └────────────┘ └─────────┘

CI/CD Pipeline (GitHub Actions)
┌────────────────────────────────────────────────────────────────────────┐
│ Push → Build → Test → Lint → Security Scan → Deploy (Staging/Prod)    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Claude Code 환경 업그레이드 계획

### MCP (Model Context Protocol) 구성

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Claude Code MCP Integration                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐ │
│  │  GitHub     │   │   JIRA      │   │   Slack     │   │  Database   │ │
│  │  MCP Server │   │  MCP Server │   │  MCP Server │   │ MCP Servers │ │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘ │
│         │                 │                 │                 │         │
│         └─────────────────┴─────────────────┴─────────────────┘         │
│                                   │                                      │
│                         ┌─────────▼─────────┐                           │
│                         │    Claude Code    │                           │
│                         │   + Skills/Hooks  │                           │
│                         └───────────────────┘                           │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### MCP 서버 설정 계획

| MCP 서버 | 용도 | 설정 방식 |
|----------|------|----------|
| **GitHub** | PR 생성/리뷰, 이슈 관리 | HTTP (`api.githubcopilot.com`) |
| **JIRA** | 백로그/칸반 관리 | HTTP (Atlassian Cloud) |
| **PostgreSQL** | 메타데이터 조회/저장 | stdio (`@bytebase/dbhub`) |
| **Elasticsearch** | 벡터 검색/인덱싱 | stdio (Custom Python) |
| **Neo4j** | 그래프 쿼리 | stdio (Custom Python) |

### .mcp.json 설정 (계획)
```json
{
  "mcpServers": {
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/"
    },
    "postgres": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@bytebase/dbhub"],
      "env": {"DSN": "${POSTGRES_URL}"}
    },
    "elasticsearch": {
      "type": "stdio",
      "command": "python",
      "args": [".claude/mcp/elasticsearch_server.py"],
      "env": {"ES_URL": "${ELASTICSEARCH_URL}"}
    }
  }
}
```

### Skills 구성 계획

```
.claude/skills/
├── pr-review/                    # PR 코드 리뷰
│   └── SKILL.md
├── knowledge-extraction/         # 지식 요소 추출
│   └── SKILL.md
├── elasticsearch-search/         # ES 벡터/키워드 검색
│   └── SKILL.md
├── jira-management/             # JIRA 이슈 관리
│   └── SKILL.md
├── graph-query/                 # Neo4j 그래프 쿼리
│   └── SKILL.md
└── metadata-extraction/         # 문서 메타데이터 추출
    └── SKILL.md
```

### Hooks 구성 계획

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {"type": "command", "command": "./.claude/hooks/python_formatter.py"},
          {"type": "command", "command": "./.claude/hooks/markdown_formatter.py"}
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {"type": "command", "command": "./.claude/hooks/bash_validator.py"}
        ]
      }
    ]
  }
}
```

### 자동화 워크플로우 (목표)

```
1. PR 자동 리뷰
   User: "PR #123 리뷰해줘"
   Claude: [GitHub MCP] → [pr-review Skill] → 코멘트 작성

2. 문서 → 지식 그래프
   User: "이 문서 분석해서 DB에 저장해"
   Claude: [knowledge-extraction Skill] → [PostgreSQL MCP] → [Neo4j MCP] → [ES MCP]

3. JIRA 연동 개발
   User: "HRKP-123 이슈 구현해"
   Claude: [JIRA MCP] → 요구사항 확인 → 코드 작성 → PR 생성

4. Slack 알림
   Claude: [Slack MCP] → 진행상황 보고
```

---

## Blockers / Issues

현재 블로커 없음.

---

## Session Notes

### 2026-01-17 (설계 완료 마일스톤)
- **Phase 2 설계 완료 달성** - 종합 점수 9.1/10
  - 탁월(95%+) 문서: 5개 달성 (Backend, Frontend, UI Design System, API, Platform)
  - 3차 리뷰 완료: `2026-01-17_design_3rd_review.md`
- **핵심 설계서 개선** (88% → 95%)
  - Backend: SSE 스트리밍, Prometheus 메트릭, Saga 패턴, Rate Limiting, Liquibase, Grafana
  - Frontend: WebSocket 통신, MSW API Mocking, Bundle 최적화, Storybook, PWA, CI/CD
  - UI Design System: 복합 컴포넌트 5종, 반응형 사이드바, 모달 스택, Markdown 렌더러, 차트 시각화
- **Mermaid 다이어그램 15개+ 추가**
- **작업 일지 & 바이브 코딩 일지 작성**
- **Phase 2 진행률**: 95% → 100% 완료 ✅
- **다음 단계**: 인력 확보 및 역할 배정 후 Phase 3 착수

### 2026-01-16 (Evening)
- **Gleaning 기술 통합** - Microsoft GraphRAG 기반 다중 추출 기법
  - Entity Recall 60% → 80% (+33% 향상)
  - 비용 +60% 증가 (1회 gleaning 최적)
  - `hybrid_rag_platform_detailed_design.md` v2.3 → v2.4 업데이트
  - `api_integration_design.md`에 enableGleaning, maxGleanings 옵션 추가
  - `glossary.md` v2.0 → v2.1 업데이트 (Gleaning 용어 추가)
- **인프라 설계 변경** (K8s → Docker Compose)
  - 서버 규모: 13대 → 1~2대
  - 예상 비용: ~$100,000 → ~$14,000 (86% 절감)
  - YAGNI 원칙 적용 (필요할 때 확장)
  - K8s 설계서는 `technical_assessment/`에 백업 보관
- **대규모 설계서 작성** (18개 신규, 6개 업데이트)
  - 인프라 설계서, DevOps 설계서, 에러 코드 표준
  - 용어사전, UI 디자인 시스템 가이드, RAG 성능 테스트 설계
  - 9개 설계서 2차 검토 완료
- **Git 커밋**: 35 files changed, +26,866 insertions
- **작업 일지 & 바이브 코딩 일지 작성**
- **Phase 2 진행률**: 90% → 95% 업데이트

### 2026-01-16 (Morning)
- **Backend 상세 설계서 완성** (`backend_detailed_design.md`)
  - 17개 섹션 구성 (아키텍처, 모듈구조, 패키지, 레이어, JPA 등)
  - 개발 에이전트가 이해하고 구현할 수 있도록 상세 작성
- **기술 검토 문서 작성** (`technical_assessment/`)
  - API 아키텍처 설계 검토 (Option A/B/C 분석 → Option C 선정)
  - TLS 인증서 구현 검토 (환경별 요구사항 정리)
- **설계서 Mermaid 다이어그램 변환**
  - api_integration_design.md, data_encryption_design.md
  - authentication_authorization_detailed_design.md (4개 다이어그램)
  - hybrid_rag_platform_detailed_design.md, frontend_detailed_design.md

### 2026-01-15
- **프레젠테이션 자료 대량 생성** (6개 PPT, 58장)
  - Hybrid RAG Platform 설계서 (Brown 테마)
  - Frontend 상세 설계서 (Brown 테마)
  - 인증/권한 관리 설계서 (Brown 테마)
  - UI Storyboard (Brown 테마 + 개발자 가이드)
- **Presentation Maker Skill v2.0 업데이트**
  - Brown Earth 테마 추가
  - 듀얼 패널 레이아웃 (와이어프레임 + 설명 박스)
- **Web Design System Skill v2.0 보완**
  - 다크 모드, 모션 디자인, Core Web Vitals 가이드 추가
- **다음 작업 우선순위 재정의**
  - P0: API 설계서, Backend 설계서, 민감 데이터 암호화 설계
  - P1: 개발 환경 구축, AI Service 초기화
  - P2: SpringBoot 초기화

### 2026-01-14 (Evening - Updated)
- PLAN.md 범위 대폭 확장
- ALM 전략 추가 (GitHub + JIRA Cloud + Slack)
- Slack AI Agent 구성 계획 추가
- 릴리즈 관리 전략 정의
- **현재 작업**: 기획 문서 범위 확정 및 우선순위 결정
- **다음 작업**: 문서 작성 순서 결정 후 진행

### 2026-01-14 (Morning)
- 설계서 코드 검증 리뷰 완료
- 4가지 치명적 이슈 수정
- 복잡도 기반 라우팅 전략 설계 추가
- 문서 버전 2.2로 업데이트

---

## Quick Commands

```bash
# Docker 환경 시작
cd infrastructure/docker && docker-compose up -d

# API 서버 시작
cd knowledge_service && uvicorn app.main:app --reload --port 8000

# 테스트 실행
cd knowledge_service && poetry run pytest

# 작업 일지 생성
.\scripts\create_worklog.ps1
```

---

## References

- [상세 설계서](./knowledge_service/docs/02_design/hybrid_rag_platform_detailed_design.md)
- [구축 계획서](./knowledge_service/docs/01_planning/hybrid_rag_knowledge_platform_plan.md)
- [프론트엔드 구현 계획서](./knowledge_service/docs/01_planning/frontend_implementation_plan.md)
- [코드 리뷰](./knowledge_service/docs/02_design/review/2026-01-14_detailed_code_review.md)
- [CLAUDE.md](./CLAUDE.md) - 개발 가이드라인
