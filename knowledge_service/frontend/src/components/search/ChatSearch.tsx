/**
 * ChatSearch - 채팅형 검색 컴포넌트
 *
 * SSE 스트리밍을 통한 실시간 AI 응답
 * Tailwind CSS + Heroicons 기반
 */
import { useState, useRef, useEffect, useCallback } from 'react';
import {
  PaperAirplaneIcon,
  ArrowPathIcon,
  UserIcon,
  SparklesIcon,
  ExclamationTriangleIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline';
import { searchService, type SearchResult } from '@/services/searchService';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sources?: SearchResult[];
  isStreaming?: boolean;
}

/**
 * MessageBubble - 메시지 버블 컴포넌트
 */
const MessageBubble: React.FC<{ message: Message }> = ({ message }) => {
  const isUser = message.role === 'user';

  return (
    <div
      className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}
      data-testid={`message-${message.id}`}
    >
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          isUser
            ? 'bg-primary-600 text-white'
            : 'bg-accent-100 dark:bg-accent-900/30 text-accent-600 dark:text-accent-400'
        }`}
      >
        {isUser ? (
          <UserIcon className="h-4 w-4" />
        ) : (
          <SparklesIcon className="h-4 w-4" />
        )}
      </div>

      {/* Content */}
      <div className={`flex-1 ${isUser ? 'text-right' : ''}`}>
        <div
          className={`inline-block max-w-[80%] px-4 py-3 rounded-xl ${
            isUser
              ? 'bg-primary-600 text-white rounded-tr-sm'
              : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-900 dark:text-white rounded-tl-sm'
          }`}
        >
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>

          {/* Streaming indicator */}
          {message.isStreaming && (
            <span className="inline-flex items-center gap-1 mt-1">
              <span className="w-1.5 h-1.5 rounded-full bg-primary-400 animate-pulse" />
              <span className="w-1.5 h-1.5 rounded-full bg-primary-400 animate-pulse delay-75" />
              <span className="w-1.5 h-1.5 rounded-full bg-primary-400 animate-pulse delay-150" />
            </span>
          )}
        </div>

        {/* Sources */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="mt-2 space-y-1">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Sources:</p>
            <div className="flex flex-wrap gap-2">
              {message.sources.slice(0, 3).map((source) => (
                <div
                  key={source.chunkId}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-xs text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-750 transition-colors cursor-pointer"
                  title={source.content}
                >
                  <DocumentTextIcon className="h-3.5 w-3.5 text-gray-400" />
                  <span className="truncate max-w-[150px]">
                    {source.metadata?.projectName || 'Document'}
                  </span>
                  <span className="text-gray-400">
                    {(source.score * 100).toFixed(0)}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Timestamp */}
        <p
          className={`mt-1 text-2xs text-gray-400 dark:text-gray-500 ${
            isUser ? 'text-right' : ''
          }`}
        >
          {message.timestamp.toLocaleTimeString('ko-KR', {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </p>
      </div>
    </div>
  );
};

/**
 * ChatSearch 메인 컴포넌트
 */
const ChatSearch: React.FC = () => {
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Cleanup EventSource on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      const trimmedQuery = query.trim();
      if (!trimmedQuery || isLoading) return;

      setError(null);

      // Add user message
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: trimmedQuery,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMessage]);
      setQuery('');
      setIsLoading(true);

      // Create streaming assistant message
      const assistantId = `assistant-${Date.now()}`;
      setMessages((prev) => [
        ...prev,
        {
          id: assistantId,
          role: 'assistant',
          content: '',
          timestamp: new Date(),
          isStreaming: true,
        },
      ]);

      try {
        // Use SSE streaming for real-time responses
        const eventSource = searchService.streamSearch(
          trimmedQuery,
          // onMessage
          (data: string) => {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantId
                  ? { ...msg, content: msg.content + data }
                  : msg
              )
            );
          },
          // onError
          (errorEvent: Event) => {
            console.error('SSE error:', errorEvent);
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantId
                  ? {
                      ...msg,
                      isStreaming: false,
                      content:
                        msg.content ||
                        'Sorry, an error occurred while processing your request. Please try again.',
                    }
                  : msg
              )
            );
            setIsLoading(false);
            setError('Connection error. Please try again.');
          },
          // onComplete
          () => {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantId
                  ? { ...msg, isStreaming: false }
                  : msg
              )
            );
            setIsLoading(false);
          }
        );

        eventSourceRef.current = eventSource;
      } catch (err) {
        console.error('Search error:', err);
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantId
              ? {
                  ...msg,
                  isStreaming: false,
                  content:
                    'Sorry, failed to connect to the search service. Please check your connection and try again.',
                }
              : msg
          )
        );
        setIsLoading(false);
        setError('Failed to start search. Please try again.');
      }
    },
    [query, isLoading]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSubmit(e as unknown as React.FormEvent);
      }
    },
    [handleSubmit]
  );

  const handleClearChat = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    setMessages([]);
    setError(null);
    setIsLoading(false);
    inputRef.current?.focus();
  }, []);

  return (
    <div
      className="flex flex-col bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden"
      style={{ height: 'calc(100vh - 280px)', minHeight: '400px' }}
      data-testid="chat-search"
    >
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-md">
              <SparklesIcon className="h-12 w-12 text-primary-300 dark:text-primary-600 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                Knowledge Search Assistant
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
                Ask questions about your knowledge base. I will search through documents
                and provide relevant answers with source references.
              </p>
              <div className="space-y-2">
                <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
                  Try asking:
                </p>
                {[
                  'What is the document upload process?',
                  'Summarize the latest technical guidelines',
                  'How does the authentication system work?',
                ].map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => {
                      setQuery(suggestion);
                      inputRef.current?.focus();
                    }}
                    className="block w-full text-left px-4 py-2.5 text-sm text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-750 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Error banner */}
      {error && (
        <div className="px-4 py-2 bg-error-50 dark:bg-error-900/20 border-t border-error-200 dark:border-error-800 flex items-center gap-2">
          <ExclamationTriangleIcon className="h-4 w-4 text-error-500 flex-shrink-0" />
          <span className="text-xs text-error-700 dark:text-error-300">{error}</span>
          <button
            onClick={() => setError(null)}
            className="ml-auto text-xs text-error-500 hover:text-error-700 font-medium"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Input Area */}
      <div className="border-t border-gray-200 dark:border-gray-700 p-4">
        <form onSubmit={handleSubmit} className="flex items-end gap-3">
          {/* Clear chat button */}
          {messages.length > 0 && (
            <button
              type="button"
              onClick={handleClearChat}
              className="flex-shrink-0 p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              title="Clear conversation"
              aria-label="Clear conversation"
            >
              <ArrowPathIcon className="h-5 w-5" />
            </button>
          )}

          {/* Input */}
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question..."
              disabled={isLoading}
              rows={1}
              className="w-full px-4 py-2.5 text-sm rounded-xl border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 focus:bg-white dark:focus:bg-gray-800 resize-none disabled:opacity-50 transition-colors"
              style={{ maxHeight: '120px' }}
              aria-label="Search query"
            />
          </div>

          {/* Submit button */}
          <button
            type="submit"
            disabled={!query.trim() || isLoading}
            className="flex-shrink-0 p-2.5 rounded-xl bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            aria-label="Send message"
          >
            {isLoading ? (
              <ArrowPathIcon className="h-5 w-5 animate-spin" />
            ) : (
              <PaperAirplaneIcon className="h-5 w-5" />
            )}
          </button>
        </form>
        <p className="mt-2 text-2xs text-gray-400 dark:text-gray-500 text-center">
          Powered by Hybrid RAG - Press Enter to send, Shift+Enter for new line
        </p>
      </div>
    </div>
  );
};

export default ChatSearch;
