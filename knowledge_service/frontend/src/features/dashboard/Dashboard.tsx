/**
 * Dashboard - Main dashboard layout component
 *
 * Implements STORY-041 Acceptance Criteria:
 * - AC1: Welcome message with user name after login
 * - AC2: StatCards showing document count, search count, active users, response time
 * - AC3: Recent 5 search records display
 * - AC4: Quick search input navigates to search page on Enter
 * - AC5: Sidebar menu navigation (handled by shared Sidebar component)
 *
 * Uses Tailwind CSS, Heroicons, React Query, and Headless UI.
 */
import React from 'react';
import {
  DocumentTextIcon,
  MagnifyingGlassIcon,
  UsersIcon,
  ClockIcon,
  ChartBarIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { useAuth } from '@/auth';
import StatCard, { StatCardSkeleton } from './components/StatCard';
import QuickSearch from './components/QuickSearch';
import RecentSearches from './components/RecentSearches';
import { useDashboardStats } from './hooks/useDashboardStats';
import { useRecentSearches } from './hooks/useRecentSearches';

/**
 * WelcomeSection - Personalized welcome message (AC1)
 */
const WelcomeSection: React.FC = () => {
  const { user } = useAuth();

  const getGreeting = (): string => {
    const hour = new Date().getHours();
    if (hour < 12) return '좋은 아침이에요';
    if (hour < 18) return '안녕하세요';
    return '좋은 저녁이에요';
  };

  const displayName = user?.name || user?.username || 'User';

  return (
    <div data-testid="welcome-section">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
        {getGreeting()},{' '}
        <span className="text-primary-600 dark:text-primary-400">
          {displayName}
        </span>
      </h1>
      <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
        Knowledge Portal에 오신 것을 환영합니다. 주요 현황을 확인하세요.
      </p>
    </div>
  );
};

/**
 * StatsSection - Statistics cards grid (AC2)
 */
const StatsSection: React.FC = () => {
  const { data: stats, isLoading, isError } = useDashboardStats();

  if (isLoading) {
    return (
      <div
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
        data-testid="stats-loading"
      >
        {[...Array(4)].map((_, i) => (
          <StatCardSkeleton key={i} />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div
        className="bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-xl p-4 flex items-center gap-3"
        role="alert"
        data-testid="stats-error"
      >
        <ExclamationTriangleIcon className="h-5 w-5 text-error-500 flex-shrink-0" />
        <p className="text-sm text-error-700 dark:text-error-300">
          대시보드 통계를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.
        </p>
      </div>
    );
  }

  return (
    <div
      className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
      data-testid="stats-section"
    >
      <StatCard
        title="전체 문서"
        value={stats?.totalDocuments?.toLocaleString() ?? '0'}
        subtitle={`오늘 ${stats?.documentsToday ?? 0}건 추가`}
        icon={
          <DocumentTextIcon className="h-5 w-5 text-primary-600 dark:text-primary-400" />
        }
        iconBg="bg-primary-50 dark:bg-primary-900/30"
      />
      <StatCard
        title="검색 횟수"
        value={stats?.totalSearches?.toLocaleString() ?? '0'}
        subtitle={`오늘 ${stats?.searchesToday ?? 0}건`}
        icon={
          <MagnifyingGlassIcon className="h-5 w-5 text-success-600 dark:text-success-400" />
        }
        iconBg="bg-success-50 dark:bg-success-900/30"
      />
      <StatCard
        title="활성 사용자"
        value={stats?.activeUsers?.toLocaleString() ?? '0'}
        icon={
          <UsersIcon className="h-5 w-5 text-accent-600 dark:text-accent-400" />
        }
        iconBg="bg-accent-50 dark:bg-accent-900/30"
      />
      <StatCard
        title="평균 응답시간"
        value={`${stats?.indexingRate ?? 0}ms`}
        icon={
          <ClockIcon className="h-5 w-5 text-warning-600 dark:text-warning-400" />
        }
        iconBg="bg-warning-50 dark:bg-warning-900/30"
      />
    </div>
  );
};

/**
 * QuickSearchSection - Dashboard quick search with recent history (AC3, AC4)
 */
const QuickSearchSection: React.FC = () => {
  const { displaySearches, addSearch, removeSearch, clearAll } =
    useRecentSearches({ displayCount: 5 });

  const handleSearch = (query: string) => {
    addSearch(query);
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-gray-900 dark:text-white">
          빠른 검색
        </h2>
        <ChartBarIcon className="h-5 w-5 text-gray-400 dark:text-gray-500" />
      </div>

      {/* Quick Search Input (AC4) */}
      <QuickSearch onSearch={handleSearch} />

      {/* Recent Searches (AC3) */}
      <div className="mt-4">
        <h3 className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
          최근 검색
        </h3>
        <RecentSearches
          searches={displaySearches}
          onRemove={removeSearch}
          onClearAll={clearAll}
        />
      </div>
    </div>
  );
};

/**
 * Dashboard - Main dashboard page component
 *
 * Combines all dashboard sections into a responsive layout.
 */
const Dashboard: React.FC = () => {
  return (
    <div className="space-y-6" data-testid="dashboard-page">
      {/* Welcome Message (AC1) */}
      <WelcomeSection />

      {/* Statistics Cards (AC2) */}
      <StatsSection />

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Quick Search and Recent Searches (2 columns) */}
        <div className="lg:col-span-2">
          <QuickSearchSection />
        </div>

        {/* Right: Summary panel */}
        <div className="space-y-6">
          {/* Quick Stats Summary */}
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
            <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">
              시작하기
            </h2>
            <ul className="space-y-3">
              <li className="flex items-start gap-3">
                <div className="flex-shrink-0 mt-0.5 p-1.5 rounded-full bg-primary-50 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400">
                  <MagnifyingGlassIcon className="h-4 w-4" />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    지식 검색
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    검색창에 질문을 입력하거나 검색 페이지에서 상세 검색을 이용하세요.
                  </p>
                </div>
              </li>
              <li className="flex items-start gap-3">
                <div className="flex-shrink-0 mt-0.5 p-1.5 rounded-full bg-success-50 dark:bg-success-900/30 text-success-600 dark:text-success-400">
                  <DocumentTextIcon className="h-4 w-4" />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    문서 탐색
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    지식 베이스 페이지에서 등록된 문서를 탐색하고 관리하세요.
                  </p>
                </div>
              </li>
              <li className="flex items-start gap-3">
                <div className="flex-shrink-0 mt-0.5 p-1.5 rounded-full bg-accent-50 dark:bg-accent-900/30 text-accent-600 dark:text-accent-400">
                  <UsersIcon className="h-4 w-4" />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    협업
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    유용한 문서를 북마크하고 팀원들과 공유하세요.
                  </p>
                </div>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
