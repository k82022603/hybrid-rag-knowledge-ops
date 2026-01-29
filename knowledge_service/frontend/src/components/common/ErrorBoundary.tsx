/**
 * ErrorBoundary Component
 *
 * A React error boundary that catches JavaScript errors anywhere in its child
 * component tree, logs those errors, and displays a fallback UI.
 *
 * Features:
 * - Catches rendering errors in child components
 * - Provides a user-friendly fallback UI
 * - Logs errors for debugging and monitoring
 * - Supports custom fallback rendering
 * - Allows retry/reset functionality
 */
import React, { Component, type ErrorInfo, type ReactNode } from 'react';
import { logComponentError } from '@/utils/errorLogger';

/**
 * Props for custom fallback component
 */
export interface FallbackProps {
  error: Error;
  resetError: () => void;
}

/**
 * ErrorBoundary component props
 */
export interface ErrorBoundaryProps {
  children: ReactNode;
  /** Custom fallback component to render on error */
  fallback?: ReactNode | ((props: FallbackProps) => ReactNode);
  /** Callback when an error is caught */
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  /** Whether to show error details in development */
  showDetails?: boolean;
}

/**
 * ErrorBoundary component state
 */
interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

/**
 * Default fallback UI component
 */
const DefaultFallback: React.FC<FallbackProps & { showDetails?: boolean; errorInfo?: ErrorInfo | null }> = ({
  error,
  resetError,
  showDetails = false,
  errorInfo,
}) => {
  const isDev = import.meta.env.DEV;

  return (
    <div
      role="alert"
      aria-live="assertive"
      className="min-h-[400px] flex items-center justify-center p-8"
      data-testid="error-boundary-fallback"
    >
      <div className="max-w-md w-full bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 text-center">
        {/* Error Icon */}
        <div className="mx-auto w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mb-4">
          <svg
            className="w-8 h-8 text-red-600 dark:text-red-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
        </div>

        {/* Error Title */}
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
          Something went wrong
        </h2>

        {/* Error Description */}
        <p className="text-gray-600 dark:text-gray-300 mb-4">
          We're sorry, but something unexpected happened. Please try again or contact support if the problem persists.
        </p>

        {/* Error Details (Development only) */}
        {(isDev || showDetails) && error && (
          <div className="mt-4 p-4 bg-gray-100 dark:bg-gray-900 rounded-lg text-left overflow-auto max-h-48">
            <p className="text-sm font-mono text-red-600 dark:text-red-400 break-all">
              {error.name}: {error.message}
            </p>
            {errorInfo?.componentStack && (
              <pre className="mt-2 text-xs font-mono text-gray-500 dark:text-gray-400 whitespace-pre-wrap">
                {errorInfo.componentStack}
              </pre>
            )}
          </div>
        )}

        {/* Action Buttons */}
        <div className="mt-6 flex flex-col sm:flex-row gap-3 justify-center">
          <button
            onClick={resetError}
            className="inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 transition-colors"
            data-testid="error-boundary-retry"
          >
            <svg
              className="w-4 h-4 mr-2"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            Try Again
          </button>
          <button
            onClick={() => window.location.href = '/'}
            className="inline-flex items-center justify-center px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 transition-colors"
            data-testid="error-boundary-home"
          >
            <svg
              className="w-4 h-4 mr-2"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"
              />
            </svg>
            Go to Home
          </button>
        </div>
      </div>
    </div>
  );
};

/**
 * ErrorBoundary class component
 *
 * React Error Boundaries must be class components as they use
 * getDerivedStateFromError and componentDidCatch lifecycle methods.
 */
class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  /**
   * Update state when an error is thrown
   */
  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return {
      hasError: true,
      error,
    };
  }

  /**
   * Log error information when caught
   */
  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // Update state with error info
    this.setState({ errorInfo });

    // Log the error
    logComponentError(error, { componentStack: errorInfo.componentStack ?? undefined });

    // Call custom error handler if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
  }

  /**
   * Reset error state to allow retry
   */
  resetError = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render(): ReactNode {
    const { hasError, error, errorInfo } = this.state;
    const { children, fallback, showDetails } = this.props;

    if (hasError && error) {
      // Custom fallback component
      if (fallback) {
        if (typeof fallback === 'function') {
          return fallback({ error, resetError: this.resetError });
        }
        return fallback;
      }

      // Default fallback UI
      return (
        <DefaultFallback
          error={error}
          resetError={this.resetError}
          showDetails={showDetails}
          errorInfo={errorInfo}
        />
      );
    }

    return children;
  }
}

export default ErrorBoundary;
