package com.knowledge.backend.service;

import java.time.LocalDateTime;
import java.util.UUID;

import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import com.knowledge.backend.api.dto.user.NotificationSettingResponse;
import com.knowledge.backend.api.dto.user.UserActivityResponse;
import com.knowledge.backend.api.dto.user.UserProfileResponse;
import com.knowledge.backend.domain.entity.UserNotificationSetting;
import com.knowledge.backend.domain.repository.AuditLogRepository;
import com.knowledge.backend.domain.repository.KnowledgeUserRepository;
import com.knowledge.backend.domain.repository.UserNotificationSettingRepository;
import com.knowledge.backend.exception.BadRequestException;
import com.knowledge.backend.exception.ResourceNotFoundException;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import reactor.core.publisher.Flux;
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
    private final AuditLogRepository auditLogRepository;
    private final UserNotificationSettingRepository notificationSettingRepository;
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

    // ========================================================================
    // Activity Operations
    // ========================================================================

    /**
     * Get user activities from audit logs
     *
     * @param userId the user UUID
     * @param limit max results
     * @return Flux of UserActivityResponse
     */
    public Flux<UserActivityResponse> getUserActivities(UUID userId, int limit) {
        log.debug("Getting activities for user: {}, limit: {}", userId, limit);

        return auditLogRepository.findByUserId(userId, limit)
                .map(auditLog -> UserActivityResponse.builder()
                        .id(auditLog.getId())
                        .action(auditLog.getAction())
                        .resourceType(auditLog.getResourceType())
                        .resourceId(auditLog.getResourceId())
                        .description(auditLog.getAction() + " on " + auditLog.getResourceType())
                        .createdAt(auditLog.getCreatedAt())
                        .build());
    }

    // ========================================================================
    // Notification Settings Operations
    // ========================================================================

    /**
     * Get user notification settings
     *
     * @param userId the user UUID
     * @return Mono of NotificationSettingResponse
     */
    public Mono<NotificationSettingResponse> getNotificationSettings(UUID userId) {
        log.debug("Getting notification settings for user: {}", userId);

        return notificationSettingRepository.findByUserId(userId)
                .map(NotificationSettingResponse::from);
    }

    /**
     * Update user notification settings
     *
     * @param userId              the user UUID
     * @param emailEnabled        email notifications enabled
     * @param searchAlertEnabled  search alert notifications enabled
     * @param documentUpdateEnabled document update notifications enabled
     * @param systemNoticeEnabled system notice notifications enabled
     * @return Mono of updated NotificationSettingResponse
     */
    public Mono<NotificationSettingResponse> updateNotificationSettings(
            UUID userId,
            Boolean emailEnabled,
            Boolean searchAlertEnabled,
            Boolean documentUpdateEnabled,
            Boolean systemNoticeEnabled
    ) {
        log.info("Updating notification settings for user: {}", userId);

        return notificationSettingRepository.findByUserId(userId)
                .switchIfEmpty(Mono.defer(() -> {
                    // Create default settings if not exists
                    UserNotificationSetting newSetting = UserNotificationSetting.builder()
                            .userId(userId)
                            .emailEnabled(true)
                            .searchAlertEnabled(false)
                            .documentUpdateEnabled(true)
                            .systemNoticeEnabled(true)
                            .createdAt(LocalDateTime.now())
                            .updatedAt(LocalDateTime.now())
                            .build();
                    return notificationSettingRepository.save(newSetting);
                }))
                .flatMap(setting -> {
                    if (emailEnabled != null) setting.setEmailEnabled(emailEnabled);
                    if (searchAlertEnabled != null) setting.setSearchAlertEnabled(searchAlertEnabled);
                    if (documentUpdateEnabled != null) setting.setDocumentUpdateEnabled(documentUpdateEnabled);
                    if (systemNoticeEnabled != null) setting.setSystemNoticeEnabled(systemNoticeEnabled);
                    setting.setUpdatedAt(LocalDateTime.now());
                    return notificationSettingRepository.save(setting);
                })
                .doOnSuccess(s -> log.info("Notification settings updated for user: {}", userId))
                .map(NotificationSettingResponse::from);
    }
}
