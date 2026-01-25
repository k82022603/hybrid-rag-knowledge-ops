package com.knowledge.backend.service;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.time.Duration;
import java.time.LocalDateTime;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.core.ReactiveRedisTemplate;
import org.springframework.data.redis.core.ReactiveValueOperations;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.test.util.ReflectionTestUtils;

import com.knowledge.backend.api.dto.auth.LoginResponse;
import com.knowledge.backend.api.dto.auth.TokenResponse;
import com.knowledge.backend.api.dto.auth.UserResponse;
import com.knowledge.backend.domain.entity.User;
import com.knowledge.backend.domain.repository.UserRepository;
import com.knowledge.backend.exception.AuthenticationException;
import com.knowledge.backend.exception.TooManyRequestsException;
import com.knowledge.backend.exception.UserNotFoundException;
import com.knowledge.backend.security.JwtTokenProvider;

import reactor.core.publisher.Mono;
import reactor.test.StepVerifier;

/**
 * Unit tests for AuthService
 *
 * <p>Tests authentication, token refresh, logout, and user info retrieval
 */
@ExtendWith(MockitoExtension.class)
class AuthServiceTest {

    @Mock
    private UserRepository userRepository;

    @Mock
    private JwtTokenProvider jwtTokenProvider;

    @Mock
    private ReactiveRedisTemplate<String, String> redisTemplate;

    @Mock
    private ReactiveValueOperations<String, String> valueOperations;

    @InjectMocks
    private AuthService authService;

    private User testUser;
    private BCryptPasswordEncoder passwordEncoder = new BCryptPasswordEncoder();

    @BeforeEach
    void setUp() {
        // Set configuration values
        ReflectionTestUtils.setField(authService, "maxLoginAttempts", 5);
        ReflectionTestUtils.setField(authService, "lockoutDurationMinutes", 15);

        // Create test user
        testUser = User.builder()
                .id(1L)
                .email("test@example.com")
                .username("testuser")
                .passwordHash(passwordEncoder.encode("password123"))
                .firstName("Test")
                .lastName("User")
                .roles("USER")
                .isActive(true)
                .isLocked(false)
                .failedLoginAttempts(0)
                .createdAt(LocalDateTime.now())
                .build();

        // Setup Redis mock
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
    }

    @Nested
    @DisplayName("Login Tests")
    class LoginTests {

        @Test
        @DisplayName("Should login successfully with valid credentials")
        void shouldLoginSuccessfully() {
            // Given
            String email = "test@example.com";
            String password = "password123";
            String accessToken = "access-token";
            String refreshToken = "refresh-token";
            String jti = "jti-123";

            when(valueOperations.get(anyString())).thenReturn(Mono.just("0"));
            when(userRepository.findByEmail(email)).thenReturn(Mono.just(testUser));
            when(jwtTokenProvider.generateAccessToken(testUser)).thenReturn(accessToken);
            when(jwtTokenProvider.generateRefreshToken(testUser)).thenReturn(refreshToken);
            when(jwtTokenProvider.getJtiFromToken(refreshToken)).thenReturn(jti);
            when(jwtTokenProvider.getAccessTokenExpirationSeconds()).thenReturn(3600L);
            when(redisTemplate.delete(anyString())).thenReturn(Mono.just(1L));
            when(userRepository.updateLastLoginAt(anyLong(), any(LocalDateTime.class))).thenReturn(Mono.just(1));
            when(userRepository.resetLoginAttempts(anyLong())).thenReturn(Mono.just(1));
            when(valueOperations.set(anyString(), anyString(), any(Duration.class))).thenReturn(Mono.just(true));

            // When & Then
            StepVerifier.create(authService.login(email, password))
                    .expectNextMatches(response -> {
                        return response.getAccessToken().equals(accessToken) &&
                               response.getRefreshToken().equals(refreshToken) &&
                               response.getUser().getEmail().equals(email) &&
                               response.getExpiresIn().equals(3600L);
                    })
                    .verifyComplete();
        }

        @Test
        @DisplayName("Should fail login with invalid password")
        void shouldFailLoginWithInvalidPassword() {
            // Given
            String email = "test@example.com";
            String wrongPassword = "wrongpassword";

            when(valueOperations.get(anyString())).thenReturn(Mono.just("0"));
            when(userRepository.findByEmail(email)).thenReturn(Mono.just(testUser));
            when(valueOperations.increment(anyString())).thenReturn(Mono.just(1L));
            when(redisTemplate.expire(anyString(), any(Duration.class))).thenReturn(Mono.just(true));

            // When & Then
            StepVerifier.create(authService.login(email, wrongPassword))
                    .expectError(AuthenticationException.class)
                    .verify();
        }

