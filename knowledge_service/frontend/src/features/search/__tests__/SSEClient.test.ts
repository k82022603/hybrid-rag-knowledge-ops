/**
 * SSEPostClient unit tests
 *
 * Tests the SSEPostClient utility class for:
 * - POST-based connection lifecycle (connect, close, abort)
 * - fetch + ReadableStream processing
 * - SSE event parsing (data:, event:, [DONE], JSON, raw text)
 * - Error handling with exponential backoff retry
 * - Abort/cancel via AbortController
 * - Reconnection logic
 * - Authorization header inclusion
 *
 * STORY-050: Migrated from EventSource-based tests to
 * fetch + ReadableStream mocks.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  SSEPostClient,
  parseSSEBuffer,
  type SSEPostClientOptions,
  type SSERequestBody,
} from '@/shared/api/sse';

// --------------------------------------------------------------------------
// Mock fetch + ReadableStream
// --------------------------------------------------------------------------

/** Helper to create a ReadableStream from SSE text chunks */
function createSSEStream(
  chunks: string[]
): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  let index = 0;

  return new ReadableStream({
    pull(controller) {
      if (index < chunks.length) {
        controller.enqueue(encoder.encode(chunks[index]));
        index++;
      } else {
        controller.close();
      }
    },
  });
}

/** Helper to create a mock Response with SSE stream */
function createMockResponse(
  chunks: string[],
  status = 200,
  statusText = 'OK'
): Response {
  const stream = createSSEStream(chunks);
  return new Response(stream, {
    status,
    statusText,
    headers: { 'Content-Type': 'text/event-stream' },
  });
}

/** Default request body for tests */
const defaultBody: SSERequestBody = {
  query: 'test query',
  conversation_history: [],
  top_k: 5,
};

