package com.knowledge.gateway.dto;

import java.time.Instant;

/**
 * Unified error response DTO for all Gateway errors.
 *
 * <p>Provides a consistent error format across Gateway exception handlers,
 * fallback controllers, and authentication filters.
 *
 * @param timestamp ISO-8601 timestamp of the error
 * @param status    HTTP status code
 * @param error     Short error category (e.g., "Authentication failed")
 * @param message   Human-readable error description
 * @param path      Request path that caused the error
 * @param traceId   Distributed tracing ID for correlation (nullable)
 */
public record ErrorResponse(
    String timestamp,
    int status,
    String error,
    String message,
    String path,
    String traceId
) {

    /**
     * Creates an ErrorResponse with the current timestamp.
     */
    public static ErrorResponse of(int status, String error, String message, String path, String traceId) {
        return new ErrorResponse(
            Instant.now().toString(),
            status,
            error,
            message,
            path,
            traceId
        );
    }
}
