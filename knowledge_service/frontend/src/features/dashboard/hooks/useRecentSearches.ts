/**
 * useRecentSearches - Recent search history hook
 *
 * Manages recent search queries using localStorage for persistence.
 * Provides methods to add, remove, and clear search history.
 */
import { useState, useCallback, useEffect } from 'react';

/** Storage key for recent searches */
const STORAGE_KEY = 'kp_recent_searches';

/** Maximum number of recent searches to store */
const MAX_RECENT_SEARCHES = 10;

/** Recent search item interface */
export interface RecentSearchItem {
  /** Unique identifier */
  id: string;
  /** The search query text */
  query: string;
  /** Timestamp of when the search was performed */
  timestamp: string;
  /** Number of results returned (optional) */
  resultCount?: number;
}

/**
 * Load recent searches from localStorage.
 */
const loadFromStorage = (): RecentSearchItem[] => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored) as RecentSearchItem[];
    }
  } catch (error) {
    console.error('[useRecentSearches] Failed to load from storage:', error);
  }
  return [];
};

/**
 * Save recent searches to localStorage.
 */
const saveToStorage = (items: RecentSearchItem[]): void => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  } catch (error) {
    console.error('[useRecentSearches] Failed to save to storage:', error);
  }
};

export interface UseRecentSearchesOptions {
  /** Maximum number of items to keep (default: 10) */
  maxItems?: number;
  /** Number of items to display (default: 5) */
  displayCount?: number;
}

/**
 * Custom hook for managing recent search history.
 *
 * @param options - Configuration options
 * @returns Recent searches state and management functions
 *
 * @example
 * ```tsx
 * const { searches, addSearch, removeSearch, clearAll } = useRecentSearches({ displayCount: 5 });
 * ```
 */
export const useRecentSearches = (options: UseRecentSearchesOptions = {}) => {
  const { maxItems = MAX_RECENT_SEARCHES, displayCount = 5 } = options;
  const [searches, setSearches] = useState<RecentSearchItem[]>(() => loadFromStorage());

  // Sync with localStorage on mount
  useEffect(() => {
    const stored = loadFromStorage();
    if (stored.length > 0) {
      setSearches(stored);
    }
  }, []);

  /**
   * Add a new search to the recent history.
   * Deduplicates by query text and keeps the most recent at the top.
   */
  const addSearch = useCallback(
    (query: string, resultCount?: number) => {
      setSearches((prev) => {
        // Remove duplicates of the same query
        const filtered = prev.filter(
          (item) => item.query.toLowerCase() !== query.toLowerCase()
        );

        const newItem: RecentSearchItem = {
          id: `search_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`,
          query,
          timestamp: new Date().toISOString(),
          resultCount,
        };

        // Prepend new item, limit to maxItems
        const updated = [newItem, ...filtered].slice(0, maxItems);
        saveToStorage(updated);
        return updated;
      });
    },
    [maxItems]
  );

  /**
   * Remove a specific search by ID.
   */
  const removeSearch = useCallback((id: string) => {
    setSearches((prev) => {
      const updated = prev.filter((item) => item.id !== id);
      saveToStorage(updated);
      return updated;
    });
  }, []);

  /**
   * Clear all recent searches.
   */
  const clearAll = useCallback(() => {
    setSearches([]);
    saveToStorage([]);
  }, []);

  return {
    /** All stored recent searches */
    searches,
    /** Recent searches limited to displayCount */
    displaySearches: searches.slice(0, displayCount),
    /** Add a new search query */
    addSearch,
    /** Remove a search by ID */
    removeSearch,
    /** Clear all searches */
    clearAll,
    /** Total number of stored searches */
    totalCount: searches.length,
  };
};

export default useRecentSearches;
