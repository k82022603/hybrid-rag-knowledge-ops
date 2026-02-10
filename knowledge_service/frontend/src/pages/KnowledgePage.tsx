/**
 * KnowledgePage - 지식 관리 페이지
 *
 * 문서 목록 표시/검색/필터링, 문서 상세 보기,
 * 처리 상태 모니터링, 문서 삭제
 * Tailwind CSS + React Query 기반
 */
import React, { useState, useCallback, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Dialog, Transition } from '@headlessui/react';
import { Fragment } from 'react';
import {
  DocumentTextIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
  CloudArrowUpIcon,
  TrashIcon,
  EyeIcon,
  XMarkIcon,
  CheckCircleIcon,
  ClockIcon,
  ExclamationCircleIcon,
  FolderOpenIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline';
import {
  knowledgeService,
  type Document as KnowledgeDocument,
} from '@/services/knowledgeService';

/**
 * Document category options
 */
const DOCUMENT_TYPE_OPTIONS = [
  { value: '', label: 'All Types' },
  { value: 'technical', label: 'Technical Document' },
  { value: 'guide', label: 'Guide / Manual' },
  { value: 'policy', label: 'Policy / Regulation' },
  { value: 'report', label: 'Report' },
  { value: 'meeting', label: 'Meeting Notes' },
  { value: 'other', label: 'Other' },
];

/**
 * Status badge component
 */
const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const config: Record<string, { classes: string; icon: React.ReactNode }> = {
    completed: {
      classes: 'bg-success-50 text-success-700 dark:bg-success-900/30 dark:text-success-400',
      icon: <CheckCircleIcon className="h-3.5 w-3.5" />,
    },
    processing: {
      classes: 'bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400',
      icon: <ArrowPathIcon className="h-3.5 w-3.5 animate-spin" />,
    },
    pending: {
      classes: 'bg-warning-50 text-warning-700 dark:bg-warning-900/30 dark:text-warning-400',
      icon: <ClockIcon className="h-3.5 w-3.5" />,
    },
    failed: {
      classes: 'bg-error-50 text-error-700 dark:bg-error-900/30 dark:text-error-400',
      icon: <ExclamationCircleIcon className="h-3.5 w-3.5" />,
    },
  };

  const { classes, icon } = config[status] || config.pending;

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${classes}`}
    >
      {icon}
      {status}
    </span>
  );
};

/**
 * DocumentDetailDialog - 문서 상세 다이얼로그
 */
const DocumentDetailDialog: React.FC<{
  document: KnowledgeDocument | null;
  onClose: () => void;
}> = ({ document, onClose }) => {
  if (!document) return null;

  return (
    <Transition appear show={document !== null} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
        </Transition.Child>

        <div className="fixed inset-0 flex items-center justify-center p-4">
          <Transition.Child
            as={Fragment}
            enter="ease-out duration-300"
            enterFrom="opacity-0 scale-95"
            enterTo="opacity-100 scale-100"
            leave="ease-in duration-200"
            leaveFrom="opacity-100 scale-100"
            leaveTo="opacity-0 scale-95"
          >
            <Dialog.Panel className="mx-auto max-w-2xl w-full max-h-[80vh] rounded-xl bg-white dark:bg-gray-800 shadow-xl flex flex-col">
              {/* Header */}
              <div className="flex items-start justify-between p-6 border-b border-gray-200 dark:border-gray-700">
                <div className="flex-1 min-w-0 pr-4">
                  <Dialog.Title className="text-lg font-semibold text-gray-900 dark:text-white">
                    {document.title}
                  </Dialog.Title>
                  <div className="flex items-center gap-3 mt-2">
                    <StatusBadge status={document.status} />
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      {document.documentType}
                    </span>
                    <span className="text-xs text-gray-400 dark:text-gray-500">
                      {new Date(document.createdAt).toLocaleDateString('ko-KR')}
                    </span>
                  </div>
                </div>
                <button
                  onClick={onClose}
                  className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 hover:text-gray-600 transition-colors"
                  aria-label="Close"
                >
                  <XMarkIcon className="h-5 w-5" />
                </button>
              </div>

              {/* Content */}
              <div className="flex-1 overflow-y-auto p-6 space-y-4">
                {/* Metadata */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                      Project
                    </label>
                    <p className="text-sm text-gray-900 dark:text-white">
                      {document.projectName || 'N/A'}
                    </p>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                      Author
                    </label>
                    <p className="text-sm text-gray-900 dark:text-white">
                      {document.metadata?.author || 'N/A'}
                    </p>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                      Department
                    </label>
                    <p className="text-sm text-gray-900 dark:text-white">
                      {document.metadata?.department || 'N/A'}
                    </p>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                      Last Updated
                    </label>
                    <p className="text-sm text-gray-900 dark:text-white">
                      {new Date(document.updatedAt).toLocaleString('ko-KR')}
                    </p>
                  </div>
                </div>

                {/* Tags */}
                {document.metadata?.tags && document.metadata.tags.length > 0 && (
                  <div>
                    <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
                      Tags
                    </label>
                    <div className="flex flex-wrap gap-1.5">
                      {document.metadata.tags.map((tag) => (
                        <span
                          key={tag}
                          className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary-100 text-primary-800 dark:bg-primary-900 dark:text-primary-200"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Content preview */}
                <div>
                  <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
                    Content Preview
                  </label>
                  <div className="p-4 rounded-lg bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700">
                    <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap line-clamp-[20]">
                      {document.content || 'No content preview available.'}
                    </p>
                  </div>
                </div>
              </div>
            </Dialog.Panel>
          </Transition.Child>
        </div>
      </Dialog>
    </Transition>
  );
};

/**
 * DeleteConfirmDialog - 삭제 확인 다이얼로그
 */
const DeleteConfirmDialog: React.FC<{
  document: KnowledgeDocument | null;
  onConfirm: () => void;
  onCancel: () => void;
  isDeleting: boolean;
}> = ({ document, onConfirm, onCancel, isDeleting }) => (
  <Transition appear show={document !== null} as={Fragment}>
    <Dialog as="div" className="relative z-50" onClose={onCancel}>
      <Transition.Child
        as={Fragment}
        enter="ease-out duration-300"
        enterFrom="opacity-0"
        enterTo="opacity-100"
        leave="ease-in duration-200"
        leaveFrom="opacity-100"
        leaveTo="opacity-0"
      >
        <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
      </Transition.Child>

      <div className="fixed inset-0 flex items-center justify-center p-4">
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0 scale-95"
          enterTo="opacity-100 scale-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100 scale-100"
          leaveTo="opacity-0 scale-95"
        >
          <Dialog.Panel className="mx-auto max-w-sm w-full rounded-xl bg-white dark:bg-gray-800 p-6 shadow-xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-full bg-error-100 dark:bg-error-900/30">
                <ExclamationTriangleIcon className="h-5 w-5 text-error-600 dark:text-error-400" />
              </div>
              <Dialog.Title className="text-lg font-semibold text-gray-900 dark:text-white">
                Delete Document
              </Dialog.Title>
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Are you sure you want to delete{' '}
              <span className="font-medium text-gray-900 dark:text-white">
                &quot;{document?.title}&quot;
              </span>
              ? This action cannot be undone.
            </p>
            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={onCancel}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={onConfirm}
                disabled={isDeleting}
                className="px-4 py-2 text-sm font-medium text-white bg-error-600 rounded-lg hover:bg-error-700 disabled:opacity-50 transition-colors"
              >
                {isDeleting ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </Dialog.Panel>
        </Transition.Child>
      </div>
    </Dialog>
  </Transition>
);

/**
 * KnowledgePage - 메인 컴포넌트
 */
const KnowledgePage: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // State
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [page, setPage] = useState(1);
  const [selectedDocument, setSelectedDocument] = useState<KnowledgeDocument | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<KnowledgeDocument | null>(null);
  const [filtersExpanded, setFiltersExpanded] = useState(false);
  const pageSize = 15;

  // Document list query
  const {
    data: documentData,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['documents', { page, pageSize, documentType: typeFilter }],
    queryFn: () =>
      knowledgeService.getDocuments(page, pageSize, {
        documentType: typeFilter || undefined,
      }),
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => knowledgeService.deleteDocument(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      setDeleteTarget(null);
    },
  });

  // Handlers
  const handleSearch = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      setPage(1);
      // For now, the search query is handled client-side for filtering
      // In production, this would be a server-side filter parameter
    },
    []
  );

  const handleTypeFilterChange = useCallback((value: string) => {
    setTypeFilter(value);
    setPage(1);
  }, []);

  const handleViewDocument = useCallback((doc: KnowledgeDocument) => {
    setSelectedDocument(doc);
  }, []);

  const handleDeleteDocument = useCallback((doc: KnowledgeDocument) => {
    setDeleteTarget(doc);
  }, []);

  const confirmDelete = useCallback(() => {
    if (deleteTarget) {
      deleteMutation.mutate(deleteTarget.id);
    }
  }, [deleteTarget, deleteMutation]);

  // Data
  const documents = documentData?.documents ?? [];
  const totalCount = documentData?.totalCount ?? 0;
  const totalPages = Math.ceil(totalCount / pageSize);

  // Client-side search filter (supplement to server-side filtering)
  const filteredDocuments = useMemo(() => {
    if (!searchQuery.trim()) return documents;
    const q = searchQuery.toLowerCase();
    return documents.filter(
      (doc) =>
        doc.title.toLowerCase().includes(q) ||
        doc.documentType.toLowerCase().includes(q) ||
        doc.projectName?.toLowerCase().includes(q) ||
        doc.metadata?.tags?.some((tag) => tag.toLowerCase().includes(q))
    );
  }, [documents, searchQuery]);

  // Processing stats
  const processingStats = useMemo(() => {
    const stats = { completed: 0, processing: 0, pending: 0, failed: 0 };
    documents.forEach((doc) => {
      if (doc.status in stats) {
        stats[doc.status as keyof typeof stats]++;
      }
    });
    return stats;
  }, [documents]);

  return (
    <div className="space-y-6" data-testid="knowledge-page">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            지식 관리
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            지식 베이스의 문서를 업로드, 관리, 모니터링하세요
          </p>
        </div>
        <button
          onClick={() => navigate('/upload')}
          className="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 transition-colors shadow-sm"
        >
          <CloudArrowUpIcon className="h-5 w-5" />
          문서 업로드
        </button>
      </div>

      {/* Processing Status Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-center gap-2 mb-1">
            <CheckCircleIcon className="h-4 w-4 text-success-500" />
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400">완료</span>
          </div>
          <p className="text-xl font-bold text-gray-900 dark:text-white">{processingStats.completed}</p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-center gap-2 mb-1">
            <ArrowPathIcon className="h-4 w-4 text-primary-500 animate-spin" />
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400">처리 중</span>
          </div>
          <p className="text-xl font-bold text-gray-900 dark:text-white">{processingStats.processing}</p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-center gap-2 mb-1">
            <ClockIcon className="h-4 w-4 text-warning-500" />
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400">대기</span>
          </div>
          <p className="text-xl font-bold text-gray-900 dark:text-white">{processingStats.pending}</p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-center gap-2 mb-1">
            <ExclamationCircleIcon className="h-4 w-4 text-error-500" />
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400">실패</span>
          </div>
          <p className="text-xl font-bold text-gray-900 dark:text-white">{processingStats.failed}</p>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-3">
          {/* Search input */}
          <div className="relative flex-1">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="제목, 유형 또는 태그로 문서 검색..."
              className="w-full pl-9 pr-4 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              aria-label="Search documents"
            />
          </div>

          {/* Filter toggle */}
          <button
            type="button"
            onClick={() => setFiltersExpanded(!filtersExpanded)}
            className={`inline-flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg border transition-colors ${
              filtersExpanded || typeFilter
                ? 'border-primary-300 text-primary-700 bg-primary-50 dark:border-primary-700 dark:text-primary-300 dark:bg-primary-900/30'
                : 'border-gray-300 text-gray-700 dark:border-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`}
          >
            <FunnelIcon className="h-4 w-4" />
            Filters
            {typeFilter && (
              <span className="ml-1 inline-flex items-center justify-center w-5 h-5 text-xs font-bold bg-primary-600 text-white rounded-full">
                1
              </span>
            )}
          </button>
        </form>

        {/* Expanded filters */}
        {filtersExpanded && (
          <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700 flex flex-wrap gap-3">
            <div>
              <label htmlFor="type-filter" className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                Document Type
              </label>
              <select
                id="type-filter"
                value={typeFilter}
                onChange={(e) => handleTypeFilterChange(e.target.value)}
                className="px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
              >
                {DOCUMENT_TYPE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {typeFilter && (
              <button
                onClick={() => {
                  setTypeFilter('');
                  setPage(1);
                }}
                className="self-end px-3 py-1.5 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
              >
                Clear filters
              </button>
            )}
          </div>
        )}
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center py-16">
          <div className="text-center">
            <ArrowPathIcon className="h-8 w-8 text-primary-500 animate-spin mx-auto mb-3" />
            <p className="text-sm text-gray-500 dark:text-gray-400">Loading documents...</p>
          </div>
        </div>
      )}

      {/* Error State */}
      {isError && (
        <div className="flex items-center justify-center py-16">
          <div className="text-center max-w-sm">
            <ExclamationTriangleIcon className="h-10 w-10 text-error-500 mx-auto mb-3" />
            <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-1">
              Failed to load documents
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
              {error instanceof Error ? error.message : 'An unexpected error occurred.'}
            </p>
            <button
              onClick={() => refetch()}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 transition-colors"
            >
              <ArrowPathIcon className="h-4 w-4" />
              Retry
            </button>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !isError && filteredDocuments.length === 0 && (
        <div className="flex items-center justify-center py-16">
          <div className="text-center max-w-sm">
            <FolderOpenIcon className="h-12 w-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
            <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-1">
              No documents found
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
              {searchQuery || typeFilter
                ? 'Try adjusting your search or filters.'
                : 'Upload your first document to get started.'}
            </p>
            {!searchQuery && !typeFilter && (
              <button
                onClick={() => navigate('/upload')}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 transition-colors"
              >
                <CloudArrowUpIcon className="h-4 w-4" />
                문서 업로드
              </button>
            )}
          </div>
        </div>
      )}

      {/* Document Table */}
      {!isLoading && !isError && filteredDocuments.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-900">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Document
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider hidden sm:table-cell">
                    Type
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider hidden md:table-cell">
                    Project
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider hidden lg:table-cell">
                    Date
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {filteredDocuments.map((doc) => (
                  <tr
                    key={doc.id}
                    className="hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors"
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <DocumentTextIcon className="h-5 w-5 text-gray-400 flex-shrink-0" />
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-gray-900 dark:text-white truncate max-w-xs">
                            {doc.title}
                          </p>
                          {doc.metadata?.tags && doc.metadata.tags.length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-1">
                              {doc.metadata.tags.slice(0, 2).map((tag) => (
                                <span
                                  key={tag}
                                  className="inline-flex items-center px-1.5 py-0.5 rounded text-2xs bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300"
                                >
                                  {tag}
                                </span>
                              ))}
                              {doc.metadata.tags.length > 2 && (
                                <span className="text-2xs text-gray-400">
                                  +{doc.metadata.tags.length - 2}
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 hidden sm:table-cell">
                      <span className="text-sm text-gray-600 dark:text-gray-300">
                        {doc.documentType}
                      </span>
                    </td>
                    <td className="px-4 py-3 hidden md:table-cell">
                      <span className="text-sm text-gray-600 dark:text-gray-300">
                        {doc.projectName || 'N/A'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={doc.status} />
                    </td>
                    <td className="px-4 py-3 hidden lg:table-cell">
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {new Date(doc.createdAt).toLocaleDateString('ko-KR')}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => handleViewDocument(doc)}
                          className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500 dark:text-gray-400 transition-colors"
                          title="View details"
                          aria-label={`View ${doc.title}`}
                        >
                          <EyeIcon className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => handleDeleteDocument(doc)}
                          className="p-1.5 rounded-lg hover:bg-error-50 dark:hover:bg-error-900/30 text-gray-500 hover:text-error-500 dark:text-gray-400 transition-colors"
                          title="Delete document"
                          aria-label={`Delete ${doc.title}`}
                        >
                          <TrashIcon className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 dark:border-gray-700">
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Showing {(page - 1) * pageSize + 1}-{Math.min(page * pageSize, totalCount)} of{' '}
                {totalCount} documents
              </p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <ChevronLeftIcon className="h-3.5 w-3.5" />
                  Previous
                </button>
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  Page {page} of {totalPages}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Next
                  <ChevronRightIcon className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Detail Dialog */}
      <DocumentDetailDialog
        document={selectedDocument}
        onClose={() => setSelectedDocument(null)}
      />

      {/* Delete Dialog */}
      <DeleteConfirmDialog
        document={deleteTarget}
        onConfirm={confirmDelete}
        onCancel={() => setDeleteTarget(null)}
        isDeleting={deleteMutation.isPending}
      />
    </div>
  );
};

export default KnowledgePage;
