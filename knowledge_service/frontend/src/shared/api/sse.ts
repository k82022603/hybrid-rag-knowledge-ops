/**
 * SSEPostClient - POST-based Server-Sent Events client using fetch + ReadableStream
 *
 * Replaces the previous EventSource-based SSEClient (STORY-043) to support:
 * - POST method for sending complex request bodies (conversation_history, topK, filters)
 * - Authorization header (JWT Bearer token) without URL exposure
 * - AbortController-based cancellation
 * - Exponential backoff retry (up to configurable max retries)
 * - Typed event data parsing (JSON or raw string)
 * - [DONE] sentinel detection for stream completion
 * - Connection state tracking
 *
 * Implements STORY-050 requirements:
 * - AC1: POST body with query, conversation_history, topK
 * - AC2: Backwards-compatible callback interface with useStreamingSearch
 * - AC3: Auto-reconnect with max 3 retries
 * - AC4: Token-unit streaming with [DONE] completion
 * - AC5: EventSource code fully removed
 *
 * @example
 * ```ts
 * const client = new SSEPostClient('/api/v1/search/chat/stream', {
 *   body: { query: 'hello', conversation_history: [], top_k: 5 },
 *   headers: { Authorization: 'Bearer xxx' },
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

/** Request body for POST-based SSE streaming */
export interface SSERequestBody {
  query: string;
  conversation_history?: Array<{
    role: 'user' | 'assistant';
    content: string;
  }>;
  top_k?: number;
  filters?: {
    documentType?: string;
    projectName?: string;
    dateFrom?: string;
    dateTo?: string;
  };
  [key: string]: unknown;
}

/** Configuration options for SSEPostClient */
export interface SSEPostClientOptions {
  /** Request body to send via POST */
  body: SSERequestBody;
  /** Additional headers (e.g., Authorization) */
  headers?: Record<string, string>;
  /** Called for each token/text chunk received */
  onToken: (token: string) => void;
  /** Called when source citations are received */
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
  | 'SERVER_ERROR'
  | 'HTTP_ERROR';

/** Connection states for SSEPostClient */
export type SSEConnectionState =
  | 'idle'
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'closed'
  | 'error';

/**
 * Parse a single SSE line from the stream buffer.
 *
 * SSE protocol lines follow the format:
 *   data: <payload>\n\n
 *   event: <event-name>\n
 *   id: <id>\n
 *
 * This function extracts complete SSE events from a text buffer,
 * returning the remaining (incomplete) buffer for the next chunk.
 *
 * @param buffer - accumulated text from the ReadableStream
 * @param onEvent - callback for each complete SSE event
 * @returns remaining buffer text (incomplete event)
 */
export function parseSSEBuffer(
  buffer: string,
  onEvent: (eventType: string, data: string) => void
): string {
  // SSE events are separated by double newlines
  const events = buffer.split('\n\n');

  // The last element may be an incomplete event
  const remaining = events.pop() ?? '';

  for (const event of events) {
    if (!event.trim()) continue;

    let eventType = 'message';
    const dataLines: string[] = [];

    const lines = event.split('\n');
    for (const line of lines) {
      if (line.startsWith('event:')) {
        eventType = line.slice(6).trim();
      } else if (line.startsWith('data:')) {
        dataLines.push(line.slice(5).trimStart());
      } else if (line.startsWith('id:')) {
        // Event ID - not used currently but parsed for completeness
      } else if (line.startsWith(':')) {
        // Comment line - ignore
      }
    }

    if (dataLines.length > 0) {
      const data = dataLines.join('\n');
      onEvent(eventType, data);
    }
  }

  return remaining;
}

/**
 * SSEPostClient manages a POST-based SSE connection using fetch + ReadableStream
 * with automatic retry, abort support, and structured event parsing.
 *
 * Unlike EventSource (GET-only), this client sends request data via POST body,
 * allowing complex payloads and secure Authorization headers.
 */
export class SSEPostClient {
  private abortController: AbortController | null = null;
  private retryCount = 0;
  private retryTimeoutId: ReturnType<typeof setTimeout> | null = null;
  private aborted = false;
  private _state: SSEConnectionState = 'idle';

  private readonly maxRetries: number;
  private readonly retryDelay: number;
  private readonly maxRetryDelay: number;

  constructor(
    private readonly url: string,
    private readonly options: SSEPostClientOptions
  ) {
    this.maxRetries = options.maxRetries ?? 3;
    this.retryDelay = options.retryDelay ?? 1000;
    this.maxRetryDelay = options.maxRetryDelay ?? 10000;
  }

  /** Current connection state */
  get state(): SSEConnectionState {
    return this._state;
  }

  /** Whether the connection is currently active */
  get isConnected(): boolean {
    return this._state === 'connected';
  }

  /** Whether the client has been aborted */
  get isAborted(): boolean {
    return this.aborted;
  }

  /**
   * Open the SSE connection via POST and begin receiving events.
   * Safe to call multiple times; previous connections are aborted first.
   */
  connect(): void {
    if (this.aborted) return;

    // Abort any existing connection
    this.abortExisting();

    this._state = this.retryCount > 0 ? 'reconnecting' : 'connecting';

    // Create a new AbortController for this connection
    this.abortController = new AbortController();

    this.startFetch();
  }

