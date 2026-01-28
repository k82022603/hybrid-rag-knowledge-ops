/**
 * ChatSearch integration tests
 *
 * Tests the ChatSearch page component with SSE streaming integration:
 * - Renders all sub-components
 * - Streaming indicator and cancel button visibility
 * - Error banner display and dismiss
 * - End-to-end message flow with SSE
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import ChatSearch from '../ChatSearch';

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
    readyState: 1,
    url,
  };
  mockESInstances.push(instance);
  return instance;
});

Object.defineProperty(MockEventSource, 'CONNECTING', { value: 0 });
Object.defineProperty(MockEventSource, 'OPEN', { value: 1 });
Object.defineProperty(MockEventSource, 'CLOSED', { value: 2 });

vi.stubGlobal('EventSource', MockEventSource);

// Mock scrollIntoView
Element.prototype.scrollIntoView = vi.fn();

// --------------------------------------------------------------------------
// Helpers
// --------------------------------------------------------------------------

function getLatestES(): MockESInstance {
  return mockESInstances[mockESInstances.length - 1];
}

function simulateMessage(data: string): void {
  const es = getLatestES();
  es.onmessage?.(new MessageEvent('message', { data }));
}

function simulateOpen(): void {
  const es = getLatestES();
  es.onopen?.(new Event('open'));
}

// --------------------------------------------------------------------------
// Tests
// --------------------------------------------------------------------------

describe('ChatSearch', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    MockEventSource.mockClear();
    mockESInstances = [];
  });

  afterEach(() => {
    vi.useRealTimers();
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
      render(<ChatSearch />);

      const input = screen.getByTestId('chat-input');
      fireEvent.change(input, { target: { value: 'What is RAG?' } });

      const submitButton = screen.getByTestId('chat-submit');
      fireEvent.click(submitButton);

      expect(screen.getByTestId('streaming-indicator')).toBeInTheDocument();
      expect(screen.getByTestId('cancel-stream-button')).toBeInTheDocument();
    });

    it('should show user message and assistant placeholder after submit', () => {
      render(<ChatSearch />);

      const input = screen.getByTestId('chat-input');
      fireEvent.change(input, { target: { value: 'Test question' } });
      fireEvent.click(screen.getByTestId('chat-submit'));

      // User message should appear
      expect(screen.getByText('Test question')).toBeInTheDocument();
    });

    it('should stream tokens into the assistant message', () => {
      render(<ChatSearch />);

      const input = screen.getByTestId('chat-input');
      fireEvent.change(input, { target: { value: 'Hello?' } });
      fireEvent.click(screen.getByTestId('chat-submit'));

      act(() => {
        simulateOpen();
      });

      act(() => {
        simulateMessage('This is ');
      });

      act(() => {
        simulateMessage('the answer.');
      });

      expect(screen.getByText('This is the answer.')).toBeInTheDocument();
    });

    it('should hide streaming indicator after [DONE]', () => {
      render(<ChatSearch />);

      const input = screen.getByTestId('chat-input');
      fireEvent.change(input, { target: { value: 'Test' } });
      fireEvent.click(screen.getByTestId('chat-submit'));

      act(() => {
        simulateMessage('Answer');
      });

      act(() => {
        simulateMessage('[DONE]');
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
    it('should cancel streaming when cancel button is clicked', () => {
      render(<ChatSearch />);

      const input = screen.getByTestId('chat-input');
      fireEvent.change(input, { target: { value: 'Test' } });
      fireEvent.click(screen.getByTestId('chat-submit'));

      act(() => {
        simulateMessage('Partial');
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
    it('should display error banner when error occurs', () => {
      render(<ChatSearch />);

      const input = screen.getByTestId('chat-input');
      fireEvent.change(input, { target: { value: 'Test' } });
      fireEvent.click(screen.getByTestId('chat-submit'));

      // Exhaust retries to trigger error
      for (let i = 0; i < 3; i++) {
        act(() => {
          const es = getLatestES();
          es.onerror?.(new Event('error'));
          vi.advanceTimersByTime(10000);
        });
      }
      act(() => {
        const es = getLatestES();
        es.onerror?.(new Event('error'));
      });

      // Error banner should appear
      expect(screen.getByText('Dismiss')).toBeInTheDocument();
    });

    it('should dismiss error banner when Dismiss is clicked', () => {
      render(<ChatSearch />);

      const input = screen.getByTestId('chat-input');
      fireEvent.change(input, { target: { value: 'Test' } });
      fireEvent.click(screen.getByTestId('chat-submit'));

      // Trigger error
      for (let i = 0; i < 4; i++) {
        act(() => {
          const es = getLatestES();
          es.onerror?.(new Event('error'));
          vi.advanceTimersByTime(10000);
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
      render(<ChatSearch />);

      const input = screen.getByTestId('chat-input');
      fireEvent.change(input, { target: { value: 'Enter test' } });
      fireEvent.keyDown(input, { key: 'Enter' });

      expect(MockEventSource).toHaveBeenCalledTimes(1);
      expect(screen.getByText('Enter test')).toBeInTheDocument();
    });

    it('should not submit on Shift+Enter', () => {
      render(<ChatSearch />);

      const input = screen.getByTestId('chat-input');
      fireEvent.change(input, { target: { value: 'No submit' } });
      fireEvent.keyDown(input, { key: 'Enter', shiftKey: true });

      expect(MockEventSource).not.toHaveBeenCalled();
    });
  });
});
