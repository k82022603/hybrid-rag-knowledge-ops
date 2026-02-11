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
  title?: string;
  sourceType?: string;
  metadata: {
    documentType?: string;
    projectName?: string;
    title?: string;
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
  /** Whether this chunk has a computed embedding (SCRUM-97) */
  hasEmbedding?: boolean;
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
   * Keyword search (synchronous) - Hybrid 검색 (Vector + Keyword + Graph RRF 융합)
   */
  async search(params: SearchQuery): Promise<SearchResponse> {
    // Backend uses /search/hybrid with SearchRequest schema
    // Convert camelCase filter keys to snake_case for backend compatibility
    const filters = params.filters;
    const snakeFilters = filters ? {
      document_type: filters.documentType || undefined,
      project_name: filters.projectName || undefined,
      date_from: filters.dateFrom || undefined,
      date_to: filters.dateTo || undefined,
    } : null;

    const requestBody = {
      query: params.query,
      top_k: params.pageSize ?? 10,
      filters: snakeFilters,
      useGraph: true,
      useVector: true,
    };

    const response = await api.post('/search/hybrid', requestBody);
    const data = response.data;

    // Map backend snake_case response to frontend camelCase
    return {
      query: data.query,
      answer: data.answer,
      results: (data.results ?? []).map((r: Record<string, unknown>) => {
        const meta = (r.metadata ?? {}) as Record<string, unknown>;
        return {
          chunkId: r.chunk_id ?? r.chunkId ?? '',
          documentId: r.document_id ?? r.documentId ?? '',
          content: r.content ?? '',
          score: r.score ?? 0,
          title: meta.title as string | undefined,
          sourceType: (r.source_type ?? meta.search_source ?? r.sourceType) as string | undefined,
          metadata: {
            documentType: meta.document_type as string | undefined,
            projectName: meta.project_name as string | undefined,
            title: meta.title as string | undefined,
            summary: meta.summary as string | undefined,
          },
          graphContext: r.graph_context ?? r.graphContext ?? (
            (meta.matched_entities as string[] | undefined)?.length
              ? { relatedEntities: meta.matched_entities as string[], community: meta.community as string | undefined }
              : undefined
          ),
          hasEmbedding: r.has_embedding ?? r.hasEmbedding ?? true,
        };
      }),
      totalCount: data.total ?? data.totalCount ?? 0,
    };
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
   * Chat search (synchronous POST) - 비스트리밍 대화형 검색
   * POST /search/chat → JSON 응답 (answer + sources 포함)
   */
  async chatSearch(params: {
    query: string;
    conversationId?: string;
    topK?: number;
    conversationHistory?: Array<{ role: 'user' | 'assistant'; content: string }>;
  }): Promise<{
    answer: string;
    sources: Array<Record<string, unknown>>;
    conversationId: string;
    latencyMs?: number;
    turnCount?: number;
    pipelineStages?: Record<string, unknown>;
  }> {
    const requestBody = {
      query: params.query,
      conversationId: params.conversationId || undefined,
      topK: params.topK ?? 5,
      useReasoner: false,
    };

    const response = await api.post('/search/chat', requestBody);
    return response.data;
  },

  /**
   * Expert search
   */
  async findExperts(topic: string, depth = 2, limit = 5) {
    const response = await api.post('/graph/experts', { topic, depth, limit });
    return response.data;
  },

  /**
   * Get document download URL
   * Returns MinIO presigned URL for the original document
   */
  async getDocumentDownloadUrl(documentId: string): Promise<{ download_url: string; filename: string }> {
    const response = await api.get(`/documents/${documentId}/download`);
    return response.data;
  },
};

export default searchService;
