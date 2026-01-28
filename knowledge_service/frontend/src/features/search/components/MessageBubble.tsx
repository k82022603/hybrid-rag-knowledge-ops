/**
 * MessageBubble - User/AI message bubble component
 *
 * Renders a single chat message with avatar, content, timestamp,
 * and optional source citations for AI responses.
 * Uses Tailwind CSS with dark mode support.
 */
import React from 'react';
import {
  UserIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline';
import type { Message } from '../types';
import SourceCitation from './SourceCitation';

export interface MessageBubbleProps {
  /** The message to render */
  message: Message;
}

/**
 * MessageBubble component for chat search.
 * Displays user messages on the right and AI messages on the left.
 */
const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
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
        aria-hidden="true"
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
            <span className="inline-flex items-center gap-1 mt-1" aria-label="Loading response">
              <span className="w-1.5 h-1.5 rounded-full bg-primary-400 animate-pulse" />
              <span className="w-1.5 h-1.5 rounded-full bg-primary-400 animate-pulse delay-75" />
              <span className="w-1.5 h-1.5 rounded-full bg-primary-400 animate-pulse delay-150" />
            </span>
          )}
        </div>

        {/* Source Citations */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <SourceCitation sources={message.sources} />
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

export default MessageBubble;
