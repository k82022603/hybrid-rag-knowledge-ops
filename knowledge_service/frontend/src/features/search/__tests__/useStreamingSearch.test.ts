/**
 * useStreamingSearch hook unit tests
 *
 * Tests the streaming search hook for:
 * - sendMessage flow (user + assistant message creation, POST SSE connection)
 * - Token streaming and incremental append
 * - Source citations delivery after stream completes
 * - Cancel stream functionality
 * - Clear messages functionality
 * - Error handling and dismissal
 * - Reconnection state feedback
 * - Conversation history in POST body
 * - Authorization header inclusion
 *
 * STORY-050: Migrated from EventSource mocks to fetch + ReadableStream mocks
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useStreamingSearch } from '../hooks/useStreamingSearch';

// --------------------------------------------------------------------------
// Mock fetch + ReadableStream
// --------------------------------------------------------------------------

/** Helper to create a ReadableStream from SSE text chunks */
function createSSEStream(chunks: string[]): ReadableStream<Uint8Array> {
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
  status = 200
): Response {
  const stream = createSSEStream(chunks);
  return new Response(stream, {
    status,
    headers: { 'Content-Type': 'text/event-stream' },
  });
}

/**
 * Helper to create a controllable SSE stream.
 * Returns an object with push() to send chunks and close() to end.
 */
function createControllableStream(): {
  response: Response;
  push: (chunk: string) => void;
  close: () => void;
} {
  const encoder = new TextEncoder();
  let controller: ReadableStreamDefaultController<Uint8Array>;

  const stream = new ReadableStream<Uint8Array>({
    start(ctrl) {
      controller = ctrl;
    },
  });

  const response = new Response(stream, {
    status: 200,
    headers: { 'Content-Type': 'text/event-stream' },
  });

  return {
    response,
    push: (chunk: string) => controller.enqueue(encoder.encode(chunk)),
    close: () => controller.close(),
  };
}

// --------------------------------------------------------------------------
// Mock getAuthToken
// --------------------------------------------------------------------------
vi.mock('@/shared/api/sse', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/shared/api/sse')>();
  return {
    ...actual,
    getAuthToken: vi.fn(() => 'mock-jwt-token'),
  };
});

// --------------------------------------------------------------------------
// Helpers
// --------------------------------------------------------------------------

let fetchSpy: ReturnType<typeof vi.fn>;

// --------------------------------------------------------------------------
// Tests
// --------------------------------------------------------------------------

