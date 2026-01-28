/**
 * useStreamingSearch - Full SSE streaming lifecycle management hook
 *
 * Provides complete chat search functionality with:
 * - SSEClient-based streaming with retry/reconnect
 * - Message state management (user + assistant messages)
 * - Stream cancellation via abort button
 * - Source citations attached after stream completes
 * - Error state with dismissal
 * - Reconnection status feedback
 *
 * Implements STORY-043 Acceptance Criteria:
 * - AC1: Token-by-token display
 * - AC2: Incremental token append
 * - AC3: Source citations after [DONE]
 * - AC4: Auto-reconnect with 3 retries + exponential backoff
 * - AC5: User cancel/abort support
 */
import { useState, useCallback, useRef, useEffect } from 'react';
import { SSEClient, type SSESourceData } from '@/shared/api/sse';
import type { Message, Source } from '../types';

/** Return type for the useStreamingSearch hook */
export interface UseStreamingSearchReturn {
  /** Current query input value */
  query: string;
  /** Set query input value */
  setQuery: (value: string) => void;
  /** List of chat messages (user + assistant) */
  messages: Message[];
  /** Whether a streaming response is in progress */
  isStreaming: boolean;
  /** Whether the SSE connection is being established */
  isConnecting: boolean;
  /** Current error message, if any */
  error: string | null;
  /** Current reconnection attempt info, if reconnecting */
  reconnectInfo: ReconnectInfo | null;
  /** Send a message and start streaming response */
  sendMessage: (queryOverride?: string) => void;
  /** Cancel the current streaming response */
  cancelStream: () => void;
  /** Clear all messages and reset state */
  clearMessages: () => void;
  /** Dismiss the error banner */
  dismissError: () => void;
}

/** Reconnection attempt information */
export interface ReconnectInfo {
  attempt: number;
  maxRetries: number;
}

/**
 * Converts SSESourceData to the Source type used by the UI.
 */
function mapSSESourcesToSources(sseSources: SSESourceData[]): Source[] {
  return sseSources.map((s) => ({
    chunkId: s.chunkId,
    documentId: s.documentId,
    content: s.content,
    score: s.score,
    metadata: s.metadata,
    graphContext: s.graphContext,
  }));
}

/**
 * Generate a unique message ID with role prefix.
 */
function createMessageId(role: 'user' | 'assistant'): string {
  return `${role}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

/**
 * Custom hook for managing SSE-based streaming chat search.
 *
 * @param baseUrl - The base URL for SSE search endpoint (default: '/api/v1/search/stream')
 * @returns Streaming search state and actions
 */
export const useStreamingSearch = (
  baseUrl: string = '/api/v1/search/stream'
): UseStreamingSearchReturn => {
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reconnectInfo, setReconnectInfo] = useState<ReconnectInfo | null>(
    null
  );

  // Ref to hold the current SSEClient instance
  const clientRef = useRef<SSEClient | null>(null);
  // Ref to track the current assistant message ID during streaming
  const assistantIdRef = useRef<string | null>(null);

  // Cleanup SSEClient on unmount
  useEffect(() => {
    return () => {
      if (clientRef.current) {
        clientRef.current.abort();
        clientRef.current = null;
      }
    };
  }, []);

  /**
   * Send a message and start streaming the AI response.
   *
   * @param queryOverride - Optional query text (uses current query state if not provided)
   */
  const sendMessage = useCallback(
    (queryOverride?: string) => {
      const text = (queryOverride ?? query).trim();
      if (!text || isStreaming) return;

      // Reset state
      setError(null);
      setReconnectInfo(null);

      // Abort any existing stream
      if (clientRef.current) {
        clientRef.current.abort();
        clientRef.current = null;
      }

      // Create user message
      const userMessage: Message = {
        id: createMessageId('user'),
        role: 'user',
        content: text,
        timestamp: new Date(),
      };

      // Create assistant message placeholder
      const assistantId = createMessageId('assistant');
      assistantIdRef.current = assistantId;

      const assistantMessage: Message = {
        id: assistantId,
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        isStreaming: true,
      };

      setMessages((prev) => [...prev, userMessage, assistantMessage]);
      setQuery('');
      setIsStreaming(true);
      setIsConnecting(true);

      // Build the SSE URL
      const sseUrl = `${baseUrl}?query=${encodeURIComponent(text)}`;

      // Create SSE client with full lifecycle callbacks
      const client = new SSEClient(sseUrl, {
        onToken: (token: string) => {
          setIsConnecting(false);
          setReconnectInfo(null);

          // Append token to the current assistant message
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantId
                ? { ...msg, content: msg.content + token }
                : msg
            )
          );
        },

        onSources: (sseSources: SSESourceData[]) => {
          // Attach source citations to the assistant message
          const sources = mapSSESourcesToSources(sseSources);
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantId ? { ...msg, sources } : msg
            )
          );
        },

        onComplete: () => {
          // Finalize the assistant message
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantId ? { ...msg, isStreaming: false } : msg
            )
          );
          setIsStreaming(false);
          setIsConnecting(false);
          setReconnectInfo(null);
          assistantIdRef.current = null;
          clientRef.current = null;
        },

        onError: (sseError) => {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantId
                ? {
                    ...msg,
                    isStreaming: false,
                    content:
                      msg.content ||
                      'An error occurred while generating the response. Please try again.',
                  }
                : msg
            )
          );
          setIsStreaming(false);
          setIsConnecting(false);
          setReconnectInfo(null);
          setError(sseError.message);
          assistantIdRef.current = null;
          clientRef.current = null;
        },

        onReconnect: (attempt: number, maxRetries: number) => {
          setReconnectInfo({ attempt, maxRetries });
        },

        maxRetries: 3,
        retryDelay: 1000,
        maxRetryDelay: 10000,
      });

      clientRef.current = client;
      client.connect();
    },
    [query, isStreaming, baseUrl]
  );

  /**
   * Cancel the current streaming response.
   * The partial response is preserved with streaming flag cleared.
   */
  const cancelStream = useCallback(() => {
    if (clientRef.current) {
      clientRef.current.abort();
      clientRef.current = null;
    }

    const currentAssistantId = assistantIdRef.current;
    if (currentAssistantId) {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === currentAssistantId
            ? {
                ...msg,
                isStreaming: false,
                content: msg.content || 'Response cancelled by user.',
              }
            : msg
        )
      );
    }

    setIsStreaming(false);
    setIsConnecting(false);
    setReconnectInfo(null);
    assistantIdRef.current = null;
  }, []);

  /**
   * Clear all messages and reset the conversation state.
   */
  const clearMessages = useCallback(() => {
    if (clientRef.current) {
      clientRef.current.abort();
      clientRef.current = null;
    }

    setMessages([]);
    setError(null);
    setIsStreaming(false);
    setIsConnecting(false);
    setReconnectInfo(null);
    assistantIdRef.current = null;
  }, []);

  /**
   * Dismiss the current error message.
   */
  const dismissError = useCallback(() => {
    setError(null);
  }, []);

  return {
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
  };
};

export default useStreamingSearch;
