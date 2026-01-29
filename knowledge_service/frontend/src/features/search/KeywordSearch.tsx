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
import { LiveRegion } from '@/components/common';

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

  // Generate status message for screen readers
  const getStatusMessage = () => {
    if (isLoading) return 'Searching...';
    if (isError) return `Search failed: ${error?.message || 'Unknown error'}`;
    if (submittedQuery && results.length === 0) return 'No results found';
    if (results.length > 0) return `Found ${totalCount} results for "${submittedQuery}"`;
    return '';
  };

  return (
    <div className="space-y-4" data-testid="keyword-search" role="region" aria-label="Keyword search">
      {/* Screen reader announcements */}
      <LiveRegion
        message={getStatusMessage()}
        politeness={isError ? 'assertive' : 'polite'}
      />
      {/* Search Input */}
      <form onSubmit={handleSearch} role="search" aria-label="Search documents">
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <div className="flex gap-3">
            <div className="relative flex-1">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" aria-hidden="true" />
              <input
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Enter search keywords..."
                className="w-full pl-10 pr-4 py-2.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 focus:bg-white dark:focus:bg-gray-800"
                aria-label="Search keywords"
                aria-describedby="search-hint"
                data-testid="keyword-search-input"
              />
              <span id="search-hint" className="sr-only">
                Enter keywords to search through documents, reports, and knowledge articles. Press Enter or click Search to submit.
              </span>
            </div>
            <button
              type="button"
              onClick={toggleFilters}
              className={`inline-flex items-center gap-2 px-3 py-2.5 text-sm font-medium rounded-lg border transition-colors ${
                showFilters || hasActiveFilters
                  ? 'border-primary-300 text-primary-700 bg-primary-50 dark:border-primary-700 dark:text-primary-300 dark:bg-primary-900/30'
                  : 'border-gray-300 text-gray-700 dark:border-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
              }`}
              aria-label={showFilters ? 'Hide filters' : 'Show filters'}
              aria-expanded={showFilters}
              aria-controls="search-filters-panel"
            >
              <AdjustmentsHorizontalIcon className="h-4 w-4" aria-hidden="true" />
              <span className="hidden sm:inline">Filters</span>
              {hasActiveFilters && (
                <span
                  className="inline-flex items-center justify-center w-5 h-5 text-xs font-bold bg-primary-600 text-white rounded-full"
                  aria-label={`${Object.values(filters).filter(Boolean).length} active filters`}
                >
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
        <div id="search-filters-panel">
          <SearchFilters filters={filters} onFilterChange={setFilters} />
        </div>
      )}

      {/* Results Section */}
      <div>
        {/* Loading State */}
        {isLoading && (
          <div className="flex items-center justify-center py-16" role="status" aria-live="polite">
            <div className="text-center">
              <ArrowPathIcon className="h-8 w-8 text-primary-500 animate-spin mx-auto mb-3" aria-hidden="true" />
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Searching...
              </p>
            </div>
          </div>
        )}

        {/* Error State */}
        {isError && (
          <div className="flex items-center justify-center py-16" role="alert" aria-live="assertive">
            <div className="text-center max-w-sm">
              <ExclamationTriangleIcon className="h-10 w-10 text-error-500 mx-auto mb-3" aria-hidden="true" />
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
            <div className="space-y-3" role="list" aria-label="Search results">
              {results.map((result, index) => (
                <div key={result.chunkId} role="listitem">
                  <SearchResultCard result={result} resultIndex={index + 1} totalResults={totalCount} />
                </div>
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <nav
                className="flex items-center justify-between mt-6"
                aria-label="Search results pagination"
              >
                <p className="text-sm text-gray-500 dark:text-gray-400" aria-live="polite">
                  Page {page} of {totalPages}
                </p>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => goToPage(page - 1)}
                    disabled={page <= 1}
                    className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500"
                    aria-label={`Go to previous page, page ${page - 1}`}
                  >
                    <ChevronLeftIcon className="h-4 w-4" aria-hidden="true" />
                    <span>Previous</span>
                  </button>
                  <button
                    onClick={() => goToPage(page + 1)}
                    disabled={page >= totalPages}
                    className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500"
                    aria-label={`Go to next page, page ${page + 1}`}
                  >
                    <span>Next</span>
                    <ChevronRightIcon className="h-4 w-4" aria-hidden="true" />
                  </button>
                </div>
              </nav>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default KeywordSearch;
