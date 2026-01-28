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
 * User Activity Entity
 *
 * <p>Tracks user activity within the knowledge platform.
 * Activities include searches, document views, bookmarks, etc.
 * Maps to 'audit_logs' table filtered by user_id.
 *
 * <p>Note: This is a read-only projection from audit_logs for user-facing activity feed.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Table("audit_logs")
public class UserActivity {

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

    @Column("request_path")
    private String requestPath;

    @Column("status")
    private String status;

    @Column("duration_ms")
    private Integer durationMs;

    @CreatedDate
    @Column("created_at")
    private LocalDateTime createdAt;
}
