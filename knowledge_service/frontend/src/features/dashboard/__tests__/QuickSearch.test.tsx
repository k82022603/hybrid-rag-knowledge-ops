/**
 * QuickSearch component tests
 *
 * Tests for the dashboard quick search component.
 * AC4: Quick search input navigates to search page on Enter.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import QuickSearch from '../components/QuickSearch';

// Mock react-router-dom navigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const renderQuickSearch = (props = {}) => {
  return render(
    <MemoryRouter>
      <QuickSearch {...props} />
    </MemoryRouter>
  );
};

describe('QuickSearch', () => {
  beforeEach(() => {
    mockNavigate.mockClear();
  });

  it('renders search input with placeholder', () => {
    renderQuickSearch();

    const input = screen.getByTestId('quick-search-input');
    expect(input).toBeInTheDocument();
    expect(input).toHaveAttribute(
      'placeholder',
      'Search knowledge base... (Ctrl+K)'
    );
  });

  it('renders custom placeholder', () => {
    renderQuickSearch({ placeholder: 'Custom placeholder' });

    const input = screen.getByTestId('quick-search-input');
    expect(input).toHaveAttribute('placeholder', 'Custom placeholder');
  });

  it('has correct role and aria-label', () => {
    renderQuickSearch();

    expect(screen.getByRole('search')).toBeInTheDocument();
    expect(screen.getByLabelText('Search query')).toBeInTheDocument();
  });

  it('updates input value on change', async () => {
    renderQuickSearch();

    const input = screen.getByTestId('quick-search-input');
    fireEvent.change(input, { target: { value: 'test query' } });

    expect(input).toHaveValue('test query');
  });

  it('navigates to search page on form submit (AC4)', async () => {
    renderQuickSearch();

    const input = screen.getByTestId('quick-search-input');
    fireEvent.change(input, { target: { value: 'knowledge graph' } });
    fireEvent.submit(input.closest('form')!);

    expect(mockNavigate).toHaveBeenCalledWith(
      '/search?q=knowledge%20graph'
    );
  });

  it('calls onSearch callback when submitted', () => {
    const onSearch = vi.fn();
    renderQuickSearch({ onSearch });

    const input = screen.getByTestId('quick-search-input');
    fireEvent.change(input, { target: { value: 'test' } });
    fireEvent.submit(input.closest('form')!);

    expect(onSearch).toHaveBeenCalledWith('test');
  });

  it('does not navigate when query is empty', () => {
    renderQuickSearch();

    const input = screen.getByTestId('quick-search-input');
    fireEvent.submit(input.closest('form')!);

    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it('does not navigate when query is only whitespace', () => {
    renderQuickSearch();

    const input = screen.getByTestId('quick-search-input');
    fireEvent.change(input, { target: { value: '   ' } });
    fireEvent.submit(input.closest('form')!);

    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it('trims whitespace from query before navigating', () => {
    renderQuickSearch();

    const input = screen.getByTestId('quick-search-input');
    fireEvent.change(input, { target: { value: '  test query  ' } });
    fireEvent.submit(input.closest('form')!);

    expect(mockNavigate).toHaveBeenCalledWith(
      '/search?q=test%20query'
    );
  });

  it('has correct data-testid', () => {
    renderQuickSearch();

    expect(screen.getByTestId('quick-search')).toBeInTheDocument();
  });
});
