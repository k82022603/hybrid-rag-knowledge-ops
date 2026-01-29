/**
 * KeywordSearch component tests
 *
 * Tests for the keyword search page component:
 * - Search input and form submission
 * - Loading and error states
 * - Results display
 * - Filters toggle and display
 * - Pagination
 * - AI answer display
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import KeywordSearch from '../KeywordSearch';
import type { SearchResultItem } from '../types';

// Mock useKeywordSearch hook
const mockUseKeywordSearch = vi.fn();

vi.mock('../hooks/useKeywordSearch', () => ({
  useKeywordSearch: () => mockUseKeywordSearch(),
  default: () => mockUseKeywordSearch(),
}));

// Mock SearchFilters component
vi.mock('@/components/search/SearchFilters', () => ({
  default: ({ filters, onFilterChange }: { filters: object; onFilterChange: (f: object) => void }) => (
    <div data-testid="search-filters-mock">
      <button onClick={() => onFilterChange({ documentType: 'test' })}>
        Change Filter
      </button>
      <span>{JSON.stringify(filters)}</span>
    </div>
  ),
}));

// Mock SearchResultCard component
vi.mock('../components/SearchResultCard', () => ({
  default: ({ result }: { result: SearchResultItem }) => (
    <div data-testid={`result-card-${result.chunkId}`}>
      <span>{result.content}</span>
      <span>{result.score}</span>
    </div>
  ),
}));

const mockResult: SearchResultItem = {
  chunkId: 'chunk-1',
  documentId: 'doc-1',
  content: 'Test content',
  score: 0.85,
  metadata: {
    documentType: 'technical',
    projectName: 'Project A',
  },
};

const defaultHookReturn = {
  query: '',
  setQuery: vi.fn(),
  submittedQuery: '',
  filters: {},
  showFilters: false,
  toggleFilters: vi.fn(),
  setFilters: vi.fn(),
  page: 1,
  totalPages: 1,
  totalCount: 0,
  results: [],
  answer: undefined,
  isLoading: false,
  isError: false,
  error: null,
  handleSearch: vi.fn((e: Event) => e.preventDefault()),
  goToPage: vi.fn(),
  hasActiveFilters: false,
};

describe('KeywordSearch', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseKeywordSearch.mockReturnValue(defaultHookReturn);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ===== Rendering =====

  describe('rendering', () => {
    it('should render the keyword search container', () => {
      render(<KeywordSearch />);

      expect(screen.getByTestId('keyword-search')).toBeInTheDocument();
    });

    it('should render search input', () => {
      render(<KeywordSearch />);

      expect(screen.getByTestId('keyword-search-input')).toBeInTheDocument();
    });

    it('should render search submit button', () => {
      render(<KeywordSearch />);

      expect(screen.getByTestId('keyword-search-submit')).toBeInTheDocument();
    });

    it('should render filters toggle button', () => {
      render(<KeywordSearch />);

      expect(
        screen.getByRole('button', { name: /show filters/i })
      ).toBeInTheDocument();
    });

    it('should render placeholder text in input', () => {
      render(<KeywordSearch />);

      expect(
        screen.getByPlaceholderText('Enter search keywords...')
      ).toBeInTheDocument();
    });
  });

  // ===== Empty State =====

  describe('empty state', () => {
    it('should show empty state when no query submitted', () => {
      render(<KeywordSearch />);

      expect(screen.getByText('Enter keywords to search')).toBeInTheDocument();
      expect(
        screen.getByText(
          'Search through documents, reports, and knowledge articles'
        )
      ).toBeInTheDocument();
    });
  });

  // ===== Loading State =====

  describe('loading state', () => {
    it('should show loading spinner when isLoading is true', () => {
      mockUseKeywordSearch.mockReturnValue({
        ...defaultHookReturn,
        submittedQuery: 'test',
        isLoading: true,
      });

      render(<KeywordSearch />);

      // Check the visible loading state (use getAllByRole since LiveRegion also has role="status")
      const statusElements = screen.getAllByRole('status');
      expect(statusElements.length).toBeGreaterThan(0);
    });

    it('should disable submit button when loading', () => {
      mockUseKeywordSearch.mockReturnValue({
        ...defaultHookReturn,
        query: 'test',
        isLoading: true,
      });

      render(<KeywordSearch />);

      expect(screen.getByTestId('keyword-search-submit')).toBeDisabled();
    });
  });

  // ===== Error State =====

  describe('error state', () => {
    it('should show error message when isError is true', () => {
      mockUseKeywordSearch.mockReturnValue({
        ...defaultHookReturn,
        submittedQuery: 'test',
        isError: true,
        error: { message: 'Network error' },
      });

      render(<KeywordSearch />);

      expect(screen.getByText('Search failed')).toBeInTheDocument();
      expect(screen.getByText('Network error')).toBeInTheDocument();
    });

    it('should show default error message when error has no message', () => {
      mockUseKeywordSearch.mockReturnValue({
        ...defaultHookReturn,
        submittedQuery: 'test',
        isError: true,
        error: null,
      });

      render(<KeywordSearch />);

      expect(screen.getByText('Search failed')).toBeInTheDocument();
      expect(
        screen.getByText('An unexpected error occurred.')
      ).toBeInTheDocument();
    });
  });

  // ===== No Results =====

  describe('no results state', () => {
    it('should show no results message when results are empty', () => {
      mockUseKeywordSearch.mockReturnValue({
        ...defaultHookReturn,
        submittedQuery: 'test query',
        results: [],
        totalCount: 0,
      });

      render(<KeywordSearch />);

      // Use heading role to target the visible message, not the LiveRegion
      expect(screen.getByRole('heading', { name: 'No results found' })).toBeInTheDocument();
      expect(
        screen.getByText('Try different keywords or adjust your filters')
      ).toBeInTheDocument();
    });
  });

  // ===== Results Display =====

  describe('results display', () => {
    it('should display result count', () => {
      mockUseKeywordSearch.mockReturnValue({
        ...defaultHookReturn,
        submittedQuery: 'test query',
        results: [mockResult],
        totalCount: 42,
      });

      render(<KeywordSearch />);

      expect(screen.getByText('42')).toBeInTheDocument();
      // submittedQuery is inside a span, so search for it specifically
      expect(screen.getByText('test query')).toBeInTheDocument();
    });

    it('should render search result cards', () => {
      mockUseKeywordSearch.mockReturnValue({
        ...defaultHookReturn,
        submittedQuery: 'test',
        results: [
          mockResult,
          { ...mockResult, chunkId: 'chunk-2', content: 'Second result' },
        ],
        totalCount: 2,
      });

      render(<KeywordSearch />);

      expect(screen.getByTestId('result-card-chunk-1')).toBeInTheDocument();
      expect(screen.getByTestId('result-card-chunk-2')).toBeInTheDocument();
    });
  });

  // ===== AI Answer =====

  describe('AI answer display', () => {
    it('should display AI answer when available', () => {
      mockUseKeywordSearch.mockReturnValue({
        ...defaultHookReturn,
        submittedQuery: 'test',
        results: [mockResult],
        totalCount: 1,
        answer: 'This is the AI-generated answer.',
      });

      render(<KeywordSearch />);

      expect(screen.getByText('AI Answer')).toBeInTheDocument();
      expect(
        screen.getByText('This is the AI-generated answer.')
      ).toBeInTheDocument();
    });

    it('should not show AI answer section when answer is undefined', () => {
      mockUseKeywordSearch.mockReturnValue({
        ...defaultHookReturn,
        submittedQuery: 'test',
        results: [mockResult],
        totalCount: 1,
        answer: undefined,
      });

      render(<KeywordSearch />);

      expect(screen.queryByText('AI Answer')).not.toBeInTheDocument();
    });
  });

  // ===== Filters =====

  describe('filters', () => {
    it('should not show filters panel by default', () => {
      render(<KeywordSearch />);

      expect(
        screen.queryByTestId('search-filters-mock')
      ).not.toBeInTheDocument();
    });

    it('should show filters panel when showFilters is true', () => {
      mockUseKeywordSearch.mockReturnValue({
        ...defaultHookReturn,
        showFilters: true,
      });

      render(<KeywordSearch />);

      expect(screen.getByTestId('search-filters-mock')).toBeInTheDocument();
    });

    it('should call toggleFilters when filter button is clicked', () => {
      const mockToggleFilters = vi.fn();
      mockUseKeywordSearch.mockReturnValue({
        ...defaultHookReturn,
        toggleFilters: mockToggleFilters,
      });

      render(<KeywordSearch />);

      fireEvent.click(screen.getByRole('button', { name: /show filters/i }));

      expect(mockToggleFilters).toHaveBeenCalled();
    });

    it('should show active filter count badge', () => {
      mockUseKeywordSearch.mockReturnValue({
        ...defaultHookReturn,
        filters: { documentType: 'guide', projectName: 'project-a' },
        hasActiveFilters: true,
      });

      render(<KeywordSearch />);

      // Badge should show count of active filters (2)
      expect(screen.getByText('2')).toBeInTheDocument();
    });

    it('should call setFilters when filter changes', () => {
      const mockSetFilters = vi.fn();
      mockUseKeywordSearch.mockReturnValue({
        ...defaultHookReturn,
        showFilters: true,
        setFilters: mockSetFilters,
      });

      render(<KeywordSearch />);

      fireEvent.click(screen.getByText('Change Filter'));

      expect(mockSetFilters).toHaveBeenCalledWith({ documentType: 'test' });
    });
  });

  // ===== Search Form =====

  describe('search form', () => {
    it('should call setQuery when input value changes', () => {
      const mockSetQuery = vi.fn();
      mockUseKeywordSearch.mockReturnValue({
        ...defaultHookReturn,
        setQuery: mockSetQuery,
      });

      render(<KeywordSearch />);

      fireEvent.change(screen.getByTestId('keyword-search-input'), {
        target: { value: 'new query' },
      });

      expect(mockSetQuery).toHaveBeenCalledWith('new query');
    });

    it('should call handleSearch when form is submitted', () => {
      const mockHandleSearch = vi.fn((e: Event) => e.preventDefault());
      mockUseKeywordSearch.mockReturnValue({
        ...defaultHookReturn,
        query: 'test',
        handleSearch: mockHandleSearch,
      });

      render(<KeywordSearch />);

      fireEvent.click(screen.getByTestId('keyword-search-submit'));

      expect(mockHandleSearch).toHaveBeenCalled();
    });

    it('should disable submit button when query is empty', () => {
      mockUseKeywordSearch.mockReturnValue({
        ...defaultHookReturn,
        query: '',
      });

      render(<KeywordSearch />);

      expect(screen.getByTestId('keyword-search-submit')).toBeDisabled();
    });

    it('should disable submit button when query is only whitespace', () => {
      mockUseKeywordSearch.mockReturnValue({
        ...defaultHookReturn,
        query: '   ',
      });

      render(<KeywordSearch />);

      expect(screen.getByTestId('keyword-search-submit')).toBeDisabled();
    });

    it('should enable submit button when query has content', () => {
      mockUseKeywordSearch.mockReturnValue({
        ...defaultHookReturn,
        query: 'valid query',
      });

      render(<KeywordSearch />);

      expect(screen.getByTestId('keyword-search-submit')).not.toBeDisabled();
    });
  });

  // ===== Pagination =====

  describe('pagination', () => {
    it('should not show pagination when only one page', () => {
      mockUseKeywordSearch.mockReturnValue({
        ...defaultHookReturn,
        submittedQuery: 'test',
        results: [mockResult],
        totalCount: 5,
        totalPages: 1,
        page: 1,
      });

      render(<KeywordSearch />);

      expect(screen.queryByText('Previous')).not.toBeInTheDocument();
      expect(screen.queryByText('Next')).not.toBeInTheDocument();
    });

    it('should show pagination when multiple pages exist', () => {
      mockUseKeywordSearch.mockReturnValue({
        ...defaultHookReturn,
        submittedQuery: 'test',
        results: [mockResult],
        totalCount: 50,
        totalPages: 5,
        page: 2,
      });

      render(<KeywordSearch />);

      expect(screen.getByText('Previous')).toBeInTheDocument();
      expect(screen.getByText('Next')).toBeInTheDocument();
      expect(screen.getByText('Page 2 of 5')).toBeInTheDocument();
    });

    it('should disable Previous button on first page', () => {
      mockUseKeywordSearch.mockReturnValue({
        ...defaultHookReturn,
        submittedQuery: 'test',
        results: [mockResult],
        totalCount: 50,
        totalPages: 5,
        page: 1,
      });

      render(<KeywordSearch />);

      expect(screen.getByText('Previous').closest('button')).toBeDisabled();
    });

    it('should disable Next button on last page', () => {
      mockUseKeywordSearch.mockReturnValue({
        ...defaultHookReturn,
        submittedQuery: 'test',
        results: [mockResult],
        totalCount: 50,
        totalPages: 5,
        page: 5,
      });

      render(<KeywordSearch />);

      expect(screen.getByText('Next').closest('button')).toBeDisabled();
    });

    it('should call goToPage with previous page number', () => {
      const mockGoToPage = vi.fn();
      mockUseKeywordSearch.mockReturnValue({
        ...defaultHookReturn,
        submittedQuery: 'test',
        results: [mockResult],
        totalCount: 50,
        totalPages: 5,
        page: 3,
        goToPage: mockGoToPage,
      });

      render(<KeywordSearch />);

      fireEvent.click(screen.getByText('Previous'));

      expect(mockGoToPage).toHaveBeenCalledWith(2);
    });

    it('should call goToPage with next page number', () => {
      const mockGoToPage = vi.fn();
      mockUseKeywordSearch.mockReturnValue({
        ...defaultHookReturn,
        submittedQuery: 'test',
        results: [mockResult],
        totalCount: 50,
        totalPages: 5,
        page: 3,
        goToPage: mockGoToPage,
      });

      render(<KeywordSearch />);

      fireEvent.click(screen.getByText('Next'));

      expect(mockGoToPage).toHaveBeenCalledWith(4);
    });
  });

  // ===== Accessibility =====

  describe('accessibility', () => {
    it('should have aria-label on search input', () => {
      render(<KeywordSearch />);

      expect(screen.getByTestId('keyword-search-input')).toHaveAttribute(
        'aria-label',
        'Search keywords'
      );
    });

    it('should have aria-label on filter toggle button', () => {
      render(<KeywordSearch />);

      expect(
        screen.getByRole('button', { name: /show filters/i })
      ).toHaveAttribute('aria-label', 'Show filters');
    });
  });
});
