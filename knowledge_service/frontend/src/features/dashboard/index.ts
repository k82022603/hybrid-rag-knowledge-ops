/**
 * Dashboard feature module exports
 *
 * STORY-041: Dashboard UI implementation
 */

// Main component
export { default as Dashboard } from './Dashboard';

// Sub-components
export { default as StatCard } from './components/StatCard';
export { StatCardSkeleton } from './components/StatCard';
export type { StatCardProps } from './components/StatCard';

export { default as QuickSearch } from './components/QuickSearch';
export type { QuickSearchProps } from './components/QuickSearch';

export { default as RecentSearches } from './components/RecentSearches';
export { RecentSearchesSkeleton } from './components/RecentSearches';
export type { RecentSearchesProps } from './components/RecentSearches';

// Hooks
export { useDashboardStats, DASHBOARD_STATS_QUERY_KEY } from './hooks/useDashboardStats';
export type { UseDashboardStatsOptions } from './hooks/useDashboardStats';

export { useRecentSearches } from './hooks/useRecentSearches';
export type { RecentSearchItem, UseRecentSearchesOptions } from './hooks/useRecentSearches';
