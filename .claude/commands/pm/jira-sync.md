# Jira Sync - Jira 이슈 일괄 동기화

Jira와 로컬 백로그 파일 상태를 동기화합니다.

## 사용법

```
/pm:jira-sync [sprint_number]
```

## 기능

### 1. 상태 확인
로컬 백로그 파일과 Jira 이슈 상태 비교

### 2. Jira → 로컬 동기화
Jira 상태를 기준으로 로컬 파일 업데이트

### 3. 로컬 → Jira 동기화
로컬 파일 상태를 기준으로 Jira 업데이트

## 실행 프로세스

```bash
# 1. 환경변수 로드
source .env

# 2. Jira API 연결 테스트
curl -sS "https://${JIRA_HOST}/rest/api/3/myself" \
  -u "${JIRA_EMAIL}:${JIRA_API_TOKEN}"

# 3. Sprint 이슈 조회
curl -sS "https://${JIRA_HOST}/rest/api/3/search?jql=project=SCRUM+AND+sprint=XX" \
  -u "${JIRA_EMAIL}:${JIRA_API_TOKEN}"

# 4. 상태별 비교 및 동기화
```

## Jira API 참조

### 이슈 조회
```bash
curl -sS "https://${JIRA_HOST}/rest/api/3/issue/SCRUM-10" \
  -u "${JIRA_EMAIL}:${JIRA_API_TOKEN}"
```

### 상태 변경
```bash
curl -sS -X POST "https://${JIRA_HOST}/rest/api/3/issue/SCRUM-10/transitions" \
  -u "${JIRA_EMAIL}:${JIRA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"transition": {"id": "41"}}'  # 41 = 완료
```

### Transition IDs
| 상태 | ID |
|------|-----|
| 해야 할 일 | 11 |
| 진행 중 | 21 |
| 검토 중 | 31 |
| 완료 | 41 |

## 필요 환경변수

```bash
JIRA_HOST=your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-api-token
JIRA_PROJECT_KEY=SCRUM
```
