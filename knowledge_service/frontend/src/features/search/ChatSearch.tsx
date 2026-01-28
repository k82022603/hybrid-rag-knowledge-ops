/**
 * ChatSearch - Chat-style search page component
 *
 * Implements STORY-042 Acceptance Criteria:
 * - AC1: Chat input area and message display
 * - AC2: User questions and AI answers in chat format
 * - AC3: Source document links in AI responses
 * - AC4: Loading indicator during search
 * - AC5: Auto-scroll + manual scroll support
 *
 * Implements STORY-043 Acceptance Criteria:
 * - AC1: Token-by-token streaming display
 * - AC2: Incremental token append
 * - AC3: Source citations after [DONE]
 * - AC4: Auto-reconnect with 3 retries + exponential backoff
 * - AC5: User cancel/abort support
 *
 * Composed of: MessageList, ChatInput, StreamingIndicator, SourceCitation (via MessageBubble)
 * Uses: useStreamingSearch hook for SSE lifecycle management
 */
import React from 'react';
import {
  ExclamationTriangleIcon,
  StopIcon,
} from '@heroicons/react/24/outline';
import MessageList from './components/MessageList';
import ChatInput from './components/ChatInput';
import StreamingIndicator from './components/StreamingIndicator';
import { useStreamingSearch } from './hooks/useStreamingSearch';

/**
 * ChatSearch page component (/search/chat)
 */
const ChatSearch: React.FC = () => {
  const {
    query,
    setQuery,
    messages,
    isStreaming,
    isConnecting,
    error,
    reconnectInfo,
    sendMessage,
    cancelStream,
    clearMessages,
    dismissError,
  } = useStreamingSearch();

  return (
    <div
      className="flex flex-col bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden"
      style={{ height: 'calc(100vh - 280px)', minHeight: '400px' }}
      data-testid="chat-search"
    >
      {/* Messages Area */}
      <MessageList
        messages={messages}
        onSuggestionClick={(suggestion) => {
          setQuery(suggestion);
        }}
      />

      {/* Streaming Indicator + Cancel Button */}
      {isStreaming && (
        <div className="flex items-center justify-between border-t border-gray-100 dark:border-gray-700/50">
          <StreamingIndicator
            isStreaming={isStreaming}
            isConnecting={isConnecting}
            reconnectInfo={reconnectInfo}
          />
          <button
            onClick={cancelStream}
            className="flex items-center gap-1.5 mr-4 px-3 py-1.5 text-xs font-medium text-gray-500 dark:text-gray-400 hover:text-error-600 dark:hover:text-error-400 hover:bg-error-50 dark:hover:bg-error-900/20 rounded-lg transition-colors"
            aria-label="Cancel streaming response"
            data-testid="cancel-stream-button"
          >
            <StopIcon className="h-3.5 w-3.5" />
            <span>Cancel</span>
          </button>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="px-4 py-2 bg-error-50 dark:bg-error-900/20 border-t border-error-200 dark:border-error-800 flex items-center gap-2">
          <ExclamationTriangleIcon className="h-4 w-4 text-error-500 flex-shrink-0" />
          <span className="text-xs text-error-700 dark:text-error-300">
            {error}
          </span>
          <button
            onClick={dismissError}
            className="ml-auto text-xs text-error-500 hover:text-error-700 font-medium"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Input Area */}
      <ChatInput
        value={query}
        onChange={setQuery}
        onSubmit={() => sendMessage()}
        onClear={clearMessages}
        isLoading={isStreaming}
        showClear={messages.length > 0}
      />
    </div>
  );
};

export default ChatSearch;
