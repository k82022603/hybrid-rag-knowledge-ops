/**
 * DocumentUploadPage - 문서 업로드 페이지
 *
 * 드래그 앤 드롭 파일 업로드, 메타데이터 입력,
 * 업로드 진행률 표시, 업로드 이력 표시
 */
import React, { useState, useCallback, useRef } from 'react';
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
import { knowledgeService, type Document as KnowledgeDocument } from '@/services/knowledgeService';

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
const MAX_FILE_SIZE_MB = 50;
const MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024;

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
}

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
  onUpdateTitle: (id: string, title: string) => void;
  onUpdateCategory: (id: string, category: string) => void;
  onAddTag: (id: string, tag: string) => void;
  onRemoveTag: (id: string, tag: string) => void;
}> = ({ uploadFile, onRemove, onUpdateTitle, onUpdateCategory, onAddTag, onRemoveTag }) => {
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

      {/* Progress bar */}
      {(uploadFile.status === 'uploading' || uploadFile.status === 'completed') && (
        <div className="mb-4">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {uploadFile.status === 'completed' ? 'Completed' : `Uploading... ${uploadFile.progress}%`}
            </span>
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
            <div
              className={`h-1.5 rounded-full transition-all duration-300 ${
                uploadFile.status === 'completed' ? 'bg-success-500' : 'bg-primary-500'
              }`}
              style={{ width: `${uploadFile.progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Error message */}
      {uploadFile.status === 'failed' && uploadFile.error && (
        <div className="flex items-center gap-2 p-2 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg mb-4" role="alert">
          <ExclamationTriangleIcon className="h-4 w-4 text-error-500 flex-shrink-0" />
          <span className="text-xs text-error-700 dark:text-error-300">{uploadFile.error}</span>
        </div>
      )}

      {/* Metadata form (only when pending) */}
      {isEditable && (
        <div className="space-y-3 pt-3 border-t border-gray-100 dark:border-gray-700">
          {/* Title */}
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              Title
            </label>
            <input
              type="text"
              value={uploadFile.title}
              onChange={(e) => onUpdateTitle(uploadFile.id, e.target.value)}
              placeholder="Document title (optional)"
              className="w-full px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
            />
          </div>

          {/* Category */}
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              Category
            </label>
            <select
              value={uploadFile.category}
              onChange={(e) => onUpdateCategory(uploadFile.id, e.target.value)}
              className="w-full px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
            >
              <option value="">Select category</option>
              <option value="technical">Technical Document</option>
              <option value="guide">Guide / Manual</option>
              <option value="policy">Policy / Regulation</option>
              <option value="report">Report</option>
              <option value="meeting">Meeting Notes</option>
              <option value="other">Other</option>
            </select>
          </div>

          {/* Tags */}
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              Tags
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
                placeholder="Add a tag..."
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
      pending: 'bg-warning-50 text-warning-700 dark:bg-warning-900/30 dark:text-warning-400',
      failed: 'bg-error-50 text-error-700 dark:bg-error-900/30 dark:text-error-400',
    };
    return (
      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-2xs font-medium ${classes[status] || classes.pending}`}>
        {status}
      </span>
    );
  };

  return (
    <div className="space-y-2">
      {documents.map((doc: KnowledgeDocument) => (
        <div
          key={doc.id}
          className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors"
        >
          <DocumentTextIcon className="h-5 w-5 text-gray-400 flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{doc.title}</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {doc.documentType} &middot; {new Date(doc.createdAt).toLocaleDateString('ko-KR')}
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
        // Simulate progress updates
        const progressInterval = setInterval(() => {
          setFiles((prev) =>
            prev.map((f) =>
              f.id === uploadFile.id && f.status === 'uploading'
                ? { ...f, progress: Math.min(f.progress + 10, 90) }
                : f
            )
          );
        }, 200);

        await knowledgeService.uploadFile(uploadFile.file, {
          projectName: uploadFile.title,
          documentType: uploadFile.category,
        });

        clearInterval(progressInterval);

        // Set completed
        setFiles((prev) =>
          prev.map((f) =>
            f.id === uploadFile.id ? { ...f, status: 'completed' as const, progress: 100 } : f
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

  const handleClearCompleted = useCallback(() => {
    setFiles((prev) => prev.filter((f) => f.status !== 'completed'));
  }, []);

  const pendingCount = files.filter((f) => f.status === 'pending').length;
  const completedCount = files.filter((f) => f.status === 'completed').length;

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
                <h2 className="text-sm font-medium text-gray-900 dark:text-white">
                  {files.length} file{files.length !== 1 ? 's' : ''} selected
                </h2>
                <div className="flex items-center gap-3">
                  {completedCount > 0 && (
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
