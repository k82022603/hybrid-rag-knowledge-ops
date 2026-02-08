/**
 * ChatInput - Text input with send button for chat search
 *
 * Features:
 * - Auto-resizing textarea
 * - Enter to send, Shift+Enter for new line
 * - Send button with loading state (Heroicons)
 * - Clear conversation button
 */
import React, { useRef, useCallback } from 'react';
import {
  PaperAirplaneIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';

export interface ChatInputProps {
  /** Current query value */
  value: string;
  /** Called when query value changes */
  onChange: (value: string) => void;
  /** Called when user submits (Enter or button click) */
  onSubmit: () => void;
  /** Called when user clicks clear */
  onClear?: () => void;
  /** Whether the search is currently in progress */
  isLoading?: boolean;
  /** Whether to show the clear button */
  showClear?: boolean;
  /** Placeholder text */
  placeholder?: string;
}

/**
 * ChatInput component for the chat search interface.
 */
const ChatInput: React.FC<ChatInputProps> = ({
  value,
  onChange,
  onSubmit,
  onClear,
  isLoading = false,
  showClear = false,
  placeholder = '질문을 입력하세요...',
}) => {
  const inputRef = useRef<HTMLTextAreaElement>(null);

  /** Handle Enter key press (submit on Enter, newline on Shift+Enter) */
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (value.trim() && !isLoading) {
          onSubmit();
        }
      }
    },
    [value, isLoading, onSubmit]
  );

  /** Handle form submit */
  const handleFormSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (value.trim() && !isLoading) {
        onSubmit();
      }
    },
    [value, isLoading, onSubmit]
  );

  return (
    <div className="border-t border-gray-200 dark:border-gray-700 p-4">
      <form onSubmit={handleFormSubmit} className="flex items-end gap-3">
        {/* Clear chat button */}
        {showClear && onClear && (
          <button
            type="button"
            onClick={onClear}
            className="flex-shrink-0 p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            title="대화 초기화"
            aria-label="대화 초기화"
          >
            <ArrowPathIcon className="h-5 w-5" />
          </button>
        )}

        {/* Textarea Input */}
        <div className="flex-1 relative">
          <textarea
            ref={inputRef}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={isLoading}
            rows={1}
            className="w-full px-4 py-2.5 text-sm rounded-xl border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 focus:bg-white dark:focus:bg-gray-800 resize-none disabled:opacity-50 transition-colors"
            style={{ maxHeight: '120px' }}
            aria-label="Search query"
            data-testid="chat-input"
          />
        </div>

        {/* Submit button */}
        <button
          type="submit"
          disabled={!value.trim() || isLoading}
          className="flex-shrink-0 p-2.5 rounded-xl bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          aria-label="Send message"
          data-testid="chat-submit"
        >
          {isLoading ? (
            <ArrowPathIcon className="h-5 w-5 animate-spin" />
          ) : (
            <PaperAirplaneIcon className="h-5 w-5" />
          )}
        </button>
      </form>
      <p className="mt-2 text-2xs text-gray-400 dark:text-gray-500 text-center">
        Hybrid RAG 기반 검색 - Enter로 전송, Shift+Enter로 줄바꿈
      </p>
    </div>
  );
};

export default ChatInput;