  /**
   * Start the fetch request and process the ReadableStream.
   */
  private async startFetch(): Promise<void> {
    try {
      const response = await fetch(this.url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
          'Cache-Control': 'no-cache',
          ...this.options.headers,
        },
        body: JSON.stringify(this.options.body),
        signal: this.abortController?.signal,
      });

      // Check for HTTP errors
      if (!response.ok) {
        const errorText = await response.text().catch(() => 'Unknown error');
        throw new SSEError(
          `HTTP ${response.status}: ${errorText}`,
          'HTTP_ERROR',
          response.status >= 500
        );
      }

      // Successfully connected
      this._state = 'connected';
      this.retryCount = 0;

      // Process the ReadableStream
      await this.processStream(response);
    } catch (err) {
      if (this.aborted) {
        this._state = 'closed';
        return;
      }

      // Handle AbortError (user cancelled)
      if (err instanceof DOMException && err.name === 'AbortError') {
        this._state = 'closed';
        return;
      }

      // Handle SSEError from HTTP status codes
      if (err instanceof SSEError) {
        if (err.retriable) {
          this.handleRetry();
        } else {
          this._state = 'error';
          this.options.onError?.(err);
        }
        return;
      }

      // Network or other errors - attempt retry
      this.handleRetry();
    }
  }

  /**
   * Process the ReadableStream from the fetch response.
   * Reads chunks, decodes UTF-8, and parses SSE events.
   */
  private async processStream(response: Response): Promise<void> {
    const reader = response.body?.getReader();
    if (!reader) {
      throw new SSEError(
        'Response body is not readable',
        'CONNECTION_FAILED',
        false
      );
    }

    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          // Stream ended naturally - process any remaining buffer
          if (buffer.trim()) {
            this.processRemainingBuffer(buffer);
          }
          this._state = 'closed';
          this.options.onComplete?.();
          return;
        }

        if (this.aborted) {
          reader.cancel();
          return;
        }

        // Decode the chunk and append to buffer
        buffer += decoder.decode(value, { stream: true });

        // Parse complete SSE events from the buffer
        buffer = parseSSEBuffer(buffer, (eventType, data) => {
          this.handleEvent(eventType, data);
        });
      }
    } catch (err) {
      if (this.aborted) {
        this._state = 'closed';
        return;
      }

      if (err instanceof DOMException && err.name === 'AbortError') {
        this._state = 'closed';
        return;
      }

      // Connection lost during streaming - attempt retry
      this.handleRetry();
    } finally {
      try {
        reader.releaseLock();
      } catch {
        // Reader may already be released
      }
    }
  }

  /**
   * Process any remaining text in the buffer when the stream ends.
   */
  private processRemainingBuffer(buffer: string): void {
    const lines = buffer.split('\n');
    const dataLines: string[] = [];

    for (const line of lines) {
      if (line.startsWith('data:')) {
        dataLines.push(line.slice(5).trimStart());
      }
    }

    if (dataLines.length > 0) {
      const data = dataLines.join('\n');
      this.handleEvent('message', data);
    }
  }

  /**
   * Handle a parsed SSE event.
   */
  private handleEvent(eventType: string, data: string): void {
    if (this.aborted) return;

    // Only handle 'message' type events (default SSE event type)
    if (eventType !== 'message') return;

    // Check for stream completion sentinel
    if (data === '[DONE]') {
      this.abortExisting();
      this._state = 'closed';
      this.options.onComplete?.();
      return;
    }

    // Try parsing as structured JSON event
    try {
      const parsed = JSON.parse(data);

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
      this.options.onToken(data);
    } catch {
      // Not JSON - treat as raw token text
      this.options.onToken(data);
    }
  }

  /**
   * Handle retry with exponential backoff.
   */
  private handleRetry(): void {
    this.abortExisting();

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

  /**
   * Abort the SSE connection permanently.
   * No further reconnect attempts will be made.
   */
  abort(): void {
    this.aborted = true;
    this.clearRetryTimeout();
    this.abortExisting();
    this._state = 'closed';
  }

  /**
   * Close the SSE connection without permanent abort.
   * Can be reconnected by calling connect() again.
   */
  close(): void {
    this.clearRetryTimeout();
    this.abortExisting();
    this._state = 'closed';
  }

  /** Abort the existing fetch request */
  private abortExisting(): void {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
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

/**
 * Helper function to get the current auth token.
 * Checks Keycloak first, then falls back to localStorage.
 *
 * @returns Bearer token string or undefined
 */
export function getAuthToken(): string | undefined {
  // Strategy 1: Try localStorage direct auth token
  const directToken = localStorage.getItem('auth_access_token');
  if (directToken) {
    return directToken;
  }
  return undefined;
}

// Backwards compatibility: export SSEPostClient as SSEClient
export { SSEPostClient as SSEClient };

// Also export the options type with backwards-compatible name
export type { SSEPostClientOptions as SSEOptions };

export default SSEPostClient;