        @Test
        @DisplayName("Should fail login with non-existent email")
        void shouldFailLoginWithNonExistentEmail() {
            // Given
            String email = "nonexistent@example.com";
            String password = "password123";

            when(valueOperations.get(anyString())).thenReturn(Mono.just("0"));
            when(userRepository.findByEmail(email)).thenReturn(Mono.empty());
            when(valueOperations.increment(anyString())).thenReturn(Mono.just(1L));
            when(redisTemplate.expire(anyString(), any(Duration.class))).thenReturn(Mono.just(true));

            // When & Then
            StepVerifier.create(authService.login(email, password))
                    .expectError(AuthenticationException.class)
                    .verify();
        }

        @Test
        @DisplayName("Should fail login when account is locked")
        void shouldFailLoginWhenAccountLocked() {
            // Given
            String email = "test@example.com";
            String password = "password123";

            User lockedUser = User.builder()
                    .id(1L)
                    .email(email)
                    .passwordHash(passwordEncoder.encode(password))
                    .isActive(true)
                    .isLocked(true)
                    .lockedUntil(LocalDateTime.now().plusMinutes(10))
                    .build();

            when(valueOperations.get(anyString())).thenReturn(Mono.just("0"));
            when(userRepository.findByEmail(email)).thenReturn(Mono.just(lockedUser));
            when(valueOperations.increment(anyString())).thenReturn(Mono.just(1L));
            when(redisTemplate.expire(anyString(), any(Duration.class))).thenReturn(Mono.just(true));

            // When & Then
            StepVerifier.create(authService.login(email, password))
                    .expectError(AuthenticationException.class)
                    .verify();
        }

        @Test
        @DisplayName("Should fail login when account is not active")
        void shouldFailLoginWhenAccountNotActive() {
            // Given
            String email = "test@example.com";
            String password = "password123";

            User inactiveUser = User.builder()
                    .id(1L)
                    .email(email)
                    .passwordHash(passwordEncoder.encode(password))
                    .isActive(false)
                    .isLocked(false)
                    .build();

            when(valueOperations.get(anyString())).thenReturn(Mono.just("0"));
            when(userRepository.findByEmail(email)).thenReturn(Mono.just(inactiveUser));

            // When & Then
            StepVerifier.create(authService.login(email, password))
                    .expectError(AuthenticationException.class)
                    .verify();
        }

        @Test
        @DisplayName("Should fail with TooManyRequestsException when rate limit exceeded")
        void shouldFailWhenRateLimitExceeded() {
            // Given
            String email = "test@example.com";
            String password = "password123";

            when(valueOperations.get(anyString())).thenReturn(Mono.just("5"));

            // When & Then
            StepVerifier.create(authService.login(email, password))
                    .expectError(TooManyRequestsException.class)
                    .verify();
        }

        @Test
        @DisplayName("Should lock account after max failed attempts")
        void shouldLockAccountAfterMaxFailedAttempts() {
            // Given
            String email = "test@example.com";
            String wrongPassword = "wrongpassword";

            when(valueOperations.get(anyString())).thenReturn(Mono.just("4"));
            when(userRepository.findByEmail(email)).thenReturn(Mono.just(testUser));
            when(valueOperations.increment(anyString())).thenReturn(Mono.just(5L));
            when(userRepository.lockUser(anyLong(), eq(true), any(LocalDateTime.class))).thenReturn(Mono.just(1));

            // When & Then
            StepVerifier.create(authService.login(email, wrongPassword))
                    .expectError(TooManyRequestsException.class)
                    .verify();

            verify(userRepository).lockUser(eq(1L), eq(true), any(LocalDateTime.class));
        }
    }

    @Nested
    @DisplayName("Refresh Token Tests")
    class RefreshTokenTests {

        @Test
        @DisplayName("Should refresh token successfully")
        void shouldRefreshTokenSuccessfully() {
            // Given
            String oldRefreshToken = "old-refresh-token";
            String newAccessToken = "new-access-token";
            String newRefreshToken = "new-refresh-token";
            String oldJti = "old-jti";
            String newJti = "new-jti";

            when(jwtTokenProvider.validateToken(oldRefreshToken)).thenReturn(true);
            when(jwtTokenProvider.validateRefreshToken(oldRefreshToken)).thenReturn(true);
            when(jwtTokenProvider.getUserIdFromToken(oldRefreshToken)).thenReturn(1L);
            when(jwtTokenProvider.getJtiFromToken(oldRefreshToken)).thenReturn(oldJti);
            when(redisTemplate.hasKey(anyString())).thenReturn(Mono.just(true));
            when(userRepository.findById(1L)).thenReturn(Mono.just(testUser));
            when(redisTemplate.delete(anyString())).thenReturn(Mono.just(1L));
            when(jwtTokenProvider.generateAccessToken(testUser)).thenReturn(newAccessToken);
            when(jwtTokenProvider.generateRefreshToken(testUser)).thenReturn(newRefreshToken);
            when(jwtTokenProvider.getJtiFromToken(newRefreshToken)).thenReturn(newJti);
            when(jwtTokenProvider.getAccessTokenExpirationSeconds()).thenReturn(3600L);
            when(jwtTokenProvider.getRefreshTokenExpirationSeconds()).thenReturn(604800L);
            when(valueOperations.set(anyString(), anyString(), any(Duration.class))).thenReturn(Mono.just(true));

            // When & Then
            StepVerifier.create(authService.refreshToken(oldRefreshToken))
                    .expectNextMatches(response -> {
                        return response.getAccessToken().equals(newAccessToken) &&
                               response.getRefreshToken().equals(newRefreshToken) &&
                               response.getExpiresIn().equals(3600L);
                    })
                    .verifyComplete();
        }

