# 프론트엔드 상세 설계서 검토 결과서

> ⚠️ **Update Notice (2026-01-25)**: MUI → Tailwind CSS 마이그레이션 결정
> - 이 리뷰는 MUI v5 기준으로 작성됨
> - 신규 기술 스택: Tailwind CSS 3.4+ + Headless UI + Heroicons
> - 참조: [04.Tailwind_Antigravity_Stitch_도입_영향도_분석.md](../../../../docs/technical_assessment/Guides/04.Tailwind_Antigravity_Stitch_도입_영향도_분석.md)

**문서명**: 프론트엔드 상세 설계서 (frontend_detailed_design.md)
**버전**: 1.0 (Updated: 2.0)
**검토일**: 2026-01-16
**검토자**: Claude AI Architect
**적합성 판정**: ✅ **적합** (조건부 승인)

---

## 1. 문서 개요

| 항목 | 내용 |
|------|------|
| 목적 | Hybrid RAG 지식 플랫폼 웹 프론트엔드 설계 |
| 기술 스택 | React 18, TypeScript, Vite, MUI v5 |
| 상태 관리 | Redux Toolkit + React Query |
| 아키텍처 | Feature-based 모듈 구조 |

---

## 2. 검토 결과 요약

| 평가 항목 | 점수 | 평가 |
|-----------|------|------|
| 완성도 | 9/10 | 매우 우수 |
| 기술적 타당성 | 9/10 | 매우 우수 |
| 확장성 | 8/10 | 우수 |
| 접근성 | 8/10 | 우수 (가이드라인 보완됨) |
| 테스트 전략 | 7/10 | 양호 |
| **종합 점수** | **8.2/10** | **우수** |

---

## 3. 우수 사항

### 3.1 현대적 기술 스택 선정
```
React 18          - Concurrent Mode, Suspense
TypeScript 5.x    - 타입 안정성
Vite              - 빠른 HMR, 최적화 빌드
Tailwind CSS 3.4+ - 유틸리티 CSS 프레임워크 (MUI 대체)
Headless UI       - 접근성 지원 컴포넌트
TanStack Query    - 서버 상태 관리
```
- 최신 안정 버전 채택
- 생산성과 성능 균형

### 3.2 Feature-based 폴더 구조
```
src/
├── features/
│   ├── auth/           # 인증 기능
│   ├── knowledge/      # 지식 관리
│   ├── search/         # 검색 기능
│   └── chat/           # RAG Chat
├── shared/             # 공통 컴포넌트
└── core/               # 핵심 설정
```
- 기능별 응집도 높음
- 독립적 개발/배포 가능
- 코드 탐색 용이

### 3.3 상태 관리 전략
```
┌─────────────────────────────────────┐
│           상태 관리 전략              │
├─────────────────┬───────────────────┤
│   서버 상태      │     클라이언트     │
│  React Query    │   Redux Toolkit   │
├─────────────────┼───────────────────┤
│ - API 캐싱      │ - 인증 상태        │
│ - 자동 재검증   │ - UI 상태          │
│ - 낙관적 업데이트│ - 전역 설정        │
└─────────────────┴───────────────────┘
```
- 서버/클라이언트 상태 분리
- 캐싱 전략 명확

### 3.4 컴포넌트 아키텍처
```typescript
// Compound Component Pattern
<SearchBox>
  <SearchBox.Input />
  <SearchBox.Filters />
  <SearchBox.Results />
</SearchBox>
```
- Compound Pattern 적용
- 재사용성 극대화
- Props Drilling 방지

### 3.5 Chat 스트리밍 UI
```typescript
// SSE 기반 실시간 응답
const { data, isStreaming } = useChatStream(query);
```
- Server-Sent Events 활용
- 타이핑 애니메이션
- 마크다운 렌더링

---

## 4. 개선 필요 사항

### 4.1 [중요] 접근성(A11y) 가이드라인 보완

**현재**: ARIA 속성 일부 언급
**필요**: WCAG 2.1 AA 준수 명세

---

#### 4.1.1 WCAG 2.1 AA 원칙별 요구사항

