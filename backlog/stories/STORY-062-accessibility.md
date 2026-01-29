# STORY-062: 접근성 (WCAG 2.1 AA) 보완

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-52 |
| **Epic** | EPIC-003 |
| **Status** | Done |
| **Priority** | Medium |
| **Story Points** | 2 |
| **Assignee** | Frontend |
| **Sprint** | 4 |

---

## User Story

**As a** 키보드 또는 스크린 리더 사용자,
**I want** 모든 UI 요소가 WCAG 2.1 AA 기준을 충족하여 접근 가능,
**So that** 마우스 없이도 키보드만으로 전체 기능을 사용하고 스크린 리더로 콘텐츠를 이해할 수 있음.

---

## Acceptance Criteria

- [ ] **Given** 에러 dismiss 버튼, **When** 스크린 리더가 읽음, **Then** aria-label="에러 닫기"가 명확하게 안내
- [ ] **Given** SourceCitation 출처 목록, **When** Tab 키로 이동, **Then** 각 출처 항목에 포커스가 이동하고 Enter로 상세 확인 가능
- [ ] **Given** 페이지네이션 컴포넌트, **When** 키보드로 조작, **Then** 현재 페이지 aria-current="page" 표시 및 방향키/Enter로 페이지 이동
- [ ] **Given** 모든 인터랙티브 요소, **When** Tab 키로 순회, **Then** 논리적 순서로 포커스 이동 (skip-to-content 포함)
- [ ] **Given** 포커스가 있는 요소, **When** 시각적으로 확인, **Then** 명확한 포커스 인디케이터(outline)가 보임 (최소 2px)
- [ ] **Given** 색상 대비, **When** WCAG 대비 검사, **Then** 텍스트 대비율 4.5:1 이상 (AA 기준)
- [ ] **Given** axe-core 자동 접근성 검사, **When** 전체 페이지 스캔, **Then** 심각(serious) 이상 위반 0건

---

## Tasks

- [ ] 에러 dismiss 버튼에 aria-label="에러 닫기" 추가
- [ ] SourceCitation 키보드 네비게이션 구현 (Tab/Enter/Escape)
- [ ] 페이지네이션 접근성 개선 (aria-current, aria-label)
- [ ] 전체 페이지 탭 순서(tabIndex) 검토 및 수정
- [ ] skip-to-content 링크 추가
- [ ] 포커스 인디케이터 스타일 통일 (Tailwind CSS focus:ring)
- [ ] 색상 대비 검토 및 수정 (텍스트, 버튼, 링크)
- [ ] 이미지/아이콘에 alt text 또는 aria-hidden 적용
- [ ] axe-core 또는 jest-axe 자동 접근성 테스트 추가
- [ ] 키보드 전용 사용자 테스트 시나리오 수행

---

## 기술 노트

### 문제점 (Sprint 03 리뷰에서 도출)

Sprint 03 Frontend 접근성 감사에서 7건의 WCAG 2.1 AA 위반 항목이 식별됨:

1. **에러 dismiss aria-label 부재** - 스크린 리더가 버튼 목적을 알 수 없음
2. **SourceCitation 키보드 네비게이션 불가** - 마우스로만 접근 가능
3. **페이지네이션 접근성 부족** - 현재 페이지 표시 없음, 키보드 조작 불가
4. **포커스 인디케이터 불명확** - 일부 요소에서 포커스 표시 안 됨
5. **탭 순서 비논리적** - 시각적 순서와 탭 순서 불일치
6. **색상 대비 미달** - 일부 텍스트의 대비율 3:1 미만
7. **alt text 누락** - 아이콘에 대체 텍스트 없음

### 수정 예시

```typescript
// Before (접근성 미흡)
<button onClick={onDismiss}>X</button>

// After (WCAG 2.1 AA 충족)
<button
  onClick={onDismiss}
  aria-label="에러 닫기"
  className="focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
>
  <span aria-hidden="true">X</span>
</button>
```

```typescript
// SourceCitation 키보드 네비게이션
<ul role="list" aria-label="참고 자료 목록">
  {sources.map((source, index) => (
    <li key={source.id}>
      <a
        href={source.url}
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter') handleSourceClick(source);
          if (e.key === 'Escape') handleClose();
        }}
        aria-label={`출처 ${index + 1}: ${source.title}`}
        className="focus:ring-2 focus:ring-primary-500 rounded"
      >
        {source.title}
      </a>
    </li>
  ))}
</ul>
```

```typescript
// 페이지네이션 접근성
<nav aria-label="페이지 네비게이션">
  <ul className="flex gap-2">
    {pages.map(page => (
      <li key={page}>
        <button
          aria-current={currentPage === page ? 'page' : undefined}
          aria-label={`${page}페이지로 이동`}
          className="focus:ring-2 focus:ring-primary-500"
        >
          {page}
        </button>
      </li>
    ))}
  </ul>
</nav>
```

### 접근성 체크리스트 (WCAG 2.1 AA)

```
[Perceivable]
  [ ] 1.1.1 Non-text Content - alt text
  [ ] 1.4.3 Contrast (Minimum) - 4.5:1
  [ ] 1.4.11 Non-text Contrast - 3:1 (UI 요소)

[Operable]
  [ ] 2.1.1 Keyboard - 모든 기능 키보드 접근
  [ ] 2.4.3 Focus Order - 논리적 탭 순서
  [ ] 2.4.7 Focus Visible - 포커스 인디케이터

[Understandable]
  [ ] 3.3.2 Labels or Instructions - 명확한 레이블

[Robust]
  [ ] 4.1.2 Name, Role, Value - ARIA 속성
```

### 영향 범위

- `frontend/src/features/search/components/` - 접근성 속성 추가
- `frontend/src/shared/components/` - 공통 컴포넌트 접근성 개선
- `frontend/src/styles/` - 포커스 인디케이터 스타일
- `frontend/src/tests/accessibility/` - 접근성 테스트

---

## 테스트 계획

- [ ] Automated Test: jest-axe로 컴포넌트별 접근성 자동 검사
- [ ] Manual Test: 키보드 전용 전체 기능 사용 시나리오
- [ ] Manual Test: 스크린 리더(NVDA 또는 VoiceOver)로 전체 탐색
- [ ] Color Test: 색상 대비 검사 도구(Contrast Checker)로 확인
- [ ] Regression Test: 접근성 테스트를 CI에 추가하여 리그레션 방지

---

## 참고 자료

- Sprint 03 완료 리뷰에서 도출 - 접근성 감사 7건 위반
- [WCAG 2.1 Guidelines](https://www.w3.org/TR/WCAG21/)
- [axe-core](https://github.com/dequelabs/axe-core)
- [jest-axe](https://github.com/nickcolley/jest-axe)
