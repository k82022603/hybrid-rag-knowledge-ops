import api from './api';

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

/**
 * SearchService - 검색 API 서비스
 */
export const searchService = {
  /**
   * 키워드 검색 (동기)
   */
  async search(params: SearchQuery): Promise<SearchResponse> {
    const response = await api.post<SearchResponse>('/search', params);
    return response.data;
  },

  /**
   * 채팅 검색 (SSE 스트리밍)
   *
   * @param query 검색 쿼리
   * @param onMessage 메시지 수신 콜백
   * @param onError 에러 콜백
   * @param onComplete 완료 콜백
   * @returns EventSource 인스턴스
   */
  streamSearch(
    query: string,
    onMessage: (data: string) => void,
    onError: (error: Event) => void,
    onComplete: () => void
  ): EventSource {
    const eventSource = new EventSource(
      `/api/v1/search/stream?query=${encodeURIComponent(query)}`
    );

    eventSource.onmessage = (event) => {
      if (event.data === '[DONE]') {
        eventSource.close();
        onComplete();
      } else {
        onMessage(event.data);
      }
    };

    eventSource.onerror = (error) => {
      eventSource.close();
      onError(error);
    };

    return eventSource;
  },

  /**
   * 전문가 검색
   */
  async findExperts(topic: string, depth = 2, limit = 5) {
    const response = await api.post('/graph/experts', { topic, depth, limit });
    return response.data;
  },
};

export default searchService;
