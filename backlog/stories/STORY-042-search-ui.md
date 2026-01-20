# STORY-042: Search UI 컴포넌트

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-43 |
| **Epic** | EPIC-003 |
| **Status** | To Do |
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
- [ ] 단위 테스트 작성

---

## 기술 노트

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

- [Frontend 상세 설계서](../../knowledge_service/docs/02_design/frontend_detailed_design.md)
- [UI Storyboard](../../knowledge_service/docs/02_design/ui_storyboard/)
