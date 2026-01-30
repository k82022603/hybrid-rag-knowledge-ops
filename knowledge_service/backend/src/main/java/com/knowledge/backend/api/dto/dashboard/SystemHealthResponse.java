package com.knowledge.backend.api.dto.dashboard;

import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;

/**
 * System Health Response DTO
 *
 * <p>Overall system health status including individual service health.
 * Used by GET /api/v1/dashboard/health endpoint.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class SystemHealthResponse {

    /**
     * Overall system health status
     */
    private String overall;

    /**
     * Timestamp of health check
     */
    private LocalDateTime timestamp;

    /**
     * Individual service health statuses
     */
    private List<ServiceHealth> services;

    /**
     * Individual service health status
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ServiceHealth {
        private String name;
        private String status;
        private Long responseTime;
        private LocalDateTime lastChecked;
    }
}
