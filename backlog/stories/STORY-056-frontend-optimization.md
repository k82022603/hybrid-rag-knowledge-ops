# STORY-056: Frontend ErrorBoundary + 성능 최적화

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-46 |
| **Epic** | EPIC-003 |
| **Status** | To Do |
| **Priority** | High |
| **Story Points** | 3 |
| **Assignee** | Frontend |
| **Sprint** | 4 |

---

## User Story

**As a** 지식 검색 사용자,
**I want** 렌더링 에러 시 전체 앱이 크래시되지 않고 fallback UI가 표시되며, 스트리밍 시 부드러운 성능을 경험,
**So that** 예외 상황에서도 안정적인 사용 경험을 유지하고 토큰 스트리밍 시 버벅임 없이 응답을 읽을 수 있음.

---

## Acceptance Criteria

- [ ] **Given** 컴포넌트 렌더링 중 JavaScript 에러 발생, **When** ErrorBoundary에 의해 캐치됨, **Then** fallback UI("문제가 발생했습니다. 새로고침해주세요.") 표시
- [ ] **Given** ErrorBoundary 동작 후, **When** "다시 시도" 버튼 클릭, **Then** 해당 섹션이 리셋되어 정상 렌더링 시도
- [ ] **Given** MessageBubble 컴포넌트에 React.memo 적용, **When** 다른 메시지가 추가됨, **Then** 변경되지 않은 기존 MessageBubble은 리렌더링되지 않음
- [ ] **Given** SSE 토큰 스트리밍 중, **When** 초당 50+ 토큰 수신, **Then** useRef + requestAnimationFrame 버퍼링으로 DOM 업데이트 최소화
- [ ] **Given** 성능 최적화 적용 후, **When** React DevTools Profiler로 측정, **Then** 불필요한 리렌더링 50% 이상 감소

---

## Tasks

- [ ] React ErrorBoundary 클래스 컴포넌트 구현
- [ ] ErrorBoundary fallback UI 디자인 (Tailwind CSS)
- [ ] App 레벨 및 주요 섹션별 ErrorBoundary 배치
- [ ] "다시 시도" 버튼 및 리셋 로직 구현
- [ ] MessageBubble에 React.memo 적용 (props 비교 함수 포함)
- [ ] SSE 토큰 수신 시 useRef + requestAnimationFrame 버퍼링 구현
- [ ] 리렌더링 최적화 전후 성능 비교 측정
- [ ] 단위 테스트 작성 (ErrorBoundary 동작, memo 동작)

---

## 기술 노트

### 문제점 (Sprint 03 리뷰에서 도출)

Sprint 03 Frontend 구현에서 다음 문제가 식별됨:

1. **ErrorBoundary 부재** - 컴포넌트 렌더링 에러 시 전체 앱이 화이트스크린으로 크래시
2. **MessageBubble 리렌더링 과다** - 새 토큰이 추가될 때마다 모든 MessageBubble이 리렌더링
3. **SSE 스트리밍 성능** - 토큰마다 setState가 호출되어 초당 수십 회 불필요한 DOM 업데이트

### 해결 방향

#### ErrorBoundary

```typescript
// frontend/src/shared/components/ErrorBoundary.tsx
class ErrorBoundary extends React.Component<Props, State> {
  state = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo);
    // 에러 리포팅 서비스에 전송 (선택)
  }

  render() {
    if (this.state.hasError) {
      return <ErrorFallback onRetry={() => this.setState({ hasError: false })} />;
    }
    return this.props.children;
  }
}
```

#### 성능 최적화

```typescript
// React.memo로 불필요한 리렌더링 방지
const MessageBubble = React.memo(({ message }: Props) => {
  return <div className="...">{message.content}</div>;
}, (prev, next) => prev.message.id === next.message.id
   && prev.message.content === next.message.content);

// useRef + RAF 버퍼링
const bufferRef = useRef<string>('');
const rafRef = useRef<number>();

const appendToken = useCallback((token: string) => {
  bufferRef.current += token;

  if (!rafRef.current) {
    rafRef.current = requestAnimationFrame(() => {
      setContent(prev => prev + bufferRef.current);
      bufferRef.current = '';
      rafRef.current = undefined;
    });
  }
}, []);
```

### 영향 범위

- `frontend/src/shared/components/ErrorBoundary.tsx` - 신규
- `frontend/src/shared/components/ErrorFallback.tsx` - 신규
- `frontend/src/App.tsx` - ErrorBoundary 배치
- `frontend/src/features/search/components/MessageBubble.tsx` - React.memo
- `frontend/src/features/search/hooks/useStreamingSearch.ts` - RAF 버퍼링

---

## 테스트 계획

- [ ] Unit Test: ErrorBoundary가 에러를 캐치하고 fallback 표시
- [ ] Unit Test: "다시 시도" 버튼으로 리셋 동작
- [ ] Unit Test: React.memo가 동일 props에서 리렌더링 방지
- [ ] Performance Test: RAF 버퍼링 전후 DOM 업데이트 횟수 비교
- [ ] Visual Test: fallback UI 렌더링 확인

---

## 참고 자료

- Sprint 03 완료 리뷰에서 도출 - ErrorBoundary 부재, 성능 이슈
- [STORY-043 SSE 스트리밍](./STORY-043-sse-streaming.md)
- [React Error Boundaries](https://react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary)
