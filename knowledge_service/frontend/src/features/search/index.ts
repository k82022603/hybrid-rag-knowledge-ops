/**
 * Search feature module exports
 *
 * Provides chat search and keyword search components,
 * sub-components, hooks, and type definitions.
 *
 * STORY-050: SSE protocol migrated from EventSource (GET) to
 * fetch + ReadableStream (POST) via SSEPostClient.
 */

// Page-level components
export { default as ChatSearch } from './ChatSearch';
export { default as KeywordSearch } from './KeywordSearch';

// Sub-components
export { default as MessageList } from './components/MessageList';
export { default as MessageBubble } from './components/MessageBubble';
export { default as ChatInput } from './components/ChatInput';
export { default as SourceCitation } from './components/SourceCitation';
export { default as SearchResultCard } from './components/SearchResultCard';
export { default as StreamingIndicator } from './components/StreamingIndicator';

// Hooks
export { useSearchChat } from './hooks/useSearchChat';
export { useKeywordSearch } from './hooks/useKeywordSearch';
export { useStreamingSearch } from './hooks/useStreamingSearch';

// Types
export type {
  Message,
  MessageRole,
  Source,
  SearchResultItem,
  SearchFilters,
  KeywordSearchResponse,
  SearchMode,
} from './types';

export type {
  UseStreamingSearchReturn,
  UseStreamingSearchOptions,
  ReconnectInfo,
} from './hooks/useStreamingSearch';
