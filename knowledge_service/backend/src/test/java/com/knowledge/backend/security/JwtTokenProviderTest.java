package com.knowledge.backend.security;

import static org.junit.jupiter.api.Assertions.*;

import java.time.LocalDateTime;
import java.util.Date;
import java.util.Set;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import com.knowledge.backend.domain.entity.User;

/**
 * Unit tests for JwtTokenProvider
 *
 * <p>Tests JWT token generation, validation, and parsing
 */
class JwtTokenProviderTest {

    private JwtTokenProvider jwtTokenProvider;
    private User testUser;

    @BeforeEach
    void setUp() {
        jwtTokenProvider = new JwtTokenProvider();

        // Set configuration values via reflection
        ReflectionTestUtils.setField(jwtTokenProvider, "secret", "TestSecretKeyForJWTTokenGenerationMustBeAtLeast256Bits");
        ReflectionTestUtils.setField(jwtTokenProvider, "accessTokenExpiration", 3600000L); // 1 hour
        ReflectionTestUtils.setField(jwtTokenProvider, "refreshTokenExpiration", 604800000L); // 7 days
        ReflectionTestUtils.setField(jwtTokenProvider, "issuer", "test-issuer");

        // Initialize the provider
        jwtTokenProvider.init();

        // Create test user
        testUser = User.builder()
                .id(1L)
                .email("test@example.com")
                .username("testuser")
                .passwordHash("hashed")
                .firstName("Test")
                .lastName("User")
                .roles("USER,ADMIN")
                .isActive(true)
                .createdAt(LocalDateTime.now())
                .build();
    }

    @Nested
    @DisplayName("Access Token Generation Tests")
    class AccessTokenGenerationTests {

        @Test
        @DisplayName("Should generate valid access token")
        void shouldGenerateValidAccessToken() {
            // When
            String token = jwtTokenProvider.generateAccessToken(testUser);

            // Then
            assertNotNull(token);
            assertFalse(token.isEmpty());
            assertTrue(jwtTokenProvider.validateToken(token));
        }

        @Test
        @DisplayName("Should include correct claims in access token")
        void shouldIncludeCorrectClaimsInAccessToken() {
            // When
            String token = jwtTokenProvider.generateAccessToken(testUser);

            // Then
            assertEquals(1L, jwtTokenProvider.getUserIdFromToken(token));
            assertEquals("test@example.com", jwtTokenProvider.getEmailFromToken(token));
            assertEquals("testuser", jwtTokenProvider.getUsernameFromToken(token));

            Set<String> roles = jwtTokenProvider.getRolesFromToken(token);
            assertTrue(roles.contains("USER"));
            assertTrue(roles.contains("ADMIN"));
        }

        @Test
        @DisplayName("Should set correct expiration for access token")
        void shouldSetCorrectExpirationForAccessToken() {
            // When
            String token = jwtTokenProvider.generateAccessToken(testUser);

            // Then
            Date expiration = jwtTokenProvider.getExpirationFromToken(token);
            assertNotNull(expiration);

            // Expiration should be approximately 1 hour from now
            long expectedExpiration = System.currentTimeMillis() + 3600000L;
            long actualExpiration = expiration.getTime();

            // Allow 5 second tolerance
            assertTrue(Math.abs(expectedExpiration - actualExpiration) < 5000);
        }
    }

    @Nested
    @DisplayName("Refresh Token Generation Tests")
    class RefreshTokenGenerationTests {

        @Test
        @DisplayName("Should generate valid refresh token")
        void shouldGenerateValidRefreshToken() {
            // When
            String token = jwtTokenProvider.generateRefreshToken(testUser);

            // Then
            assertNotNull(token);
            assertFalse(token.isEmpty());
            assertTrue(jwtTokenProvider.validateToken(token));
        }

        @Test
        @DisplayName("Should include JTI in refresh token")
        void shouldIncludeJtiInRefreshToken() {
            // When
            String token = jwtTokenProvider.generateRefreshToken(testUser);

            // Then
            String jti = jwtTokenProvider.getJtiFromToken(token);
            assertNotNull(jti);
            assertFalse(jti.isEmpty());
        }

        @Test
        @DisplayName("Should generate unique JTI for each refresh token")
        void shouldGenerateUniqueJtiForEachToken() {
            // When
            String token1 = jwtTokenProvider.generateRefreshToken(testUser);
            String token2 = jwtTokenProvider.generateRefreshToken(testUser);

            // Then
            String jti1 = jwtTokenProvider.getJtiFromToken(token1);
            String jti2 = jwtTokenProvider.getJtiFromToken(token2);

            assertNotEquals(jti1, jti2);
        }

        @Test
        @DisplayName("Should validate refresh token type correctly")
        void shouldValidateRefreshTokenType() {
            // When
            String refreshToken = jwtTokenProvider.generateRefreshToken(testUser);
            String accessToken = jwtTokenProvider.generateAccessToken(testUser);

            // Then
            assertTrue(jwtTokenProvider.validateRefreshToken(refreshToken));
            assertFalse(jwtTokenProvider.validateRefreshToken(accessToken));
        }

