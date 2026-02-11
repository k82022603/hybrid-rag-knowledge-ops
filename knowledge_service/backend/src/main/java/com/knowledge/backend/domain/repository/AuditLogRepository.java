package com.knowledge.backend.domain.repository;

import java.util.UUID;

import org.springframework.data.r2dbc.repository.Query;
import org.springframework.data.r2dbc.repository.R2dbcRepository;
import org.springframework.stereotype.Repository;

import com.knowledge.backend.domain.entity.AuditLog;

import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

/**
 * Audit Log Repository
 *
 * <p>R2DBC repository for AuditLog entity (audit_logs table).
 */
@Repository
public interface AuditLogRepository extends R2dbcRepository<AuditLog, UUID> {

    @Query("SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT :limit OFFSET :offset")
    Flux<AuditLog> findAllPaged(int limit, long offset);

    @Query("SELECT * FROM audit_logs WHERE user_id = :userId ORDER BY created_at DESC LIMIT :limit")
    Flux<AuditLog> findByUserId(UUID userId, int limit);

    @Query("SELECT * FROM audit_logs WHERE action = :action ORDER BY created_at DESC LIMIT :limit")
    Flux<AuditLog> findByAction(String action, int limit);

    @Query("SELECT * FROM audit_logs WHERE resource_type = :resourceType ORDER BY created_at DESC LIMIT :limit")
    Flux<AuditLog> findByResourceType(String resourceType, int limit);

    @Query("SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT :limit")
    Flux<AuditLog> findRecent(int limit);

    /**
     * Insert audit log (no user_id)
     */
    @Query("INSERT INTO audit_logs (action, resource_type, resource_id, ip_address, user_agent, request_path, status, error_message, duration_ms, created_at) " +
           "VALUES (:action, :resourceType, :resourceId, :ipAddress, :userAgent, :requestPath, :status, :errorMessage, :durationMs, :createdAt)")
    Mono<Void> insertLog(
            String action,
            String resourceType,
            UUID resourceId,
            String ipAddress,
            String userAgent,
            String requestPath,
            String status,
            String errorMessage,
            Integer durationMs,
            java.time.LocalDateTime createdAt
    );

    /**
     * Insert audit log with user_id
     */
    @Query("INSERT INTO audit_logs (user_id, action, resource_type, resource_id, ip_address, user_agent, request_path, status, error_message, duration_ms, created_at) " +
           "VALUES (:userId, :action, :resourceType, :resourceId, :ipAddress, :userAgent, :requestPath, :status, :errorMessage, :durationMs, :createdAt)")
    Mono<Void> insertLogWithUser(
            UUID userId,
            String action,
            String resourceType,
            UUID resourceId,
            String ipAddress,
            String userAgent,
            String requestPath,
            String status,
            String errorMessage,
            Integer durationMs,
            java.time.LocalDateTime createdAt
    );
}
