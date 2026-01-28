package com.knowledge.backend.api.dto.user;

import java.time.LocalDateTime;
import java.util.UUID;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.knowledge.backend.domain.entity.UserActivity;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * User Activity Response DTO
 *
 * <p>Response format for user activity feed entries.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class UserActivityResponse {

    private UUID id;
    private String action;
    private String resourceType;
    private UUID resourceId;
    private String description;
    private LocalDateTime createdAt;

    /**
     * Convert UserActivity entity (audit_log projection) to UserActivityResponse DTO
     *
     * @param activity the UserActivity entity
     * @return UserActivityResponse DTO
     */
    public static UserActivityResponse from(UserActivity activity) {
        return UserActivityResponse.builder()
                .id(activity.getId())
                .action(activity.getAction())
                .resourceType(activity.getResourceType())
                .resourceId(activity.getResourceId())
                .description(activity.getAction() + " on " + activity.getResourceType())
                .createdAt(activity.getCreatedAt())
                .build();
    }
}
