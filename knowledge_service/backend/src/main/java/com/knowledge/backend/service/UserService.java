package com.knowledge.backend.service;

import java.util.UUID;

import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import com.knowledge.backend.api.dto.user.UserProfileResponse;
import com.knowledge.backend.domain.repository.KnowledgeUserRepository;
import com.knowledge.backend.exception.BadRequestException;
import com.knowledge.backend.exception.ResourceNotFoundException;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import reactor.core.publisher.Mono;

/**
 * User Service
 *
 * <p>Handles knowledge domain user profile operations.
 * Uses the 'users' table (not auth_users).
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class UserService {

    private final KnowledgeUserRepository knowledgeUserRepository;
    private final PasswordEncoder passwordEncoder = new BCryptPasswordEncoder();

    /**
     * Get user profile by ID
     *
     * @param userId the user UUID
     * @return Mono of UserProfileResponse
     */
    public Mono<UserProfileResponse> getUserById(UUID userId) {
        log.debug("Getting user profile: {}", userId);

        return knowledgeUserRepository.findById(userId)
                .switchIfEmpty(Mono.error(new ResourceNotFoundException("User", userId)))
                .map(UserProfileResponse::from);
    }

    /**
     * Get user profile by email
     *
     * @param email the user email
     * @return Mono of UserProfileResponse
     */
    public Mono<UserProfileResponse> getUserByEmail(String email) {
        log.debug("Getting user profile by email: {}", email);

        return knowledgeUserRepository.findByEmail(email)
                .switchIfEmpty(Mono.error(new ResourceNotFoundException("User not found with email: " + email)))
                .map(UserProfileResponse::from);
    }

    /**
     * Update user profile
     *
     * @param userId      the user UUID
     * @param displayName new display name (optional)
     * @param department  new department (optional)
     * @param position    new position (optional)
     * @return Mono of updated UserProfileResponse
     */
    public Mono<UserProfileResponse> updateProfile(UUID userId, String displayName, String department, String position) {
        log.info("Updating user profile: {}", userId);

        return knowledgeUserRepository.findById(userId)
                .switchIfEmpty(Mono.error(new ResourceNotFoundException("User", userId)))
                .flatMap(user -> {
                    if (displayName != null) user.setDisplayName(displayName);
                    if (department != null) user.setDepartment(department);
                    if (position != null) user.setPosition(position);
                    return knowledgeUserRepository.save(user);
                })
                .doOnSuccess(u -> log.info("User profile updated: {}", u.getId()))
                .map(UserProfileResponse::from);
    }

    /**
     * Change user password
     *
     * @param userId          the user UUID
     * @param currentPassword current password
     * @param newPassword     new password
     * @param confirmPassword confirm new password
     * @return Mono of void
     */
    public Mono<Void> changePassword(UUID userId, String currentPassword, String newPassword, String confirmPassword) {
        log.info("Changing password for user: {}", userId);

        if (!newPassword.equals(confirmPassword)) {
            return Mono.error(new BadRequestException("New password and confirmation do not match"));
        }

        return knowledgeUserRepository.findById(userId)
                .switchIfEmpty(Mono.error(new ResourceNotFoundException("User", userId)))
                .flatMap(user -> {
                    if (!passwordEncoder.matches(currentPassword, user.getPasswordHash())) {
                        return Mono.error(new BadRequestException("Current password is incorrect"));
                    }

                    user.setPasswordHash(passwordEncoder.encode(newPassword));
                    return knowledgeUserRepository.save(user);
                })
                .doOnSuccess(u -> log.info("Password changed for user: {}", u.getId()))
                .then();
    }
}
