# STORY-042: Search UI 컴포넌트

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-31 |
| **Epic** | EPIC-003 |
| **Status** | Done |
| **Priority** | High |
| **Story Points** | 5 |
| **Assignee** | Frontend |
| **Sprint** | 3 |

---

## User Story

**As a** 지식 검색 사용자,
**I want** 채팅 형태의 검색 인터페이스,
**So that** 자연어로 질문하고 대화형으로 답변을 받을 수 있음.

---

## Acceptance Criteria

- [ ] **Given** 검색 페이지 접근, **When** 렌더링, **Then** 채팅 입력창과 메시지 영역 표시
- [ ] **Given** 질문 입력 후 전송, **When** API 응답, **Then** 사용자 질문과 AI 응답이 채팅 형태로 표시
- [ ] **Given** AI 응답, **When** 출처 포함, **Then** 출처 문서 링크 표시
- [ ] **Given** 검색 중, **When** 로딩 상태, **Then** 로딩 인디케이터 표시
- [ ] **Given** 긴 대화, **When** 스크롤, **Then** 자동 스크롤 및 수동 스크롤 지원
- [ ] **Given** 키워드 검색 페이지 접근 (/search/keyword), **When** 렌더링, **Then** 검색어 입력창과 결과 목록 표시
- [ ] **Given** 키워드 입력 후 검색, **When** API 응답, **Then** 검색 결과가 카드/리스트 형태로 표시 (제목, 요약, 출처)
- [ ] **Given** 검색 결과, **When** 항목 클릭, **Then** 문서 상세 또는 채팅 검색으로 이동

---

## Tasks

- [ ] ChatSearch 페이지 컴포넌트
- [ ] MessageList 컴포넌트
- [ ] MessageBubble 컴포넌트 (User/AI)
- [ ] ChatInput 컴포넌트
- [ ] SourceCitation 컴포넌트
- [ ] useSearchChat 훅 구현
- [ ] 자동 스크롤 로직
- [ ] 에러 처리 및 재시도
- [ ] KeywordSearch 페이지 컴포넌트 (/search/keyword)
- [ ] SearchResultCard 컴포넌트
- [ ] SearchResultList 컴포넌트
- [ ] useKeywordSearch 훅 구현
- [ ] 단위 테스트 작성 (Chat + Keyword)

---

## 기술 노트

> **마이그레이션 공지** (2026-01-25)
>
> 아래에 MUI 코드(레거시)와 Tailwind 코드(권장) 두 버전이 제공됩니다.
> **신규 구현 시 Tailwind 버전을 사용하세요.**
>
> 전환 가이드: [MUI to Tailwind 마이그레이션 가이드](../../knowledge_service/docs/05_development/06_mui_to_tailwind_migration.md)

### ChatSearch 페이지 (Tailwind - 권장)

```typescript
// frontend/src/features/search/ChatSearch.tsx
import { useState, useRef, useEffect } from 'react';
import { MessageList } from './components/MessageList';
import { ChatInput } from './components/ChatInput';
import { useSearchChat } from './hooks/useSearchChat';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  timestamp: Date;
}

export const ChatSearch: React.FC = () => {
  const { messages, sendMessage, isLoading, error, retry } = useSearchChat();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  // 자동 스크롤
  useEffect(() => {
    if (autoScroll) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, autoScroll]);

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const { scrollTop, scrollHeight, clientHeight } = e.currentTarget;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
    setAutoScroll(isAtBottom);
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* 메시지 영역 */}
      <div
        className="flex-1 overflow-auto p-4"
        onScroll={handleScroll}
      >
        <MessageList messages={messages} isLoading={isLoading} />
        <div ref={messagesEndRef} />
      </div>

      {/* 에러 표시 */}
      {error && (
        <div className="mx-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700">
          오류가 발생했습니다.
          <button
            onClick={retry}
            className="ml-2 underline hover:no-underline"
          >
            재시도
          </button>
        </div>
      )}

      {/* 입력 영역 */}
      <div className="border-t border-gray-200 bg-white p-4">
        <ChatInput
          onSend={sendMessage}
          disabled={isLoading}
          placeholder="질문을 입력하세요..."
        />
      </div>
    </div>
  );
};
```

### MessageBubble 컴포넌트 (Tailwind - 권장)

