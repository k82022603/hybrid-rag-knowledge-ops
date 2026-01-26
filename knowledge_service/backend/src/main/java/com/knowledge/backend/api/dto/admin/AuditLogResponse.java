package com.knowledge.backend.api.dto.admin;

import java.time.LocalDateTime;
import java.util.UUID;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.knowledge.backend.domain.entity.AuditLog;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Audit Log Response DTO
 *
 * <p>Response format for audit log entries.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class AuditLogResponse {

    private UUID id;
    private UUID userId;
    private String action;
    private String resourceType;
    private UUID resourceId;
    private String ipAddress;
    private String requestPath;
    private String status;
    private String errorMessage;
    private Integer durationMs;
    private LocalDateTime createdAt;

    /**
     * Convert AuditLog entity to AuditLogResponse DTO
     *
     * @param log the AuditLog entity
     * @return AuditLogResponse DTO
     */
    public static AuditLogResponse from(AuditLog log) {
        return AuditLogResponse.builder()
                .id(log.getId())
                .userId(log.getUserId())
                .action(log.getAction())
                .resourceType(log.getResourceType())
                .resourceId(log.getResourceId())
                .ipAddress(log.getIpAddress())
                .requestPath(log.getRequestPath())
                .status(log.getStatus())
                .errorMessage(log.getErrorMessage())
                .durationMs(log.getDurationMs())
                .createdAt(log.getCreatedAt())
                .build();
    }
}
