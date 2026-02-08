/**
 * KeywordSearch - Keyword search page component
 *
 * Implements STORY-042 Acceptance Criteria:
 * - Keyword search input with submit
 * - Search result cards with relevance scores (연관도 상|중|하)
 * - Search filters (document type, project, date range)
 * - Pagination for results
 * - AI-generated answer display
 * - Loading and error states
 * - Graph panel visualization (reused from ChatSearch)
 *
 * Uses: useKeywordSearch hook, SearchResultCard, SearchFilters, GraphPanel
 */
import React, { useState, useCallback } from 'react';
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
import GraphPanel from './components/GraphPanel';
import { useKeywordSearch } from './hooks/useKeywordSearch';
import { LiveRegion } from '@/components/common';
import type { Source } from './types';

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

  // Graph panel state (reused from ChatSearch)
  const [showGraphPanel, setShowGraphPanel] = useState(false);
  const [selectedGraphEntities, setSelectedGraphEntities] = useState<string[]>([]);

  /** Handle graph source click - reused from ChatSearch pattern */
  const handleGraphSourceClick = useCallback((source: Source) => {
    const entities: string[] = [];
    if (source.graphContext?.relatedEntities?.length) {
      entities.push(...source.graphContext.relatedEntities);
    }
    // ISSUE-011: title이 파일명인 경우 엔티티로 사용하지 않음
    if (entities.length === 0 && source.title) {
      const isFilename = /\.\w{2,5}$/.test(source.title) &&
        /\.(pdf|docx?|xlsx?|pptx?|txt|md|html?|csv|json|xml|hwp)$/i.test(source.title);
      if (!isFilename) {
        entities.push(source.title);
      }
    }
    // Fallback: projectName from metadata
    if (entities.length === 0 && source.metadata?.projectName) {
      entities.push(source.metadata.projectName);
    }
    if (entities.length > 0) {
      setSelectedGraphEntities(entities);
      setShowGraphPanel(true);
    }
  }, []);

  const closeGraphPanel = useCallback(() => {
    setShowGraphPanel(false);
    setSelectedGraphEntities([]);
  }, []);

  /** Handle document download - open API URL directly for FileResponse/Redirect */
  const handleDownloadClick = useCallback((documentId: string) => {
    const baseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1';
    window.open(`${baseUrl}/documents/${documentId}/download`, '_blank');
  }, []);

  // Generate status message for screen readers
  const getStatusMessage = () => {
    if (isLoading) return '검색 중...';
    if (isError) return `검색 실패: ${error?.message || '알 수 없는 오류'}`;
    if (submittedQuery && results.length === 0) return '검색 결과가 없습니다';
    if (results.length > 0) return `"${submittedQuery}" 검색 결과 ${totalCount}건`;
    return '';
  };

  return (
    <div
      className="relative flex flex-row gap-0 overflow-hidden"
      style={{ height: 'calc(100vh - 280px)', minHeight: '400px' }}
      data-testid="keyword-search"
      role="region"
      aria-label="키워드 검색"
    >
      {/* Screen reader announcements */}
      <LiveRegion
        message={getStatusMessage()}
        politeness={isError ? 'assertive' : 'polite'}
      />

      {/* Left: Search Area */}
      <div className={`flex flex-col min-w-0 overflow-y-auto ${showGraphPanel ? 'flex-[3]' : 'flex-1'}`}>
        <div className="space-y-4 p-4">
          {/* Search Input */}
          <form onSubmit={handleSearch} role="search" aria-label="문서 검색">
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
              <div className="flex gap-3">
                <div className="relative flex-1">
                  <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" aria-hidden="true" />
                  <input
                    type="search"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="검색어를 입력하세요..."
                    className="w-full pl-10 pr-4 py-2.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 focus:bg-white dark:focus:bg-gray-800"
                    aria-label="검색 키워드"
                    aria-describedby="search-hint"
                    data-testid="keyword-search-input"
                  />
                  <span id="search-hint" className="sr-only">
                    문서, 보고서, 지식 문서를 검색합니다. Enter 또는 검색 버튼을 클릭하세요.
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
                  aria-label={showFilters ? '필터 숨기기' : '필터 보기'}
                  aria-expanded={showFilters}
                  aria-controls="search-filters-panel"
                >
                  <AdjustmentsHorizontalIcon className="h-4 w-4" aria-hidden="true" />
                  <span className="hidden sm:inline">필터</span>
                  {hasActiveFilters && (
                    <span
                      className="inline-flex items-center justify-center w-5 h-5 text-xs font-bold bg-primary-600 text-white rounded-full"
                      aria-label={`활성 필터 ${Object.values(filters).filter(Boolean).length}개`}
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
                  검색
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
                    검색 중...
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
                    검색에 실패했습니다
                  </h3>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {error?.message || '알 수 없는 오류가 발생했습니다.'}
                  </p>
                </div>
              </div>
            )}

            {/* Empty State - No query submitted */}
            {!submittedQuery && !isLoading && (
              <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-16 text-center">
                <MagnifyingGlassIcon className="h-12 w-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
                <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-1">
                  키워드를 입력하여 검색하세요
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  문서, 보고서, 지식 문서를 통합 검색합니다
                </p>
              </div>
            )}

            {/* No Results State */}
            {submittedQuery && !isLoading && !isError && results.length === 0 && (
              <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-16 text-center">
                <DocumentTextIcon className="h-12 w-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
                <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-1">
                  검색 결과가 없습니다
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  다른 키워드를 입력하거나 필터를 조정해보세요
                </p>
              </div>
            )}

            {/* Results Display */}
            {!isLoading && !isError && results.length > 0 && (
              <>
                {/* Result count */}
                <div className="flex items-center justify-between mb-3">
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    &quot;<span className="font-medium">{submittedQuery}</span>&quot; 검색 결과{' '}
                    <span className="font-medium text-gray-900 dark:text-white">
                      {totalCount}
                    </span>건
                  </p>
                </div>

                {/* AI Generated Answer */}
                {answer && (
                  <div className="mb-4 p-4 bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800 rounded-xl">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-primary-100 text-primary-700 dark:bg-primary-900 dark:text-primary-300">
                        <SparklesIcon className="h-3 w-3" />
                        AI 답변
                      </span>
                    </div>
                    <p className="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
                      {answer}
                    </p>
                  </div>
                )}

                {/* Result cards */}
                <div className="space-y-3" role="list" aria-label="검색 결과">
                  {results.map((result, index) => {
                    // Graph 버튼은 graphContext가 있거나 title이 파일명이 아닌 경우에만 표시
                    const hasGraphData = !!(
                      result.graphContext?.relatedEntities?.length ||
                      (result.sourceType === 'graph')
                    );
                    return (
                      <div key={result.chunkId || index} role="listitem">
                        <SearchResultCard
                          result={result}
                          resultIndex={index + 1}
                          totalResults={totalCount}
                          onGraphClick={hasGraphData ? () => handleGraphSourceClick(result as Source) : undefined}
                          onDownloadClick={result.documentId ? () => handleDownloadClick(result.documentId) : undefined}
                        />
                      </div>
                    );
                  })}
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                  <nav
                    className="flex items-center justify-between mt-6"
                    aria-label="검색 결과 페이지"
                  >
                    <p className="text-sm text-gray-500 dark:text-gray-400" aria-live="polite">
                      {page} / {totalPages} 페이지
                    </p>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => goToPage(page - 1)}
                        disabled={page <= 1}
                        className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500"
                        aria-label={`이전 페이지 (${page - 1}페이지)`}
                      >
                        <ChevronLeftIcon className="h-4 w-4" aria-hidden="true" />
                        <span>이전</span>
                      </button>
                      <button
                        onClick={() => goToPage(page + 1)}
                        disabled={page >= totalPages}
                        className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500"
                        aria-label={`다음 페이지 (${page + 1}페이지)`}
                      >
                        <span>다음</span>
                        <ChevronRightIcon className="h-4 w-4" aria-hidden="true" />
                      </button>
                    </div>
                  </nav>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      {/* Right: Graph Panel (reused from ChatSearch) */}
      {showGraphPanel && (
        <>
          {/* Inline panel for md and above */}
          <div className="hidden md:flex flex-[2] min-w-[280px] max-w-[500px] border-l border-gray-200 dark:border-gray-700">
            <GraphPanel
              entityNames={selectedGraphEntities}
              onClose={closeGraphPanel}
            />
          </div>
          {/* Overlay panel for smaller screens */}
          <div className="md:hidden absolute inset-0 z-20">
            <GraphPanel
              entityNames={selectedGraphEntities}
              onClose={closeGraphPanel}
            />
          </div>
        </>
      )}
    </div>
  );
};

export default KeywordSearch;
