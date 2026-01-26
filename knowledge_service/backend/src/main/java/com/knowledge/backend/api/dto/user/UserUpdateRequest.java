package com.knowledge.backend.api.dto.user;

import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * User Update Request DTO
 *
 * <p>Request format for updating user profile.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UserUpdateRequest {

    @Size(max = 200, message = "Display name must be at most 200 characters")
    private String displayName;

    @Size(max = 100, message = "Department must be at most 100 characters")
    private String department;

    @Size(max = 100, message = "Position must be at most 100 characters")
    private String position;
}
