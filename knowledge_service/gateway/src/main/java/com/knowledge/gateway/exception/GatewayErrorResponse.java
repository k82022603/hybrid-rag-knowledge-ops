package com.knowledge.gateway.exception;

/**
 * Standardized error response for Gateway API errors.
 *
 * <p>Used by {@link GlobalExceptionHandler} and {@link com.knowledge.gateway.filter.JwtAuthenticationFilter}
 * to produce consistent JSON error responses via Jackson ObjectMapper,
 * replacing manual {@code String.format} JSON assembly.
 */
public record GatewayErrorResponse(
    String error,
    String message,
    int status,
    String path,
    String timestamp
) {}
