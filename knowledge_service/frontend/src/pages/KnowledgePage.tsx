/**
 * KnowledgePage - 지식 관리 페이지
 *
 * 문서 목록 표시/검색/필터링, 처리 상태 모니터링, 문서 다운로드
 * Tailwind CSS + React Query 기반
 *
 * Backend API: GET /api/v1/documents (AI Service)
 * Response: { documents: DocumentListItem[], total, page, page_size, total_pages }
 */
import React, { useState, useCallback, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  DocumentTextIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
  CloudArrowUpIcon,
  ArrowDownTrayIcon,
  CheckCircleIcon,
  ClockIcon,
  ExclamationCircleIcon,
  FolderOpenIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline';
import {
  knowledgeService,
  type DocumentListItem,
  type DocumentStatus,
  type DocumentFormat,
} from '@/services/knowledgeService';

/**
 * Format filter options matching backend DocumentFormat enum
 */
const FORMAT_OPTIONS: { value: DocumentFormat | ''; label: string }[] = [
  { value: '', label: 'All Formats' },
  { value: 'pdf', label: 'PDF' },
  { value: 'docx', label: 'DOCX' },
  { value: 'hwp', label: 'HWP' },
  { value: 'pptx', label: 'PPTX' },
  { value: 'md', label: 'Markdown' },
  { value: 'txt', label: 'Text' },
  { value: 'html', label: 'HTML' },
];

/**
 * Status filter options matching backend DocumentStatus enum
 */
const STATUS_OPTIONS: { value: DocumentStatus | ''; label: string }[] = [
  { value: '', label: 'All Status' },
  { value: 'queued', label: 'Queued' },
  { value: 'processing', label: 'Processing' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
];

/**
 * File size formatter
 */
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
};

/**
 * Check if a status represents an active processing state
 */
const isActiveProcessing = (s: string): boolean =>
  ['processing', 'parsing', 'chunking', 'embedding', 'storing', 'extracting'].includes(s);

/**
 * Status badge component
 */
const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  let classes: string;
  let icon: React.ReactNode;

  if (status === 'completed') {
    classes = 'bg-success-50 text-success-700 dark:bg-success-900/30 dark:text-success-400';
    icon = <CheckCircleIcon className="h-3.5 w-3.5" />;
  } else if (isActiveProcessing(status)) {
    classes = 'bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400';
    icon = <ArrowPathIcon className="h-3.5 w-3.5 animate-spin" />;
  } else if (status === 'queued') {
    classes = 'bg-warning-50 text-warning-700 dark:bg-warning-900/30 dark:text-warning-400';
    icon = <ClockIcon className="h-3.5 w-3.5" />;
  } else if (status === 'failed') {
    classes = 'bg-error-50 text-error-700 dark:bg-error-900/30 dark:text-error-400';
    icon = <ExclamationCircleIcon className="h-3.5 w-3.5" />;
  } else {
    classes = 'bg-gray-50 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400';
    icon = <ClockIcon className="h-3.5 w-3.5" />;
  }

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
 * KnowledgePage - main component
 */
const KnowledgePage: React.FC = () => {
  const navigate = useNavigate();

  // State
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<DocumentStatus | ''>('');
  const [formatFilter, setFormatFilter] = useState<DocumentFormat | ''>('');
  const [page, setPage] = useState(1);
  const [filtersExpanded, setFiltersExpanded] = useState(false);
  const pageSize = 15;

  // Document list query - matches backend API exactly
  const {
    data: documentData,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['documents', { page, pageSize, status: statusFilter, format: formatFilter }],
    queryFn: () =>
      knowledgeService.getDocuments(page, pageSize, {
        status: statusFilter || undefined,
        format: formatFilter || undefined,
      }),
  });

  // Handlers
  const handleSearch = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
  }, []);

  const handleStatusFilterChange = useCallback((value: string) => {
    setStatusFilter(value as DocumentStatus | '');
    setPage(1);
  }, []);

  const handleFormatFilterChange = useCallback((value: string) => {
    setFormatFilter(value as DocumentFormat | '');
    setPage(1);
  }, []);

  const handleDownload = useCallback((doc: DocumentListItem) => {
    const url = knowledgeService.getDownloadUrl(doc.document_id);
    window.open(url, '_blank');
  }, []);

  // Data from backend
  const documents = documentData?.documents ?? [];
  const total = documentData?.total ?? 0;
  const totalPages = documentData?.total_pages ?? 1;

  // Client-side search filter (filename search supplement)
  const filteredDocuments = useMemo(() => {
    if (!searchQuery.trim()) return documents;
    const q = searchQuery.toLowerCase();
    return documents.filter(
      (doc) =>
        doc.filename.toLowerCase().includes(q) ||
        doc.format.toLowerCase().includes(q)
    );
  }, [documents, searchQuery]);

  // Processing stats from current page data
  const processingStats = useMemo(() => {
    const stats = { completed: 0, processing: 0, queued: 0, failed: 0 };
    documents.forEach((doc) => {
      if (doc.status === 'completed') stats.completed++;
      else if (doc.status === 'failed') stats.failed++;
      else if (doc.status === 'queued') stats.queued++;
      else if (isActiveProcessing(doc.status)) stats.processing++;
    });
    return stats;
  }, [documents]);

  const activeFilterCount = (statusFilter ? 1 : 0) + (formatFilter ? 1 : 0);

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
          <p className="text-xl font-bold text-gray-900 dark:text-white">{processingStats.queued}</p>
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
              placeholder="파일명으로 검색..."
              className="w-full pl-9 pr-4 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              aria-label="Search documents"
            />
          </div>

          {/* Filter toggle */}
          <button
            type="button"
            onClick={() => setFiltersExpanded(!filtersExpanded)}
            className={`inline-flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg border transition-colors ${
              filtersExpanded || activeFilterCount > 0
                ? 'border-primary-300 text-primary-700 bg-primary-50 dark:border-primary-700 dark:text-primary-300 dark:bg-primary-900/30'
                : 'border-gray-300 text-gray-700 dark:border-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`}
          >
            <FunnelIcon className="h-4 w-4" />
            Filters
            {activeFilterCount > 0 && (
              <span className="ml-1 inline-flex items-center justify-center w-5 h-5 text-xs font-bold bg-primary-600 text-white rounded-full">
                {activeFilterCount}
              </span>
            )}
          </button>
        </form>

        {/* Expanded filters */}
        {filtersExpanded && (
          <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700 flex flex-wrap gap-3">
            <div>
              <label htmlFor="status-filter" className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                Status
              </label>
              <select
                id="status-filter"
                value={statusFilter}
                onChange={(e) => handleStatusFilterChange(e.target.value)}
                className="px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
              >
                {STATUS_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="format-filter" className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                Format
              </label>
              <select
                id="format-filter"
                value={formatFilter}
                onChange={(e) => handleFormatFilterChange(e.target.value)}
                className="px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
              >
                {FORMAT_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {activeFilterCount > 0 && (
              <button
                onClick={() => {
                  setStatusFilter('');
                  setFormatFilter('');
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
              {searchQuery || activeFilterCount > 0
                ? 'Try adjusting your search or filters.'
                : 'Upload your first document to get started.'}
            </p>
            {!searchQuery && activeFilterCount === 0 && (
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
                    Filename
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider hidden sm:table-cell">
                    Format
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider hidden md:table-cell">
                    Size
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
                    key={doc.document_id}
                    className="hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors"
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <DocumentTextIcon className="h-5 w-5 text-gray-400 flex-shrink-0" />
                        <p className="text-sm font-medium text-gray-900 dark:text-white truncate max-w-xs">
                          {doc.filename}
                        </p>
                      </div>
                    </td>
                    <td className="px-4 py-3 hidden sm:table-cell">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300 uppercase">
                        {doc.format}
                      </span>
                    </td>
                    <td className="px-4 py-3 hidden md:table-cell">
                      <span className="text-sm text-gray-600 dark:text-gray-300">
                        {formatFileSize(doc.size_bytes)}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={doc.status} />
                    </td>
                    <td className="px-4 py-3 hidden lg:table-cell">
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {new Date(doc.created_at).toLocaleDateString('ko-KR')}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        {doc.status === 'completed' && (
                          <button
                            onClick={() => handleDownload(doc)}
                            className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500 dark:text-gray-400 transition-colors"
                            title="Download original"
                            aria-label={`Download ${doc.filename}`}
                          >
                            <ArrowDownTrayIcon className="h-4 w-4" />
                          </button>
                        )}
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
                Showing {(page - 1) * pageSize + 1}-{Math.min(page * pageSize, total)} of{' '}
                {total} documents
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
    </div>
  );
};

export default KnowledgePage;
