package com.knowledge.gateway.dto;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.time.Instant;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;

/**
 * Unit tests for ErrorResponse record
 *
 * <p>Tests the static factory method and field validation for the unified
 * error response DTO used across Gateway exception handlers.
 */
class ErrorResponseTest {

    @Test
    @DisplayName("U01: ErrorResponse.of()가 모든 필드를 올바르게 설정한다")
    void of_CreatesCorrectRecord_WithAllFields() {
        int status = 404;
        String error = "Not Found";
        String message = "Resource not found";
        String path = "/api/v1/knowledge/123";
        String traceId = "abc-123-xyz";

        ErrorResponse response = ErrorResponse.of(status, error, message, path, traceId);

        assertThat(response.status()).isEqualTo(status);
        assertThat(response.error()).isEqualTo(error);
        assertThat(response.message()).isEqualTo(message);
        assertThat(response.path()).isEqualTo(path);
        assertThat(response.traceId()).isEqualTo(traceId);
        assertThat(response.timestamp()).isNotNull();
    }

    @Test
    @DisplayName("U02: timestamp는 유효한 ISO 8601 형식이어야 한다")
    void of_Timestamp_IsValidIso8601Format() {
        ErrorResponse response = ErrorResponse.of(
            500, "Internal Server Error", "Unexpected error", "/api/v1/search", "trace-001"
        );

        String timestamp = response.timestamp();
        assertThat(timestamp).isNotNull().isNotBlank();

        // ISO 8601 파싱 성공 여부 확인 (Instant.parse는 ISO 8601 형식만 허용)
        assertThatCode(() -> Instant.parse(timestamp))
            .as("timestamp must be valid ISO 8601 format: %s", timestamp)
            .doesNotThrowAnyException();
    }

    @Test
    @DisplayName("U03: traceId는 null이거나 비어있으면 안 된다 (null traceId 전달 시 필드에 저장됨)")
    void of_TraceId_IsNotNullWhenProvided() {
        String expectedTraceId = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01";

        ErrorResponse response = ErrorResponse.of(
            401, "Authentication failed", "Invalid token", "/api/v1/auth/login", expectedTraceId
        );

        assertThat(response.traceId())
            .as("traceId must not be null or empty when provided")
            .isNotNull()
            .isNotEmpty()
            .isEqualTo(expectedTraceId);
    }
}