        @Test
        @DisplayName("Should set correct expiration for refresh token")
        void shouldSetCorrectExpirationForRefreshToken() {
            // When
            String token = jwtTokenProvider.generateRefreshToken(testUser);

            // Then
            Date expiration = jwtTokenProvider.getExpirationFromToken(token);
            assertNotNull(expiration);

            // Expiration should be approximately 7 days from now
            long expectedExpiration = System.currentTimeMillis() + 604800000L;
            long actualExpiration = expiration.getTime();

            // Allow 5 second tolerance
            assertTrue(Math.abs(expectedExpiration - actualExpiration) < 5000);
        }
    }

    @Nested
    @DisplayName("Token Validation Tests")
    class TokenValidationTests {

        @Test
        @DisplayName("Should return false for invalid token")
        void shouldReturnFalseForInvalidToken() {
            // When
            boolean isValid = jwtTokenProvider.validateToken("invalid.token.here");

            // Then
            assertFalse(isValid);
        }

        @Test
        @DisplayName("Should return false for null token")
        void shouldReturnFalseForNullToken() {
            // When & Then
            assertFalse(jwtTokenProvider.validateToken(null));
        }

        @Test
        @DisplayName("Should return false for empty token")
        void shouldReturnFalseForEmptyToken() {
            // When & Then
            assertFalse(jwtTokenProvider.validateToken(""));
        }

        @Test
        @DisplayName("Should return false for malformed token")
        void shouldReturnFalseForMalformedToken() {
            // When & Then
            assertFalse(jwtTokenProvider.validateToken("not-a-jwt"));
            assertFalse(jwtTokenProvider.validateToken("only.two.parts.but.invalid"));
        }

        @Test
        @DisplayName("Should detect expired token")
        void shouldDetectExpiredToken() {
            // Create a provider with very short expiration
            JwtTokenProvider shortExpProvider = new JwtTokenProvider();
            ReflectionTestUtils.setField(shortExpProvider, "secret", "TestSecretKeyForJWTTokenGenerationMustBeAtLeast256Bits");
            ReflectionTestUtils.setField(shortExpProvider, "accessTokenExpiration", 1L); // 1ms
            ReflectionTestUtils.setField(shortExpProvider, "refreshTokenExpiration", 1L);
            ReflectionTestUtils.setField(shortExpProvider, "issuer", "test-issuer");
            shortExpProvider.init();

            // Generate token and wait for expiration
            String token = shortExpProvider.generateAccessToken(testUser);

            try {
                Thread.sleep(100); // Wait for token to expire
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }

            // Then
            assertFalse(shortExpProvider.validateToken(token));
            assertTrue(shortExpProvider.isTokenExpired(token));
        }
    }

    @Nested
    @DisplayName("Expiration Calculation Tests")
    class ExpirationCalculationTests {

        @Test
        @DisplayName("Should return correct access token expiration in seconds")
        void shouldReturnCorrectAccessTokenExpirationSeconds() {
            // When
            long expirationSeconds = jwtTokenProvider.getAccessTokenExpirationSeconds();

            // Then
            assertEquals(3600L, expirationSeconds);
        }

        @Test
        @DisplayName("Should return correct refresh token expiration in seconds")
        void shouldReturnCorrectRefreshTokenExpirationSeconds() {
            // When
            long expirationSeconds = jwtTokenProvider.getRefreshTokenExpirationSeconds();

            // Then
            assertEquals(604800L, expirationSeconds);
        }
    }

    @Nested
    @DisplayName("Secret Key Security Tests")
    class SecretKeyTests {

        @Test
        @DisplayName("Should reject null secret key")
        void shouldRejectNullSecretKey() {
            // Given
            JwtTokenProvider nullSecretProvider = new JwtTokenProvider();
            ReflectionTestUtils.setField(nullSecretProvider, "secret", null);
            ReflectionTestUtils.setField(nullSecretProvider, "accessTokenExpiration", 3600000L);
            ReflectionTestUtils.setField(nullSecretProvider, "refreshTokenExpiration", 604800000L);
            ReflectionTestUtils.setField(nullSecretProvider, "issuer", "test-issuer");

            // When & Then
            IllegalStateException ex = assertThrows(IllegalStateException.class, nullSecretProvider::init);
            assertTrue(ex.getMessage().contains("JWT_SECRET"));
        }

        @Test
        @DisplayName("Should reject blank secret key")
        void shouldRejectBlankSecretKey() {
            // Given
            JwtTokenProvider blankSecretProvider = new JwtTokenProvider();
            ReflectionTestUtils.setField(blankSecretProvider, "secret", "   ");
            ReflectionTestUtils.setField(blankSecretProvider, "accessTokenExpiration", 3600000L);
            ReflectionTestUtils.setField(blankSecretProvider, "refreshTokenExpiration", 604800000L);
            ReflectionTestUtils.setField(blankSecretProvider, "issuer", "test-issuer");

            // When & Then
            IllegalStateException ex = assertThrows(IllegalStateException.class, blankSecretProvider::init);
            assertTrue(ex.getMessage().contains("JWT_SECRET"));
        }

