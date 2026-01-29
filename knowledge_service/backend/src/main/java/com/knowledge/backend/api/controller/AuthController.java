package com.knowledge.backend.api.controller;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.knowledge.backend.api.dto.auth.LoginRequest;
import com.knowledge.backend.api.dto.auth.LoginResponse;
import com.knowledge.backend.api.dto.auth.LogoutRequest;
import com.knowledge.backend.api.dto.auth.RefreshRequest;
import com.knowledge.backend.api.dto.auth.TokenResponse;
import com.knowledge.backend.api.dto.auth.UserResponse;
import com.knowledge.backend.security.JwtUser;
import com.knowledge.backend.service.AuthService;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import reactor.core.publisher.Mono;

/**
 * Authentication Controller
 *
 * <p>Handles authentication endpoints: login, logout, refresh, and user info
 *
 * <p>Endpoints:
 * <ul>
 *   <li>POST /api/v1/auth/login - Authenticate user with email/password</li>
 *   <li>POST /api/v1/auth/refresh - Refresh access token</li>
 *   <li>POST /api/v1/auth/logout - Invalidate session</li>
 *   <li>GET /api/v1/auth/me - Get current user info</li>
 * </ul>
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;

    /**
     * Login endpoint
     *
     * <p>Authenticates user with email and password, returns JWT tokens
     *
     * @param request login credentials (email, password)
     * @return LoginResponse with user info and tokens
     */
    @PostMapping("/login")
    public Mono<ResponseEntity<LoginResponse>> login(
            @Valid @RequestBody LoginRequest request
    ) {
        log.info("Login request for email: {}", request.getEmail());

        return authService.login(request.getEmail(), request.getPassword())
                .map(response -> {
                    log.info("Login successful for email: {}", request.getEmail());
                    return ResponseEntity.ok(response);
                })
                .doOnError(e -> log.error("Login failed for email {}: {}", request.getEmail(), e.getMessage()));
    }

    /**
     * Refresh token endpoint
     *
     * <p>Generates new access token using refresh token
     *
     * @param request refresh token
     * @return TokenResponse with new tokens
     */
    @PostMapping("/refresh")
    public Mono<ResponseEntity<TokenResponse>> refresh(
            @Valid @RequestBody RefreshRequest request
    ) {
        log.info("Token refresh request");

        return authService.refreshToken(request.getRefreshToken())
                .map(response -> {
                    log.info("Token refresh successful");
                    return ResponseEntity.ok(response);
                })
                .doOnError(e -> log.error("Token refresh failed: {}", e.getMessage()));
    }

    /**
     * Logout endpoint
     *
     * <p>Invalidates refresh token and ends session.
     * Requires authentication - unauthenticated requests return 401 Unauthorized.
     *
     * @param principal current authenticated user from JWT
     * @param request optional refresh token to invalidate
     * @return empty response with 200 OK, or 401 if not authenticated
     */
    @PostMapping("/logout")
    public Mono<ResponseEntity<Void>> logout(
            @AuthenticationPrincipal Object principal,
            @RequestBody(required = false) LogoutRequest request
    ) {
        // Logout requires authentication
        if (principal == null) {
            log.warn("Unauthenticated logout request rejected");
            return Mono.just(ResponseEntity.status(HttpStatus.UNAUTHORIZED).build());
        }

        if (principal instanceof JwtUser user) {
            String refreshToken = request != null ? request.getRefreshToken() : null;
            log.info("Logout request for user: {}", user.id());
            return authService.logout(Long.parseLong(user.id()), refreshToken)
                    .then(Mono.just(ResponseEntity.ok().<Void>build()));
        }

        // Unknown principal type - reject
        log.warn("Logout request with unknown principal type: {}", principal.getClass().getName());
        return Mono.just(ResponseEntity.status(HttpStatus.UNAUTHORIZED).build());
    }

    /**
     * Get current user endpoint
     *
     * <p>Returns information about the currently authenticated user
     *
     * @param principal current authenticated user from JWT
     * @return UserResponse with user details
     */
    @GetMapping("/me")
    public Mono<ResponseEntity<UserResponse>> getCurrentUser(
            @AuthenticationPrincipal Object principal
    ) {
        if (principal == null) {
            log.warn("Unauthenticated request to /me endpoint");
            return Mono.just(ResponseEntity.status(HttpStatus.UNAUTHORIZED).build());
        }

        if (principal instanceof JwtUser user) {
            log.debug("Get current user request for: {}", user.id());
            return authService.getCurrentUser(Long.parseLong(user.id()))
                    .map(ResponseEntity::ok)
                    .doOnError(e -> log.error("Failed to get current user: {}", e.getMessage()));
        }

        log.warn("Unknown principal type: {}", principal.getClass().getName());
        return Mono.just(ResponseEntity.status(HttpStatus.UNAUTHORIZED).build());
    }
}