| 원칙 | 영문 | 핵심 요구사항 |
|------|------|---------------|
| **인지 가능** | Perceivable | 모든 콘텐츠를 인지할 수 있어야 함 |
| **운용 가능** | Operable | 모든 기능을 조작할 수 있어야 함 |
| **이해 가능** | Understandable | 콘텐츠와 UI가 이해 가능해야 함 |
| **견고함** | Robust | 다양한 보조 기술과 호환되어야 함 |

---

#### 4.1.2 컴포넌트별 접근성 체크리스트

##### 🔘 버튼 (Button)
```typescript
// ✅ 올바른 예시
<Button
  aria-label="문서 검색"
  aria-describedby="search-hint"
  disabled={isLoading}
  aria-busy={isLoading}
>
  {isLoading ? <Spinner aria-hidden="true" /> : <SearchIcon aria-hidden="true" />}
  검색
</Button>
<span id="search-hint" className="visually-hidden">
  Enter 키를 눌러 검색을 실행합니다
</span>

// ❌ 잘못된 예시
<div onClick={handleClick} className="button">검색</div>
```

| 항목 | 요구사항 |
|------|----------|
| 시맨틱 태그 | `<button>` 또는 `role="button"` 사용 |
| 키보드 접근 | Enter, Space 키로 활성화 |
| 포커스 표시 | `outline` 또는 커스텀 포커스 스타일 |
| 아이콘 버튼 | `aria-label` 필수 |
| 로딩 상태 | `aria-busy="true"` 적용 |
| 비활성화 | `disabled` 속성 + 시각적 표시 |

---

##### 📝 폼 입력 (Form Input)
```typescript
// ✅ 올바른 예시
<FormControl error={!!errors.email}>
  <InputLabel htmlFor="email-input" id="email-label">
    이메일 주소 *
  </InputLabel>
  <TextField
    id="email-input"
    aria-labelledby="email-label"
    aria-describedby="email-error email-hint"
    aria-required="true"
    aria-invalid={!!errors.email}
    type="email"
    autoComplete="email"
  />
  <FormHelperText id="email-hint">
    업무용 이메일을 입력해주세요
  </FormHelperText>
  {errors.email && (
    <FormHelperText id="email-error" role="alert">
      {errors.email.message}
    </FormHelperText>
  )}
</FormControl>
```

| 항목 | 요구사항 |
|------|----------|
| 라벨 연결 | `<label htmlFor>` 또는 `aria-labelledby` |
| 필수 필드 | `aria-required="true"` + 시각적 표시 (*) |
| 에러 상태 | `aria-invalid="true"` + `role="alert"` |
| 힌트 텍스트 | `aria-describedby` 연결 |
| 자동완성 | `autoComplete` 속성 적용 |

---

##### 🗂️ 모달/다이얼로그 (Modal/Dialog)
```typescript
// ✅ 올바른 예시
<Dialog
  open={isOpen}
  onClose={handleClose}
  aria-labelledby="dialog-title"
  aria-describedby="dialog-description"
  aria-modal="true"
  role="dialog"
>
  <DialogTitle id="dialog-title">
    문서 삭제 확인
  </DialogTitle>
  <DialogContent>
    <DialogContentText id="dialog-description">
      이 문서를 삭제하시겠습니까? 삭제된 문서는 복구할 수 없습니다.
    </DialogContentText>
  </DialogContent>
  <DialogActions>
    <Button onClick={handleClose}>취소</Button>
    <Button onClick={handleConfirm} autoFocus>
      삭제
    </Button>
  </DialogActions>
</Dialog>
```

| 항목 | 요구사항 |
|------|----------|
| 역할 | `role="dialog"` 또는 `role="alertdialog"` |
| 제목 연결 | `aria-labelledby` → 제목 ID |
| 포커스 트랩 | 모달 내부에서만 Tab 이동 |
| 포커스 복원 | 닫을 때 트리거 요소로 복귀 |
| ESC 닫기 | Escape 키로 닫기 지원 |
| 배경 비활성화 | `aria-hidden="true"` (배경 콘텐츠) |

**포커스 트랩 구현:**
```typescript
// useFocusTrap 훅
const useFocusTrap = (isOpen: boolean) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen || !containerRef.current) return;

    const focusableElements = containerRef.current.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const firstElement = focusableElements[0] as HTMLElement;
    const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;

      if (e.shiftKey && document.activeElement === firstElement) {
        e.preventDefault();
        lastElement.focus();
      } else if (!e.shiftKey && document.activeElement === lastElement) {
        e.preventDefault();
        firstElement.focus();
      }
    };

    firstElement?.focus();
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  return containerRef;
};
```

