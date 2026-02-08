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
 * Layout: Left (chat) + Right (graph panel, conditional)
 * Composed of: MessageList, ChatInput, StreamingIndicator, SourceCitation, GraphPanel
 * Uses: useStreamingSearch hook for SSE lifecycle management
 */
import React, { useState, useCallback } from 'react';
import {
  ExclamationTriangleIcon,
  StopIcon,
} from '@heroicons/react/24/outline';
import MessageList from './components/MessageList';
import ChatInput from './components/ChatInput';
import StreamingIndicator from './components/StreamingIndicator';
import GraphPanel from './components/GraphPanel';
import { useStreamingSearch } from './hooks/useStreamingSearch';
import { LiveRegion } from '@/components/common';
import type { Source } from './types';

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

  // Graph panel state
  const [showGraphPanel, setShowGraphPanel] = useState(false);
  const [selectedGraphEntities, setSelectedGraphEntities] = useState<string[]>(
    [],
  );

  const handleGraphSourceClick = useCallback((source: Source) => {
    if (source.sourceType !== 'graph') return;
    const entities: string[] = [];
    if (source.graphContext?.relatedEntities?.length) {
      entities.push(...source.graphContext.relatedEntities);
    }
    // ISSUE-011: title이 파일명인 경우 엔티티로 사용하지 않음
    if (entities.length === 0 && source.title) {
      const isFilename = /\.\w{2,5}$/.test(source.title) &&
        /\.(pdf|docx?|xlsx?|pptx?|txt|md|html?|csv|json|xml|hwp)$/i.test(source.title);
      if (!isFilename) {
        entities.push(source.title);
      }
    }
    if (entities.length > 0) {
      setSelectedGraphEntities(entities);
      setShowGraphPanel(true);
    }
  }, []);

  const closeGraphPanel = useCallback(() => {
    setShowGraphPanel(false);
    setSelectedGraphEntities([]);
  }, []);

  /** Handle document download - open API URL directly for FileResponse/Redirect */
  const handleDownloadClick = useCallback((source: Source) => {
    if (!source.documentId) return;
    const baseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1';
    window.open(`${baseUrl}/documents/${source.documentId}/download`, '_blank');
  }, []);

  // Generate status message for screen readers
  const getStatusMessage = () => {
    if (isConnecting) return 'Connecting to search service...';
    if (isStreaming) return 'Generating response...';
    if (error) return `Error: ${error}`;
    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      if (lastMessage.role === 'assistant') {
        return 'Response complete';
      }
    }
    return '';
  };

  return (
    <div
      className="relative flex flex-row bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden"
      style={{ height: 'calc(100vh - 280px)', minHeight: '400px' }}
      data-testid="chat-search"
      role="region"
      aria-label="Chat search interface"
    >
      {/* Screen reader announcements for search status */}
      <LiveRegion
        message={getStatusMessage()}
        politeness={error ? 'assertive' : 'polite'}
      />

      {/* Left: Chat Area */}
      <div
        className={`flex flex-col min-w-0 overflow-hidden ${showGraphPanel ? 'flex-[3]' : 'flex-1'}`}
      >
        {/* Messages Area */}
        <MessageList
          messages={messages}
          onSuggestionClick={(suggestion) => {
            setQuery(suggestion);
          }}
          onGraphSourceClick={handleGraphSourceClick}
          onDownloadClick={handleDownloadClick}
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
          <div
            className="px-4 py-2 bg-error-50 dark:bg-error-900/20 border-t border-error-200 dark:border-error-800 flex items-center gap-2"
            role="alert"
            aria-live="assertive"
          >
            <ExclamationTriangleIcon
              className="h-4 w-4 text-error-500 flex-shrink-0"
              aria-hidden="true"
            />
            <span className="text-xs text-error-700 dark:text-error-300">
              {error}
            </span>
            <button
              onClick={dismissError}
              className="ml-auto text-xs text-error-500 hover:text-error-700 font-medium focus:outline-none focus:ring-2 focus:ring-error-500 rounded px-1"
              aria-label="Dismiss error message"
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

      {/* Right: Graph Panel - shown inline on md+, overlay on small screens */}
      {showGraphPanel && (
        <>
          {/* Inline panel for md and above */}
          <div className="hidden md:flex flex-[2] min-w-[280px] max-w-[500px]">
            <GraphPanel
              entityNames={selectedGraphEntities}
              onClose={closeGraphPanel}
            />
          </div>
          {/* Overlay panel for smaller screens */}
          <div className="md:hidden absolute inset-0 z-20">
            <GraphPanel
              entityNames={selectedGraphEntities}
              onClose={closeGraphPanel}
            />
          </div>
        </>
      )}
    </div>
  );
};

export default ChatSearch;