/** Helper to create options with default mocks */
function createOptions(
  overrides: Partial<Omit<SSEPostClientOptions, 'body'>> = {}
): SSEPostClientOptions {
  return {
    body: defaultBody,
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
// parseSSEBuffer Tests
// --------------------------------------------------------------------------

describe('parseSSEBuffer', () => {
  it('should parse a single data event', () => {
    const onEvent = vi.fn();
    const remaining = parseSSEBuffer('data: Hello\n\n', onEvent);

    expect(onEvent).toHaveBeenCalledWith('message', 'Hello');
    expect(remaining).toBe('');
  });

  it('should parse multiple events', () => {
    const onEvent = vi.fn();
    const remaining = parseSSEBuffer(
      'data: first\n\ndata: second\n\n',
      onEvent
    );

    expect(onEvent).toHaveBeenCalledTimes(2);
    expect(onEvent).toHaveBeenCalledWith('message', 'first');
    expect(onEvent).toHaveBeenCalledWith('message', 'second');
    expect(remaining).toBe('');
  });

  it('should handle custom event types', () => {
    const onEvent = vi.fn();
    parseSSEBuffer('event: custom\ndata: payload\n\n', onEvent);

    expect(onEvent).toHaveBeenCalledWith('custom', 'payload');
  });

  it('should return incomplete events as remaining buffer', () => {
    const onEvent = vi.fn();
    const remaining = parseSSEBuffer('data: complete\n\ndata: incomp', onEvent);

    expect(onEvent).toHaveBeenCalledTimes(1);
    expect(onEvent).toHaveBeenCalledWith('message', 'complete');
    expect(remaining).toBe('data: incomp');
  });

  it('should handle multi-line data events', () => {
    const onEvent = vi.fn();
    parseSSEBuffer('data: line1\ndata: line2\n\n', onEvent);

    expect(onEvent).toHaveBeenCalledWith('message', 'line1\nline2');
  });

  it('should ignore comment lines', () => {
    const onEvent = vi.fn();
    parseSSEBuffer(': this is a comment\ndata: actual data\n\n', onEvent);

    expect(onEvent).toHaveBeenCalledWith('message', 'actual data');
  });

  it('should skip empty events', () => {
    const onEvent = vi.fn();
    parseSSEBuffer('\n\ndata: real\n\n', onEvent);

    expect(onEvent).toHaveBeenCalledTimes(1);
    expect(onEvent).toHaveBeenCalledWith('message', 'real');
  });

  it('should handle [DONE] sentinel as data', () => {
    const onEvent = vi.fn();
    parseSSEBuffer('data: [DONE]\n\n', onEvent);

    expect(onEvent).toHaveBeenCalledWith('message', '[DONE]');
  });

  it('should handle JSON data events', () => {
    const onEvent = vi.fn();
    const json = JSON.stringify({ type: 'token', data: 'hello' });
    parseSSEBuffer(`data: ${json}\n\n`, onEvent);

    expect(onEvent).toHaveBeenCalledWith('message', json);
  });
});

// --------------------------------------------------------------------------
// SSEPostClient Tests
// --------------------------------------------------------------------------

describe('SSEPostClient', () => {
  let fetchSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.useFakeTimers();
    fetchSpy = vi.fn();
    vi.stubGlobal('fetch', fetchSpy);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  // ===== Connection Lifecycle =====

  describe('connection lifecycle', () => {
    it('should start in idle state', () => {
      const options = createOptions();
      const client = new SSEPostClient('/api/test', options);

      expect(client.state).toBe('idle');
      expect(client.isConnected).toBe(false);
      expect(client.isAborted).toBe(false);
    });

    it('should transition to connecting state on connect()', () => {
      fetchSpy.mockReturnValue(new Promise(() => {})); // Never resolves
      const options = createOptions();
      const client = new SSEPostClient('/api/test', options);

      client.connect();

      expect(client.state).toBe('connecting');
    });

    it('should send POST request with correct headers and body', async () => {
      const mockResponse = createMockResponse(['data: hello\n\ndata: [DONE]\n\n']);
      fetchSpy.mockResolvedValue(mockResponse);

      const options = createOptions({
        headers: { Authorization: 'Bearer test-token' },
      });
      const client = new SSEPostClient('/api/test', options);

      client.connect();
      await vi.runAllTimersAsync();

      expect(fetchSpy).toHaveBeenCalledWith(
        '/api/test',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            Accept: 'text/event-stream',
            Authorization: 'Bearer test-token',
          }),
          body: JSON.stringify(defaultBody),
        })
      );
    });

    it('should transition to closed state after stream completes', async () => {
      const mockResponse = createMockResponse(['data: [DONE]\n\n']);
      fetchSpy.mockResolvedValue(mockResponse);

      const options = createOptions();
      const client = new SSEPostClient('/api/test', options);

      client.connect();
      await vi.runAllTimersAsync();

      expect(client.state).toBe('closed');
      expect(options.onComplete).toHaveBeenCalled();
    });

    it('should close connection on close()', () => {
      fetchSpy.mockReturnValue(new Promise(() => {}));
      const options = createOptions();
      const client = new SSEPostClient('/api/test', options);

      client.connect();
      client.close();

      expect(client.state).toBe('closed');
    });
  });

  // ===== Message Parsing =====

  describe('message parsing', () => {
    it('should call onToken for raw text data', async () => {
      const mockResponse = createMockResponse([
        'data: Hello \n\ndata: [DONE]\n\n',
      ]);
      fetchSpy.mockResolvedValue(mockResponse);

      const options = createOptions();
      const client = new SSEPostClient('/api/test', options);

      client.connect();
      await vi.runAllTimersAsync();

      expect(options.onToken).toHaveBeenCalledWith('Hello ');
    });

    it('should call onToken for JSON token events', async () => {
      const tokenEvent = JSON.stringify({ type: 'token', data: 'world' });
      const mockResponse = createMockResponse([
        `data: ${tokenEvent}\n\ndata: [DONE]\n\n`,
      ]);
      fetchSpy.mockResolvedValue(mockResponse);

      const options = createOptions();
      const client = new SSEPostClient('/api/test', options);

      client.connect();
      await vi.runAllTimersAsync();

      expect(options.onToken).toHaveBeenCalledWith('world');
    });

    it('should call onSources for JSON sources events', async () => {
      const sources = [
        {
          chunkId: 'c1',
          documentId: 'd1',
          content: 'test',
          score: 0.95,
        },
      ];
      const sourcesEvent = JSON.stringify({ type: 'sources', data: sources });
      const mockResponse = createMockResponse([
        `data: ${sourcesEvent}\n\ndata: [DONE]\n\n`,
      ]);
      fetchSpy.mockResolvedValue(mockResponse);

      const options = createOptions();
      const client = new SSEPostClient('/api/test', options);

      client.connect();
      await vi.runAllTimersAsync();

      expect(options.onSources).toHaveBeenCalledWith(sources);
    });

    it('should call onComplete and close on [DONE] sentinel', async () => {
      const mockResponse = createMockResponse([
        'data: some text\n\ndata: [DONE]\n\n',
      ]);
      fetchSpy.mockResolvedValue(mockResponse);

      const options = createOptions();
      const client = new SSEPostClient('/api/test', options);

      client.connect();
      await vi.runAllTimersAsync();

      expect(options.onComplete).toHaveBeenCalled();
      expect(client.state).toBe('closed');
    });

    it('should call onError for JSON error events from server', async () => {
      const errorEvent = JSON.stringify({
        type: 'error',
        message: 'Rate limit exceeded',
      });
      const mockResponse = createMockResponse([
        `data: ${errorEvent}\n\ndata: [DONE]\n\n`,
      ]);
      fetchSpy.mockResolvedValue(mockResponse);

      const options = createOptions();
      const client = new SSEPostClient('/api/test', options);

      client.connect();
      await vi.runAllTimersAsync();

      expect(options.onError).toHaveBeenCalledWith(
        expect.objectContaining({
          message: 'Rate limit exceeded',
          code: 'SERVER_ERROR',
        })
      );
    });

    it('should treat unknown JSON structure as raw token text', async () => {
      const unknownJson = JSON.stringify({ foo: 'bar' });
      const mockResponse = createMockResponse([
        `data: ${unknownJson}\n\ndata: [DONE]\n\n`,
      ]);
      fetchSpy.mockResolvedValue(mockResponse);

      const options = createOptions();
      const client = new SSEPostClient('/api/test', options);

      client.connect();
      await vi.runAllTimersAsync();

      expect(options.onToken).toHaveBeenCalledWith(unknownJson);
    });

    it('should handle multiple chunks arriving separately', async () => {
      const mockResponse = createMockResponse([
        'data: first\n\n',
        'data: second\n\n',
        'data: [DONE]\n\n',
      ]);
      fetchSpy.mockResolvedValue(mockResponse);

      const options = createOptions();
      const client = new SSEPostClient('/api/test', options);

      client.connect();
      await vi.runAllTimersAsync();

      expect(options.onToken).toHaveBeenCalledWith('first');
      expect(options.onToken).toHaveBeenCalledWith('second');
      expect(options.onComplete).toHaveBeenCalled();
    });

    it('should handle split SSE events across chunks', async () => {
      // Event split across two chunks
      const mockResponse = createMockResponse([
        'data: hel',
        'lo\n\ndata: [DONE]\n\n',
      ]);
      fetchSpy.mockResolvedValue(mockResponse);

      const options = createOptions();
      const client = new SSEPostClient('/api/test', options);

      client.connect();
      await vi.runAllTimersAsync();

      expect(options.onToken).toHaveBeenCalledWith('hello');
      expect(options.onComplete).toHaveBeenCalled();
    });
  });

  // ===== Error Handling & Retry =====

  describe('error handling and retry', () => {
    it('should retry on network error with exponential backoff', async () => {
      // First 3 calls fail, 4th succeeds
      fetchSpy
        .mockRejectedValueOnce(new TypeError('Failed to fetch'))
        .mockRejectedValueOnce(new TypeError('Failed to fetch'))
        .mockRejectedValueOnce(new TypeError('Failed to fetch'))
        .mockResolvedValueOnce(
          createMockResponse(['data: [DONE]\n\n'])
        );

      const options = createOptions({
        maxRetries: 3,
        retryDelay: 100,
      });
      const client = new SSEPostClient('/api/test', options);

      client.connect();

      // Wait for first fetch to fail
      await vi.advanceTimersByTimeAsync(0);

      expect(client.state).toBe('reconnecting');
      expect(options.onReconnect).toHaveBeenCalledWith(1, 3);

      // Advance past first retry delay (100ms)
      await vi.advanceTimersByTimeAsync(100);
      // Second failure
      await vi.advanceTimersByTimeAsync(0);

      expect(options.onReconnect).toHaveBeenCalledWith(2, 3);

      // Advance past second retry delay (200ms)
      await vi.advanceTimersByTimeAsync(200);
      // Third failure
      await vi.advanceTimersByTimeAsync(0);

      expect(options.onReconnect).toHaveBeenCalledWith(3, 3);

      // Advance past third retry delay (400ms)
      await vi.advanceTimersByTimeAsync(400);
      // Fourth attempt succeeds
      await vi.advanceTimersByTimeAsync(0);
      await vi.runAllTimersAsync();

      expect(options.onComplete).toHaveBeenCalled();
    });

    it('should call onError with MAX_RETRIES_EXCEEDED after all retries exhausted', async () => {
      fetchSpy.mockRejectedValue(new TypeError('Failed to fetch'));

      const options = createOptions({
        maxRetries: 2,
        retryDelay: 100,
      });
      const client = new SSEPostClient('/api/test', options);

      client.connect();

      // Initial attempt fails
      await vi.advanceTimersByTimeAsync(0);

      // Retry 1 (delay 100ms)
      await vi.advanceTimersByTimeAsync(100);
      await vi.advanceTimersByTimeAsync(0);

      // Retry 2 (delay 200ms)
      await vi.advanceTimersByTimeAsync(200);
      await vi.advanceTimersByTimeAsync(0);

      // Exhausted - should fail
      expect(options.onError).toHaveBeenCalledWith(
        expect.objectContaining({
          code: 'MAX_RETRIES_EXCEEDED',
          retriable: false,
        })
      );
      expect(client.state).toBe('error');
    });

    it('should handle HTTP error responses', async () => {
      fetchSpy.mockResolvedValue(
        new Response('Forbidden', { status: 403, statusText: 'Forbidden' })
      );

      const options = createOptions();
      const client = new SSEPostClient('/api/test', options);

      client.connect();
      await vi.runAllTimersAsync();

      expect(options.onError).toHaveBeenCalledWith(
        expect.objectContaining({
          code: 'HTTP_ERROR',
        })
      );
    });

    it('should retry on 5xx server errors', async () => {
      fetchSpy
        .mockResolvedValueOnce(
          new Response('Server Error', { status: 500, statusText: 'Internal Server Error' })
        )
        .mockResolvedValueOnce(
          createMockResponse(['data: [DONE]\n\n'])
        );

      const options = createOptions({
        maxRetries: 3,
        retryDelay: 100,
      });
      const client = new SSEPostClient('/api/test', options);

      client.connect();

      // First attempt - 500 error (retriable)
      await vi.advanceTimersByTimeAsync(0);

      // Retry after delay
      await vi.advanceTimersByTimeAsync(100);
      await vi.runAllTimersAsync();

      expect(options.onComplete).toHaveBeenCalled();
    });
  });

  // ===== Abort =====

  describe('abort', () => {
    it('should prevent further retries on abort', async () => {
      fetchSpy.mockRejectedValue(new TypeError('Failed to fetch'));

      const options = createOptions({ maxRetries: 3, retryDelay: 100 });
      const client = new SSEPostClient('/api/test', options);

      client.connect();
      await vi.advanceTimersByTimeAsync(0);

      // Abort before retry fires
      client.abort();

      await vi.advanceTimersByTimeAsync(10000);

      expect(fetchSpy).toHaveBeenCalledTimes(1);
      expect(client.isAborted).toBe(true);
      expect(client.state).toBe('closed');
    });

    it('should not connect after abort', () => {
      const options = createOptions();
      const client = new SSEPostClient('/api/test', options);

      client.abort();
      client.connect();

      expect(fetchSpy).not.toHaveBeenCalled();
    });

    it('should use AbortController signal in fetch call', () => {
      fetchSpy.mockReturnValue(new Promise(() => {}));
      const options = createOptions();
      const client = new SSEPostClient('/api/test', options);

      client.connect();

      expect(fetchSpy).toHaveBeenCalledWith(
        '/api/test',
        expect.objectContaining({
          signal: expect.any(AbortSignal),
        })
      );
    });
  });

  // ===== POST Body =====

  describe('POST body', () => {
    it('should include conversation_history in request body', async () => {
      const mockResponse = createMockResponse(['data: [DONE]\n\n']);
      fetchSpy.mockResolvedValue(mockResponse);

      const body: SSERequestBody = {
        query: 'What is RAG?',
        conversation_history: [
          { role: 'user', content: 'Tell me about AI' },
          { role: 'assistant', content: 'AI is...' },
        ],
        top_k: 10,
      };

      const options = createOptions();
      options.body = body;
      const client = new SSEPostClient('/api/test', options);

      client.connect();
      await vi.runAllTimersAsync();

      expect(fetchSpy).toHaveBeenCalledWith(
        '/api/test',
        expect.objectContaining({
          body: JSON.stringify(body),
        })
      );
    });

    it('should include filters in request body when provided', async () => {
      const mockResponse = createMockResponse(['data: [DONE]\n\n']);
      fetchSpy.mockResolvedValue(mockResponse);

      const body: SSERequestBody = {
        query: 'test',
        filters: {
          documentType: 'manual',
          projectName: 'ProjectA',
        },
      };

      const options = createOptions();
      options.body = body;
      const client = new SSEPostClient('/api/test', options);

      client.connect();
      await vi.runAllTimersAsync();

      const callBody = JSON.parse(
        fetchSpy.mock.calls[0][1].body as string
      );
      expect(callBody.filters.documentType).toBe('manual');
      expect(callBody.filters.projectName).toBe('ProjectA');
    });
  });

  // ===== Authorization Headers =====

  describe('authorization headers', () => {
    it('should include Authorization header when provided', async () => {
      const mockResponse = createMockResponse(['data: [DONE]\n\n']);
      fetchSpy.mockResolvedValue(mockResponse);

      const options = createOptions({
        headers: { Authorization: 'Bearer jwt-token-123' },
      });
      const client = new SSEPostClient('/api/test', options);

      client.connect();
      await vi.runAllTimersAsync();

      expect(fetchSpy).toHaveBeenCalledWith(
        '/api/test',
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer jwt-token-123',
          }),
        })
      );
    });

    it('should not include Authorization header when not provided', async () => {
      const mockResponse = createMockResponse(['data: [DONE]\n\n']);
      fetchSpy.mockResolvedValue(mockResponse);

      const options = createOptions();
      const client = new SSEPostClient('/api/test', options);

      client.connect();
      await vi.runAllTimersAsync();

      const callHeaders = fetchSpy.mock.calls[0][1].headers as Record<string, string>;
      expect(callHeaders).not.toHaveProperty('Authorization');
    });
  });

  // ===== Default Options =====

  describe('default options', () => {
    it('should use default maxRetries of 3 when not specified', async () => {
      fetchSpy.mockRejectedValue(new TypeError('Failed to fetch'));

      const options: SSEPostClientOptions = {
        body: defaultBody,
        onToken: vi.fn(),
        onError: vi.fn(),
      };
      const client = new SSEPostClient('/api/test', options);

      client.connect();

      // Exhaust 3 retries
      for (let i = 0; i < 3; i++) {
        await vi.advanceTimersByTimeAsync(0);
        await vi.advanceTimersByTimeAsync(10000);
      }

      // 4th attempt should exceed retries
      await vi.advanceTimersByTimeAsync(0);

      expect(options.onError).toHaveBeenCalledWith(
        expect.objectContaining({ code: 'MAX_RETRIES_EXCEEDED' })
      );
    });
  });

  // ===== Stream Completion Without [DONE] =====

  describe('stream completion without [DONE]', () => {
    it('should call onComplete when stream naturally ends', async () => {
      const mockResponse = createMockResponse([
        'data: hello\n\n',
        'data: world\n\n',
      ]);
      fetchSpy.mockResolvedValue(mockResponse);

      const options = createOptions();
      const client = new SSEPostClient('/api/test', options);

      client.connect();
      await vi.runAllTimersAsync();

      expect(options.onToken).toHaveBeenCalledWith('hello');
      expect(options.onToken).toHaveBeenCalledWith('world');
      expect(options.onComplete).toHaveBeenCalled();
    });
  });
});
