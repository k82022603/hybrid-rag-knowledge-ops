package com.knowledge.backend.domain.repository;

import java.util.UUID;

import org.springframework.data.r2dbc.repository.Query;
import org.springframework.data.r2dbc.repository.R2dbcRepository;
import org.springframework.stereotype.Repository;

import com.knowledge.backend.domain.entity.AuditLog;

import reactor.core.publisher.Flux;

/**
 * Audit Log Repository
 *
 * <p>R2DBC repository for AuditLog entity (audit_logs table).
 */
@Repository
public interface AuditLogRepository extends R2dbcRepository<AuditLog, UUID> {

    /**
     * Find audit logs with pagination
     *
     * @param limit  page size
     * @param offset page offset
     * @return Flux of audit log entries
     */
    @Query("SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT :limit OFFSET :offset")
    Flux<AuditLog> findAllPaged(int limit, long offset);

    /**
     * Find audit logs by user ID
     *
     * @param userId the user UUID
     * @param limit  max results
     * @return Flux of audit log entries
     */
    @Query("SELECT * FROM audit_logs WHERE user_id = :userId ORDER BY created_at DESC LIMIT :limit")
    Flux<AuditLog> findByUserId(UUID userId, int limit);

    /**
     * Find audit logs by action type
     *
     * @param action the action type
     * @param limit  max results
     * @return Flux of audit log entries
     */
    @Query("SELECT * FROM audit_logs WHERE action = :action ORDER BY created_at DESC LIMIT :limit")
    Flux<AuditLog> findByAction(String action, int limit);

    /**
     * Find audit logs by resource type
     *
     * @param resourceType the resource type
     * @param limit        max results
     * @return Flux of audit log entries
     */
    @Query("SELECT * FROM audit_logs WHERE resource_type = :resourceType ORDER BY created_at DESC LIMIT :limit")
    Flux<AuditLog> findByResourceType(String resourceType, int limit);

    /**
     * Find recent audit logs
     *
     * @param limit max results
     * @return Flux of recent audit logs
     */
    @Query("SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT :limit")
    Flux<AuditLog> findRecent(int limit);
}