describe('useStreamingSearch', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    fetchSpy = vi.fn();
    vi.stubGlobal('fetch', fetchSpy);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  // ===== Initial State =====

  describe('initial state', () => {
    it('should return initial state with empty messages and no errors', () => {
      const { result } = renderHook(() => useStreamingSearch());

      expect(result.current.query).toBe('');
      expect(result.current.messages).toEqual([]);
      expect(result.current.isStreaming).toBe(false);
      expect(result.current.isConnecting).toBe(false);
      expect(result.current.error).toBeNull();
      expect(result.current.reconnectInfo).toBeNull();
    });
  });

  // ===== sendMessage =====

  describe('sendMessage', () => {
    it('should create user and assistant messages and start POST SSE connection', async () => {
      const mockResponse = createMockResponse(['data: [DONE]\n\n']);
      fetchSpy.mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useStreamingSearch());

      act(() => {
        result.current.setQuery('What is RAG?');
      });

      act(() => {
        result.current.sendMessage();
      });

      // Should have user message + assistant placeholder
      expect(result.current.messages).toHaveLength(2);
      expect(result.current.messages[0].role).toBe('user');
      expect(result.current.messages[0].content).toBe('What is RAG?');
      expect(result.current.messages[1].role).toBe('assistant');
      expect(result.current.messages[1].content).toBe('');
      expect(result.current.messages[1].isStreaming).toBe(true);

      // Should be streaming
      expect(result.current.isStreaming).toBe(true);
      expect(result.current.isConnecting).toBe(true);

      // Query should be cleared
      expect(result.current.query).toBe('');

      // fetch should be called with POST method
      expect(fetchSpy).toHaveBeenCalledTimes(1);
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            Authorization: 'Bearer mock-jwt-token',
          }),
        })
      );

      // Request body should contain the query
      const callBody = JSON.parse(fetchSpy.mock.calls[0][1].body as string);
      expect(callBody.query).toBe('What is RAG?');
      expect(callBody.conversation_history).toEqual([]);
      expect(callBody.top_k).toBe(5);
    });

    it('should accept query override parameter', () => {
      fetchSpy.mockReturnValue(new Promise(() => {}));

      const { result } = renderHook(() => useStreamingSearch());

      act(() => {
        result.current.sendMessage('Override query');
      });

      expect(result.current.messages[0].content).toBe('Override query');

      const callBody = JSON.parse(fetchSpy.mock.calls[0][1].body as string);
      expect(callBody.query).toBe('Override query');
    });

    it('should not send empty query', () => {
      const { result } = renderHook(() => useStreamingSearch());

      act(() => {
        result.current.sendMessage('');
      });

      expect(result.current.messages).toHaveLength(0);
      expect(fetchSpy).not.toHaveBeenCalled();
    });

    it('should not send while already streaming', () => {
      fetchSpy.mockReturnValue(new Promise(() => {}));

      const { result } = renderHook(() => useStreamingSearch());

      act(() => {
        result.current.sendMessage('First query');
      });

      act(() => {
        result.current.setQuery('Second query');
      });

      act(() => {
        result.current.sendMessage();
      });

      // Only the first query should be sent
      expect(result.current.messages).toHaveLength(2);
      expect(fetchSpy).toHaveBeenCalledTimes(1);
    });

    it('should include conversation history from previous messages', async () => {
      // First round
      const firstResponse = createMockResponse([
        'data: First answer\n\ndata: [DONE]\n\n',
      ]);
      fetchSpy.mockResolvedValueOnce(firstResponse);

      const { result } = renderHook(() => useStreamingSearch());

      await act(async () => {
        result.current.sendMessage('First question');
        await vi.runAllTimersAsync();
      });

      // Second round
      const secondResponse = createMockResponse([
        'data: Second answer\n\ndata: [DONE]\n\n',
      ]);
      fetchSpy.mockResolvedValueOnce(secondResponse);

      await act(async () => {
        result.current.setQuery('Second question');
      });

      await act(async () => {
        result.current.sendMessage();
        await vi.runAllTimersAsync();
      });

      // Second call should include conversation history
      const secondCallBody = JSON.parse(
        fetchSpy.mock.calls[1][1].body as string
      );
      expect(secondCallBody.query).toBe('Second question');
      expect(secondCallBody.conversation_history).toEqual(
        expect.arrayContaining([
          expect.objectContaining({
            role: 'user',
            content: 'First question',
          }),
          expect.objectContaining({
            role: 'assistant',
            content: 'First answer',
          }),
        ])
      );
    });
  });

  // ===== Token Streaming =====

  describe('token streaming', () => {
    it('should append tokens to assistant message incrementally', async () => {
      const mockResponse = createMockResponse([
        'data: Hello\n\n',
        'data:  World\n\n',
        'data: [DONE]\n\n',
      ]);
      fetchSpy.mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useStreamingSearch());

      await act(async () => {
        result.current.sendMessage('Test query');
        await vi.runAllTimersAsync();
      });

      expect(result.current.messages[1].content).toBe('Hello World');
      expect(result.current.isConnecting).toBe(false);
    });

    it('should parse JSON token events', async () => {
      const tokenEvent = JSON.stringify({ type: 'token', data: 'Parsed' });
      const mockResponse = createMockResponse([
        `data: ${tokenEvent}\n\ndata: [DONE]\n\n`,
      ]);
      fetchSpy.mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useStreamingSearch());

      await act(async () => {
        result.current.sendMessage('Test');
        await vi.runAllTimersAsync();
      });

      expect(result.current.messages[1].content).toBe('Parsed');
    });
  });

  // ===== Source Citations =====

  describe('source citations', () => {
    it('should attach sources to assistant message when received', async () => {
      const sources = [
        {
          chunkId: 'c1',
          documentId: 'd1',
          content: 'Source content',
          score: 0.95,
          metadata: { projectName: 'TestProject' },
        },
      ];
      const sourcesEvent = JSON.stringify({ type: 'sources', data: sources });
      const mockResponse = createMockResponse([
        'data: Answer text\n\n',
        `data: ${sourcesEvent}\n\n`,
        'data: [DONE]\n\n',
      ]);
      fetchSpy.mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useStreamingSearch());

      await act(async () => {
        result.current.sendMessage('Test');
        await vi.runAllTimersAsync();
      });

      expect(result.current.messages[1].sources).toHaveLength(1);
      expect(result.current.messages[1].sources?.[0].chunkId).toBe('c1');
      expect(result.current.messages[1].sources?.[0].score).toBe(0.95);
    });
  });

  // ===== Stream Completion =====

  describe('stream completion', () => {
    it('should finalize message on [DONE] event', async () => {
      const mockResponse = createMockResponse([
        'data: Answer text\n\n',
        'data: [DONE]\n\n',
      ]);
      fetchSpy.mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useStreamingSearch());

      await act(async () => {
        result.current.sendMessage('Test');
        await vi.runAllTimersAsync();
      });

      expect(result.current.messages[1].isStreaming).toBe(false);
      expect(result.current.messages[1].content).toBe('Answer text');
      expect(result.current.isStreaming).toBe(false);
      expect(result.current.isConnecting).toBe(false);
    });

    it('should display sources after [DONE] event', async () => {
      const sources = [
        { chunkId: 'c1', documentId: 'd1', content: 'ctx', score: 0.9 },
      ];
      const sourcesEvent = JSON.stringify({ type: 'sources', data: sources });
      const mockResponse = createMockResponse([
        'data: The answer is...\n\n',
        `data: ${sourcesEvent}\n\n`,
        'data: [DONE]\n\n',
      ]);
      fetchSpy.mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useStreamingSearch());

      await act(async () => {
        result.current.sendMessage('Test');
        await vi.runAllTimersAsync();
      });

      expect(result.current.messages[1].content).toBe('The answer is...');
      expect(result.current.messages[1].sources).toHaveLength(1);
      expect(result.current.messages[1].isStreaming).toBe(false);
    });
  });

  // ===== Cancel Stream =====

  describe('cancelStream', () => {
    it('should abort the stream and preserve partial content', async () => {
      // Use a controllable stream so we can cancel mid-stream
      const { response, push } = createControllableStream();
      fetchSpy.mockResolvedValue(response);

      const { result } = renderHook(() => useStreamingSearch());

      await act(async () => {
        result.current.sendMessage('Test');
        // Let fetch resolve
        await vi.advanceTimersByTimeAsync(0);
      });

      // Push some data
      await act(async () => {
        push('data: Partial\n\n');
        await vi.advanceTimersByTimeAsync(0);
      });

      // Cancel
      act(() => {
        result.current.cancelStream();
      });

      expect(result.current.isStreaming).toBe(false);
      expect(result.current.messages[1].isStreaming).toBe(false);
      expect(result.current.messages[1].content).toBe('Partial');
    });

    it('should set fallback content if cancelled with empty response', () => {
      fetchSpy.mockReturnValue(new Promise(() => {}));

      const { result } = renderHook(() => useStreamingSearch());

      act(() => {
        result.current.sendMessage('Test');
      });

      // Cancel immediately without any tokens received
      act(() => {
        result.current.cancelStream();
      });

      expect(result.current.messages[1].content).toBe(
        'Response cancelled by user.'
      );
    });
  });

  // ===== Clear Messages =====

  describe('clearMessages', () => {
    it('should clear all messages and reset state', async () => {
      const mockResponse = createMockResponse([
        'data: Some content\n\ndata: [DONE]\n\n',
      ]);
      fetchSpy.mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useStreamingSearch());

      await act(async () => {
        result.current.sendMessage('Test');
        await vi.runAllTimersAsync();
      });

      act(() => {
        result.current.clearMessages();
      });

      expect(result.current.messages).toEqual([]);
      expect(result.current.isStreaming).toBe(false);
      expect(result.current.error).toBeNull();
    });
  });

  // ===== Error Handling =====

  describe('error handling', () => {
    it('should set error message when max retries exceeded', async () => {
      fetchSpy.mockRejectedValue(new TypeError('Failed to fetch'));

      const { result } = renderHook(() => useStreamingSearch());

      await act(async () => {
        result.current.sendMessage('Test');
      });

      // Exhaust retries
      for (let i = 0; i < 3; i++) {
        await act(async () => {
          await vi.advanceTimersByTimeAsync(0);
          await vi.advanceTimersByTimeAsync(10000);
        });
      }

      // Final failure
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });

      expect(result.current.error).toBeTruthy();
      expect(result.current.isStreaming).toBe(false);
      expect(result.current.messages[1].isStreaming).toBe(false);
    });

    it('should set fallback content on error with empty response', async () => {
      fetchSpy.mockRejectedValue(new TypeError('Failed to fetch'));

      const { result } = renderHook(() => useStreamingSearch());

      await act(async () => {
        result.current.sendMessage('Test');
      });

      // Exhaust all retries
      for (let i = 0; i < 3; i++) {
        await act(async () => {
          await vi.advanceTimersByTimeAsync(0);
          await vi.advanceTimersByTimeAsync(10000);
        });
      }
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });

      expect(result.current.messages[1].content).toContain('error occurred');
    });

    it('should dismiss error via dismissError', async () => {
      fetchSpy.mockRejectedValue(new TypeError('Failed to fetch'));

      const { result } = renderHook(() => useStreamingSearch());

      await act(async () => {
        result.current.sendMessage('Test');
      });

      // Exhaust retries
      for (let i = 0; i < 4; i++) {
        await act(async () => {
          await vi.advanceTimersByTimeAsync(0);
          await vi.advanceTimersByTimeAsync(10000);
        });
      }

      expect(result.current.error).toBeTruthy();

      act(() => {
        result.current.dismissError();
      });

      expect(result.current.error).toBeNull();
    });
  });

  // ===== Reconnection Info =====

  describe('reconnection info', () => {
    it('should provide reconnect info during retry', async () => {
      fetchSpy
        .mockRejectedValueOnce(new TypeError('Failed to fetch'))
        .mockResolvedValueOnce(
          createMockResponse(['data: token\n\ndata: [DONE]\n\n'])
        );

      const { result } = renderHook(() => useStreamingSearch());

      await act(async () => {
        result.current.sendMessage('Test');
        await vi.advanceTimersByTimeAsync(0);
      });

      expect(result.current.reconnectInfo).toEqual({
        attempt: 1,
        maxRetries: 3,
      });

      // After successful reconnect, info should clear
      await act(async () => {
        await vi.advanceTimersByTimeAsync(1000);
        await vi.runAllTimersAsync();
      });

      expect(result.current.reconnectInfo).toBeNull();
    });
  });

  // ===== Custom Base URL =====

  describe('custom base URL', () => {
    it('should use provided baseUrl (string parameter)', () => {
      fetchSpy.mockReturnValue(new Promise(() => {}));

      const { result } = renderHook(() =>
        useStreamingSearch('/custom/api/stream')
      );

      act(() => {
        result.current.sendMessage('Test');
      });

      expect(fetchSpy).toHaveBeenCalledWith(
        '/custom/api/stream',
        expect.any(Object)
      );
    });

    it('should use provided baseUrl (options parameter)', () => {
      fetchSpy.mockReturnValue(new Promise(() => {}));

      const { result } = renderHook(() =>
        useStreamingSearch({ baseUrl: '/custom/api/stream', topK: 10 })
      );

      act(() => {
        result.current.sendMessage('Test');
      });

      expect(fetchSpy).toHaveBeenCalledWith(
        '/custom/api/stream',
        expect.any(Object)
      );

      const callBody = JSON.parse(fetchSpy.mock.calls[0][1].body as string);
      expect(callBody.top_k).toBe(10);
    });
  });

  // ===== Cleanup =====

  describe('cleanup on unmount', () => {
    it('should abort SSE client on unmount', () => {
      fetchSpy.mockReturnValue(new Promise(() => {}));

      const { result, unmount } = renderHook(() => useStreamingSearch());

      act(() => {
        result.current.sendMessage('Test');
      });

      unmount();

      // After unmount, no further actions should occur
      // (The abort is called internally via the client ref cleanup)
      expect(result.current.messages).toHaveLength(2);
    });
  });

  // ===== POST Body Verification =====

  describe('POST body', () => {
    it('should send query in POST body instead of URL query parameter', () => {
      fetchSpy.mockReturnValue(new Promise(() => {}));

      const { result } = renderHook(() => useStreamingSearch());

      act(() => {
        result.current.sendMessage('What is RAG?');
      });

      // URL should not contain query parameter
      const url = fetchSpy.mock.calls[0][0] as string;
      expect(url).not.toContain('query=');
      expect(url).not.toContain('What%20is%20RAG');

      // Body should contain the query
      const body = JSON.parse(fetchSpy.mock.calls[0][1].body as string);
      expect(body.query).toBe('What is RAG?');
    });

    it('should include Authorization header in request', () => {
      fetchSpy.mockReturnValue(new Promise(() => {}));

      const { result } = renderHook(() => useStreamingSearch());

      act(() => {
        result.current.sendMessage('Test');
      });

      const headers = fetchSpy.mock.calls[0][1].headers as Record<
        string,
        string
      >;
      expect(headers['Authorization']).toBe('Bearer mock-jwt-token');
    });
  });
});
