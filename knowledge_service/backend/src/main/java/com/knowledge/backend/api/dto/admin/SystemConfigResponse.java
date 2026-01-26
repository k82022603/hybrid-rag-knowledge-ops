package com.knowledge.backend.api.dto.admin;

import java.time.LocalDateTime;
import java.util.UUID;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.knowledge.backend.domain.entity.SystemConfig;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * System Config Response DTO
 *
 * <p>Response format for system configuration data.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class SystemConfigResponse {

    private String key;
    private String value;
    private String description;
    private UUID updatedBy;
    private LocalDateTime updatedAt;

    /**
     * Convert SystemConfig entity to SystemConfigResponse DTO
     *
     * @param config the SystemConfig entity
     * @return SystemConfigResponse DTO
     */
    public static SystemConfigResponse from(SystemConfig config) {
        return SystemConfigResponse.builder()
                .key(config.getKey())
                .value(config.getValue())
                .description(config.getDescription())
                .updatedBy(config.getUpdatedBy())
                .updatedAt(config.getUpdatedAt())
                .build();
    }
}
