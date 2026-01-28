/**
 * useDashboardStats - Dashboard statistics API hook
 *
 * Fetches dashboard statistics (total documents, searches, active users, indexing rate)
 * using React Query with auto-refresh every 60 seconds.
 */
import { useQuery } from '@tanstack/react-query';
import {
  dashboardService,
  type DashboardStats,
} from '@/services/dashboardService';

/** Query key for dashboard stats */
export const DASHBOARD_STATS_QUERY_KEY = ['dashboard', 'stats'] as const;

/** Default refetch interval: 60 seconds */
const REFETCH_INTERVAL = 60_000;

export interface UseDashboardStatsOptions {
  /** Whether the query is enabled (default: true) */
  enabled?: boolean;
  /** Refetch interval in milliseconds (default: 60000) */
  refetchInterval?: number;
}

/**
 * Custom hook for fetching dashboard statistics.
 *
 * @param options - Query options
 * @returns React Query result with DashboardStats data
 *
 * @example
 * ```tsx
 * const { data: stats, isLoading, isError } = useDashboardStats();
 * ```
 */
export const useDashboardStats = (options: UseDashboardStatsOptions = {}) => {
  const { enabled = true, refetchInterval = REFETCH_INTERVAL } = options;

  return useQuery<DashboardStats>({
    queryKey: [...DASHBOARD_STATS_QUERY_KEY],
    queryFn: () => dashboardService.getStats(),
    enabled,
    refetchInterval,
    staleTime: 30_000,
  });
};

export default useDashboardStats;
