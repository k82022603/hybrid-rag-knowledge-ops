/**
 * useRecentSearches hook tests
 *
 * Tests for the recent search history management hook.
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useRecentSearches } from '../hooks/useRecentSearches';

describe('useRecentSearches', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('returns empty searches initially', () => {
    const { result } = renderHook(() => useRecentSearches());

    expect(result.current.searches).toEqual([]);
    expect(result.current.displaySearches).toEqual([]);
    expect(result.current.totalCount).toBe(0);
  });

  it('adds a search item', () => {
    const { result } = renderHook(() => useRecentSearches());

    act(() => {
      result.current.addSearch('test query');
    });

    expect(result.current.searches).toHaveLength(1);
    expect(result.current.searches[0].query).toBe('test query');
  });

  it('adds search with result count', () => {
    const { result } = renderHook(() => useRecentSearches());

    act(() => {
      result.current.addSearch('test query', 42);
    });

    expect(result.current.searches[0].resultCount).toBe(42);
  });

  it('deduplicates searches by query (case-insensitive)', () => {
    const { result } = renderHook(() => useRecentSearches());

    act(() => {
      result.current.addSearch('Test Query');
    });
    act(() => {
      result.current.addSearch('test query');
    });

    expect(result.current.searches).toHaveLength(1);
    expect(result.current.searches[0].query).toBe('test query');
  });

  it('prepends new items (most recent first)', () => {
    const { result } = renderHook(() => useRecentSearches());

    act(() => {
      result.current.addSearch('first');
    });
    act(() => {
      result.current.addSearch('second');
    });

    expect(result.current.searches[0].query).toBe('second');
    expect(result.current.searches[1].query).toBe('first');
  });

  it('limits displaySearches to displayCount', () => {
    const { result } = renderHook(() =>
      useRecentSearches({ displayCount: 3 })
    );

    act(() => {
      result.current.addSearch('one');
      result.current.addSearch('two');
      result.current.addSearch('three');
      result.current.addSearch('four');
      result.current.addSearch('five');
    });

    expect(result.current.searches).toHaveLength(5);
    expect(result.current.displaySearches).toHaveLength(3);
  });

  it('limits total stored items to maxItems', () => {
    const { result } = renderHook(() =>
      useRecentSearches({ maxItems: 3 })
    );

    act(() => {
      for (let i = 0; i < 5; i++) {
        result.current.addSearch(`query ${i}`);
      }
    });

    expect(result.current.searches).toHaveLength(3);
  });

  it('removes a search by ID', () => {
    const { result } = renderHook(() => useRecentSearches());

    act(() => {
      result.current.addSearch('to remove');
      result.current.addSearch('to keep');
    });

    const idToRemove = result.current.searches[1].id;

    act(() => {
      result.current.removeSearch(idToRemove);
    });

    expect(result.current.searches).toHaveLength(1);
    expect(result.current.searches[0].query).toBe('to keep');
  });

  it('clears all searches', () => {
    const { result } = renderHook(() => useRecentSearches());

    act(() => {
      result.current.addSearch('one');
      result.current.addSearch('two');
    });

    act(() => {
      result.current.clearAll();
    });

    expect(result.current.searches).toHaveLength(0);
    expect(result.current.totalCount).toBe(0);
  });

  it('persists searches to localStorage', () => {
    const { result } = renderHook(() => useRecentSearches());

    act(() => {
      result.current.addSearch('persisted query');
    });

    const stored = JSON.parse(localStorage.getItem('kp_recent_searches') || '[]');
    expect(stored).toHaveLength(1);
    expect(stored[0].query).toBe('persisted query');
  });

  it('loads searches from localStorage on mount', () => {
    const storedItems = [
      {
        id: 'test_1',
        query: 'stored query',
        timestamp: new Date().toISOString(),
      },
    ];
    localStorage.setItem('kp_recent_searches', JSON.stringify(storedItems));

    const { result } = renderHook(() => useRecentSearches());

    expect(result.current.searches).toHaveLength(1);
    expect(result.current.searches[0].query).toBe('stored query');
  });

  it('generates unique IDs for each search', () => {
    const { result } = renderHook(() => useRecentSearches());

    act(() => {
      result.current.addSearch('first');
      result.current.addSearch('second');
    });

    const ids = result.current.searches.map((s) => s.id);
    const uniqueIds = new Set(ids);
    expect(uniqueIds.size).toBe(ids.length);
  });
});
