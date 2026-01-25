package com.knowledge.backend.api.controller;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;

import java.time.LocalDateTime;
import java.util.Set;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.reactive.WebFluxTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.web.reactive.server.WebTestClient;

import com.knowledge.backend.api.dto.auth.LoginRequest;
import com.knowledge.backend.api.dto.auth.LoginResponse;
import com.knowledge.backend.api.dto.auth.RefreshRequest;
import com.knowledge.backend.api.dto.auth.TokenResponse;
import com.knowledge.backend.api.dto.auth.UserResponse;
import com.knowledge.backend.exception.AuthenticationException;
import com.knowledge.backend.exception.GlobalExceptionHandler;
import com.knowledge.backend.exception.TooManyRequestsException;
import com.knowledge.backend.service.AuthService;

import reactor.core.publisher.Mono;

/**
 * Unit tests for AuthController
 *
 * <p>Tests REST endpoints for authentication
 */
@WebFluxTest(AuthController.class)
@Import(GlobalExceptionHandler.class)
class AuthControllerTest {

    @Autowired
    private WebTestClient webTestClient;

    @MockBean
    private AuthService authService;

    private LoginResponse mockLoginResponse;
    private TokenResponse mockTokenResponse;
    private UserResponse mockUserResponse;

    @BeforeEach
    void setUp() {
        mockLoginResponse = LoginResponse.builder()
                .user(LoginResponse.UserInfo.builder()
                        .id("1")
                        .email("test@example.com")
                        .username("testuser")
                        .roles(Set.of("USER"))
                        .build())
                .accessToken("access-token")
                .refreshToken("refresh-token")
                .expiresIn(3600L)
                .build();

        mockTokenResponse = TokenResponse.builder()
                .accessToken("new-access-token")
                .refreshToken("new-refresh-token")
                .expiresIn(3600L)
                .build();

        mockUserResponse = UserResponse.builder()
                .id("1")
                .email("test@example.com")
                .username("testuser")
                .firstName("Test")
                .lastName("User")
                .roles(Set.of("USER"))
                .createdAt(LocalDateTime.now())
                .lastLoginAt(LocalDateTime.now())
                .build();
    }

    @Nested
    @DisplayName("POST /api/auth/login Tests")
    class LoginTests {

        @Test
        @DisplayName("Should login successfully with valid credentials")
        void shouldLoginSuccessfully() {
            // Given
            LoginRequest request = LoginRequest.builder()
                    .email("test@example.com")
                    .password("password123")
                    .build();

            when(authService.login(anyString(), anyString()))
                    .thenReturn(Mono.just(mockLoginResponse));

            // When & Then
            webTestClient.post()
                    .uri("/api/auth/login")
                    .contentType(MediaType.APPLICATION_JSON)
                    .bodyValue(request)
                    .exchange()
                    .expectStatus().isOk()
                    .expectBody()
                    .jsonPath("$.accessToken").isEqualTo("access-token")
                    .jsonPath("$.refreshToken").isEqualTo("refresh-token")
                    .jsonPath("$.expiresIn").isEqualTo(3600)
                    .jsonPath("$.user.email").isEqualTo("test@example.com")
                    .jsonPath("$.user.username").isEqualTo("testuser");
        }

        @Test
        @DisplayName("Should return 401 for invalid credentials")
        void shouldReturn401ForInvalidCredentials() {
            // Given
            LoginRequest request = LoginRequest.builder()
                    .email("test@example.com")
                    .password("wrongpassword")
                    .build();

            when(authService.login(anyString(), anyString()))
                    .thenReturn(Mono.error(new AuthenticationException("Invalid email or password")));

            // When & Then
            webTestClient.post()
                    .uri("/api/auth/login")
                    .contentType(MediaType.APPLICATION_JSON)
                    .bodyValue(request)
                    .exchange()
                    .expectStatus().isUnauthorized()
                    .expectBody()
                    .jsonPath("$.status").isEqualTo(401)
                    .jsonPath("$.message").isEqualTo("Invalid email or password");
        }

        @Test
        @DisplayName("Should return 429 when rate limit exceeded")
        void shouldReturn429WhenRateLimitExceeded() {
            // Given
            LoginRequest request = LoginRequest.builder()
                    .email("test@example.com")
                    .password("password123")
                    .build();

            when(authService.login(anyString(), anyString()))
                    .thenReturn(Mono.error(new TooManyRequestsException("Too many attempts", 900)));

            // When & Then
            webTestClient.post()
                    .uri("/api/auth/login")
                    .contentType(MediaType.APPLICATION_JSON)
                    .bodyValue(request)
                    .exchange()
                    .expectStatus().isEqualTo(429)
                    .expectHeader().valueEquals("Retry-After", "900")
                    .expectBody()
                    .jsonPath("$.status").isEqualTo(429);
        }

        @Test
        @DisplayName("Should return 400 for invalid email format")
        void shouldReturn400ForInvalidEmailFormat() {
            // Given
            LoginRequest request = LoginRequest.builder()
                    .email("invalid-email")
                    .password("password123")
                    .build();

            // When & Then
            webTestClient.post()
                    .uri("/api/auth/login")
                    .contentType(MediaType.APPLICATION_JSON)
                    .bodyValue(request)
                    .exchange()
                    .expectStatus().isBadRequest()
                    .expectBody()
                    .jsonPath("$.status").isEqualTo(400)
                    .jsonPath("$.validationErrors.email").exists();
        }

