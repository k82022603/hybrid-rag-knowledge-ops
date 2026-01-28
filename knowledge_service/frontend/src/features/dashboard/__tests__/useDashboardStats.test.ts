/**
 * useDashboardStats hook tests
 *
 * Tests for the dashboard statistics React Query hook.
 */
import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useDashboardStats, DASHBOARD_STATS_QUERY_KEY } from '../hooks/useDashboardStats';

// Mock the dashboard service
const mockGetStats = vi.fn();
vi.mock('@/services/dashboardService', () => ({
  dashboardService: {
    getStats: (...args: unknown[]) => mockGetStats(...args),
  },
}));

const createQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: 0,
      },
    },
  });

const createWrapper = () => {
  const queryClient = createQueryClient();
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
};

describe('useDashboardStats', () => {
  it('exports correct query key', () => {
    expect(DASHBOARD_STATS_QUERY_KEY).toEqual(['dashboard', 'stats']);
  });

  it('fetches stats successfully', async () => {
    const mockStats = {
      totalDocuments: 100,
      totalSearches: 500,
      activeUsers: 25,
      indexingRate: 95,
      documentsToday: 5,
      searchesToday: 30,
    };
    mockGetStats.mockResolvedValue(mockStats);

    const { result } = renderHook(() => useDashboardStats(), {
      wrapper: createWrapper(),
    });

    // Initially loading
    expect(result.current.isLoading).toBe(true);

    // Wait for data
    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockStats);
  });

  it('handles error state', async () => {
    mockGetStats.mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => useDashboardStats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
  });

  it('respects enabled option', () => {
    const { result } = renderHook(
      () => useDashboardStats({ enabled: false }),
      { wrapper: createWrapper() }
    );

    expect(result.current.isLoading).toBe(false);
    expect(result.current.fetchStatus).toBe('idle');
  });
});
