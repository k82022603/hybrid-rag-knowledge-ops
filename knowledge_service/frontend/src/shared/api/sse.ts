/**
 * SSEClient - Server-Sent Events client with retry and reconnect logic
 *
 * Provides a robust SSE connection with:
 * - Exponential backoff retry (up to configurable max retries)
 * - Abort/cancel support via AbortController
 * - Typed event data parsing (JSON or raw string)
 * - [DONE] sentinel detection for stream completion
 * - Connection state tracking
 *
 * @example
 * ```ts
 * const client = new SSEClient('/api/v1/search/stream?query=hello', {
 *   onToken: (token) => appendToMessage(token),
 *   onSources: (sources) => setSources(sources),
 *   onComplete: () => setIsStreaming(false),
 *   onError: (error) => setError(error.message),
 * });
 * client.connect();
 * // Later: client.abort();
 * ```
 */

/** SSE event data types sent by the backend */
export interface SSETokenEvent {
  type: 'token';
  data: string;
}

export interface SSESourcesEvent {
  type: 'sources';
  data: SSESourceData[];
}

export interface SSESourceData {
  chunkId: string;
  documentId: string;
  content: string;
  score: number;
  metadata?: {
    documentType?: string;
    projectName?: string;
    category?: {
      level1: string;
      level2: string;
      level3: string;
    };
    summary?: string;
  };
  graphContext?: {
    relatedEntities: string[];
    community: string;
  };
}

export interface SSEErrorEvent {
  type: 'error';
  message: string;
}

/** Configuration options for SSEClient */
export interface SSEOptions {
  /** Called for each token/text chunk received */
  onToken: (token: string) => void;
  /** Called when source citations are received (after [DONE]) */
  onSources?: (sources: SSESourceData[]) => void;
  /** Called when the stream completes successfully */
  onComplete?: () => void;
  /** Called on connection or parsing errors */
  onError?: (error: SSEError) => void;
  /** Called when a reconnect attempt starts */
  onReconnect?: (attempt: number, maxRetries: number) => void;
  /** Maximum number of retry attempts (default: 3) */
  maxRetries?: number;
  /** Initial retry delay in ms (default: 1000). Doubles with each retry. */
  retryDelay?: number;
  /** Maximum retry delay in ms (default: 10000) */
  maxRetryDelay?: number;
}

/** Structured error for SSE failures */
export class SSEError extends Error {
  constructor(
    message: string,
    public readonly code: SSEErrorCode,
    public readonly retriable: boolean = false
  ) {
    super(message);
    this.name = 'SSEError';
  }
}

/** Error code classifications */
export type SSEErrorCode =
  | 'CONNECTION_FAILED'
  | 'CONNECTION_LOST'
  | 'PARSE_ERROR'
  | 'MAX_RETRIES_EXCEEDED'
  | 'ABORTED'
  | 'SERVER_ERROR';

/** Connection states for SSEClient */
export type SSEConnectionState =
  | 'idle'
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'closed'
  | 'error';

/**
 * SSEClient manages a Server-Sent Events connection with automatic
 * retry, abort support, and structured event parsing.
 */
export class SSEClient {
  private eventSource: EventSource | null = null;
  private retryCount = 0;
  private retryTimeoutId: ReturnType<typeof setTimeout> | null = null;
  private aborted = false;
  private _state: SSEConnectionState = 'idle';

  private readonly maxRetries: number;
  private readonly retryDelay: number;
  private readonly maxRetryDelay: number;

  constructor(
    private readonly url: string,
    private readonly options: SSEOptions
  ) {
    this.maxRetries = options.maxRetries ?? 3;
    this.retryDelay = options.retryDelay ?? 1000;
    this.maxRetryDelay = options.maxRetryDelay ?? 10000;
  }

  /** Current connection state */
  get state(): SSEConnectionState {
    return this._state;
  }

  /** Whether the connection is currently open */
  get isConnected(): boolean {
    return (
      this._state === 'connected' &&
      this.eventSource?.readyState === EventSource.OPEN
    );
  }

