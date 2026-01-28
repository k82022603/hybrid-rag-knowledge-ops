/**
 * useStreamingSearch hook unit tests
 *
 * Tests the streaming search hook for:
 * - sendMessage flow (user + assistant message creation, SSE connection)
 * - Token streaming and incremental append
 * - Source citations delivery after stream completes
 * - Cancel stream functionality
 * - Clear messages functionality
 * - Error handling and dismissal
 * - Reconnection state feedback
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useStreamingSearch } from '../hooks/useStreamingSearch';

// --------------------------------------------------------------------------
// Mock EventSource
// --------------------------------------------------------------------------

type MockESInstance = {
  onmessage: ((event: MessageEvent) => void) | null;
  onerror: ((event: Event) => void) | null;
  onopen: ((event: Event) => void) | null;
  close: ReturnType<typeof vi.fn>;
  readyState: number;
  url: string;
};

let mockESInstances: MockESInstance[] = [];

const MockEventSource = vi.fn().mockImplementation((url: string) => {
  const instance: MockESInstance = {
    onmessage: null,
    onerror: null,
    onopen: null,
    close: vi.fn(),
    readyState: 1, // OPEN
    url,
  };
  mockESInstances.push(instance);
  return instance;
});

Object.defineProperty(MockEventSource, 'CONNECTING', { value: 0 });
Object.defineProperty(MockEventSource, 'OPEN', { value: 1 });
Object.defineProperty(MockEventSource, 'CLOSED', { value: 2 });

vi.stubGlobal('EventSource', MockEventSource);

// --------------------------------------------------------------------------
// Helpers
// --------------------------------------------------------------------------

/** Get the latest mock EventSource instance */
function getLatestES(): MockESInstance {
  return mockESInstances[mockESInstances.length - 1];
}

/** Simulate SSE onopen event on latest instance */
function simulateOpen(): void {
  const es = getLatestES();
  es.onopen?.(new Event('open'));
}

/** Simulate SSE message event on latest instance */
function simulateMessage(data: string): void {
  const es = getLatestES();
  es.onmessage?.(new MessageEvent('message', { data }));
}

/** Simulate SSE error event on latest instance */
function simulateError(): void {
  const es = getLatestES();
  es.onerror?.(new Event('error'));
}

// --------------------------------------------------------------------------
// Tests
// --------------------------------------------------------------------------

