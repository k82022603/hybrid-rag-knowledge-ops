package com.knowledge.backend.domain.repository;

import java.util.UUID;

import org.springframework.data.r2dbc.repository.R2dbcRepository;
import org.springframework.stereotype.Repository;

import com.knowledge.backend.domain.entity.UserNotificationSetting;

import reactor.core.publisher.Mono;

/**
 * User Notification Setting Repository
 *
 * <p>R2DBC repository for UserNotificationSetting entity.
 */
@Repository
public interface UserNotificationSettingRepository extends R2dbcRepository<UserNotificationSetting, UUID> {

    /**
     * Find notification settings by user ID
     *
     * @param userId the user UUID
     * @return Mono of notification settings
     */
    Mono<UserNotificationSetting> findByUserId(UUID userId);
}
