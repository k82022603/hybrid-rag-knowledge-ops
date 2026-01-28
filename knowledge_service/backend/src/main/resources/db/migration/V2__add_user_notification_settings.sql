-- V2: Add user_notification_settings table for user notification preferences
-- Part of STORY-047: Backend API 32 Implementation

CREATE TABLE IF NOT EXISTS user_notification_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    email_enabled BOOLEAN NOT NULL DEFAULT true,
    search_alert_enabled BOOLEAN NOT NULL DEFAULT false,
    document_update_enabled BOOLEAN NOT NULL DEFAULT true,
    system_notice_enabled BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_notification_settings_user_id
    ON user_notification_settings(user_id);

COMMENT ON TABLE user_notification_settings IS 'Per-user notification preferences';
COMMENT ON COLUMN user_notification_settings.email_enabled IS 'Enable email notifications';
COMMENT ON COLUMN user_notification_settings.search_alert_enabled IS 'Enable search result alerts';
COMMENT ON COLUMN user_notification_settings.document_update_enabled IS 'Enable document update notifications';
COMMENT ON COLUMN user_notification_settings.system_notice_enabled IS 'Enable system notice notifications';
