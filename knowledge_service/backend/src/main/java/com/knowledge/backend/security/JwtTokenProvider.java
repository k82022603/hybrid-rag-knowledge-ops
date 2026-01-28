package com.knowledge.backend.security;

import java.security.Key;
import java.util.Date;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

import javax.crypto.SecretKey;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import com.knowledge.backend.domain.entity.User;

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
 * JWT Token Provider
 *
 * <p>Handles JWT token generation, validation, and parsing.
 *
 * <p>Security: JWT_SECRET must be provided via environment variable.
 * The application will fail to start if JWT_SECRET is not set or is too short.
 * No default/fallback secret is allowed.
 */
@Slf4j
@Component
public class JwtTokenProvider {

    @Value("${jwt.secret}")
    private String secret;

    @Value("${jwt.access-token-expiration:3600000}")
    private long accessTokenExpiration; // 1 hour in milliseconds

    @Value("${jwt.refresh-token-expiration:604800000}")
    private long refreshTokenExpiration; // 7 days in milliseconds

    @Value("${jwt.issuer:knowledge-platform}")
    private String issuer;

    private SecretKey key;

    /**
     * Validate and initialize the JWT signing key.
     *
     * <p>Fails fast if JWT_SECRET is not configured or is too short.
     * This prevents the application from starting with an insecure configuration.
     *
     * @throws IllegalStateException if JWT_SECRET is missing or shorter than 32 characters
     */
    @PostConstruct
    public void init() {
        if (secret == null || secret.isBlank()) {
            throw new IllegalStateException(
                "JWT_SECRET environment variable is not set. " +
                "Application cannot start without a valid JWT secret. " +
                "Set JWT_SECRET with at least 32 characters."
            );
        }
        if (secret.length() < 32) {
            throw new IllegalStateException(
                "JWT_SECRET must be at least 32 characters (256 bits) for HS256 signing. " +
                "Current length: " + secret.length() + ". " +
                "Generate a secure secret: openssl rand -base64 48"
            );
        }
        this.key = Keys.hmacShaKeyFor(secret.getBytes());
        log.info("JWT Token Provider initialized successfully (secret length: {} chars)", secret.length());
    }

    /**
     * Generate access token for user
     *
     * @param user the user entity
     * @return JWT access token
     */
    public String generateAccessToken(User user) {
        Date now = new Date();
        Date expiryDate = new Date(now.getTime() + accessTokenExpiration);

        return Jwts.builder()
                .subject(user.getId().toString())
                .issuer(issuer)
                .issuedAt(now)
                .expiration(expiryDate)
                .claims(Map.of(
                        "email", user.getEmail(),
                        "username", user.getUsername(),
                        "roles", user.getRolesAsSet(),
                        "type", "access"
                ))
                .signWith(key, Jwts.SIG.HS256)
                .compact();
    }

    /**
     * Generate refresh token for user
     *
     * @param user the user entity
     * @return JWT refresh token
     */
    public String generateRefreshToken(User user) {
        Date now = new Date();
        Date expiryDate = new Date(now.getTime() + refreshTokenExpiration);

        return Jwts.builder()
                .subject(user.getId().toString())
                .issuer(issuer)
                .issuedAt(now)
                .expiration(expiryDate)
                .id(UUID.randomUUID().toString())
                .claims(Map.of(
                        "email", user.getEmail(),
                        "type", "refresh"
                ))
                .signWith(key, Jwts.SIG.HS256)
                .compact();
    }

    /**
     * Validate JWT token
     *
     * @param token the JWT token
     * @return true if token is valid
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
            log.error("Invalid JWT signature: {}", ex.getMessage());
        } catch (MalformedJwtException ex) {
            log.error("Invalid JWT token: {}", ex.getMessage());
        } catch (ExpiredJwtException ex) {
            log.error("Expired JWT token: {}", ex.getMessage());
        } catch (UnsupportedJwtException ex) {
            log.error("Unsupported JWT token: {}", ex.getMessage());
        } catch (IllegalArgumentException ex) {
            log.error("JWT claims string is empty: {}", ex.getMessage());
        }
        return false;
    }

    /**
     * Validate refresh token specifically
     *
     * @param token the JWT refresh token
     * @return true if token is valid and is a refresh token
     */
    public boolean validateRefreshToken(String token) {
        try {
            Claims claims = getClaims(token);
            String type = claims.get("type", String.class);
            return "refresh".equals(type);
        } catch (Exception ex) {
            log.error("Refresh token validation failed: {}", ex.getMessage());
            return false;
        }
    }

    /**
     * Get user ID from token
     *
     * @param token the JWT token
     * @return user ID
     */
    public Long getUserIdFromToken(String token) {
        Claims claims = getClaims(token);
        return Long.parseLong(claims.getSubject());
    }

    /**
     * Get email from token
     *
     * @param token the JWT token
     * @return user email
     */
    public String getEmailFromToken(String token) {
        Claims claims = getClaims(token);
        return claims.get("email", String.class);
    }

    /**
     * Get username from token
     *
     * @param token the JWT token
     * @return username
     */
    public String getUsernameFromToken(String token) {
        Claims claims = getClaims(token);
        return claims.get("username", String.class);
    }

    /**
     * Get roles from token
     *
     * @param token the JWT token
     * @return set of roles
     */
    @SuppressWarnings("unchecked")
    public Set<String> getRolesFromToken(String token) {
        Claims claims = getClaims(token);
        Object roles = claims.get("roles");
        if (roles instanceof java.util.Collection) {
            return Set.copyOf((java.util.Collection<String>) roles);
        }
        return Set.of();
    }

    /**
     * Get JWT ID (jti) from token
     *
     * @param token the JWT token
     * @return JWT ID
     */
    public String getJtiFromToken(String token) {
        Claims claims = getClaims(token);
        return claims.getId();
    }

    /**
     * Get expiration date from token
     *
     * @param token the JWT token
     * @return expiration date
     */
    public Date getExpirationFromToken(String token) {
        Claims claims = getClaims(token);
        return claims.getExpiration();
    }

    /**
     * Check if token is expired
     *
     * @param token the JWT token
     * @return true if token is expired
     */
    public boolean isTokenExpired(String token) {
        try {
            Date expiration = getExpirationFromToken(token);
            return expiration.before(new Date());
        } catch (ExpiredJwtException ex) {
            return true;
        }
    }

    /**
     * Get access token expiration in seconds
     *
     * @return expiration in seconds
     */
    public long getAccessTokenExpirationSeconds() {
        return accessTokenExpiration / 1000;
    }

    /**
     * Get refresh token expiration in seconds
     *
     * @return expiration in seconds
     */
    public long getRefreshTokenExpirationSeconds() {
        return refreshTokenExpiration / 1000;
    }

    /**
     * Get claims from token
     *
     * @param token the JWT token
     * @return Claims object
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
