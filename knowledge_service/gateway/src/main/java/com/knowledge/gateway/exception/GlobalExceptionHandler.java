package com.knowledge.gateway.exception;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.knowledge.gateway.dto.ErrorResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.web.reactive.error.ErrorWebExceptionHandler;
import org.springframework.core.annotation.Order;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.core.AuthenticationException;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.net.ConnectException;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.TimeoutException;

/**
 * Global Exception Handler for API Gateway
 *
 * <p>Handles authentication, authorization, routing, and upstream errors
 * with a unified {@link ErrorResponse} JSON format including traceId for correlation.
 */
@Component
@Order(-2)
@Slf4j
@RequiredArgsConstructor
public class GlobalExceptionHandler implements ErrorWebExceptionHandler {

    private final ObjectMapper objectMapper;

    @Override
    public Mono<Void> handle(ServerWebExchange exchange, Throwable ex) {
        HttpStatus status;
        String error;
        String message;

        if (ex instanceof AuthenticationException) {
            status = HttpStatus.UNAUTHORIZED;
            error = "Authentication failed";
            message = "Invalid or missing authentication credentials. Please provide a valid JWT token.";
            log.warn("Authentication failure for path {}: {}",
                exchange.getRequest().getPath(), ex.getMessage());
        } else if (ex instanceof AccessDeniedException) {
            status = HttpStatus.FORBIDDEN;
            error = "Access denied";
            message = "You do not have permission to access this resource.";
            log.warn("Access denied for path {}: {}",
                exchange.getRequest().getPath(), ex.getMessage());
        } else if (ex instanceof ResponseStatusException responseStatusEx) {
            status = HttpStatus.valueOf(responseStatusEx.getStatusCode().value());
            if (status == HttpStatus.NOT_FOUND) {
                error = "Not found";
                message = "The requested resource was not found.";
                log.info("Resource not found: {}", exchange.getRequest().getPath());
            } else if (status == HttpStatus.SERVICE_UNAVAILABLE) {
                error = "Service unavailable";
                message = "The requested service is temporarily unavailable.";
                log.warn("Service unavailable for path {}", exchange.getRequest().getPath());
            } else {
                error = status.getReasonPhrase();
                message = responseStatusEx.getReason() != null ?
                    responseStatusEx.getReason() : "An error occurred processing your request.";
            }
        } else if (ex instanceof TimeoutException) {
            status = HttpStatus.GATEWAY_TIMEOUT;
            error = "Gateway timeout";
            message = "The upstream service did not respond in time.";
            log.warn("Timeout for path {}: {}", exchange.getRequest().getPath(), ex.getMessage());
        } else if (ex instanceof ConnectException) {
            status = HttpStatus.BAD_GATEWAY;
            error = "Bad gateway";
            message = "Unable to connect to the upstream service.";
            log.warn("Connection failed for path {}: {}", exchange.getRequest().getPath(), ex.getMessage());
        } else {
            status = HttpStatus.INTERNAL_SERVER_ERROR;
            error = "Internal server error";
            message = "An unexpected error occurred. Please try again later.";
            log.error("Unexpected error for path {}: {}",
                exchange.getRequest().getPath(), ex.getMessage(), ex);
        }

        return writeErrorResponse(exchange, status, error, message);
    }

    /**
     * Write unified JSON error response using {@link ErrorResponse} DTO.
     *
     * <p>Extracts traceId from the exchange request ID for distributed tracing correlation.
     */
    private Mono<Void> writeErrorResponse(
            ServerWebExchange exchange,
            HttpStatus status,
            String error,
            String message) {

        exchange.getResponse().setStatusCode(status);
        exchange.getResponse().getHeaders().setContentType(MediaType.APPLICATION_JSON);

        String traceId = exchange.getRequest().getId();
        String path = exchange.getRequest().getPath().value();

        ErrorResponse errorResponse = ErrorResponse.of(
            status.value(), error, message, path, traceId
        );

        byte[] bytes;
        try {
            bytes = objectMapper.writeValueAsBytes(errorResponse);
        } catch (JsonProcessingException e) {
            log.error("Failed to serialize error response", e);
            bytes = "{\"error\":\"Internal server error\"}".getBytes(StandardCharsets.UTF_8);
        }

        DataBuffer buffer = exchange.getResponse()
            .bufferFactory()
            .wrap(bytes);

        return exchange.getResponse().writeWith(Mono.just(buffer));
    }
}
