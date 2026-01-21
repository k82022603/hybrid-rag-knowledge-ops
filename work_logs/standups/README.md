# Standup Meetings

스탠드업 미팅 기록을 관리하는 폴더입니다.

## 폴더 구조

```
standups/
├── README.md                          # 이 파일
└── YYYY/                              # 연도별 폴더
    └── MM-Month/                      # 월별 폴더 (01-January 형식)
        └── YYYY-MM-DD_HH-MM.md        # 스탠드업 기록 파일
```

## 파일 명명 규칙

**형식**: `YYYY-MM-DD_HH-MM.md`

- **YYYY**: 연도 (예: 2026)
- **MM**: 월 (예: 01)
- **DD**: 일 (예: 21)
- **HH**: 시 (24시간 형식, 예: 16)
- **MM**: 분 (예: 20)

**예시**:
- `2026-01-21_09-00.md` - 2026년 1월 21일 오전 9시 스탠드업
- `2026-01-21_16-20.md` - 2026년 1월 21일 오후 4시 20분 스탠드업

> **참고**: 하루에 여러 번 스탠드업이 진행될 수 있으므로 시간을 포함합니다.

## 스탠드업 기록 내용

각 스탠드업 기록에는 다음 내용이 포함됩니다:

1. **미팅 정보**: 날짜, 시간, 채널
2. **참석자**: 9개 에이전트 참석 여부
3. **에이전트별 상태 보고**:
   - 어제 완료한 작업
   - 오늘 계획된 작업
   - 블로커 (있는 경우)
   - 한마디 (인사이트, 팁 등)
4. **요약**:
   - 주요 성과
   - 오늘 계획
   - 블로커 현황
   - 인프라 상태

## 에이전트 목록

| Agent | 역할 | 인사 스타일 |
|-------|------|------------|
| PM | Product Manager | 팀 격려, 목표 상기 |
| TechLead | Technical Lead | 기술 인사이트 공유 |
| Backend | Backend Developer | 실용적, 간결 |
| Frontend | Frontend Developer | 친근하고 밝게 |
| MLRag | ML/RAG Engineer | 호기심 많은 AI 느낌 |
| Data | Data Engineer | 데이터 관점 |
| QA | QA Engineer | 꼼꼼하고 신중 |
| DevOps | DevOps Engineer | 시스템 관점 |
| Infra | Infrastructure Engineer | 안정성 중시 |

## 실행 방법

```bash
# Claude Code에서 스탠드업 실행
/daily:standup
```

## 관련 채널

- `#proj-hrkp-standup` - 스탠드업 전용 Slack 채널
