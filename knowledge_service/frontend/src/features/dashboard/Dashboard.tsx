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
    <div data-testid="welcome-section" className="animate-fade-in-up">
      <h1 className="text-3xl font-bold text-gray-900 dark:text-white tracking-tight">
        {getGreeting()},{' '}
        <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary-600 to-accent-600 dark:from-primary-400 dark:to-accent-400">
          {displayName}
        </span>
        님
      </h1>
      <p className="mt-2 text-base text-gray-600 dark:text-gray-400 max-w-2xl">
        Knowledge Portal에 오신 것을 환영합니다. 오늘의 주요 현황과 업데이트를 확인하세요.
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
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6"
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
        className="bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-xl p-4 flex items-center gap-3 animate-fade-in"
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
      className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 animate-fade-in-up delay-100"
      data-testid="stats-section"
    >
      <StatCard
        title="전체 문서"
        value={stats?.totalDocuments?.toLocaleString() ?? '0'}
        subtitle={`오늘 ${stats?.documentsToday ?? 0}건 추가`}
        icon={
          <DocumentTextIcon className="h-6 w-6 text-primary-600 dark:text-primary-400" />
        }
        iconBg="bg-primary-50 dark:bg-primary-900/30 group-hover:bg-primary-100 dark:group-hover:bg-primary-900/50 transition-colors"
      />
      <StatCard
        title="검색 횟수"
        value={stats?.totalSearches?.toLocaleString() ?? '0'}
        subtitle={`오늘 ${stats?.searchesToday ?? 0}건`}
        icon={
          <MagnifyingGlassIcon className="h-6 w-6 text-success-600 dark:text-success-400" />
        }
        iconBg="bg-success-50 dark:bg-success-900/30 group-hover:bg-success-100 dark:group-hover:bg-success-900/50 transition-colors"
      />
      <StatCard
        title="활성 사용자"
        value={stats?.activeUsers?.toLocaleString() ?? '0'}
        icon={
          <UsersIcon className="h-6 w-6 text-accent-600 dark:text-accent-400" />
        }
        iconBg="bg-accent-50 dark:bg-accent-900/30 group-hover:bg-accent-100 dark:group-hover:bg-accent-900/50 transition-colors"
      />
      <StatCard
        title="평균 응답시간"
        value={`${stats?.indexingRate ?? 0}ms`}
        icon={
          <ClockIcon className="h-6 w-6 text-warning-600 dark:text-warning-400" />
        }
        iconBg="bg-warning-50 dark:bg-warning-900/30 group-hover:bg-warning-100 dark:group-hover:bg-warning-900/50 transition-colors"
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
    <div className="card h-full animate-fade-in-up delay-200">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-bold text-gray-900 dark:text-white">
          빠른 검색
        </h2>
        <div className="p-2 rounded-lg bg-gray-50 dark:bg-gray-800 text-gray-400 dark:text-gray-500">
          <ChartBarIcon className="h-5 w-5" />
        </div>
      </div>

      {/* Quick Search Input (AC4) */}
      <div className="mb-8">
        <QuickSearch onSearch={handleSearch} />
      </div>

      {/* Recent Searches (AC3) */}
      <div>
        <div className="flex items-center justify-between mb-3 border-b border-gray-100 dark:border-gray-700/50 pb-2">
          <h3 className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
            최근 검색어
          </h3>
          {displaySearches.length > 0 && (
            <button key="clear-all" onClick={clearAll} className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors">
              모두 지우기
            </button>
          )}
        </div>
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
    <div className="space-y-8 pb-8" data-testid="dashboard-page">
      {/* Welcome Message (AC1) */}
      <WelcomeSection />

      {/* Statistics Cards (AC2) */}
      <StatsSection />

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 sm:gap-8">
        {/* Left: Quick Search and Recent Searches (2 columns) */}
        <div className="lg:col-span-2">
          <QuickSearchSection />
        </div>

        {/* Right: Summary panel */}
        <div className="space-y-6 animate-fade-in-up delay-300">
          {/* Quick Stats Summary */}
          <div className="card bg-gradient-to-br from-white to-gray-50 dark:from-gray-800 dark:to-gray-800/80">
            <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-5 flex items-center gap-2">
              <span className="w-1 h-6 rounded-full bg-primary-500"></span>
              시작하기
            </h2>
            <ul className="space-y-4">
              <li className="flex items-start gap-4 p-3 rounded-xl hover:bg-white dark:hover:bg-gray-700/50 hover:shadow-sm transition-all duration-200">
                <div className="flex-shrink-0 p-2 rounded-lg bg-primary-100/50 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400">
                  <MagnifyingGlassIcon className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-sm font-bold text-gray-900 dark:text-white">
                    지식 검색
                  </p>
                  <p className="text-xs text-gray-600 dark:text-gray-400 mt-1 leading-relaxed">
                    검색창에 질문을 입력하거나 검색 페이지에서 상세 검색을 이용하세요.
                  </p>
                </div>
              </li>
              <li className="flex items-start gap-4 p-3 rounded-xl hover:bg-white dark:hover:bg-gray-700/50 hover:shadow-sm transition-all duration-200">
                <div className="flex-shrink-0 p-2 rounded-lg bg-success-100/50 dark:bg-success-900/20 text-success-600 dark:text-success-400">
                  <DocumentTextIcon className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-sm font-bold text-gray-900 dark:text-white">
                    문서 탐색
                  </p>
                  <p className="text-xs text-gray-600 dark:text-gray-400 mt-1 leading-relaxed">
                    지식 베이스 페이지에서 등록된 문서를 탐색하고 관리하세요.
                  </p>
                </div>
              </li>
              <li className="flex items-start gap-4 p-3 rounded-xl hover:bg-white dark:hover:bg-gray-700/50 hover:shadow-sm transition-all duration-200">
                <div className="flex-shrink-0 p-2 rounded-lg bg-accent-100/50 dark:bg-accent-900/20 text-accent-600 dark:text-accent-400">
                  <UsersIcon className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-sm font-bold text-gray-900 dark:text-white">
                    협업
                  </p>
                  <p className="text-xs text-gray-600 dark:text-gray-400 mt-1 leading-relaxed">
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
