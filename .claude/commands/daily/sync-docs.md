# Sync Docs - 프로젝트 문서 현행화

README.md, CLAUDE.md, PLAN.md를 오늘 작업 내용으로 업데이트합니다.

## 대상 파일

| 파일 | 업데이트 내용 |
|------|--------------|
| `README.md` | 버전, 날짜, 설계 상태, Next Steps, 완료 항목 |
| `CLAUDE.md` | 버전, 날짜, 참고 문서 링크 |
| `PLAN.md` | Phase 진행률, Session Notes, 문서 구조, Key Decisions |

## 실행 로직

### 1. 오늘 작업 내용 파악

**소스**:
- `git log --oneline --since="today 00:00"` - 오늘 커밋 내역
- 현재 대화에서 완료된 작업
- 오늘 생성/수정된 파일 목록

### 2. README.md 업데이트

**업데이트 항목**:
```markdown
- 프로젝트 버전: X.Y → X.Z (마이너 버전 증가)
- 마지막 업데이트: YYYY-MM-DD
- 설계서 상태: 현재 진행 상황 반영
- 주요 기능: 새 기능 추가 시 목록에 추가
- Next Steps: 완료된 항목 제거, 새 작업 추가
- 완료된 설계 섹션: 오늘 완료 항목 추가
- 하단 footer: 최신 상태 반영
```

### 3. CLAUDE.md 업데이트

**업데이트 항목**:
```markdown
- Version: X.Y → X.Z
- Updated: YYYY-MM-DD
- 참고 문서: 새 문서 링크 추가
```

### 4. PLAN.md 업데이트

**업데이트 항목**:
```markdown
- Last Updated: YYYY-MM-DD
- Current Phase: 진행률 업데이트
- Current Status: 프로그레스 바 업데이트

Phase 2 섹션:
- 완료된 작업 체크 표시
- 새 완료 항목 추가

현재 작업 큐:
- 완료된 P0 작업 목록 업데이트
- 새 작업 큐 재정렬

문서 구조:
- 새 파일/폴더 추가

Key Decisions:
- 새 의사결정 추가 (있는 경우)

Session Notes:
- 오늘 날짜 섹션 추가/업데이트
  - 주요 작업 내용
  - 변경 사항
  - 커밋 정보
```

### 5. 버전 관리 규칙

```
버전 증가 기준:
- 문서 현행화만: patch (X.Y.Z → X.Y.Z+1) - 생략 가능
- 새 기능/설계 추가: minor (X.Y → X.Y+1)
- 대규모 변경: major (X → X+1)

예시:
- README v3.0 → v3.1 (새 기능 추가)
- CLAUDE v2.4 → v2.5 (참고 문서 추가)
- PLAN Phase 2.9 → 2.9 (세션 노트만 추가 시 버전 유지)
```

### 6. 커밋 (선택)
```bash
git add README.md CLAUDE.md PLAN.md
git commit -m "[DOCS] 프로젝트 메인 문서 현행화"
```

---

**사용법**: `/sync-docs`
**결과물**: README.md, CLAUDE.md, PLAN.md 업데이트
