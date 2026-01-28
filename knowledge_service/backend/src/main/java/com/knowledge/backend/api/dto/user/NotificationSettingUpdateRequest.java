package com.knowledge.backend.api.dto.user;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Notification Setting Update Request DTO
 *
 * <p>Request format for updating notification preferences.
 * All fields are optional; only non-null fields will be updated.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class NotificationSettingUpdateRequest {

    private Boolean emailEnabled;
    private Boolean searchAlertEnabled;
    private Boolean documentUpdateEnabled;
    private Boolean systemNoticeEnabled;
}
