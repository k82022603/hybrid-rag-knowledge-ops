/**
 * 공통 타입 정의
 */

// 사용자 타입
export interface User {
  id: string;
  username: string;
  email: string;
  roles: string[];
}

// 페이지네이션 타입
export interface Pagination {
  page: number;
  pageSize: number;
  totalCount: number;
  totalPages: number;
}

// API 응답 타입
export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
  error?: string;
}

// 문서 타입
export interface Document {
  id: string;
  title: string;
  content: string;
  documentType: string;
  projectName: string;
  status: DocumentStatus;
  createdAt: string;
  updatedAt: string;
  metadata: DocumentMetadata;
}

export type DocumentStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface DocumentMetadata {
  author?: string;
  department?: string;
  tags?: string[];
  validStartDate?: string;
  validEndDate?: string;
}

// 검색 결과 타입
export interface SearchResult {
  chunkId: string;
  documentId: string;
  content: string;
  score: number;
  metadata: {
    documentType?: string;
    projectName?: string;
    category?: Category;
    summary?: string;
  };
  graphContext?: GraphContext;
}

export interface Category {
  level1: string;
  level2: string;
  level3: string;
}

export interface GraphContext {
  relatedEntities: string[];
  community: string;
}

// 채팅 메시지 타입
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  sources?: SearchResult[];
}

// 알림 타입
export interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
  duration?: number;
}
