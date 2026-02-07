/**
 * MessageList - Chat message list with auto-scroll
 *
 * Renders a scrollable list of chat messages with automatic
 * scroll-to-bottom behavior. Supports manual scroll override
 * (user scrolling up pauses auto-scroll).
 */
import React, { useRef, useEffect, useCallback, useState } from 'react';
import { SparklesIcon } from '@heroicons/react/24/outline';
import type { Message, Source } from '../types';
import MessageBubble from './MessageBubble';

export interface MessageListProps {
  /** List of messages to display */
  messages: Message[];
  /** Callback when a suggestion is clicked (empty state) */
  onSuggestionClick?: (suggestion: string) => void;
  /** Callback when a graph source is clicked for visualization */
  onGraphSourceClick?: (source: Source) => void;
}

/** Default search suggestions for empty state */
const SUGGESTIONS = [
  'What is the document upload process?',
  'Summarize the latest technical guidelines',
  'How does the authentication system work?',
];

/**
 * EmptyState - Displayed when no messages exist
 */
const EmptyState: React.FC<{ onSuggestionClick?: (s: string) => void }> = ({
  onSuggestionClick,
}) => (
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
        {SUGGESTIONS.map((suggestion) => (
          <button
            key={suggestion}
            onClick={() => onSuggestionClick?.(suggestion)}
            className="block w-full text-left px-4 py-2.5 text-sm text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-750 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          >
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  </div>
);

/**
 * MessageList component with auto-scroll and manual scroll detection.
 */
const MessageList: React.FC<MessageListProps> = ({
  messages,
  onSuggestionClick,
  onGraphSourceClick,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [isUserScrolling, setIsUserScrolling] = useState(false);

  /** Scroll to the bottom of the message list */
  const scrollToBottom = useCallback(() => {
    if (!isUserScrolling) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [isUserScrolling]);

  /** Auto-scroll when messages change */
  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  /** Detect manual user scrolling */
  const handleScroll = useCallback(() => {
    const container = containerRef.current;
    if (!container) return;

    const { scrollTop, scrollHeight, clientHeight } = container;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
    setIsUserScrolling(!isAtBottom);
  }, []);

  /** Show scroll-to-bottom button when user scrolls up */
  const handleScrollToBottomClick = useCallback(() => {
    setIsUserScrolling(false);
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  if (messages.length === 0) {
    return (
      <div className="flex-1 overflow-y-auto p-4" data-testid="message-list-empty">
        <EmptyState onSuggestionClick={onSuggestionClick} />
      </div>
    );
  }

  return (
    <div className="relative flex-1 min-h-0">
      <div
        ref={containerRef}
        className="h-full chat-scroll p-4 space-y-4"
        onScroll={handleScroll}
        data-testid="message-list"
        role="log"
        aria-label="Chat messages"
        aria-live="polite"
      >
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} onGraphSourceClick={onGraphSourceClick} />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Scroll to bottom button */}
      {isUserScrolling && messages.length > 0 && (
        <button
          onClick={handleScrollToBottomClick}
          className="absolute bottom-4 left-1/2 -translate-x-1/2 inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-gray-800/80 dark:bg-gray-200/80 dark:text-gray-800 rounded-full shadow-lg hover:bg-gray-900/90 dark:hover:bg-gray-100/90 transition-colors backdrop-blur-sm z-10"
          aria-label="Scroll to latest message"
        >
          Scroll to bottom
        </button>
      )}
    </div>
  );
};

export default MessageList;
