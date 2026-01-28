/**
 * useSearchChat - Chat search custom hook
 *
 * Manages chat message state, SSE streaming communication,
 * auto-scroll behavior, and error handling for the chat search feature.
 */
import { useState, useCallback, useRef, useEffect } from 'react';
import { searchService } from '@/services/searchService';
import type { Message } from '../types';

export interface UseSearchChatReturn {
  /** Current query input value */
  query: string;
  /** Set query input value */
  setQuery: (value: string) => void;
  /** List of chat messages */
  messages: Message[];
  /** Whether a search is in progress */
  isLoading: boolean;
  /** Current error message, if any */
  error: string | null;
  /** Submit the current query */
  handleSubmit: () => void;
  /** Clear the conversation */
  handleClear: () => void;
  /** Dismiss the error banner */
  dismissError: () => void;
}

/**
 * Custom hook for managing chat search state and SSE streaming.
 */
export const useSearchChat = (): UseSearchChatReturn => {
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  // Cleanup EventSource on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  /** Submit the current query for streaming search */
  const handleSubmit = useCallback(() => {
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

    // Create streaming assistant message placeholder
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
      // Start SSE streaming
      const eventSource = searchService.streamSearch(
        trimmedQuery,
        // onMessage - append streamed content
        (data: string) => {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantId
                ? { ...msg, content: msg.content + data }
                : msg
            )
          );
        },
        // onError - handle connection errors
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
        // onComplete - finalize the message
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
  }, [query, isLoading]);

  /** Clear all messages and reset state */
  const handleClear = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    setMessages([]);
    setError(null);
    setIsLoading(false);
  }, []);

  /** Dismiss error banner */
  const dismissError = useCallback(() => {
    setError(null);
  }, []);

  return {
    query,
    setQuery,
    messages,
    isLoading,
    error,
    handleSubmit,
    handleClear,
    dismissError,
  };
};

export default useSearchChat;