        @Test
        @DisplayName("Should return 400 for missing password")
        void shouldReturn400ForMissingPassword() {
            // Given
            LoginRequest request = LoginRequest.builder()
                    .email("test@example.com")
                    .password("")
                    .build();

            // When & Then
            webTestClient.post()
                    .uri("/api/auth/login")
                    .contentType(MediaType.APPLICATION_JSON)
                    .bodyValue(request)
                    .exchange()
                    .expectStatus().isBadRequest()
                    .expectBody()
                    .jsonPath("$.status").isEqualTo(400)
                    .jsonPath("$.validationErrors.password").exists();
        }

        @Test
        @DisplayName("Should return 400 for short password")
        void shouldReturn400ForShortPassword() {
            // Given
            LoginRequest request = LoginRequest.builder()
                    .email("test@example.com")
                    .password("12345")
                    .build();

            // When & Then
            webTestClient.post()
                    .uri("/api/auth/login")
                    .contentType(MediaType.APPLICATION_JSON)
                    .bodyValue(request)
                    .exchange()
                    .expectStatus().isBadRequest()
                    .expectBody()
                    .jsonPath("$.status").isEqualTo(400)
                    .jsonPath("$.validationErrors.password").exists();
        }
    }

    @Nested
    @DisplayName("POST /api/auth/refresh Tests")
    class RefreshTests {

        @Test
        @DisplayName("Should refresh token successfully")
        void shouldRefreshTokenSuccessfully() {
            // Given
            RefreshRequest request = RefreshRequest.builder()
                    .refreshToken("valid-refresh-token")
                    .build();

            when(authService.refreshToken(anyString()))
                    .thenReturn(Mono.just(mockTokenResponse));

            // When & Then
            webTestClient.post()
                    .uri("/api/auth/refresh")
                    .contentType(MediaType.APPLICATION_JSON)
                    .bodyValue(request)
                    .exchange()
                    .expectStatus().isOk()
                    .expectBody()
                    .jsonPath("$.accessToken").isEqualTo("new-access-token")
                    .jsonPath("$.refreshToken").isEqualTo("new-refresh-token")
                    .jsonPath("$.expiresIn").isEqualTo(3600);
        }

        @Test
        @DisplayName("Should return 401 for invalid refresh token")
        void shouldReturn401ForInvalidRefreshToken() {
            // Given
            RefreshRequest request = RefreshRequest.builder()
                    .refreshToken("invalid-refresh-token")
                    .build();

            when(authService.refreshToken(anyString()))
                    .thenReturn(Mono.error(new AuthenticationException("Invalid refresh token")));

            // When & Then
            webTestClient.post()
                    .uri("/api/auth/refresh")
                    .contentType(MediaType.APPLICATION_JSON)
                    .bodyValue(request)
                    .exchange()
                    .expectStatus().isUnauthorized()
                    .expectBody()
                    .jsonPath("$.status").isEqualTo(401);
        }

        @Test
        @DisplayName("Should return 400 for missing refresh token")
        void shouldReturn400ForMissingRefreshToken() {
            // Given
            RefreshRequest request = RefreshRequest.builder()
                    .refreshToken("")
                    .build();

            // When & Then
            webTestClient.post()
                    .uri("/api/auth/refresh")
                    .contentType(MediaType.APPLICATION_JSON)
                    .bodyValue(request)
                    .exchange()
                    .expectStatus().isBadRequest()
                    .expectBody()
                    .jsonPath("$.status").isEqualTo(400);
        }
    }

    @Nested
    @DisplayName("POST /api/auth/logout Tests")
    class LogoutTests {

        @Test
        @WithMockUser
        @DisplayName("Should logout successfully")
        void shouldLogoutSuccessfully() {
            // Given
            when(authService.logout(anyLong(), any()))
                    .thenReturn(Mono.empty());

            // When & Then
            webTestClient.post()
                    .uri("/api/auth/logout")
                    .contentType(MediaType.APPLICATION_JSON)
                    .exchange()
                    .expectStatus().isOk();
        }
    }

    @Nested
    @DisplayName("GET /api/auth/me Tests")
    class GetCurrentUserTests {

        @Test
        @WithMockUser
        @DisplayName("Should get current user successfully")
        void shouldGetCurrentUserSuccessfully() {
            // Given
            when(authService.getCurrentUser(anyLong()))
                    .thenReturn(Mono.just(mockUserResponse));

            // When & Then
            webTestClient.get()
                    .uri("/api/auth/me")
                    .exchange()
                    .expectStatus().isOk()
                    .expectBody()
                    .jsonPath("$.email").isEqualTo("test@example.com")
                    .jsonPath("$.username").isEqualTo("testuser")
                    .jsonPath("$.firstName").isEqualTo("Test")
                    .jsonPath("$.lastName").isEqualTo("User");
        }

        @Test
        @DisplayName("Should return 401 when not authenticated")
        void shouldReturn401WhenNotAuthenticated() {
            // When & Then
            webTestClient.get()
                    .uri("/api/auth/me")
                    .exchange()
                    .expectStatus().isUnauthorized();
        }
    }
}
