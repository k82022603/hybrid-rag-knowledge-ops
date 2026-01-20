# Backlog Sync - Story 상태 동기화

Story 상태 변경 시 Sprint 문서, Story 파일, Jira를 동시에 업데이트합니다.

## 사용법

```
/pm:backlog-sync STORY-010 SCRUM-10 Done 01
```

## 파라미터

| 파라미터 | 설명 | 예시 |
|----------|------|------|
| STORY_ID | Story 파일 ID | STORY-010 |
| JIRA_ID | Jira 이슈 키 | SCRUM-10 |
| STATUS | 변경할 상태 | "In Progress", "In Review", "Done" |
| SPRINT_NUM | Sprint 번호 | 01, 02 |

## 실행 내용

1. **Sprint 문서 업데이트** - `backlog/sprints/sprint-XX.md`
2. **Story 파일 업데이트** - `backlog/stories/STORY-XXX-*.md`
3. **Jira 상태 변경** - API 호출 (환경변수 필요)
4. **Slack 알림** - 팀 채널 알림 (환경변수 필요)

## 스크립트 직접 실행

```bash
./scripts/backlog-sync.sh STORY-010 SCRUM-10 Done 01
```

## Jira Transition IDs

| 상태 | Transition ID |
|------|---------------|
| 해야 할 일 (To Do) | 11 |
| 진행 중 (In Progress) | 21 |
| 검토 중 (In Review) | 31 |
| 완료 (Done) | 41 |

## 필요 환경변수

```bash
# .env 파일에 설정 필요
JIRA_HOST=your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-api-token
SLACK_BOT_TOKEN=xoxb-your-token  # 선택
SLACK_CHANNEL=proj-hrkp-dev       # 선택
```

## 예시

### Story 시작
```bash
/pm:backlog-sync STORY-001 SCRUM-6 "In Progress" 02
```

### Story 완료
```bash
/pm:backlog-sync STORY-001 SCRUM-6 Done 02
```

### 일괄 완료 (Sprint 01 전체)
```bash
./scripts/backlog-sync.sh STORY-010 SCRUM-10 Done 01
./scripts/backlog-sync.sh STORY-011 SCRUM-11 Done 01
./scripts/backlog-sync.sh STORY-012 SCRUM-12 Done 01
./scripts/backlog-sync.sh STORY-013 SCRUM-13 Done 01
./scripts/backlog-sync.sh STORY-014 SCRUM-14 Done 01
```
