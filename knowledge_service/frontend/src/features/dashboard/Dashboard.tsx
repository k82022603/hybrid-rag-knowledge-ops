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
    if (hour < 12) return 'Good Morning';
    if (hour < 18) return 'Good Afternoon';
    return 'Good Evening';
  };

  const displayName = user?.name || user?.username || 'User';

  return (
    <div data-testid="welcome-section" className="animate-fade-in-up">
      <h1 className="text-4xl font-display font-bold text-white tracking-tight">
        {getGreeting()},{' '}
        <span className="text-transparent bg-clip-text bg-gradient-to-r from-neon-cyan to-neon-purple text-glow">
          {displayName}
        </span>
      </h1>
      <p className="mt-2 text-lg text-gray-400 max-w-2xl font-light">
        Welcome to NEXUS. Monitor your intelligent knowledge operations.
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
        className="glass-panel border-error-900/50 p-4 flex items-center gap-3 animate-fade-in"
        role="alert"
        data-testid="stats-error"
      >
        <ExclamationTriangleIcon className="h-5 w-5 text-error-500 flex-shrink-0" />
        <p className="text-sm text-error-400">
          Failed to load dashboard statistics. Please try again later.
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
        title="Total Documents"
        value={stats?.totalDocuments?.toLocaleString() ?? '0'}
        subtitle={`+${stats?.documentsToday ?? 0} today`}
        icon={
          <DocumentTextIcon className="h-6 w-6 text-neon-cyan" />
        }
        iconBg="bg-neon-cyan/10 group-hover:bg-neon-cyan/20 transition-colors shadow-[0_0_10px_rgba(6,182,212,0.2)]"
        trend={{ value: stats?.documentsToday ?? 0, isPositive: true }}
      />
      <StatCard
        title="Total Searches"
        value={stats?.totalSearches?.toLocaleString() ?? '0'}
        subtitle={`${stats?.searchesToday ?? 0} queries today`}
        icon={
          <MagnifyingGlassIcon className="h-6 w-6 text-neon-purple" />
        }
        iconBg="bg-neon-purple/10 group-hover:bg-neon-purple/20 transition-colors shadow-[0_0_10px_rgba(168,85,247,0.2)]"
      />
      <StatCard
        title="Active Users"
        value={stats?.activeUsers?.toLocaleString() ?? '0'}
        icon={
          <UsersIcon className="h-6 w-6 text-neon-pink" />
        }
        iconBg="bg-neon-pink/10 group-hover:bg-neon-pink/20 transition-colors shadow-[0_0_10px_rgba(236,72,153,0.2)]"
      />
      <StatCard
        title="Avg Response Time"
        value={`${stats?.indexingRate ?? 0}ms`}
        icon={
          <ClockIcon className="h-6 w-6 text-yellow-400" />
        }
        iconBg="bg-yellow-400/10 group-hover:bg-yellow-400/20 transition-colors shadow-[0_0_10px_rgba(250,204,21,0.2)]"
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
    <div className="glass-panel h-full animate-fade-in-up delay-200 p-6">
      <div className="flex items-center justify-between mb-8">
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          <MagnifyingGlassIcon className="h-5 w-5 text-neon-cyan" />
          Quick Search
        </h2>
        <div className="p-2 rounded-lg bg-white/5 text-gray-400">
          <span className="text-xs font-mono font-medium">⌘K</span>
        </div>
      </div>

      {/* Quick Search Input (AC4) */}
      <div className="mb-8">
        <QuickSearch onSearch={handleSearch} />
      </div>

      {/* Recent Searches (AC3) */}
      <div>
        <div className="flex items-center justify-between mb-4 border-b border-white/10 pb-2">
          <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider">
            Recent Queries
          </h3>
          {displaySearches.length > 0 && (
            <button key="clear-all" onClick={clearAll} className="text-xs text-gray-400 hover:text-white transition-colors">
              Clear History
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
          <div className="glass-panel p-6 bg-gradient-to-br from-dark-300 to-dark-200 border-white/5">
            <h2 className="text-lg font-bold text-white mb-5 flex items-center gap-3">
              <span className="w-1.5 h-6 rounded-full bg-neon-purple shadow-[0_0_10px_rgba(168,85,247,0.5)]"></span>
              Get Started
            </h2>
            <ul className="space-y-4">
              <li className="flex items-start gap-4 p-3 rounded-xl hover:bg-white/5 transition-all duration-300 group cursor-pointer">
                <div className="flex-shrink-0 p-2 rounded-lg bg-neon-cyan/10 text-neon-cyan group-hover:bg-neon-cyan/20 group-hover:scale-110 transition-all duration-300">
                  <MagnifyingGlassIcon className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-sm font-bold text-white group-hover:text-neon-cyan transition-colors">
                    Knowledge Search
                  </p>
                  <p className="text-xs text-gray-400 mt-1 leading-relaxed">
                    Use the quick search above or visit the search page for advanced filtering.
                  </p>
                </div>
              </li>
              <li className="flex items-start gap-4 p-3 rounded-xl hover:bg-white/5 transition-all duration-300 group cursor-pointer">
                <div className="flex-shrink-0 p-2 rounded-lg bg-neon-purple/10 text-neon-purple group-hover:bg-neon-purple/20 group-hover:scale-110 transition-all duration-300">
                  <DocumentTextIcon className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-sm font-bold text-white group-hover:text-neon-purple transition-colors">
                    Document Explorer
                  </p>
                  <p className="text-xs text-gray-400 mt-1 leading-relaxed">
                    Browse and manage uploaded documents in the Knowledge Base.
                  </p>
                </div>
              </li>
              <li className="flex items-start gap-4 p-3 rounded-xl hover:bg-white/5 transition-all duration-300 group cursor-pointer">
                <div className="flex-shrink-0 p-2 rounded-lg bg-neon-pink/10 text-neon-pink group-hover:bg-neon-pink/20 group-hover:scale-110 transition-all duration-300">
                  <ChartBarIcon className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-sm font-bold text-white group-hover:text-neon-pink transition-colors">
                    Analytics
                  </p>
                  <p className="text-xs text-gray-400 mt-1 leading-relaxed">
                    View detailed system performance and usage statistics.
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
