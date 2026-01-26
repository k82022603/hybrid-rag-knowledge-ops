/**
 * DashboardPage - 대시보드 페이지
 *
 * 검색 통계, 시스템 상태, 사용자 활동 로그 시각화
 * Tailwind CSS + React Query 기반
 */
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  DocumentTextIcon,
  MagnifyingGlassIcon,
  UsersIcon,
  ArrowTrendingUpIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  ArrowUpTrayIcon,
  PencilIcon,
  ArrowRightStartOnRectangleIcon,
  ArrowDownTrayIcon,
  TrashIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline';
import {
  dashboardService,
  type DashboardStats,
  type RecentActivity,
  type SystemHealth,
  type SearchTrend,
  type PopularQuery,
  type DocumentTypeDistribution,
} from '@/services/dashboardService';

/**
 * StatCard - 통계 카드 컴포넌트
 */
interface StatCardProps {
  title: string;
  value: string;
  subtitle?: string;
  icon: React.ReactNode;
  iconBg: string;
  trend?: { value: number; isPositive: boolean };
}

const StatCard: React.FC<StatCardProps> = ({ title, value, subtitle, icon, iconBg, trend }) => (
  <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
    <div className="flex items-center gap-3 mb-3">
      <div className={`p-2.5 rounded-lg ${iconBg}`}>{icon}</div>
      <span className="text-sm font-medium text-gray-500 dark:text-gray-400">{title}</span>
    </div>
    <div className="flex items-end justify-between">
      <div>
        <p className="text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
        {subtitle && (
          <p className="mt-0.5 text-xs text-gray-400 dark:text-gray-500">{subtitle}</p>
        )}
      </div>
      {trend && (
        <span
          className={`inline-flex items-center text-xs font-medium ${
            trend.isPositive
              ? 'text-success-600 dark:text-success-400'
              : 'text-error-600 dark:text-error-400'
          }`}
        >
          {trend.isPositive ? '+' : ''}
          {trend.value}%
        </span>
      )}
    </div>
  </div>
);

/**
 * Activity icon mapping
 */
const ACTIVITY_ICONS: Record<string, React.ReactNode> = {
  search: <MagnifyingGlassIcon className="h-4 w-4" />,
  upload: <ArrowUpTrayIcon className="h-4 w-4" />,
  download: <ArrowDownTrayIcon className="h-4 w-4" />,
  edit: <PencilIcon className="h-4 w-4" />,
  delete: <TrashIcon className="h-4 w-4" />,
  login: <ArrowRightStartOnRectangleIcon className="h-4 w-4" />,
};

const ACTIVITY_COLORS: Record<string, string> = {
  search: 'bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400',
  upload: 'bg-success-100 dark:bg-success-900/30 text-success-600 dark:text-success-400',
  download: 'bg-accent-100 dark:bg-accent-900/30 text-accent-600 dark:text-accent-400',
  edit: 'bg-warning-100 dark:bg-warning-900/30 text-warning-600 dark:text-warning-400',
  delete: 'bg-error-100 dark:bg-error-900/30 text-error-600 dark:text-error-400',
  login: 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400',
};

/**
 * StatsSection - 통계 카드 영역
 */
const StatsSection: React.FC = () => {
  const { data: stats, isLoading, isError } = useQuery<DashboardStats>({
    queryKey: ['dashboard', 'stats'],
    queryFn: () => dashboardService.getStats(),
    refetchInterval: 60000,
  });

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div
            key={i}
            className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 animate-pulse"
          >
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-lg bg-gray-200 dark:bg-gray-700" />
              <div className="h-4 w-24 rounded bg-gray-200 dark:bg-gray-700" />
            </div>
            <div className="h-8 w-20 rounded bg-gray-200 dark:bg-gray-700" />
          </div>
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-xl p-4 flex items-center gap-3">
        <ExclamationTriangleIcon className="h-5 w-5 text-error-500 flex-shrink-0" />
        <p className="text-sm text-error-700 dark:text-error-300">
          Failed to load dashboard statistics.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
      <StatCard
        title="Total Documents"
        value={stats?.totalDocuments?.toLocaleString() ?? '0'}
        subtitle={`${stats?.documentsToday ?? 0} added today`}
        icon={<DocumentTextIcon className="h-5 w-5 text-primary-600 dark:text-primary-400" />}
        iconBg="bg-primary-50 dark:bg-primary-900/30"
      />
      <StatCard
        title="Search Queries"
        value={stats?.totalSearches?.toLocaleString() ?? '0'}
        subtitle={`${stats?.searchesToday ?? 0} today`}
        icon={<MagnifyingGlassIcon className="h-5 w-5 text-success-600 dark:text-success-400" />}
        iconBg="bg-success-50 dark:bg-success-900/30"
      />
      <StatCard
        title="Active Users"
        value={stats?.activeUsers?.toLocaleString() ?? '0'}
        icon={<UsersIcon className="h-5 w-5 text-accent-600 dark:text-accent-400" />}
        iconBg="bg-accent-50 dark:bg-accent-900/30"
      />
      <StatCard
        title="Indexing Rate"
        value={`${stats?.indexingRate ?? 0}%`}
        icon={<ArrowTrendingUpIcon className="h-5 w-5 text-warning-600 dark:text-warning-400" />}
        iconBg="bg-warning-50 dark:bg-warning-900/30"
      />
    </div>
  );
};

