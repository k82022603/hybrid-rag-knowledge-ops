/**
 * Error Logging Utility
 *
 * Provides centralized error logging for the application.
 * Supports different log levels and optional external reporting integration.
 */

export interface ErrorInfo {
  componentStack?: string;
  timestamp?: string;
  userAgent?: string;
  url?: string;
  userId?: string;
}

export interface ErrorLog {
  message: string;
  name: string;
  stack?: string;
  info?: ErrorInfo;
  severity: 'error' | 'warning' | 'info';
}

/**
 * Error severity levels
 */
export enum ErrorSeverity {
  ERROR = 'error',
  WARNING = 'warning',
  INFO = 'info',
}

/**
 * Log storage key for persisting errors
 */
const ERROR_LOG_KEY = 'error_logs';
const MAX_STORED_ERRORS = 50;

/**
 * Get stored error logs from localStorage
 */
export const getStoredErrors = (): ErrorLog[] => {
  try {
    const stored = localStorage.getItem(ERROR_LOG_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
};

/**
 * Store error log to localStorage
 */
const storeError = (errorLog: ErrorLog): void => {
  try {
    const errors = getStoredErrors();
    errors.unshift(errorLog);
    // Keep only the last MAX_STORED_ERRORS entries
    const trimmed = errors.slice(0, MAX_STORED_ERRORS);
    localStorage.setItem(ERROR_LOG_KEY, JSON.stringify(trimmed));
  } catch {
    // Silently fail if localStorage is not available
  }
};

/**
 * Clear all stored error logs
 */
export const clearStoredErrors = (): void => {
  try {
    localStorage.removeItem(ERROR_LOG_KEY);
  } catch {
    // Silently fail if localStorage is not available
  }
};

/**
 * Format error for logging
 */
const formatError = (error: Error, info?: ErrorInfo): ErrorLog => {
  return {
    message: error.message,
    name: error.name,
    stack: error.stack,
    info: {
      ...info,
      timestamp: new Date().toISOString(),
      userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : undefined,
      url: typeof window !== 'undefined' ? window.location.href : undefined,
    },
    severity: ErrorSeverity.ERROR,
  };
};

/**
 * Log error to console and optionally to external service
 *
 * @param error - The error object to log
 * @param info - Additional context information
 * @param severity - Error severity level
 */
export const logError = (
  error: Error,
  info?: ErrorInfo,
  severity: ErrorSeverity = ErrorSeverity.ERROR
): void => {
  const errorLog = formatError(error, info);
  errorLog.severity = severity;

  // Console logging
  switch (severity) {
    case ErrorSeverity.ERROR:
      console.error('[ErrorLogger] Error:', errorLog);
      break;
    case ErrorSeverity.WARNING:
      console.warn('[ErrorLogger] Warning:', errorLog);
      break;
    case ErrorSeverity.INFO:
      console.info('[ErrorLogger] Info:', errorLog);
      break;
  }

  // Store error in localStorage for debugging
  storeError(errorLog);

  // External reporting integration point
  // In production, this would send to a service like Sentry, LogRocket, etc.
  if (import.meta.env.PROD) {
    reportToExternalService(errorLog);
  }
};

/**
 * Report error to external monitoring service
 * This is a placeholder for integration with services like Sentry, LogRocket, etc.
 */
const reportToExternalService = (errorLog: ErrorLog): void => {
  // TODO: Integrate with external error monitoring service
  // Example: Sentry.captureException(errorLog);
  // For now, we'll just log that we would report
  console.log('[ErrorLogger] Would report to external service:', errorLog.message);
};

/**
 * Log React ErrorBoundary errors
 *
 * @param error - The caught error
 * @param errorInfo - React error info with component stack
 */
export const logComponentError = (
  error: Error,
  errorInfo: { componentStack?: string }
): void => {
  logError(error, {
    componentStack: errorInfo.componentStack,
  });
};

/**
 * Create error from unknown caught value
 */
export const toError = (value: unknown): Error => {
  if (value instanceof Error) {
    return value;
  }
  if (typeof value === 'string') {
    return new Error(value);
  }
  return new Error(String(value));
};

export default {
  logError,
  logComponentError,
  getStoredErrors,
  clearStoredErrors,
  toError,
  ErrorSeverity,
};
