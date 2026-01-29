/**
 * VisuallyHidden - Screen reader only component
 *
 * Hides content visually while keeping it accessible to screen readers.
 * This is essential for providing context to assistive technologies
 * without affecting visual layout.
 *
 * WCAG 2.1 Reference:
 * - Success Criterion 1.3.1 (Info and Relationships)
 * - Success Criterion 4.1.2 (Name, Role, Value)
 */
import React from 'react';

export interface VisuallyHiddenProps {
  /** Content to be hidden visually but accessible to screen readers */
  children: React.ReactNode;
  /** Optional HTML element to render (default: span) */
  as?: keyof JSX.IntrinsicElements;
}

/**
 * VisuallyHidden component for accessible hidden content.
 *
 * @example
 * <button>
 *   <SearchIcon />
 *   <VisuallyHidden>Search</VisuallyHidden>
 * </button>
 */
const VisuallyHidden: React.FC<VisuallyHiddenProps> = ({
  children,
  as: Component = 'span',
}) => {
  return (
    <Component className="sr-only" data-testid="visually-hidden">
      {children}
    </Component>
  );
};

export default VisuallyHidden;
