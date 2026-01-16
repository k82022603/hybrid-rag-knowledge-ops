# Daily Log - 작업일지 작성/업데이트

오늘의 작업일지를 작성하거나 업데이트합니다.
**업데이트 모드**: 기존 파일이 있으면 추가 내용을 반영합니다.

## 파일 경로
```
work_logs/daily_logs/{{YYYY}}/{{MM}}-{{Month}}/{{YYYY-MM-DD}}.md
```

## 실행 로직

### 1. 파일 존재 여부 확인
해당 날짜의 작업일지가 이미 존재하는지 확인

### 2-A. 파일이 존재하는 경우 (업데이트 모드)

1. **기존 파일 읽기**
2. **추가 작업 파악**:
   - `git log --oneline` 에서 기존 작업일지 이후 커밋 확인
   - 현재 대화에서 완료된 작업 추출
3. **업데이트 적용**:
   - Today's Focus: 새 완료 항목 추가
   - Completed Tasks: 새 작업 섹션 추가 (번호 이어서)
   - Key Decisions: 새 의사결정 추가
   - Today's Achievements: 수치 업데이트
   - Next Steps: 갱신

### 2-B. 파일이 존재하지 않는 경우 (생성 모드)

이전 작업일지를 참고하여 새로 생성

## 작업일지 템플릿

```markdown
# Work Log - YYYY-MM-DD

## 📌 Today's Focus
- [x] 완료된 주요 작업 1
- [x] 완료된 주요 작업 2

## ✅ Completed Tasks

### 1. 작업명
**내용**:
- 상세 내용
- 결과 및 영향

### 2. 작업명
**내용**:
- 상세 내용

## 💡 Key Decisions
1. **결정 사항**: 선택한 내용
   - 근거: 이유
   - 효과: 기대 효과

## 🐛 Issues & Blockers
- 발생한 문제 (없으면 "없음")

## 📚 Learnings
1. 오늘 배운 것
2. 새로운 인사이트

## 📊 Today's Achievements

| 카테고리 | 수량 | 상세 |
|:--------:|:----:|------|
| 신규 문서 | N개 | 목록 |
| 업데이트 | N개 | 목록 |
| 코드 라인 | +N | insertions |

## 📅 Next Steps

### 🔴 P0 - 최우선 (내일)
- [ ] 작업 1

### 🟡 P1 - 중요
- [ ] 작업 2

### 🟢 P2 - 일반
- [ ] 작업 3

## 📊 Time Spent
- 작업 1: 약 N시간
- 작업 2: 약 N시간
- 총: 약 N시간

## 🔗 References
- 관련 커밋: `hash`
- 관련 문서: [링크](path)

---
**작성일**: YYYY-MM-DD
```

### 3. 커밋 (선택)
```bash
git add work_logs/daily_logs/
git commit -m "[DOCS] YYYY-MM-DD 작업일지 작성/업데이트"
```

---

**사용법**: `/daily-log`
**모드**: 업데이트 (기존 파일 보존 + 추가 내용 반영)
**결과물**: `work_logs/daily_logs/YYYY/MM-Month/YYYY-MM-DD.md`
