# PM Commands - Product Manager 도구

PM(Product Manager) 에이전트를 위한 백로그 및 Jira 관리 명령어입니다.

## 명령어 목록

| 명령어 | 설명 |
|--------|------|
| `/pm:backlog-sync` | Story 상태 동기화 (Sprint 문서 + Story 파일 + Jira + Slack) |
| `/pm:jira-sync` | Jira 이슈 일괄 동기화 |

## 사용 예시

### Story 완료 처리
```bash
/pm:backlog-sync STORY-010 SCRUM-10 Done 01
```

### Sprint 전체 동기화
```bash
/pm:jira-sync 01
```

## 관련 스크립트

| 스크립트 | 설명 |
|----------|------|
| `scripts/backlog-sync.sh` | Story 상태 동기화 쉘 스크립트 |

## 환경변수 설정

`.env` 파일에 다음 설정 필요:

```bash
# Jira (for REST API calls)
JIRA_HOST=your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-api-token
JIRA_PROJECT_KEY=SCRUM

# Note: MCP도 동일한 JIRA_HOST 사용 (도메인만, https:// 제외)
# See .claude/settings.json for MCP configuration

# Slack (선택)
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_CHANNEL=proj-hrkp-dev
```

## Jira Transition IDs

| 상태 | Transition ID | 설명 |
|------|---------------|------|
| To Do | 11 | 해야 할 일 |
| In Progress | 21 | 진행 중 |
| In Review | 31 | 검토 중 |
| Done | 41 | 완료 |

## 참고

- [PM Agent 설정](.claude/agents/project-manager.md)
- [백로그 관리 가이드](backlog/README.md)
- [Jira Slack Claude 통합가이드](docs/07_Jira_Slack_Claude_통합가이드.md)