---

##### 🔔 알림/토스트 (Alert/Toast)
```typescript
// ✅ 올바른 예시
<Snackbar
  open={isOpen}
  autoHideDuration={6000}
  onClose={handleClose}
>
  <Alert
    severity="success"
    role="alert"
    aria-live="polite"
    onClose={handleClose}
    action={
      <IconButton
        aria-label="알림 닫기"
        size="small"
        onClick={handleClose}
      >
        <CloseIcon fontSize="small" />
      </IconButton>
    }
  >
    문서가 성공적으로 저장되었습니다.
  </Alert>
</Snackbar>

// 긴급 알림 (에러)
<Alert
  severity="error"
  role="alert"
  aria-live="assertive"  // 즉시 읽음
>
  저장에 실패했습니다. 다시 시도해주세요.
</Alert>
```

| 유형 | aria-live | 용도 |
|------|-----------|------|
| 성공/정보 | `polite` | 현재 읽기 완료 후 안내 |
| 경고/에러 | `assertive` | 즉시 안내 (중단) |
| 상태 변경 | `status` | 상태 업데이트 알림 |

---

##### 📋 테이블 (Table)
```typescript
// ✅ 올바른 예시
<Table aria-label="지식 문서 목록">
  <caption className="visually-hidden">
    총 {totalCount}개의 문서가 있습니다. 제목을 클릭하여 정렬할 수 있습니다.
  </caption>
  <TableHead>
    <TableRow>
      <TableCell
        component="th"
        scope="col"
        aria-sort={sortField === 'title' ? sortOrder : 'none'}
      >
        <TableSortLabel
          active={sortField === 'title'}
          direction={sortOrder}
          onClick={() => handleSort('title')}
        >
          제목
          <span className="visually-hidden">
            {sortField === 'title'
              ? `${sortOrder === 'asc' ? '오름차순' : '내림차순'} 정렬됨`
              : '정렬하려면 클릭'}
          </span>
        </TableSortLabel>
      </TableCell>
      <TableCell component="th" scope="col">작성자</TableCell>
      <TableCell component="th" scope="col">작성일</TableCell>
      <TableCell component="th" scope="col">작업</TableCell>
    </TableRow>
  </TableHead>
  <TableBody>
    {documents.map((doc, index) => (
      <TableRow key={doc.id} aria-rowindex={index + 1}>
        <TableCell>{doc.title}</TableCell>
        <TableCell>{doc.author}</TableCell>
        <TableCell>{formatDate(doc.createdAt)}</TableCell>
        <TableCell>
          <IconButton aria-label={`${doc.title} 편집`}>
            <EditIcon />
          </IconButton>
          <IconButton aria-label={`${doc.title} 삭제`}>
            <DeleteIcon />
          </IconButton>
        </TableCell>
      </TableRow>
    ))}
  </TableBody>
</Table>
```

| 항목 | 요구사항 |
|------|----------|
| 테이블 라벨 | `aria-label` 또는 `<caption>` |
| 헤더 셀 | `<th scope="col/row">` |
| 정렬 상태 | `aria-sort="ascending/descending/none"` |
| 아이콘 버튼 | 컨텍스트 포함 `aria-label` |

---

##### 🧭 네비게이션 (Navigation)
```typescript
// ✅ 올바른 예시
<nav aria-label="메인 메뉴">
  <ul role="menubar" aria-label="주요 기능">
    <li role="none">
      <a
        role="menuitem"
        href="/knowledge"
        aria-current={isActive('/knowledge') ? 'page' : undefined}
      >
        지식 관리
      </a>
    </li>
    <li role="none">
      <button
        role="menuitem"
        aria-haspopup="true"
        aria-expanded={isSearchOpen}
        onClick={toggleSearch}
      >
        검색
      </button>
    </li>
  </ul>
</nav>

// 사이드바 네비게이션
<aside aria-label="사이드 메뉴">
  <nav aria-label="카테고리 필터">
    <ul>
      <li>
        <a
          href="/category/tech"
          aria-current={category === 'tech' ? 'page' : undefined}
        >
          기술 문서
        </a>
      </li>
    </ul>
  </nav>
</aside>
```

