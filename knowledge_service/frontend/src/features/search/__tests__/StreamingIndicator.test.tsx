/**
 * StreamingIndicator component tests
 *
 * Tests the streaming indicator UI component for:
 * - Visibility based on isStreaming prop
 * - Status messages for connecting, streaming, and reconnecting states
 * - Accessibility attributes (role, aria-live, aria-label)
 * - Animated dots rendering
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import StreamingIndicator from '../components/StreamingIndicator';

describe('StreamingIndicator', () => {
  // ===== Visibility =====

  describe('visibility', () => {
    it('should render when isStreaming is true', () => {
      render(<StreamingIndicator isStreaming={true} />);

      expect(screen.getByTestId('streaming-indicator')).toBeInTheDocument();
    });

    it('should not render when isStreaming is false', () => {
      render(<StreamingIndicator isStreaming={false} />);

      expect(screen.queryByTestId('streaming-indicator')).not.toBeInTheDocument();
    });
  });

  // ===== Status Messages =====

  describe('status messages', () => {
    it('should show "Generating response..." during active streaming', () => {
      render(<StreamingIndicator isStreaming={true} />);

      expect(screen.getByText('Generating response...')).toBeInTheDocument();
    });

    it('should show "Connecting..." when isConnecting is true', () => {
      render(<StreamingIndicator isStreaming={true} isConnecting={true} />);

      expect(screen.getByText('Connecting...')).toBeInTheDocument();
    });

    it('should show reconnect info when reconnecting', () => {
      render(
        <StreamingIndicator
          isStreaming={true}
          reconnectInfo={{ attempt: 2, maxRetries: 3 }}
        />
      );

      expect(
        screen.getByText('Reconnecting... (attempt 2/3)')
      ).toBeInTheDocument();
    });

    it('should prioritize reconnect info over connecting state', () => {
      render(
        <StreamingIndicator
          isStreaming={true}
          isConnecting={true}
          reconnectInfo={{ attempt: 1, maxRetries: 3 }}
        />
      );

      expect(
        screen.getByText('Reconnecting... (attempt 1/3)')
      ).toBeInTheDocument();
      expect(screen.queryByText('Connecting...')).not.toBeInTheDocument();
    });
  });

  // ===== Accessibility =====

  describe('accessibility', () => {
    it('should have role="status"', () => {
      render(<StreamingIndicator isStreaming={true} />);

      const indicator = screen.getByTestId('streaming-indicator');
      expect(indicator).toHaveAttribute('role', 'status');
    });

    it('should have aria-live="polite"', () => {
      render(<StreamingIndicator isStreaming={true} />);

      const indicator = screen.getByTestId('streaming-indicator');
      expect(indicator).toHaveAttribute('aria-live', 'polite');
    });

    it('should have descriptive aria-label', () => {
      render(<StreamingIndicator isStreaming={true} />);

      const indicator = screen.getByTestId('streaming-indicator');
      expect(indicator).toHaveAttribute('aria-label', 'Generating response...');
    });

    it('should update aria-label for reconnecting state', () => {
      render(
        <StreamingIndicator
          isStreaming={true}
          reconnectInfo={{ attempt: 1, maxRetries: 3 }}
        />
      );

      const indicator = screen.getByTestId('streaming-indicator');
      expect(indicator).toHaveAttribute(
        'aria-label',
        'Reconnecting... (attempt 1/3)'
      );
    });

    it('should mark animated dots as aria-hidden', () => {
      const { container } = render(
        <StreamingIndicator isStreaming={true} />
      );

      const dotsContainer = container.querySelector('[aria-hidden="true"]');
      expect(dotsContainer).toBeInTheDocument();
    });
  });

  // ===== Animated Dots =====

  describe('animated dots', () => {
    it('should render three animated dots', () => {
      const { container } = render(
        <StreamingIndicator isStreaming={true} />
      );

      const dots = container.querySelectorAll('.animate-bounce');
      expect(dots).toHaveLength(3);
    });

    it('should render dots with staggered animation delays', () => {
      const { container } = render(
        <StreamingIndicator isStreaming={true} />
      );

      const dots = container.querySelectorAll('.animate-bounce');
      expect(dots[0]).toHaveStyle({ animationDelay: '0ms' });
      expect(dots[1]).toHaveStyle({ animationDelay: '150ms' });
      expect(dots[2]).toHaveStyle({ animationDelay: '300ms' });
    });
  });

  // ===== Custom className =====

  describe('custom className', () => {
    it('should apply custom className to container', () => {
      render(
        <StreamingIndicator isStreaming={true} className="my-custom-class" />
      );

      const indicator = screen.getByTestId('streaming-indicator');
      expect(indicator).toHaveClass('my-custom-class');
    });
  });
});
