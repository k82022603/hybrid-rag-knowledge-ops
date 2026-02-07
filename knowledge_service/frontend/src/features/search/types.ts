/**
 * Search feature type definitions
 *
 * Defines Message, SearchResult, Source, and related types
 * for chat search and keyword search features.
 */

/** Chat message role */
export type MessageRole = 'user' | 'assistant';

/** Source document reference from AI response */
export interface Source {
  chunkId: string;
  documentId: string;
  content: string;
  score: number;
  /** Document title from backend (e.g., "기술 가이드라인") */
  title?: string;
  /** 1-based index matching [출처N] in LLM answer */
  index?: number;
  /** Search source type (e.g., "vector", "keyword", "graph") */
  sourceType?: string;
  metadata?: {
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

/** Chat message */
export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
  sources?: Source[];
  isStreaming?: boolean;
}

/** Keyword search result (alias of Source for clarity) */
export type SearchResultItem = Source;

/** Search filters */
export interface SearchFilters {
  documentType?: string;
  projectName?: string;
  dateFrom?: string;
  dateTo?: string;
}

/** Keyword search response */
export interface KeywordSearchResponse {
  query: string;
  answer?: string;
  results: SearchResultItem[];
  totalCount: number;
}

/** Search mode for tabbed navigation */
export type SearchMode = 'chat' | 'keyword';

/** Graph node from /graph/subgraph API */
export interface GraphNode {
  id: string;
  name?: string;
  label?: string;
  type: string;
  [key: string]: unknown;
}

/** Graph edge from /graph/subgraph API */
export interface GraphEdge {
  source: string;
  target: string;
  type: string;
  [key: string]: unknown;
}

/** Subgraph API response */
export interface SubgraphData {
  center: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  node_count: number;
}
