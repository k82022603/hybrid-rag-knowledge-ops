/**
 * StatCard component tests
 *
 * Tests for the dashboard statistics card component.
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import StatCard, { StatCardSkeleton } from '../components/StatCard';

describe('StatCard', () => {
  const defaultProps = {
    title: 'Total Documents',
    value: '1,234',
    icon: <span data-testid="mock-icon">icon</span>,
    iconBg: 'bg-primary-50',
  };

  it('renders title and value correctly', () => {
    render(<StatCard {...defaultProps} />);

    expect(screen.getByText('Total Documents')).toBeInTheDocument();
    expect(screen.getByText('1,234')).toBeInTheDocument();
  });

  it('renders icon within the icon container', () => {
    render(<StatCard {...defaultProps} />);

    expect(screen.getByTestId('mock-icon')).toBeInTheDocument();
  });

  it('renders subtitle when provided', () => {
    render(<StatCard {...defaultProps} subtitle="12 added today" />);

    expect(screen.getByText('12 added today')).toBeInTheDocument();
  });

  it('does not render subtitle when not provided', () => {
    render(<StatCard {...defaultProps} />);

    expect(screen.queryByText('added today')).not.toBeInTheDocument();
  });

  it('renders positive trend indicator', () => {
    render(
      <StatCard {...defaultProps} trend={{ value: 12, isPositive: true }} />
    );

    expect(screen.getByText('+12%')).toBeInTheDocument();
  });

  it('renders negative trend indicator', () => {
    render(
      <StatCard {...defaultProps} trend={{ value: -5, isPositive: false }} />
    );

    expect(screen.getByText('-5%')).toBeInTheDocument();
  });

  it('does not render trend when not provided', () => {
    render(<StatCard {...defaultProps} />);

    expect(screen.queryByText('%')).not.toBeInTheDocument();
  });

  it('has correct data-testid', () => {
    render(<StatCard {...defaultProps} />);

    expect(screen.getByTestId('stat-card')).toBeInTheDocument();
  });

  it('has correct aria-label', () => {
    render(<StatCard {...defaultProps} />);

    expect(
      screen.getByRole('region', { name: 'Total Documents: 1,234' })
    ).toBeInTheDocument();
  });

  it('applies custom iconBg class', () => {
    const { container } = render(
      <StatCard {...defaultProps} iconBg="bg-success-50" />
    );

    const iconContainer = container.querySelector('.bg-success-50');
    expect(iconContainer).toBeInTheDocument();
  });
});

describe('StatCardSkeleton', () => {
  it('renders skeleton with correct test id', () => {
    render(<StatCardSkeleton />);

    expect(screen.getByTestId('stat-card-skeleton')).toBeInTheDocument();
  });

  it('has animate-pulse class', () => {
    render(<StatCardSkeleton />);

    const skeleton = screen.getByTestId('stat-card-skeleton');
    expect(skeleton).toHaveClass('animate-pulse');
  });

  it('is hidden from accessibility tree', () => {
    render(<StatCardSkeleton />);

    const skeleton = screen.getByTestId('stat-card-skeleton');
    expect(skeleton).toHaveAttribute('aria-hidden', 'true');
  });
});
