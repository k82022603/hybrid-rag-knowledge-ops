/**
 * SearchFilters - 검색 필터 컴포넌트
 *
 * 문서 유형, 프로젝트, 날짜 범위 필터링
 * Tailwind CSS 기반
 */
import { useCallback } from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';

interface Filters {
  documentType?: string;
  projectName?: string;
  dateFrom?: string;
  dateTo?: string;
}

interface SearchFiltersProps {
  filters: Filters;
  onFilterChange: (filters: Filters) => void;
}

const DOCUMENT_TYPES = [
  { value: '', label: 'All Types' },
  { value: 'technical', label: 'Technical' },
  { value: 'guide', label: 'Guide' },
  { value: 'manual', label: 'Manual' },
  { value: 'report', label: 'Report' },
  { value: 'policy', label: 'Policy' },
  { value: 'meeting', label: 'Meeting Notes' },
];

const PROJECTS = [
  { value: '', label: 'All Projects' },
  { value: 'project-a', label: 'Project A' },
  { value: 'project-b', label: 'Project B' },
  { value: 'project-c', label: 'Project C' },
];

/**
 * SearchFilters 컴포넌트
 */
const SearchFilters: React.FC<SearchFiltersProps> = ({ filters, onFilterChange }) => {
  const handleChange = useCallback(
    (field: keyof Filters, value: string) => {
      onFilterChange({
        ...filters,
        [field]: value || undefined,
      });
    },
    [filters, onFilterChange]
  );

  const handleClear = useCallback(() => {
    onFilterChange({});
  }, [onFilterChange]);

  const hasFilters = Object.values(filters).some(Boolean);

  return (
    <div
      role="search"
      aria-label="Search filters"
      className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4"
      data-testid="search-filters"
    >
      <div className="flex items-center justify-between mb-3">
        <h3 id="filters-heading" className="text-sm font-medium text-gray-900 dark:text-white">Filters</h3>
        {hasFilters && (
          <button
            onClick={handleClear}
            className="inline-flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 rounded-md px-1"
            aria-label="Clear all filters"
            data-testid="clear-all-filters"
          >
            <XMarkIcon className="h-3.5 w-3.5" aria-hidden="true" />
            <span>Clear all</span>
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3" role="group" aria-labelledby="filters-heading">
        {/* Document Type */}
        <div>
          <label
            htmlFor="filter-doc-type"
            className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1"
          >
            Document Type
          </label>
          <select
            id="filter-doc-type"
            value={filters.documentType || ''}
            onChange={(e) => handleChange('documentType', e.target.value)}
            className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          >
            {DOCUMENT_TYPES.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
        </div>

        {/* Project */}
        <div>
          <label
            htmlFor="filter-project"
            className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1"
          >
            Project
          </label>
          <select
            id="filter-project"
            value={filters.projectName || ''}
            onChange={(e) => handleChange('projectName', e.target.value)}
            className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          >
            {PROJECTS.map((project) => (
              <option key={project.value} value={project.value}>
                {project.label}
              </option>
            ))}
          </select>
        </div>

        {/* Date From */}
        <div>
          <label
            htmlFor="filter-date-from"
            className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1"
          >
            From Date
          </label>
          <input
            id="filter-date-from"
            type="date"
            value={filters.dateFrom || ''}
            onChange={(e) => handleChange('dateFrom', e.target.value)}
            className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          />
        </div>

        {/* Date To */}
        <div>
          <label
            htmlFor="filter-date-to"
            className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1"
          >
            To Date
          </label>
          <input
            id="filter-date-to"
            type="date"
            value={filters.dateTo || ''}
            onChange={(e) => handleChange('dateTo', e.target.value)}
            className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          />
        </div>
      </div>

      {/* Active filter chips */}
      {hasFilters && (
        <div
          className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-gray-100 dark:border-gray-700"
          role="list"
          aria-label="Active filters"
        >
          {filters.documentType && (
            <span
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-primary-100 text-primary-800 dark:bg-primary-900 dark:text-primary-200"
              role="listitem"
            >
              <span>Type: {filters.documentType}</span>
              <button
                onClick={() => handleChange('documentType', '')}
                className="ml-0.5 hover:text-primary-600 focus:outline-none focus:ring-2 focus:ring-primary-500 rounded-full"
                aria-label={`Remove document type filter: ${filters.documentType}`}
              >
                <XMarkIcon className="h-3 w-3" aria-hidden="true" />
              </button>
            </span>
          )}
          {filters.projectName && (
            <span
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-primary-100 text-primary-800 dark:bg-primary-900 dark:text-primary-200"
              role="listitem"
            >
              <span>Project: {filters.projectName}</span>
              <button
                onClick={() => handleChange('projectName', '')}
                className="ml-0.5 hover:text-primary-600 focus:outline-none focus:ring-2 focus:ring-primary-500 rounded-full"
                aria-label={`Remove project filter: ${filters.projectName}`}
              >
                <XMarkIcon className="h-3 w-3" aria-hidden="true" />
              </button>
            </span>
          )}
          {filters.dateFrom && (
            <span
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-primary-100 text-primary-800 dark:bg-primary-900 dark:text-primary-200"
              role="listitem"
            >
              <span>From: {filters.dateFrom}</span>
              <button
                onClick={() => handleChange('dateFrom', '')}
                className="ml-0.5 hover:text-primary-600 focus:outline-none focus:ring-2 focus:ring-primary-500 rounded-full"
                aria-label={`Remove from date filter: ${filters.dateFrom}`}
              >
                <XMarkIcon className="h-3 w-3" aria-hidden="true" />
              </button>
            </span>
          )}
          {filters.dateTo && (
            <span
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-primary-100 text-primary-800 dark:bg-primary-900 dark:text-primary-200"
              role="listitem"
            >
              <span>To: {filters.dateTo}</span>
              <button
                onClick={() => handleChange('dateTo', '')}
                className="ml-0.5 hover:text-primary-600 focus:outline-none focus:ring-2 focus:ring-primary-500 rounded-full"
                aria-label={`Remove to date filter: ${filters.dateTo}`}
              >
                <XMarkIcon className="h-3 w-3" aria-hidden="true" />
              </button>
            </span>
          )}
        </div>
      )}
    </div>
  );
};

export default SearchFilters;
