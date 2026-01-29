/**
 * SearchPage component tests
 *
 * Tests for the main SearchPage component:
 * - Tab navigation between Chat and Keyword search
 * - Proper aria attributes for accessibility
 * - Tab content switching
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import SearchPage from '../SearchPage';

// Mock ChatSearch component
vi.mock('@/components/search/ChatSearch', () => ({
  default: () => <div data-testid="chat-search-mock">Chat Search Component</div>,
}));

// Mock KeywordSearch component
vi.mock('@/components/search/KeywordSearch', () => ({
  default: () => (
    <div data-testid="keyword-search-mock">Keyword Search Component</div>
  ),
}));

describe('SearchPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ===== Rendering =====

  describe('rendering', () => {
    it('should render the search page container', () => {
      render(<SearchPage />);

      expect(screen.getByTestId('search-page')).toBeInTheDocument();
    });

    it('should render page title and description', () => {
      render(<SearchPage />);

      expect(screen.getByText('Search')).toBeInTheDocument();
      expect(
        screen.getByText(
          'Search through the knowledge base using chat or keyword search'
        )
      ).toBeInTheDocument();
    });

    it('should render tab navigation with both tabs', () => {
      render(<SearchPage />);

      expect(screen.getByRole('tablist')).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /Chat Search/i })).toBeInTheDocument();
      expect(
        screen.getByRole('tab', { name: /Keyword Search/i })
      ).toBeInTheDocument();
    });

    it('should render chat search tab as active by default', () => {
      render(<SearchPage />);

      const chatTab = screen.getByRole('tab', { name: /Chat Search/i });
      const keywordTab = screen.getByRole('tab', { name: /Keyword Search/i });

      expect(chatTab).toHaveAttribute('aria-selected', 'true');
      expect(keywordTab).toHaveAttribute('aria-selected', 'false');
    });

    it('should render ChatSearch component by default', () => {
      render(<SearchPage />);

      expect(screen.getByTestId('chat-search-mock')).toBeInTheDocument();
      expect(
        screen.queryByTestId('keyword-search-mock')
      ).not.toBeInTheDocument();
    });
  });

  // ===== Tab Navigation =====

  describe('tab navigation', () => {
    it('should switch to keyword search when keyword tab is clicked', () => {
      render(<SearchPage />);

      const keywordTab = screen.getByRole('tab', { name: /Keyword Search/i });
      fireEvent.click(keywordTab);

      expect(keywordTab).toHaveAttribute('aria-selected', 'true');
      expect(screen.getByTestId('keyword-search-mock')).toBeInTheDocument();
      expect(screen.queryByTestId('chat-search-mock')).not.toBeInTheDocument();
    });

    it('should switch back to chat search when chat tab is clicked', () => {
      render(<SearchPage />);

      // First switch to keyword
      fireEvent.click(screen.getByRole('tab', { name: /Keyword Search/i }));

      // Then switch back to chat
      const chatTab = screen.getByRole('tab', { name: /Chat Search/i });
      fireEvent.click(chatTab);

      expect(chatTab).toHaveAttribute('aria-selected', 'true');
      expect(screen.getByTestId('chat-search-mock')).toBeInTheDocument();
    });

    it('should update aria-selected on tab switch', () => {
      render(<SearchPage />);

      const chatTab = screen.getByRole('tab', { name: /Chat Search/i });
      const keywordTab = screen.getByRole('tab', { name: /Keyword Search/i });

      // Initial state
      expect(chatTab).toHaveAttribute('aria-selected', 'true');
      expect(keywordTab).toHaveAttribute('aria-selected', 'false');

      // After switching
      fireEvent.click(keywordTab);
      expect(chatTab).toHaveAttribute('aria-selected', 'false');
      expect(keywordTab).toHaveAttribute('aria-selected', 'true');
    });
  });

  // ===== Accessibility =====

  describe('accessibility', () => {
    it('should have aria-label on tab navigation', () => {
      render(<SearchPage />);

      expect(screen.getByRole('tablist')).toHaveAttribute(
        'aria-label',
        'Search tabs'
      );
    });

    it('should have aria-controls on each tab', () => {
      render(<SearchPage />);

      const chatTab = screen.getByRole('tab', { name: /Chat Search/i });
      const keywordTab = screen.getByRole('tab', { name: /Keyword Search/i });

      expect(chatTab).toHaveAttribute('aria-controls', 'tab-panel-chat');
      expect(keywordTab).toHaveAttribute('aria-controls', 'tab-panel-keyword');
    });

    it('should have role="tabpanel" on content area', () => {
      render(<SearchPage />);

      expect(screen.getByRole('tabpanel')).toBeInTheDocument();
    });

    it('should update tabpanel id when tab changes', () => {
      render(<SearchPage />);

      // Initial - chat panel
      expect(screen.getByRole('tabpanel')).toHaveAttribute(
        'id',
        'tab-panel-chat'
      );

      // After switching to keyword
      fireEvent.click(screen.getByRole('tab', { name: /Keyword Search/i }));
      expect(screen.getByRole('tabpanel')).toHaveAttribute(
        'id',
        'tab-panel-keyword'
      );
    });
  });

  // ===== Visual Elements =====

  describe('visual elements', () => {
    it('should render icons in tabs', () => {
      render(<SearchPage />);

      const tabs = screen.getAllByRole('tab');
      // Each tab should contain an svg icon
      tabs.forEach((tab) => {
        expect(tab.querySelector('svg')).toBeInTheDocument();
      });
    });

    it('should show active indicator on selected tab', () => {
      render(<SearchPage />);

      const chatTab = screen.getByRole('tab', { name: /Chat Search/i });
      // Active tab should have a visual indicator (span with specific classes)
      expect(chatTab.querySelector('span.absolute')).toBeInTheDocument();
    });
  });
});
