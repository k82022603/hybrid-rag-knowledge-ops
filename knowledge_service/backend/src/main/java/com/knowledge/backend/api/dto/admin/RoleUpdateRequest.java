package com.knowledge.backend.api.dto.admin;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Role Update Request DTO
 *
 * <p>Request format for updating a user's role.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RoleUpdateRequest {

    @NotBlank(message = "Role is required")
    @Pattern(regexp = "^(admin|user|viewer)$", message = "Role must be one of: admin, user, viewer")
    private String role;
}
