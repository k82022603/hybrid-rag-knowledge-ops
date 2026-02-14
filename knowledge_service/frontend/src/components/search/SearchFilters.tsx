/**
 * SearchFilters - 검색 필터 컴포넌트
 *
 * 문서 유형, 날짜 범위 필터링
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
  { value: '', label: '전체' },
  { value: 'txt', label: 'TXT' },
  { value: 'pdf', label: 'PDF' },
  { value: 'pptx', label: 'PPTX' },
  { value: 'docx', label: 'DOCX' },
  { value: 'xlsx', label: 'XLSX' },
  { value: 'hwp', label: 'HWP' },
  { value: 'md', label: 'Markdown' },
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
      aria-label="검색 필터"
      className="glass-panel p-5"
      data-testid="search-filters"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 id="filters-heading" className="text-sm font-bold text-gray-900 dark:text-white uppercase tracking-wider">필터 옵션</h3>
        {hasFilters && (
          <button
            onClick={handleClear}
            className="inline-flex items-center gap-1 text-xs text-neon-cyan hover:text-neon-cyan/80 transition-colors focus:outline-none focus:ring-2 focus:ring-neon-cyan rounded-md px-2 py-1 bg-neon-cyan/10 hover:bg-neon-cyan/20"
            aria-label="모든 필터 초기화"
            data-testid="clear-all-filters"
          >
            <XMarkIcon className="h-3.5 w-3.5" aria-hidden="true" />
            <span>초기화</span>
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4" role="group" aria-labelledby="filters-heading">
        {/* Document Type */}
        <div>
          <label
            htmlFor="filter-doc-type"
            className="block text-xs font-semibold text-gray-500 dark:text-gray-400 mb-2 ml-1"
          >
            문서 유형
          </label>
          <select
            id="filter-doc-type"
            value={filters.documentType || ''}
            onChange={(e) => handleChange('documentType', e.target.value)}
            className="w-full px-3 py-2.5 text-sm rounded-lg border border-white/10 bg-black/20 text-gray-200 outline-none focus:ring-1 focus:ring-neon-cyan focus:border-neon-cyan transition-all hover:bg-black/30"
          >
            {DOCUMENT_TYPES.map((type) => (
              <option key={type.value} value={type.value} className="bg-dark-200 text-gray-200">
                {type.label}
              </option>
            ))}
          </select>
        </div>

        {/* Date From */}
        <div>
          <label
            htmlFor="filter-date-from"
            className="block text-xs font-semibold text-gray-500 dark:text-gray-400 mb-2 ml-1"
          >
            시작일
          </label>
          <input
            id="filter-date-from"
            type="date"
            value={filters.dateFrom || ''}
            onChange={(e) => handleChange('dateFrom', e.target.value)}
            className="w-full px-3 py-2.5 text-sm rounded-lg border border-white/10 bg-black/20 text-gray-200 outline-none focus:ring-1 focus:ring-neon-cyan focus:border-neon-cyan transition-all hover:bg-black/30 placeholder-gray-600"
          />
        </div>

        {/* Date To */}
        <div>
          <label
            htmlFor="filter-date-to"
            className="block text-xs font-semibold text-gray-500 dark:text-gray-400 mb-2 ml-1"
          >
            종료일
          </label>
          <input
            id="filter-date-to"
            type="date"
            value={filters.dateTo || ''}
            onChange={(e) => handleChange('dateTo', e.target.value)}
            className="w-full px-3 py-2.5 text-sm rounded-lg border border-white/10 bg-black/20 text-gray-200 outline-none focus:ring-1 focus:ring-neon-cyan focus:border-neon-cyan transition-all hover:bg-black/30 placeholder-gray-600"
          />
        </div>
      </div>

      {/* Active filter chips */}
      {hasFilters && (
        <div
          className="flex flex-wrap gap-2 mt-4 pt-4 border-t border-white/10"
          role="list"
          aria-label="적용된 필터"
        >
          {filters.documentType && (
            <span
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/20 shadow-[0_0_10px_rgba(6,182,212,0.2)]"
              role="listitem"
            >
              <span>유형: {filters.documentType.toUpperCase()}</span>
              <button
                onClick={() => handleChange('documentType', '')}
                className="hover:text-white focus:outline-none rounded-full p-0.5 hover:bg-neon-cyan/20 transition-colors"
                aria-label={`문서 유형 필터 제거: ${filters.documentType}`}
              >
                <XMarkIcon className="h-3 w-3" aria-hidden="true" />
              </button>
            </span>
          )}
          {filters.dateFrom && (
            <span
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-neon-purple/10 text-neon-purple border border-neon-purple/20 shadow-[0_0_10px_rgba(168,85,247,0.2)]"
              role="listitem"
            >
              <span>시작: {filters.dateFrom}</span>
              <button
                onClick={() => handleChange('dateFrom', '')}
                className="hover:text-white focus:outline-none rounded-full p-0.5 hover:bg-neon-purple/20 transition-colors"
                aria-label={`시작일 필터 제거: ${filters.dateFrom}`}
              >
                <XMarkIcon className="h-3 w-3" aria-hidden="true" />
              </button>
            </span>
          )}
          {filters.dateTo && (
            <span
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-neon-purple/10 text-neon-purple border border-neon-purple/20 shadow-[0_0_10px_rgba(168,85,247,0.2)]"
              role="listitem"
            >
              <span>종료: {filters.dateTo}</span>
              <button
                onClick={() => handleChange('dateTo', '')}
                className="hover:text-white focus:outline-none rounded-full p-0.5 hover:bg-neon-purple/20 transition-colors"
                aria-label={`종료일 필터 제거: ${filters.dateTo}`}
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
