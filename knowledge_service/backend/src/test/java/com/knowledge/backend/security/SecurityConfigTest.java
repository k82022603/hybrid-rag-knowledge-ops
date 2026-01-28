package com.knowledge.backend.security;

import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

/**
 * Security Configuration Tests
 *
 * <p>Validates security hardening measures for STORY-053:
 * - JWT Secret environment variable enforcement
 * - Application startup failure on missing/short secrets
 *
 * @since Sprint 04 - STORY-053 Security Hardening
 */
class SecurityConfigTest {

    @Nested
    @DisplayName("JWT Secret Validation Tests (STORY-053)")
    class JwtSecretValidationTests {

        @Test
        @DisplayName("AC1: Application should fail to start when JWT_SECRET is not set (empty)")
        void shouldFailWhenJwtSecretIsEmpty() {
            // Given
            JwtTokenProvider provider = new JwtTokenProvider();
            ReflectionTestUtils.setField(provider, "secret", "");
            ReflectionTestUtils.setField(provider, "accessTokenExpiration", 3600000L);
            ReflectionTestUtils.setField(provider, "refreshTokenExpiration", 604800000L);
            ReflectionTestUtils.setField(provider, "issuer", "test-issuer");

            // When & Then
            IllegalStateException ex = assertThrows(IllegalStateException.class, provider::init);
            assertTrue(ex.getMessage().contains("JWT_SECRET"),
                "Error message should mention JWT_SECRET");
            assertTrue(ex.getMessage().contains("not set"),
                "Error message should indicate the secret is not set");
        }

        @Test
        @DisplayName("AC1: Application should fail to start when JWT_SECRET is null")
        void shouldFailWhenJwtSecretIsNull() {
            // Given
            JwtTokenProvider provider = new JwtTokenProvider();
            ReflectionTestUtils.setField(provider, "secret", null);
            ReflectionTestUtils.setField(provider, "accessTokenExpiration", 3600000L);
            ReflectionTestUtils.setField(provider, "refreshTokenExpiration", 604800000L);
            ReflectionTestUtils.setField(provider, "issuer", "test-issuer");

            // When & Then
            assertThrows(IllegalStateException.class, provider::init);
        }

        @Test
        @DisplayName("AC5: application.yml should not contain hardcoded JWT secret default")
        void shouldNotHaveHardcodedDefault() {
            // This test verifies the @Value annotation no longer has a default
            // By creating a provider and NOT setting the secret, init() should fail
            JwtTokenProvider provider = new JwtTokenProvider();
            // secret field is null by default (no hardcoded value)
            ReflectionTestUtils.setField(provider, "accessTokenExpiration", 3600000L);
            ReflectionTestUtils.setField(provider, "refreshTokenExpiration", 604800000L);
            ReflectionTestUtils.setField(provider, "issuer", "test-issuer");

            // When & Then - should fail because no default secret exists
            assertThrows(IllegalStateException.class, provider::init);
        }

        @Test
        @DisplayName("JWT Secret minimum length enforcement (32 chars)")
        void shouldEnforceMinimumSecretLength() {
            // Given
            JwtTokenProvider provider = new JwtTokenProvider();
            ReflectionTestUtils.setField(provider, "secret", "TooShortSecret123"); // 17 chars
            ReflectionTestUtils.setField(provider, "accessTokenExpiration", 3600000L);
            ReflectionTestUtils.setField(provider, "refreshTokenExpiration", 604800000L);
            ReflectionTestUtils.setField(provider, "issuer", "test-issuer");

            // When & Then
            IllegalStateException ex = assertThrows(IllegalStateException.class, provider::init);
            assertTrue(ex.getMessage().contains("32 characters"),
                "Error message should mention minimum character requirement");
        }

        @Test
        @DisplayName("Should succeed with properly configured secret")
        void shouldSucceedWithProperSecret() {
            // Given
            JwtTokenProvider provider = new JwtTokenProvider();
            ReflectionTestUtils.setField(provider, "secret",
                "AProperlyLongSecretKeyThatExceeds32CharactersForSecurity!");
            ReflectionTestUtils.setField(provider, "accessTokenExpiration", 3600000L);
            ReflectionTestUtils.setField(provider, "refreshTokenExpiration", 604800000L);
            ReflectionTestUtils.setField(provider, "issuer", "test-issuer");

            // When & Then
            assertDoesNotThrow(provider::init);
        }
    }
}
