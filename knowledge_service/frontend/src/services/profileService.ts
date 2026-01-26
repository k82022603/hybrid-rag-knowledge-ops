/**
 * Profile Service
 *
 * 사용자 프로필 API 서비스
 * - 프로필 조회/수정
 * - 비밀번호 변경
 * - 활동 이력 조회
 * - 알림 설정
 */
import api from './api';
import type { User } from '@/types';

/**
 * 프로필 수정 요청 인터페이스
 */
export interface UpdateProfileRequest {
  name?: string;
  firstName?: string;
  lastName?: string;
  department?: string;
}

/**
 * 비밀번호 변경 요청 인터페이스
 */
export interface ChangePasswordRequest {
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
}

/**
 * 활동 이력 인터페이스
 */
export interface ActivityLog {
  id: string;
  type: 'search' | 'upload' | 'download' | 'edit' | 'delete' | 'login';
  description: string;
  resourceId?: string;
  resourceName?: string;
  timestamp: string;
}

/**
 * 활동 이력 목록 응답
 */
export interface ActivityLogListResponse {
  activities: ActivityLog[];
  totalCount: number;
  page: number;
  pageSize: number;
}

/**
 * 알림 설정 인터페이스
 */
export interface NotificationSettings {
  emailNotifications: boolean;
  searchAlerts: boolean;
  documentUpdates: boolean;
  systemNotifications: boolean;
  weeklyDigest: boolean;
}

/**
 * ProfileService - 프로필 관리 API
 */
export const profileService = {
  /**
   * 현재 사용자 프로필 조회
   */
  async getProfile(): Promise<User> {
    const response = await api.get<User>('/users/me');
    return response.data;
  },

  /**
   * 프로필 수정
   */
  async updateProfile(data: UpdateProfileRequest): Promise<User> {
    const response = await api.put<User>('/users/me', data);
    return response.data;
  },

  /**
   * 비밀번호 변경
   */
  async changePassword(data: ChangePasswordRequest): Promise<void> {
    await api.put('/users/me/password', data);
  },

  /**
   * 활동 이력 조회
   */
  async getActivityHistory(
    page = 1,
    pageSize = 20,
    type?: string
  ): Promise<ActivityLogListResponse> {
    const response = await api.get<ActivityLogListResponse>('/users/me/activities', {
      params: { page, pageSize, type },
    });
    return response.data;
  },

  /**
   * 알림 설정 조회
   */
  async getNotificationSettings(): Promise<NotificationSettings> {
    const response = await api.get<NotificationSettings>('/users/me/notifications');
    return response.data;
  },

  /**
   * 알림 설정 업데이트
   */
  async updateNotificationSettings(
    data: Partial<NotificationSettings>
  ): Promise<NotificationSettings> {
    const response = await api.put<NotificationSettings>(
      '/users/me/notifications',
      data
    );
    return response.data;
  },
};

export default profileService;
