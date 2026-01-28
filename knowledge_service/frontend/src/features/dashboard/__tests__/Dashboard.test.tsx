/**
 * Dashboard component tests
 *
 * Tests for the main Dashboard component.
 * Covers all Acceptance Criteria (AC1-AC5).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Dashboard from '../Dashboard';

// Mock useAuth
const mockUser = {
  id: 'user-1',
  username: 'testuser',
  email: 'test@example.com',
  name: 'Test User',
  roles: ['USER'],
};

vi.mock('@/auth', () => ({
  useAuth: () => ({
    user: mockUser,
    isAuthenticated: true,
    hasRole: (role: string) => mockUser.roles.includes(role),
    authMethod: 'direct',
    logout: vi.fn(),
  }),
}));

// Mock dashboardService
vi.mock('@/services/dashboardService', () => ({
  dashboardService: {
    getStats: vi.fn().mockResolvedValue({
      totalDocuments: 1234,
      totalSearches: 5678,
      activeUsers: 42,
      indexingRate: 150,
      documentsToday: 12,
      searchesToday: 89,
    }),
    getSystemHealth: vi.fn().mockResolvedValue({
      overall: 'healthy',
      services: [],
    }),
    getRecentActivities: vi.fn().mockResolvedValue([]),
    getSearchTrends: vi.fn().mockResolvedValue([]),
    getPopularQueries: vi.fn().mockResolvedValue([]),
    getDocumentTypeDistribution: vi.fn().mockResolvedValue([]),
  },
}));

// Mock react-router-dom navigate
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => vi.fn(),
  };
});

const createQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: 0,
      },
    },
  });

const renderDashboard = () => {
  const queryClient = createQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    </QueryClientProvider>
  );
};

describe('Dashboard', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('renders dashboard page with correct data-testid', () => {
    renderDashboard();

    expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
  });

  it('displays welcome message with user name (AC1)', () => {
    renderDashboard();

    expect(screen.getByTestId('welcome-section')).toBeInTheDocument();
    expect(screen.getByText('Test User')).toBeInTheDocument();
  });

  it('displays time-based greeting in welcome message (AC1)', () => {
    renderDashboard();

    const welcomeSection = screen.getByTestId('welcome-section');
    const headingText = welcomeSection.querySelector('h1')?.textContent || '';

    // Should contain one of the greetings
    const hasGreeting =
      headingText.includes('Good morning') ||
      headingText.includes('Good afternoon') ||
      headingText.includes('Good evening');
    expect(hasGreeting).toBe(true);
  });

  it('shows loading skeletons initially (AC2)', () => {
    renderDashboard();

    // Should show loading state initially
    expect(screen.getByTestId('stats-loading')).toBeInTheDocument();
  });

  it('renders stat cards after data loads (AC2)', async () => {
    renderDashboard();

    // Wait for data to load
    const totalDocs = await screen.findByText('1,234');
    expect(totalDocs).toBeInTheDocument();

    const totalSearches = await screen.findByText('5,678');
    expect(totalSearches).toBeInTheDocument();

    const activeUsers = await screen.findByText('42');
    expect(activeUsers).toBeInTheDocument();
  });

  it('renders quick search component (AC4)', () => {
    renderDashboard();

    expect(screen.getByTestId('quick-search')).toBeInTheDocument();
    expect(screen.getByTestId('quick-search-input')).toBeInTheDocument();
  });

  it('renders Recent Searches section header (AC3)', () => {
    renderDashboard();

    expect(screen.getByText('Recent Searches')).toBeInTheDocument();
  });

  it('shows empty state for recent searches when none exist (AC3)', () => {
    renderDashboard();

    expect(screen.getByText('No recent searches yet.')).toBeInTheDocument();
  });

  it('renders Getting Started guide', () => {
    renderDashboard();

    expect(screen.getByText('Getting Started')).toBeInTheDocument();
    expect(screen.getByText('Search Knowledge')).toBeInTheDocument();
    expect(screen.getByText('Browse Documents')).toBeInTheDocument();
    expect(screen.getByText('Collaborate')).toBeInTheDocument();
  });

  it('renders Quick Search section header', () => {
    renderDashboard();

    expect(screen.getByText('Quick Search')).toBeInTheDocument();
  });
});
