# STORY-043: SSE 스트리밍 응답

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-46 |
| **Epic** | EPIC-003 |
| **Status** | To Do |
| **Priority** | Medium |
| **Story Points** | 3 |
| **Assignee** | Frontend |
| **Sprint** | 3 |

---

## User Story

**As a** 지식 검색 사용자,
**I want** AI 응답이 실시간으로 스트리밍,
**So that** 긴 응답도 빠르게 확인하며 대기 시간을 줄일 수 있음.

---

## Acceptance Criteria

- [ ] **Given** 검색 요청 전송, **When** AI 응답 시작, **Then** 토큰 단위로 실시간 표시
- [ ] **Given** 스트리밍 중, **When** 새 토큰 수신, **Then** 기존 응답에 추가
- [ ] **Given** 스트리밍 완료, **When** [DONE] 이벤트, **Then** 출처 정보 표시
- [ ] **Given** 네트워크 오류, **When** SSE 연결 끊김, **Then** 자동 재연결 시도 (3회)
- [ ] **Given** 사용자 취소, **When** 중단 버튼 클릭, **Then** SSE 연결 종료

---

## Tasks

- [ ] SSE 연결 유틸리티 구현
- [ ] useStreamingSearch 훅 구현
- [ ] 스트리밍 메시지 상태 관리
- [ ] 에러 핸들링 및 재연결
- [ ] 취소 기능 구현
- [ ] 스트리밍 인디케이터 UI
- [ ] 단위 테스트 작성

---

## 기술 노트

> **마이그레이션 공지** (2026-01-25)
>
> 아래에 MUI 코드(레거시)와 Tailwind 코드(권장) 두 버전이 제공됩니다.
> **신규 구현 시 Tailwind 버전을 사용하세요.**
>
> **참고**: SSE 유틸리티, 훅 로직은 UI 독립적이므로 변경 없음.
>
> 전환 가이드: [MUI to Tailwind 마이그레이션 가이드](../../knowledge_service/docs/05_development/mui_to_tailwind_migration.md)

### SSE 유틸리티 (공통 - 변경 없음)

```typescript
// frontend/src/shared/api/sse.ts
// UI 독립적 로직이므로 MUI/Tailwind 관계없이 동일하게 사용
export interface SSEOptions {
  onMessage: (data: any) => void;
  onError?: (error: Event) => void;
  onComplete?: () => void;
  retries?: number;
  retryDelay?: number;
}

export class SSEClient {
  private eventSource: EventSource | null = null;
  private retryCount = 0;
  private aborted = false;

  constructor(
    private url: string,
    private options: SSEOptions
  ) {}

  connect(): void {
    if (this.aborted) return;

    this.eventSource = new EventSource(this.url);

    this.eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'done') {
          this.options.onComplete?.();
          this.close();
          return;
        }

        this.options.onMessage(data);
        this.retryCount = 0; // 성공 시 재시도 카운트 리셋
      } catch (e) {
        console.error('SSE parse error:', e);
      }
    };

    this.eventSource.onerror = (error) => {
      this.options.onError?.(error);
      this.handleError();
    };
  }

  private handleError(): void {
    this.close();

    const maxRetries = this.options.retries ?? 3;
    const retryDelay = this.options.retryDelay ?? 1000;

    if (this.retryCount < maxRetries && !this.aborted) {
      this.retryCount++;
      console.log(`SSE reconnecting... (${this.retryCount}/${maxRetries})`);
      setTimeout(() => this.connect(), retryDelay * this.retryCount);
    }
  }

  abort(): void {
    this.aborted = true;
    this.close();
  }

  close(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }
}
```

### 스트리밍 인디케이터 (Tailwind - 권장)

```typescript
// frontend/src/features/search/components/StreamingIndicator.tsx
export const StreamingIndicator: React.FC = () => {
  return (
    <div className="flex items-center p-2">
      <div className="w-2 h-2 bg-primary-600 rounded-full mr-2 animate-pulse" />
      <span className="text-sm text-gray-500">응답 생성 중...</span>
    </div>
  );
};
```

### ChatSearch 업데이트 (Tailwind - 권장)

```typescript
// ChatSearch.tsx 수정
import { StreamingIndicator } from './components/StreamingIndicator';

export const ChatSearch: React.FC = () => {
  const {
    messages,
    isStreaming,
    error,
    sendMessage,
    cancelStream
  } = useStreamingSearch();

  return (
    <div className="flex flex-col h-screen">
      <div className="flex-1 overflow-auto p-4">
        <MessageList messages={messages} />
        {isStreaming && <StreamingIndicator />}
        <div ref={messagesEndRef} />
      </div>

      <div className="border-t border-gray-200 p-4">
        <ChatInput
          onSend={sendMessage}
          disabled={isStreaming}
          onCancel={isStreaming ? cancelStream : undefined}
        />
      </div>
    </div>
  );
};
```

---

<details>
<summary>레거시 코드 (MUI) - 참고용</summary>

### SSE 유틸리티

