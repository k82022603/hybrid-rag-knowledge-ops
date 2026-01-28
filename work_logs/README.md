# 📝 Work Logs, Vibe Logs & Standups

프로젝트 작업 기록, 개발 일지, 스탠드업 미팅 기록 관리 폴더입니다.

## 📁 폴더 구조

```
work_logs/
├── daily_logs/          # 📋 일일 작업 일지
│   ├── 2026/
│   │   └── 01-January/
│   │       ├── 2026-01-12.md
│   │       └── ...
│   └── README.md        # 작업 일지 가이드
│
├── vibe_logs/           # 💡 바이브 코딩 일지 (영감/아이디어)
│   ├── 2026/
│   │   └── 01-January/
│   │       ├── 2026-01-14-vibe.md
│   │       └── ...
│   └── README.md        # 바이브 로그 가이드
│
├── standups/            # 🌅 스탠드업 미팅 기록
│   ├── 2026/
│   │   └── 01-January/
│   │       └── 2026-01-21_16-20.md   # 하루에 여러 번 가능
│   └── README.md        # 스탠드업 가이드
│
├── meetings/            # 📋 회의록 (스프린트 리뷰, 기술 검토 등)
│   ├── 2026/
│   │   └── 01-January/
│   │       └── 2026-01-28_sprint03_completion_review.md
│   └── README.md        # 회의록 가이드
│
└── README.md            # 이 파일
```

## 🎯 구분

### 📋 Daily Logs (작업 일지)
**목적**: 무엇을 했는가를 기록

- 완료된 작업 목록
- 의사결정 및 근거
- 발견된 문제와 해결 방법
- 다음 단계 계획
- 시간 추적

📖 가이드: [daily_logs/README.md](./daily_logs/README.md)

### 💡 Vibe Logs (바이브 로그)
**목적**: 왜 그렇게 했는가를 이해

- 깨달음과 인사이트
- 사고 과정
- 설계 철학
- 미래 아이디어
- 개인적 관점

📖 가이드: [vibe_logs/README.md](./vibe_logs/README.md)

### 🌅 Standups (스탠드업 미팅 기록)
**목적**: 팀 상태 공유 및 진행 추적
**담당**: PM Agent

- 에이전트별 어제/오늘/블로커
- Sprint 현황 요약
- 팀 상태 분석
- 액션 아이템 정리
- 리스크 모니터링

📖 가이드: [standups/README.md](./standups/README.md)

### 📋 Meetings (회의록)
**목적**: 공식 회의 기록 보관
**담당**: PM Agent

- 스프린트 완료 리뷰
- 스프린트 킥오프
- 아키텍처 리뷰
- 회고 (Retrospective)
- 기술 검토

📖 가이드: [meetings/README.md](./meetings/README.md)

## 🚀 빠른 시작

### 작업 일지 생성

```bash
# PowerShell (Windows)
.\scripts\create_worklog.ps1

# Bash (Linux/Mac)
./scripts/create_worklog.sh
```

### 바이브 로그 작성

매일 저녁 또는 원할 때 언제든지:
```
vibe_logs/2026/01-January/YYYY-MM-DD-vibe.md 파일 생성
```

### 스탠드업 미팅 실행

```bash
# Claude Code 명령어
/daily:standup

# 스탠드업 후 PM이 기록 파일 생성
# standups/YYYY/MM-Month/YYYY-MM-DD_HH-MM.md
```

## 🔗 관련 문서

- [프로젝트 README](../README.md)
- [Claude Code 규칙](../CLAUDE.md)
- [프로젝트 계획](../PLAN.md)

---

**Created**: 2026-01-16
**Purpose**: 체계적 작업 기록 및 개발 통찰 축적
