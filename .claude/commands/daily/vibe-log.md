---
description: 바이브 코딩 일지 작성/업데이트 (인사이트 및 아이디어 기록)
allowed-tools: Bash(git:*), Bash(ls:*), Read, Write, Edit, Glob
---

# Vibe Log - 바이브 코딩 일지 작성/업데이트

오늘의 바이브 코딩 일지를 작성하거나 업데이트합니다.
**업데이트 모드**: 기존 파일이 있으면 새로운 인사이트를 추가합니다.

## 파일 경로
```
work_logs/vibe_logs/{{YYYY}}/{{MM}}-{{Month}}/{{YYYY-MM-DD}}-vibe.md
```

## 작성 톤
- 철학적, 성찰적
- 기술적 내용보다 **사고 과정과 인사이트** 중심
- 명언/인용구 활용
- 자문자답 형식 포함

## 실행 로직

### 1. 파일 존재 여부 확인
해당 날짜의 바이브 일지가 이미 존재하는지 확인

### 2-A. 파일이 존재하는 경우 (업데이트 모드)

1. **기존 파일 읽기**
2. **새로운 인사이트 파악**:
   - 추가 작업에서 얻은 깨달음
   - 새로운 아이디어나 영감
   - 변화된 관점이나 철학
3. **업데이트 적용**:
   - Inspiration & Insights: 새 섹션 번호 이어서 추가
   - Future Ideas: 새 아이디어 추가
   - Still Wondering: 새 고민 추가
   - Conversation with Myself: 새 Q&A 추가
   - Statistics: 수치 업데이트

### 2-B. 파일이 존재하지 않는 경우 (생성 모드)

이전 바이브 일지를 참고하여 새로 생성

## 바이브 일지 템플릿

```markdown
# Vibe Coding Log - YYYY-MM-DD

## 🌀 Today's Vibe

> "인용구나 오늘의 깨달음을 한 문장으로"

오늘의 핵심 감상을 2-3문장으로 서술

---

## 💡 Inspiration & Insights

### 1. "인사이트 제목"

**발견**:
발견한 내용이나 기법 설명

**통찰**:
- 핵심 인사이트 1
- 핵심 인사이트 2
- 이것이 왜 중요한지

---

### 2. "두 번째 인사이트"

**경험**:
경험한 내용

**배운 점**:
- 배운 것 1
- 배운 것 2

---

## 🔄 Thinking Process

### 의사결정 과정

```
1단계: 문제 인식
  → 무엇이 문제였는지

2단계: 해결책 탐색
  → 어떤 옵션들을 고려했는지

3단계: 선택과 근거
  → 왜 그것을 선택했는지

4단계: 결과
  → 어떤 결과가 나왔는지
```

---

## 🎨 Architecture Philosophy Evolved

### Before
```
이전에 생각하던 방식
```

### After
```
오늘 바뀐 생각/접근법
```

**깨달음**:
- 왜 바뀌었는지
- 무엇을 배웠는지

---

## 🚀 Future Ideas

### 1. 아이디어 제목
```
간단한 코드나 pseudo-code
또는 아이디어 스케치
```

---

## 🤔 Still Wondering

### 1. "아직 답을 못 찾은 질문"
```
고민 중인 내용
현재 생각하고 있는 것들
```

---

## 💬 Conversation with Myself

**Q: 스스로에게 던지는 질문?**

A: 자문자답 형식의 답변

---

**Q: 또 다른 질문?**

A: 답변

---

## 📊 Statistics

| 항목 | 수량 |
|------|------|
| 신규 문서 | N개 |
| 업데이트 문서 | N개 |
| 총 라인 추가 | +N |
| 핵심 인사이트 | N개 |

---

## 🎯 Tomorrow's Focus
- [ ] 내일 집중할 것 1
- [ ] 내일 집중할 것 2

---

## 🌟 Key Takeaway

> **"오늘의 핵심 교훈을 한 문장으로"**

마무리 문장 (2-3줄)

---

**Created**: YYYY-MM-DD HH:MM KST
**Mood**: 이모지 + 감정 상태
```

### 3. 커밋 (선택)
```bash
git add work_logs/vibe_logs/
git commit -m "[DOCS] YYYY-MM-DD 바이브 코딩 일지 작성/업데이트"
```

---

**사용법**: `/project:daily:vibe-log`
**모드**: 업데이트 (기존 파일 보존 + 새 인사이트 추가)
**결과물**: `work_logs/vibe_logs/YYYY/MM-Month/YYYY-MM-DD-vibe.md`