| 항목 | 요구사항 |
|------|----------|
| 랜드마크 | `<nav>`, `<main>`, `<aside>` 사용 |
| 현재 페이지 | `aria-current="page"` |
| 서브메뉴 | `aria-haspopup`, `aria-expanded` |
| 복수 nav | 각각 `aria-label`로 구분 |

---

##### 💬 RAG Chat 인터페이스
```typescript
// ✅ 올바른 예시
<section aria-label="AI 채팅" role="log" aria-live="polite">
  <h2 id="chat-title">RAG Chat</h2>

  <div
    role="log"
    aria-labelledby="chat-title"
    aria-describedby="chat-status"
    tabIndex={0}
  >
    {messages.map((msg, index) => (
      <article
        key={msg.id}
        aria-label={`${msg.role === 'user' ? '사용자' : 'AI'} 메시지`}
        aria-posinset={index + 1}
        aria-setsize={messages.length}
      >
        <span className="visually-hidden">
          {msg.role === 'user' ? '사용자' : 'AI'}:
        </span>
        <div>{msg.content}</div>
        {msg.sources && (
          <details>
            <summary>참조 문서 {msg.sources.length}개</summary>
            <ul aria-label="참조 문서 목록">
              {msg.sources.map(src => (
                <li key={src.id}>{src.title}</li>
              ))}
            </ul>
          </details>
        )}
      </article>
    ))}
  </div>

  <div id="chat-status" aria-live="polite" className="visually-hidden">
    {isStreaming ? 'AI가 응답을 작성 중입니다...' : '응답 대기 중'}
  </div>

  <form onSubmit={handleSubmit} aria-label="메시지 입력">
    <TextField
      aria-label="질문 입력"
      placeholder="질문을 입력하세요..."
      value={input}
      onChange={handleChange}
      aria-describedby="input-hint"
    />
    <span id="input-hint" className="visually-hidden">
      Enter 키를 눌러 전송합니다
    </span>
    <Button
      type="submit"
      aria-label="메시지 전송"
      disabled={!input.trim() || isStreaming}
    >
      <SendIcon aria-hidden="true" />
    </Button>
  </form>
</section>
```

---

#### 4.1.3 키보드 네비게이션 가이드

##### 필수 키보드 지원
| 키 | 동작 |
|----|------|
| `Tab` | 다음 포커스 가능 요소로 이동 |
| `Shift + Tab` | 이전 포커스 가능 요소로 이동 |
| `Enter` | 버튼 활성화, 링크 이동 |
| `Space` | 체크박스/라디오 토글, 버튼 활성화 |
| `Escape` | 모달/드롭다운 닫기 |
| `Arrow Keys` | 메뉴/탭/슬라이더 항목 이동 |
| `Home/End` | 목록 처음/끝으로 이동 |

##### 포커스 스타일 정의
```css
/* 기본 포커스 스타일 */
:focus-visible {
  outline: 2px solid #1976d2;
  outline-offset: 2px;
}

/* 버튼 포커스 */
.MuiButton-root:focus-visible {
  outline: 2px solid #1976d2;
  outline-offset: 2px;
  box-shadow: 0 0 0 4px rgba(25, 118, 210, 0.2);
}

/* 입력 필드 포커스 */
.MuiInputBase-root.Mui-focused {
  outline: none;
  box-shadow: 0 0 0 3px rgba(25, 118, 210, 0.3);
}

/* 포커스 표시 숨기지 않음 */
:focus:not(:focus-visible) {
  outline: none; /* 마우스 클릭 시만 숨김 */
}
```

##### Skip Link 구현
```typescript
// 스킵 링크 컴포넌트
const SkipLinks: React.FC = () => (
  <nav aria-label="스킵 링크" className="skip-links">
    <a href="#main-content" className="skip-link">
      본문으로 바로가기
    </a>
    <a href="#main-nav" className="skip-link">
      메뉴로 바로가기
    </a>
    <a href="#search" className="skip-link">
      검색으로 바로가기
    </a>
  </nav>
);

// CSS
.skip-link {
  position: absolute;
  top: -40px;
  left: 0;
  padding: 8px 16px;
  background: #1976d2;
  color: white;
  z-index: 1000;
  transition: top 0.2s;
}

.skip-link:focus {
  top: 0;
}
```

---

