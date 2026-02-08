/**
 * SearchResultCard - Keyword search result card component
 *
 * Displays a single search result with title, content preview,
 * relevance score (연관도 상|중|하), metadata badges, Graph button,
 * and optional summary.
 */
import React, { useState } from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { DocumentTextIcon, ShareIcon, ArrowDownTrayIcon, ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/24/outline';
import type { SearchResultItem } from '../types';

export interface SearchResultCardProps {
  /** The search result to display */
  result: SearchResultItem;
  /** Optional index of this result (1-based) for accessibility */
  resultIndex?: number;
  /** Optional total number of results for accessibility */
  totalResults?: number;
  /** Callback when Graph button is clicked */
  onGraphClick?: () => void;
  /** Callback when Download button is clicked */
  onDownloadClick?: () => void;
}

/**
 * Returns relevance level info based on score.
 */
const getRelevanceInfo = (score: number): { label: string; className: string } => {
  if (score >= 0.7)
    return { label: '상', className: 'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-400' };
  if (score >= 0.4)
    return { label: '중', className: 'bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400' };
  return { label: '하', className: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300' };
};

/**
 * SearchResultCard component for keyword search results.
 */
const SearchResultCard: React.FC<SearchResultCardProps> = ({
  result,
  resultIndex,
  totalResults,
  onGraphClick,
  onDownloadClick,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const title = result.metadata?.projectName || result.title || '문서';
  const ariaLabel = resultIndex && totalResults
    ? `검색 결과 ${resultIndex}/${totalResults}: ${title}, 연관도 ${getRelevanceInfo(result.score).label} (${(result.score * 100).toFixed(0)}%)`
    : `검색 결과: ${title}`;

  return (
    <article
      className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 hover:shadow-soft transition-shadow focus-within:ring-2 focus-within:ring-primary-500"
      data-testid={`search-result-${result.chunkId}`}
      aria-label={ariaLabel}
      tabIndex={0}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <DocumentTextIcon className="h-5 w-5 text-gray-400 flex-shrink-0" aria-hidden="true" />
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white truncate">
            {title}
          </h3>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {/* Graph button */}
          {onGraphClick && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onGraphClick();
              }}
              className="inline-flex items-center gap-1 px-2 py-0.5 text-2xs font-medium text-teal-600 dark:text-teal-400 hover:bg-teal-50 dark:hover:bg-teal-900/20 border border-teal-200 dark:border-teal-800 rounded-full transition-colors"
              aria-label={`${title} 그래프 보기`}
            >
              <ShareIcon className="h-3 w-3" aria-hidden="true" />
              Graph
            </button>
          )}
          {/* Download button */}
          {onDownloadClick && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onDownloadClick();
              }}
              className="inline-flex items-center gap-1 px-2 py-0.5 text-2xs font-medium text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-full transition-colors"
              aria-label={`${title} 원본 다운로드`}
            >
              <ArrowDownTrayIcon className="h-3 w-3" aria-hidden="true" />
              원본
            </button>
          )}
          {/* Relevance badge */}
          <span
            className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${getRelevanceInfo(result.score).className}`}
            aria-label={`연관도 ${getRelevanceInfo(result.score).label} (${(result.score * 100).toFixed(0)}%)`}
          >
            연관도 {getRelevanceInfo(result.score).label} ({(result.score * 100).toFixed(0)}%)
          </span>
        </div>
      </div>

      {/* Content preview (Markdown) - expandable */}
      <div className={`text-sm text-gray-600 dark:text-gray-300 mb-1 prose prose-sm dark:prose-invert max-w-none prose-p:my-0.5 prose-ul:my-0.5 prose-ol:my-0.5 prose-li:my-0 prose-headings:my-1 prose-headings:text-sm prose-pre:my-1 prose-pre:text-xs ${isExpanded ? '' : 'line-clamp-3'}`}>
        <Markdown remarkPlugins={[remarkGfm]}>
          {result.content}
        </Markdown>
      </div>
      {result.content && result.content.length > 100 && (
        <button
          type="button"
          onClick={() => setIsExpanded(!isExpanded)}
          className="inline-flex items-center gap-0.5 text-2xs text-primary-500 hover:text-primary-700 dark:hover:text-primary-300 mb-2"
        >
          {isExpanded ? (
            <>
              <ChevronUpIcon className="h-3 w-3" />
              접기
            </>
          ) : (
            <>
              <ChevronDownIcon className="h-3 w-3" />
              더 보기
            </>
          )}
        </button>
      )}

      {/* Metadata badges */}
      <div className="flex flex-wrap items-center gap-2">
        {result.metadata?.documentType && (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-2xs font-medium bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300">
            {result.metadata.documentType}
          </span>
        )}
        {result.metadata?.category && (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-2xs font-medium bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300">
            {result.metadata.category.level1}
            {result.metadata.category.level2 &&
              ` / ${result.metadata.category.level2}`}
          </span>
        )}
        {result.graphContext?.community && (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-2xs font-medium bg-accent-50 text-accent-700 dark:bg-accent-900/30 dark:text-accent-400">
            {result.graphContext.community}
          </span>
        )}
        {result.sourceType && (
          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-2xs font-medium ${
            result.sourceType === 'vector'
              ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
              : result.sourceType === 'keyword'
                ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300'
                : result.sourceType === 'graph'
                  ? 'bg-teal-100 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300'
          }`}>
            {result.sourceType === 'vector' ? 'Vector' : result.sourceType === 'keyword' ? 'Keyword' : result.sourceType === 'graph' ? 'Graph' : result.sourceType}
          </span>
        )}
      </div>

      {/* Summary */}
      {result.metadata?.summary && (
        <p className="mt-2 text-xs text-gray-500 dark:text-gray-400 italic">
          {result.metadata.summary}
        </p>
      )}
    </article>
  );
};

export default SearchResultCard;
