package com.knowledge.backend.service;

import java.time.Duration;
import java.time.LocalDateTime;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.ReactiveRedisTemplate;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import com.knowledge.backend.api.dto.auth.LoginRequest;
import com.knowledge.backend.api.dto.auth.LoginResponse;
import com.knowledge.backend.api.dto.auth.TokenResponse;
import com.knowledge.backend.api.dto.auth.UserResponse;
import com.knowledge.backend.domain.entity.User;
import com.knowledge.backend.domain.repository.UserRepository;
import com.knowledge.backend.exception.AuthenticationException;
import com.knowledge.backend.exception.TooManyRequestsException;
import com.knowledge.backend.exception.UserNotFoundException;
import com.knowledge.backend.security.JwtTokenProvider;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import reactor.core.publisher.Mono;

/**
 * Authentication Service
 *
 * <p>Handles user authentication, token management, and session control
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class AuthService {

    private final UserRepository userRepository;
    private final JwtTokenProvider jwtTokenProvider;
    private final ReactiveRedisTemplate<String, String> redisTemplate;

    private final PasswordEncoder passwordEncoder = new BCryptPasswordEncoder();

    private static final String REFRESH_TOKEN_PREFIX = "refresh_token:";
    private static final String LOGIN_ATTEMPTS_PREFIX = "login_attempts:";

    @Value("${auth.max-login-attempts:5}")
    private int maxLoginAttempts;

    @Value("${auth.lockout-duration-minutes:15}")
    private int lockoutDurationMinutes;

    /**
     * Authenticate user and generate tokens
     *
     * @param email user email
     * @param password user password
     * @return Mono of LoginResponse with tokens
     */
    public Mono<LoginResponse> login(String email, String password) {
        log.info("Login attempt for email: {}", email);

        return checkRateLimit(email)
                .flatMap(allowed -> {
                    if (!allowed) {
                        log.warn("Rate limit exceeded for email: {}", email);
                        return Mono.error(new TooManyRequestsException(
                                "Login attempts exceeded. Please try again after " + lockoutDurationMinutes + " minutes.",
                                lockoutDurationMinutes * 60L
                        ));
                    }
                    return findAndValidateUser(email, password);
                });
    }

    /**
     * Refresh access token using refresh token
     *
     * @param refreshToken the refresh token
     * @return Mono of TokenResponse with new tokens
     */
    public Mono<TokenResponse> refreshToken(String refreshToken) {
        log.info("Token refresh attempt");

        if (!jwtTokenProvider.validateToken(refreshToken)) {
            log.warn("Invalid refresh token");
            return Mono.error(new AuthenticationException("Invalid or expired refresh token"));
        }

        if (!jwtTokenProvider.validateRefreshToken(refreshToken)) {
            log.warn("Token is not a refresh token");
            return Mono.error(new AuthenticationException("Invalid token type"));
        }

        Long userId = jwtTokenProvider.getUserIdFromToken(refreshToken);
        String jti = jwtTokenProvider.getJtiFromToken(refreshToken);

        // Check if refresh token is in Redis (not revoked)
        return isRefreshTokenValid(userId, jti)
                .flatMap(isValid -> {
                    if (!isValid) {
                        log.warn("Refresh token has been revoked for user: {}", userId);
                        return Mono.error(new AuthenticationException("Refresh token has been revoked"));
                    }
                    return userRepository.findById(userId);
                })
                .switchIfEmpty(Mono.error(new UserNotFoundException("User not found")))
                .filter(User::isAccountActive)
                .switchIfEmpty(Mono.error(new AuthenticationException("User account is not active")))
                .flatMap(user -> {
                    // Revoke old refresh token and generate new tokens
                    return revokeRefreshToken(userId, jti)
                            .then(Mono.defer(() -> {
                                String newAccessToken = jwtTokenProvider.generateAccessToken(user);
                                String newRefreshToken = jwtTokenProvider.generateRefreshToken(user);
                                String newJti = jwtTokenProvider.getJtiFromToken(newRefreshToken);

                                return storeRefreshToken(user.getId(), newJti)
                                        .thenReturn(TokenResponse.builder()
                                                .accessToken(newAccessToken)
                                                .refreshToken(newRefreshToken)
                                                .expiresIn(jwtTokenProvider.getAccessTokenExpirationSeconds())
                                                .build());
                            }));
                });
    }

    /**
     * Logout user and invalidate refresh token
     *
     * @param userId user ID
     * @param refreshToken the refresh token to invalidate
     * @return Mono of void
     */
    public Mono<Void> logout(Long userId, String refreshToken) {
        log.info("Logout for user: {}", userId);

        if (refreshToken == null || refreshToken.isEmpty()) {
            return Mono.empty();
        }

        try {
            String jti = jwtTokenProvider.getJtiFromToken(refreshToken);
            return revokeRefreshToken(userId, jti).then();
        } catch (Exception e) {
            log.warn("Failed to parse refresh token during logout: {}", e.getMessage());
            return Mono.empty();
        }
    }

    /**
     * Get current user information
     *
     * @param userId user ID
     * @return Mono of UserResponse
     */
    public Mono<UserResponse> getCurrentUser(Long userId) {
        log.debug("Getting current user info for: {}", userId);

        return userRepository.findById(userId)
                .switchIfEmpty(Mono.error(new UserNotFoundException("User not found")))
                .map(this::toUserResponse);
    }

    /**
     * Check if refresh token is valid (exists in Redis)
     *
     * @param userId user ID
     * @param jti JWT ID
     * @return Mono of Boolean
     */
    private Mono<Boolean> isRefreshTokenValid(Long userId, String jti) {
        String key = REFRESH_TOKEN_PREFIX + userId + ":" + jti;
        return redisTemplate.hasKey(key);
    }

    /**
     * Store refresh token in Redis
     *
     * @param userId user ID
     * @param jti JWT ID
     * @return Mono of Boolean
     */
    private Mono<Boolean> storeRefreshToken(Long userId, String jti) {
        String key = REFRESH_TOKEN_PREFIX + userId + ":" + jti;
        Duration ttl = Duration.ofSeconds(jwtTokenProvider.getRefreshTokenExpirationSeconds());
        return redisTemplate.opsForValue().set(key, "valid", ttl);
    }

    /**
     * Revoke refresh token from Redis
     *
     * @param userId user ID
     * @param jti JWT ID
     * @return Mono of Boolean
     */
    private Mono<Boolean> revokeRefreshToken(Long userId, String jti) {
        String key = REFRESH_TOKEN_PREFIX + userId + ":" + jti;
        return redisTemplate.delete(key).map(count -> count > 0);
    }

    /**
     * Check rate limit for login attempts
     *
     * @param email user email
     * @return Mono of Boolean (true if allowed)
     */
    private Mono<Boolean> checkRateLimit(String email) {
        String key = LOGIN_ATTEMPTS_PREFIX + email;

        return redisTemplate.opsForValue().get(key)
                .defaultIfEmpty("0")
                .flatMap(attemptsStr -> {
                    int attempts = Integer.parseInt(attemptsStr);
                    return Mono.just(attempts < maxLoginAttempts);
                });
    }

    /**
     * Increment login attempts counter
     *
     * @param email user email
     * @return Mono of current attempt count
     */
    private Mono<Long> incrementLoginAttempts(String email) {
        String key = LOGIN_ATTEMPTS_PREFIX + email;

        return redisTemplate.opsForValue().increment(key)
                .flatMap(count -> {
                    if (count == 1) {
                        // Set expiration on first attempt
                        return redisTemplate.expire(key, Duration.ofMinutes(lockoutDurationMinutes))
                                .thenReturn(count);
                    }
                    return Mono.just(count);
                });
    }

    /**
     * Reset login attempts counter
     *
     * @param email user email
     * @return Mono of Boolean
     */
    private Mono<Boolean> resetLoginAttempts(String email) {
        String key = LOGIN_ATTEMPTS_PREFIX + email;
        return redisTemplate.delete(key).map(count -> count > 0);
    }

    /**
     * Find and validate user credentials
     *
     * @param email user email
     * @param password user password
     * @return Mono of LoginResponse
     */
    private Mono<LoginResponse> findAndValidateUser(String email, String password) {
        return userRepository.findByEmail(email)
                .flatMap(user -> validateUserAndGenerateTokens(user, email, password))
                .switchIfEmpty(handleUserNotFound(email));
    }

    /**
     * Validate user and generate tokens
     *
     * @param user the user entity
     * @param email user email
     * @param password user password
     * @return Mono of LoginResponse
     */
    private Mono<LoginResponse> validateUserAndGenerateTokens(User user, String email, String password) {
        // Check if account is locked
        if (user.isAccountLocked()) {
            log.warn("Account is locked for email: {}", email);
            return incrementLoginAttempts(email)
                    .then(Mono.error(new AuthenticationException("Account is locked. Please try again later.")));
        }

        // Check if account is active
        if (!user.isAccountActive()) {
            log.warn("Account is not active for email: {}", email);
            return Mono.error(new AuthenticationException("Account is not active"));
        }

        // Validate password
        if (!passwordEncoder.matches(password, user.getPasswordHash())) {
            log.warn("Invalid password for email: {}", email);
            return handleInvalidPassword(email, user);
        }

        // Successful login
        log.info("Login successful for email: {}", email);
        return generateLoginResponse(user, email);
    }

    /**
     * Handle invalid password
     *
     * @param email user email
     * @param user the user entity
     * @return Mono error
     */
    private Mono<LoginResponse> handleInvalidPassword(String email, User user) {
        return incrementLoginAttempts(email)
                .flatMap(attempts -> {
                    if (attempts >= maxLoginAttempts) {
                        // Lock the account
                        return userRepository.lockUser(
                                        user.getId(),
                                        true,
                                        LocalDateTime.now().plusMinutes(lockoutDurationMinutes))
                                .then(Mono.error(new TooManyRequestsException(
                                        "Too many failed attempts. Account locked for " + lockoutDurationMinutes + " minutes.",
                                        lockoutDurationMinutes * 60L
                                )));
                    }
                    return Mono.error(new AuthenticationException("Invalid email or password"));
                });
    }

    /**
     * Handle user not found scenario
     *
     * @param email user email
     * @return Mono error
     */
    private Mono<LoginResponse> handleUserNotFound(String email) {
        log.warn("User not found for email: {}", email);
        return incrementLoginAttempts(email)
                .then(Mono.error(new AuthenticationException("Invalid email or password")));
    }

    /**
     * Generate login response with tokens
     *
     * @param user the user entity
     * @param email user email
     * @return Mono of LoginResponse
     */
    private Mono<LoginResponse> generateLoginResponse(User user, String email) {
        String accessToken = jwtTokenProvider.generateAccessToken(user);
        String refreshToken = jwtTokenProvider.generateRefreshToken(user);
        String jti = jwtTokenProvider.getJtiFromToken(refreshToken);

        return resetLoginAttempts(email)
                .then(userRepository.updateLastLoginAt(user.getId(), LocalDateTime.now()))
                .then(userRepository.resetLoginAttempts(user.getId()))
                .then(storeRefreshToken(user.getId(), jti))
                .thenReturn(LoginResponse.builder()
                        .user(LoginResponse.UserInfo.builder()
                                .id(user.getId().toString())
                                .email(user.getEmail())
                                .username(user.getUsername())
                                .roles(user.getRolesAsSet())
                                .build())
                        .accessToken(accessToken)
                        .refreshToken(refreshToken)
                        .expiresIn(jwtTokenProvider.getAccessTokenExpirationSeconds())
                        .build());
    }

    /**
     * Convert User entity to UserResponse DTO
     *
     * @param user the user entity
     * @return UserResponse DTO
     */
    private UserResponse toUserResponse(User user) {
        return UserResponse.builder()
                .id(user.getId().toString())
                .email(user.getEmail())
                .username(user.getUsername())
                .firstName(user.getFirstName())
                .lastName(user.getLastName())
                .roles(user.getRolesAsSet())
                .createdAt(user.getCreatedAt())
                .lastLoginAt(user.getLastLoginAt())
                .build();
    }
}
