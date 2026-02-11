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
 * Composed of: MessageList, ChatInput, SourceCitation, GraphPanel
 * Uses: useChatSearch hook for synchronous POST /search/chat
 */
import React, { useState, useCallback } from 'react';
import {
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import MessageList from './components/MessageList';
import ChatInput from './components/ChatInput';
import GraphPanel from './components/GraphPanel';
import { useChatSearch } from './hooks/useChatSearch';
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
    isLoading,
    error,
    sendMessage,
    clearMessages,
    dismissError,
  } = useChatSearch();

  // Graph panel state
  const [showGraphPanel, setShowGraphPanel] = useState(false);
  const [selectedGraphEntities, setSelectedGraphEntities] = useState<string[]>(
    [],
  );

  const handleGraphSourceClick = useCallback((source: Source) => {
    if (source.sourceType !== 'graph') return;
    const entities: string[] = [];

    // 1순위: graphContext의 relatedEntities (matched_entities 매핑, 가장 정확)
    if (source.graphContext?.relatedEntities?.length) {
      entities.push(...source.graphContext.relatedEntities);
    }

    // 2순위: 마지막 사용자 질문 (Neo4j에서 관련 엔티티를 찾을 가능성이 title보다 높음)
    if (entities.length === 0) {
      const lastUserMsg = [...messages].reverse().find((m) => m.role === 'user');
      if (lastUserMsg?.content?.trim()) {
        entities.push(lastUserMsg.content.trim());
      }
    }

    // 3순위: title에서 의미 있는 키워드 추출 (최후 수단)
    // ISSUE-011: title이 파일명이거나 괄호 포함 제목은 엔티티로 적합하지 않음
    if (entities.length === 0 && source.title) {
      const isFilename = /\.\w{2,5}$/.test(source.title) &&
        /\.(pdf|docx?|xlsx?|pptx?|txt|md|html?|csv|json|xml|hwp)$/i.test(source.title);
      if (!isFilename) {
        const cleaned = source.title.replace(/\([^)]*\)/g, '').trim();
        if (cleaned) {
          entities.push(cleaned);
        }
      }
    }

    // 4순위: projectName from metadata
    if (entities.length === 0 && source.metadata?.projectName) {
      entities.push(source.metadata.projectName);
    }

    if (entities.length > 0) {
      setSelectedGraphEntities(entities);
      setShowGraphPanel(true);
    }
  }, [messages]);

  const closeGraphPanel = useCallback(() => {
    setShowGraphPanel(false);
    setSelectedGraphEntities([]);
  }, []);

  /** Handle document download via fetch + blob (auth token included) */
  const handleDownloadClick = useCallback(async (source: Source) => {
    if (!source.documentId) return;
    try {
      const { default: api } = await import('@/services/api');
      const resp = await api.get(`/documents/${source.documentId}/download`, {
        responseType: 'blob',
      });
      const disposition = resp.headers['content-disposition'] || '';
      let filename = source.title || 'document';
      const match = disposition.match(/filename\*?=(?:utf-8''|"?)([^;"]+)/i);
      if (match) filename = decodeURIComponent(match[1].replace(/"/g, ''));
      const url = window.URL.createObjectURL(resp.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('[ChatSearch] Download failed:', err);
    }
  }, []);

  // Generate status message for screen readers
  const getStatusMessage = () => {
    if (isLoading) return '답변 생성 중...';
    if (error) return `오류: ${error}`;
    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      if (lastMessage.role === 'assistant') {
        return '답변 완료';
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

        {/* Loading Indicator */}
        {isLoading && (
          <div className="flex items-center gap-2 px-4 py-2 border-t border-gray-100 dark:border-gray-700/50">
            <div className="h-4 w-4 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
            <span className="text-xs text-gray-500 dark:text-gray-400">답변 생성 중...</span>
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
              닫기
            </button>
          </div>
        )}

        {/* Input Area */}
        <ChatInput
          value={query}
          onChange={setQuery}
          onSubmit={() => sendMessage()}
          onClear={clearMessages}
          isLoading={isLoading}
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
