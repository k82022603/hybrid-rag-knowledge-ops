/**
 * KeywordSearch - 키워드 검색 컴포넌트
 *
 * 필터링 및 페이지네이션 지원
 * Tailwind CSS + React Query 기반
 */
import { useState, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  MagnifyingGlassIcon,
  DocumentTextIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  AdjustmentsHorizontalIcon,
} from '@heroicons/react/24/outline';
import SearchFilters from './SearchFilters';
import { searchService, type SearchQuery, type SearchResponse } from '@/services/searchService';

/**
 * Result score color mapping
 */
const getScoreColor = (score: number): string => {
  if (score >= 0.9) return 'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-400';
  if (score >= 0.7) return 'bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400';
  if (score >= 0.5) return 'bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-400';
  return 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300';
};

interface Filters {
  documentType?: string;
  projectName?: string;
  dateFrom?: string;
  dateTo?: string;
}

/**
 * KeywordSearch 메인 컴포넌트
 */
const KeywordSearch: React.FC = () => {
  const [query, setQuery] = useState('');
  const [submittedQuery, setSubmittedQuery] = useState('');
  const [filters, setFilters] = useState<Filters>({});
  const [page, setPage] = useState(1);
  const [showFilters, setShowFilters] = useState(false);
  const pageSize = 10;

  // Search query
  const {
    data: searchData,
    isLoading,
    isError,
    error,
  } = useQuery<SearchResponse>({
    queryKey: ['search', submittedQuery, filters, page],
    queryFn: () => {
      const params: SearchQuery = {
        query: submittedQuery,
        filters: {
          documentType: filters.documentType,
          projectName: filters.projectName,
          dateFrom: filters.dateFrom,
          dateTo: filters.dateTo,
        },
        page,
        pageSize,
      };
      return searchService.search(params);
    },
    enabled: !!submittedQuery,
  });

  const results = searchData?.results ?? [];
  const totalCount = searchData?.totalCount ?? 0;
  const totalPages = Math.ceil(totalCount / pageSize);

  const handleSearch = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!query.trim()) return;
      setSubmittedQuery(query.trim());
      setPage(1);
    },
    [query]
  );

  const handleFilterChange = useCallback((newFilters: Filters) => {
    setFilters(newFilters);
    setPage(1);
  }, []);

  const hasActiveFilters = Object.values(filters).some(Boolean);

  return (
    <div className="space-y-4" data-testid="keyword-search">
      {/* Search Input */}
      <form onSubmit={handleSearch}>
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <div className="flex gap-3">
            <div className="relative flex-1">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Enter search keywords..."
                className="w-full pl-10 pr-4 py-2.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 focus:bg-white dark:focus:bg-gray-800"
                aria-label="Search keywords"
              />
            </div>
            <button
              type="button"
              onClick={() => setShowFilters(!showFilters)}
              className={`inline-flex items-center gap-2 px-3 py-2.5 text-sm font-medium rounded-lg border transition-colors ${
                showFilters || hasActiveFilters
                  ? 'border-primary-300 text-primary-700 bg-primary-50 dark:border-primary-700 dark:text-primary-300 dark:bg-primary-900/30'
                  : 'border-gray-300 text-gray-700 dark:border-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
              }`}
              aria-label="Toggle filters"
            >
              <AdjustmentsHorizontalIcon className="h-4 w-4" />
              <span className="hidden sm:inline">Filters</span>
              {hasActiveFilters && (
                <span className="inline-flex items-center justify-center w-5 h-5 text-xs font-bold bg-primary-600 text-white rounded-full">
                  {Object.values(filters).filter(Boolean).length}
                </span>
              )}
            </button>
            <button
              type="submit"
              disabled={isLoading || !query.trim()}
              className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? (
                <ArrowPathIcon className="h-4 w-4 animate-spin" />
              ) : (
                <MagnifyingGlassIcon className="h-4 w-4" />
              )}
              Search
            </button>
          </div>
        </div>
      </form>

      {/* Filters */}
      {showFilters && (
        <SearchFilters filters={filters} onFilterChange={handleFilterChange} />
      )}

      {/* Results */}
      <div>
        {/* Loading */}
        {isLoading && (
          <div className="flex items-center justify-center py-16">
            <div className="text-center">
              <ArrowPathIcon className="h-8 w-8 text-primary-500 animate-spin mx-auto mb-3" />
              <p className="text-sm text-gray-500 dark:text-gray-400">Searching...</p>
            </div>
          </div>
        )}

        {/* Error */}
        {isError && (
          <div className="flex items-center justify-center py-16">
            <div className="text-center max-w-sm">
              <ExclamationTriangleIcon className="h-10 w-10 text-error-500 mx-auto mb-3" />
              <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-1">
                Search failed
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {error instanceof Error ? error.message : 'An unexpected error occurred.'}
              </p>
            </div>
          </div>
        )}

        {/* No query state */}
        {!submittedQuery && !isLoading && (
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-16 text-center">
            <MagnifyingGlassIcon className="h-12 w-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
            <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-1">
              Enter keywords to search
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Search through documents, reports, and knowledge articles
            </p>
          </div>
        )}

        {/* No results */}
        {submittedQuery && !isLoading && !isError && results.length === 0 && (
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-16 text-center">
            <DocumentTextIcon className="h-12 w-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
            <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-1">
              No results found
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Try different keywords or adjust your filters
            </p>
          </div>
        )}

        {/* Results list */}
        {!isLoading && !isError && results.length > 0 && (
          <>
            {/* Result count and answer */}
            <div className="flex items-center justify-between mb-3">
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Found <span className="font-medium text-gray-900 dark:text-white">{totalCount}</span>{' '}
                results for &quot;<span className="font-medium">{submittedQuery}</span>&quot;
              </p>
            </div>

            {/* AI Generated Answer */}
            {searchData?.answer && (
              <div className="mb-4 p-4 bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800 rounded-xl">
                <div className="flex items-center gap-2 mb-2">
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-primary-100 text-primary-700 dark:bg-primary-900 dark:text-primary-300">
                    AI Answer
                  </span>
                </div>
                <p className="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
                  {searchData.answer}
                </p>
              </div>
            )}

            {/* Result cards */}
            <div className="space-y-3">
              {results.map((result) => (
                <div
                  key={result.chunkId}
                  className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 hover:shadow-soft transition-shadow"
                >
                  {/* Header */}
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <DocumentTextIcon className="h-5 w-5 text-gray-400 flex-shrink-0" />
                      <h3 className="text-sm font-semibold text-gray-900 dark:text-white truncate">
                        {result.metadata?.projectName || 'Document'}
                      </h3>
                    </div>
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium flex-shrink-0 ${getScoreColor(
                        result.score
                      )}`}
                    >
                      {(result.score * 100).toFixed(0)}%
                    </span>
                  </div>

                  {/* Content */}
                  <p className="text-sm text-gray-600 dark:text-gray-300 line-clamp-3 mb-3">
                    {result.content}
                  </p>

                  {/* Metadata */}
                  <div className="flex flex-wrap items-center gap-2">
                    {result.metadata?.documentType && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-2xs font-medium bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300">
                        {result.metadata.documentType}
                      </span>
                    )}
                    {result.metadata?.category && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-2xs font-medium bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300">
                        {result.metadata.category.level1}
                        {result.metadata.category.level2 && ` / ${result.metadata.category.level2}`}
                      </span>
                    )}
                    {result.graphContext?.community && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-2xs font-medium bg-accent-50 text-accent-700 dark:bg-accent-900/30 dark:text-accent-400">
                        {result.graphContext.community}
                      </span>
                    )}
                  </div>

                  {/* Summary */}
                  {result.metadata?.summary && (
                    <p className="mt-2 text-xs text-gray-500 dark:text-gray-400 italic">
                      {result.metadata.summary}
                    </p>
                  )}
                </div>
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-6">
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Page {page} of {totalPages}
                </p>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page <= 1}
                    className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <ChevronLeftIcon className="h-4 w-4" />
                    Previous
                  </button>
                  <button
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page >= totalPages}
                    className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    Next
                    <ChevronRightIcon className="h-4 w-4" />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default KeywordSearch;
