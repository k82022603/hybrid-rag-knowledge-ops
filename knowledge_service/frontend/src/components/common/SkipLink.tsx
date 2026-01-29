/**
 * SkipLink - Accessibility skip navigation component
 *
 * Provides a "Skip to main content" link for keyboard users
 * that becomes visible on focus. This is a WCAG 2.1 AA requirement
 * for keyboard accessibility (Success Criterion 2.4.1).
 *
 * Features:
 * - Hidden by default, visible on focus
 * - Allows keyboard users to skip repetitive navigation
 * - High contrast styling for visibility
 */
import React from 'react';

export interface SkipLinkProps {
  /** ID of the main content element to skip to */
  targetId?: string;
  /** Custom text for the skip link */
  text?: string;
}

/**
 * SkipLink component for keyboard navigation accessibility.
 *
 * @example
 * // In your layout component:
 * <SkipLink targetId="main-content" />
 * <Header />
 * <Sidebar />
 * <main id="main-content">...</main>
 */
const SkipLink: React.FC<SkipLinkProps> = ({
  targetId = 'main-content',
  text = 'Skip to main content',
}) => {
  const focusTarget = () => {
    const target = document.getElementById(targetId);
    if (target) {
      target.focus();
      // scrollIntoView may not be available in all environments (e.g., jsdom)
      if (typeof target.scrollIntoView === 'function') {
        target.scrollIntoView({ behavior: 'smooth' });
      }
    }
  };

  const handleClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
    e.preventDefault();
    focusTarget();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLAnchorElement>) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      focusTarget();
    }
  };

  return (
    <a
      href={`#${targetId}`}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className="
        sr-only focus:not-sr-only
        focus:fixed focus:top-4 focus:left-4 focus:z-[100]
        focus:inline-block focus:px-4 focus:py-2
        focus:bg-primary-600 focus:text-white
        focus:font-semibold focus:text-sm
        focus:rounded-lg focus:shadow-lg
        focus:outline-none focus:ring-2 focus:ring-primary-300 focus:ring-offset-2
        transition-all duration-200
      "
      data-testid="skip-link"
    >
      {text}
    </a>
  );
};

export default SkipLink;
