import api from './api';

/**
 * Backend DocumentStatus enum values
 * Matches: queued, processing, parsing, chunking, embedding, storing, extracting, completed, failed
 */
export type DocumentStatus =
  | 'queued'
  | 'processing'
  | 'parsing'
  | 'chunking'
  | 'embedding'
  | 'storing'
  | 'extracting'
  | 'completed'
  | 'failed';

/**
 * Backend DocumentFormat enum values
 */
export type DocumentFormat =
  | 'pdf'
  | 'docx'
  | 'hwp'
  | 'pptx'
  | 'md'
  | 'txt'
  | 'log'
  | 'html'
  | 'svg'
  | 'ipynb';

/**
 * DocumentListItem - matches backend DocumentListItem model
 * GET /api/v1/documents response item
 */
export interface DocumentListItem {
  document_id: string;
  filename: string;
  format: DocumentFormat;
  size_bytes: number;
  status: DocumentStatus;
  created_at: string;
}

/**
 * DocumentListResponse - matches backend DocumentListResponse model
 * GET /api/v1/documents response
 */
export interface DocumentListResponse {
  documents: DocumentListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

/**
 * DocumentResponse - matches backend DocumentResponse model
 * POST /api/v1/documents/upload response
 */
export interface DocumentUploadResponse {
  document_id: string;
  filename: string;
  format: DocumentFormat;
  size_bytes: number;
  status: DocumentStatus;
  status_url: string;
  created_at: string;
  metadata: {
    title?: string;
    description?: string;
    tags?: string[];
    project_name?: string;
  } | null;
}

/**
 * DocumentStatusResponse - matches backend DocumentStatusResponse model
 * GET /api/v1/documents/{id}/status response
 */
export interface DocumentStatusResponse {
  document_id: string;
  status: DocumentStatus;
  progress_percent: number;
  error_message: string | null;
  updated_at: string;
}

/**
 * KnowledgeService - AI Service Document API
 *
 * All document endpoints route through Gateway to AI Service (FastAPI)
 * Path prefix: /api/v1/documents
 */
export const knowledgeService = {
  /**
   * List documents (paginated)
   *
   * Backend: GET /api/v1/documents?page=1&page_size=20&status=completed&format=pdf
   */
  async getDocuments(
    page = 1,
    pageSize = 20,
    filters?: { status?: DocumentStatus; format?: DocumentFormat }
  ): Promise<DocumentListResponse> {
    const params: Record<string, string | number> = {
      page,
      page_size: pageSize,
    };
    if (filters?.status) params.status = filters.status;
    if (filters?.format) params.format = filters.format;

    const response = await api.get<DocumentListResponse>('/documents', { params });
    return response.data;
  },

  /**
   * Get document processing status
   *
   * Backend: GET /api/v1/documents/{document_id}/status
   */
  async getProcessingStatus(documentId: string): Promise<DocumentStatusResponse> {
    const response = await api.get<DocumentStatusResponse>(
      `/documents/${documentId}/status`
    );
    return response.data;
  },

  /**
   * Upload a file
   *
   * Backend: POST /api/v1/documents/upload
   * - file: UploadFile (multipart)
   * - metadata: optional JSON string form field
   */
  async uploadFile(
    file: File,
    metadata?: { title?: string; project_name?: string; tags?: string[] }
  ): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    if (metadata) {
      formData.append('metadata', JSON.stringify(metadata));
    }

    const response = await api.post<DocumentUploadResponse>(
      '/documents/upload',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  },

  /**
   * Trigger document processing
   *
   * Backend: POST /api/v1/documents/{document_id}/process
   */
  async processDocument(
    documentId: string
  ): Promise<{ document_id: string; status: string; message: string; status_url: string }> {
    const response = await api.post(`/documents/${documentId}/process`);
    return response.data;
  },

  /**
   * Retry failed document processing
   *
   * Backend: POST /api/v1/documents/{document_id}/retry
   */
  async retryDocument(
    documentId: string
  ): Promise<{
    document_id: string;
    status: string;
    message: string;
    previous_status: string;
    status_url: string;
  }> {
    const response = await api.post(`/documents/${documentId}/retry`);
    return response.data;
  },

  /**
   * Process all pending documents
   *
   * Backend: POST /api/v1/documents/process-pending?batch_size=5
   */
  async processPending(
    batchSize = 5
  ): Promise<{
    count: number;
    status: string;
    message: string;
    document_ids?: string[];
  }> {
    const response = await api.post('/documents/process-pending', null, {
      params: { batch_size: batchSize },
    });
    return response.data;
  },

  /**
   * Download document (returns redirect URL)
   *
   * Backend: GET /api/v1/documents/{document_id}/download
   */
  getDownloadUrl(documentId: string): string {
    const baseURL = api.defaults.baseURL || '/api/v1';
    return `${baseURL}/documents/${documentId}/download`;
  },

  /**
   * SSE stream URL for processing status
   *
   * Backend: GET /api/v1/documents/{document_id}/status/stream
   * Used with EventSource directly (not axios)
   */
  getProcessingStatusStreamUrl(documentId: string): string {
    return `/api/v1/documents/${documentId}/status/stream`;
  },
};

export default knowledgeService;
