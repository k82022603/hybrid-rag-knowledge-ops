/**
 * Error Logger Utility Tests
 *
 * Tests for the error logging utility functions.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  logError,
  logComponentError,
  getStoredErrors,
  clearStoredErrors,
  toError,
  ErrorSeverity,
} from '../errorLogger';

describe('errorLogger', () => {
  const originalConsoleError = console.error;
  const originalConsoleWarn = console.warn;
  const originalConsoleInfo = console.info;
  const originalConsoleLog = console.log;

  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();

    // Mock console methods
    console.error = vi.fn();
    console.warn = vi.fn();
    console.info = vi.fn();
    console.log = vi.fn();
  });

  afterEach(() => {
    // Restore console methods
    console.error = originalConsoleError;
    console.warn = originalConsoleWarn;
    console.info = originalConsoleInfo;
    console.log = originalConsoleLog;
  });

  describe('logError', () => {
    it('logs error to console', () => {
      const error = new Error('Test error');

      logError(error);

      expect(console.error).toHaveBeenCalledWith(
        '[ErrorLogger] Error:',
        expect.objectContaining({
          message: 'Test error',
          name: 'Error',
          severity: 'error',
        })
      );
    });

    it('logs warning to console with warning severity', () => {
      const error = new Error('Test warning');

      logError(error, undefined, ErrorSeverity.WARNING);

      expect(console.warn).toHaveBeenCalledWith(
        '[ErrorLogger] Warning:',
        expect.objectContaining({
          message: 'Test warning',
          severity: 'warning',
        })
      );
    });

    it('logs info to console with info severity', () => {
      const error = new Error('Test info');

      logError(error, undefined, ErrorSeverity.INFO);

      expect(console.info).toHaveBeenCalledWith(
        '[ErrorLogger] Info:',
        expect.objectContaining({
          message: 'Test info',
          severity: 'info',
        })
      );
    });

    it('stores error in localStorage', () => {
      const error = new Error('Test error');

      logError(error);

      const storedErrors = getStoredErrors();
      expect(storedErrors).toHaveLength(1);
      expect(storedErrors[0].message).toBe('Test error');
    });

    it('includes error info in log', () => {
      const error = new Error('Test error');
      const errorInfo = {
        componentStack: 'at Component1\nat Component2',
      };

      logError(error, errorInfo);

      const storedErrors = getStoredErrors();
      expect(storedErrors[0].info?.componentStack).toBe(
        'at Component1\nat Component2'
      );
    });

    it('adds timestamp to error info', () => {
      const error = new Error('Test error');

      logError(error);

      const storedErrors = getStoredErrors();
      expect(storedErrors[0].info?.timestamp).toBeDefined();
      expect(new Date(storedErrors[0].info?.timestamp!).getTime()).not.toBeNaN();
    });
  });

  describe('logComponentError', () => {
    it('logs component error with stack', () => {
      const error = new Error('Component error');
      const errorInfo = { componentStack: 'Component stack trace' };

      logComponentError(error, errorInfo);

      expect(console.error).toHaveBeenCalled();
      const storedErrors = getStoredErrors();
      expect(storedErrors[0].info?.componentStack).toBe('Component stack trace');
    });
  });

  describe('getStoredErrors', () => {
    it('returns empty array when no errors stored', () => {
      const errors = getStoredErrors();
      expect(errors).toEqual([]);
    });

    it('returns stored errors', () => {
      logError(new Error('Error 1'));
      logError(new Error('Error 2'));

      const errors = getStoredErrors();
      expect(errors).toHaveLength(2);
    });

    it('stores errors in reverse chronological order', () => {
      logError(new Error('First error'));
      logError(new Error('Second error'));

      const errors = getStoredErrors();
      expect(errors[0].message).toBe('Second error');
      expect(errors[1].message).toBe('First error');
    });
  });

  describe('clearStoredErrors', () => {
    it('clears all stored errors', () => {
      logError(new Error('Error 1'));
      logError(new Error('Error 2'));

      clearStoredErrors();

      const errors = getStoredErrors();
      expect(errors).toEqual([]);
    });
  });

  describe('toError', () => {
    it('returns same Error if already an Error', () => {
      const error = new Error('Original error');
      const result = toError(error);

      expect(result).toBe(error);
    });

    it('converts string to Error', () => {
      const result = toError('String error message');

      expect(result).toBeInstanceOf(Error);
      expect(result.message).toBe('String error message');
    });

    it('converts other types to Error', () => {
      const result = toError({ key: 'value' });

      expect(result).toBeInstanceOf(Error);
      expect(result.message).toBe('[object Object]');
    });

    it('converts number to Error', () => {
      const result = toError(42);

      expect(result).toBeInstanceOf(Error);
      expect(result.message).toBe('42');
    });

    it('converts null to Error', () => {
      const result = toError(null);

      expect(result).toBeInstanceOf(Error);
      expect(result.message).toBe('null');
    });

    it('converts undefined to Error', () => {
      const result = toError(undefined);

      expect(result).toBeInstanceOf(Error);
      expect(result.message).toBe('undefined');
    });
  });

  describe('Error storage limit', () => {
    it('keeps only the last 50 errors', () => {
      // Log 60 errors
      for (let i = 0; i < 60; i++) {
        logError(new Error(`Error ${i}`));
      }

      const errors = getStoredErrors();
      expect(errors).toHaveLength(50);
      // Most recent error should be Error 59
      expect(errors[0].message).toBe('Error 59');
      // Oldest stored error should be Error 10 (first 10 are trimmed)
      expect(errors[49].message).toBe('Error 10');
    });
  });
});
