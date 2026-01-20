import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  knowledgeService,
  UploadDocumentRequest,
} from '@/services/knowledgeService';

/**
 * useDocuments - 문서 목록 조회 훅
 */
export const useDocuments = (
  page = 1,
  pageSize = 10,
  filters?: { documentType?: string; projectName?: string }
) => {
  return useQuery({
    queryKey: ['documents', page, pageSize, filters],
    queryFn: () => knowledgeService.getDocuments(page, pageSize, filters),
  });
};

/**
 * useDocument - 문서 상세 조회 훅
 */
export const useDocument = (id: string, enabled = true) => {
  return useQuery({
    queryKey: ['document', id],
    queryFn: () => knowledgeService.getDocument(id),
    enabled: enabled && !!id,
  });
};

/**
 * useUploadDocument - 문서 업로드 훅
 */
export const useUploadDocument = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: UploadDocumentRequest) =>
      knowledgeService.uploadDocument(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });
};

/**
 * useUploadFile - 파일 업로드 훅
 */
export const useUploadFile = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      file,
      metadata,
    }: {
      file: File;
      metadata?: { projectName?: string; documentType?: string };
    }) => knowledgeService.uploadFile(file, metadata),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });
};

/**
 * useUpdateDocument - 문서 수정 훅
 */
export const useUpdateDocument = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: string;
      data: Partial<UploadDocumentRequest>;
    }) => knowledgeService.updateDocument(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      queryClient.invalidateQueries({ queryKey: ['document', variables.id] });
    },
  });
};

/**
 * useDeleteDocument - 문서 삭제 훅
 */
export const useDeleteDocument = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => knowledgeService.deleteDocument(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });
};

export default useDocuments;
