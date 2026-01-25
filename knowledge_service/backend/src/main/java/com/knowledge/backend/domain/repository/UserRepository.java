package com.knowledge.backend.domain.repository;

import org.springframework.data.r2dbc.repository.Modifying;
import org.springframework.data.r2dbc.repository.Query;
import org.springframework.data.r2dbc.repository.R2dbcRepository;
import org.springframework.stereotype.Repository;

import com.knowledge.backend.domain.entity.User;

import reactor.core.publisher.Mono;

/**
 * User Repository
 *
 * <p>R2DBC repository for User entity (auth_users table)
 */
@Repository
public interface UserRepository extends R2dbcRepository<User, Long> {

    /**
     * Find user by email
     *
     * @param email user email
     * @return Mono of User
     */
    Mono<User> findByEmail(String email);

    /**
     * Find user by username
     *
     * @param username user username
     * @return Mono of User
     */
    Mono<User> findByUsername(String username);

    /**
     * Check if user exists by email
     *
     * @param email user email
     * @return Mono of Boolean
     */
    Mono<Boolean> existsByEmail(String email);

    /**
     * Update last login time
     *
     * @param userId user ID
     * @param lastLoginAt last login timestamp
     * @return Mono of updated rows
     */
    @Modifying
    @Query("UPDATE auth_users SET last_login_at = :lastLoginAt WHERE id = :userId")
    Mono<Integer> updateLastLoginAt(Long userId, java.time.LocalDateTime lastLoginAt);

    /**
     * Update failed login attempts
     *
     * @param userId user ID
     * @param failedAttempts number of failed attempts
     * @return Mono of updated rows
     */
    @Modifying
    @Query("UPDATE auth_users SET failed_login_attempts = :failedAttempts WHERE id = :userId")
    Mono<Integer> updateFailedLoginAttempts(Long userId, Integer failedAttempts);

    /**
     * Lock user account
     *
     * @param userId user ID
     * @param isLocked locked status
     * @param lockedUntil lock expiry time
     * @return Mono of updated rows
     */
    @Modifying
    @Query("UPDATE auth_users SET is_locked = :isLocked, locked_until = :lockedUntil WHERE id = :userId")
    Mono<Integer> lockUser(Long userId, Boolean isLocked, java.time.LocalDateTime lockedUntil);

    /**
     * Reset login attempts and unlock
     *
     * @param userId user ID
     * @return Mono of updated rows
     */
    @Modifying
    @Query("UPDATE auth_users SET failed_login_attempts = 0, is_locked = false, locked_until = null WHERE id = :userId")
    Mono<Integer> resetLoginAttempts(Long userId);
}
