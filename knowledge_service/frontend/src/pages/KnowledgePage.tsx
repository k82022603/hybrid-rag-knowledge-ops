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
    classes = 'bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/30 shadow-[0_0_8px_rgba(6,182,212,0.2)]';
    icon = <CheckCircleIcon className="h-3.5 w-3.5" />;
  } else if (isActiveProcessing(status)) {
    classes = 'bg-neon-purple/10 text-neon-purple border border-neon-purple/30 shadow-[0_0_8px_rgba(168,85,247,0.2)]';
    icon = <ArrowPathIcon className="h-3.5 w-3.5 animate-spin" />;
  } else if (status === 'queued') {
    classes = 'bg-white/5 text-gray-400 border border-white/10';
    icon = <ClockIcon className="h-3.5 w-3.5" />;
  } else if (status === 'failed') {
    classes = 'bg-error-900/20 text-error-500 border border-error-900/30';
    icon = <ExclamationCircleIcon className="h-3.5 w-3.5" />;
  } else {
    classes = 'bg-white/5 text-gray-400 border border-white/10';
    icon = <ClockIcon className="h-3.5 w-3.5" />;
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${classes}`}
    >
      {icon}
      {status.charAt(0).toUpperCase() + status.slice(1)}
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
          <h1 className="text-3xl font-display font-bold text-white tracking-tight text-glow">
            Knowledge Base
          </h1>
          <p className="mt-1 text-sm text-gray-400">
            Manage your vector database and document processing pipeline
          </p>
        </div>
        <button
          onClick={() => navigate('/upload')}
          className="btn-primary shadow-glow-cyan"
        >
          <CloudArrowUpIcon className="h-5 w-5" />
          Upload Documents
        </button>
      </div>

      {/* Processing Status Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="glass-panel p-5 card-hover group cursor-default border-t-2 border-t-neon-cyan/50">
          <div className="flex items-center gap-2 mb-2">
            <div className="p-1.5 rounded-lg bg-neon-cyan/10 text-neon-cyan">
              <CheckCircleIcon className="h-5 w-5" />
            </div>
            <span className="text-sm font-semibold text-gray-400">Completed</span>
          </div>
          <div className="flex items-end justify-between">
            <p className="text-3xl font-bold text-white tabular-nums group-hover:text-neon-cyan transition-colors text-glow">
              {processingStats.completed}
            </p>
            {processingStats.completed > 0 && <span className="text-xs text-neon-cyan mb-1">Documents</span>}
          </div>
        </div>

        <div className="glass-panel p-5 card-hover group cursor-default border-t-2 border-t-neon-purple/50">
          <div className="flex items-center gap-2 mb-2">
            <div className="p-1.5 rounded-lg bg-neon-purple/10 text-neon-purple">
              <ArrowPathIcon className="h-5 w-5 group-hover:animate-spin" />
            </div>
            <span className="text-sm font-semibold text-gray-400">Processing</span>
          </div>
          <div className="flex items-end justify-between">
            <p className="text-3xl font-bold text-white tabular-nums group-hover:text-neon-purple transition-colors text-glow-purple">
              {processingStats.processing}
            </p>
            {processingStats.processing > 0 && <span className="text-xs text-neon-purple mb-1">Active</span>}
          </div>
        </div>

        <div className="glass-panel p-5 card-hover group cursor-default border-t-2 border-t-gray-500/50">
          <div className="flex items-center gap-2 mb-2">
            <div className="p-1.5 rounded-lg bg-white/5 text-gray-400">
              <ClockIcon className="h-5 w-5" />
            </div>
            <span className="text-sm font-semibold text-gray-400">Queued</span>
          </div>
          <div className="flex items-end justify-between">
            <p className="text-3xl font-bold text-white tabular-nums group-hover:text-gray-300 transition-colors">
              {processingStats.queued}
            </p>
            {processingStats.queued > 0 && <span className="text-xs text-gray-400 mb-1">Pending</span>}
          </div>
        </div>

        <div className="glass-panel p-5 card-hover group cursor-default border-t-2 border-t-error-500/50">
          <div className="flex items-center gap-2 mb-2">
            <div className="p-1.5 rounded-lg bg-error-900/20 text-error-500">
              <ExclamationCircleIcon className="h-5 w-5" />
            </div>
            <span className="text-sm font-semibold text-gray-400">Failed</span>
          </div>
          <div className="flex items-end justify-between">
            <p className="text-3xl font-bold text-white tabular-nums group-hover:text-error-500 transition-colors">
              {processingStats.failed}
            </p>
            {processingStats.failed > 0 && <span className="text-xs text-error-500 mb-1">Errors</span>}
          </div>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="glass-panel p-5">
        <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-3">
          {/* Search input */}
          <div className="relative flex-1 group">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500 group-focus-within:text-neon-cyan transition-colors" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by filename..."
              className="w-full pl-9 pr-3 py-2.5 text-sm rounded-lg border border-white/10 bg-black/20 text-gray-200 outline-none focus:ring-1 focus:ring-neon-cyan focus:border-neon-cyan transition-all hover:bg-black/30 placeholder-gray-600"
              aria-label="Search documents"
            />
          </div>

          {/* Filter toggle */}
          <button
            type="button"
            onClick={() => setFiltersExpanded(!filtersExpanded)}
            className={`btn ${filtersExpanded || activeFilterCount > 0
              ? 'bg-neon-cyan/10 text-neon-cyan border-neon-cyan/50 hover:bg-neon-cyan/20'
              : 'btn-secondary'
              }`}
          >
            <FunnelIcon className="h-4 w-4" />
            Filters
            {activeFilterCount > 0 && (
              <span className="ml-1 inline-flex items-center justify-center w-5 h-5 text-[10px] font-bold bg-neon-cyan text-black rounded-full">
                {activeFilterCount}
              </span>
            )}
          </button>
        </form>

        {/* Expanded filters */}
        {filtersExpanded && (
          <div className="mt-4 pt-4 border-t border-white/10 flex flex-wrap gap-4 animate-slide-down">
            <div className="w-full sm:w-auto">
              <label htmlFor="status-filter" className="block text-xs font-semibold text-gray-500 mb-1.5 uppercase tracking-wider">
                Status
              </label>
              <select
                id="status-filter"
                value={statusFilter}
                onChange={(e) => handleStatusFilterChange(e.target.value)}
                className="w-full sm:w-48 px-3 py-2 text-sm rounded-lg border border-white/10 bg-black/20 text-gray-200 outline-none focus:ring-1 focus:ring-neon-cyan focus:border-neon-cyan transition-all hover:bg-black/30"
              >
                {STATUS_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value} className="bg-dark-200 text-gray-200">
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="w-full sm:w-auto">
              <label htmlFor="format-filter" className="block text-xs font-semibold text-gray-500 mb-1.5 uppercase tracking-wider">
                Format
              </label>
              <select
                id="format-filter"
                value={formatFilter}
                onChange={(e) => handleFormatFilterChange(e.target.value)}
                className="w-full sm:w-48 px-3 py-2 text-sm rounded-lg border border-white/10 bg-black/20 text-gray-200 outline-none focus:ring-1 focus:ring-neon-cyan focus:border-neon-cyan transition-all hover:bg-black/30"
              >
                {FORMAT_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value} className="bg-dark-200 text-gray-200">
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
                className="self-end px-3 py-2 text-sm font-medium text-gray-500 hover:text-white transition-colors"
              >
                Clear all
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
              <div className="absolute inset-0 rounded-full border-4 border-white/5"></div>
              <div className="absolute inset-0 rounded-full border-4 border-neon-cyan border-t-transparent animate-spin"></div>
            </div>
            <p className="text-sm font-medium text-gray-400">Loading documents...</p>
          </div>
        </div>
      )}

      {/* Error State */}
      {isError && (
        <div className="flex items-center justify-center py-20">
          <div className="text-center max-w-sm p-6 glass-panel border-error-900/50">
            <div className="w-12 h-12 rounded-full bg-error-900/20 flex items-center justify-center mx-auto mb-4">
              <ExclamationTriangleIcon className="h-6 w-6 text-error-500" />
            </div>
            <h3 className="text-lg font-bold text-white mb-2">
              Connection Error
            </h3>
            <p className="text-sm text-gray-400 mb-6">
              {error instanceof Error ? error.message : 'An unexpected error occurred while fetching documents.'}
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
        <div className="flex flex-col items-center justify-center py-20 glass-panel border-dashed border-white/10">
          <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mb-4">
            <FolderOpenIcon className="h-8 w-8 text-gray-500" />
          </div>
          <h3 className="text-base font-semibold text-white mb-1">
            No documents found
          </h3>
          <p className="text-sm text-gray-400 mb-6 max-w-xs text-center">
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
        <div className="glass-panel overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-white/10">
              <thead className="bg-white/5 backdrop-blur-sm">
                <tr>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Filename
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider hidden sm:table-cell">
                    Format
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider hidden md:table-cell">
                    Size
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider hidden lg:table-cell">
                    Date
                  </th>
                  <th className="px-6 py-4 text-right text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 bg-transparent">
                {filteredDocuments.map((doc) => (
                  <tr
                    key={doc.document_id}
                    className="group hover:bg-white/5 transition-colors"
                  >
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-white/5 text-gray-400 group-hover:bg-neon-cyan/20 group-hover:text-neon-cyan transition-colors">
                          <DocumentTextIcon className="h-5 w-5 flex-shrink-0" />
                        </div>
                        <p className="text-sm font-medium text-gray-200 truncate max-w-xs group-hover:text-white transition-colors">
                          {doc.filename}
                        </p>
                      </div>
                    </td>
                    <td className="px-6 py-4 hidden sm:table-cell">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-white/5 text-gray-400 border border-white/10 uppercase tracking-wide">
                        {doc.format}
                      </span>
                    </td>
                    <td className="px-6 py-4 hidden md:table-cell">
                      <span className="text-sm text-gray-400 tabular-nums font-mono">
                        {formatFileSize(doc.size_bytes)}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <StatusBadge status={doc.status} />
                    </td>
                    <td className="px-6 py-4 hidden lg:table-cell">
                      <span className="text-xs text-gray-500">
                        {new Date(doc.created_at).toLocaleDateString('ko-KR')}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        {doc.status === 'completed' && (
                          <button
                            onClick={() => handleDownload(doc)}
                            className="p-2 rounded-lg hover:bg-white/10 text-gray-500 hover:text-white transition-all"
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
            <div className="flex items-center justify-between px-6 py-4 border-t border-white/10 bg-white/5">
              <p className="text-xs text-gray-500">
                Showing <span className="font-medium text-gray-300">{(page - 1) * pageSize + 1}</span>-
                <span className="font-medium text-gray-300">{Math.min(page * pageSize, total)}</span> of{' '}
                <span className="font-medium text-gray-300">{total}</span> documents
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
                <span className="text-xs font-medium text-gray-400">
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
