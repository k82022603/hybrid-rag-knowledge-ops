package com.knowledge.backend.domain.entity;

import java.time.LocalDateTime;
import java.util.UUID;

import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.Id;
import org.springframework.data.relational.core.mapping.Column;
import org.springframework.data.relational.core.mapping.Table;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Audit Log Entity
 *
 * <p>Audit trail for all system activities.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Table("audit_logs")
public class AuditLog {

    @Id
    private UUID id;

    @Column("user_id")
    private UUID userId;

    @Column("action")
    private String action;

    @Column("resource_type")
    private String resourceType;

    @Column("resource_id")
    private UUID resourceId;

    @Column("ip_address")
    private String ipAddress;

    @Column("user_agent")
    private String userAgent;

    @Column("request_path")
    private String requestPath;

    @Column("status")
    private String status;

    @Column("error_message")
    private String errorMessage;

    @Column("duration_ms")
    private Integer durationMs;

    @CreatedDate
    @Column("created_at")
    private LocalDateTime createdAt;
}
