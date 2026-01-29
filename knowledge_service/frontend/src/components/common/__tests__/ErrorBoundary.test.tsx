/**
 * ErrorBoundary Component Tests
 *
 * Tests for the ErrorBoundary component.
 * Covers error catching, fallback UI rendering, and reset functionality.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ErrorBoundary, { type FallbackProps } from '../ErrorBoundary';

// Suppress console.error for cleaner test output
const originalError = console.error;

beforeEach(() => {
  console.error = vi.fn();
});

afterEach(() => {
  console.error = originalError;
});

// Component that throws an error for testing
const ThrowError: React.FC<{ shouldThrow?: boolean }> = ({ shouldThrow = true }) => {
  if (shouldThrow) {
    throw new Error('Test error message');
  }
  return <div data-testid="child-component">Child rendered successfully</div>;
};

// Component that throws on render
const BrokenComponent: React.FC = () => {
  throw new Error('Component crashed');
};

describe('ErrorBoundary', () => {
  describe('Normal rendering', () => {
    it('renders children when there is no error', () => {
      render(
        <ErrorBoundary>
          <div data-testid="test-child">Hello World</div>
        </ErrorBoundary>
      );

      expect(screen.getByTestId('test-child')).toBeInTheDocument();
      expect(screen.getByText('Hello World')).toBeInTheDocument();
    });

    it('renders multiple children correctly', () => {
      render(
        <ErrorBoundary>
          <div data-testid="child-1">First</div>
          <div data-testid="child-2">Second</div>
        </ErrorBoundary>
      );

      expect(screen.getByTestId('child-1')).toBeInTheDocument();
      expect(screen.getByTestId('child-2')).toBeInTheDocument();
    });
  });

  describe('Error handling', () => {
    it('catches errors and displays fallback UI', () => {
      render(
        <ErrorBoundary>
          <ThrowError />
        </ErrorBoundary>
      );

      expect(screen.getByTestId('error-boundary-fallback')).toBeInTheDocument();
      expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    });

    it('displays error message in development mode', () => {
      render(
        <ErrorBoundary showDetails>
          <ThrowError />
        </ErrorBoundary>
      );

      expect(screen.getByText(/Test error message/)).toBeInTheDocument();
    });

    it('calls onError callback when error is caught', () => {
      const onError = vi.fn();

      render(
        <ErrorBoundary onError={onError}>
          <ThrowError />
        </ErrorBoundary>
      );

      expect(onError).toHaveBeenCalled();
      expect(onError).toHaveBeenCalledWith(
        expect.any(Error),
        expect.objectContaining({
          componentStack: expect.any(String),
        })
      );
    });
  });

  describe('Fallback UI', () => {
    it('displays default fallback UI', () => {
      render(
        <ErrorBoundary>
          <BrokenComponent />
        </ErrorBoundary>
      );

      expect(screen.getByTestId('error-boundary-fallback')).toBeInTheDocument();
      expect(screen.getByText('Something went wrong')).toBeInTheDocument();
      expect(screen.getByTestId('error-boundary-retry')).toBeInTheDocument();
      expect(screen.getByTestId('error-boundary-home')).toBeInTheDocument();
    });

    it('renders custom fallback ReactNode', () => {
      render(
        <ErrorBoundary fallback={<div data-testid="custom-fallback">Custom Error</div>}>
          <BrokenComponent />
        </ErrorBoundary>
      );

      expect(screen.getByTestId('custom-fallback')).toBeInTheDocument();
      expect(screen.getByText('Custom Error')).toBeInTheDocument();
    });

    it('renders custom fallback function with error and reset', () => {
      const CustomFallback: React.FC<FallbackProps> = ({ error, resetError }) => (
        <div data-testid="custom-fallback">
          <p data-testid="custom-error-message">{error.message}</p>
          <button onClick={resetError} data-testid="custom-reset">
            Reset
          </button>
        </div>
      );

      render(
        <ErrorBoundary fallback={CustomFallback}>
          <ThrowError />
        </ErrorBoundary>
      );

      expect(screen.getByTestId('custom-fallback')).toBeInTheDocument();
      expect(screen.getByTestId('custom-error-message')).toHaveTextContent('Test error message');
      expect(screen.getByTestId('custom-reset')).toBeInTheDocument();
    });
  });

  describe('Reset functionality', () => {
    it('retry button is accessible and clickable', () => {
      render(
        <ErrorBoundary>
          <BrokenComponent />
        </ErrorBoundary>
      );

      // Verify the retry button exists and is clickable
      const retryButton = screen.getByTestId('error-boundary-retry');
      expect(retryButton).toBeInTheDocument();
      expect(retryButton).toBeEnabled();

      // Click should not throw
      fireEvent.click(retryButton);
    });

    it('resets error state using custom fallback reset function', () => {
      let shouldThrow = true;

      const CustomFallback: React.FC<FallbackProps> = ({ resetError }) => (
        <button onClick={resetError} data-testid="custom-reset">
          Try Again
        </button>
      );

      const ToggleThrowComponent: React.FC = () => {
        if (shouldThrow) {
          throw new Error('Error');
        }
        return <div data-testid="success">Success!</div>;
      };

      render(
        <ErrorBoundary fallback={CustomFallback}>
          <ToggleThrowComponent />
        </ErrorBoundary>
      );

      expect(screen.getByTestId('custom-reset')).toBeInTheDocument();

      // Change the throw condition before reset
      shouldThrow = false;

      fireEvent.click(screen.getByTestId('custom-reset'));

      expect(screen.getByTestId('success')).toBeInTheDocument();
    });
  });

  describe('Go to Home functionality', () => {
    it('navigates to home when Go to Home button is clicked', () => {
      const originalLocation = window.location;
      Object.defineProperty(window, 'location', {
        writable: true,
        value: { ...originalLocation, href: '' },
      });

      render(
        <ErrorBoundary>
          <BrokenComponent />
        </ErrorBoundary>
      );

      fireEvent.click(screen.getByTestId('error-boundary-home'));

      expect(window.location.href).toBe('/');

      // Restore original location
      Object.defineProperty(window, 'location', {
        writable: true,
        value: originalLocation,
      });
    });
  });

  describe('Accessibility', () => {
    it('has accessible buttons in fallback UI', () => {
      render(
        <ErrorBoundary>
          <BrokenComponent />
        </ErrorBoundary>
      );

      const retryButton = screen.getByTestId('error-boundary-retry');
      const homeButton = screen.getByTestId('error-boundary-home');

      expect(retryButton).toHaveAccessibleName(/Try Again/);
      expect(homeButton).toHaveAccessibleName(/Go to Home/);
    });

    it('renders error icon with aria-hidden', () => {
      render(
        <ErrorBoundary>
          <BrokenComponent />
        </ErrorBoundary>
      );

      const icons = screen.getByTestId('error-boundary-fallback').querySelectorAll('svg[aria-hidden="true"]');
      expect(icons.length).toBeGreaterThan(0);
    });
  });
});
