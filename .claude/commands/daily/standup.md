---
description: 데일리 스탠드업 미팅 시작 (팀원 인사 + 상태 공유)
allowed-tools: Bash, Read, Glob, Grep
---

# Daily Standup - 스탠드업 미팅 시작

데일리 스탠드업 미팅을 시작하고, 모든 팀원 에이전트가 Slack에 인사와 상태를 공유합니다.

## 채널
- `#proj-hrkp-standup` - 스탠드업 전용 채널

## 실행 단계

### 1. PM Agent가 스탠드업 시작 선언

```bash
send_slack() {
    local text="$1"
    curl -s -X POST "https://slack.com/api/chat.postMessage" \
        -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
        -H "Content-Type: application/json; charset=utf-8" \
        -d "{\"channel\": \"proj-hrkp-standup\", \"text\": \"$text\"}"
}

source .env
send_slack "*[PM]* === Daily Standup 시작 === $(date +%Y-%m-%d)"
```

### 2. 각 에이전트가 인사 + 상태 공유

**순서**: PM -> TechLead -> Backend -> Frontend -> MLRag -> Data -> QA -> DevOps -> Infra

각 에이전트는 다음 형식으로 메시지 전송:

```
*[에이전트명]* 안녕하세요! {개성있는 인사}
• 어제: {어제 완료한 것}
• 오늘: {오늘 할 것}
• 블로커: {있으면 공유, 없으면 "없음"}
• 한마디: {자유롭게 한마디}
```

### 3. 에이전트별 인사말 스타일

| Agent | 인사 스타일 | 한마디 주제 |
|-------|-----------|------------|
| PM | 팀 격려, 목표 상기 | Sprint 진행률, 일정 |
| TechLead | 기술 인사이트 공유 | 아키텍처 팁, 기술 트렌드 |
| Backend | 실용적, 간결 | API 상태, 성능 |
| Frontend | 친근하고 밝게 | UX 아이디어, 디자인 |
| MLRag | 호기심 많은 AI 느낌 | RAG 품질, 모델 인사이트 |
| Data | 데이터 관점 | 데이터 통계, 품질 지표 |
| QA | 꼼꼼하고 신중 | 테스트 커버리지, 버그 현황 |
| DevOps | 시스템 관점 | 인프라 상태, 배포 현황 |
| Infra | 안정성 중시 | 컨테이너 상태, 리소스 |

### 4. 스탠드업 종료

```bash
send_slack "*[PM]* === Daily Standup 종료 === 오늘도 화이팅!"
```

## 실행 스크립트

```bash
#!/bin/bash
source .env

CHANNEL="proj-hrkp-standup"
TOKEN="$SLACK_BOT_TOKEN"
TODAY=$(date +%Y-%m-%d)

send() {
    curl -s -X POST "https://slack.com/api/chat.postMessage" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json; charset=utf-8" \
        -d "{\"channel\": \"$CHANNEL\", \"text\": \"$1\"}"
}

# 스탠드업 시작
send "*[PM]* === Daily Standup $TODAY ==="
sleep 1

# 각 에이전트 인사 (실제로는 각 에이전트가 자신의 상태를 분석하여 전송)
# 아래는 예시 - 실제로는 git log, 작업일지 등을 분석하여 생성

send "*[PM]* 안녕하세요! 오늘도 좋은 하루 시작합니다.
• 어제: Sprint 01 계획 완료
• 오늘: SCRUM-10 착수 조율
• 블로커: 없음
• 한마디: Sprint 01 목표 달성을 향해 함께 가봅시다!"

send "*[TechLead]* 반갑습니다. 기술적 도전을 즐기는 하루가 되길.
• 어제: 설계 문서 최종 검토
• 오늘: 코드 리뷰 대기
• 블로커: 없음
• 한마디: 좋은 설계가 좋은 코드를 만듭니다."

# ... (다른 에이전트들도 동일하게)

send "*[PM]* === Standup 종료 === 오늘도 화이팅!"
```

## 5. 스탠드업 기록 생성 (PM 담당)

스탠드업 종료 후 PM Agent가 기록 파일을 생성합니다.

### 기록 폴더 구조

```
work_logs/standups/
├── README.md
└── YYYY/
    └── MM-Month/
        └── YYYY-MM-DD_HH-MM.md
```

### 파일명 규칙

- **형식**: `YYYY-MM-DD_HH-MM.md`
- **예시**: `2026-01-21_16-20.md` (하루에 여러 번 가능)

### 기록 내용 (필수)

```markdown
# Daily Standup Meeting

**날짜**: YYYY-MM-DD
**시간**: HH:MM
**채널**: #proj-hrkp-standup

## 참석자
| Agent | 역할 | 상태 |
|-------|------|------|
| PM | Product Manager | ✅ 참석 |
...

## 에이전트별 상태 보고
(각 에이전트의 어제/오늘/블로커/한마디)

## Sprint 현황 (PM Summary)
- Sprint 상태, Velocity, 완료된 Stories

## 팀 상태 분석
- 블로커 현황, 에이전트별 워크로드

## 다음 액션 아이템
- P0/P1/P2 우선순위별 정리

## 리스크 모니터링
- 확률, 영향, 대응 계획
```

### 기록 생성 스크립트

```bash
#!/bin/bash
# 스탠드업 기록 폴더 생성
YEAR=$(date +%Y)
MONTH=$(date +%m-%B)
STANDUP_DIR="work_logs/standups/${YEAR}/${MONTH}"
mkdir -p "$STANDUP_DIR"

# 파일명 생성 (하루에 여러 번 가능)
FILENAME="${STANDUP_DIR}/$(date +%Y-%m-%d_%H-%M).md"

# PM Agent가 기록 작성
echo "스탠드업 기록 파일: $FILENAME"
```

---

## 자동화 옵션

1. **수동 실행**: `/daily:standup` 명령어로 직접 실행
2. **자동 실행**: PM Agent가 Sprint 진행 중 매일 아침 자동 호출

## 실행 후 PM 작업 (필수)

스탠드업 미팅 후 PM Agent는 다음 작업을 수행해야 합니다:

1. ✅ Slack 메시지 전송 완료 확인
2. ✅ `work_logs/standups/YYYY/MM-Month/YYYY-MM-DD_HH-MM.md` 기록 파일 생성
3. ✅ Sprint 현황, 팀 상태, 액션 아이템, 리스크 정리
4. ✅ Slack에 기록 완료 알림 (proj-hrkp-dev)

```bash
# PM이 기록 완료 후 알림
./scripts/send_slack.sh proj-hrkp-dev PM "작업 완료: 스탠드업 미팅 기록 - work_logs/standups/..."
```

## 참고

- 각 에이전트의 "어제/오늘" 내용은 git log, 작업일지, Jira 상태를 분석하여 자동 생성
- "한마디"는 에이전트 성격에 맞는 랜덤 메시지 또는 실제 인사이트
- **스탠드업 기록은 PM Agent의 책임** - 반드시 기록 파일을 생성해야 함
