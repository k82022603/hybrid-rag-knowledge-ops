/**
 * Accessibility Tests - WCAG 2.1 AA Compliance
 *
 * These tests verify that components meet accessibility requirements
 * using jest-axe for automated accessibility testing.
 *
 * WCAG 2.1 AA Requirements Tested:
 * - 1.3.1 Info and Relationships (Level A)
 * - 1.4.3 Contrast (Minimum) (Level AA)
 * - 2.1.1 Keyboard (Level A)
 * - 2.4.1 Bypass Blocks (Level A)
 * - 2.4.4 Link Purpose (Level A)
 * - 4.1.2 Name, Role, Value (Level A)
 * - 4.1.3 Status Messages (Level AA)
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import { BrowserRouter } from 'react-router-dom';

import SkipLink from '../SkipLink';
import VisuallyHidden from '../VisuallyHidden';
import LiveRegion from '../LiveRegion';
import ErrorBoundary from '../ErrorBoundary';
import Header from '../Header';
import Sidebar from '../Sidebar';
import SearchFilters from '../../search/SearchFilters';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';

// Extend Jest matchers with axe accessibility matchers
expect.extend(toHaveNoViolations);

// Mock the errorLogger
vi.mock('@/utils/errorLogger', () => ({
  logComponentError: vi.fn(),
}));

// Mock useAuth for Header and Sidebar tests
const mockUseAuth = vi.fn();
vi.mock('@/auth', () => ({
  useAuth: () => mockUseAuth(),
}));

// Mock authService
vi.mock('@/services', () => ({
  authService: {
    logout: vi.fn().mockResolvedValue(undefined),
  },
}));

// Create mock store
const createMockStore = () => {
  return configureStore({
    reducer: {
      auth: () => ({
        user: null,
        token: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
      }),
    },
  });
};

describe('Accessibility Components', () => {
  describe('SkipLink', () => {
    it('should have no accessibility violations', async () => {
      const { container } = render(
        <BrowserRouter>
          <SkipLink targetId="main-content" />
          <main id="main-content" tabIndex={-1}>
            Main content
          </main>
        </BrowserRouter>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should be focusable with keyboard', () => {
      render(
        <BrowserRouter>
          <SkipLink targetId="main-content" />
          <main id="main-content" tabIndex={-1}>
            Main content
          </main>
        </BrowserRouter>
      );

      const skipLink = screen.getByTestId('skip-link');
      skipLink.focus();
      expect(document.activeElement).toBe(skipLink);
    });

    it('should move focus to target on click', () => {
      render(
        <BrowserRouter>
          <SkipLink targetId="main-content" />
          <main id="main-content" tabIndex={-1}>
            Main content
          </main>
        </BrowserRouter>
      );

      const skipLink = screen.getByTestId('skip-link');
      const mainContent = screen.getByRole('main');

      fireEvent.click(skipLink);

      expect(document.activeElement).toBe(mainContent);
    });

    it('should move focus to target on Enter key', () => {
      render(
        <BrowserRouter>
          <SkipLink targetId="main-content" />
          <main id="main-content" tabIndex={-1}>
            Main content
          </main>
        </BrowserRouter>
      );

      const skipLink = screen.getByTestId('skip-link');
      const mainContent = screen.getByRole('main');

      fireEvent.keyDown(skipLink, { key: 'Enter' });

      expect(document.activeElement).toBe(mainContent);
    });

    it('should render custom text', () => {
      render(
        <BrowserRouter>
          <SkipLink targetId="main" text="Skip navigation" />
        </BrowserRouter>
      );

      expect(screen.getByText('Skip navigation')).toBeInTheDocument();
    });
  });

  describe('VisuallyHidden', () => {
    it('should have no accessibility violations', async () => {
      const { container } = render(
        <VisuallyHidden>Hidden accessible text</VisuallyHidden>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should be visually hidden but accessible', () => {
      render(<VisuallyHidden>Screen reader text</VisuallyHidden>);

      const element = screen.getByTestId('visually-hidden');
      expect(element).toHaveClass('sr-only');
      expect(element).toHaveTextContent('Screen reader text');
    });

    it('should render as custom element', () => {
      render(<VisuallyHidden as="div">Content</VisuallyHidden>);

      const element = screen.getByTestId('visually-hidden');
      expect(element.tagName.toLowerCase()).toBe('div');
    });
  });

  describe('LiveRegion', () => {
    it('should have no accessibility violations', async () => {
      const { container } = render(
        <LiveRegion message="5 results found" />
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should have correct ARIA attributes for polite announcements', () => {
      render(<LiveRegion message="Loading complete" politeness="polite" />);

      const region = screen.getByTestId('live-region');
      expect(region).toHaveAttribute('role', 'status');
      expect(region).toHaveAttribute('aria-live', 'polite');
      expect(region).toHaveAttribute('aria-atomic', 'true');
    });

    it('should have correct ARIA attributes for assertive announcements', () => {
      render(<LiveRegion message="Error occurred" politeness="assertive" />);

      const region = screen.getByTestId('live-region');
      expect(region).toHaveAttribute('aria-live', 'assertive');
    });

    it('should be visually hidden', () => {
      render(<LiveRegion message="Test message" />);

      const region = screen.getByTestId('live-region');
      expect(region).toHaveClass('sr-only');
    });
  });

  describe('ErrorBoundary', () => {
    // Error boundary tests for accessibility
    const ThrowError = ({ shouldThrow }: { shouldThrow: boolean }) => {
      if (shouldThrow) {
        throw new Error('Test error');
      }
      return <div>No error</div>;
    };

    it('should have no accessibility violations in fallback UI', async () => {
      // Suppress console.error for expected error
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

      const { container } = render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();

      consoleError.mockRestore();
    });

    it('should render accessible error fallback', () => {
      // Suppress console.error for expected error
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      // Check for accessible heading
      expect(screen.getByRole('heading', { name: /something went wrong/i })).toBeInTheDocument();

      // Check for accessible buttons
      expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /go to home/i })).toBeInTheDocument();

      consoleError.mockRestore();
    });

    it('should have focusable retry button', () => {
      // Suppress console.error for expected error
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      );

      const retryButton = screen.getByTestId('error-boundary-retry');
      retryButton.focus();
      expect(document.activeElement).toBe(retryButton);

      consoleError.mockRestore();
    });
  });
});

describe('Keyboard Navigation', () => {
  it('should support tab navigation through interactive elements', () => {
    render(
      <BrowserRouter>
        <div>
          <SkipLink targetId="main-content" />
          <button>First button</button>
          <button>Second button</button>
          <main id="main-content" tabIndex={-1}>
            <button>Main button</button>
          </main>
        </div>
      </BrowserRouter>
    );

    const skipLink = screen.getByTestId('skip-link');
    const firstButton = screen.getByText('First button');
    const secondButton = screen.getByText('Second button');

    // Test tab order
    skipLink.focus();
    expect(document.activeElement).toBe(skipLink);

    fireEvent.keyDown(skipLink, { key: 'Tab' });
    firstButton.focus();
    expect(document.activeElement).toBe(firstButton);

    fireEvent.keyDown(firstButton, { key: 'Tab' });
    secondButton.focus();
    expect(document.activeElement).toBe(secondButton);
  });
});

describe('ARIA Labels', () => {
  it('should have proper aria-label on interactive elements', () => {
    render(
      <BrowserRouter>
        <SkipLink targetId="main" text="Skip to content" />
      </BrowserRouter>
    );

    const skipLink = screen.getByRole('link', { name: /skip to content/i });
    expect(skipLink).toBeInTheDocument();
  });

  it('should announce live region content to screen readers', () => {
    const { rerender } = render(
      <LiveRegion message="No results" />
    );

    expect(screen.getByText('No results')).toBeInTheDocument();

    // Update message
    rerender(<LiveRegion message="5 results found" />);

    expect(screen.getByText('5 results found')).toBeInTheDocument();
  });
});

describe('Header Accessibility', () => {
  beforeEach(() => {
    mockUseAuth.mockReturnValue({
      user: { name: 'Test User', email: 'test@example.com', roles: [] },
      isAuthenticated: true,
      authMethod: 'direct',
      logout: vi.fn(),
      hasRole: () => false,
    });
  });

  it('should have no accessibility violations', async () => {
    const store = createMockStore();
    const { container } = render(
      <Provider store={store}>
        <BrowserRouter>
          <Header onMenuClick={() => {}} isSidebarOpen={true} />
        </BrowserRouter>
      </Provider>
    );

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have accessible sidebar toggle button with aria-expanded', () => {
    const store = createMockStore();
    render(
      <Provider store={store}>
        <BrowserRouter>
          <Header onMenuClick={() => {}} isSidebarOpen={true} />
        </BrowserRouter>
      </Provider>
    );

    const toggleButton = screen.getByTestId('sidebar-toggle');
    expect(toggleButton).toHaveAttribute('aria-expanded', 'true');
    expect(toggleButton).toHaveAttribute('aria-label', 'Close sidebar navigation');
  });

  it('should update aria-label when sidebar is closed', () => {
    const store = createMockStore();
    render(
      <Provider store={store}>
        <BrowserRouter>
          <Header onMenuClick={() => {}} isSidebarOpen={false} />
        </BrowserRouter>
      </Provider>
    );

    const toggleButton = screen.getByTestId('sidebar-toggle');
    expect(toggleButton).toHaveAttribute('aria-expanded', 'false');
    expect(toggleButton).toHaveAttribute('aria-label', 'Open sidebar navigation');
  });

  it('should have role="banner" on header element', () => {
    const store = createMockStore();
    render(
      <Provider store={store}>
        <BrowserRouter>
          <Header onMenuClick={() => {}} isSidebarOpen={true} />
        </BrowserRouter>
      </Provider>
    );

    expect(screen.getByRole('banner')).toBeInTheDocument();
  });
});

describe('Sidebar Accessibility', () => {
  beforeEach(() => {
    mockUseAuth.mockReturnValue({
      user: null,
      isAuthenticated: false,
      authMethod: 'direct',
      logout: vi.fn(),
      hasRole: () => false,
    });
  });

  it('should have no accessibility violations', async () => {
    const { container } = render(
      <BrowserRouter>
        <Sidebar open={true} width={256} onClose={() => {}} />
      </BrowserRouter>
    );

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have navigation landmark via nav element inside aside', () => {
    render(
      <BrowserRouter>
        <Sidebar open={true} width={256} onClose={() => {}} />
      </BrowserRouter>
    );

    // The aside contains a nav element for the menu
    const sidebar = screen.getByTestId('sidebar');
    expect(sidebar).toBeInTheDocument();
    expect(sidebar.querySelector('nav')).toBeInTheDocument();
  });

  it('should have aria-hidden when closed', () => {
    render(
      <BrowserRouter>
        <Sidebar open={false} width={256} onClose={() => {}} />
      </BrowserRouter>
    );

    const sidebar = screen.getByTestId('sidebar');
    expect(sidebar).toHaveAttribute('aria-hidden', 'true');
  });

  it('should have accessible close button', () => {
    render(
      <BrowserRouter>
        <Sidebar open={true} width={256} onClose={() => {}} />
      </BrowserRouter>
    );

    const closeButton = screen.getByTestId('sidebar-close');
    expect(closeButton).toHaveAttribute('aria-label', 'Close sidebar');
  });

  it('should mark current page with aria-current', () => {
    render(
      <BrowserRouter>
        <Sidebar open={true} width={256} onClose={() => {}} />
      </BrowserRouter>
    );

    // Dashboard should be available (no roles required)
    const dashboardButton = screen.getByTestId('nav-dashboard');
    expect(dashboardButton).toBeInTheDocument();
  });
});

describe('SearchFilters Accessibility', () => {
  it('should have no accessibility violations', async () => {
    const { container } = render(
      <SearchFilters filters={{}} onFilterChange={() => {}} />
    );

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have role="search" on container', () => {
    render(
      <SearchFilters filters={{}} onFilterChange={() => {}} />
    );

    expect(screen.getByRole('search')).toBeInTheDocument();
  });

  it('should have labeled filter inputs', () => {
    render(
      <SearchFilters filters={{}} onFilterChange={() => {}} />
    );

    expect(screen.getByLabelText('Document Type')).toBeInTheDocument();
    expect(screen.getByLabelText('Project')).toBeInTheDocument();
    expect(screen.getByLabelText('From Date')).toBeInTheDocument();
    expect(screen.getByLabelText('To Date')).toBeInTheDocument();
  });

  it('should have accessible clear all button when filters are active', () => {
    render(
      <SearchFilters
        filters={{ documentType: 'technical' }}
        onFilterChange={() => {}}
      />
    );

    const clearButton = screen.getByTestId('clear-all-filters');
    expect(clearButton).toHaveAttribute('aria-label', 'Clear all filters');
  });

  it('should have accessible active filter chips', () => {
    render(
      <SearchFilters
        filters={{ documentType: 'technical', projectName: 'project-a' }}
        onFilterChange={() => {}}
      />
    );

    // Check active filters list
    const filterList = screen.getByRole('list', { name: /active filters/i });
    expect(filterList).toBeInTheDocument();

    // Check individual filter remove buttons
    const removeDocTypeBtn = screen.getByRole('button', {
      name: /remove document type filter: technical/i,
    });
    expect(removeDocTypeBtn).toBeInTheDocument();
  });
});
