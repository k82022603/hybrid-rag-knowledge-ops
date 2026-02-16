/**
 * RecentSearches - Recent search history display component
 *
 * Shows the most recent search queries with timestamps.
 * Clicking a search item navigates to the search page with that query.
 *
 * AC3: Display the 5 most recent search records
 */
import React, { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ClockIcon,
  MagnifyingGlassIcon,
  XMarkIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';
import type { RecentSearchItem } from '../hooks/useRecentSearches';

export interface RecentSearchesProps {
  /** List of recent search items */
  searches: RecentSearchItem[];
  /** Callback to remove a search item by ID */
  onRemove?: (id: string) => void;
  /** Callback to clear all search history */
  onClearAll?: () => void;
  /** Callback when a search is clicked */
  onSearchClick?: (query: string) => void;
}

/**
 * RecentSearchesSkeleton - Loading skeleton
 */
export const RecentSearchesSkeleton: React.FC = () => (
  <div className="space-y-3 animate-pulse" data-testid="recent-searches-skeleton">
    {[...Array(5)].map((_, i) => (
      <div key={i} className="flex items-center gap-3 py-2">
        <div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700" />
        <div className="flex-1 space-y-1">
          <div className="h-4 w-3/4 rounded bg-gray-200 dark:bg-gray-700" />
          <div className="h-3 w-1/3 rounded bg-gray-200 dark:bg-gray-700" />
        </div>
      </div>
    ))}
  </div>
);

/**
 * Format relative time from a timestamp string.
 */
const formatRelativeTime = (timestamp: string): string => {
  const now = new Date();
  const past = new Date(timestamp);
  const diffMs = now.getTime() - past.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return past.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' });
};

/**
 * RecentSearches component displays the user's recent search history.
 */
const RecentSearches: React.FC<RecentSearchesProps> = ({
  searches,
  onRemove,
  onClearAll,
  onSearchClick,
}) => {
  const navigate = useNavigate();

  const handleClick = useCallback(
    (query: string) => {
      onSearchClick?.(query);
      navigate(`/search?q=${encodeURIComponent(query)}`);
    },
    [navigate, onSearchClick]
  );

  // Empty state
  if (!searches || searches.length === 0) {
    return (
      <div className="py-8 text-center" data-testid="recent-searches-empty">
        <ClockIcon className="h-8 w-8 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No recent searches yet.
        </p>
        <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
          Your search history will appear here.
        </p>
      </div>
    );
  }

  return (
    <div data-testid="recent-searches">
      {/* Header with clear all */}
      {onClearAll && searches.length > 0 && (
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs text-gray-400 dark:text-gray-500">
            {searches.length} recent {searches.length === 1 ? 'search' : 'searches'}
          </span>
          <button
            onClick={onClearAll}
            className="inline-flex items-center gap-1 text-xs text-gray-400 hover:text-error-500 dark:text-gray-500 dark:hover:text-error-400 transition-colors"
            aria-label="Clear all search history"
            data-testid="clear-all-searches"
          >
            <TrashIcon className="h-3.5 w-3.5" />
            Clear all
          </button>
        </div>
      )}

      {/* Search list */}
      <ul
        className="space-y-0.5"
        role="list"
        aria-label="Recent search history"
      >
        {searches.map((item) => (
          <li
            key={item.id}
            className="group flex items-center gap-3 py-2 px-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors cursor-pointer"
            data-testid="recent-search-item"
          >
            <button
              onClick={() => handleClick(item.query)}
              className="flex items-center gap-3 flex-1 min-w-0 text-left"
              aria-label={`Search for: ${item.query}`}
            >
              <div className="flex-shrink-0 p-1.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-400 dark:text-gray-500">
                <MagnifyingGlassIcon className="h-4 w-4" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-900 dark:text-white truncate">
                  {item.query}
                </p>
                <p className="text-xs text-gray-400 dark:text-gray-500">
                  {formatRelativeTime(item.timestamp)}
                  {item.resultCount !== undefined && (
                    <span className="ml-2">
                      {item.resultCount} {item.resultCount === 1 ? 'result' : 'results'}
                    </span>
                  )}
                </p>
              </div>
            </button>

            {/* Remove button */}
            {onRemove && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onRemove(item.id);
                }}
                className="flex-shrink-0 p-1 rounded opacity-0 group-hover:opacity-100 text-gray-400 hover:text-error-500 dark:text-gray-500 dark:hover:text-error-400 transition-all"
                aria-label={`Remove search: ${item.query}`}
                data-testid="remove-search-item"
              >
                <XMarkIcon className="h-4 w-4" />
              </button>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
};

export default RecentSearches;
