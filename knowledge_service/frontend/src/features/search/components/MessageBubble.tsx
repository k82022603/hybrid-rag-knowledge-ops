/**
 * MessageBubble - User/AI message bubble component
 *
 * Renders a single chat message with avatar, content, timestamp,
 * and optional source citations for AI responses.
 * Uses Tailwind CSS with dark mode support.
 *
 * Markdown plugins:
 * - remark-gfm: Tables, strikethrough, task lists, autolinks
 * - remark-breaks: Soft line breaks as <br>
 * - rehype-highlight: Code syntax highlighting
 */
import React, { useState, useCallback } from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github.css';
import {
  UserIcon,
  SparklesIcon,
  ClipboardDocumentIcon,
  CheckIcon,
} from '@heroicons/react/24/outline';
import type { Message, Source } from '../types';
import SourceCitation from './SourceCitation';

export interface MessageBubbleProps {
  /** The message to render */
  message: Message;
  /** Callback when a graph source is clicked for visualization */
  onGraphSourceClick?: (source: Source) => void;
}

/** Remark/Rehype plugin configuration (stable references) */
const remarkPlugins = [remarkGfm, remarkBreaks];
const rehypePlugins = [rehypeHighlight];

/**
 * MessageBubble component for chat search.
 * Displays user messages on the right and AI messages on the left.
 */
const MessageBubble: React.FC<MessageBubbleProps> = ({ message, onGraphSourceClick }) => {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);

  const handleCopyRaw = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const textarea = document.createElement('textarea');
      textarea.value = message.content;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [message.content]);

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
          className={`relative inline-block max-w-[80%] px-4 py-3 rounded-xl group ${
            isUser
              ? 'bg-primary-600 text-white rounded-tr-sm'
              : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-900 dark:text-white rounded-tl-sm'
          }`}
        >
          {isUser ? (
            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="text-sm prose prose-sm dark:prose-invert max-w-none prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5 prose-headings:my-2 prose-table:my-2 prose-th:px-2 prose-th:py-1 prose-td:px-2 prose-td:py-1 prose-pre:my-2 prose-pre:rounded-lg prose-code:text-xs">
              <Markdown remarkPlugins={remarkPlugins} rehypePlugins={rehypePlugins}>
                {message.content}
              </Markdown>
            </div>
          )}

          {/* Copy Raw button (AI messages only, visible on hover) */}
          {!isUser && !message.isStreaming && message.content && (
            <button
              onClick={handleCopyRaw}
              className="absolute top-2 right-2 p-1 rounded-md opacity-0 group-hover:opacity-100 transition-opacity bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-500 dark:text-gray-400"
              title={copied ? 'Copied!' : 'Copy raw markdown'}
              aria-label="Copy raw markdown"
            >
              {copied ? (
                <CheckIcon className="h-3.5 w-3.5 text-green-500" />
              ) : (
                <ClipboardDocumentIcon className="h-3.5 w-3.5" />
              )}
            </button>
          )}

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
          <SourceCitation sources={message.sources} onGraphSourceClick={onGraphSourceClick} />
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