        @Test
        @DisplayName("Should reject empty secret key")
        void shouldRejectEmptySecretKey() {
            // Given
            JwtTokenProvider emptySecretProvider = new JwtTokenProvider();
            ReflectionTestUtils.setField(emptySecretProvider, "secret", "");
            ReflectionTestUtils.setField(emptySecretProvider, "accessTokenExpiration", 3600000L);
            ReflectionTestUtils.setField(emptySecretProvider, "refreshTokenExpiration", 604800000L);
            ReflectionTestUtils.setField(emptySecretProvider, "issuer", "test-issuer");

            // When & Then
            IllegalStateException ex = assertThrows(IllegalStateException.class, emptySecretProvider::init);
            assertTrue(ex.getMessage().contains("JWT_SECRET"));
        }

        @Test
        @DisplayName("Should reject short secret key (less than 32 characters)")
        void shouldRejectShortSecretKey() {
            // Given
            JwtTokenProvider shortSecretProvider = new JwtTokenProvider();
            ReflectionTestUtils.setField(shortSecretProvider, "secret", "short");
            ReflectionTestUtils.setField(shortSecretProvider, "accessTokenExpiration", 3600000L);
            ReflectionTestUtils.setField(shortSecretProvider, "refreshTokenExpiration", 604800000L);
            ReflectionTestUtils.setField(shortSecretProvider, "issuer", "test-issuer");

            // When & Then
            IllegalStateException ex = assertThrows(IllegalStateException.class, shortSecretProvider::init);
            assertTrue(ex.getMessage().contains("at least 32 characters"));
        }

        @Test
        @DisplayName("Should accept valid secret key with 32+ characters")
        void shouldAcceptValidSecretKey() {
            // Given
            JwtTokenProvider validSecretProvider = new JwtTokenProvider();
            ReflectionTestUtils.setField(validSecretProvider, "secret",
                "ThisIsAValidSecretKeyWith32Chars!");
            ReflectionTestUtils.setField(validSecretProvider, "accessTokenExpiration", 3600000L);
            ReflectionTestUtils.setField(validSecretProvider, "refreshTokenExpiration", 604800000L);
            ReflectionTestUtils.setField(validSecretProvider, "issuer", "test-issuer");

            // When & Then - should not throw
            assertDoesNotThrow(validSecretProvider::init);
            String token = validSecretProvider.generateAccessToken(testUser);
            assertNotNull(token);
            assertTrue(validSecretProvider.validateToken(token));
        }
    }

    @Nested
    @DisplayName("User Roles Tests")
    class UserRolesTests {

        @Test
        @DisplayName("Should handle user with no roles")
        void shouldHandleUserWithNoRoles() {
            // Given
            User noRolesUser = User.builder()
                    .id(2L)
                    .email("noroles@example.com")
                    .username("noroles")
                    .roles(null)
                    .isActive(true)
                    .build();

            // When
            String token = jwtTokenProvider.generateAccessToken(noRolesUser);
            Set<String> roles = jwtTokenProvider.getRolesFromToken(token);

            // Then
            assertNotNull(roles);
            assertTrue(roles.isEmpty());
        }

        @Test
        @DisplayName("Should handle user with empty roles")
        void shouldHandleUserWithEmptyRoles() {
            // Given
            User emptyRolesUser = User.builder()
                    .id(2L)
                    .email("emptyroles@example.com")
                    .username("emptyroles")
                    .roles("")
                    .isActive(true)
                    .build();

            // When
            String token = jwtTokenProvider.generateAccessToken(emptyRolesUser);
            Set<String> roles = jwtTokenProvider.getRolesFromToken(token);

            // Then
            assertNotNull(roles);
            assertTrue(roles.isEmpty());
        }

        @Test
        @DisplayName("Should handle user with single role")
        void shouldHandleUserWithSingleRole() {
            // Given
            User singleRoleUser = User.builder()
                    .id(2L)
                    .email("single@example.com")
                    .username("singlerole")
                    .roles("USER")
                    .isActive(true)
                    .build();

            // When
            String token = jwtTokenProvider.generateAccessToken(singleRoleUser);
            Set<String> roles = jwtTokenProvider.getRolesFromToken(token);

            // Then
            assertEquals(1, roles.size());
            assertTrue(roles.contains("USER"));
        }

        @Test
        @DisplayName("Should handle user with multiple roles")
        void shouldHandleUserWithMultipleRoles() {
            // Given
            User multiRoleUser = User.builder()
                    .id(2L)
                    .email("multi@example.com")
                    .username("multirole")
                    .roles("USER,ADMIN,DEVELOPER")
                    .isActive(true)
                    .build();

            // When
            String token = jwtTokenProvider.generateAccessToken(multiRoleUser);
            Set<String> roles = jwtTokenProvider.getRolesFromToken(token);

            // Then
            assertEquals(3, roles.size());
            assertTrue(roles.contains("USER"));
            assertTrue(roles.contains("ADMIN"));
            assertTrue(roles.contains("DEVELOPER"));
        }
    }
}
