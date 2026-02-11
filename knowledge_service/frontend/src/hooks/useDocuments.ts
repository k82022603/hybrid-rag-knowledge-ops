import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  knowledgeService,
  type DocumentStatus,
  type DocumentFormat,
} from '@/services/knowledgeService';

/**
 * useDocuments - document list query hook
 *
 * Backend: GET /api/v1/documents?page=1&page_size=20&status=completed&format=pdf
 */
export const useDocuments = (
  page = 1,
  pageSize = 20,
  filters?: { status?: DocumentStatus; format?: DocumentFormat }
) => {
  return useQuery({
    queryKey: ['documents', page, pageSize, filters],
    queryFn: () => knowledgeService.getDocuments(page, pageSize, filters),
  });
};

/**
 * useDocumentStatus - document processing status query hook
 *
 * Backend: GET /api/v1/documents/{document_id}/status
 */
export const useDocumentStatus = (documentId: string, enabled = true) => {
  return useQuery({
    queryKey: ['document-status', documentId],
    queryFn: () => knowledgeService.getProcessingStatus(documentId),
    enabled: enabled && !!documentId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === 'completed' || status === 'failed') return false;
      return 3000; // poll every 3s while processing
    },
  });
};

/**
 * useUploadFile - file upload mutation hook
 *
 * Backend: POST /api/v1/documents/upload
 */
export const useUploadFile = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      file,
      metadata,
    }: {
      file: File;
      metadata?: { title?: string; project_name?: string; tags?: string[] };
    }) => knowledgeService.uploadFile(file, metadata),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });
};

/**
 * useRetryDocument - retry failed document mutation hook
 *
 * Backend: POST /api/v1/documents/{document_id}/retry
 */
export const useRetryDocument = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (documentId: string) => knowledgeService.retryDocument(documentId),
    onSuccess: (_, documentId) => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      queryClient.invalidateQueries({ queryKey: ['document-status', documentId] });
    },
  });
};

export default useDocuments;
