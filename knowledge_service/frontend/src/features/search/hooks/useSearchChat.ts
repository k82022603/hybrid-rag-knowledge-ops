/**
 * useSearchChat - Chat search custom hook (refactored for STORY-043)
 *
 * Wraps useStreamingSearch to provide backwards-compatible API
 * for components that use the original useSearchChat interface.
 *
 * The original raw EventSource logic has been replaced by SSEClient
 * via useStreamingSearch, which provides:
 * - Automatic retry with exponential backoff
 * - Abort/cancel support
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