  /** Whether the client has been aborted */
  get isAborted(): boolean {
    return this.aborted;
  }

  /**
   * Open the SSE connection and begin receiving events.
   * Safe to call multiple times; previous connections are closed first.
   */
  connect(): void {
    if (this.aborted) return;

    // Clean up any existing connection
    this.closeEventSource();

    this._state = this.retryCount > 0 ? 'reconnecting' : 'connecting';

    try {
      this.eventSource = new EventSource(this.url);

      this.eventSource.onopen = () => {
        this._state = 'connected';
        this.retryCount = 0; // Reset retry count on successful connection
      };

      this.eventSource.onmessage = (event: MessageEvent) => {
        this.handleMessage(event);
      };

      this.eventSource.onerror = () => {
        this.handleError();
      };
    } catch (err) {
      this._state = 'error';
      this.options.onError?.(
        new SSEError(
          'Failed to create EventSource connection',
          'CONNECTION_FAILED',
          true
        )
      );
    }
  }

  /**
   * Abort the SSE connection permanently.
   * No further reconnect attempts will be made.
   */
  abort(): void {
    this.aborted = true;
    this.clearRetryTimeout();
    this.closeEventSource();
    this._state = 'closed';
  }

  /**
   * Close the SSE connection without aborting.
   * Can be reconnected by calling connect() again.
   */
  close(): void {
    this.clearRetryTimeout();
    this.closeEventSource();
    this._state = 'closed';
  }

  /** Parse and dispatch an incoming SSE message */
  private handleMessage(event: MessageEvent): void {
    if (this.aborted) return;

    const rawData = event.data as string;

    // Check for stream completion sentinel
    if (rawData === '[DONE]') {
      this.closeEventSource();
      this._state = 'closed';
      this.options.onComplete?.();
      return;
    }

    // Try parsing as structured JSON event
    try {
      const parsed = JSON.parse(rawData);

      if (parsed.type === 'token' && typeof parsed.data === 'string') {
        this.options.onToken(parsed.data);
        return;
      }

      if (parsed.type === 'sources' && Array.isArray(parsed.data)) {
        this.options.onSources?.(parsed.data);
        return;
      }

      if (parsed.type === 'error') {
        this.options.onError?.(
          new SSEError(
            parsed.message || 'Server error',
            'SERVER_ERROR',
            false
          )
        );
        return;
      }

      // Unknown structured event - treat as token text
      this.options.onToken(rawData);
    } catch {
      // Not JSON - treat as raw token text
      this.options.onToken(rawData);
    }
  }

  /** Handle EventSource errors with exponential backoff retry */
  private handleError(): void {
    this.closeEventSource();

    if (this.aborted) {
      this._state = 'closed';
      return;
    }

    if (this.retryCount >= this.maxRetries) {
      this._state = 'error';
      this.options.onError?.(
        new SSEError(
          `Connection failed after ${this.maxRetries} retry attempts`,
          'MAX_RETRIES_EXCEEDED',
          false
        )
      );
      return;
    }

    this.retryCount += 1;
    this._state = 'reconnecting';

    // Exponential backoff: delay * 2^(retryCount-1), capped at maxRetryDelay
    const delay = Math.min(
      this.retryDelay * Math.pow(2, this.retryCount - 1),
      this.maxRetryDelay
    );

    this.options.onReconnect?.(this.retryCount, this.maxRetries);

    this.retryTimeoutId = setTimeout(() => {
      if (!this.aborted) {
        this.connect();
      }
    }, delay);
  }

  /** Close the underlying EventSource */
  private closeEventSource(): void {
    if (this.eventSource) {
      this.eventSource.onopen = null;
      this.eventSource.onmessage = null;
      this.eventSource.onerror = null;
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  /** Clear any pending retry timeout */
  private clearRetryTimeout(): void {
    if (this.retryTimeoutId !== null) {
      clearTimeout(this.retryTimeoutId);
      this.retryTimeoutId = null;
    }
  }
}

export default SSEClient;
