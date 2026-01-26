package com.knowledge.backend.api.dto.admin;

import java.util.Map;

import jakarta.validation.constraints.NotEmpty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * System Config Update Request DTO
 *
 * <p>Request format for updating system configuration.
 * Accepts key-value pairs to update.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SystemConfigUpdateRequest {

    @NotEmpty(message = "At least one configuration entry is required")
    private Map<String, String> configs;
}
