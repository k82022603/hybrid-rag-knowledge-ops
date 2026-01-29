/**
 * useKeywordSearch hook tests
 *
 * Tests for the keyword search custom hook:
 * - Query state management
 * - Filter state management
 * - Pagination controls
 * - React Query integration
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useKeywordSearch } from '../hooks/useKeywordSearch';
import type { ReactNode } from 'react';

// Mock searchService
const mockSearch = vi.fn();

vi.mock('@/services/searchService', () => ({
  searchService: {
    search: (params: unknown) => mockSearch(params),
  },
}));

// Create wrapper with React Query provider
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('useKeywordSearch', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSearch.mockResolvedValue({
      results: [],
      totalCount: 0,
      answer: undefined,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ===== Initial State =====

  describe('initial state', () => {
    it('should have empty query', () => {
      const { result } = renderHook(() => useKeywordSearch(), {
        wrapper: createWrapper(),
      });

      expect(result.current.query).toBe('');
    });

    it('should have empty submittedQuery', () => {
      const { result } = renderHook(() => useKeywordSearch(), {
        wrapper: createWrapper(),
      });

      expect(result.current.submittedQuery).toBe('');
    });

    it('should have empty filters', () => {
      const { result } = renderHook(() => useKeywordSearch(), {
        wrapper: createWrapper(),
      });

      expect(result.current.filters).toEqual({});
    });

    it('should have showFilters as false', () => {
      const { result } = renderHook(() => useKeywordSearch(), {
        wrapper: createWrapper(),
      });

      expect(result.current.showFilters).toBe(false);
    });

    it('should have page as 1', () => {
      const { result } = renderHook(() => useKeywordSearch(), {
        wrapper: createWrapper(),
      });

      expect(result.current.page).toBe(1);
    });

    it('should have empty results', () => {
      const { result } = renderHook(() => useKeywordSearch(), {
        wrapper: createWrapper(),
      });

      expect(result.current.results).toEqual([]);
    });

    it('should have totalCount as 0', () => {
      const { result } = renderHook(() => useKeywordSearch(), {
        wrapper: createWrapper(),
      });

      expect(result.current.totalCount).toBe(0);
    });

    it('should have totalPages as 0', () => {
      const { result } = renderHook(() => useKeywordSearch(), {
        wrapper: createWrapper(),
      });

      expect(result.current.totalPages).toBe(0);
    });

    it('should not be loading initially', () => {
      const { result } = renderHook(() => useKeywordSearch(), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(false);
    });

    it('should have no error initially', () => {
      const { result } = renderHook(() => useKeywordSearch(), {
        wrapper: createWrapper(),
      });

      expect(result.current.isError).toBe(false);
      expect(result.current.error).toBe(null);
    });

    it('should have hasActiveFilters as false', () => {
      const { result } = renderHook(() => useKeywordSearch(), {
        wrapper: createWrapper(),
      });

      expect(result.current.hasActiveFilters).toBe(false);
    });
  });

  // ===== Query Management =====

  describe('query management', () => {
    it('should update query when setQuery is called', () => {
      const { result } = renderHook(() => useKeywordSearch(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.setQuery('test query');
      });

      expect(result.current.query).toBe('test query');
    });

    it('should not trigger search when query changes without submit', () => {
      const { result } = renderHook(() => useKeywordSearch(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.setQuery('test');
      });

      expect(mockSearch).not.toHaveBeenCalled();
    });
  });

  // ===== Search Submission =====

  describe('search submission', () => {
    it('should update submittedQuery when handleSearch is called', () => {
      const { result } = renderHook(() => useKeywordSearch(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.setQuery('search term');
      });

      act(() => {
        const mockEvent = { preventDefault: vi.fn() } as unknown as React.FormEvent;
        result.current.handleSearch(mockEvent);
      });

      expect(result.current.submittedQuery).toBe('search term');
    });

    it('should call preventDefault on form event', () => {
      const { result } = renderHook(() => useKeywordSearch(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.setQuery('test');
      });

      const mockEvent = { preventDefault: vi.fn() } as unknown as React.FormEvent;

      act(() => {
        result.current.handleSearch(mockEvent);
      });

      expect(mockEvent.preventDefault).toHaveBeenCalled();
    });

    it('should trim query when submitting', () => {
      const { result } = renderHook(() => useKeywordSearch(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.setQuery('  trimmed query  ');
      });

      act(() => {
        const mockEvent = { preventDefault: vi.fn() } as unknown as React.FormEvent;
        result.current.handleSearch(mockEvent);
      });

      expect(result.current.submittedQuery).toBe('trimmed query');
    });

    it('should not submit empty query', () => {
      const { result } = renderHook(() => useKeywordSearch(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.setQuery('');
      });

      act(() => {
        const mockEvent = { preventDefault: vi.fn() } as unknown as React.FormEvent;
        result.current.handleSearch(mockEvent);
      });

      expect(result.current.submittedQuery).toBe('');
    });

    it('should not submit whitespace-only query', () => {
      const { result } = renderHook(() => useKeywordSearch(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.setQuery('   ');
      });

      act(() => {
        const mockEvent = { preventDefault: vi.fn() } as unknown as React.FormEvent;
        result.current.handleSearch(mockEvent);
      });

      expect(result.current.submittedQuery).toBe('');
    });

    it('should reset page to 1 when submitting', () => {
      const { result } = renderHook(() => useKeywordSearch(), {
        wrapper: createWrapper(),
      });

      // First set page to something other than 1
      act(() => {
        result.current.goToPage(3);
      });

      act(() => {
        result.current.setQuery('new search');
      });

      act(() => {
        const mockEvent = { preventDefault: vi.fn() } as unknown as React.FormEvent;
        result.current.handleSearch(mockEvent);
      });

      expect(result.current.page).toBe(1);
    });
  });

  // ===== Filters =====

  describe('filters', () => {
    it('should update filters when setFilters is called', () => {
      const { result } = renderHook(() => useKeywordSearch(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.setFilters({ documentType: 'guide' });
      });

      expect(result.current.filters).toEqual({ documentType: 'guide' });
    });

    it('should reset page to 1 when filters change', () => {
      const { result } = renderHook(() => useKeywordSearch(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.goToPage(5);
      });

      act(() => {
        result.current.setFilters({ projectName: 'project-a' });
      });

      expect(result.current.page).toBe(1);
    });

    it('should toggle showFilters when toggleFilters is called', () => {
      const { result } = renderHook(() => useKeywordSearch(), {
        wrapper: createWrapper(),
      });

      expect(result.current.showFilters).toBe(false);

      act(() => {
        result.current.toggleFilters();
      });

      expect(result.current.showFilters).toBe(true);

      act(() => {
        result.current.toggleFilters();
      });

      expect(result.current.showFilters).toBe(false);
    });

    it('should set hasActiveFilters to true when filters are set', () => {
      const { result } = renderHook(() => useKeywordSearch(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.setFilters({ documentType: 'technical' });
      });

      expect(result.current.hasActiveFilters).toBe(true);
    });

    it('should set hasActiveFilters to false when filters are cleared', () => {
      const { result } = renderHook(() => useKeywordSearch(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.setFilters({ documentType: 'guide' });
      });

      act(() => {
        result.current.setFilters({});
      });

      expect(result.current.hasActiveFilters).toBe(false);
    });

    it('should handle multiple filters', () => {
      const { result } = renderHook(() => useKeywordSearch(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.setFilters({
          documentType: 'report',
          projectName: 'project-b',
          dateFrom: '2024-01-01',
          dateTo: '2024-12-31',
        });
      });

      expect(result.current.filters).toEqual({
        documentType: 'report',
        projectName: 'project-b',
        dateFrom: '2024-01-01',
        dateTo: '2024-12-31',
      });
      expect(result.current.hasActiveFilters).toBe(true);
    });
  });

  // ===== Pagination =====

  describe('pagination', () => {
    it('should update page when goToPage is called', () => {
      const { result } = renderHook(() => useKeywordSearch(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.goToPage(3);
      });

      expect(result.current.page).toBe(3);
    });

    it('should not allow page less than 1', () => {
      const { result } = renderHook(() => useKeywordSearch(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.goToPage(0);
      });

      expect(result.current.page).toBe(1);

      act(() => {
        result.current.goToPage(-5);
      });

      expect(result.current.page).toBe(1);
    });

    it('should calculate totalPages correctly', async () => {
      mockSearch.mockResolvedValue({
        results: [{ chunkId: '1', content: 'test', score: 0.5 }],
        totalCount: 45,
      });

      const { result } = renderHook(() => useKeywordSearch(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.setQuery('test');
      });

      act(() => {
        const mockEvent = { preventDefault: vi.fn() } as unknown as React.FormEvent;
        result.current.handleSearch(mockEvent);
      });

      await waitFor(() => {
        // With PAGE_SIZE of 10, 45 results = 5 pages
        expect(result.current.totalPages).toBe(5);
      });
    });
  });

  // ===== React Query Integration =====

  describe('React Query integration', () => {
    it('should call searchService.search with correct params after submit', async () => {
      const { result } = renderHook(() => useKeywordSearch(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.setQuery('test query');
        result.current.setFilters({ documentType: 'guide' });
      });

      act(() => {
        const mockEvent = { preventDefault: vi.fn() } as unknown as React.FormEvent;
        result.current.handleSearch(mockEvent);
      });

      await waitFor(() => {
        expect(mockSearch).toHaveBeenCalledWith({
          query: 'test query',
          filters: {
            documentType: 'guide',
            projectName: undefined,
            dateFrom: undefined,
            dateTo: undefined,
          },
          page: 1,
          pageSize: 10,
        });
      });
    });

    it('should update results when search succeeds', async () => {
      const mockResults = [
        { chunkId: '1', content: 'Result 1', score: 0.9 },
        { chunkId: '2', content: 'Result 2', score: 0.8 },
      ];

      mockSearch.mockResolvedValue({
        results: mockResults,
        totalCount: 2,
        answer: 'AI generated answer',
      });

      const { result } = renderHook(() => useKeywordSearch(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.setQuery('test');
      });

      act(() => {
        const mockEvent = { preventDefault: vi.fn() } as unknown as React.FormEvent;
        result.current.handleSearch(mockEvent);
      });

      await waitFor(() => {
        expect(result.current.results).toEqual(mockResults);
        expect(result.current.totalCount).toBe(2);
        expect(result.current.answer).toBe('AI generated answer');
      });
    });

    it('should set isError when search fails', async () => {
      mockSearch.mockRejectedValue(new Error('Search failed'));

      const { result } = renderHook(() => useKeywordSearch(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.setQuery('test');
      });

      act(() => {
        const mockEvent = { preventDefault: vi.fn() } as unknown as React.FormEvent;
        result.current.handleSearch(mockEvent);
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
        expect(result.current.error).toBeInstanceOf(Error);
        expect(result.current.error?.message).toBe('Search failed');
      });
    });

    it('should not call search when query is not submitted', () => {
      renderHook(() => useKeywordSearch(), {
        wrapper: createWrapper(),
      });

      // No search submitted, so searchService should not be called
      expect(mockSearch).not.toHaveBeenCalled();
    });
  });
});