```typescript
// frontend/src/shared/api/sse.ts
export interface SSEOptions {
  onMessage: (data: any) => void;
  onError?: (error: Event) => void;
  onComplete?: () => void;
  retries?: number;
  retryDelay?: number;
}

export class SSEClient {
  private eventSource: EventSource | null = null;
  private retryCount = 0;
  private aborted = false;

  constructor(
    private url: string,
    private options: SSEOptions
  ) {}

  connect(): void {
    if (this.aborted) return;

    this.eventSource = new EventSource(this.url);

    this.eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'done') {
          this.options.onComplete?.();
          this.close();
          return;
        }

        this.options.onMessage(data);
        this.retryCount = 0; // 성공 시 재시도 카운트 리셋
      } catch (e) {
        console.error('SSE parse error:', e);
      }
    };

    this.eventSource.onerror = (error) => {
      this.options.onError?.(error);
      this.handleError();
    };
  }

  private handleError(): void {
    this.close();

    const maxRetries = this.options.retries ?? 3;
    const retryDelay = this.options.retryDelay ?? 1000;

    if (this.retryCount < maxRetries && !this.aborted) {
      this.retryCount++;
      console.log(`SSE reconnecting... (${this.retryCount}/${maxRetries})`);
      setTimeout(() => this.connect(), retryDelay * this.retryCount);
    }
  }

  abort(): void {
    this.aborted = true;
    this.close();
  }

  close(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }
}
```

### useStreamingSearch 훅

```typescript
// frontend/src/features/search/hooks/useStreamingSearch.ts
import { useState, useCallback, useRef } from 'react';
import { SSEClient } from '../../../shared/api/sse';
import { useAuth } from '../../auth/useAuth';

interface StreamState {
  isStreaming: boolean;
  currentContent: string;
  sources: Source[];
  error: Error | null;
}

export const useStreamingSearch = () => {
  const { getToken } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [streamState, setStreamState] = useState<StreamState>({
    isStreaming: false,
    currentContent: '',
    sources: [],
    error: null
  });
  const sseClientRef = useRef<SSEClient | null>(null);

  const sendMessage = useCallback(async (query: string) => {
    // 1. 사용자 메시지 추가
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: query,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMessage]);

    // 2. 스트리밍 시작
    setStreamState({
      isStreaming: true,
      currentContent: '',
      sources: [],
      error: null
    });

    // 3. AI 응답 플레이스홀더
    const assistantId = crypto.randomUUID();
    setMessages(prev => [...prev, {
      id: assistantId,
      role: 'assistant',
      content: '',
      timestamp: new Date()
    }]);

    // 4. SSE 연결
    const token = await getToken();
    const url = `/api/v1/search/chat/stream?query=${encodeURIComponent(query)}&token=${token}`;

    sseClientRef.current = new SSEClient(url, {
      onMessage: (data) => {
        // 토큰 추가
        if (data.content) {
          setStreamState(prev => ({
            ...prev,
            currentContent: prev.currentContent + data.content
          }));
          setMessages(prev => prev.map(msg =>
            msg.id === assistantId
              ? { ...msg, content: msg.content + data.content }
              : msg
          ));
        }

        // 출처 정보
        if (data.sources) {
          setStreamState(prev => ({
            ...prev,
            sources: data.sources
          }));
        }
      },
      onComplete: () => {
        setStreamState(prev => ({
          ...prev,
          isStreaming: false
        }));
        // 최종 출처 추가
        setMessages(prev => prev.map(msg =>
          msg.id === assistantId
            ? { ...msg, sources: streamState.sources }
            : msg
        ));
      },
      onError: (error) => {
        setStreamState(prev => ({
          ...prev,
          isStreaming: false,
          error: new Error('스트리밍 연결 오류')
        }));
      }
    });

    sseClientRef.current.connect();
  }, [getToken]);

  const cancelStream = useCallback(() => {
    sseClientRef.current?.abort();
    setStreamState(prev => ({
      ...prev,
      isStreaming: false
    }));
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  return {
    messages,
    isStreaming: streamState.isStreaming,
    error: streamState.error,
    sendMessage,
    cancelStream,
    clearMessages
  };
};
```

### 스트리밍 인디케이터

```typescript
// frontend/src/features/search/components/StreamingIndicator.tsx
import { Box, Typography, keyframes } from '@mui/material';

const blink = keyframes`
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
`;

export const StreamingIndicator: React.FC = () => {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', p: 1 }}>
      <Box
        sx={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          bgcolor: 'primary.main',
          mr: 1,
          animation: `${blink} 1s ease-in-out infinite`
        }}
      />
      <Typography variant="body2" color="textSecondary">
        응답 생성 중...
      </Typography>
    </Box>
  );
};
```

### ChatSearch 업데이트

```typescript
// ChatSearch.tsx 수정
export const ChatSearch: React.FC = () => {
  const {
    messages,
    isStreaming,
    error,
    sendMessage,
    cancelStream
  } = useStreamingSearch();

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>
        <MessageList messages={messages} />
        {isStreaming && <StreamingIndicator />}
        <div ref={messagesEndRef} />
      </Box>

      <Paper sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
        <ChatInput
          onSend={sendMessage}
          disabled={isStreaming}
          onCancel={isStreaming ? cancelStream : undefined}
        />
      </Paper>
    </Box>
  );
};
```

</details>

### 영향 범위
- `frontend/src/shared/api/sse.ts` (신규)
- `frontend/src/features/search/hooks/useStreamingSearch.ts` (신규)
- `frontend/src/features/search/components/StreamingIndicator.tsx` (신규)
- `frontend/src/features/search/ChatSearch.tsx` (수정)

---

## 테스트 계획

- [ ] Unit Test: SSEClient 연결/종료
- [ ] Unit Test: useStreamingSearch 상태 관리
- [ ] Unit Test: 재연결 로직
- [ ] Integration Test: 실제 SSE 엔드포인트
- [ ] E2E Test: 전체 스트리밍 플로우

---

## 참고 자료

- [Server-Sent Events MDN](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [Frontend 상세 설계서](../../knowledge_service/docs/02_design/frontend_detailed_design.md)
