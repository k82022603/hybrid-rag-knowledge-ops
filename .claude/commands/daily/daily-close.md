---
description: 하루 마무리 자동화 (작업일지 + 바이브로그 + 문서 현행화 + 커밋/푸시)
allowed-tools: Bash(git:*), Bash(ls:*), Read, Write, Edit, Glob
---

# Daily Close - 하루 마무리 자동화

하루 일과를 마무리하는 전체 워크플로우를 실행합니다.
**업데이트 모드**: 기존 파일이 있으면 추가 내용을 반영하여 업데이트합니다.

## 실행 순서

### 1. 미커밋 변경사항 확인 및 커밋
```bash
git status
```
- 커밋되지 않은 변경사항이 있으면 적절한 커밋 메시지로 커밋
- 이미 모두 커밋되어 있으면 다음 단계로

### 2. 작업일지 작성/업데이트
**파일 경로**: `work_logs/daily_logs/{{YYYY}}/{{MM}}-{{Month}}/{{YYYY-MM-DD}}.md`

**처리 로직**:
1. 해당 날짜 파일이 이미 존재하는지 확인
2. **존재하면**: 기존 파일을 읽고, 이후 추가된 작업 내용을 파악하여 업데이트
3. **존재하지 않으면**: 새로 생성

**추가 작업 파악 방법**:
- `git log --oneline --since="기존 파일 수정 시간"` 으로 이후 커밋 확인
- 현재 대화에서 완료된 작업 추출

**업데이트 시 주의사항**:
- 기존 Today's Focus에 새 항목 추가
- 기존 Completed Tasks 섹션에 새 작업 추가
- Today's Achievements 수치 업데이트
- Next Steps 갱신

### 3. 바이브 코딩 일지 작성/업데이트
**파일 경로**: `work_logs/vibe_logs/{{YYYY}}/{{MM}}-{{Month}}/{{YYYY-MM-DD}}-vibe.md`

**처리 로직**:
1. 해당 날짜 파일이 이미 존재하는지 확인
2. **존재하면**: 기존 파일을 읽고, 새로운 인사이트/아이디어 추가
3. **존재하지 않으면**: 새로 생성

**업데이트 시 추가할 내용**:
- 새로운 Inspiration & Insights
- 추가된 사고 과정
- 새로운 아이디어
- Statistics 업데이트

### 4. 프로젝트 문서 현행화
다음 파일들을 오늘 작업 내용으로 업데이트:

- **README.md**: 버전, 날짜, 설계 상태, Next Steps, 완료 항목
- **CLAUDE.md**: 버전, 날짜, 참고 문서 링크
- **PLAN.md**: Phase 진행률, Session Notes, 문서 구조, Key Decisions

### 5. 최종 커밋 및 푸시
```bash
git add .
git commit -m "[DOCS] 일일 마무리 - 작업일지, 바이브로그, 문서 현행화 (업데이트)"
git push origin main
```

### 6. 완료 보고
마무리 내용을 간단히 요약:
- 업데이트된 파일 목록
- 추가된 주요 내용
- 최종 커밋 해시

---

**사용법**: `/project:daily:daily-close`
**모드**: 업데이트 (기존 파일 보존 + 추가 내용 반영)