```typescript
// frontend/src/features/search/components/MessageBubble.tsx
import { UserIcon, CpuChipIcon } from '@heroicons/react/24/solid';
import { Message, Source } from '../types';
import { SourceCitation } from './SourceCitation';
import ReactMarkdown from 'react-markdown';

interface MessageBubbleProps {
  message: Message;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`flex max-w-[80%] ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
        {/* 아바타 */}
        <div className={`flex-shrink-0 ${isUser ? 'ml-3' : 'mr-3'}`}>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
            isUser ? 'bg-secondary-500' : 'bg-primary-500'
          }`}>
            {isUser ? (
              <UserIcon className="h-5 w-5 text-white" />
            ) : (
              <CpuChipIcon className="h-5 w-5 text-white" />
            )}
          </div>
        </div>

        <div>
          {/* 메시지 내용 */}
          <div className={`p-3 rounded-lg ${
            isUser
              ? 'bg-primary-600 text-white'
              : 'bg-gray-100 text-gray-900'
          }`}>
            {isUser ? (
              <p>{message.content}</p>
            ) : (
              <div className="prose prose-sm max-w-none">
                <ReactMarkdown>{message.content}</ReactMarkdown>
              </div>
            )}
          </div>

          {/* 출처 (AI 응답만) */}
          {!isUser && message.sources && message.sources.length > 0 && (
            <div className="mt-2">
              <span className="text-xs text-gray-500">출처:</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {message.sources.map((source, idx) => (
                  <SourceCitation key={idx} source={source} />
                ))}
              </div>
            </div>
          )}

          {/* 타임스탬프 */}
          <p className="text-xs text-gray-400 mt-1">
            {new Date(message.timestamp).toLocaleTimeString()}
          </p>
        </div>
      </div>
    </div>
  );
};
```

### ChatInput 컴포넌트 (Tailwind - 권장)

```typescript
// frontend/src/features/search/components/ChatInput.tsx
import { useState, useRef } from 'react';
import { PaperAirplaneIcon } from '@heroicons/react/24/solid';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSend,
  disabled,
  placeholder = '메시지를 입력하세요...'
}) => {
  const [input, setInput] = useState('');
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    if (input.trim() && !disabled) {
      onSend(input.trim());
      setInput('');
      inputRef.current?.focus();
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex items-end gap-2">
      <textarea
        ref={inputRef}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyPress={handleKeyPress}
        placeholder={placeholder}
        disabled={disabled}
        rows={1}
        className="flex-1 resize-none rounded-lg border border-gray-300 px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
        style={{ maxHeight: '120px' }}
      />
      <button
        onClick={handleSend}
        disabled={disabled || !input.trim()}
        className="p-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
      >
        {disabled ? (
          <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        ) : (
          <PaperAirplaneIcon className="h-5 w-5" />
        )}
      </button>
    </div>
  );
};
```

### SourceCitation 컴포넌트 (Tailwind - 권장)

```typescript
// frontend/src/features/search/components/SourceCitation.tsx
import { DocumentTextIcon } from '@heroicons/react/24/outline';

interface Source {
  title: string;
  chunk_id: string;
  doc_type?: string;
}

export const SourceCitation: React.FC<{ source: Source }> = ({ source }) => {
  return (
    <button
      onClick={() => {
        // TODO: 문서 상세 페이지로 이동
        console.log('Navigate to:', source.chunk_id);
      }}
      className="inline-flex items-center gap-1 px-2 py-1 text-xs border border-gray-300 rounded-full hover:bg-gray-100 transition-colors"
      title={`문서: ${source.title}`}
    >
      <DocumentTextIcon className="h-3 w-3 text-gray-500" />
      <span className="text-gray-700 truncate max-w-[150px]">{source.title}</span>
    </button>
  );
};
```

---

<details>
<summary>레거시 코드 (MUI) - 참고용</summary>

### ChatSearch 페이지

```typescript
// frontend/src/features/search/ChatSearch.tsx
import { useState, useRef, useEffect } from 'react';
import { Box, Paper } from '@mui/material';
import { MessageList } from './components/MessageList';
import { ChatInput } from './components/ChatInput';
import { useSearchChat } from './hooks/useSearchChat';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  timestamp: Date;
}

export const ChatSearch: React.FC = () => {
  const { messages, sendMessage, isLoading, error, retry } = useSearchChat();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  // 자동 스크롤
  useEffect(() => {
    if (autoScroll) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, autoScroll]);

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const { scrollTop, scrollHeight, clientHeight } = e.currentTarget;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
    setAutoScroll(isAtBottom);
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      {/* 메시지 영역 */}
      <Box
        sx={{ flex: 1, overflow: 'auto', p: 2 }}
        onScroll={handleScroll}
      >
        <MessageList messages={messages} isLoading={isLoading} />
        <div ref={messagesEndRef} />
      </Box>

      {/* 에러 표시 */}
      {error && (
        <Paper sx={{ p: 2, m: 2, bgcolor: 'error.light' }}>
          오류가 발생했습니다. <button onClick={retry}>재시도</button>
        </Paper>
      )}

      {/* 입력 영역 */}
      <Paper sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
        <ChatInput
          onSend={sendMessage}
          disabled={isLoading}
          placeholder="질문을 입력하세요..."
        />
      </Paper>
    </Box>
  );
};
```

### MessageBubble 컴포넌트

