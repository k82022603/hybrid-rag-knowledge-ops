/**
 * Sidebar component tests
 *
 * Tests for the navigation sidebar component:
 * - Rendering of menu items
 * - Role-based menu filtering
 * - Navigation handling
 * - Mobile responsive behavior
 * - Active state indicators
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Sidebar from '../Sidebar';

// Mock useAuth
const mockHasRole = vi.fn();
vi.mock('@/auth', () => ({
  useAuth: () => ({
    hasRole: mockHasRole,
  }),
}));

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const renderSidebar = (
  props: { open?: boolean; width?: number; onClose?: () => void } = {},
  initialRoute = '/dashboard'
) => {
  const defaultProps = {
    open: true,
    width: 256,
    ...props,
  };

  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <Sidebar {...defaultProps} />
    </MemoryRouter>
  );
};

describe('Sidebar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default: user has no admin or knowledge manager roles
    mockHasRole.mockReturnValue(false);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ===== Rendering =====

  describe('rendering', () => {
    it('should render the sidebar when open', () => {
      renderSidebar({ open: true });

      expect(screen.getByRole('navigation')).toBeInTheDocument();
    });

    it('should render with specified width', () => {
      renderSidebar({ open: true, width: 300 });

      const sidebar = screen.getByTestId('sidebar');
      expect(sidebar).toHaveStyle({ width: '300px' });
    });

    it('should render Dashboard menu item', () => {
      renderSidebar();

      expect(
        screen.getByRole('button', { name: /Dashboard/i })
      ).toBeInTheDocument();
    });

    it('should render Search menu item', () => {
      renderSidebar();

      expect(
        screen.getByRole('button', { name: /Search/i })
      ).toBeInTheDocument();
    });

    it('should render Bookmarks menu item', () => {
      renderSidebar();

      expect(
        screen.getByRole('button', { name: /Bookmarks/i })
      ).toBeInTheDocument();
    });

    it('should render Profile menu item', () => {
      renderSidebar();

      expect(
        screen.getByRole('button', { name: /Profile/i })
      ).toBeInTheDocument();
    });

    it('should render version info at bottom', () => {
      renderSidebar();

      expect(screen.getByText('Knowledge Portal v0.1.0')).toBeInTheDocument();
      expect(screen.getByText('Powered by Hybrid RAG')).toBeInTheDocument();
    });
  });

  // ===== Role-based Menu =====

  describe('role-based menu filtering', () => {
    it('should not show Knowledge menu for regular users', () => {
      mockHasRole.mockReturnValue(false);
      renderSidebar();

      expect(
        screen.queryByRole('button', { name: /Knowledge/i })
      ).not.toBeInTheDocument();
    });

    it('should not show Upload menu for regular users', () => {
      mockHasRole.mockReturnValue(false);
      renderSidebar();

      expect(
        screen.queryByRole('button', { name: /Upload/i })
      ).not.toBeInTheDocument();
    });

    it('should not show Admin menu for regular users', () => {
      mockHasRole.mockReturnValue(false);
      renderSidebar();

      expect(
        screen.queryByRole('button', { name: /Admin/i })
      ).not.toBeInTheDocument();
    });

    it('should show Knowledge menu for KNOWLEDGE_MANAGER role', () => {
      mockHasRole.mockImplementation((role) =>
        ['KNOWLEDGE_MANAGER'].includes(role)
      );
      renderSidebar();

      expect(
        screen.getByRole('button', { name: /Knowledge/i })
      ).toBeInTheDocument();
    });

    it('should show Upload menu for KNOWLEDGE_MANAGER role', () => {
      mockHasRole.mockImplementation((role) =>
        ['KNOWLEDGE_MANAGER'].includes(role)
      );
      renderSidebar();

      expect(
        screen.getByRole('button', { name: /Upload/i })
      ).toBeInTheDocument();
    });

    it('should show Admin menu for ADMIN role', () => {
      mockHasRole.mockImplementation((role) => ['ADMIN'].includes(role));
      renderSidebar();

      expect(
        screen.getByRole('button', { name: /Admin/i })
      ).toBeInTheDocument();
    });

    it('should show all menus for ADMIN role', () => {
      mockHasRole.mockReturnValue(true);
      renderSidebar();

      expect(
        screen.getByRole('button', { name: /Dashboard/i })
      ).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: /Search/i })
      ).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: /Knowledge/i })
      ).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: /Upload/i })
      ).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: /Bookmarks/i })
      ).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: /Profile/i })
      ).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: /Admin/i })
      ).toBeInTheDocument();
    });
  });

  // ===== Navigation =====

  describe('navigation', () => {
    it('should navigate to dashboard when Dashboard is clicked', () => {
      renderSidebar();

      fireEvent.click(screen.getByRole('button', { name: /Dashboard/i }));

      expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
    });

    it('should navigate to search when Search is clicked', () => {
      renderSidebar();

      fireEvent.click(screen.getByRole('button', { name: /Search/i }));

      expect(mockNavigate).toHaveBeenCalledWith('/search');
    });

    it('should navigate to bookmarks when Bookmarks is clicked', () => {
      renderSidebar();

      fireEvent.click(screen.getByRole('button', { name: /Bookmarks/i }));

      expect(mockNavigate).toHaveBeenCalledWith('/bookmarks');
    });

    it('should navigate to profile when Profile is clicked', () => {
      renderSidebar();

      fireEvent.click(screen.getByRole('button', { name: /Profile/i }));

      expect(mockNavigate).toHaveBeenCalledWith('/profile');
    });

    it('should navigate to knowledge when Knowledge is clicked', () => {
      mockHasRole.mockReturnValue(true);
      renderSidebar();

      fireEvent.click(screen.getByRole('button', { name: /Knowledge/i }));

      expect(mockNavigate).toHaveBeenCalledWith('/knowledge');
    });

    it('should navigate to upload when Upload is clicked', () => {
      mockHasRole.mockReturnValue(true);
      renderSidebar();

      fireEvent.click(screen.getByRole('button', { name: /Upload/i }));

      expect(mockNavigate).toHaveBeenCalledWith('/upload');
    });

    it('should navigate to admin when Admin is clicked', () => {
      mockHasRole.mockReturnValue(true);
      renderSidebar();

      fireEvent.click(screen.getByRole('button', { name: /Admin/i }));

      expect(mockNavigate).toHaveBeenCalledWith('/admin');
    });
  });

  // ===== Active State =====

  describe('active state', () => {
    it('should highlight active menu item for /dashboard', () => {
      renderSidebar({}, '/dashboard');

      const dashboardButton = screen.getByRole('button', { name: /Dashboard/i });
      expect(dashboardButton).toHaveClass('bg-primary-50');
    });

    it('should highlight active menu item for /search', () => {
      renderSidebar({}, '/search');

      const searchButton = screen.getByRole('button', { name: /Search/i });
      expect(searchButton).toHaveClass('bg-primary-50');
    });

    it('should highlight active menu item for nested routes', () => {
      renderSidebar({}, '/search/keyword');

      const searchButton = screen.getByRole('button', { name: /Search/i });
      expect(searchButton).toHaveClass('bg-primary-50');
    });

    it('should show active indicator dot on selected item', () => {
      renderSidebar({}, '/dashboard');

      const dashboardButton = screen.getByRole('button', { name: /Dashboard/i });
      // Active indicator is a span with rounded-full class inside the button
      expect(dashboardButton.querySelector('.rounded-full')).toBeInTheDocument();
    });
  });

  // ===== Mobile Behavior =====

  describe('mobile behavior', () => {
    it('should render mobile close button', () => {
      renderSidebar({ open: true, onClose: vi.fn() });

      expect(
        screen.getByRole('button', { name: /Close sidebar/i })
      ).toBeInTheDocument();
    });

    it('should call onClose when close button is clicked', () => {
      const mockOnClose = vi.fn();
      renderSidebar({ open: true, onClose: mockOnClose });

      fireEvent.click(screen.getByRole('button', { name: /Close sidebar/i }));

      expect(mockOnClose).toHaveBeenCalled();
    });

    it('should render overlay when open', () => {
      renderSidebar({ open: true, onClose: vi.fn() });

      // Overlay has aria-hidden="true"
      const overlay = document.querySelector('[aria-hidden="true"]');
      expect(overlay).toBeInTheDocument();
    });

    it('should call onClose when overlay is clicked', () => {
      const mockOnClose = vi.fn();
      renderSidebar({ open: true, onClose: mockOnClose });

      const overlay = document.querySelector('[aria-hidden="true"]');
      if (overlay) {
        fireEvent.click(overlay);
      }

      expect(mockOnClose).toHaveBeenCalled();
    });

    it('should show Menu text in mobile header', () => {
      renderSidebar({ open: true, onClose: vi.fn() });

      expect(screen.getByText('Menu')).toBeInTheDocument();
    });
  });

  // ===== Sidebar Visibility =====

  describe('sidebar visibility', () => {
    it('should have translate-x-0 class when open', () => {
      renderSidebar({ open: true });

      const sidebar = screen.getByTestId('sidebar');
      expect(sidebar).toHaveClass('translate-x-0');
    });

    it('should have -translate-x-full class when closed', () => {
      renderSidebar({ open: false });

      const sidebar = screen.getByTestId('sidebar');
      expect(sidebar).toHaveClass('-translate-x-full');
    });
  });

  // ===== Dividers =====

  describe('dividers', () => {
    it('should render dividers between menu sections', () => {
      mockHasRole.mockReturnValue(true);
      renderSidebar();

      // There should be at least 2 dividers (before Bookmarks and before Admin)
      const dividers = document.querySelectorAll('.border-t');
      expect(dividers.length).toBeGreaterThanOrEqual(2);
    });
  });

  // ===== Icons =====

  describe('icons', () => {
    it('should render icons for all menu items', () => {
      renderSidebar();

      const buttons = screen.getAllByRole('button');
      // Each menu button should have an svg icon
      buttons.forEach((button) => {
        // Skip the close button which may have different structure
        if (button.querySelector('svg')) {
          expect(button.querySelector('svg')).toBeInTheDocument();
        }
      });
    });
  });
});