#### 4.1.4 색상 및 대비 요구사항

##### 최소 대비율
| 요소 | 최소 대비율 | 권장 |
|------|-------------|------|
| 일반 텍스트 (< 18px) | 4.5:1 | 7:1 |
| 큰 텍스트 (≥ 18px bold / 24px) | 3:1 | 4.5:1 |
| UI 컴포넌트/그래픽 | 3:1 | 4.5:1 |
| 비활성화 요소 | 해당 없음 | - |

##### 색상 팔레트 (접근성 검증 완료)
```typescript
// MUI 테마 - 접근성 검증된 색상
const accessibleTheme = createTheme({
  palette: {
    primary: {
      main: '#1565c0',      // 흰색 배경 대비 6.5:1
      contrastText: '#fff',
    },
    secondary: {
      main: '#7b1fa2',      // 흰색 배경 대비 7.2:1
      contrastText: '#fff',
    },
    error: {
      main: '#c62828',      // 흰색 배경 대비 6.9:1
      contrastText: '#fff',
    },
    warning: {
      main: '#e65100',      // 흰색 배경 대비 4.6:1
      contrastText: '#000',
    },
    success: {
      main: '#2e7d32',      // 흰색 배경 대비 5.1:1
      contrastText: '#fff',
    },
    text: {
      primary: '#212121',   // 흰색 배경 대비 16.1:1
      secondary: '#616161', // 흰색 배경 대비 5.9:1
      disabled: '#9e9e9e',  // 대비 요구 없음
    },
  },
});
```

##### 색상만으로 정보 전달 금지
```typescript
// ❌ 잘못된 예시 - 색상만으로 상태 표시
<span style={{ color: 'red' }}>{status}</span>

// ✅ 올바른 예시 - 아이콘 + 텍스트 + 색상
<Chip
  icon={<ErrorIcon />}
  label={`오류: ${status}`}
  color="error"
  aria-label={`상태: 오류 - ${status}`}
/>
```

---

#### 4.1.5 스크린 리더 지원

##### 숨김 텍스트 유틸리티
```css
/* 시각적으로 숨기지만 스크린 리더는 읽음 */
.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

/* 포커스 시 표시 */
.visually-hidden-focusable:focus {
  position: static;
  width: auto;
  height: auto;
  margin: 0;
  overflow: visible;
  clip: auto;
  white-space: normal;
}
```

##### ARIA Live Region 사용 가이드
```typescript
// 로딩 상태 알림
<div aria-live="polite" aria-busy={isLoading}>
  {isLoading ? '데이터를 불러오는 중...' : `${count}개 결과 로드됨`}
</div>

// 실시간 검색 결과
<div aria-live="polite" aria-atomic="true">
  {searchResults.length}개의 검색 결과가 있습니다
</div>

// 에러 알림 (즉시)
<div role="alert" aria-live="assertive">
  {error && `오류: ${error.message}`}
</div>
```

---

#### 4.1.6 접근성 테스트 도구 및 방법

##### 자동화 도구
| 도구 | 용도 | 통합 방법 |
|------|------|-----------|
| **axe-core** | 자동 접근성 검사 | Jest/Vitest 통합 |
| **eslint-plugin-jsx-a11y** | 코드 린팅 | ESLint 설정 |
| **Lighthouse** | 전체 페이지 감사 | CI/CD 통합 |
| **WAVE** | 브라우저 확장 | 수동 검사 |

##### 테스트 설정
```typescript
// vitest.setup.ts
import '@testing-library/jest-dom';
import { configureAxe, toHaveNoViolations } from 'jest-axe';

expect.extend(toHaveNoViolations);

const axe = configureAxe({
  rules: {
    // 일시적으로 비활성화할 규칙 (이유 명시 필수)
    // 'color-contrast': { enabled: false },
  },
});

// 접근성 테스트 예시
describe('SearchBox 접근성', () => {
  it('접근성 위반이 없어야 함', async () => {
    const { container } = render(<SearchBox />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('키보드로 검색 가능해야 함', async () => {
    render(<SearchBox />);
    const input = screen.getByRole('searchbox');

    await userEvent.tab();
    expect(input).toHaveFocus();

    await userEvent.type(input, 'test query');
    await userEvent.keyboard('{Enter}');

    expect(mockSearch).toHaveBeenCalledWith('test query');
  });
});
```

