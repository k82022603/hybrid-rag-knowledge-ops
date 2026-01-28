package com.knowledge.backend.domain.entity;

import java.time.LocalDateTime;
import java.util.UUID;

import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.Id;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.relational.core.mapping.Column;
import org.springframework.data.relational.core.mapping.Table;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * User Notification Setting Entity
 *
 * <p>Stores per-user notification preferences.
 * Allows users to opt-in/out of various notification channels.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Table("user_notification_settings")
public class UserNotificationSetting {

    @Id
    private UUID id;

    @Column("user_id")
    private UUID userId;

    @Column("email_enabled")
    @Builder.Default
    private Boolean emailEnabled = true;

    @Column("search_alert_enabled")
    @Builder.Default
    private Boolean searchAlertEnabled = false;

    @Column("document_update_enabled")
    @Builder.Default
    private Boolean documentUpdateEnabled = true;

    @Column("system_notice_enabled")
    @Builder.Default
    private Boolean systemNoticeEnabled = true;

    @CreatedDate
    @Column("created_at")
    private LocalDateTime createdAt;

    @LastModifiedDate
    @Column("updated_at")
    private LocalDateTime updatedAt;
}
