# Jira Backlog 관리

프로젝트 백로그를 로컬에서 관리하고 Jira와 동기화하는 가이드

**Version**: 1.0 | **Updated**: 2026-01-18

---

## 폴더 구조

```
backlog/
├── README.md           # 이 파일
├── epics/              # Epic 정의
│   └── EPIC-XXX-title.md
├── stories/            # User Story
│   └── STORY-XXX-title.md
└── sprints/            # 스프린트 계획
    └── sprint-XX.md
```

---

## 파일 명명 규칙

| 유형 | 형식 | 예시 |
|------|------|------|
| Epic | `EPIC-{번호}-{제목}.md` | `EPIC-001-document-processing.md` |
| Story | `STORY-{번호}-{제목}.md` | `STORY-001-file-upload.md` |
| Sprint | `sprint-{번호}.md` | `sprint-01.md` |

---

## Jira 이슈 타입 매핑

| 로컬 | Jira Issue Type |
|------|-----------------|
| Epic | Epic |
| Story | Story |
| Task (Story 내) | Sub-task |
| Bug | Bug |

---

## 워크플로우

### 1. 로컬에서 백로그 작성
```bash
# Epic 작성
vi backlog/epics/EPIC-001-document-processing.md

# Story 작성
vi backlog/stories/STORY-001-file-upload.md
```

### 2. Jira 등록 (수동)
- 로컬 파일 내용을 Jira에 복사
- Jira 이슈 번호를 파일에 업데이트

### 3. Jira 등록 (Claude Agent 활용)
```bash
# Claude Code에서
"backlog/stories/STORY-001-file-upload.md 내용으로 Jira 이슈 생성해줘"
```

### 4. 동기화 상태 관리
- 파일 내 `jira_id` 필드로 동기화 상태 추적
- `status: synced` / `status: pending`

---

## 우선순위 정의

| Priority | 설명 | SLA |
|----------|------|-----|
| Critical | 서비스 장애, 보안 이슈 | 즉시 |
| High | 핵심 기능, 블로커 | 이번 스프린트 |
| Medium | 일반 기능 | 다음 스프린트 |
| Low | 개선사항, Nice-to-have | 백로그 |

---

## Story Point 기준

| Point | 복잡도 | 예상 작업량 |
|-------|--------|-------------|
| 1 | 매우 간단 | 설정 변경, 오타 수정 |
| 2 | 간단 | 단일 함수 수정 |
| 3 | 보통 | 단일 기능 구현 |
| 5 | 복잡 | 여러 파일 수정, 테스트 포함 |
| 8 | 매우 복잡 | 새 모듈, 통합 필요 |
| 13 | 에픽급 | 분해 필요 |

---

## 상태 정의

| Status | 설명 |
|--------|------|
| `draft` | 작성 중 |
| `ready` | Jira 등록 대기 |
| `synced` | Jira에 등록됨 |
| `in_progress` | 작업 중 |
| `done` | 완료 |

---

## 참고

- [02_스프린트_실행_계획서.md](../docs/02_스프린트_실행_계획서.md)
- [개발자 통합 가이드](../knowledge_service/docs/05_development/02_developer_integration_guide.md)
