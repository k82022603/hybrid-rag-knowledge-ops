package com.knowledge.backend.api.dto.auth;

import java.util.Set;

import com.fasterxml.jackson.annotation.JsonProperty;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Login Response DTO
 *
 * <p>Contains user info and JWT tokens after successful authentication.
 * Uses @JsonProperty to ensure camelCase serialization for Frontend compatibility.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class LoginResponse {

    @JsonProperty("user")
    private UserInfo user;

    @JsonProperty("accessToken")
    private String accessToken;

    @JsonProperty("refreshToken")
    private String refreshToken;

    @JsonProperty("expiresIn")
    private Long expiresIn;

    /**
     * User Information nested class
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class UserInfo {
        @JsonProperty("id")
        private String id;

        @JsonProperty("email")
        private String email;

        @JsonProperty("username")
        private String username;

        @JsonProperty("roles")
        private Set<String> roles;
    }
}
