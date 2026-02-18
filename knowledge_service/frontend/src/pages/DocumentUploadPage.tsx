/**
 * DocumentUploadPage - 문서 업로드 페이지
 *
 * 드래그 앤 드롭 파일 업로드, 메타데이터 입력,
 * 업로드 진행률 표시, 업로드 이력 표시
 */
import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  CloudArrowUpIcon,
  DocumentTextIcon,
  XMarkIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  ArrowPathIcon,
  PlusIcon,
  ExclamationTriangleIcon,
  DocumentArrowUpIcon,
} from '@heroicons/react/24/outline';
import { knowledgeService, type DocumentListItem } from '@/services/knowledgeService';

/**
 * 지원 파일 형식
 */
const SUPPORTED_FORMATS = [
  { ext: '.pdf', label: 'PDF', mime: 'application/pdf' },
  { ext: '.docx', label: 'DOCX', mime: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' },
  { ext: '.pptx', label: 'PPTX', mime: 'application/vnd.openxmlformats-officedocument.presentationml.presentation' },
  { ext: '.hwp', label: 'HWP', mime: 'application/x-hwp' },
  { ext: '.md', label: 'Markdown', mime: 'text/markdown' },
  { ext: '.txt', label: 'Text', mime: 'text/plain' },
  { ext: '.html', label: 'HTML', mime: 'text/html' },
];

const ACCEPTED_TYPES = SUPPORTED_FORMATS.map((f) => f.mime).join(',');
const MAX_FILE_SIZE_MB = 2048; // 2GB
const MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024;

/**
 * 문서 처리 상태
 */
type ProcessingStatus = 'queued' | 'processing' | 'completed' | 'failed';

/**
 * 파일 상태 인터페이스
 */
interface UploadFile {
  id: string;
  file: File;
  title: string;
  category: string;
  tags: string[];
  progress: number;
  status: 'pending' | 'uploading' | 'completed' | 'failed';
  error?: string;
  /** Server-assigned document ID after upload */
  documentId?: string;
  /** Backend processing status after upload completes */
  processingStatus?: ProcessingStatus;
}

/**
 * Maximum number of polling attempts (5-second interval x 60 = 5 minutes)
 */
const MAX_POLL_ATTEMPTS = 60;
const POLL_INTERVAL_MS = 5000;

/**
 * 파일 사이즈 포맷
 */
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
};

/**
 * 파일 확장자 가져오기
 */
const getFileExtension = (filename: string): string => {
  return filename.slice(filename.lastIndexOf('.')).toLowerCase();
};

/**
 * FileDropzone - 드래그 앤 드롭 영역
 */
const FileDropzone: React.FC<{
  onFilesSelected: (files: File[]) => void;
  disabled?: boolean;
}> = ({ onFilesSelected, disabled }) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateFiles = useCallback((files: File[]): File[] => {
    return files.filter((file) => {
      const ext = getFileExtension(file.name);
      const isSupported = SUPPORTED_FORMATS.some((f) => f.ext === ext);
      const isValidSize = file.size <= MAX_FILE_SIZE;

      if (!isSupported) {
        console.warn(`Unsupported file format: ${file.name}`);
        return false;
      }
      if (!isValidSize) {
        console.warn(`File too large: ${file.name} (${formatFileSize(file.size)})`);
        return false;
      }
      return true;
    });
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled) setIsDragOver(true);
  }, [disabled]);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      if (disabled) return;

      const files = Array.from(e.dataTransfer.files);
      const validFiles = validateFiles(files);
      if (validFiles.length > 0) {
        onFilesSelected(validFiles);
      }
    },
    [disabled, onFilesSelected, validateFiles]
  );

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(e.target.files || []);
      const validFiles = validateFiles(files);
      if (validFiles.length > 0) {
        onFilesSelected(validFiles);
      }
      // Reset input so the same file can be selected again
      if (inputRef.current) {
        inputRef.current.value = '';
      }
    },
    [onFilesSelected, validateFiles]
  );

  return (
    <div
      className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
        isDragOver
          ? 'border-primary-400 bg-primary-50 dark:bg-primary-900/20'
          : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
      } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={() => !disabled && inputRef.current?.click()}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if ((e.key === 'Enter' || e.key === ' ') && !disabled) {
          inputRef.current?.click();
        }
      }}
      aria-label="Drop files here or click to browse"
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={ACCEPTED_TYPES}
        onChange={handleInputChange}
        className="hidden"
        aria-hidden="true"
      />

      <CloudArrowUpIcon
        className={`h-12 w-12 mx-auto mb-4 ${
          isDragOver ? 'text-primary-500' : 'text-gray-400 dark:text-gray-500'
        }`}
      />

      <p className="text-sm font-medium text-gray-900 dark:text-white mb-1">
        {isDragOver ? 'Drop files here' : 'Drag and drop files, or click to browse'}
      </p>
      <p className="text-xs text-gray-500 dark:text-gray-400">
        Supported formats: {SUPPORTED_FORMATS.map((f) => f.label).join(', ')}
      </p>
      <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
        Maximum file size: {MAX_FILE_SIZE_MB}MB
      </p>
    </div>
  );
};

