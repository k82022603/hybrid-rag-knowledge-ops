/**
 * SearchResultCard component tests
 *
 * Tests for the keyword search result card component:
 * - Rendering of result data
 * - Relevance score display and colors
 * - Metadata badges
 * - Accessibility attributes
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import SearchResultCard from '../components/SearchResultCard';
import type { SearchResultItem } from '../types';

const createMockResult = (overrides: Partial<SearchResultItem> = {}): SearchResultItem => ({
  chunkId: 'chunk-123',
  documentId: 'doc-456',
  content: 'This is the search result content that displays in the card.',
  score: 0.85,
  metadata: {
    documentType: 'technical',
    projectName: 'Test Project',
    category: {
      level1: 'Engineering',
      level2: 'Backend',
      level3: 'API',
    },
    summary: 'A brief summary of the document.',
  },
  graphContext: {
    relatedEntities: ['entity1', 'entity2'],
    community: 'Development',
  },
  ...overrides,
});

describe('SearchResultCard', () => {
  // ===== Basic Rendering =====

  describe('basic rendering', () => {
    it('should render the card with correct test id', () => {
      render(<SearchResultCard result={createMockResult()} />);

      expect(screen.getByTestId('search-result-chunk-123')).toBeInTheDocument();
    });

    it('should render content preview', () => {
      render(<SearchResultCard result={createMockResult()} />);

      expect(
        screen.getByText(
          'This is the search result content that displays in the card.'
        )
      ).toBeInTheDocument();
    });

    it('should render project name as title', () => {
      render(<SearchResultCard result={createMockResult()} />);

      expect(screen.getByText('Test Project')).toBeInTheDocument();
    });

    it('should render "Document" as title when no project name', () => {
      render(
        <SearchResultCard
          result={createMockResult({
            metadata: {
              documentType: 'guide',
            },
          })}
        />
      );

      expect(screen.getByText('Document')).toBeInTheDocument();
    });

    it('should render document icon', () => {
      render(<SearchResultCard result={createMockResult()} />);

      const card = screen.getByTestId('search-result-chunk-123');
      expect(card.querySelector('svg')).toBeInTheDocument();
    });
  });

  // ===== Relevance Score =====

  describe('relevance score', () => {
    it('should display score as percentage', () => {
      render(<SearchResultCard result={createMockResult({ score: 0.85 })} />);

      expect(screen.getByText('85%')).toBeInTheDocument();
    });

    it('should display 100% for perfect score', () => {
      render(<SearchResultCard result={createMockResult({ score: 1.0 })} />);

      expect(screen.getByText('100%')).toBeInTheDocument();
    });

    it('should display 0% for zero score', () => {
      render(<SearchResultCard result={createMockResult({ score: 0 })} />);

      expect(screen.getByText('0%')).toBeInTheDocument();
    });

    it('should round score to nearest integer', () => {
      render(<SearchResultCard result={createMockResult({ score: 0.756 })} />);

      expect(screen.getByText('76%')).toBeInTheDocument();
    });

    it('should have accessible label for score', () => {
      render(<SearchResultCard result={createMockResult({ score: 0.92 })} />);

      expect(screen.getByLabelText('Relevance: 92%')).toBeInTheDocument();
    });
  });

  // ===== Score Color Classes =====

  describe('score color classes', () => {
    it('should use success color for score >= 0.9', () => {
      render(<SearchResultCard result={createMockResult({ score: 0.95 })} />);

      const scoreBadge = screen.getByText('95%');
      expect(scoreBadge).toHaveClass('bg-success-100');
      expect(scoreBadge).toHaveClass('text-success-700');
    });

    it('should use primary color for score >= 0.7 and < 0.9', () => {
      render(<SearchResultCard result={createMockResult({ score: 0.75 })} />);

      const scoreBadge = screen.getByText('75%');
      expect(scoreBadge).toHaveClass('bg-primary-100');
      expect(scoreBadge).toHaveClass('text-primary-700');
    });

    it('should use warning color for score >= 0.5 and < 0.7', () => {
      render(<SearchResultCard result={createMockResult({ score: 0.55 })} />);

      const scoreBadge = screen.getByText('55%');
      expect(scoreBadge).toHaveClass('bg-warning-100');
      expect(scoreBadge).toHaveClass('text-warning-700');
    });

    it('should use gray color for score < 0.5', () => {
      render(<SearchResultCard result={createMockResult({ score: 0.35 })} />);

      const scoreBadge = screen.getByText('35%');
      expect(scoreBadge).toHaveClass('bg-gray-100');
      expect(scoreBadge).toHaveClass('text-gray-700');
    });

    it('should use success color for exactly 0.9', () => {
      render(<SearchResultCard result={createMockResult({ score: 0.9 })} />);

      const scoreBadge = screen.getByText('90%');
      expect(scoreBadge).toHaveClass('bg-success-100');
    });

    it('should use primary color for exactly 0.7', () => {
      render(<SearchResultCard result={createMockResult({ score: 0.7 })} />);

      const scoreBadge = screen.getByText('70%');
      expect(scoreBadge).toHaveClass('bg-primary-100');
    });

    it('should use warning color for exactly 0.5', () => {
      render(<SearchResultCard result={createMockResult({ score: 0.5 })} />);

      const scoreBadge = screen.getByText('50%');
      expect(scoreBadge).toHaveClass('bg-warning-100');
    });
  });

  // ===== Metadata Badges =====

  describe('metadata badges', () => {
    it('should display document type badge', () => {
      render(<SearchResultCard result={createMockResult()} />);

      expect(screen.getByText('technical')).toBeInTheDocument();
    });

    it('should not display document type badge when not provided', () => {
      render(
        <SearchResultCard
          result={createMockResult({
            metadata: {
              projectName: 'Project',
            },
          })}
        />
      );

      expect(screen.queryByText('technical')).not.toBeInTheDocument();
    });

    it('should display category levels', () => {
      render(<SearchResultCard result={createMockResult()} />);

      // Category shows "level1 / level2"
      expect(screen.getByText('Engineering / Backend')).toBeInTheDocument();
    });

    it('should display only level1 when level2 is not provided', () => {
      render(
        <SearchResultCard
          result={createMockResult({
            metadata: {
              category: {
                level1: 'Engineering',
                level2: '',
                level3: '',
              },
            },
          })}
        />
      );

      expect(screen.getByText('Engineering')).toBeInTheDocument();
    });

    it('should display community badge from graph context', () => {
      render(<SearchResultCard result={createMockResult()} />);

      expect(screen.getByText('Development')).toBeInTheDocument();
    });

    it('should not display community badge when not provided', () => {
      render(
        <SearchResultCard
          result={createMockResult({
            graphContext: undefined,
          })}
        />
      );

      expect(screen.queryByText('Development')).not.toBeInTheDocument();
    });
  });

  // ===== Summary =====

  describe('summary', () => {
    it('should display summary when provided', () => {
      render(<SearchResultCard result={createMockResult()} />);

      expect(
        screen.getByText('A brief summary of the document.')
      ).toBeInTheDocument();
    });

    it('should not display summary when not provided', () => {
      render(
        <SearchResultCard
          result={createMockResult({
            metadata: {
              documentType: 'guide',
              projectName: 'Project',
            },
          })}
        />
      );

      expect(
        screen.queryByText('A brief summary of the document.')
      ).not.toBeInTheDocument();
    });

    it('should display summary in italics', () => {
      render(<SearchResultCard result={createMockResult()} />);

      const summary = screen.getByText('A brief summary of the document.');
      expect(summary).toHaveClass('italic');
    });
  });

  // ===== Accessibility =====

  describe('accessibility', () => {
    it('should have role="article"', () => {
      render(<SearchResultCard result={createMockResult()} />);

      expect(screen.getByRole('article')).toBeInTheDocument();
    });

    it('should have aria-label with project name', () => {
      render(<SearchResultCard result={createMockResult()} />);

      expect(
        screen.getByRole('article', {
          name: 'Search result: Test Project',
        })
      ).toBeInTheDocument();
    });

    it('should have aria-label with "Document" when no project name', () => {
      render(
        <SearchResultCard
          result={createMockResult({
            metadata: undefined,
          })}
        />
      );

      expect(
        screen.getByRole('article', {
          name: 'Search result: Document',
        })
      ).toBeInTheDocument();
    });

    it('should have aria-hidden on decorative icon', () => {
      render(<SearchResultCard result={createMockResult()} />);

      const card = screen.getByTestId('search-result-chunk-123');
      const icon = card.querySelector('svg');
      expect(icon).toHaveAttribute('aria-hidden', 'true');
    });
  });

  // ===== Edge Cases =====

  describe('edge cases', () => {
    it('should handle empty content', () => {
      render(
        <SearchResultCard
          result={createMockResult({
            content: '',
          })}
        />
      );

      expect(screen.getByTestId('search-result-chunk-123')).toBeInTheDocument();
    });

    it('should handle very long content', () => {
      const longContent = 'A'.repeat(1000);
      render(
        <SearchResultCard
          result={createMockResult({
            content: longContent,
          })}
        />
      );

      // Content should be truncated with line-clamp
      const contentElement = screen.getByText(longContent);
      expect(contentElement).toHaveClass('line-clamp-3');
    });

    it('should handle minimal result data', () => {
      const minimalResult: SearchResultItem = {
        chunkId: 'min-chunk',
        documentId: 'min-doc',
        content: 'Minimal content',
        score: 0.5,
      };

      render(<SearchResultCard result={minimalResult} />);

      expect(screen.getByTestId('search-result-min-chunk')).toBeInTheDocument();
      expect(screen.getByText('Minimal content')).toBeInTheDocument();
      expect(screen.getByText('50%')).toBeInTheDocument();
    });
  });
});
