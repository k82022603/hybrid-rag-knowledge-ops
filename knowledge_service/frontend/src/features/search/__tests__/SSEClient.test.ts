/**
 * SSEClient unit tests
 *
 * Tests the SSEClient utility class for:
 * - Connection lifecycle (connect, close, abort)
 * - Message parsing (token, sources, [DONE], raw text, JSON)
 * - Error handling with exponential backoff retry
 * - Abort cancellation
 * - Reconnection logic
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { SSEClient, type SSEOptions } from '@/shared/api/sse';

// --------------------------------------------------------------------------
// Mock EventSource
// --------------------------------------------------------------------------

type EventSourceHandler = ((event: MessageEvent) => void) | null;
type EventSourceErrorHandler = ((event: Event) => void) | null;
type EventSourceOpenHandler = ((event: Event) => void) | null;

let mockEventSourceInstance: {
  onmessage: EventSourceHandler;
  onerror: EventSourceErrorHandler;
  onopen: EventSourceOpenHandler;
  close: ReturnType<typeof vi.fn>;
  readyState: number;
  url: string;
};

const MockEventSource = vi.fn().mockImplementation((url: string) => {
  mockEventSourceInstance = {
    onmessage: null,
    onerror: null,
    onopen: null,
    close: vi.fn(),
    readyState: EventSource.OPEN,
    url,
  };
  return mockEventSourceInstance;
});

// Assign EventSource readyState constants
Object.defineProperty(MockEventSource, 'CONNECTING', { value: 0 });
Object.defineProperty(MockEventSource, 'OPEN', { value: 1 });
Object.defineProperty(MockEventSource, 'CLOSED', { value: 2 });

// Replace global EventSource
vi.stubGlobal('EventSource', MockEventSource);

// --------------------------------------------------------------------------
// Helper to create options with default mocks
// --------------------------------------------------------------------------
function createOptions(overrides: Partial<SSEOptions> = {}): SSEOptions {
  return {
    onToken: vi.fn(),
    onSources: vi.fn(),
    onComplete: vi.fn(),
    onError: vi.fn(),
    onReconnect: vi.fn(),
    maxRetries: 3,
    retryDelay: 100,
    maxRetryDelay: 1000,
    ...overrides,
  };
}

// --------------------------------------------------------------------------
// Tests
// --------------------------------------------------------------------------

describe('SSEClient', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    MockEventSource.mockClear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  // ===== Connection Lifecycle =====

  describe('connection lifecycle', () => {
    it('should create an EventSource with the provided URL on connect()', () => {
      const options = createOptions();
      const client = new SSEClient('/api/test', options);

      expect(client.state).toBe('idle');

      client.connect();

      expect(MockEventSource).toHaveBeenCalledWith('/api/test');
      expect(client.state).toBe('connecting');
    });

    it('should transition to connected state when onopen fires', () => {
      const options = createOptions();
      const client = new SSEClient('/api/test', options);

      client.connect();
      mockEventSourceInstance.onopen?.(new Event('open'));

      expect(client.state).toBe('connected');
    });

    it('should report isConnected=true when state is connected and readyState is OPEN', () => {
      const options = createOptions();
      const client = new SSEClient('/api/test', options);

      client.connect();
      mockEventSourceInstance.onopen?.(new Event('open'));

      expect(client.isConnected).toBe(true);
    });

    it('should close the EventSource on close()', () => {
      const options = createOptions();
      const client = new SSEClient('/api/test', options);

      client.connect();
      client.close();

      expect(mockEventSourceInstance.close).toHaveBeenCalled();
      expect(client.state).toBe('closed');
    });

    it('should close existing connection before creating a new one on reconnect', () => {
      const options = createOptions();
      const client = new SSEClient('/api/test', options);

      client.connect();
      const firstInstance = mockEventSourceInstance;

      // Simulate a second connect
      client.connect();

      expect(firstInstance.close).toHaveBeenCalled();
      expect(MockEventSource).toHaveBeenCalledTimes(2);
    });
  });

  // ===== Message Parsing =====

  describe('message parsing', () => {
    it('should call onToken for raw text data', () => {
      const options = createOptions();
      const client = new SSEClient('/api/test', options);

      client.connect();
      mockEventSourceInstance.onmessage?.(
        new MessageEvent('message', { data: 'Hello ' })
      );

      expect(options.onToken).toHaveBeenCalledWith('Hello ');
    });

    it('should call onToken for JSON token events', () => {
      const options = createOptions();
      const client = new SSEClient('/api/test', options);

      client.connect();
      mockEventSourceInstance.onmessage?.(
        new MessageEvent('message', {
          data: JSON.stringify({ type: 'token', data: 'world' }),
        })
      );

      expect(options.onToken).toHaveBeenCalledWith('world');
    });

    it('should call onSources for JSON sources events', () => {
      const options = createOptions();
      const client = new SSEClient('/api/test', options);

      const sources = [
        {
          chunkId: 'c1',
          documentId: 'd1',
          content: 'test',
          score: 0.95,
        },
      ];

      client.connect();
      mockEventSourceInstance.onmessage?.(
        new MessageEvent('message', {
          data: JSON.stringify({ type: 'sources', data: sources }),
        })
      );

      expect(options.onSources).toHaveBeenCalledWith(sources);
    });

    it('should call onComplete and close on [DONE] sentinel', () => {
      const options = createOptions();
      const client = new SSEClient('/api/test', options);

      client.connect();
      mockEventSourceInstance.onmessage?.(
        new MessageEvent('message', { data: '[DONE]' })
      );

      expect(options.onComplete).toHaveBeenCalled();
      expect(mockEventSourceInstance.close).toHaveBeenCalled();
      expect(client.state).toBe('closed');
    });

    it('should call onError for JSON error events from server', () => {
      const options = createOptions();
      const client = new SSEClient('/api/test', options);

      client.connect();
      mockEventSourceInstance.onmessage?.(
        new MessageEvent('message', {
          data: JSON.stringify({ type: 'error', message: 'Rate limit exceeded' }),
        })
      );

      expect(options.onError).toHaveBeenCalledWith(
        expect.objectContaining({
          message: 'Rate limit exceeded',
          code: 'SERVER_ERROR',
        })
      );
    });

    it('should treat unknown JSON structure as raw token text', () => {
      const options = createOptions();
      const client = new SSEClient('/api/test', options);

      const unknownJson = JSON.stringify({ foo: 'bar' });
      client.connect();
      mockEventSourceInstance.onmessage?.(
        new MessageEvent('message', { data: unknownJson })
      );

      expect(options.onToken).toHaveBeenCalledWith(unknownJson);
    });

    it('should ignore messages after abort', () => {
      const options = createOptions();
      const client = new SSEClient('/api/test', options);

      client.connect();
      client.abort();

      mockEventSourceInstance.onmessage?.(
        new MessageEvent('message', { data: 'ignored' })
      );

      expect(options.onToken).not.toHaveBeenCalled();
    });
  });

  // ===== Error Handling & Retry =====

  describe('error handling and retry', () => {
    it('should retry on error with exponential backoff', () => {
      const options = createOptions({ maxRetries: 3, retryDelay: 100 });
      const client = new SSEClient('/api/test', options);

      client.connect();
      expect(MockEventSource).toHaveBeenCalledTimes(1);

      // First error - should schedule retry after 100ms
      mockEventSourceInstance.onerror?.(new Event('error'));
      expect(client.state).toBe('reconnecting');
      expect(options.onReconnect).toHaveBeenCalledWith(1, 3);

      vi.advanceTimersByTime(100);
      expect(MockEventSource).toHaveBeenCalledTimes(2);

      // Second error - should schedule retry after 200ms
      mockEventSourceInstance.onerror?.(new Event('error'));
      expect(options.onReconnect).toHaveBeenCalledWith(2, 3);

      vi.advanceTimersByTime(200);
      expect(MockEventSource).toHaveBeenCalledTimes(3);

      // Third error - should schedule retry after 400ms
      mockEventSourceInstance.onerror?.(new Event('error'));
      expect(options.onReconnect).toHaveBeenCalledWith(3, 3);

      vi.advanceTimersByTime(400);
      expect(MockEventSource).toHaveBeenCalledTimes(4);
    });

    it('should call onError with MAX_RETRIES_EXCEEDED after all retries exhausted', () => {
      const options = createOptions({ maxRetries: 2, retryDelay: 100 });
      const client = new SSEClient('/api/test', options);

      client.connect();

      // First error -> retry 1
      mockEventSourceInstance.onerror?.(new Event('error'));
      vi.advanceTimersByTime(100);

      // Second error -> retry 2
      mockEventSourceInstance.onerror?.(new Event('error'));
      vi.advanceTimersByTime(200);

      // Third error -> exhausted
      mockEventSourceInstance.onerror?.(new Event('error'));

      expect(options.onError).toHaveBeenCalledWith(
        expect.objectContaining({
          code: 'MAX_RETRIES_EXCEEDED',
          retriable: false,
        })
      );
      expect(client.state).toBe('error');
    });

    it('should reset retry count after successful reconnection', () => {
      const options = createOptions({ maxRetries: 3, retryDelay: 100 });
      const client = new SSEClient('/api/test', options);

      client.connect();

      // Error -> retry
      mockEventSourceInstance.onerror?.(new Event('error'));
      vi.advanceTimersByTime(100);

      // Successful reconnect
      mockEventSourceInstance.onopen?.(new Event('open'));

      // Another error -> should start from retry 1 again
      mockEventSourceInstance.onerror?.(new Event('error'));
      expect(options.onReconnect).toHaveBeenLastCalledWith(1, 3);
    });

    it('should cap retry delay at maxRetryDelay', () => {
      const options = createOptions({
        maxRetries: 10,
        retryDelay: 500,
        maxRetryDelay: 1000,
      });
      const client = new SSEClient('/api/test', options);

      client.connect();

      // Error 1: delay = 500ms
      mockEventSourceInstance.onerror?.(new Event('error'));
      vi.advanceTimersByTime(500);

      // Error 2: delay = 1000ms (500 * 2)
      mockEventSourceInstance.onerror?.(new Event('error'));
      vi.advanceTimersByTime(1000);

      // Error 3: delay = 1000ms (capped, not 2000)
      mockEventSourceInstance.onerror?.(new Event('error'));

      // Verify it does NOT reconnect at 1500ms but at 1000ms
      vi.advanceTimersByTime(999);
      expect(MockEventSource).toHaveBeenCalledTimes(3);
      vi.advanceTimersByTime(1);
      expect(MockEventSource).toHaveBeenCalledTimes(4);
    });
  });

  // ===== Abort =====

  describe('abort', () => {
    it('should close connection and prevent further retries', () => {
      const options = createOptions({ maxRetries: 3, retryDelay: 100 });
      const client = new SSEClient('/api/test', options);

      client.connect();
      mockEventSourceInstance.onerror?.(new Event('error'));

      // Abort before retry fires
      client.abort();

      vi.advanceTimersByTime(1000);

      // Should not have reconnected
      expect(MockEventSource).toHaveBeenCalledTimes(1);
      expect(client.isAborted).toBe(true);
      expect(client.state).toBe('closed');
    });

    it('should not connect after abort', () => {
      const options = createOptions();
      const client = new SSEClient('/api/test', options);

      client.abort();
      client.connect();

      expect(MockEventSource).not.toHaveBeenCalled();
    });

    it('should not retry after abort during error handling', () => {
      const options = createOptions({ maxRetries: 3, retryDelay: 100 });
      const client = new SSEClient('/api/test', options);

      client.connect();

      // Abort then trigger error
      client.abort();
      mockEventSourceInstance.onerror?.(new Event('error'));

      vi.advanceTimersByTime(5000);
      expect(MockEventSource).toHaveBeenCalledTimes(1);
    });
  });

  // ===== Default Options =====

  describe('default options', () => {
    it('should use default maxRetries of 3 when not specified', () => {
      const options: SSEOptions = {
        onToken: vi.fn(),
        onError: vi.fn(),
      };
      const client = new SSEClient('/api/test', options);

      client.connect();

      // Exhaust 3 retries
      for (let i = 0; i < 3; i++) {
        mockEventSourceInstance.onerror?.(new Event('error'));
        vi.advanceTimersByTime(10000);
      }

      // 4th error should trigger MAX_RETRIES_EXCEEDED
      mockEventSourceInstance.onerror?.(new Event('error'));

      expect(options.onError).toHaveBeenCalledWith(
        expect.objectContaining({ code: 'MAX_RETRIES_EXCEEDED' })
      );
    });
  });
});
