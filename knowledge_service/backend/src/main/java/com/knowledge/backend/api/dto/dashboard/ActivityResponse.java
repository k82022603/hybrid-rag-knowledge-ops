package com.knowledge.backend.api.dto.dashboard;

import java.time.LocalDateTime;
import java.util.UUID;

import com.fasterxml.jackson.annotation.JsonInclude;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Activity Response DTO
 *
 * <p>Represents a recent activity entry for the dashboard.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class ActivityResponse {

    private UUID id;
    private String activityType;
    private String description;
    private UUID userId;
    private UUID resourceId;
    private String resourceType;
    private LocalDateTime createdAt;
}
