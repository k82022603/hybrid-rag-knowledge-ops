/**
 * StreamingIndicator - Visual feedback during AI response streaming
 *
 * Displays animated dots with status text to indicate that the AI
 * is currently generating a response. Supports different states:
 * - Connecting: "Connecting..."
 * - Streaming: "Generating response..."
 * - Reconnecting: "Reconnecting... (attempt X/Y)"
 *
 * Accessible via aria-live="polite" for screen readers.
 * Uses Tailwind CSS for animations and styling.
 */
import React from 'react';
import type { ReconnectInfo } from '../hooks/useStreamingSearch';

export interface StreamingIndicatorProps {
  /** Whether the stream is currently active */
  isStreaming: boolean;
  /** Whether the connection is being established */
  isConnecting?: boolean;
  /** Reconnection attempt info (shown during retry) */
  reconnectInfo?: ReconnectInfo | null;
  /** Optional CSS class to apply to the container */
  className?: string;
}

/**
 * Returns the appropriate status message based on connection state.
 */
function getStatusMessage(
  isConnecting: boolean,
  reconnectInfo?: ReconnectInfo | null
): string {
  if (reconnectInfo) {
    return `Reconnecting... (attempt ${reconnectInfo.attempt}/${reconnectInfo.maxRetries})`;
  }
  if (isConnecting) {
    return 'Connecting...';
  }
  return 'Generating response...';
}

/**
 * StreamingIndicator component for chat search.
 *
 * Renders animated dots and a status message during SSE streaming.
 */
const StreamingIndicator: React.FC<StreamingIndicatorProps> = ({
  isStreaming,
  isConnecting = false,
  reconnectInfo = null,
  className = '',
}) => {
  if (!isStreaming) return null;

  const statusMessage = getStatusMessage(isConnecting, reconnectInfo);
  const isReconnecting = reconnectInfo !== null;

  return (
    <div
      className={`flex items-center gap-2 px-4 py-2 ${className}`}
      role="status"
      aria-live="polite"
      aria-label={statusMessage}
      data-testid="streaming-indicator"
    >
      {/* Animated dots */}
      <div className="flex items-center gap-1" aria-hidden="true">
        <span
          className={`w-1.5 h-1.5 rounded-full ${
            isReconnecting
              ? 'bg-warning-400 dark:bg-warning-500'
              : 'bg-primary-400 dark:bg-primary-500'
          } animate-bounce`}
          style={{ animationDelay: '0ms', animationDuration: '1s' }}
        />
        <span
          className={`w-1.5 h-1.5 rounded-full ${
            isReconnecting
              ? 'bg-warning-400 dark:bg-warning-500'
              : 'bg-primary-400 dark:bg-primary-500'
          } animate-bounce`}
          style={{ animationDelay: '150ms', animationDuration: '1s' }}
        />
        <span
          className={`w-1.5 h-1.5 rounded-full ${
            isReconnecting
              ? 'bg-warning-400 dark:bg-warning-500'
              : 'bg-primary-400 dark:bg-primary-500'
          } animate-bounce`}
          style={{ animationDelay: '300ms', animationDuration: '1s' }}
        />
      </div>

      {/* Status text */}
      <span
        className={`text-xs ${
          isReconnecting
            ? 'text-warning-600 dark:text-warning-400'
            : 'text-gray-500 dark:text-gray-400'
        }`}
      >
        {statusMessage}
      </span>
    </div>
  );
};

export default StreamingIndicator;
