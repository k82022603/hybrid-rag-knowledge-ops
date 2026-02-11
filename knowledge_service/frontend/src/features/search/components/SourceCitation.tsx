/**
 * SourceCitation - AI response source document display
 *
 * Shows source documents referenced in AI-generated answers.
 * Each citation shows [출처N] index, source type badge, document title,
 * relevance score, and expandable markdown content preview.
 * Graph sources include a "Graph" button to open the visualization panel.
 */
import React, { useState } from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
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
    return { label: '상', className: 'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-400' };
  if (score >= 0.4)
    return { label: '중', className: 'bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400' };
  return { label: '하', className: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300' };
}

/**
 * Single source card with markdown content and expand/collapse.
 */
function SourceCard({
  source,
  sourceIndex,
  isExpanded,
  onToggle,
  onGraphSourceClick,
  onDownloadClick,
}: {
  source: Source;
  sourceIndex: number;
  isExpanded: boolean;
  onToggle: () => void;
  onGraphSourceClick?: (source: Source) => void;
  onDownloadClick?: (source: Source) => void;
}) {
  const title = getSourceTitle(source);
  const relevance = getRelevanceInfo(source.score);
  const hasContent = !!source.content && source.content.length > 0;
  const isLongContent = !!source.content && source.content.length > 100;

  return (
    <article
      className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden hover:shadow-sm transition-shadow"
      data-testid={`source-card-${source.chunkId || sourceIndex}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between gap-2 px-3 py-2">
        <div className="flex items-center gap-1.5 flex-1 min-w-0">
          <DocumentTextIcon
            className="h-4 w-4 text-primary-500 flex-shrink-0"
            aria-hidden="true"
          />
          <span className="font-semibold text-xs text-primary-600 dark:text-primary-400 flex-shrink-0">
            [출처{sourceIndex}]
          </span>
          <span className="text-xs font-medium text-gray-900 dark:text-white truncate">
            {title}
          </span>
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          {source.sourceType && (
            <SourceTypeBadge type={source.sourceType} />
          )}
          {/* Embedding status badge (SCRUM-97) */}
          <span
            className={`inline-flex items-center px-1.5 py-0.5 rounded-full text-2xs font-medium ${
              source.hasEmbedding !== false
                ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
                : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'
            }`}
          >
            {source.hasEmbedding !== false ? 'AI 검색' : '키워드'}
          </span>
          {/* Graph button */}
          {source.sourceType === 'graph' && onGraphSourceClick && (
            <button
              type="button"
              onClick={() => onGraphSourceClick(source)}
              className="inline-flex items-center gap-0.5 px-1.5 py-0.5 text-2xs font-medium text-teal-600 dark:text-teal-400 hover:bg-teal-50 dark:hover:bg-teal-900/20 border border-teal-200 dark:border-teal-800 rounded-full transition-colors"
              aria-label={`${title} 그래프 보기`}
            >
              <ShareIcon className="h-2.5 w-2.5" aria-hidden="true" />
              Graph
            </button>
          )}
          {/* Download button */}
          {source.documentId && onDownloadClick && (
            <button
              type="button"
              onClick={() => onDownloadClick(source)}
              className="inline-flex items-center gap-0.5 px-1.5 py-0.5 text-2xs font-medium text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-full transition-colors"
              aria-label={`${title} 원본 다운로드`}
            >
              <ArrowDownTrayIcon className="h-2.5 w-2.5" aria-hidden="true" />
            </button>
          )}
          {/* Relevance badge */}
          <span
            className={`inline-flex items-center px-1.5 py-0.5 rounded-full text-2xs font-medium ${relevance.className}`}
          >
            {(source.score * 100).toFixed(0)}%
          </span>
        </div>
      </div>

      {/* Markdown content preview - expandable */}
      {hasContent && (
        <div className="px-3 pb-2">
          <div
            className={`text-xs text-gray-600 dark:text-gray-300 prose prose-sm dark:prose-invert max-w-none prose-p:my-0.5 prose-ul:my-0.5 prose-ol:my-0.5 prose-li:my-0 prose-headings:my-1 prose-headings:text-xs prose-pre:my-1 prose-pre:text-2xs ${
              isExpanded ? '' : 'line-clamp-3'
            }`}
          >
            <Markdown remarkPlugins={[remarkGfm]}>
              {source.content}
            </Markdown>
          </div>
          {isLongContent && (
            <button
              type="button"
              onClick={onToggle}
              className="inline-flex items-center gap-0.5 mt-1 text-2xs text-primary-500 hover:text-primary-700 dark:hover:text-primary-300"
              aria-expanded={isExpanded}
              aria-label={isExpanded ? '콘텐츠 접기' : '콘텐츠 더 보기'}
            >
              {isExpanded ? (
                <>
                  <ChevronUpIcon className="h-3 w-3" />
                  접기
                </>
              ) : (
                <>
                  <ChevronDownIcon className="h-3 w-3" />
                  더 보기
                </>
              )}
            </button>
          )}
        </div>
      )}

      {/* Metadata badges */}
      {(source.metadata?.documentType || source.graphContext?.community) && (
        <div className="flex flex-wrap items-center gap-1.5 px-3 pb-2">
          {source.metadata?.documentType && (
            <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-2xs font-medium bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300">
              {source.metadata.documentType}
            </span>
          )}
          {source.graphContext?.community && (
            <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-2xs font-medium bg-accent-50 text-accent-700 dark:bg-accent-900/30 dark:text-accent-400">
              {source.graphContext.community}
            </span>
          )}
        </div>
      )}
    </article>
  );
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
  const [expandedSet, setExpandedSet] = useState<Set<number>>(new Set());
  const [showAll, setShowAll] = useState(false);

  if (!sources || sources.length === 0) return null;

  const displayedSources = showAll ? sources : sources.slice(0, maxDisplay);
  const remainingCount = sources.length - maxDisplay;

  const toggleExpand = (idx: number) => {
    setExpandedSet((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) {
        next.delete(idx);
      } else {
        next.add(idx);
      }
      return next;
    });
  };

  return (
    <div className="mt-3 space-y-2" data-testid="source-citation">
      <p className="text-xs font-semibold text-gray-500 dark:text-gray-400">
        Sources ({sources.length}):
      </p>
      <div className="space-y-2">
        {displayedSources.map((source, idx) => {
          const sourceIndex = source.index || idx + 1;
          return (
            <SourceCard
              key={source.chunkId || idx}
              source={source}
              sourceIndex={sourceIndex}
              isExpanded={expandedSet.has(idx)}
              onToggle={() => toggleExpand(idx)}
              onGraphSourceClick={onGraphSourceClick}
              onDownloadClick={onDownloadClick}
            />
          );
        })}

        {/* Show more / Show less toggle */}
        {remainingCount > 0 && (
          <button
            onClick={() => setShowAll(!showAll)}
            className="text-xs text-primary-500 hover:text-primary-700 dark:hover:text-primary-300 px-1 py-0.5"
          >
            {showAll ? '접기' : `+${remainingCount}개 더 보기`}
          </button>
        )}
      </div>
    </div>
  );
};

export default SourceCitation;