/**
 * SystemHealthSection - 시스템 상태 영역
 */
const SystemHealthSection: React.FC = () => {
  const { data: health, isLoading } = useQuery<SystemHealth>({
    queryKey: ['dashboard', 'health'],
    queryFn: () => dashboardService.getSystemHealth(),
    refetchInterval: 30000,
  });

  const statusColors: Record<string, string> = {
    up: 'text-success-500',
    down: 'text-error-500',
    degraded: 'text-warning-500',
  };

  const statusIcons: Record<string, React.ReactNode> = {
    up: <CheckCircleIcon className="h-4 w-4" />,
    down: <XCircleIcon className="h-4 w-4" />,
    degraded: <ExclamationTriangleIcon className="h-4 w-4" />,
  };

  const overallColors: Record<string, string> = {
    healthy: 'bg-success-50 text-success-700 border-success-200 dark:bg-success-900/30 dark:text-success-300 dark:border-success-800',
    degraded: 'bg-warning-50 text-warning-700 border-warning-200 dark:bg-warning-900/30 dark:text-warning-300 dark:border-warning-800',
    unhealthy: 'bg-error-50 text-error-700 border-error-200 dark:bg-error-900/30 dark:text-error-300 dark:border-error-800',
  };

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-3">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="flex items-center justify-between py-2">
            <div className="h-4 w-32 rounded bg-gray-200 dark:bg-gray-700" />
            <div className="h-4 w-12 rounded bg-gray-200 dark:bg-gray-700" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div>
      {/* Overall status */}
      {health?.overall && (
        <div
          className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border mb-4 ${
            overallColors[health.overall] || overallColors.degraded
          }`}
        >
          {health.overall === 'healthy' ? (
            <CheckCircleIcon className="h-3.5 w-3.5" />
          ) : (
            <ExclamationTriangleIcon className="h-3.5 w-3.5" />
          )}
          System {health.overall}
        </div>
      )}

      {/* Service list */}
      <ul className="space-y-2" role="list" aria-label="System services status">
        {health?.services?.map((service) => (
          <li
            key={service.name}
            className="flex items-center justify-between py-2 border-b border-gray-100 dark:border-gray-700 last:border-0"
          >
            <div className="flex items-center gap-2">
              <span className={statusColors[service.status] || statusColors.degraded}>
                {statusIcons[service.status]}
              </span>
              <span className="text-sm text-gray-900 dark:text-white">{service.name}</span>
            </div>
            <div className="flex items-center gap-2">
              {service.responseTime !== undefined && (
                <span className="text-xs text-gray-400 dark:text-gray-500">
                  {service.responseTime}ms
                </span>
              )}
              <span
                className={`inline-flex items-center px-2 py-0.5 rounded-full text-2xs font-medium ${
                  service.status === 'up'
                    ? 'bg-success-50 text-success-700 dark:bg-success-900/30 dark:text-success-400'
                    : service.status === 'down'
                    ? 'bg-error-50 text-error-700 dark:bg-error-900/30 dark:text-error-400'
                    : 'bg-warning-50 text-warning-700 dark:bg-warning-900/30 dark:text-warning-400'
                }`}
              >
                {service.status}
              </span>
            </div>
          </li>
        )) ?? (
          <li className="py-4 text-center text-sm text-gray-500 dark:text-gray-400">
            No services data available.
          </li>
        )}
      </ul>
    </div>
  );
};

/**
 * RecentActivitySection - 최근 활동 영역
 */
const RecentActivitySection: React.FC = () => {
  const { data: activities, isLoading, isError } = useQuery<RecentActivity[]>({
    queryKey: ['dashboard', 'activities'],
    queryFn: () => dashboardService.getRecentActivities(15),
    refetchInterval: 30000,
  });

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-3">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="flex items-center gap-3 py-2">
            <div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700" />
            <div className="flex-1 space-y-1">
              <div className="h-4 w-3/4 rounded bg-gray-200 dark:bg-gray-700" />
              <div className="h-3 w-1/2 rounded bg-gray-200 dark:bg-gray-700" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="py-8 text-center">
        <ExclamationTriangleIcon className="h-8 w-8 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Failed to load recent activity.
        </p>
      </div>
    );
  }

  if (!activities || activities.length === 0) {
    return (
      <div className="py-8 text-center">
        <ClockIcon className="h-8 w-8 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No recent activity.
        </p>
      </div>
    );
  }

  return (
    <ul className="space-y-0.5" role="list" aria-label="Recent activity">
      {activities.map((activity) => (
        <li
          key={activity.id}
          className="flex items-start gap-3 py-2.5 px-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors"
        >
          <div
            className={`mt-0.5 p-1.5 rounded-full flex-shrink-0 ${
              ACTIVITY_COLORS[activity.type] || ACTIVITY_COLORS.login
            }`}
          >
            {ACTIVITY_ICONS[activity.type] || <ClockIcon className="h-4 w-4" />}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-gray-900 dark:text-white">
              <span className="font-medium">{activity.userName}</span>{' '}
              <span className="text-gray-600 dark:text-gray-300">{activity.description}</span>
            </p>
            {activity.resourceName && (
              <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                {activity.resourceName}
              </p>
            )}
          </div>
          <span className="text-xs text-gray-400 dark:text-gray-500 whitespace-nowrap flex-shrink-0">
            {new Date(activity.timestamp).toLocaleString('ko-KR', {
              month: 'short',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
            })}
          </span>
        </li>
      ))}
    </ul>
  );
};

/**
 * SearchTrendsSection - 검색 트렌드 영역 (바 차트 대체)
 */
const SearchTrendsSection: React.FC = () => {
  const { data: trends, isLoading } = useQuery<SearchTrend[]>({
    queryKey: ['dashboard', 'search-trends'],
    queryFn: () => dashboardService.getSearchTrends(7),
    refetchInterval: 300000,
  });

  if (isLoading) {
    return (
      <div className="animate-pulse">
        <div className="flex items-end gap-2 h-32">
          {[...Array(7)].map((_, i) => (
            <div
              key={i}
              className="flex-1 rounded-t bg-gray-200 dark:bg-gray-700"
              style={{ height: `${Math.random() * 100}%` }}
            />
          ))}
        </div>
      </div>
    );
  }

  if (!trends || trends.length === 0) {
    return (
      <div className="py-8 text-center">
        <ChartBarIcon className="h-8 w-8 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
        <p className="text-sm text-gray-500 dark:text-gray-400">No search trend data.</p>
      </div>
    );
  }

  const maxCount = Math.max(...trends.map((t) => t.count), 1);

  return (
    <div>
      {/* Simple bar chart */}
      <div className="flex items-end gap-2 h-32" role="img" aria-label="Search trend chart">
        {trends.map((trend) => {
          const heightPercent = (trend.count / maxCount) * 100;
          return (
            <div key={trend.date} className="flex-1 flex flex-col items-center gap-1">
              <span className="text-2xs text-gray-500 dark:text-gray-400">{trend.count}</span>
              <div
                className="w-full rounded-t bg-primary-500 dark:bg-primary-400 transition-all duration-300"
                style={{ height: `${Math.max(heightPercent, 4)}%` }}
                title={`${trend.date}: ${trend.count} searches`}
              />
            </div>
          );
        })}
      </div>
      {/* Date labels */}
      <div className="flex gap-2 mt-2">
        {trends.map((trend) => (
          <div key={trend.date} className="flex-1 text-center">
            <span className="text-2xs text-gray-400 dark:text-gray-500">
              {new Date(trend.date).toLocaleDateString('ko-KR', {
                month: 'short',
                day: 'numeric',
              })}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

/**
 * PopularQueriesSection - 인기 검색어 영역
 */
const PopularQueriesSection: React.FC = () => {
  const { data: queries, isLoading } = useQuery<PopularQuery[]>({
    queryKey: ['dashboard', 'popular-queries'],
    queryFn: () => dashboardService.getPopularQueries(8),
    refetchInterval: 300000,
  });

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-2">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="flex items-center justify-between py-1.5">
            <div className="h-4 w-40 rounded bg-gray-200 dark:bg-gray-700" />
            <div className="h-4 w-8 rounded bg-gray-200 dark:bg-gray-700" />
          </div>
        ))}
      </div>
    );
  }

  if (!queries || queries.length === 0) {
    return (
      <div className="py-8 text-center">
        <MagnifyingGlassIcon className="h-8 w-8 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
        <p className="text-sm text-gray-500 dark:text-gray-400">No popular queries yet.</p>
      </div>
    );
  }

  const maxCount = Math.max(...queries.map((q) => q.count), 1);

  return (
    <ul className="space-y-2" role="list" aria-label="Popular search queries">
      {queries.map((query, index) => (
        <li
          key={query.query}
          className="flex items-center gap-3 py-1.5"
        >
          <span className="text-xs font-medium text-gray-400 dark:text-gray-500 w-5 text-right">
            {index + 1}
          </span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm text-gray-900 dark:text-white truncate">{query.query}</span>
              <span className="text-xs text-gray-500 dark:text-gray-400 ml-2 flex-shrink-0">
                {query.count}
              </span>
            </div>
            <div className="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-1">
              <div
                className="bg-primary-500 dark:bg-primary-400 h-1 rounded-full transition-all duration-300"
                style={{ width: `${(query.count / maxCount) * 100}%` }}
              />
            </div>
          </div>
        </li>
      ))}
    </ul>
  );
};

/**
 * DocumentDistributionSection - 문서 유형 분포 영역
 */
const DocumentDistributionSection: React.FC = () => {
  const { data: distribution, isLoading } = useQuery<DocumentTypeDistribution[]>({
    queryKey: ['dashboard', 'document-types'],
    queryFn: () => dashboardService.getDocumentTypeDistribution(),
    refetchInterval: 300000,
  });

  const COLORS = [
    'bg-primary-500',
    'bg-accent-500',
    'bg-success-500',
    'bg-warning-500',
    'bg-error-500',
    'bg-purple-500',
    'bg-pink-500',
    'bg-indigo-500',
  ];

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-3">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="flex items-center gap-3">
            <div className="w-3 h-3 rounded-full bg-gray-200 dark:bg-gray-700" />
            <div className="flex-1 h-4 rounded bg-gray-200 dark:bg-gray-700" />
            <div className="w-8 h-4 rounded bg-gray-200 dark:bg-gray-700" />
          </div>
        ))}
      </div>
    );
  }

  if (!distribution || distribution.length === 0) {
    return (
      <div className="py-8 text-center">
        <DocumentTextIcon className="h-8 w-8 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
        <p className="text-sm text-gray-500 dark:text-gray-400">No document data available.</p>
      </div>
    );
  }

  return (
    <div>
      {/* Stacked bar */}
      <div className="flex rounded-full h-3 overflow-hidden mb-4" role="img" aria-label="Document type distribution">
        {distribution.map((item, index) => (
          <div
            key={item.type}
            className={`${COLORS[index % COLORS.length]} transition-all duration-300`}
            style={{ width: `${item.percentage}%` }}
            title={`${item.type}: ${item.count} (${item.percentage}%)`}
          />
        ))}
      </div>

      {/* Legend */}
      <ul className="space-y-2">
        {distribution.map((item, index) => (
          <li key={item.type} className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className={`w-2.5 h-2.5 rounded-full ${COLORS[index % COLORS.length]}`} />
              <span className="text-sm text-gray-700 dark:text-gray-300">{item.type}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-900 dark:text-white">{item.count}</span>
              <span className="text-xs text-gray-400 dark:text-gray-500">({item.percentage}%)</span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
};

/**
 * DashboardPage - 메인 컴포넌트
 */
const DashboardPage: React.FC = () => {
  return (
    <div className="space-y-6" data-testid="dashboard-page">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Knowledge Portal overview and statistics
        </p>
      </div>

      {/* Stats Cards */}
      <StatsSection />

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Activity and Trends (2 columns) */}
        <div className="lg:col-span-2 space-y-6">
          {/* Search Trends */}
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-gray-900 dark:text-white">
                Search Trends (Last 7 Days)
              </h2>
              <ChartBarIcon className="h-5 w-5 text-gray-400 dark:text-gray-500" />
            </div>
            <SearchTrendsSection />
          </div>

          {/* Recent Activity */}
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-gray-900 dark:text-white">
                Recent Activity
              </h2>
              <ClockIcon className="h-5 w-5 text-gray-400 dark:text-gray-500" />
            </div>
            <RecentActivitySection />
          </div>
        </div>

        {/* Right: Side panels (1 column) */}
        <div className="space-y-6">
          {/* System Health */}
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-gray-900 dark:text-white">
                System Status
              </h2>
              <ArrowPathIcon className="h-4 w-4 text-gray-400 dark:text-gray-500" />
            </div>
            <SystemHealthSection />
          </div>

          {/* Popular Queries */}
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-gray-900 dark:text-white">
                Popular Searches
              </h2>
              <MagnifyingGlassIcon className="h-5 w-5 text-gray-400 dark:text-gray-500" />
            </div>
            <PopularQueriesSection />
          </div>

          {/* Document Distribution */}
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-gray-900 dark:text-white">
                Document Types
              </h2>
              <DocumentTextIcon className="h-5 w-5 text-gray-400 dark:text-gray-500" />
            </div>
            <DocumentDistributionSection />
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
