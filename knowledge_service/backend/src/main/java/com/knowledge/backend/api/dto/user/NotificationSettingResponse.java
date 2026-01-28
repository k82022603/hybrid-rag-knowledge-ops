package com.knowledge.backend.api.dto.user;

import java.time.LocalDateTime;
import java.util.UUID;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.knowledge.backend.domain.entity.UserNotificationSetting;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Notification Setting Response DTO
 *
 * <p>Response format for user notification preferences.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class NotificationSettingResponse {

    private UUID id;
    private Boolean emailEnabled;
    private Boolean searchAlertEnabled;
    private Boolean documentUpdateEnabled;
    private Boolean systemNoticeEnabled;
    private LocalDateTime updatedAt;

    /**
     * Convert UserNotificationSetting entity to NotificationSettingResponse DTO
     *
     * @param setting the UserNotificationSetting entity
     * @return NotificationSettingResponse DTO
     */
    public static NotificationSettingResponse from(UserNotificationSetting setting) {
        return NotificationSettingResponse.builder()
                .id(setting.getId())
                .emailEnabled(setting.getEmailEnabled())
                .searchAlertEnabled(setting.getSearchAlertEnabled())
                .documentUpdateEnabled(setting.getDocumentUpdateEnabled())
                .systemNoticeEnabled(setting.getSystemNoticeEnabled())
                .updatedAt(setting.getUpdatedAt())
                .build();
    }

    /**
     * Create default notification settings response
     *
     * @return default NotificationSettingResponse
     */
    public static NotificationSettingResponse defaultSettings() {
        return NotificationSettingResponse.builder()
                .emailEnabled(true)
                .searchAlertEnabled(false)
                .documentUpdateEnabled(true)
                .systemNoticeEnabled(true)
                .build();
    }
}
