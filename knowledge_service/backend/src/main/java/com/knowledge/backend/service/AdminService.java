package com.knowledge.backend.service;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

import org.springframework.stereotype.Service;

import com.knowledge.backend.api.dto.admin.AuditLogResponse;
import com.knowledge.backend.api.dto.admin.SystemConfigResponse;
import com.knowledge.backend.api.dto.user.UserProfileResponse;
import com.knowledge.backend.domain.entity.SystemConfig;
import com.knowledge.backend.domain.repository.AuditLogRepository;
import com.knowledge.backend.domain.repository.DocumentRepository;
import com.knowledge.backend.domain.repository.KnowledgeUserRepository;
import com.knowledge.backend.domain.repository.SearchHistoryRepository;
import com.knowledge.backend.domain.repository.SystemConfigRepository;
import com.knowledge.backend.exception.ResourceNotFoundException;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

/**
 * Admin Service
 *
 * <p>Handles administrative operations: user management, system config, audit logs.
 * All operations require ADMIN role verification at the controller level.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class AdminService {

    private final KnowledgeUserRepository knowledgeUserRepository;
    private final SystemConfigRepository systemConfigRepository;
    private final AuditLogRepository auditLogRepository;
    private final DocumentRepository documentRepository;
    private final SearchHistoryRepository searchHistoryRepository;

    // ========================================================================
    // User Management
    // ========================================================================

    /**
     * Get paginated user list with optional search and status filter
     *
     * @param page     page number (0-based)
     * @param size     page size
     * @param search   optional search keyword (username, email, displayName, department)
     * @param isActive optional active status filter
     * @return Flux of UserProfileResponse
     */
    public Flux<UserProfileResponse> getUsers(int page, int size, String search, Boolean isActive) {
        log.debug("Getting users - page: {}, size: {}, search: {}, isActive: {}", page, size, search, isActive);
        long offset = (long) page * size;

        boolean hasSearch = search != null && !search.isBlank();
        boolean hasStatus = isActive != null;

        Flux<com.knowledge.backend.domain.entity.KnowledgeUser> users;
        if (hasSearch && hasStatus) {
            users = knowledgeUserRepository.findBySearchAndIsActivePaged(search.trim(), isActive, size, offset);
        } else if (hasSearch) {
            users = knowledgeUserRepository.findBySearchPaged(search.trim(), size, offset);
        } else if (hasStatus) {
            users = knowledgeUserRepository.findByIsActivePaged(isActive, size, offset);
        } else {
            users = knowledgeUserRepository.findAllPaged(size, offset);
        }

        return users.map(UserProfileResponse::from);
    }

    /**
     * Update user role
     *
     * @param userId the user UUID
     * @param role   the new role
     * @return Mono of updated UserProfileResponse
     */
    public Mono<UserProfileResponse> updateUserRole(UUID userId, String role) {
        log.info("Updating user role: userId={}, role={}", userId, role);

        return knowledgeUserRepository.findById(userId)
                .switchIfEmpty(Mono.error(new ResourceNotFoundException("User", userId)))
                .flatMap(user -> {
                    user.setRole(role);
                    return knowledgeUserRepository.save(user);
                })
                .doOnSuccess(u -> log.info("User role updated: id={}, role={}", u.getId(), u.getRole()))
                .map(UserProfileResponse::from);
    }

    /**
     * Update user active status
     *
     * @param userId   the user UUID
     * @param isActive new active status
     * @return Mono of updated UserProfileResponse
     */
    public Mono<UserProfileResponse> updateUserStatus(UUID userId, boolean isActive) {
        log.info("Updating user status: userId={}, isActive={}", userId, isActive);

        return knowledgeUserRepository.findById(userId)
                .switchIfEmpty(Mono.error(new ResourceNotFoundException("User", userId)))
                .flatMap(user -> {
                    user.setIsActive(isActive);
                    return knowledgeUserRepository.save(user);
                })
                .doOnSuccess(u -> log.info("User status updated: id={}, active={}", u.getId(), u.getIsActive()))
                .map(UserProfileResponse::from);
    }

    // ========================================================================
    // System Configuration
    // ========================================================================

    /**
     * Get all system configurations
     *
     * @return Flux of SystemConfigResponse
     */
    public Flux<SystemConfigResponse> getSystemConfig() {
        log.debug("Getting system configurations");

        return systemConfigRepository.findAll()
                .map(SystemConfigResponse::from);
    }

    /**
     * Update system configurations
     *
     * @param configs   key-value pairs to update
     * @param updatedBy user UUID performing the update
     * @return Flux of updated SystemConfigResponse
     */
    public Flux<SystemConfigResponse> updateSystemConfig(Map<String, String> configs, UUID updatedBy) {
        log.info("Updating system config: {} entries, by user: {}", configs.size(), updatedBy);

        return Flux.fromIterable(configs.entrySet())
                .flatMap(entry ->
                    systemConfigRepository.findById(entry.getKey())
                        .switchIfEmpty(Mono.just(SystemConfig.builder()
                                .key(entry.getKey())
                                .build()))
                        .flatMap(config -> {
                            config.setValue(entry.getValue());
                            config.setUpdatedBy(updatedBy);
                            config.setUpdatedAt(LocalDateTime.now());
                            return systemConfigRepository.save(config);
                        })
                )
                .doOnComplete(() -> log.info("System config updated successfully"))
                .map(SystemConfigResponse::from);
    }

    // ========================================================================
    // System Statistics
    // ========================================================================

    /**
     * Get system statistics (document count, user count, search count, etc.)
     *
     * @return Mono of stats map
     */
    public Mono<Map<String, Object>> getSystemStats() {
        log.debug("Getting system statistics");

        Mono<Long> totalDocs = documentRepository.countTotal().defaultIfEmpty(0L);
        Mono<Long> totalUsers = knowledgeUserRepository.countTotal().defaultIfEmpty(0L);
        Mono<Long> activeUsers = knowledgeUserRepository.countActive().defaultIfEmpty(0L);
        Mono<Long> totalSearches = searchHistoryRepository.countTotal().defaultIfEmpty(0L);

        return Mono.zip(totalDocs, totalUsers, activeUsers, totalSearches)
                .map(tuple -> {
                    Map<String, Object> stats = new HashMap<>();
                    stats.put("totalDocuments", tuple.getT1());
                    stats.put("totalUsers", tuple.getT2());
                    stats.put("activeUsers", tuple.getT3());
                    stats.put("totalSearches", tuple.getT4());
                    stats.put("totalSearchesToday", 0);
                    stats.put("storageUsed", "N/A");
                    stats.put("indexingRate", 100);
                    stats.put("avgResponseTime", 0);
                    return stats;
                });
    }

    // ========================================================================
    // Audit Logs
    // ========================================================================

    /**
     * Get paginated audit logs
     *
     * @param page page number (0-based)
     * @param size page size
     * @return Flux of AuditLogResponse
     */
    public Flux<AuditLogResponse> getAuditLogs(int page, int size) {
        log.debug("Getting audit logs - page: {}, size: {}", page, size);
        long offset = (long) page * size;

        return auditLogRepository.findAllPaged(size, offset)
                .map(AuditLogResponse::from);
    }
}