describe('useStreamingSearch', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    MockEventSource.mockClear();
    mockESInstances = [];
  });

  afterEach(() => {
    vi.useRealTimers();
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
    it('should create user and assistant messages and start SSE connection', () => {
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

      // EventSource should be created
      expect(MockEventSource).toHaveBeenCalledTimes(1);
      expect(getLatestES().url).toContain('query=What%20is%20RAG%3F');
    });

    it('should accept query override parameter', () => {
      const { result } = renderHook(() => useStreamingSearch());

      act(() => {
        result.current.sendMessage('Override query');
      });

      expect(result.current.messages[0].content).toBe('Override query');
      expect(getLatestES().url).toContain('query=Override%20query');
    });

    it('should not send empty query', () => {
      const { result } = renderHook(() => useStreamingSearch());

      act(() => {
        result.current.sendMessage('');
      });

      expect(result.current.messages).toHaveLength(0);
      expect(MockEventSource).not.toHaveBeenCalled();
    });

    it('should not send while already streaming', () => {
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
      expect(MockEventSource).toHaveBeenCalledTimes(1);
    });
  });

  // ===== Token Streaming =====

  describe('token streaming', () => {
    it('should append tokens to assistant message incrementally', () => {
      const { result } = renderHook(() => useStreamingSearch());

      act(() => {
        result.current.sendMessage('Test query');
      });

      act(() => {
        simulateOpen();
      });

      // Stream tokens
      act(() => {
        simulateMessage('Hello');
      });

      expect(result.current.messages[1].content).toBe('Hello');
      expect(result.current.isConnecting).toBe(false);

      act(() => {
        simulateMessage(' World');
      });

      expect(result.current.messages[1].content).toBe('Hello World');
    });

    it('should parse JSON token events', () => {
      const { result } = renderHook(() => useStreamingSearch());

      act(() => {
        result.current.sendMessage('Test');
      });

      act(() => {
        simulateMessage(JSON.stringify({ type: 'token', data: 'Parsed' }));
      });

      expect(result.current.messages[1].content).toBe('Parsed');
    });
  });

  // ===== Source Citations =====

  describe('source citations', () => {
    it('should attach sources to assistant message when received', () => {
      const { result } = renderHook(() => useStreamingSearch());

      act(() => {
        result.current.sendMessage('Test');
      });

      const sources = [
        {
          chunkId: 'c1',
          documentId: 'd1',
          content: 'Source content',
          score: 0.95,
          metadata: { projectName: 'TestProject' },
        },
      ];

      act(() => {
        simulateMessage(JSON.stringify({ type: 'sources', data: sources }));
      });

      expect(result.current.messages[1].sources).toHaveLength(1);
      expect(result.current.messages[1].sources?.[0].chunkId).toBe('c1');
      expect(result.current.messages[1].sources?.[0].score).toBe(0.95);
    });
  });

  // ===== Stream Completion =====

  describe('stream completion', () => {
    it('should finalize message on [DONE] event', () => {
      const { result } = renderHook(() => useStreamingSearch());

      act(() => {
        result.current.sendMessage('Test');
      });

      act(() => {
        simulateMessage('Answer text');
      });

      act(() => {
        simulateMessage('[DONE]');
      });

      expect(result.current.messages[1].isStreaming).toBe(false);
      expect(result.current.messages[1].content).toBe('Answer text');
      expect(result.current.isStreaming).toBe(false);
      expect(result.current.isConnecting).toBe(false);
    });

    it('should display sources after [DONE] event', () => {
      const { result } = renderHook(() => useStreamingSearch());

      act(() => {
        result.current.sendMessage('Test');
      });

      // Stream tokens
      act(() => {
        simulateMessage('The answer is...');
      });

      // Sources arrive
      const sources = [
        { chunkId: 'c1', documentId: 'd1', content: 'ctx', score: 0.9 },
      ];
      act(() => {
        simulateMessage(JSON.stringify({ type: 'sources', data: sources }));
      });

      // Stream completes
      act(() => {
        simulateMessage('[DONE]');
      });

      expect(result.current.messages[1].content).toBe('The answer is...');
      expect(result.current.messages[1].sources).toHaveLength(1);
      expect(result.current.messages[1].isStreaming).toBe(false);
    });
  });

  // ===== Cancel Stream =====

  describe('cancelStream', () => {
    it('should abort the stream and preserve partial content', () => {
      const { result } = renderHook(() => useStreamingSearch());

      act(() => {
        result.current.sendMessage('Test');
      });

      act(() => {
        simulateMessage('Partial');
      });

      act(() => {
        result.current.cancelStream();
      });

      expect(result.current.isStreaming).toBe(false);
      expect(result.current.messages[1].isStreaming).toBe(false);
      expect(result.current.messages[1].content).toBe('Partial');
      expect(getLatestES().close).toHaveBeenCalled();
    });

    it('should set fallback content if cancelled with empty response', () => {
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
    it('should clear all messages and reset state', () => {
      const { result } = renderHook(() => useStreamingSearch());

      act(() => {
        result.current.sendMessage('Test');
      });

      act(() => {
        simulateMessage('Some content');
      });

      act(() => {
        result.current.clearMessages();
      });

      expect(result.current.messages).toEqual([]);
      expect(result.current.isStreaming).toBe(false);
      expect(result.current.error).toBeNull();
      expect(getLatestES().close).toHaveBeenCalled();
    });
  });

  // ===== Error Handling =====

  describe('error handling', () => {
    it('should set error message when max retries exceeded', () => {
      const { result } = renderHook(() => useStreamingSearch());

      act(() => {
        result.current.sendMessage('Test');
      });

      // Trigger errors until retry limit
      for (let i = 0; i < 3; i++) {
        act(() => {
          simulateError();
        });
        act(() => {
          vi.advanceTimersByTime(10000);
        });
      }

      // Final error exceeds retries
      act(() => {
        simulateError();
      });

      expect(result.current.error).toBeTruthy();
      expect(result.current.isStreaming).toBe(false);
      expect(result.current.messages[1].isStreaming).toBe(false);
    });

    it('should set fallback content on error with empty response', () => {
      const { result } = renderHook(() => useStreamingSearch());

      act(() => {
        result.current.sendMessage('Test');
      });

      // Exhaust all retries
      for (let i = 0; i < 3; i++) {
        act(() => {
          simulateError();
          vi.advanceTimersByTime(10000);
        });
      }
      act(() => {
        simulateError();
      });

      expect(result.current.messages[1].content).toContain('error occurred');
    });

    it('should dismiss error via dismissError', () => {
      const { result } = renderHook(() => useStreamingSearch());

      act(() => {
        result.current.sendMessage('Test');
      });

      // Force error
      for (let i = 0; i < 4; i++) {
        act(() => {
          simulateError();
          vi.advanceTimersByTime(10000);
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
    it('should provide reconnect info during retry', () => {
      const { result } = renderHook(() => useStreamingSearch());

      act(() => {
        result.current.sendMessage('Test');
      });

      act(() => {
        simulateError();
      });

      expect(result.current.reconnectInfo).toEqual({
        attempt: 1,
        maxRetries: 3,
      });

      // After successful reconnect, info should clear
      act(() => {
        vi.advanceTimersByTime(1000);
      });

      act(() => {
        simulateOpen();
        simulateMessage('token');
      });

      expect(result.current.reconnectInfo).toBeNull();
    });
  });

  // ===== Custom Base URL =====

  describe('custom base URL', () => {
    it('should use provided baseUrl', () => {
      const { result } = renderHook(() =>
        useStreamingSearch('/custom/api/stream')
      );

      act(() => {
        result.current.sendMessage('Test');
      });

      expect(getLatestES().url).toContain('/custom/api/stream');
    });
  });

  // ===== Cleanup =====

  describe('cleanup on unmount', () => {
    it('should abort SSE client on unmount', () => {
      const { result, unmount } = renderHook(() => useStreamingSearch());

      act(() => {
        result.current.sendMessage('Test');
      });

      const es = getLatestES();

      unmount();

      expect(es.close).toHaveBeenCalled();
    });
  });
});
