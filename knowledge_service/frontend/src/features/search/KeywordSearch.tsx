/**
 * KeywordSearch - Keyword search page component
 *
 * Implements STORY-042 Acceptance Criteria:
 * - Keyword search input with submit
 * - Search result cards with relevance scores
 * - Search filters (document type, project, date range)
 * - Pagination for results
 * - AI-generated answer display
 * - Loading and error states
 *
 * Uses: useKeywordSearch hook, SearchResultCard, SearchFilters
 */
import React from 'react';
import {
  MagnifyingGlassIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
  DocumentTextIcon,
  AdjustmentsHorizontalIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline';
import SearchFilters from '@/components/search/SearchFilters';
import SearchResultCard from './components/SearchResultCard';
import { useKeywordSearch } from './hooks/useKeywordSearch';

/**
 * KeywordSearch page component (/search/keyword)
 */
const KeywordSearch: React.FC = () => {
  const {
    query,
    setQuery,
    submittedQuery,
    filters,
    showFilters,
    toggleFilters,
    setFilters,
    page,
    totalPages,
    totalCount,
    results,
    answer,
    isLoading,
    isError,
    error,
    handleSearch,
    goToPage,
    hasActiveFilters,
  } = useKeywordSearch();

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
                data-testid="keyword-search-input"
              />
            </div>
            <button
              type="button"
              onClick={toggleFilters}
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
              data-testid="keyword-search-submit"
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

      {/* Filters Panel */}
      {showFilters && (
        <SearchFilters filters={filters} onFilterChange={setFilters} />
      )}

      {/* Results Section */}
      <div>
        {/* Loading State */}
        {isLoading && (
          <div className="flex items-center justify-center py-16">
            <div className="text-center">
              <ArrowPathIcon className="h-8 w-8 text-primary-500 animate-spin mx-auto mb-3" />
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Searching...
              </p>
            </div>
          </div>
        )}

        {/* Error State */}
        {isError && (
          <div className="flex items-center justify-center py-16">
            <div className="text-center max-w-sm">
              <ExclamationTriangleIcon className="h-10 w-10 text-error-500 mx-auto mb-3" />
              <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-1">
                Search failed
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {error?.message || 'An unexpected error occurred.'}
              </p>
            </div>
          </div>
        )}

        {/* Empty State - No query submitted */}
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

        {/* No Results State */}
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

        {/* Results Display */}
        {!isLoading && !isError && results.length > 0 && (
          <>
            {/* Result count */}
            <div className="flex items-center justify-between mb-3">
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Found{' '}
                <span className="font-medium text-gray-900 dark:text-white">
                  {totalCount}
                </span>{' '}
                results for &quot;
                <span className="font-medium">{submittedQuery}</span>&quot;
              </p>
            </div>

            {/* AI Generated Answer */}
            {answer && (
              <div className="mb-4 p-4 bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800 rounded-xl">
                <div className="flex items-center gap-2 mb-2">
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-primary-100 text-primary-700 dark:bg-primary-900 dark:text-primary-300">
                    <SparklesIcon className="h-3 w-3" />
                    AI Answer
                  </span>
                </div>
                <p className="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
                  {answer}
                </p>
              </div>
            )}

            {/* Result cards */}
            <div className="space-y-3">
              {results.map((result) => (
                <SearchResultCard key={result.chunkId} result={result} />
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
                    onClick={() => goToPage(page - 1)}
                    disabled={page <= 1}
                    className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <ChevronLeftIcon className="h-4 w-4" />
                    Previous
                  </button>
                  <button
                    onClick={() => goToPage(page + 1)}
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
