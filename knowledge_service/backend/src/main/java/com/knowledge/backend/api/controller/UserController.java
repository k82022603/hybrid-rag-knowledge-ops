package com.knowledge.backend.api.controller;

import java.util.UUID;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.knowledge.backend.api.dto.user.PasswordChangeRequest;
import com.knowledge.backend.api.dto.user.UserProfileResponse;
import com.knowledge.backend.api.dto.user.UserUpdateRequest;
import com.knowledge.backend.security.JwtUser;
import com.knowledge.backend.service.UserService;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import reactor.core.publisher.Mono;

/**
 * User API Controller
 *
 * <p>Handles user profile operations for the knowledge domain.
 *
 * <p>Endpoints:
 * <ul>
 *   <li>GET  /api/v1/users/me               - Get my profile</li>
 *   <li>PUT  /api/v1/users/me               - Update my profile</li>
 *   <li>PUT  /api/v1/users/me/password       - Change my password</li>
 *   <li>GET  /api/v1/users/{id}             - Get user by ID (admin)</li>
 * </ul>
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/users")
@RequiredArgsConstructor
public class UserController {

    private final UserService userService;

    /**
     * Get current user profile
     *
     * @param principal authenticated user
     * @return Mono of UserProfileResponse
     */
    @GetMapping("/me")
    @PreAuthorize("hasAnyRole('USER', 'VIEWER', 'DEVELOPER', 'ADMIN')")
    public Mono<ResponseEntity<UserProfileResponse>> getMyProfile(
            @AuthenticationPrincipal Object principal
    ) {
        if (principal instanceof JwtUser user) {
            log.info("GET /users/me - user: {}", user.email());

            // Try to find by email in knowledge domain users table
            return userService.getUserByEmail(user.email())
                    .map(ResponseEntity::ok)
                    .defaultIfEmpty(ResponseEntity.status(HttpStatus.NOT_FOUND).build());
        }

        log.warn("GET /users/me - unauthenticated request");
        return Mono.just(ResponseEntity.status(HttpStatus.UNAUTHORIZED).build());
    }

    /**
     * Update current user profile
     *
     * @param request update data
     * @param principal authenticated user
     * @return Mono of updated UserProfileResponse
     */
    @PutMapping("/me")
    @PreAuthorize("hasAnyRole('USER', 'DEVELOPER', 'ADMIN')")
    public Mono<ResponseEntity<UserProfileResponse>> updateMyProfile(
            @Valid @RequestBody UserUpdateRequest request,
            @AuthenticationPrincipal Object principal
    ) {
        if (principal instanceof JwtUser user) {
            log.info("PUT /users/me - user: {}", user.email());

            return userService.getUserByEmail(user.email())
                    .flatMap(profile -> userService.updateProfile(
                            profile.getId(),
                            request.getDisplayName(),
                            request.getDepartment(),
                            request.getPosition()
                    ))
                    .map(ResponseEntity::ok);
        }

        return Mono.just(ResponseEntity.status(HttpStatus.UNAUTHORIZED).build());
    }

    /**
     * Change current user password
     *
     * @param request password change data
     * @param principal authenticated user
     * @return empty response with 200 OK
     */
    @PutMapping("/me/password")
    @PreAuthorize("hasAnyRole('USER', 'DEVELOPER', 'ADMIN')")
    public Mono<ResponseEntity<Void>> changePassword(
            @Valid @RequestBody PasswordChangeRequest request,
            @AuthenticationPrincipal Object principal
    ) {
        if (principal instanceof JwtUser user) {
            log.info("PUT /users/me/password - user: {}", user.email());

            return userService.getUserByEmail(user.email())
                    .flatMap(profile -> userService.changePassword(
                            profile.getId(),
                            request.getCurrentPassword(),
                            request.getNewPassword(),
                            request.getConfirmPassword()
                    ))
                    .then(Mono.just(ResponseEntity.ok().<Void>build()));
        }

        return Mono.just(ResponseEntity.status(HttpStatus.UNAUTHORIZED).build());
    }

    /**
     * Get user by ID (admin only)
     *
     * @param id the user UUID
     * @return Mono of UserProfileResponse
     */
    @GetMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public Mono<ResponseEntity<UserProfileResponse>> getUserById(@PathVariable UUID id) {
        log.info("GET /users/{}", id);

        return userService.getUserById(id)
                .map(ResponseEntity::ok);
    }
}
