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
 * Composed of: MessageList, ChatInput, SourceCitation (via MessageBubble)
 * Uses: useSearchChat hook for state management
 */
import React from 'react';
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';
import MessageList from './components/MessageList';
import ChatInput from './components/ChatInput';
import { useSearchChat } from './hooks/useSearchChat';

/**
 * ChatSearch page component (/search/chat)
 */
const ChatSearch: React.FC = () => {
  const {
    query,
    setQuery,
    messages,
    isLoading,
    error,
    handleSubmit,
    handleClear,
    dismissError,
  } = useSearchChat();

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
        onSubmit={handleSubmit}
        onClear={handleClear}
        isLoading={isLoading}
        showClear={messages.length > 0}
      />
    </div>
  );
};

export default ChatSearch;
