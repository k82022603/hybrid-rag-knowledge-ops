package com.knowledge.gateway.security;

import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import javax.crypto.SecretKey;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Unit tests for JwtTokenValidator
 *
 * <p>Tests HS256 token validation, claim extraction, and token type detection.
 * Verifies that self-issued tokens are correctly validated while RS256 tokens
 * are identified as non-self-issued.
 */
class JwtTokenValidatorTest {

    private JwtTokenValidator validator;

    private static final String SECRET = "test-secret-key-minimum-32-characters-for-hs256-algorithm";
    private static final String ISSUER = "test-issuer";
    private SecretKey secretKey;

    @BeforeEach
    void setUp() {
        validator = new JwtTokenValidator();
        ReflectionTestUtils.setField(validator, "secret", SECRET);
        ReflectionTestUtils.setField(validator, "issuer", ISSUER);
        validator.init();

        secretKey = Keys.hmacShaKeyFor(SECRET.getBytes());
    }

    private String createValidToken() {
        return Jwts.builder()
            .subject("user-123")
            .issuer(ISSUER)
            .claim("email", "test@example.com")
            .claim("username", "testuser")
            .claim("roles", List.of("USER", "ADMIN"))
            .claim("type", "access")
            .issuedAt(new Date())
            .expiration(new Date(System.currentTimeMillis() + 3600000)) // 1 hour
            .signWith(secretKey)
            .compact();
    }

    @Nested
    @DisplayName("isSelfIssuedToken")
    class IsSelfIssuedToken {

        @Test
        @DisplayName("Returns true for HS256 token")
        void returnsTrue_ForHS256Token() {
            String token = createValidToken();
            assertThat(validator.isSelfIssuedToken(token)).isTrue();
        }

        @Test
        @DisplayName("Returns false for RS256-like token header")
        void returnsFalse_ForRS256Token() {
            // Simulate a token header with RS256 algorithm
            // Base64URL encode a header with RS256
            String rs256Header = java.util.Base64.getUrlEncoder().withoutPadding()
                .encodeToString("{\"alg\":\"RS256\",\"typ\":\"JWT\"}".getBytes());
            String fakePayload = java.util.Base64.getUrlEncoder().withoutPadding()
                .encodeToString("{\"sub\":\"user\"}".getBytes());
            String fakeToken = rs256Header + "." + fakePayload + ".fake-signature";

            assertThat(validator.isSelfIssuedToken(fakeToken)).isFalse();
        }

        @Test
        @DisplayName("Returns false for malformed token")
        void returnsFalse_ForMalformedToken() {
            assertThat(validator.isSelfIssuedToken("not-a-jwt")).isFalse();
        }

        @Test
        @DisplayName("Returns false for empty string")
        void returnsFalse_ForEmptyString() {
            assertThat(validator.isSelfIssuedToken("")).isFalse();
        }

        @Test
        @DisplayName("Returns false for token with only two parts")
        void returnsFalse_ForTwoPartToken() {
            assertThat(validator.isSelfIssuedToken("part1.part2")).isFalse();
        }
    }

    @Nested
    @DisplayName("validateToken")
    class ValidateToken {

        @Test
        @DisplayName("Returns true for valid token")
        void returnsTrue_ForValidToken() {
            String token = createValidToken();
            assertThat(validator.validateToken(token)).isTrue();
        }

        @Test
        @DisplayName("Returns false for expired token")
        void returnsFalse_ForExpiredToken() {
            String expiredToken = Jwts.builder()
                .subject("user-123")
                .issuer(ISSUER)
                .issuedAt(new Date(System.currentTimeMillis() - 7200000)) // 2 hours ago
                .expiration(new Date(System.currentTimeMillis() - 3600000)) // 1 hour ago
                .signWith(secretKey)
                .compact();

            assertThat(validator.validateToken(expiredToken)).isFalse();
        }

        @Test
        @DisplayName("Returns false for token with wrong signature")
        void returnsFalse_ForWrongSignature() {
            SecretKey wrongKey = Keys.hmacShaKeyFor(
                "different-secret-key-minimum-32-chars-for-hs256".getBytes()
            );
            String wrongToken = Jwts.builder()
                .subject("user-123")
                .issuer(ISSUER)
                .expiration(new Date(System.currentTimeMillis() + 3600000))
                .signWith(wrongKey)
                .compact();

            assertThat(validator.validateToken(wrongToken)).isFalse();
        }

        @Test
        @DisplayName("Returns false for token with wrong issuer")
        void returnsFalse_ForWrongIssuer() {
            String wrongIssuerToken = Jwts.builder()
                .subject("user-123")
                .issuer("wrong-issuer")
                .expiration(new Date(System.currentTimeMillis() + 3600000))
                .signWith(secretKey)
                .compact();

            assertThat(validator.validateToken(wrongIssuerToken)).isFalse();
        }

        @Test
        @DisplayName("Returns false for malformed token")
        void returnsFalse_ForMalformedToken() {
            assertThat(validator.validateToken("not.a.valid-jwt")).isFalse();
        }

        @Test
        @DisplayName("Returns false for empty token")
        void returnsFalse_ForEmptyToken() {
            assertThat(validator.validateToken("")).isFalse();
        }
    }

    @Nested
    @DisplayName("Claim extraction")
    class ClaimExtraction {

        @Test
        @DisplayName("getUserIdFromToken returns subject")
        void getUserIdFromToken_ReturnsSubject() {
            String token = createValidToken();
            assertThat(validator.getUserIdFromToken(token)).isEqualTo("user-123");
        }

        @Test
        @DisplayName("getEmailFromToken returns email claim")
        void getEmailFromToken_ReturnsEmail() {
            String token = createValidToken();
            assertThat(validator.getEmailFromToken(token)).isEqualTo("test@example.com");
        }

        @Test
        @DisplayName("getUsernameFromToken returns username claim")
        void getUsernameFromToken_ReturnsUsername() {
            String token = createValidToken();
            assertThat(validator.getUsernameFromToken(token)).isEqualTo("testuser");
        }

        @Test
        @DisplayName("getRolesFromToken returns roles set")
        void getRolesFromToken_ReturnsRoles() {
            String token = createValidToken();
            Set<String> roles = validator.getRolesFromToken(token);
            assertThat(roles).containsExactlyInAnyOrder("USER", "ADMIN");
        }

        @Test
        @DisplayName("getRolesFromToken returns empty set when no roles")
        void getRolesFromToken_ReturnsEmptySet_WhenNoRoles() {
            String tokenWithoutRoles = Jwts.builder()
                .subject("user-123")
                .issuer(ISSUER)
                .expiration(new Date(System.currentTimeMillis() + 3600000))
                .signWith(secretKey)
                .compact();

            Set<String> roles = validator.getRolesFromToken(tokenWithoutRoles);
            assertThat(roles).isEmpty();
        }

        @Test
        @DisplayName("getTokenType returns type claim")
        void getTokenType_ReturnsType() {
            String token = createValidToken();
            assertThat(validator.getTokenType(token)).isEqualTo("access");
        }
    }

    @Nested
    @DisplayName("getIssuer")
    class GetIssuer {

        @Test
        @DisplayName("Returns configured issuer")
        void returnsConfiguredIssuer() {
            assertThat(validator.getIssuer()).isEqualTo(ISSUER);
        }
    }
}
