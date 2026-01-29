/**
 * Header component tests
 *
 * Tests for the application header component:
 * - Rendering of logo and menu toggle
 * - User menu when authenticated
 * - Login button when not authenticated
 * - Logout functionality
 * - User initials display
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import Header from '../Header';

// Create mock authSlice
const createMockStore = (initialState = {}) => {
  return configureStore({
    reducer: {
      auth: () => ({
        user: null,
        token: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
        ...initialState,
      }),
    },
  });
};

// Mock useAuth
const mockLogout = vi.fn();
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

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const renderHeader = (onMenuClick = vi.fn(), storeState = {}, isSidebarOpen = true) => {
  const store = createMockStore(storeState);
  return render(
    <Provider store={store}>
      <MemoryRouter>
        <Header onMenuClick={onMenuClick} isSidebarOpen={isSidebarOpen} />
      </MemoryRouter>
    </Provider>
  );
};

describe('Header', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default: not authenticated
    mockUseAuth.mockReturnValue({
      user: null,
      isAuthenticated: false,
      authMethod: 'direct',
      logout: mockLogout,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ===== Rendering =====

  describe('rendering', () => {
    it('should render the header element', () => {
      renderHeader();

      expect(screen.getByRole('banner')).toBeInTheDocument();
    });

    it('should render menu toggle button', () => {
      renderHeader();

      expect(
        screen.getByRole('button', { name: /sidebar navigation/i })
      ).toBeInTheDocument();
    });

    it('should render logo icon', () => {
      renderHeader();

      // Logo is an svg inside a div
      const header = screen.getByRole('banner');
      expect(header.querySelector('svg')).toBeInTheDocument();
    });

    it('should render application title', () => {
      renderHeader();

      expect(screen.getByText('Knowledge Portal')).toBeInTheDocument();
    });
  });

  // ===== Menu Toggle =====

  describe('menu toggle', () => {
    it('should call onMenuClick when toggle button is clicked', () => {
      const mockOnMenuClick = vi.fn();
      renderHeader(mockOnMenuClick);

      fireEvent.click(screen.getByRole('button', { name: /sidebar navigation/i }));

      expect(mockOnMenuClick).toHaveBeenCalledTimes(1);
    });
  });

  // ===== Unauthenticated State =====

  describe('unauthenticated state', () => {
    it('should show Sign in link when not authenticated', () => {
      mockUseAuth.mockReturnValue({
        user: null,
        isAuthenticated: false,
        authMethod: 'direct',
        logout: mockLogout,
      });

      renderHeader();

      expect(screen.getByText('Sign in')).toBeInTheDocument();
    });

    it('should not show user menu when not authenticated', () => {
      mockUseAuth.mockReturnValue({
        user: null,
        isAuthenticated: false,
        authMethod: 'direct',
        logout: mockLogout,
      });

      renderHeader();

      expect(screen.queryByRole('menu')).not.toBeInTheDocument();
    });
  });

  // ===== Authenticated State =====

  describe('authenticated state', () => {
    const mockUser = {
      id: 'user-123',
      username: 'testuser',
      name: 'John Doe',
      email: 'john@example.com',
      roles: ['USER', 'KNOWLEDGE_MANAGER'],
    };

    beforeEach(() => {
      mockUseAuth.mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        authMethod: 'direct',
        logout: mockLogout,
      });
    });

    it('should not show Sign in link when authenticated', () => {
      renderHeader();

      expect(screen.queryByText('Sign in')).not.toBeInTheDocument();
    });

    it('should show user avatar with initials', () => {
      renderHeader();

      // User initials for "John Doe" should be "JD"
      expect(screen.getByText('JD')).toBeInTheDocument();
    });

    it('should show user name in menu button', () => {
      renderHeader();

      expect(screen.getByText('John Doe')).toBeInTheDocument();
    });

    it('should show user email in menu button', () => {
      renderHeader();

      expect(screen.getByText('john@example.com')).toBeInTheDocument();
    });
  });

  // ===== User Initials =====

  describe('user initials', () => {
    it('should display correct initials for two-word name', () => {
      mockUseAuth.mockReturnValue({
        user: { name: 'Alice Smith', email: 'alice@test.com' },
        isAuthenticated: true,
        authMethod: 'direct',
        logout: mockLogout,
      });

      renderHeader();

      expect(screen.getByText('AS')).toBeInTheDocument();
    });

    it('should display correct initials for single-word name', () => {
      mockUseAuth.mockReturnValue({
        user: { name: 'Bob', email: 'bob@test.com' },
        isAuthenticated: true,
        authMethod: 'direct',
        logout: mockLogout,
      });

      renderHeader();

      expect(screen.getByText('BO')).toBeInTheDocument();
    });

    it('should display correct initials for three-word name', () => {
      mockUseAuth.mockReturnValue({
        user: { name: 'Mary Jane Watson', email: 'mjw@test.com' },
        isAuthenticated: true,
        authMethod: 'direct',
        logout: mockLogout,
      });

      renderHeader();

      // First and last name initials: "MW"
      expect(screen.getByText('MW')).toBeInTheDocument();
    });

    it('should display "U" when name is not available', () => {
      mockUseAuth.mockReturnValue({
        user: { name: '', email: 'test@test.com' },
        isAuthenticated: true,
        authMethod: 'direct',
        logout: mockLogout,
      });

      renderHeader();

      expect(screen.getByText('U')).toBeInTheDocument();
    });
  });

  // ===== User Menu =====

  describe('user menu', () => {
    const mockUser = {
      id: 'user-123',
      username: 'testuser',
      name: 'Test User',
      email: 'test@example.com',
      roles: ['USER'],
    };

    beforeEach(() => {
      mockUseAuth.mockReturnValue({
        user: mockUser,
        isAuthenticated: true,
        authMethod: 'direct',
        logout: mockLogout,
      });
    });

    it('should open menu when avatar button is clicked', async () => {
      renderHeader();

      // Click the menu button (containing user avatar)
      const menuButton = screen.getByText('TU').closest('button');
      if (menuButton) {
        fireEvent.click(menuButton);
      }

      await waitFor(() => {
        expect(screen.getByText('Profile')).toBeInTheDocument();
      });
    });

    it('should show Profile option in menu', async () => {
      renderHeader();

      const menuButton = screen.getByText('TU').closest('button');
      if (menuButton) {
        fireEvent.click(menuButton);
      }

      await waitFor(() => {
        expect(screen.getByText('Profile')).toBeInTheDocument();
      });
    });

    it('should show Settings option in menu', async () => {
      renderHeader();

      const menuButton = screen.getByText('TU').closest('button');
      if (menuButton) {
        fireEvent.click(menuButton);
      }

      await waitFor(() => {
        expect(screen.getByText('Settings')).toBeInTheDocument();
      });
    });

    it('should show Sign out option in menu', async () => {
      renderHeader();

      const menuButton = screen.getByText('TU').closest('button');
      if (menuButton) {
        fireEvent.click(menuButton);
      }

      await waitFor(() => {
        expect(screen.getByText('Sign out')).toBeInTheDocument();
      });
    });

    it('should navigate to profile when Profile is clicked', async () => {
      renderHeader();

      const menuButton = screen.getByText('TU').closest('button');
      if (menuButton) {
        fireEvent.click(menuButton);
      }

      await waitFor(() => {
        const profileButton = screen.getByText('Profile').closest('button');
        if (profileButton) {
          fireEvent.click(profileButton);
        }
      });

      expect(mockNavigate).toHaveBeenCalledWith('/profile');
    });

    it('should navigate to admin when Settings is clicked', async () => {
      renderHeader();

      const menuButton = screen.getByText('TU').closest('button');
      if (menuButton) {
        fireEvent.click(menuButton);
      }

      await waitFor(() => {
        const settingsButton = screen.getByText('Settings').closest('button');
        if (settingsButton) {
          fireEvent.click(settingsButton);
        }
      });

      expect(mockNavigate).toHaveBeenCalledWith('/admin');
    });
  });

  // ===== Logout =====

  describe('logout', () => {
    it('should navigate to login on direct auth logout', async () => {
      mockUseAuth.mockReturnValue({
        user: { name: 'Test User', email: 'test@test.com' },
        isAuthenticated: true,
        authMethod: 'direct',
        logout: mockLogout,
      });

      renderHeader();

      const menuButton = screen.getByText('TU').closest('button');
      if (menuButton) {
        fireEvent.click(menuButton);
      }

      await waitFor(() => {
        const signOutButton = screen.getByText('Sign out').closest('button');
        if (signOutButton) {
          fireEvent.click(signOutButton);
        }
      });

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/login', { replace: true });
      });
    });

    it('should call keycloak logout for keycloak auth method', async () => {
      mockUseAuth.mockReturnValue({
        user: { name: 'Test User', email: 'test@test.com' },
        isAuthenticated: true,
        authMethod: 'keycloak',
        logout: mockLogout,
      });

      renderHeader();

      const menuButton = screen.getByText('TU').closest('button');
      if (menuButton) {
        fireEvent.click(menuButton);
      }

      await waitFor(() => {
        const signOutButton = screen.getByText('Sign out').closest('button');
        if (signOutButton) {
          fireEvent.click(signOutButton);
        }
      });

      await waitFor(() => {
        expect(mockLogout).toHaveBeenCalled();
      });
    });
  });

  // ===== User Roles =====

  describe('user roles display', () => {
    it('should display user roles in menu', async () => {
      mockUseAuth.mockReturnValue({
        user: {
          name: 'Admin User',
          email: 'admin@test.com',
          roles: ['ADMIN', 'KNOWLEDGE_MANAGER'],
        },
        isAuthenticated: true,
        authMethod: 'direct',
        logout: mockLogout,
      });

      renderHeader();

      const menuButton = screen.getByText('AU').closest('button');
      if (menuButton) {
        fireEvent.click(menuButton);
      }

      await waitFor(() => {
        expect(screen.getByText('ADMIN')).toBeInTheDocument();
        expect(screen.getByText('KNOWLEDGE_MANAGER')).toBeInTheDocument();
      });
    });

    it('should not display default roles', async () => {
      mockUseAuth.mockReturnValue({
        user: {
          name: 'User',
          email: 'user@test.com',
          roles: ['default-roles-kp', 'USER'],
        },
        isAuthenticated: true,
        authMethod: 'direct',
        logout: mockLogout,
      });

      renderHeader();

      const menuButton = screen.getByText('US').closest('button');
      if (menuButton) {
        fireEvent.click(menuButton);
      }

      await waitFor(() => {
        expect(screen.queryByText('default-roles-kp')).not.toBeInTheDocument();
        expect(screen.getByText('USER')).toBeInTheDocument();
      });
    });

    it('should limit displayed roles to 3', async () => {
      mockUseAuth.mockReturnValue({
        user: {
          name: 'Super User',
          email: 'super@test.com',
          roles: ['ADMIN', 'MANAGER', 'EDITOR', 'VIEWER', 'ANALYST'],
        },
        isAuthenticated: true,
        authMethod: 'direct',
        logout: mockLogout,
      });

      renderHeader();

      const menuButton = screen.getByText('SU').closest('button');
      if (menuButton) {
        fireEvent.click(menuButton);
      }

      await waitFor(() => {
        expect(screen.getByText('ADMIN')).toBeInTheDocument();
        expect(screen.getByText('MANAGER')).toBeInTheDocument();
        expect(screen.getByText('EDITOR')).toBeInTheDocument();
        expect(screen.queryByText('VIEWER')).not.toBeInTheDocument();
        expect(screen.queryByText('ANALYST')).not.toBeInTheDocument();
      });
    });
  });
});
