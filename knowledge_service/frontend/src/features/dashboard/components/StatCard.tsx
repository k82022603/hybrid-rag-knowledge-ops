/**
 * StatCard - Dashboard statistics card component
 *
 * Displays a single metric with icon, value, subtitle, and optional trend indicator.
 * Uses Tailwind CSS for styling with dark mode support.
 *
 * @example
 * ```tsx
 * <StatCard
 *   title="Total Documents"
 *   value="1,234"
 *   subtitle="12 added today"
 *   icon={<DocumentTextIcon className="h-5 w-5 text-primary-600" />}
 *   iconBg="bg-primary-50 dark:bg-primary-900/30"
 *   trend={{ value: 12, isPositive: true }}
 * />
 * ```
 */
import React from 'react';

export interface StatCardProps {
  /** Card title label */
  title: string;
  /** Primary display value */
  value: string;
  /** Optional subtitle text */
  subtitle?: string;
  /** Icon element to display */
  icon: React.ReactNode;
  /** Background color class for the icon container */
  iconBg: string;
  /** Optional trend indicator */
  trend?: {
    /** Percentage value of the trend */
    value: number;
    /** Whether the trend is positive (up) */
    isPositive: boolean;
  };
}

/**
 * StatCardSkeleton - Loading skeleton for StatCard
 */
export const StatCardSkeleton: React.FC = () => (
  <div
    className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 animate-pulse"
    data-testid="stat-card-skeleton"
    aria-hidden="true"
  >
    <div className="flex items-center gap-3 mb-3">
      <div className="w-10 h-10 rounded-lg bg-gray-200 dark:bg-gray-700" />
      <div className="h-4 w-24 rounded bg-gray-200 dark:bg-gray-700" />
    </div>
    <div className="h-8 w-20 rounded bg-gray-200 dark:bg-gray-700" />
  </div>
);

/**
 * StatCard component for displaying dashboard metrics.
 */
const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  iconBg,
  trend,
}) => (
  <div
    className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 hover:shadow-lg transition-shadow"
    data-testid="stat-card"
    role="region"
    aria-label={`${title}: ${value}`}
  >
    <div className="flex items-center gap-3 mb-3">
      <div className={`p-2.5 rounded-lg ${iconBg}`} aria-hidden="true">
        {icon}
      </div>
      <span className="text-sm font-medium text-gray-500 dark:text-gray-400">
        {title}
      </span>
    </div>
    <div className="flex items-end justify-between">
      <div>
        <p className="text-2xl font-bold text-gray-900 dark:text-white">
          {value}
        </p>
        {subtitle && (
          <p className="mt-0.5 text-xs text-gray-400 dark:text-gray-500">
            {subtitle}
          </p>
        )}
      </div>
      {trend && (
        <span
          className={`inline-flex items-center text-xs font-medium ${
            trend.isPositive
              ? 'text-success-600 dark:text-success-400'
              : 'text-error-600 dark:text-error-400'
          }`}
          aria-label={`Trend: ${trend.isPositive ? 'up' : 'down'} ${Math.abs(trend.value)}%`}
        >
          {trend.isPositive ? '+' : ''}
          {trend.value}%
        </span>
      )}
    </div>
  </div>
);

export default StatCard;