        @Test
        @DisplayName("Should fail refresh with invalid token")
        void shouldFailRefreshWithInvalidToken() {
            // Given
            String invalidToken = "invalid-token";

            when(jwtTokenProvider.validateToken(invalidToken)).thenReturn(false);

            // When & Then
            StepVerifier.create(authService.refreshToken(invalidToken))
                    .expectError(AuthenticationException.class)
                    .verify();
        }

        @Test
        @DisplayName("Should fail refresh when token is not refresh type")
        void shouldFailRefreshWhenNotRefreshToken() {
            // Given
            String accessToken = "access-token";

            when(jwtTokenProvider.validateToken(accessToken)).thenReturn(true);
            when(jwtTokenProvider.validateRefreshToken(accessToken)).thenReturn(false);

            // When & Then
            StepVerifier.create(authService.refreshToken(accessToken))
                    .expectError(AuthenticationException.class)
                    .verify();
        }

        @Test
        @DisplayName("Should fail refresh when token is revoked")
        void shouldFailRefreshWhenTokenRevoked() {
            // Given
            String revokedToken = "revoked-token";

            when(jwtTokenProvider.validateToken(revokedToken)).thenReturn(true);
            when(jwtTokenProvider.validateRefreshToken(revokedToken)).thenReturn(true);
            when(jwtTokenProvider.getUserIdFromToken(revokedToken)).thenReturn(1L);
            when(jwtTokenProvider.getJtiFromToken(revokedToken)).thenReturn("jti-123");
            when(redisTemplate.hasKey(anyString())).thenReturn(Mono.just(false));

            // When & Then
            StepVerifier.create(authService.refreshToken(revokedToken))
                    .expectError(AuthenticationException.class)
                    .verify();
        }
    }

    @Nested
    @DisplayName("Logout Tests")
    class LogoutTests {

        @Test
        @DisplayName("Should logout successfully")
        void shouldLogoutSuccessfully() {
            // Given
            Long userId = 1L;
            String refreshToken = "refresh-token";
            String jti = "jti-123";

            when(jwtTokenProvider.getJtiFromToken(refreshToken)).thenReturn(jti);
            when(redisTemplate.delete(anyString())).thenReturn(Mono.just(1L));

            // When & Then
            StepVerifier.create(authService.logout(userId, refreshToken))
                    .verifyComplete();

            verify(redisTemplate).delete("refresh_token:1:jti-123");
        }

        @Test
        @DisplayName("Should handle logout with null refresh token")
        void shouldHandleLogoutWithNullToken() {
            // Given
            Long userId = 1L;

            // When & Then
            StepVerifier.create(authService.logout(userId, null))
                    .verifyComplete();

            verify(redisTemplate, never()).delete(anyString());
        }

        @Test
        @DisplayName("Should handle logout with empty refresh token")
        void shouldHandleLogoutWithEmptyToken() {
            // Given
            Long userId = 1L;

            // When & Then
            StepVerifier.create(authService.logout(userId, ""))
                    .verifyComplete();

            verify(redisTemplate, never()).delete(anyString());
        }
    }

    @Nested
    @DisplayName("Get Current User Tests")
    class GetCurrentUserTests {

        @Test
        @DisplayName("Should get current user successfully")
        void shouldGetCurrentUserSuccessfully() {
            // Given
            Long userId = 1L;

            when(userRepository.findById(userId)).thenReturn(Mono.just(testUser));

            // When & Then
            StepVerifier.create(authService.getCurrentUser(userId))
                    .expectNextMatches(response -> {
                        return response.getEmail().equals("test@example.com") &&
                               response.getUsername().equals("testuser") &&
                               response.getFirstName().equals("Test") &&
                               response.getLastName().equals("User");
                    })
                    .verifyComplete();
        }

        @Test
        @DisplayName("Should fail when user not found")
        void shouldFailWhenUserNotFound() {
            // Given
            Long userId = 999L;

            when(userRepository.findById(userId)).thenReturn(Mono.empty());

            // When & Then
            StepVerifier.create(authService.getCurrentUser(userId))
                    .expectError(UserNotFoundException.class)
                    .verify();
        }
    }
}