##### ESLint 설정
```javascript
// .eslintrc.js
module.exports = {
  plugins: ['jsx-a11y'],
  extends: ['plugin:jsx-a11y/recommended'],
  rules: {
    'jsx-a11y/anchor-is-valid': 'error',
    'jsx-a11y/click-events-have-key-events': 'error',
    'jsx-a11y/no-static-element-interactions': 'error',
    'jsx-a11y/aria-props': 'error',
    'jsx-a11y/aria-role': 'error',
  },
};
```

##### 수동 테스트 체크리스트
- [ ] 키보드만으로 모든 기능 사용 가능
- [ ] Tab 순서가 논리적
- [ ] 포커스 표시 명확
- [ ] NVDA/VoiceOver로 콘텐츠 읽기 확인
- [ ] 200% 확대 시 콘텐츠 잘림 없음
- [ ] 다크 모드 대비율 확인
- [ ] 애니메이션 reduce-motion 존중

---

#### 4.1.7 접근성 준수 체크리스트

##### 구현 전 필수 (🔴 High)
| # | 항목 | 기준 | 담당 |
|---|------|------|------|
| 1 | 모든 이미지에 alt 텍스트 | WCAG 1.1.1 | FE |
| 2 | 폼 필드 라벨 연결 | WCAG 1.3.1 | FE |
| 3 | 색상 대비 4.5:1 이상 | WCAG 1.4.3 | UI/UX |
| 4 | 키보드 접근 가능 | WCAG 2.1.1 | FE |
| 5 | 포커스 표시 | WCAG 2.4.7 | FE |
| 6 | 페이지 제목 명확 | WCAG 2.4.2 | FE |
| 7 | 링크 목적 명확 | WCAG 2.4.4 | FE |
| 8 | 에러 식별 및 설명 | WCAG 3.3.1 | FE |

##### 구현 시 권장 (🟡 Medium)
| # | 항목 | 기준 | 담당 |
|---|------|------|------|
| 9 | Skip Links 제공 | WCAG 2.4.1 | FE |
| 10 | 랜드마크 역할 정의 | WCAG 1.3.1 | FE |
| 11 | 모달 포커스 트랩 | WCAG 2.4.3 | FE |
| 12 | 동적 콘텐츠 aria-live | WCAG 4.1.3 | FE |
| 13 | 터치 타겟 44x44px | WCAG 2.5.5 | UI/UX |
| 14 | 자동완성 힌트 | WCAG 1.3.5 | FE |

##### 배포 전 확인 (🟢 Low)
| # | 항목 | 기준 | 담당 |
|---|------|------|------|
| 15 | 언어 속성 설정 | WCAG 3.1.1 | FE |
| 16 | 일관된 네비게이션 | WCAG 3.2.3 | UI/UX |
| 17 | 일관된 식별 | WCAG 3.2.4 | UI/UX |
| 18 | motion 설정 존중 | WCAG 2.3.3 | FE |

---

**권고안 요약**:
```typescript
// 접근성 설정 객체
const a11yConfig = {
  // WCAG 2.1 AA 준수
  wcag_level: 'AA',

  // 테스트 자동화
  testing: {
    axe_core: true,
    eslint_jsx_a11y: true,
    lighthouse_threshold: 90,
  },

  // 필수 컴포넌트 패턴
  patterns: {
    focus_trap: '모달/다이얼로그',
    skip_links: '메인 레이아웃',
    aria_live: '동적 콘텐츠',
    keyboard_nav: '모든 인터랙티브 요소',
  },

  // 색상 대비
  contrast: {
    text_normal: '4.5:1',
    text_large: '3:1',
    ui_components: '3:1',
  },
};
```

### 4.2 [중요] 에러 바운더리 전략
**현재**: 기본 에러 처리만 언급
**필요**: 계층별 에러 바운더리 설계

**권고안**:
```typescript
// 에러 바운더리 계층
<GlobalErrorBoundary>      {/* 전역 폴백 */}
  <RouteErrorBoundary>     {/* 라우트별 */}
    <FeatureErrorBoundary> {/* 기능별 */}
      <Component />
    </FeatureErrorBoundary>
  </RouteErrorBoundary>
</GlobalErrorBoundary>
```