/**
 * UploadFileItem - 업로드 파일 항목
 */
const UploadFileItem: React.FC<{
  uploadFile: UploadFile;
  onRemove: (id: string) => void;
  onRetry: (id: string) => void;
  onUpdateTitle: (id: string, title: string) => void;
  onUpdateCategory: (id: string, category: string) => void;
  onAddTag: (id: string, tag: string) => void;
  onRemoveTag: (id: string, tag: string) => void;
}> = ({ uploadFile, onRemove, onRetry, onUpdateTitle, onUpdateCategory, onAddTag, onRemoveTag }) => {
  const [tagInput, setTagInput] = useState('');

  const handleAddTag = () => {
    const tag = tagInput.trim();
    if (tag && !uploadFile.tags.includes(tag)) {
      onAddTag(uploadFile.id, tag);
      setTagInput('');
    }
  };

  const handleTagKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddTag();
    }
  };

  const statusIcon = () => {
    // Processing states take priority when upload is done
    if (uploadFile.status === 'completed' && uploadFile.processingStatus) {
      switch (uploadFile.processingStatus) {
        case 'queued':
          return (
            <span className="inline-flex items-center justify-center h-5 w-5 rounded-full bg-warning-100 dark:bg-warning-900/40">
              <span className="h-2 w-2 rounded-full bg-warning-500" />
            </span>
          );
        case 'processing':
          return <ArrowPathIcon className="h-5 w-5 text-primary-500 animate-spin" />;
        case 'completed':
          return <CheckCircleIcon className="h-5 w-5 text-success-500" />;
        case 'failed':
          return <ExclamationCircleIcon className="h-5 w-5 text-error-500" />;
      }
    }

    switch (uploadFile.status) {
      case 'completed':
        return <CheckCircleIcon className="h-5 w-5 text-success-500" />;
      case 'failed':
        return <ExclamationCircleIcon className="h-5 w-5 text-error-500" />;
      case 'uploading':
        return <ArrowPathIcon className="h-5 w-5 text-primary-500 animate-spin" />;
      default:
        return <DocumentTextIcon className="h-5 w-5 text-gray-400" />;
    }
  };

  /**
   * Determine the label text for the current processing/upload status
   */
  const getProgressLabel = (): string => {
    if (uploadFile.status === 'uploading') {
      return `Uploading... ${uploadFile.progress}%`;
    }
    if (uploadFile.status === 'completed' && uploadFile.processingStatus) {
      switch (uploadFile.processingStatus) {
        case 'queued':
          return 'Queued for processing...';
        case 'processing':
          return `Processing document... ${uploadFile.progress}%`;
        case 'completed':
          return 'Ready for search';
        case 'failed':
          return 'Processing failed';
      }
    }
    if (uploadFile.status === 'completed') {
      return 'Completed';
    }
    return '';
  };

  /**
   * Determine the progress bar color class
   */
  const getProgressBarColor = (): string => {
    if (uploadFile.status === 'uploading') return 'bg-primary-500';
    if (uploadFile.processingStatus === 'queued') return 'bg-warning-400';
    if (uploadFile.processingStatus === 'processing') return 'bg-primary-500';
    if (uploadFile.processingStatus === 'completed') return 'bg-success-500';
    if (uploadFile.processingStatus === 'failed') return 'bg-error-500';
    return 'bg-success-500';
  };

  const isEditable = uploadFile.status === 'pending';

  return (
    <div
      className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5"
      data-testid={`upload-file-${uploadFile.id}`}
    >
      {/* File info header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          {statusIcon()}
          <div>
            <p className="text-sm font-medium text-gray-900 dark:text-white">{uploadFile.file.name}</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {formatFileSize(uploadFile.file.size)} &middot; {getFileExtension(uploadFile.file.name).replace('.', '').toUpperCase()}
            </p>
          </div>
        </div>
        {isEditable && (
          <button
            onClick={() => onRemove(uploadFile.id)}
            className="p-1.5 rounded-lg hover:bg-error-50 dark:hover:bg-error-900/30 text-gray-400 hover:text-error-500 transition-colors"
            aria-label={`Remove ${uploadFile.file.name}`}
          >
            <XMarkIcon className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Progress bar - 2-stage: Upload (0-50%) then Processing (50-100%) */}
      {(uploadFile.status === 'uploading' || uploadFile.status === 'completed') && (
        <div className="mb-4">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {getProgressLabel()}
            </span>
            {/* Processing status badge */}
            {uploadFile.processingStatus && uploadFile.processingStatus !== 'completed' && uploadFile.processingStatus !== 'failed' && (
              <span
                className={`inline-flex items-center px-2 py-0.5 rounded-full text-2xs font-medium ${
                  uploadFile.processingStatus === 'queued'
                    ? 'bg-warning-50 text-warning-700 dark:bg-warning-900/30 dark:text-warning-400'
                    : 'bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400'
                }`}
              >
                {uploadFile.processingStatus === 'queued' ? 'Queued' : 'Processing'}
              </span>
            )}
            {uploadFile.processingStatus === 'completed' && (
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-2xs font-medium bg-success-50 text-success-700 dark:bg-success-900/30 dark:text-success-400">
                Ready
              </span>
            )}
          </div>
          {/* 2-stage progress bar */}
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5 overflow-hidden">
            <div
              className={`h-1.5 rounded-full transition-all duration-500 ${getProgressBarColor()}`}
              style={{ width: `${uploadFile.progress}%` }}
              role="progressbar"
              aria-valuenow={uploadFile.progress}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={getProgressLabel()}
            />
          </div>
          {/* Stage labels */}
          {uploadFile.processingStatus && uploadFile.processingStatus !== 'completed' && (
            <div className="flex justify-between mt-1">
              <span className="text-2xs text-gray-400">Upload</span>
              <span className="text-2xs text-gray-400">Processing</span>
            </div>
          )}
        </div>
      )}

      {/* Error message - upload failure or processing failure */}
      {((uploadFile.status === 'failed' && uploadFile.error) ||
        (uploadFile.processingStatus === 'failed' && uploadFile.error)) && (
        <div className="flex items-center gap-2 p-2 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg mb-4" role="alert">
          <ExclamationTriangleIcon className="h-4 w-4 text-error-500 flex-shrink-0" />
          <span className="text-xs text-error-700 dark:text-error-300 flex-1">{uploadFile.error}</span>
          {/* Retry button for failed processing */}
          {uploadFile.processingStatus === 'failed' && uploadFile.documentId && (
            <button
              onClick={() => onRetry(uploadFile.id)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 transition-colors"
            >
              <ArrowPathIcon className="h-3.5 w-3.5" />
              Retry
            </button>
          )}
        </div>
      )}

      {/* Metadata form (only when pending) */}
      {isEditable && (
        <div className="space-y-3 pt-3 border-t border-gray-100 dark:border-gray-700">
          {/* Title */}
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              제목
            </label>
            <input
              type="text"
              value={uploadFile.title}
              onChange={(e) => onUpdateTitle(uploadFile.id, e.target.value)}
              placeholder="문서 제목 (선택사항)"
              className="w-full px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
            />
          </div>

          {/* Category */}
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              카테고리
            </label>
            <select
              value={uploadFile.category}
              onChange={(e) => onUpdateCategory(uploadFile.id, e.target.value)}
              className="w-full px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
            >
              <option value="">카테고리 선택</option>
              <option value="technical">기술 문서</option>
              <option value="guide">가이드 / 매뉴얼</option>
              <option value="policy">정책 / 규정</option>
              <option value="report">보고서</option>
              <option value="meeting">회의록</option>
              <option value="other">기타</option>
            </select>
          </div>

          {/* Tags */}
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              태그
            </label>
            <div className="flex flex-wrap gap-1.5 mb-2">
              {uploadFile.tags.map((tag) => (
                <span
                  key={tag}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-primary-100 text-primary-800 dark:bg-primary-900 dark:text-primary-200"
                >
                  {tag}
                  <button
                    onClick={() => onRemoveTag(uploadFile.id, tag)}
                    className="hover:text-primary-600 dark:hover:text-primary-100"
                    aria-label={`Remove tag ${tag}`}
                  >
                    <XMarkIcon className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyDown={handleTagKeyDown}
                placeholder="태그 추가..."
                className="flex-1 px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
              />
              <button
                type="button"
                onClick={handleAddTag}
                disabled={!tagInput.trim()}
                className="px-3 py-1.5 text-sm font-medium text-primary-600 hover:text-primary-700 disabled:text-gray-400 transition-colors"
              >
                <PlusIcon className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

/**
 * UploadHistory - 최근 업로드 이력
 */
const UploadHistory: React.FC = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['documents', { page: 1, pageSize: 10 }],
    queryFn: () => knowledgeService.getDocuments(1, 10),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <ArrowPathIcon className="h-5 w-5 text-primary-500 animate-spin" />
      </div>
    );
  }

  const documents = data?.documents ?? [];

  if (documents.length === 0) {
    return (
      <div className="text-center py-8">
        <DocumentArrowUpIcon className="h-8 w-8 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
        <p className="text-sm text-gray-500 dark:text-gray-400">No documents uploaded yet.</p>
      </div>
    );
  }

  const statusBadge = (status: string) => {
    const classes: Record<string, string> = {
      completed: 'bg-success-50 text-success-700 dark:bg-success-900/30 dark:text-success-400',
      processing: 'bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400',
      queued: 'bg-warning-50 text-warning-700 dark:bg-warning-900/30 dark:text-warning-400',
      failed: 'bg-error-50 text-error-700 dark:bg-error-900/30 dark:text-error-400',
    };
    return (
      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-2xs font-medium ${classes[status] || classes.queued}`}>
        {status}
      </span>
    );
  };

  return (
    <div className="space-y-2">
      {documents.map((doc: DocumentListItem) => (
        <div
          key={doc.document_id}
          className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors"
        >
          <DocumentTextIcon className="h-5 w-5 text-gray-400 flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{doc.filename}</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {doc.format.toUpperCase()} &middot; {new Date(doc.created_at).toLocaleDateString('ko-KR')}
            </p>
          </div>
          {statusBadge(doc.status)}
        </div>
      ))}
    </div>
  );
};

/**
 * DocumentUploadPage 메인 컴포넌트
 */
const DocumentUploadPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [files, setFiles] = useState<UploadFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  const handleFilesSelected = useCallback((newFiles: File[]) => {
    const uploadFiles: UploadFile[] = newFiles.map((file) => ({
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      file,
      title: file.name.replace(/\.[^/.]+$/, ''),
      category: '',
      tags: [],
      progress: 0,
      status: 'pending' as const,
    }));
    setFiles((prev) => [...prev, ...uploadFiles]);
  }, []);

  const handleRemoveFile = useCallback((id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  }, []);

  const handleUpdateTitle = useCallback((id: string, title: string) => {
    setFiles((prev) => prev.map((f) => (f.id === id ? { ...f, title } : f)));
  }, []);

  const handleUpdateCategory = useCallback((id: string, category: string) => {
    setFiles((prev) => prev.map((f) => (f.id === id ? { ...f, category } : f)));
  }, []);

  const handleAddTag = useCallback((id: string, tag: string) => {
    setFiles((prev) =>
      prev.map((f) => (f.id === id ? { ...f, tags: [...f.tags, tag] } : f))
    );
  }, []);

  const handleRemoveTag = useCallback((id: string, tag: string) => {
    setFiles((prev) =>
      prev.map((f) => (f.id === id ? { ...f, tags: f.tags.filter((t) => t !== tag) } : f))
    );
  }, []);

  const handleRetry = useCallback(async (id: string) => {
    const file = files.find((f) => f.id === id);
    if (!file?.documentId) return;

    try {
      await knowledgeService.retryDocument(file.documentId);
      setFiles((prev) =>
        prev.map((f) =>
          f.id === id
            ? { ...f, processingStatus: 'processing' as ProcessingStatus, progress: 50, error: undefined }
            : f
        )
      );
    } catch (error) {
      console.error('Retry failed:', error);
    }
  }, [files]);

  const handleUploadAll = useCallback(async () => {
    const pendingFiles = files.filter((f) => f.status === 'pending');
    if (pendingFiles.length === 0) return;

    setIsUploading(true);

    for (const uploadFile of pendingFiles) {
      // Set uploading status
      setFiles((prev) =>
        prev.map((f) => (f.id === uploadFile.id ? { ...f, status: 'uploading' as const, progress: 0 } : f))
      );

      try {
        // Simulate upload progress updates (0% to 45%)
        const progressInterval = setInterval(() => {
          setFiles((prev) =>
            prev.map((f) =>
              f.id === uploadFile.id && f.status === 'uploading'
                ? { ...f, progress: Math.min(f.progress + 5, 45) }
                : f
            )
          );
        }, 200);

        const uploadedDoc = await knowledgeService.uploadFile(uploadFile.file, {
          title: uploadFile.title || undefined,
          project_name: uploadFile.category || undefined,
          tags: uploadFile.tags.length > 0 ? uploadFile.tags : undefined,
        });

        clearInterval(progressInterval);

        // Upload complete -> transition to processing phase
        // Progress 50% = upload done, 50-100% = processing
        setFiles((prev) =>
          prev.map((f) =>
            f.id === uploadFile.id
              ? {
                  ...f,
                  status: 'completed' as const,
                  progress: 50,
                  documentId: uploadedDoc.document_id,
                  processingStatus: 'processing' as ProcessingStatus,
                }
              : f
          )
        );
      } catch (error) {
        // Set failed
        setFiles((prev) =>
          prev.map((f) =>
            f.id === uploadFile.id
              ? {
                  ...f,
                  status: 'failed' as const,
                  error: error instanceof Error ? error.message : 'Upload failed',
                }
              : f
          )
        );
      }
    }

    setIsUploading(false);
    queryClient.invalidateQueries({ queryKey: ['documents'] });
  }, [files, queryClient]);

  /**
   * SSE-based processing status streaming.
   * Opens an EventSource per processing file for real-time updates.
   * Falls back to REST polling if SSE connection fails.
   *
   * SSE events:
   *   - status: periodic progress update
   *   - done: terminal state (completed/failed)
   *   - error: document not found
   *   - timeout: server-side 5-minute timeout
   */
  const sseActiveRef = useRef<Set<string>>(new Set());
  const sseFailedRef = useRef<Set<string>>(new Set());
  const pollCountRef = useRef<Record<string, number>>({});

  // Primary: SSE streaming
  useEffect(() => {
    const eventSources: Map<string, EventSource> = new Map();

    // SSE 연결이 필요한 파일들 (업로드 완료 + processing 중 + SSE 미연결 + SSE 미실패)
    const processingFiles = files.filter(
      (f) =>
        f.status === 'completed' &&
        f.documentId &&
        f.processingStatus &&
        !['completed', 'failed'].includes(f.processingStatus) &&
        !sseActiveRef.current.has(f.id) &&
        !sseFailedRef.current.has(f.id)
    );

    for (const file of processingFiles) {
      if (!file.documentId || eventSources.has(file.id)) continue;

      const url = knowledgeService.getProcessingStatusStreamUrl(file.documentId);
      const es = new EventSource(url);
      eventSources.set(file.id, es);
      sseActiveRef.current.add(file.id);

      es.addEventListener('status', (event) => {
        try {
          const data = JSON.parse(event.data);
          setFiles((prev) =>
            prev.map((f) =>
              f.id === file.id
                ? {
                    ...f,
                    processingStatus: data.status as ProcessingStatus,
                    progress:
                      data.status === 'completed'
                        ? 100
                        : Math.max(f.progress, 50 + Math.floor((data.progress_percent || 0) / 2)),
                  }
                : f
            )
          );
        } catch (e) {
          console.warn('SSE parse error:', e);
        }
      });

      es.addEventListener('done', (event) => {
        try {
          const data = JSON.parse(event.data);
          setFiles((prev) =>
            prev.map((f) =>
              f.id === file.id
                ? {
                    ...f,
                    processingStatus: data.final_status as ProcessingStatus,
                    progress: data.final_status === 'completed' ? 100 : f.progress,
                  }
                : f
            )
          );
        } catch (e) {
          console.warn('SSE done parse error:', e);
        }
        es.close();
        eventSources.delete(file.id);
        sseActiveRef.current.delete(file.id);
      });

      es.addEventListener('error', () => {
        // SSE 연결 실패 시 정리 → REST 폴링 fallback으로 전환
        es.close();
        eventSources.delete(file.id);
        sseActiveRef.current.delete(file.id);
        sseFailedRef.current.add(file.id);
        // 상태 업데이트로 폴링 effect 재평가 트리거
        setFiles((prev) => [...prev]);
      });

      es.addEventListener('timeout', () => {
        setFiles((prev) =>
          prev.map((f) =>
            f.id === file.id
              ? { ...f, processingStatus: 'failed' as ProcessingStatus, error: 'Processing timed out' }
              : f
          )
        );
        es.close();
        eventSources.delete(file.id);
        sseActiveRef.current.delete(file.id);
      });
    }

    return () => {
      eventSources.forEach((es, fileId) => {
        es.close();
        sseActiveRef.current.delete(fileId);
      });
      eventSources.clear();
    };
  }, [files]);

  // Fallback: REST polling (only for files without active SSE connection)
  useEffect(() => {
    const processingFiles = files.filter(
      (f) =>
        f.documentId &&
        f.processingStatus &&
        (f.processingStatus === 'processing' || f.processingStatus === 'queued') &&
        !sseActiveRef.current.has(f.id)
    );

    if (processingFiles.length === 0) return;

    const intervalId = setInterval(async () => {
      for (const file of processingFiles) {
        if (!file.documentId) continue;
        // Skip if SSE became active since interval started
        if (sseActiveRef.current.has(file.id)) continue;

        const currentCount = pollCountRef.current[file.id] || 0;
        if (currentCount >= MAX_POLL_ATTEMPTS) {
          setFiles((prev) =>
            prev.map((f) =>
              f.id === file.id
                ? {
                    ...f,
                    processingStatus: 'failed' as ProcessingStatus,
                    error: 'Processing timed out after 5 minutes',
                  }
                : f
            )
          );
          delete pollCountRef.current[file.id];
          continue;
        }

        pollCountRef.current[file.id] = currentCount + 1;

        try {
          const result = await knowledgeService.getProcessingStatus(file.documentId);

          setFiles((prev) =>
            prev.map((f) => {
              if (f.id !== file.id) return f;

              const serverStatus = result.status as ProcessingStatus;
              const processingProgress = 50 + Math.round((result.progress_percent / 100) * 50);

              if (serverStatus === 'completed') {
                delete pollCountRef.current[file.id];
                return { ...f, processingStatus: 'completed', progress: 100 };
              }

              if (serverStatus === 'failed') {
                delete pollCountRef.current[file.id];
                return { ...f, processingStatus: 'failed', error: 'Document processing failed' };
              }

              return { ...f, processingStatus: serverStatus, progress: processingProgress };
            })
          );
        } catch {
          // Gracefully ignore polling errors and retry next interval
        }
      }
    }, POLL_INTERVAL_MS);

    return () => clearInterval(intervalId);
  }, [files]);

  /**
   * Invalidate document queries when all processing completes
   */
  useEffect(() => {
    const hasProcessing = files.some(
      (f) => f.processingStatus === 'processing' || f.processingStatus === 'queued'
    );
    const hasCompleted = files.some((f) => f.processingStatus === 'completed');

    if (!hasProcessing && hasCompleted) {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    }
  }, [files, queryClient]);

  const handleClearCompleted = useCallback(() => {
    setFiles((prev) =>
      prev.filter((f) => {
        // Only clear files where processing is fully completed or processing failed
        if (f.status === 'completed' && f.processingStatus === 'completed') return false;
        if (f.status === 'completed' && f.processingStatus === 'failed') return false;
        return true;
      })
    );
    // Clean up poll counts and SSE tracking for cleared files
    pollCountRef.current = {};
    sseActiveRef.current.clear();
    sseFailedRef.current.clear();
  }, []);

  const pendingCount = files.filter((f) => f.status === 'pending').length;
  const fullyCompletedCount = files.filter(
    (f) => f.status === 'completed' && f.processingStatus === 'completed'
  ).length;
  const processingCount = files.filter(
    (f) =>
      f.status === 'completed' &&
      (f.processingStatus === 'processing' || f.processingStatus === 'queued')
  ).length;
  const completedCount = fullyCompletedCount;

  return (
    <div className="space-y-6" data-testid="upload-page">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Upload Documents</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Upload documents to the knowledge base for indexing and search
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upload area - 2/3 width */}
        <div className="lg:col-span-2 space-y-6">
          {/* Dropzone */}
          <FileDropzone onFilesSelected={handleFilesSelected} disabled={isUploading} />

          {/* File list */}
          {files.length > 0 && (
            <div className="space-y-4">
              {/* Actions bar */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <h2 className="text-sm font-medium text-gray-900 dark:text-white">
                    {files.length} file{files.length !== 1 ? 's' : ''} selected
                  </h2>
                  {processingCount > 0 && (
                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-2xs font-medium bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400">
                      <ArrowPathIcon className="h-3 w-3 animate-spin" />
                      {processingCount} processing
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  {(completedCount > 0 || files.some((f) => f.processingStatus === 'failed')) && (
                    <button
                      onClick={handleClearCompleted}
                      className="text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
                    >
                      Clear completed
                    </button>
                  )}
                  <button
                    onClick={handleUploadAll}
                    disabled={isUploading || pendingCount === 0}
                    className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors"
                  >
                    {isUploading ? (
                      <>
                        <ArrowPathIcon className="h-4 w-4 animate-spin" />
                        Uploading...
                      </>
                    ) : (
                      <>
                        <CloudArrowUpIcon className="h-4 w-4" />
                        Upload {pendingCount > 0 ? `(${pendingCount})` : 'All'}
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* File items */}
              <div className="space-y-4">
                {files.map((uploadFile) => (
                  <UploadFileItem
                    key={uploadFile.id}
                    uploadFile={uploadFile}
                    onRemove={handleRemoveFile}
                    onRetry={handleRetry}
                    onUpdateTitle={handleUpdateTitle}
                    onUpdateCategory={handleUpdateCategory}
                    onAddTag={handleAddTag}
                    onRemoveTag={handleRemoveTag}
                  />
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Upload history sidebar - 1/3 width */}
        <div>
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
            <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">Recent Uploads</h2>
            <UploadHistory />
          </div>

          {/* Supported formats card */}
          <div className="mt-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Supported Formats</h3>
            <div className="grid grid-cols-2 gap-2">
              {SUPPORTED_FORMATS.map((format) => (
                <div
                  key={format.ext}
                  className="flex items-center gap-2 px-2 py-1.5 rounded-lg bg-gray-50 dark:bg-gray-750"
                >
                  <DocumentTextIcon className="h-4 w-4 text-gray-400" />
                  <span className="text-xs text-gray-600 dark:text-gray-300">{format.label}</span>
                  <span className="text-2xs text-gray-400">{format.ext}</span>
                </div>
              ))}
            </div>
            <p className="mt-3 text-xs text-gray-400 dark:text-gray-500">
              Maximum file size: {MAX_FILE_SIZE_MB}MB per file
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DocumentUploadPage;
