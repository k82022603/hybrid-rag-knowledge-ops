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
} from '@heroicons/react/24/outline';
import type { RecentSearchItem } from '../hooks/useRecentSearches';

export interface RecentSearchesProps {
  /** List of recent search items */
  searches: RecentSearchItem[];
  /** Callback to remove a search item by ID */
  onRemove?: (id: string) => void;
  /** Callback to clear all search history - Deprecated: handled by parent */
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
        <div className="w-8 h-8 rounded-full bg-white/5" />
        <div className="flex-1 space-y-1">
          <div className="h-4 w-3/4 rounded bg-white/5" />
          <div className="h-3 w-1/3 rounded bg-white/5" />
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
      <div className="py-12 text-center" data-testid="recent-searches-empty">
        <ClockIcon className="h-10 w-10 text-gray-700 mx-auto mb-3" />
        <p className="text-sm text-gray-500">
          No recent searches
        </p>
        <p className="text-xs text-gray-600 mt-1">
          Your search history will appear here
        </p>
      </div>
    );
  }

  return (
    <div data-testid="recent-searches">
      {/* Search list */}
      <ul
        className="space-y-1"
        role="list"
        aria-label="Recent search history"
      >
        {searches.map((item) => (
          <li
            key={item.id}
            className="group flex items-center gap-3 py-2.5 px-3 rounded-lg hover:bg-white/5 transition-all cursor-pointer border border-transparent hover:border-white/5"
            data-testid="recent-search-item"
          >
            <button
              onClick={() => handleClick(item.query)}
              className="flex items-center gap-3 flex-1 min-w-0 text-left"
              aria-label={`Search for: ${item.query}`}
            >
              <div className="flex-shrink-0 p-1.5 rounded-full bg-white/5 text-gray-500 group-hover:bg-neon-cyan/20 group-hover:text-neon-cyan transition-colors">
                <MagnifyingGlassIcon className="h-4 w-4" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-300 group-hover:text-white truncate transition-colors">
                  {item.query}
                </p>
                <div className="flex items-center gap-2 mt-0.5">
                  <p className="text-xs text-gray-600 group-hover:text-gray-500">
                    {formatRelativeTime(item.timestamp)}
                  </p>
                  {item.resultCount !== undefined && (
                    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] bg-white/5 text-gray-500 group-hover:bg-neon-purple/10 group-hover:text-neon-purple transition-colors">
                      {item.resultCount} results
                    </span>
                  )}
                </div>
              </div>
            </button>

            {/* Remove button */}
            {onRemove && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onRemove(item.id);
                }}
                className="flex-shrink-0 p-1.5 rounded opacity-0 group-hover:opacity-100 text-gray-600 hover:text-neon-pink hover:bg-neon-pink/10 transition-all"
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