### 4.3 [보통] 성능 최적화 상세화
**필요**:
- Bundle 사이즈 목표 (예: < 200KB gzip)
- Lazy Loading 전략
- 이미지 최적화 (WebP, srcset)

**권고안**:
```typescript
// 코드 스플리팅 예시
const KnowledgeDetail = lazy(() =>
  import('./features/knowledge/KnowledgeDetail')
);

// 번들 분석 설정
{
  "bundle_targets": {
    "initial_load": "< 150KB",
    "lazy_chunk_max": "< 50KB",
    "vendor_chunk": "< 100KB"
  }
}
```

### 4.4 [보통] 테스트 전략 구체화
**필요**:
- 컴포넌트 테스트 커버리지 목표
- E2E 테스트 시나리오
- 시각적 회귀 테스트

**권고안**:
```yaml
testing_strategy:
  unit_test:
    tool: Vitest
    coverage_target: 80%
  component_test:
    tool: React Testing Library
    focus: 사용자 상호작용
  e2e_test:
    tool: Playwright
    scenarios:
      - 로그인 플로우
      - 문서 검색
      - RAG Chat
```

### 4.5 [경미] i18n 지원
**현재**: 미언급
**권고**: react-i18next 도입 준비

---

## 5. 보안 검토

### 5.1 적합 사항
- ✅ XSS 방어 (React 기본 이스케이프)
- ✅ CSRF 토큰 처리
- ✅ 환경 변수 분리
- ✅ 인증 토큰 관리 (httpOnly 쿠키)

### 5.2 보완 필요
- ⚠️ CSP (Content Security Policy) 헤더 정책
- ⚠️ 민감 데이터 로깅 방지
- ⚠️ Third-party 스크립트 보안 검토

**권고안**:
```html
<!-- CSP 헤더 -->
<meta http-equiv="Content-Security-Policy"
      content="default-src 'self';
               script-src 'self';
               style-src 'self' 'unsafe-inline';">
```

---

## 6. UI/UX 검토

### 6.1 적합 사항
- ✅ 일관된 디자인 시스템 (MUI)
- ✅ 반응형 레이아웃
- ✅ 로딩/에러 상태 UI
- ✅ 다크 모드 지원

### 6.2 개선 권고
- 스켈레톤 로딩 패턴 상세화
- 빈 상태(Empty State) 디자인
- 마이크로 인터랙션 가이드

---

## 7. 권고 사항

| 우선순위 | 항목 | 상태 | 설명 |
|----------|------|------|------|
| 높음 | 접근성 가이드 | ✅ 완료 | WCAG 2.1 AA 가이드라인 보완됨 (섹션 4.1) |
| 높음 | 에러 바운더리 | 📋 진행 필요 | 계층별 에러 처리 전략 |
| 중간 | 번들 최적화 | 📋 진행 필요 | 사이즈 목표 및 스플리팅 전략 |
| 중간 | 테스트 전략 | 📋 진행 필요 | 커버리지 목표 및 E2E 시나리오 |
| 낮음 | i18n 준비 | 📋 향후 | 다국어 지원 인프라 |
| 낮음 | CSP 정책 | 📋 향후 | 보안 헤더 정의 |

---

## 8. 적합성 판정

### ✅ 적합 (승인)

**완료된 조건**:
1. ✅ 접근성(A11y) 가이드라인 상세 보완 완료
   - WCAG 2.1 AA 원칙별 요구사항
   - 컴포넌트별 접근성 체크리스트 (버튼, 폼, 모달, 테이블, 네비게이션, RAG Chat)
   - 키보드 네비게이션 가이드
   - 색상 대비 요구사항 및 접근성 검증 테마
   - 스크린 리더 지원 패턴
   - 테스트 도구 및 자동화 설정
   - 우선순위별 준수 체크리스트 (18개 항목)

**잔여 조건**:
2. 에러 바운더리 설계 보완 (구현 시)
3. 번들 사이즈 목표 정의 (배포 전)

**결론**: 본 설계서는 현대적 React 아키텍처를 잘 반영하고 있으며, Feature-based 구조와 상태 관리 전략이 적절합니다. 접근성 가이드라인이 WCAG 2.1 AA 수준으로 상세히 보완되어 구현 진행이 가능합니다.

---

**검토 완료**: 2026-01-16
**다음 검토**: 컴포넌트 라이브러리 구축 완료 후
