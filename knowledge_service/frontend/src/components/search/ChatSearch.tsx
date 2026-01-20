import { useState, useRef, useEffect } from 'react';
import {
  Box,
  TextField,
  IconButton,
  Paper,
  Typography,
  CircularProgress,
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

/**
 * ChatSearch - 채팅형 검색 컴포넌트
 *
 * SSE 스트리밍을 통한 실시간 AI 응답
 */
const ChatSearch: React.FC = () => {
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingContent]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: query.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setQuery('');
    setIsLoading(true);
    setStreamingContent('');

    try {
      // TODO: 실제 SSE 스트리밍 API 연결
      // const eventSource = new EventSource(
      //   `/api/v1/search/stream?query=${encodeURIComponent(query)}`
      // );
      //
      // eventSource.onmessage = (event) => {
      //   setStreamingContent((prev) => prev + event.data);
      // };
      //
      // eventSource.onerror = () => {
      //   eventSource.close();
      //   finishStreaming();
      // };

      // 임시: Mock 응답
      await new Promise((resolve) => setTimeout(resolve, 1000));
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `This is a sample response to: "${userMessage.content}". The actual implementation will use SSE streaming for real-time responses.`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Search error:', error);
    } finally {
      setIsLoading(false);
      setStreamingContent('');
    }
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '60vh' }}>
      {/* Messages Area */}
      <Paper
        elevation={1}
        sx={{
          flexGrow: 1,
          overflow: 'auto',
          p: 2,
          mb: 2,
          backgroundColor: 'background.default',
        }}
      >
        {messages.length === 0 ? (
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              color: 'text.secondary',
            }}
          >
            <Typography>Ask a question to search the knowledge base</Typography>
          </Box>
        ) : (
          messages.map((message) => (
            <Box
              key={message.id}
              sx={{
                mb: 2,
                display: 'flex',
                justifyContent:
                  message.role === 'user' ? 'flex-end' : 'flex-start',
              }}
            >
              <Paper
                sx={{
                  p: 2,
                  maxWidth: '70%',
                  backgroundColor:
                    message.role === 'user' ? 'primary.main' : 'background.paper',
                  color: message.role === 'user' ? 'white' : 'text.primary',
                }}
              >
                <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                  {message.content}
                </Typography>
              </Paper>
            </Box>
          ))
        )}
        {streamingContent && (
          <Box sx={{ mb: 2, display: 'flex', justifyContent: 'flex-start' }}>
            <Paper sx={{ p: 2, maxWidth: '70%' }}>
              <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                {streamingContent}
              </Typography>
            </Paper>
          </Box>
        )}
        <div ref={messagesEndRef} />
      </Paper>

      {/* Input Area */}
      <Paper
        component="form"
        onSubmit={handleSubmit}
        sx={{
          p: 2,
          display: 'flex',
          alignItems: 'center',
          gap: 1,
        }}
      >
        <TextField
          fullWidth
          placeholder="Ask a question..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={isLoading}
          variant="outlined"
          size="medium"
        />
        <IconButton
          type="submit"
          color="primary"
          disabled={!query.trim() || isLoading}
          size="large"
        >
          {isLoading ? <CircularProgress size={24} /> : <SendIcon />}
        </IconButton>
      </Paper>
    </Box>
  );
};

export default ChatSearch;
