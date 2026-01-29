/**
 * RecentSearches component tests
 *
 * Tests for the recent search history display.
 * AC3: Display the 5 most recent search records.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import RecentSearches, { RecentSearchesSkeleton } from '../components/RecentSearches';
import type { RecentSearchItem } from '../hooks/useRecentSearches';

// Mock react-router-dom navigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const mockSearches: RecentSearchItem[] = [
  {
    id: 'search_1',
    query: 'knowledge graph architecture',
    timestamp: new Date(Date.now() - 5 * 60 * 1000).toISOString(), // 5 min ago
    resultCount: 12,
  },
  {
    id: 'search_2',
    query: 'RAG pipeline optimization',
    timestamp: new Date(Date.now() - 60 * 60 * 1000).toISOString(), // 1 hour ago
    resultCount: 8,
  },
  {
    id: 'search_3',
    query: 'Elasticsearch vector search',
    timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(), // 2 hours ago
  },
  {
    id: 'search_4',
    query: 'Neo4j Cypher queries',
    timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(), // 1 day ago
    resultCount: 5,
  },
  {
    id: 'search_5',
    query: 'LangGraph workflow',
    timestamp: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(), // 3 days ago
    resultCount: 3,
  },
];

const renderRecentSearches = (props: Partial<React.ComponentProps<typeof RecentSearches>> = {}) => {
  return render(
    <MemoryRouter>
      <RecentSearches searches={mockSearches} {...props} />
    </MemoryRouter>
  );
};

describe('RecentSearches', () => {
  beforeEach(() => {
    mockNavigate.mockClear();
  });

  it('renders all search items (AC3)', () => {
    renderRecentSearches();

    expect(screen.getByText('knowledge graph architecture')).toBeInTheDocument();
    expect(screen.getByText('RAG pipeline optimization')).toBeInTheDocument();
    expect(screen.getByText('Elasticsearch vector search')).toBeInTheDocument();
    expect(screen.getByText('Neo4j Cypher queries')).toBeInTheDocument();
    expect(screen.getByText('LangGraph workflow')).toBeInTheDocument();
  });

  it('displays exactly 5 search items (AC3)', () => {
    renderRecentSearches();

    const items = screen.getAllByTestId('recent-search-item');
    expect(items).toHaveLength(5);
  });

  it('shows empty state when no searches', () => {
    render(
      <MemoryRouter>
        <RecentSearches searches={[]} />
      </MemoryRouter>
    );

    expect(screen.getByTestId('recent-searches-empty')).toBeInTheDocument();
    expect(screen.getByText('No recent searches yet.')).toBeInTheDocument();
  });

  it('navigates to search page on click', () => {
    renderRecentSearches();

    const firstItem = screen.getByLabelText('Search for: knowledge graph architecture');
    fireEvent.click(firstItem);

    expect(mockNavigate).toHaveBeenCalledWith(
      '/search?q=knowledge%20graph%20architecture'
    );
  });

  it('calls onSearchClick callback when item is clicked', () => {
    const onSearchClick = vi.fn();
    renderRecentSearches({ onSearchClick });

    const firstItem = screen.getByLabelText('Search for: knowledge graph architecture');
    fireEvent.click(firstItem);

    expect(onSearchClick).toHaveBeenCalledWith('knowledge graph architecture');
  });

  it('shows result count when available', () => {
    renderRecentSearches();

    expect(screen.getByText(/12 results/)).toBeInTheDocument();
    expect(screen.getByText(/8 results/)).toBeInTheDocument();
  });

  it('renders remove buttons when onRemove is provided', () => {
    const onRemove = vi.fn();
    renderRecentSearches({ onRemove });

    const removeButtons = screen.getAllByTestId('remove-search-item');
    expect(removeButtons.length).toBe(5);
  });

  it('calls onRemove with correct id when remove button clicked', () => {
    const onRemove = vi.fn();
    renderRecentSearches({ onRemove });

    const removeButtons = screen.getAllByTestId('remove-search-item');
    fireEvent.click(removeButtons[0]);

    expect(onRemove).toHaveBeenCalledWith('search_1');
  });

  it('renders clear all button when onClearAll is provided', () => {
    const onClearAll = vi.fn();
    renderRecentSearches({ onClearAll });

    expect(screen.getByTestId('clear-all-searches')).toBeInTheDocument();
  });

  it('calls onClearAll when clear all button clicked', () => {
    const onClearAll = vi.fn();
    renderRecentSearches({ onClearAll });

    fireEvent.click(screen.getByTestId('clear-all-searches'));
    expect(onClearAll).toHaveBeenCalled();
  });

  it('has correct data-testid', () => {
    renderRecentSearches();

    expect(screen.getByTestId('recent-searches')).toBeInTheDocument();
  });

  it('has accessible list role and label', () => {
    renderRecentSearches();

    expect(
      screen.getByRole('list', { name: 'Recent search history' })
    ).toBeInTheDocument();
  });
});

describe('RecentSearchesSkeleton', () => {
  it('renders skeleton with correct test id', () => {
    render(<RecentSearchesSkeleton />);

    expect(screen.getByTestId('recent-searches-skeleton')).toBeInTheDocument();
  });

  it('has animate-pulse class', () => {
    render(<RecentSearchesSkeleton />);

    const skeleton = screen.getByTestId('recent-searches-skeleton');
    expect(skeleton).toHaveClass('animate-pulse');
  });
});
