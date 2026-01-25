package com.knowledge.backend.api.dto;

import java.time.LocalDateTime;
import java.util.Map;

import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Standard Error Response DTO
 *
 * <p>Unified error response format for all API errors
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class ErrorResponse {

    private int status;
    private String error;
    private String message;
    private String path;
    private LocalDateTime timestamp;
    private Map<String, String> validationErrors;

    /**
     * Create error response with basic info
     *
     * @param status HTTP status code
     * @param message error message
     * @return ErrorResponse instance
     */
    public static ErrorResponse of(int status, String message) {
        return ErrorResponse.builder()
                .status(status)
                .message(message)
                .timestamp(LocalDateTime.now())
                .build();
    }

    /**
     * Create error response with path
     *
     * @param status HTTP status code
     * @param message error message
     * @param path request path
     * @return ErrorResponse instance
     */
    public static ErrorResponse of(int status, String message, String path) {
        return ErrorResponse.builder()
                .status(status)
                .message(message)
                .path(path)
                .timestamp(LocalDateTime.now())
                .build();
    }

    /**
     * Create error response with validation errors
     *
     * @param status HTTP status code
     * @param message error message
     * @param validationErrors field validation errors
     * @return ErrorResponse instance
     */
    public static ErrorResponse ofValidation(int status, String message, Map<String, String> validationErrors) {
        return ErrorResponse.builder()
                .status(status)
                .message(message)
                .validationErrors(validationErrors)
                .timestamp(LocalDateTime.now())
                .build();
    }
}
