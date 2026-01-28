/**
 * useSearchChat - Chat search custom hook (refactored for STORY-043, updated for STORY-050)
 *
 * Wraps useStreamingSearch to provide backwards-compatible API
 * for components that use the original useSearchChat interface.
 *
 * STORY-050: The underlying SSE transport has been migrated from
 * EventSource (GET) to fetch + ReadableStream (POST) via SSEPostClient.
 * This wrapper's interface remains unchanged for backwards compatibility.
 *
 * Features (via useStreamingSearch -> SSEPostClient):
 * - POST-based SSE with conversation_history support
 * - JWT Authorization header (not in URL)
 * - Automatic retry with exponential backoff
 * - Abort/cancel support via AbortController
 * - Source citation delivery after [DONE]
 */
import { useStreamingSearch } from './useStreamingSearch';

export interface UseSearchChatReturn {
  /** Current query input value */
  query: string;
  /** Set query input value */
  setQuery: (value: string) => void;
  /** List of chat messages */
  messages: import('../types').Message[];
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
 *
 * This is a backwards-compatible wrapper around useStreamingSearch.
 * New components should prefer useStreamingSearch directly for
 * access to cancel, reconnect info, and connecting state.
 */
export const useSearchChat = (): UseSearchChatReturn => {
  const {
    query,
    setQuery,
    messages,
    isStreaming,
    error,
    sendMessage,
    clearMessages,
    dismissError,
  } = useStreamingSearch();

  return {
    query,
    setQuery,
    messages,
    isLoading: isStreaming,
    error,
    handleSubmit: () => sendMessage(),
    handleClear: clearMessages,
    dismissError,
  };
};

export default useSearchChat;
