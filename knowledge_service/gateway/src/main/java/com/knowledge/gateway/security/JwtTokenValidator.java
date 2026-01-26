package com.knowledge.gateway.security;

import java.util.Collection;
import java.util.Set;
import java.util.stream.Collectors;

import javax.crypto.SecretKey;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.ExpiredJwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.MalformedJwtException;
import io.jsonwebtoken.UnsupportedJwtException;
import io.jsonwebtoken.security.Keys;
import io.jsonwebtoken.security.SignatureException;
import jakarta.annotation.PostConstruct;
import lombok.extern.slf4j.Slf4j;

/**
 * Lightweight JWT Token Validator for Gateway
 *
 * <p>Validates self-issued HS256 tokens from Direct Login ({@code /api/v1/auth/login}).
 * Uses the same secret key as the Backend's JwtTokenProvider for token verification.
 *
 * <p>This is intentionally separate from the Backend's JwtTokenProvider to:
 * <ul>
 *   <li>Avoid coupling Gateway to Backend domain entities</li>
 *   <li>Keep Gateway lightweight (no User entity dependency)</li>
 *   <li>Follow single-responsibility principle per service</li>
 * </ul>
 */
@Slf4j
@Component
public class JwtTokenValidator {

    @Value("${jwt.secret:your-256-bit-secret-key-for-jwt-token-generation-minimum-32-characters}")
    private String secret;

    @Value("${jwt.issuer:knowledge-platform}")
    private String issuer;

    private SecretKey key;

    @PostConstruct
    public void init() {
        // Ensure secret is at least 256 bits (32 bytes) for HS256
        if (secret.length() < 32) {
            secret = secret + "0".repeat(32 - secret.length());
        }
        this.key = Keys.hmacShaKeyFor(secret.getBytes());
        log.info("JwtTokenValidator initialized with issuer: {}", issuer);
    }

    /**
     * Check if a token is a self-issued HS256 token by examining its structure.
     *
     * <p>Self-issued tokens have 3 parts and use HS256 algorithm with our issuer.
     * Keycloak RS256 tokens will have a different issuer (Keycloak realm URL).
     *
     * @param token the JWT token string
     * @return true if the token appears to be a self-issued HS256 token
     */
    public boolean isSelfIssuedToken(String token) {
        try {
            // Parse header without verification to check algorithm
            String[] parts = token.split("\\.");
            if (parts.length != 3) {
                return false;
            }

            // Decode header (Base64URL)
            String headerJson = new String(
                java.util.Base64.getUrlDecoder().decode(parts[0])
            );

            // Check if HS256 algorithm
            return headerJson.contains("\"alg\":\"HS256\"");
        } catch (Exception e) {
            log.debug("Failed to parse token header: {}", e.getMessage());
            return false;
        }
    }

    /**
     * Validate a self-issued HS256 JWT token.
     *
     * @param token the JWT token string
     * @return true if the token is valid (correct signature, not expired, correct issuer)
     */
    public boolean validateToken(String token) {
        try {
            Jwts.parser()
                .verifyWith(key)
                .requireIssuer(issuer)
                .build()
                .parseSignedClaims(token);
            return true;
        } catch (SignatureException ex) {
            log.warn("Invalid JWT signature: {}", ex.getMessage());
        } catch (ExpiredJwtException ex) {
            log.warn("Expired JWT token: {}", ex.getMessage());
        } catch (MalformedJwtException ex) {
            log.warn("Malformed JWT token: {}", ex.getMessage());
        } catch (UnsupportedJwtException ex) {
            log.warn("Unsupported JWT token: {}", ex.getMessage());
        } catch (IllegalArgumentException ex) {
            log.warn("JWT claims string is empty: {}", ex.getMessage());
        }
        return false;
    }

    /**
     * Get user ID (subject) from token.
     *
     * @param token the JWT token string
     * @return user ID as string
     */
    public String getUserIdFromToken(String token) {
        Claims claims = getClaims(token);
        return claims.getSubject();
    }

    /**
     * Get email from token claims.
     *
     * @param token the JWT token string
     * @return user email address
     */
    public String getEmailFromToken(String token) {
        Claims claims = getClaims(token);
        return claims.get("email", String.class);
    }

    /**
     * Get username from token claims.
     *
     * @param token the JWT token string
     * @return username
     */
    public String getUsernameFromToken(String token) {
        Claims claims = getClaims(token);
        return claims.get("username", String.class);
    }

    /**
     * Get roles from token claims.
     *
     * @param token the JWT token string
     * @return set of role names (e.g., "ADMIN", "USER")
     */
    @SuppressWarnings("unchecked")
    public Set<String> getRolesFromToken(String token) {
        Claims claims = getClaims(token);
        Object roles = claims.get("roles");
        if (roles instanceof Collection) {
            return ((Collection<String>) roles).stream()
                .map(String::valueOf)
                .collect(Collectors.toSet());
        }
        return Set.of();
    }

    /**
     * Get token type (access or refresh) from claims.
     *
     * @param token the JWT token string
     * @return token type string
     */
    public String getTokenType(String token) {
        Claims claims = getClaims(token);
        return claims.get("type", String.class);
    }

    /**
     * Get the configured issuer for this validator.
     *
     * @return the JWT issuer string
     */
    public String getIssuer() {
        return issuer;
    }

    /**
     * Parse and return claims from a validated token.
     *
     * @param token the JWT token string
     * @return Claims object containing all token claims
     */
    private Claims getClaims(String token) {
        return Jwts.parser()
            .verifyWith(key)
            .requireIssuer(issuer)
            .build()
            .parseSignedClaims(token)
            .getPayload();
    }
}
