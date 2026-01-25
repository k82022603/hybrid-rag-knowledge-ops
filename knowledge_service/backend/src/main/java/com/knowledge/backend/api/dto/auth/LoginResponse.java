package com.knowledge.backend.api.dto.auth;

import java.util.Set;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Login Response DTO
 *
 * <p>Contains user info and JWT tokens after successful authentication
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class LoginResponse {

    private UserInfo user;
    private String accessToken;
    private String refreshToken;
    private Long expiresIn;

    /**
     * User Information nested class
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class UserInfo {
        private String id;
        private String email;
        private String username;
        private Set<String> roles;
    }
}
