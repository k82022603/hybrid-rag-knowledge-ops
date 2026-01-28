/**
 * SourceCitation - AI response source document display
 *
 * Shows source documents referenced in AI-generated answers.
 * Each citation shows the document name, relevance score,
 * and a preview tooltip of the content.
 */
import React from 'react';
import { DocumentTextIcon } from '@heroicons/react/24/outline';
import type { Source } from '../types';

export interface SourceCitationProps {
  /** List of source documents */
  sources: Source[];
  /** Maximum number of sources to display (default: 3) */
  maxDisplay?: number;
}

/**
 * SourceCitation component for displaying AI answer sources.
 */
const SourceCitation: React.FC<SourceCitationProps> = ({
  sources,
  maxDisplay = 3,
}) => {
  if (!sources || sources.length === 0) return null;

  const displayedSources = sources.slice(0, maxDisplay);
  const remainingCount = sources.length - maxDisplay;

  return (
    <div className="mt-2 space-y-1" data-testid="source-citation">
      <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
        Sources:
      </p>
      <div className="flex flex-wrap gap-2">
        {displayedSources.map((source) => (
          <div
            key={source.chunkId}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-xs text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-750 transition-colors cursor-pointer"
            title={source.content}
            role="link"
            tabIndex={0}
            aria-label={`Source: ${source.metadata?.projectName || 'Document'}, relevance ${(source.score * 100).toFixed(0)}%`}
          >
            <DocumentTextIcon className="h-3.5 w-3.5 text-gray-400 flex-shrink-0" aria-hidden="true" />
            <span className="truncate max-w-[150px]">
              {source.metadata?.projectName || 'Document'}
            </span>
            <span className="text-gray-400 flex-shrink-0">
              {(source.score * 100).toFixed(0)}%
            </span>
          </div>
        ))}
        {remainingCount > 0 && (
          <span className="inline-flex items-center px-2 py-1 text-xs text-gray-400 dark:text-gray-500">
            +{remainingCount} more
          </span>
        )}
      </div>
    </div>
  );
};

export default SourceCitation;