```typescript
// frontend/src/features/search/components/MessageBubble.tsx
import { Box, Paper, Typography, Avatar, Chip, Stack } from '@mui/material';
import PersonIcon from '@mui/icons-material/Person';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import { Message, Source } from '../types';
import { SourceCitation } from './SourceCitation';
import ReactMarkdown from 'react-markdown';

interface MessageBubbleProps {
  message: Message;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.role === 'user';

  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        mb: 2
      }}
    >
      <Box sx={{ display: 'flex', maxWidth: '80%' }}>
        {/* 아바타 (AI만) */}
        {!isUser && (
          <Avatar sx={{ mr: 1, bgcolor: 'primary.main' }}>
            <SmartToyIcon />
          </Avatar>
        )}

        <Box>
          {/* 메시지 내용 */}
          <Paper
            sx={{
              p: 2,
              bgcolor: isUser ? 'primary.main' : 'grey.100',
              color: isUser ? 'white' : 'text.primary',
              borderRadius: 2
            }}
          >
            {isUser ? (
              <Typography>{message.content}</Typography>
            ) : (
              <ReactMarkdown>{message.content}</ReactMarkdown>
            )}
          </Paper>

          {/* 출처 (AI 응답만) */}
          {!isUser && message.sources && message.sources.length > 0 && (
            <Box sx={{ mt: 1 }}>
              <Typography variant="caption" color="textSecondary">
                출처:
              </Typography>
              <Stack direction="row" spacing={1} sx={{ mt: 0.5, flexWrap: 'wrap' }}>
                {message.sources.map((source, idx) => (
                  <SourceCitation key={idx} source={source} />
                ))}
              </Stack>
            </Box>
          )}

          {/* 타임스탬프 */}
          <Typography variant="caption" color="textSecondary" sx={{ mt: 0.5 }}>
            {new Date(message.timestamp).toLocaleTimeString()}
          </Typography>
        </Box>

        {/* 아바타 (User만) */}
        {isUser && (
          <Avatar sx={{ ml: 1, bgcolor: 'secondary.main' }}>
            <PersonIcon />
          </Avatar>
        )}
      </Box>
    </Box>
  );
};
```

### ChatInput 컴포넌트

```typescript
// frontend/src/features/search/components/ChatInput.tsx
import { useState, useRef } from 'react';
import { TextField, IconButton, Box, CircularProgress } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSend,
  disabled,
  placeholder = '메시지를 입력하세요...'
}) => {
  const [input, setInput] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSend = () => {
    if (input.trim() && !disabled) {
      onSend(input.trim());
      setInput('');
      inputRef.current?.focus();
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <Box sx={{ display: 'flex', alignItems: 'center' }}>
      <TextField
        inputRef={inputRef}
        fullWidth
        multiline
        maxRows={4}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyPress={handleKeyPress}
        placeholder={placeholder}
        disabled={disabled}
        sx={{ mr: 1 }}
      />
      <IconButton
        onClick={handleSend}
        disabled={disabled || !input.trim()}
        color="primary"
      >
        {disabled ? <CircularProgress size={24} /> : <SendIcon />}
      </IconButton>
    </Box>
  );
};
```

### SourceCitation 컴포넌트

```typescript
// frontend/src/features/search/components/SourceCitation.tsx
import { Chip, Tooltip } from '@mui/material';
import ArticleIcon from '@mui/icons-material/Article';

interface Source {
  title: string;
  chunk_id: string;
  doc_type?: string;
}

export const SourceCitation: React.FC<{ source: Source }> = ({ source }) => {
  return (
    <Tooltip title={`문서: ${source.title}`}>
      <Chip
        icon={<ArticleIcon />}
        label={source.title}
        size="small"
        variant="outlined"
        clickable
        onClick={() => {
          // TODO: 문서 상세 페이지로 이동
          console.log('Navigate to:', source.chunk_id);
        }}
      />
    </Tooltip>
  );
};
```

</details>

### 영향 범위
- `frontend/src/features/search/ChatSearch.tsx`
- `frontend/src/features/search/components/MessageList.tsx`
- `frontend/src/features/search/components/MessageBubble.tsx`
- `frontend/src/features/search/components/ChatInput.tsx`
- `frontend/src/features/search/components/SourceCitation.tsx`
- `frontend/src/features/search/types.ts`

---

## 테스트 계획

- [ ] Unit Test: MessageBubble 렌더링 (User/AI)
- [ ] Unit Test: ChatInput 입력/전송
- [ ] Unit Test: SourceCitation 클릭
- [ ] Integration Test: 채팅 플로우
- [ ] Accessibility Test: 스크린 리더 지원

---

## 참고 자료

- [Frontend 상세 설계서](../../knowledge_service/docs/02_design/02_frontend_detailed_design.md)
- [UI Storyboard](../../knowledge_service/docs/02_design/ui_storyboard/)
