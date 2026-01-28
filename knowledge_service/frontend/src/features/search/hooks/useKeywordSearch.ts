/**
 * useKeywordSearch - Keyword search custom hook
 *
 * Manages keyword search state including query, filters,
 * pagination, and React Query integration.
 */
import { useState, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  searchService,
  type SearchQuery,
  type SearchResponse,
} from '@/services/searchService';
import type { SearchFilters } from '../types';

export interface UseKeywordSearchReturn {
  /** Current query input value */
  query: string;
  /** Set query input value */
  setQuery: (value: string) => void;
  /** The query that was actually submitted */
  submittedQuery: string;
  /** Current filter values */
  filters: SearchFilters;
  /** Whether filters panel is visible */
  showFilters: boolean;
  /** Toggle filters panel visibility */
  toggleFilters: () => void;
  /** Update filters */
  setFilters: (filters: SearchFilters) => void;
  /** Current page number */
  page: number;
  /** Total number of pages */
  totalPages: number;
  /** Total result count */
  totalCount: number;
  /** Search results */
  results: SearchResponse['results'];
  /** AI-generated answer */
  answer?: string;
  /** Whether search is loading */
  isLoading: boolean;
  /** Whether search had an error */
  isError: boolean;
  /** Error object */
  error: Error | null;
  /** Submit the search */
  handleSearch: (e: React.FormEvent) => void;
  /** Go to a specific page */
  goToPage: (page: number) => void;
  /** Whether any filters are active */
  hasActiveFilters: boolean;
}

const PAGE_SIZE = 10;

/**
 * Custom hook for keyword search with filters and pagination.
 */
export const useKeywordSearch = (): UseKeywordSearchReturn => {
  const [query, setQuery] = useState('');
  const [submittedQuery, setSubmittedQuery] = useState('');
  const [filters, setFiltersState] = useState<SearchFilters>({});
  const [page, setPage] = useState(1);
  const [showFilters, setShowFilters] = useState(false);

  // React Query for keyword search
  const {
    data: searchData,
    isLoading,
    isError,
    error,
  } = useQuery<SearchResponse>({
    queryKey: ['keyword-search', submittedQuery, filters, page],
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
        pageSize: PAGE_SIZE,
      };
      return searchService.search(params);
    },
    enabled: !!submittedQuery,
  });

  const results = searchData?.results ?? [];
  const totalCount = searchData?.totalCount ?? 0;
  const totalPages = Math.ceil(totalCount / PAGE_SIZE);
  const answer = searchData?.answer;

  /** Submit the search form */
  const handleSearch = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!query.trim()) return;
      setSubmittedQuery(query.trim());
      setPage(1);
    },
    [query]
  );

  /** Update filters and reset page */
  const setFilters = useCallback((newFilters: SearchFilters) => {
    setFiltersState(newFilters);
    setPage(1);
  }, []);

  /** Toggle filters panel */
  const toggleFilters = useCallback(() => {
    setShowFilters((prev) => !prev);
  }, []);

  /** Navigate to a specific page */
  const goToPage = useCallback((newPage: number) => {
    setPage(Math.max(1, newPage));
  }, []);

  const hasActiveFilters = Object.values(filters).some(Boolean);

  return {
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
    error: error instanceof Error ? error : null,
    handleSearch,
    goToPage,
    hasActiveFilters,
  };
};

export default useKeywordSearch;
