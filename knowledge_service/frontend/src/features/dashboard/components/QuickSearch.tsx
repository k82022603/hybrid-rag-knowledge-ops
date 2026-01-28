/**
 * QuickSearch - Quick search input component for the dashboard
 *
 * Provides a search input with keyboard shortcut hint (Ctrl+K).
 * On Enter press, navigates to the search page with the query parameter.
 *
 * AC4: Quick search input navigates to search page on Enter
 */
import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { MagnifyingGlassIcon } from '@heroicons/react/24/outline';

export interface QuickSearchProps {
  /** Callback when a search is submitted */
  onSearch?: (query: string) => void;
  /** Placeholder text */
  placeholder?: string;
}

/**
 * QuickSearch component for the dashboard.
 * Navigates to /search with query parameter on Enter.
 */
const QuickSearch: React.FC<QuickSearchProps> = ({
  onSearch,
  placeholder = 'Search knowledge base... (Ctrl+K)',
}) => {
  const [query, setQuery] = useState('');
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);

  // Handle Ctrl+K keyboard shortcut to focus input
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      const trimmed = query.trim();
      if (!trimmed) return;

      // Call optional onSearch callback
      onSearch?.(trimmed);

      // Navigate to search page with query parameter
      navigate(`/search?q=${encodeURIComponent(trimmed)}`);
    },
    [query, navigate, onSearch]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Escape') {
        setQuery('');
        inputRef.current?.blur();
      }
    },
    []
  );

  return (
    <form
      onSubmit={handleSubmit}
      className="relative w-full"
      role="search"
      aria-label="Quick search"
      data-testid="quick-search"
    >
      <div className="relative">
        <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4">
          <MagnifyingGlassIcon
            className="h-5 w-5 text-gray-400 dark:text-gray-500"
            aria-hidden="true"
          />
        </div>
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="w-full rounded-xl border border-gray-300 bg-white py-3 pl-11 pr-20 text-sm text-gray-900 placeholder:text-gray-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:placeholder:text-gray-500 dark:focus:border-primary-400"
          aria-label="Search query"
          data-testid="quick-search-input"
        />
        <div className="absolute inset-y-0 right-0 flex items-center pr-3">
          <kbd className="hidden sm:inline-flex items-center gap-1 rounded border border-gray-200 bg-gray-50 px-2 py-0.5 text-xs text-gray-400 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-500">
            <span className="text-2xs">Ctrl</span>
            <span>K</span>
          </kbd>
        </div>
      </div>
    </form>
  );
};

export default QuickSearch;
