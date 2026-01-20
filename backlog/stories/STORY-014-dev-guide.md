# STORY-014: 개발 환경 가이드

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-14 |
| **Epic** | EPIC-000 Infrastructure |
| **Status** | Done |
| **Priority** | Medium |
| **Story Points** | 3 |
| **Assignee** | TechLead |
| **Sprint** | 1 |

---

## 사용자 스토리

**As a** 신규 개발자
**I want** 상세한 개발 환경 설정 가이드가 있기를
**So that** 빠르게 개발 환경을 구축하고 프로젝트에 참여할 수 있다

---

## Acceptance Criteria

### AC1: README 업데이트
```gherkin
Given README.md 파일이 있을 때
When 신규 개발자가 읽으면
Then 프로젝트 개요와 Quick Start 방법을 이해할 수 있다
And 필요한 사전 조건을 확인할 수 있다
```

### AC2: 로컬 개발 환경 가이드
```gherkin
Given 개발 환경 가이드 문서가 있을 때
When 가이드를 따라 설정하면
Then Docker Compose로 전체 인프라를 기동할 수 있다
And 각 서비스의 개발 서버를 실행할 수 있다
```

### AC3: IDE 설정 가이드
```gherkin
Given IDE 설정 가이드가 있을 때
When VSCode 또는 IntelliJ에서 설정하면
Then 린터/포맷터가 자동으로 적용된다
And 디버깅 설정이 완료된다
```

---

## 기술 명세

### 문서 구조

```
docs/
├── README.md                    # 프로젝트 개요 + Quick Start
├── CONTRIBUTING.md              # 기여 가이드
└── development/
    ├── local-setup.md           # 로컬 환경 설정
    ├── ide-setup.md             # IDE 설정
    ├── docker-guide.md          # Docker 사용법
    └── troubleshooting.md       # 문제 해결
```

### 필수 내용

#### README.md
- 프로젝트 소개
- 기술 스택 요약
- Quick Start (5분 내 실행)
- 문서 링크

#### local-setup.md
- 사전 조건 (Docker, Node.js, Python, Java)
- .env 파일 설정
- Docker Compose 실행 방법
- 개별 서비스 실행 방법
- 초기 데이터 로딩

#### ide-setup.md
- VSCode 확장 프로그램 목록
- IntelliJ 플러그인 목록
- 설정 파일 (.vscode/, .idea/)
- 디버깅 설정

---

## 작업 분해

- [ ] README.md 업데이트
- [ ] local-setup.md 작성
- [ ] ide-setup.md 작성
- [ ] docker-guide.md 작성
- [ ] troubleshooting.md 작성 (기본)
- [ ] .vscode/settings.json 추가
- [ ] .vscode/extensions.json 추가
- [ ] 문서 리뷰

---

## 참고 자료

- [CLAUDE.md](../../CLAUDE.md) - 개발 규칙
- [스프린트 실행 계획서 - 개발 환경 가이드](../../docs/02_스프린트_실행_계획서.md#15-개발-환경-가이드)
