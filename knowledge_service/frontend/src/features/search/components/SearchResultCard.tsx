/**
 * SearchResultCard - Keyword search result card component
 *
 * Displays a single search result with title, content preview,
 * relevance score, metadata badges, and optional summary.
 */
import React from 'react';
import { DocumentTextIcon } from '@heroicons/react/24/outline';
import type { SearchResultItem } from '../types';

export interface SearchResultCardProps {
  /** The search result to display */
  result: SearchResultItem;
  /** Optional index of this result (1-based) for accessibility */
  resultIndex?: number;
  /** Optional total number of results for accessibility */
  totalResults?: number;
}

/**
 * Returns Tailwind color classes based on relevance score.
 */
const getScoreColor = (score: number): string => {
  if (score >= 0.9)
    return 'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-400';
  if (score >= 0.7)
    return 'bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400';
  if (score >= 0.5)
    return 'bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-400';
  return 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300';
};

/**
 * SearchResultCard component for keyword search results.
 */
const SearchResultCard: React.FC<SearchResultCardProps> = ({
  result,
  resultIndex,
  totalResults,
}) => {
  const ariaLabel = resultIndex && totalResults
    ? `Result ${resultIndex} of ${totalResults}: ${result.metadata?.projectName || 'Document'}, relevance ${(result.score * 100).toFixed(0)} percent`
    : `Search result: ${result.metadata?.projectName || 'Document'}`;

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
            {result.metadata?.projectName || 'Document'}
          </h3>
        </div>
        <span
          className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium flex-shrink-0 ${getScoreColor(
            result.score
          )}`}
          aria-label={`Relevance: ${(result.score * 100).toFixed(0)}%`}
        >
          {(result.score * 100).toFixed(0)}%
        </span>
      </div>

      {/* Content preview */}
      <p className="text-sm text-gray-600 dark:text-gray-300 line-clamp-3 mb-3">
        {result.content}
      </p>

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
