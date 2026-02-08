/**
 * SourceCitation - AI response source document display
 *
 * Shows source documents referenced in AI-generated answers.
 * Each citation shows [출처N] index, source type badge, document title,
 * relevance score, and expandable content preview.
 * Graph sources include a "Graph" button to open the visualization panel.
 */
import React, { useState } from 'react';
import {
  DocumentTextIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  CircleStackIcon,
  MagnifyingGlassIcon,
  ShareIcon,
  ArrowDownTrayIcon,
} from '@heroicons/react/24/outline';
import type { Source } from '../types';

export interface SourceCitationProps {
  /** List of source documents */
  sources: Source[];
  /** Maximum number of sources to display (default: 5) */
  maxDisplay?: number;
  /** Callback when a graph source's "Graph" button is clicked */
  onGraphSourceClick?: (source: Source) => void;
  /** Callback when a source's download button is clicked */
  onDownloadClick?: (source: Source) => void;
}

/** Source type badge configuration */
const SOURCE_TYPE_CONFIG: Record<
  string,
  { icon: typeof CircleStackIcon; label: string; className: string }
> = {
  vector: {
    icon: CircleStackIcon,
    label: 'Vector',
    className:
      'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300',
  },
  keyword: {
    icon: MagnifyingGlassIcon,
    label: 'Keyword',
    className:
      'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300',
  },
  graph: {
    icon: ShareIcon,
    label: 'Graph',
    className:
      'bg-teal-100 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300',
  },
};

/**
 * SourceTypeBadge - displays icon + label for source type
 */
function SourceTypeBadge({ type }: { type: string }) {
  const config = SOURCE_TYPE_CONFIG[type];
  if (!config) return null;
  const Icon = config.icon;
  return (
    <span
      className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-2xs font-medium flex-shrink-0 ${config.className}`}
    >
      <Icon className="h-2.5 w-2.5" aria-hidden="true" />
      {config.label}
    </span>
  );
}

/**
 * Get display title for a source.
 */
function getSourceTitle(source: Source): string {
  if (source.title && source.title !== '문서') return source.title;
  if (source.metadata?.projectName) return source.metadata.projectName;
  if (source.documentId) return `Doc-${source.documentId.slice(0, 8)}`;
  return '문서';
}

/**
 * Relevance level label and color based on score.
 */
function getRelevanceInfo(score: number): {
  label: string;
  className: string;
} {
  if (score >= 0.7)
    return { label: '상', className: 'text-green-600 dark:text-green-400' };
  if (score >= 0.4)
    return { label: '중', className: 'text-primary-600 dark:text-primary-400' };
  return { label: '하', className: 'text-gray-500 dark:text-gray-400' };
}

/**
 * SourceCitation component for displaying AI answer sources.
 */
const SourceCitation: React.FC<SourceCitationProps> = ({
  sources,
  maxDisplay = 5,
  onGraphSourceClick,
  onDownloadClick,
}) => {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);
  const [showAll, setShowAll] = useState(false);

  if (!sources || sources.length === 0) return null;

  const displayedSources = showAll ? sources : sources.slice(0, maxDisplay);
  const remainingCount = sources.length - maxDisplay;

  const toggleExpand = (idx: number) => {
    setExpandedIndex(expandedIndex === idx ? null : idx);
  };

  return (
    <div className="mt-2 space-y-1.5" data-testid="source-citation">
      <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
        출처 ({sources.length}):
      </p>
      <div className="space-y-1">
        {displayedSources.map((source, idx) => {
          const sourceIndex = source.index || idx + 1;
          const title = getSourceTitle(source);
          const isExpanded = expandedIndex === idx;

          return (
            <div key={source.chunkId || idx} className="group">
              {/* Source header - clickable */}
              <button
                onClick={() => toggleExpand(idx)}
                className="w-full flex items-center gap-1.5 px-2.5 py-1.5 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-xs text-left hover:bg-gray-100 dark:hover:bg-gray-750 transition-colors"
                aria-expanded={isExpanded}
                aria-label={`출처${sourceIndex}: ${title}, ${source.sourceType ? source.sourceType + ' 검색,' : ''} 연관도 ${getRelevanceInfo(source.score).label} (${(source.score * 100).toFixed(0)}%)`}
              >
                <DocumentTextIcon
                  className="h-3.5 w-3.5 text-primary-500 flex-shrink-0"
                  aria-hidden="true"
                />
                <span className="font-medium text-primary-600 dark:text-primary-400 flex-shrink-0">
                  [출처{sourceIndex}]
                </span>
                {source.sourceType && (
                  <SourceTypeBadge type={source.sourceType} />
                )}
                <span className="truncate text-gray-700 dark:text-gray-300 flex-1 min-w-0">
                  {title}
                </span>
                <span
                  className={`flex-shrink-0 font-mono text-2xs ${getRelevanceInfo(source.score).className}`}
                >
                  연관도 {getRelevanceInfo(source.score).label} ({(source.score * 100).toFixed(0)}%)
                </span>
                {/* Graph view button */}
                {source.sourceType === 'graph' && onGraphSourceClick && (
                  <span
                    role="button"
                    tabIndex={0}
                    onClick={(e) => {
                      e.stopPropagation();
                      onGraphSourceClick(source);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.stopPropagation();
                        onGraphSourceClick(source);
                      }
                    }}
                    className="flex-shrink-0 px-1.5 py-0.5 text-2xs font-medium text-teal-600 dark:text-teal-400 hover:bg-teal-50 dark:hover:bg-teal-900/20 rounded transition-colors"
                    aria-label={`View graph for ${title}`}
                  >
                    Graph
                  </span>
                )}
                {/* Download button */}
                {source.documentId && onDownloadClick && (
                  <span
                    role="button"
                    tabIndex={0}
                    onClick={(e) => {
                      e.stopPropagation();
                      onDownloadClick(source);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.stopPropagation();
                        onDownloadClick(source);
                      }
                    }}
                    className="flex-shrink-0 px-1.5 py-0.5 text-2xs font-medium text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded transition-colors"
                    aria-label={`${title} 원본 다운로드`}
                  >
                    <ArrowDownTrayIcon className="h-2.5 w-2.5 inline" aria-hidden="true" />
                  </span>
                )}
                {source.content &&
                  (isExpanded ? (
                    <ChevronUpIcon className="h-3 w-3 text-gray-400 flex-shrink-0" />
                  ) : (
                    <ChevronDownIcon className="h-3 w-3 text-gray-400 flex-shrink-0" />
                  ))}
              </button>

              {/* Expanded content preview */}
              {isExpanded && source.content && (
                <div className="mt-1 mx-1 px-3 py-2 bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-700/50 rounded-md text-xs text-gray-600 dark:text-gray-400 leading-relaxed max-h-32 overflow-y-auto">
                  {source.content}
                </div>
              )}
            </div>
          );
        })}

        {/* Show more / Show less toggle */}
        {remainingCount > 0 && (
          <button
            onClick={() => setShowAll(!showAll)}
            className="text-xs text-primary-500 hover:text-primary-700 dark:hover:text-primary-300 px-2.5 py-1"
          >
            {showAll ? '접기' : `+${remainingCount}개 더 보기`}
          </button>
        )}
      </div>
    </div>
  );
};

export default SourceCitation;
