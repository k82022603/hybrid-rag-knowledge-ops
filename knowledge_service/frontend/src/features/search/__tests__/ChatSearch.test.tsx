/**
 * ChatSearch integration tests
 *
 * Tests the ChatSearch page component with POST-based SSE streaming integration:
 * - Renders all sub-components
 * - Streaming indicator and cancel button visibility
 * - Error banner display and dismiss
 * - End-to-end message flow with fetch + ReadableStream SSE
 *
 * STORY-050: Migrated from EventSource mocks to fetch + ReadableStream mocks
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import ChatSearch from '../ChatSearch';

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
function createMockResponse(chunks: string[]): Response {
  const stream = createSSEStream(chunks);
  return new Response(stream, {
    status: 200,
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

// Mock getAuthToken
vi.mock('@/shared/api/sse', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/shared/api/sse')>();
  return {
    ...actual,
    getAuthToken: vi.fn(() => 'mock-jwt-token'),
  };
});

// Mock scrollIntoView
Element.prototype.scrollIntoView = vi.fn();

// --------------------------------------------------------------------------
// Helpers
// --------------------------------------------------------------------------

let fetchSpy: ReturnType<typeof vi.fn>;

// --------------------------------------------------------------------------
// Tests
// --------------------------------------------------------------------------

describe('ChatSearch', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    fetchSpy = vi.fn();
    vi.stubGlobal('fetch', fetchSpy);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  // ===== Rendering =====

  describe('rendering', () => {
    it('should render the chat search container', () => {
      render(<ChatSearch />);

      expect(screen.getByTestId('chat-search')).toBeInTheDocument();
    });

    it('should render empty state with suggestions when no messages', () => {
      render(<ChatSearch />);

      expect(
        screen.getByText('Knowledge Search Assistant')
      ).toBeInTheDocument();
    });

    it('should render chat input', () => {
      render(<ChatSearch />);

      expect(screen.getByTestId('chat-input')).toBeInTheDocument();
    });

    it('should not show streaming indicator initially', () => {
      render(<ChatSearch />);

      expect(
        screen.queryByTestId('streaming-indicator')
      ).not.toBeInTheDocument();
      expect(
        screen.queryByTestId('cancel-stream-button')
      ).not.toBeInTheDocument();
    });
  });

  // ===== Streaming Flow =====

  describe('streaming flow', () => {
    it('should display streaming indicator and cancel button when streaming', () => {
      // Use a never-resolving fetch so we stay in streaming state
      fetchSpy.mockReturnValue(new Promise(() => {}));

      render(<ChatSearch />);

      const input = screen.getByTestId('chat-input');
      fireEvent.change(input, { target: { value: 'What is RAG?' } });

      const submitButton = screen.getByTestId('chat-submit');
      fireEvent.click(submitButton);

      expect(screen.getByTestId('streaming-indicator')).toBeInTheDocument();
      expect(screen.getByTestId('cancel-stream-button')).toBeInTheDocument();
    });

    it('should show user message and assistant placeholder after submit', () => {
      fetchSpy.mockReturnValue(new Promise(() => {}));

      render(<ChatSearch />);

      const input = screen.getByTestId('chat-input');
      fireEvent.change(input, { target: { value: 'Test question' } });
      fireEvent.click(screen.getByTestId('chat-submit'));

      // User message should appear
      expect(screen.getByText('Test question')).toBeInTheDocument();
    });

    it('should stream tokens into the assistant message', async () => {
      const { response, push } = createControllableStream();
      fetchSpy.mockResolvedValue(response);

      render(<ChatSearch />);

      const input = screen.getByTestId('chat-input');
      fireEvent.change(input, { target: { value: 'Hello?' } });
      fireEvent.click(screen.getByTestId('chat-submit'));

      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });

      await act(async () => {
        push('data: This is \n\n');
        await vi.advanceTimersByTimeAsync(0);
      });

      await act(async () => {
        push('data: the answer.\n\n');
        await vi.advanceTimersByTimeAsync(0);
      });

      expect(screen.getByText('This is the answer.')).toBeInTheDocument();

      // Cleanup
      await act(async () => {
        push('data: [DONE]\n\n');
        await vi.advanceTimersByTimeAsync(0);
      });
    });

    it('should hide streaming indicator after [DONE]', async () => {
      const mockResponse = createMockResponse([
        'data: Answer\n\ndata: [DONE]\n\n',
      ]);
      fetchSpy.mockResolvedValue(mockResponse);

      render(<ChatSearch />);

      const input = screen.getByTestId('chat-input');
      fireEvent.change(input, { target: { value: 'Test' } });
      fireEvent.click(screen.getByTestId('chat-submit'));

      await act(async () => {
        await vi.runAllTimersAsync();
      });

      expect(
        screen.queryByTestId('streaming-indicator')
      ).not.toBeInTheDocument();
      expect(
        screen.queryByTestId('cancel-stream-button')
      ).not.toBeInTheDocument();
    });
  });

  // ===== Cancel =====

  describe('cancel stream', () => {
    it('should cancel streaming when cancel button is clicked', async () => {
      const { response, push } = createControllableStream();
      fetchSpy.mockResolvedValue(response);

      render(<ChatSearch />);

      const input = screen.getByTestId('chat-input');
      fireEvent.change(input, { target: { value: 'Test' } });
      fireEvent.click(screen.getByTestId('chat-submit'));

      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });

      await act(async () => {
        push('data: Partial\n\n');
        await vi.advanceTimersByTimeAsync(0);
      });

      // Click cancel
      fireEvent.click(screen.getByTestId('cancel-stream-button'));

      // Streaming should stop
      expect(
        screen.queryByTestId('streaming-indicator')
      ).not.toBeInTheDocument();
      expect(screen.getByText('Partial')).toBeInTheDocument();
    });

    it('should have accessible cancel button', () => {
      fetchSpy.mockReturnValue(new Promise(() => {}));

      render(<ChatSearch />);

      const input = screen.getByTestId('chat-input');
      fireEvent.change(input, { target: { value: 'Test' } });
      fireEvent.click(screen.getByTestId('chat-submit'));

      const cancelButton = screen.getByTestId('cancel-stream-button');
      expect(cancelButton).toHaveAttribute(
        'aria-label',
        'Cancel streaming response'
      );
    });
  });

  // ===== Error Banner =====

  describe('error banner', () => {
    it('should display error banner when error occurs', async () => {
      fetchSpy.mockRejectedValue(new TypeError('Failed to fetch'));

      render(<ChatSearch />);

      const input = screen.getByTestId('chat-input');
      fireEvent.change(input, { target: { value: 'Test' } });
      fireEvent.click(screen.getByTestId('chat-submit'));

      // Exhaust retries to trigger error
      for (let i = 0; i < 3; i++) {
        await act(async () => {
          await vi.advanceTimersByTimeAsync(0);
          await vi.advanceTimersByTimeAsync(10000);
        });
      }
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });

      // Error banner should appear
      expect(screen.getByText('Dismiss')).toBeInTheDocument();
    });

    it('should dismiss error banner when Dismiss is clicked', async () => {
      fetchSpy.mockRejectedValue(new TypeError('Failed to fetch'));

      render(<ChatSearch />);

      const input = screen.getByTestId('chat-input');
      fireEvent.change(input, { target: { value: 'Test' } });
      fireEvent.click(screen.getByTestId('chat-submit'));

      // Trigger error by exhausting retries
      for (let i = 0; i < 4; i++) {
        await act(async () => {
          await vi.advanceTimersByTimeAsync(0);
          await vi.advanceTimersByTimeAsync(10000);
        });
      }

      const dismissButton = screen.getByText('Dismiss');
      fireEvent.click(dismissButton);

      // Error should be dismissed
      expect(screen.queryByText('Dismiss')).not.toBeInTheDocument();
    });
  });

  // ===== Keyboard Support =====

  describe('keyboard support', () => {
    it('should submit on Enter key press', () => {
      fetchSpy.mockReturnValue(new Promise(() => {}));

      render(<ChatSearch />);

      const input = screen.getByTestId('chat-input');
      fireEvent.change(input, { target: { value: 'Enter test' } });
      fireEvent.keyDown(input, { key: 'Enter' });

      expect(fetchSpy).toHaveBeenCalledTimes(1);
      expect(screen.getByText('Enter test')).toBeInTheDocument();
    });

    it('should not submit on Shift+Enter', () => {
      render(<ChatSearch />);

      const input = screen.getByTestId('chat-input');
      fireEvent.change(input, { target: { value: 'No submit' } });
      fireEvent.keyDown(input, { key: 'Enter', shiftKey: true });

      expect(fetchSpy).not.toHaveBeenCalled();
    });
  });
});
