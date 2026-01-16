# Work Logs

프로젝트 작업 일지를 관리하는 폴더입니다.

## 📁 폴더 구조

```
work_logs/
├── 2026/
│   ├── 01-January/
│   │   ├── 2026-01-12.md
│   │   ├── 2026-01-13.md
│   │   └── weekly-summary-W02.md
│   └── 02-February/
└── README.md
```

## 🚀 빠른 시작

### PowerShell (Windows)
```powershell
# 오늘 날짜 작업 일지 생성
.\scripts\create_worklog.ps1

# 특정 날짜 작업 일지 생성
.\scripts\create_worklog.ps1 -Date "2026-01-15"
```

### Bash (Linux/Mac)
```bash
# 오늘 날짜 작업 일지 생성
./scripts/create_worklog.sh

# 실행 권한 부여 (최초 1회)
chmod +x ./scripts/create_worklog.sh
```

## 📝 작업 일지 템플릿 섹션 설명

### 📌 Today's Focus
- 오늘의 핵심 작업 목표 (체크리스트)

### ✅ Completed Tasks
- 완료한 작업 상세 기록
- 각 작업의 주요 변경 사항

### 💡 Key Decisions
- 중요한 기술적/비즈니스 결정사항
- 결정 이유 및 근거

### 🐛 Issues & Blockers
- 발견된 문제점
- 해결이 필요한 블로커

### 📚 Learnings
- 배운 점, 새로 알게 된 사실
- 기술적 인사이트

### 📅 Next Steps
- 다음 작업 계획

### 📊 Time Spent
- 작업별 소요 시간 (선택적)

### 🔗 References
- 관련 문서, PR, Issue 링크

## 📋 주간 요약 (선택적)

매주 금요일에 `weekly-summary-WXX.md` 파일 생성 권장:

```markdown
# Weekly Summary - 2026 Week 02

## 🎯 Week Goals
- 목표 1
- 목표 2

## ✅ Achievements
- 완료한 주요 작업들

## 📊 Metrics
- 문서 업데이트: 3개
- 코드 리뷰: 5개
- 버그 수정: 2개

## 🔄 Next Week
- 다음 주 계획
```

## 🤖 자동화 팁

### Git Commit Hook (선택적)
작업 일지를 Git commit 시 자동 생성하려면:

```bash
# .git/hooks/post-commit
#!/bin/bash
./scripts/create_worklog.sh
```

### VS Code Task (선택적)
`.vscode/tasks.json`에 추가:

```json
{
  "label": "Create Work Log",
  "type": "shell",
  "command": "./scripts/create_worklog.ps1",
  "problemMatcher": []
}
```

단축키: `Ctrl+Shift+B` → "Create Work Log" 선택

## 📂 백업

작업 일지는 Git에 커밋하여 버전 관리하는 것을 권장합니다:

```bash
git add work_logs/daily_logs/
git commit -m "[DOCS] Add work log for $(date +%Y-%m-%d)"
```

## 🔍 검색

모든 작업 일지에서 키워드 검색:

```bash
# PowerShell
Get-ChildItem -Path work_logs\daily_logs -Recurse -Filter *.md | Select-String "RRF"

# Bash
grep -r "RRF" work_logs/daily_logs/
```
