package com.knowledge.backend.domain.repository;

import java.util.UUID;

import org.springframework.data.r2dbc.repository.Modifying;
import org.springframework.data.r2dbc.repository.Query;
import org.springframework.data.r2dbc.repository.R2dbcRepository;
import org.springframework.stereotype.Repository;

import com.knowledge.backend.domain.entity.KnowledgeUser;

import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

/**
 * Knowledge User Repository
 *
 * <p>R2DBC repository for KnowledgeUser entity (users table).
 * Used for knowledge domain user management.
 */
@Repository
public interface KnowledgeUserRepository extends R2dbcRepository<KnowledgeUser, UUID> {

    /**
     * Find user by username
     *
     * @param username the username
     * @return Mono of user
     */
    Mono<KnowledgeUser> findByUsername(String username);

    /**
     * Find user by email
     *
     * @param email the email
     * @return Mono of user
     */
    Mono<KnowledgeUser> findByEmail(String email);

    /**
     * Find all active users
     *
     * @return Flux of active users
     */
    @Query("SELECT * FROM users WHERE is_active = true ORDER BY created_at DESC")
    Flux<KnowledgeUser> findAllActive();

    /**
     * Find all users with pagination
     *
     * @param limit  page size
     * @param offset page offset
     * @return Flux of users
     */
    @Query("SELECT * FROM users ORDER BY created_at DESC LIMIT :limit OFFSET :offset")
    Flux<KnowledgeUser> findAllPaged(int limit, long offset);

    /**
     * Find users with search keyword and pagination
     *
     * @param search search keyword (matched against username, email, display_name, department)
     * @param limit  page size
     * @param offset page offset
     * @return Flux of matching users
     */
    @Query("SELECT * FROM users WHERE " +
           "(LOWER(username) LIKE LOWER(CONCAT('%', :search, '%')) " +
           "OR LOWER(email) LIKE LOWER(CONCAT('%', :search, '%')) " +
           "OR LOWER(display_name) LIKE LOWER(CONCAT('%', :search, '%')) " +
           "OR LOWER(department) LIKE LOWER(CONCAT('%', :search, '%'))) " +
           "ORDER BY created_at DESC LIMIT :limit OFFSET :offset")
    Flux<KnowledgeUser> findBySearchPaged(String search, int limit, long offset);

    /**
     * Find users filtered by active status with pagination
     *
     * @param isActive active status filter
     * @param limit    page size
     * @param offset   page offset
     * @return Flux of filtered users
     */
    @Query("SELECT * FROM users WHERE is_active = :isActive " +
           "ORDER BY created_at DESC LIMIT :limit OFFSET :offset")
    Flux<KnowledgeUser> findByIsActivePaged(boolean isActive, int limit, long offset);

    /**
     * Find users with search keyword and active status filter with pagination
     *
     * @param search   search keyword
     * @param isActive active status filter
     * @param limit    page size
     * @param offset   page offset
     * @return Flux of matching and filtered users
     */
    @Query("SELECT * FROM users WHERE " +
           "(LOWER(username) LIKE LOWER(CONCAT('%', :search, '%')) " +
           "OR LOWER(email) LIKE LOWER(CONCAT('%', :search, '%')) " +
           "OR LOWER(display_name) LIKE LOWER(CONCAT('%', :search, '%')) " +
           "OR LOWER(department) LIKE LOWER(CONCAT('%', :search, '%'))) " +
           "AND is_active = :isActive " +
           "ORDER BY created_at DESC LIMIT :limit OFFSET :offset")
    Flux<KnowledgeUser> findBySearchAndIsActivePaged(String search, boolean isActive, int limit, long offset);

    /**
     * Update user role
     *
     * @param userId the user UUID
     * @param role   new role
     * @return Mono of updated row count
     */
    @Modifying
    @Query("UPDATE users SET role = :role, updated_at = CURRENT_TIMESTAMP WHERE id = :userId")
    Mono<Integer> updateRole(UUID userId, String role);

    /**
     * Update user active status
     *
     * @param userId   the user UUID
     * @param isActive new active status
     * @return Mono of updated row count
     */
    @Modifying
    @Query("UPDATE users SET is_active = :isActive, updated_at = CURRENT_TIMESTAMP WHERE id = :userId")
    Mono<Integer> updateActiveStatus(UUID userId, boolean isActive);

    /**
     * Count total users
     *
     * @return total user count
     */
    @Query("SELECT COUNT(*) FROM users")
    Mono<Long> countTotal();

    /**
     * Count active users
     *
     * @return active user count
     */
    @Query("SELECT COUNT(*) FROM users WHERE is_active = true")
    Mono<Long> countActive();
}
