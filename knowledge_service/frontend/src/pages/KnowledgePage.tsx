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
    <div className="space-y-6 animate-fade-in" data-testid="knowledge-page">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white tracking-tight">
            지식 관리
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            지식 베이스의 문서를 업로드, 관리, 모니터링하세요
          </p>
        </div>
        <button
          onClick={() => navigate('/upload')}
          className="btn-primary"
        >
          <CloudArrowUpIcon className="h-5 w-5" />
          문서 업로드
        </button>
      </div>

      {/* Processing Status Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="card card-hover group cursor-default">
          <div className="flex items-center gap-2 mb-2">
            <div className="p-1.5 rounded-lg bg-success-50 text-success-600 dark:bg-success-900/30 dark:text-success-400">
              <CheckCircleIcon className="h-5 w-5" />
            </div>
            <span className="text-sm font-medium text-gray-500 dark:text-gray-400">완료</span>
          </div>
          <div className="flex items-end justify-between">
            <p className="text-2xl font-bold text-gray-900 dark:text-white tabular-nums group-hover:text-success-600 dark:group-hover:text-success-400 transition-colors">
              {processingStats.completed}
            </p>
            {processingStats.completed > 0 && <span className="text-xs text-success-600 dark:text-success-400 mb-1">Documents</span>}
          </div>
        </div>

        <div className="card card-hover group cursor-default">
          <div className="flex items-center gap-2 mb-2">
            <div className="p-1.5 rounded-lg bg-primary-50 text-primary-600 dark:bg-primary-900/30 dark:text-primary-400">
              <ArrowPathIcon className="h-5 w-5 group-hover:animate-spin" />
            </div>
            <span className="text-sm font-medium text-gray-500 dark:text-gray-400">처리 중</span>
          </div>
          <div className="flex items-end justify-between">
            <p className="text-2xl font-bold text-gray-900 dark:text-white tabular-nums group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
              {processingStats.processing}
            </p>
            {processingStats.processing > 0 && <span className="text-xs text-primary-600 dark:text-primary-400 mb-1">Processing</span>}
          </div>
        </div>

        <div className="card card-hover group cursor-default">
          <div className="flex items-center gap-2 mb-2">
            <div className="p-1.5 rounded-lg bg-warning-50 text-warning-600 dark:bg-warning-900/30 dark:text-warning-400">
              <ClockIcon className="h-5 w-5" />
            </div>
            <span className="text-sm font-medium text-gray-500 dark:text-gray-400">대기</span>
          </div>
          <div className="flex items-end justify-between">
            <p className="text-2xl font-bold text-gray-900 dark:text-white tabular-nums group-hover:text-warning-600 dark:group-hover:text-warning-400 transition-colors">
              {processingStats.queued}
            </p>
            {processingStats.queued > 0 && <span className="text-xs text-warning-600 dark:text-warning-400 mb-1">Queued</span>}
          </div>
        </div>

        <div className="card card-hover group cursor-default">
          <div className="flex items-center gap-2 mb-2">
            <div className="p-1.5 rounded-lg bg-error-50 text-error-600 dark:bg-error-900/30 dark:text-error-400">
              <ExclamationCircleIcon className="h-5 w-5" />
            </div>
            <span className="text-sm font-medium text-gray-500 dark:text-gray-400">실패</span>
          </div>
          <div className="flex items-end justify-between">
            <p className="text-2xl font-bold text-gray-900 dark:text-white tabular-nums group-hover:text-error-600 dark:group-hover:text-error-400 transition-colors">
              {processingStats.failed}
            </p>
            {processingStats.failed > 0 && <span className="text-xs text-error-600 dark:text-error-400 mb-1">Failed</span>}
          </div>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="card">
        <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-3">
          {/* Search input */}
          <div className="relative flex-1 group">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 group-focus-within:text-primary-500 transition-colors" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="파일명으로 검색..."
              className="input pl-9"
              aria-label="Search documents"
            />
          </div>

          {/* Filter toggle */}
          <button
            type="button"
            onClick={() => setFiltersExpanded(!filtersExpanded)}
            className={`btn ${filtersExpanded || activeFilterCount > 0
                ? 'bg-primary-50 text-primary-700 border-primary-200 hover:bg-primary-100 dark:bg-primary-900/30 dark:text-primary-300 dark:border-primary-800'
                : 'btn-secondary'
              }`}
          >
            <FunnelIcon className="h-4 w-4" />
            Filters
            {activeFilterCount > 0 && (
              <span className="ml-1 inline-flex items-center justify-center w-5 h-5 text-[10px] font-bold bg-primary-600 text-white rounded-full">
                {activeFilterCount}
              </span>
            )}
          </button>
        </form>

        {/* Expanded filters */}
        {filtersExpanded && (
          <div className="mt-4 pt-4 border-t border-gray-100 dark:border-gray-700 flex flex-wrap gap-4 animate-slide-down">
            <div className="w-full sm:w-auto">
              <label htmlFor="status-filter" className="label text-xs uppercase tracking-wide text-gray-500">
                Status
              </label>
              <select
                id="status-filter"
                value={statusFilter}
                onChange={(e) => handleStatusFilterChange(e.target.value)}
                className="input py-1.5 text-sm w-full sm:w-40"
              >
                {STATUS_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="w-full sm:w-auto">
              <label htmlFor="format-filter" className="label text-xs uppercase tracking-wide text-gray-500">
                Format
              </label>
              <select
                id="format-filter"
                value={formatFilter}
                onChange={(e) => handleFormatFilterChange(e.target.value)}
                className="input py-1.5 text-sm w-full sm:w-40"
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
                className="self-end px-3 py-2 text-sm font-medium text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
              >
                Clear filters
              </button>
            )}
          </div>
        )}
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <div className="relative w-16 h-16 mx-auto mb-4">
              <div className="absolute inset-0 rounded-full border-4 border-gray-100 dark:border-gray-800"></div>
              <div className="absolute inset-0 rounded-full border-4 border-primary-500 border-t-transparent animate-spin"></div>
            </div>
            <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Loading documents...</p>
          </div>
        </div>
      )}

      {/* Error State */}
      {isError && (
        <div className="flex items-center justify-center py-20">
          <div className="text-center max-w-sm p-6 bg-white dark:bg-gray-800 rounded-xl shadow-soft border border-error-100 dark:border-error-900/30">
            <div className="w-12 h-12 rounded-full bg-error-50 dark:bg-error-900/30 flex items-center justify-center mx-auto mb-4">
              <ExclamationTriangleIcon className="h-6 w-6 text-error-500" />
            </div>
            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2">
              Failed to load documents
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
              {error instanceof Error ? error.message : 'An unexpected error occurred.'}
            </p>
            <button
              onClick={() => refetch()}
              className="btn-primary w-full"
            >
              <ArrowPathIcon className="h-4 w-4" />
              Retry Connection
            </button>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !isError && filteredDocuments.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 bg-white dark:bg-gray-800 rounded-xl border border-dashed border-gray-300 dark:border-gray-700">
          <div className="w-16 h-16 rounded-full bg-gray-50 dark:bg-gray-800/50 flex items-center justify-center mb-4">
            <FolderOpenIcon className="h-8 w-8 text-gray-400" />
          </div>
          <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-1">
            No documents found
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-6 max-w-xs text-center">
            {searchQuery || activeFilterCount > 0
              ? 'Try adjusting your search or filters to find what you looking for.'
              : 'Knowledge base is empty. Upload your first document to get started.'}
          </p>
          {!searchQuery && activeFilterCount === 0 && (
            <button
              onClick={() => navigate('/upload')}
              className="btn-primary"
            >
              <CloudArrowUpIcon className="h-4 w-4" />
              Upload Document
            </button>
          )}
        </div>
      )}

      {/* Document Table */}
      {!isLoading && !isError && filteredDocuments.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50/50 dark:bg-gray-900/50 backdrop-blur-sm">
                <tr>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Filename
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider hidden sm:table-cell">
                    Format
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider hidden md:table-cell">
                    Size
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider hidden lg:table-cell">
                    Date
                  </th>
                  <th className="px-6 py-4 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700/50 bg-white dark:bg-gray-800">
                {filteredDocuments.map((doc) => (
                  <tr
                    key={doc.document_id}
                    className="group hover:bg-gray-50/80 dark:hover:bg-gray-700/30 transition-colors"
                  >
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 group-hover:bg-white group-hover:text-primary-600 dark:group-hover:bg-gray-600 dark:group-hover:text-primary-400 shadow-sm transition-colors">
                          <DocumentTextIcon className="h-5 w-5 flex-shrink-0" />
                        </div>
                        <p className="text-sm font-medium text-gray-900 dark:text-white truncate max-w-xs group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
                          {doc.filename}
                        </p>
                      </div>
                    </td>
                    <td className="px-6 py-4 hidden sm:table-cell">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded text-xs font-bold bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300 uppercase tracking-wide">
                        {doc.format}
                      </span>
                    </td>
                    <td className="px-6 py-4 hidden md:table-cell">
                      <span className="text-sm text-gray-500 dark:text-gray-400 tabular-nums font-mono">
                        {formatFileSize(doc.size_bytes)}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <StatusBadge status={doc.status} />
                    </td>
                    <td className="px-6 py-4 hidden lg:table-cell">
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {new Date(doc.created_at).toLocaleDateString('ko-KR')}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        {doc.status === 'completed' && (
                          <button
                            onClick={() => handleDownload(doc)}
                            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 hover:text-gray-600 dark:hover:text-white transition-all"
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
            <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-900/50">
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Showing <span className="font-medium">{(page - 1) * pageSize + 1}</span>-
                <span className="font-medium">{Math.min(page * pageSize, total)}</span> of{' '}
                <span className="font-medium">{total}</span> documents
              </p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="btn-secondary btn-sm disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeftIcon className="h-3.5 w-3.5" />
                  Previous
                </button>
                <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
                  Page {page} of {totalPages}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="btn-secondary btn-sm disabled:opacity-50 disabled:cursor-not-allowed"
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
