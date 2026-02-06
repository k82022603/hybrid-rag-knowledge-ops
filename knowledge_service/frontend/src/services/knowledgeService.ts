import api from './api';

export interface Document {
  id: string;
  title: string;
  content: string;
  documentType: string;
  projectName: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  createdAt: string;
  updatedAt: string;
  metadata: {
    author?: string;
    department?: string;
    tags?: string[];
  };
}

export interface UploadDocumentRequest {
  title: string;
  content: string;
  documentType: string;
  projectName: string;
  metadata?: {
    author?: string;
    department?: string;
    tags?: string[];
  };
}

export interface DocumentListResponse {
  documents: Document[];
  totalCount: number;
  page: number;
  pageSize: number;
}

/**
 * KnowledgeService - 지식 관리 API 서비스
 */
export const knowledgeService = {
  /**
   * 문서 목록 조회
   */
  async getDocuments(
    page = 1,
    pageSize = 10,
    filters?: { documentType?: string; projectName?: string }
  ): Promise<DocumentListResponse> {
    const response = await api.get<DocumentListResponse>('/documents', {
      params: { page, pageSize, ...filters },
    });
    return response.data;
  },

  /**
   * 문서 상세 조회
   */
  async getDocument(id: string): Promise<Document> {
    const response = await api.get<Document>(`/documents/${id}`);
    return response.data;
  },

  /**
   * 문서 업로드
   */
  async uploadDocument(data: UploadDocumentRequest): Promise<Document> {
    const response = await api.post<Document>('/documents', data);
    return response.data;
  },

  /**
   * 파일 업로드
   */
  async uploadFile(
    file: File,
    metadata?: { projectName?: string; documentType?: string }
  ): Promise<Document> {
    const formData = new FormData();
    formData.append('file', file);
    if (metadata) {
      formData.append('metadata', JSON.stringify(metadata));
    }

    const response = await api.post<Document>('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  /**
   * 문서 수정
   */
  async updateDocument(
    id: string,
    data: Partial<UploadDocumentRequest>
  ): Promise<Document> {
    const response = await api.put<Document>(`/documents/${id}`, data);
    return response.data;
  },

  /**
   * 문서 삭제
   */
  async deleteDocument(id: string): Promise<void> {
    await api.delete(`/documents/${id}`);
  },

  /**
   * 문서 처리 상태 조회
   */
  async getProcessingStatus(id: string): Promise<{ status: string; progress: number }> {
    const response = await api.get(`/documents/${id}/status`);
    return response.data;
  },

  /**
   * 실패 문서 재시도
   */
  async retryDocument(id: string): Promise<{ document_id: string; status: string; message: string }> {
    const response = await api.post(`/documents/${id}/retry`);
    return response.data;
  },

  /**
   * 문서 처리 상태 SSE 스트림 URL 생성
   *
   * EventSource에서 사용할 절대 URL을 반환합니다.
   * api 인스턴스의 baseURL을 활용하여 프록시/개발 환경 모두 대응합니다.
   */
  getProcessingStatusStreamUrl(id: string): string {
    return `/api/v1/documents/${id}/status/stream`;
  },
};

export default knowledgeService;
