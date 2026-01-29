/**
 * LiveRegion - Accessible live region for dynamic content announcements
 *
 * Provides an ARIA live region that announces content changes to
 * screen readers. Essential for dynamic content updates like search
 * results, form validation, and loading states.
 *
 * WCAG 2.1 Reference:
 * - Success Criterion 4.1.3 (Status Messages)
 */
import React from 'react';

export interface LiveRegionProps {
  /** The message to announce */
  message: string;
  /** Politeness level: 'polite' waits for idle, 'assertive' interrupts */
  politeness?: 'polite' | 'assertive';
  /** Whether updates should be atomic (announce entire region) */
  atomic?: boolean;
  /** Whether the region is currently relevant */
  relevant?: 'additions' | 'removals' | 'text' | 'all';
  /** Additional CSS class names */
  className?: string;
}

/**
 * LiveRegion component for screen reader announcements.
 *
 * @example
 * // For search results:
 * <LiveRegion message={`${resultCount} results found`} politeness="polite" />
 *
 * // For errors:
 * <LiveRegion message="Form submission failed" politeness="assertive" />
 */
const LiveRegion: React.FC<LiveRegionProps> = ({
  message,
  politeness = 'polite',
  atomic = true,
  relevant = 'additions',
  className = '',
}) => {
  return (
    <div
      role="status"
      aria-live={politeness}
      aria-atomic={atomic}
      aria-relevant={relevant}
      className={`sr-only ${className}`}
      data-testid="live-region"
    >
      {message}
    </div>
  );
};

export default LiveRegion;
