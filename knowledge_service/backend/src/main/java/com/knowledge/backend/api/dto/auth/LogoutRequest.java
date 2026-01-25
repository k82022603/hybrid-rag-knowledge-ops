package com.knowledge.backend.api.dto.auth;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Logout Request DTO
 *
 * <p>Contains refresh token to invalidate on logout
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class LogoutRequest {

    private String refreshToken;
}
