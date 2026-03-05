package com.knowledge.gateway.exception;

/**
 * @deprecated Use {@link com.knowledge.gateway.dto.ErrorResponse} instead.
 *             This class is retained for backward compatibility only.
 *             STORY-127: Unified ErrorResponse DTO replaces this.
 */
@Deprecated(since = "STORY-127", forRemoval = true)
public record GatewayErrorResponse(
    String error,
    String message,
    int status,
    String path,
    String timestamp
) {}
