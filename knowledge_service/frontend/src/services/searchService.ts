/**
 * SearchService - Search API service
 *
 * Provides search endpoints for:
 * - Keyword search (synchronous POST)
 * - Chat search (POST-based SSE streaming via SSEPostClient)
 * - Expert search
 *
 * STORY-050: Migrated streamSearch from EventSource (GET) to
 * SSEPostClient (POST) for secure, full-featured streaming.
 * The primary streaming interface is useStreamingSearch hook;
 * this service is kept for non-hook usage patterns.
 */
import api from './api';
import {
  SSEPostClient,
  getAuthToken,
  type SSEPostClientOptions,
  type SSERequestBody,
} from '@/shared/api/sse';

export interface SearchQuery {
  query: string;
  filters?: {
    documentType?: string;
    projectName?: string;
    dateFrom?: string;
    dateTo?: string;
  };
  page?: number;
  pageSize?: number;
}

export interface SearchResult {
  chunkId: string;
  documentId: string;
  content: string;
  score: number;
  metadata: {
    documentType?: string;
    projectName?: string;
    category?: {
      level1: string;
      level2: string;
      level3: string;
    };
    summary?: string;
  };
  graphContext?: {
    relatedEntities: string[];
    community: string;
  };
}

export interface SearchResponse {
  query: string;
  answer?: string;
  results: SearchResult[];
  totalCount: number;
}

/** Options for POST-based stream search */
export interface StreamSearchOptions {
  query: string;
  conversationHistory?: Array<{
    role: 'user' | 'assistant';
    content: string;
  }>;
  topK?: number;
  filters?: SearchQuery['filters'];
  onToken: (token: string) => void;
  onError: (error: Error) => void;
  onComplete: () => void;
}

/**
 * SearchService - Search API service
 */
export const searchService = {
  /**
   * Keyword search (synchronous)
   */
  async search(params: SearchQuery): Promise<SearchResponse> {
    const response = await api.post<SearchResponse>('/search', params);
    return response.data;
  },

  /**
   * Chat search (POST-based SSE streaming)
   *
   * Uses fetch + ReadableStream via SSEPostClient to support:
   * - POST method with JSON body
   * - Authorization header (JWT Bearer token)
   * - conversation_history for multi-turn chat
   * - AbortController-based cancellation
   *
   * @param options - Stream search configuration
   * @returns SSEPostClient instance (call .abort() to cancel)
   */
  streamSearch(options: StreamSearchOptions): SSEPostClient {
    const { query, conversationHistory, topK, filters, onToken, onError, onComplete } = options;

    // Build request body
    const body: SSERequestBody = {
      query,
      conversation_history: conversationHistory ?? [],
      top_k: topK ?? 5,
    };

    if (filters) {
      body.filters = filters;
    }

    // Build authorization headers
    const headers: Record<string, string> = {};
    const token = getAuthToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const clientOptions: SSEPostClientOptions = {
      body,
      headers,
      onToken,
      onComplete,
      onError: (sseError) => onError(sseError),
      maxRetries: 3,
      retryDelay: 1000,
    };

    const baseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1';
    const client = new SSEPostClient(
      `${baseUrl}/search/chat/stream`,
      clientOptions
    );
    client.connect();

    return client;
  },

  /**
   * Expert search
   */
  async findExperts(topic: string, depth = 2, limit = 5) {
    const response = await api.post('/graph/experts', { topic, depth, limit });
    return response.data;
  },
};

export default searchService;
