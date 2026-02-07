/**
 * useStreamingSearch - Full POST-based SSE streaming lifecycle management hook
 *
 * Provides complete chat search functionality with:
 * - SSEPostClient-based streaming via fetch + ReadableStream (POST method)
 * - Conversation history sent in POST body for multi-turn chat
 * - JWT Authorization header included automatically
 * - Message state management (user + assistant messages)
 * - Stream cancellation via AbortController
 * - Source citations attached after stream completes
 * - Error state with dismissal
 * - Reconnection status feedback
 *
 * STORY-050 Migration (EventSource -> fetch + ReadableStream):
 * - Replaced EventSource (GET-only) with SSEPostClient (POST)
 * - Query, conversation_history, top_k sent via POST body
 * - Authorization header sent securely (not in URL)
 * - AbortController replaces EventSource.close()
 *
 * Implements STORY-043 Acceptance Criteria (preserved):
 * - AC1: Token-by-token display
 * - AC2: Incremental token append
 * - AC3: Source citations after [DONE]
 * - AC4: Auto-reconnect with 3 retries + exponential backoff
 * - AC5: User cancel/abort support
 *
 * Implements STORY-050 Acceptance Criteria:
 * - AC1: POST body with query, conversation_history, topK
 * - AC2: Backwards-compatible with useSearchChat wrapper
 * - AC3: Auto-reconnect with max 3 retries
 * - AC4: Token streaming with [DONE] completion
 * - AC5: EventSource code fully removed
 */
import { useState, useCallback, useRef, useEffect } from 'react';
import {
  SSEPostClient,
  getAuthToken,
  type SSESourceData,
  type SSERequestBody,
} from '@/shared/api/sse';
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

/** Configuration options for the useStreamingSearch hook */
export interface UseStreamingSearchOptions {
  /** Base URL for the SSE search endpoint (default: '/api/v1/search/chat/stream') */
  baseUrl?: string;
  /** Number of top results to retrieve (default: 5) */
  topK?: number;
  /** Search filters */
  filters?: {
    documentType?: string;
    projectName?: string;
    dateFrom?: string;
    dateTo?: string;
  };
}

/**
 * Converts SSESourceData to the Source type used by the UI.
 * Handles both camelCase (frontend) and snake_case (backend) field names.
 */
function mapSSESourcesToSources(sseSources: SSESourceData[]): Source[] {
  return sseSources.map((s) => ({
    chunkId: (s.chunkId ?? s.chunk_id ?? '') as string,
    documentId: (s.documentId ?? s.document_id ?? '') as string,
    content: (s.content ?? s.snippet ?? '') as string,
    score: (s.score ?? 0) as number,
    title: (s.title ?? '') as string,
    index: (s.index ?? 0) as number,
    sourceType: (s.sourceType ?? s.source_type ?? '') as string,
    metadata: s.metadata as Source['metadata'],
    graphContext: s.graphContext as Source['graphContext'],
  }));
}

/**
 * Generate a unique message ID with role prefix.
 */
function createMessageId(role: 'user' | 'assistant'): string {
  return `${role}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

/**
 * Build conversation history from existing messages for multi-turn chat.
 * Excludes the last user message (it's sent as the query).
 */
function buildConversationHistory(
  messages: Message[]
): Array<{ role: 'user' | 'assistant'; content: string }> {
  return messages
    .filter((msg) => msg.content && !msg.isStreaming)
    .map((msg) => ({
      role: msg.role,
      content: msg.content,
    }));
}

/**
 * Custom hook for managing POST-based SSE streaming chat search.
 *
 * @param optionsOrBaseUrl - Configuration options or legacy baseUrl string
 * @returns Streaming search state and actions
 */
export const useStreamingSearch = (
  optionsOrBaseUrl?: string | UseStreamingSearchOptions
): UseStreamingSearchReturn => {
  // Handle both legacy string parameter and new options object
  const options: UseStreamingSearchOptions =
    typeof optionsOrBaseUrl === 'string'
      ? { baseUrl: optionsOrBaseUrl }
      : optionsOrBaseUrl ?? {};

  const baseUrl = options.baseUrl ?? '/api/v1/search/chat/stream';
  const topK = options.topK ?? 5;
  const filters = options.filters;

  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reconnectInfo, setReconnectInfo] = useState<ReconnectInfo | null>(
    null
  );

  // Ref to hold the current SSEPostClient instance
  const clientRef = useRef<SSEPostClient | null>(null);
  // Ref to track the current assistant message ID during streaming
  const assistantIdRef = useRef<string | null>(null);

  // Cleanup SSEPostClient on unmount
  useEffect(() => {
    return () => {
      if (clientRef.current) {
        clientRef.current.abort();
        clientRef.current = null;
      }
    };
  }, []);

  /**
   * Send a message and start streaming the AI response via POST SSE.
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

      // Build conversation history from existing messages
      const conversationHistory = buildConversationHistory(messages);

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

      // Build the POST request body
      const requestBody: SSERequestBody = {
        query: text,
        conversation_history: conversationHistory,
        top_k: topK,
      };

      if (filters) {
        requestBody.filters = filters;
      }

      // Build authorization headers
      const headers: Record<string, string> = {};
      const token = getAuthToken();
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      // Create SSEPostClient with full lifecycle callbacks
      const client = new SSEPostClient(baseUrl, {
        body: requestBody,
        headers,

        onToken: (tokenText: string) => {
          setIsConnecting(false);
          setReconnectInfo(null);

          // Append token to the current assistant message
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantId
                ? { ...msg, content: msg.content + tokenText }
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
    [query, isStreaming, baseUrl, topK, filters, messages]
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
