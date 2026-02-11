/**
 * Admin Service
 *
 * 관리자 API 서비스
 * - 사용자 관리
 * - 시스템 설정
 * - 감사 로그
 * - 시스템 통계
 */
import api from './api';
import type { User } from '@/types';

/**
 * 사용자 목록 응답 인터페이스
 */
export interface AdminUserListResponse {
  users: AdminUser[];
  totalCount: number;
  page: number;
  pageSize: number;
}

/**
 * 관리자용 사용자 인터페이스
 */
export interface AdminUser extends User {
  status: 'active' | 'inactive' | 'locked';
  lastLogin?: string;
  createdAt: string;
  updatedAt: string;
}

/**
 * 사용자 역할 변경 요청
 */
export interface UpdateUserRolesRequest {
  userId: string;
  roles: string[];
}

/**
 * 시스템 설정 인터페이스
 */
export interface SystemSettings {
  chunkSize: number;
  chunkOverlap: number;
  embeddingModel: string;
  llmModel: string;
  maxUploadSize: number;
  supportedFormats: string[];
  indexingEnabled: boolean;
  maintenanceMode: boolean;
}

/**
 * 감사 로그 인터페이스
 */
export interface AuditLog {
  id: string;
  userId: string;
  userName: string;
  action: string;
  resource: string;
  resourceId?: string;
  details?: string;
  ipAddress: string;
  timestamp: string;
}

/**
 * 감사 로그 목록 응답
 */
export interface AuditLogListResponse {
  logs: AuditLog[];
  totalCount: number;
  page: number;
  pageSize: number;
}

/**
 * 시스템 통계 인터페이스
 */
export interface SystemStats {
  totalDocuments: number;
  totalUsers: number;
  totalSearches: number;
  totalSearchesToday: number;
  activeUsers: number;
  storageUsed: string;
  indexingRate: number;
  avgResponseTime: number;
}

/**
 * AdminService - 관리자 API
 */
export const adminService = {
  /**
   * 사용자 목록 조회
   */
  async getUsers(
    page = 1,
    pageSize = 20,
    search?: string,
    status?: string
  ): Promise<AdminUserListResponse> {
    const response = await api.get<AdminUserListResponse>('/admin/users', {
      params: { page, pageSize, search, status },
    });
    return response.data;
  },

  /**
   * 사용자 역할 변경
   */
  async updateUserRoles(data: UpdateUserRolesRequest): Promise<AdminUser> {
    const response = await api.put<AdminUser>(
      `/admin/users/${data.userId}/roles`,
      { roles: data.roles }
    );
    return response.data;
  },

  /**
   * 사용자 비활성화/활성화
   */
  async toggleUserStatus(
    userId: string,
    status: 'active' | 'inactive'
  ): Promise<AdminUser> {
    const response = await api.put<AdminUser>(
      `/admin/users/${userId}/status`,
      { status }
    );
    return response.data;
  },

  /**
   * 시스템 설정 조회
   */
  async getSystemSettings(): Promise<SystemSettings> {
    const response = await api.get<SystemSettings>('/admin/system');
    return response.data;
  },

  /**
   * 시스템 설정 업데이트
   */
  async updateSystemSettings(
    data: Partial<SystemSettings>
  ): Promise<SystemSettings> {
    const response = await api.put<SystemSettings>('/admin/system', data);
    return response.data;
  },

  /**
   * 감사 로그 조회
   */
  async getAuditLogs(
    page = 1,
    pageSize = 50,
    filters?: {
      userId?: string;
      action?: string;
      dateFrom?: string;
      dateTo?: string;
    }
  ): Promise<AuditLogListResponse> {
    const response = await api.get<AuditLogListResponse>('/admin/audit-logs', {
      params: { page, pageSize, ...filters },
    });
    return response.data;
  },

  /**
   * 시스템 통계 조회
   */
  async getSystemStats(): Promise<SystemStats> {
    const response = await api.get<SystemStats>('/admin/stats');
    return response.data;
  },

  // ============================================================
  // Cache Management (AI Service)
  // ============================================================

  /**
   * 캐시 통계 조회
   */
  async getCacheStats(): Promise<CacheStats> {
    const response = await api.get<CacheStats>('/cache/stats');
    return response.data;
  },

  /**
   * 캐시 전체 삭제
   */
  async clearCache(): Promise<CacheClearResult> {
    const response = await api.delete<CacheClearResult>('/cache/clear');
    return response.data;
  },

  /**
   * 패턴 기반 캐시 무효화
   */
  async invalidateCache(pattern?: string): Promise<CacheInvalidateResult> {
    const response = await api.delete<CacheInvalidateResult>('/cache/invalidate', {
      params: pattern ? { pattern } : {},
    });
    return response.data;
  },

  /**
   * 캐시 상태 확인
   */
  async getCacheStatus(): Promise<CacheStatus> {
    const response = await api.get<CacheStatus>('/cache/status');
    return response.data;
  },

  /**
   * 캐시 통계 초기화
   */
  async resetCacheStats(): Promise<{ success: boolean; message: string }> {
    const response = await api.post<{ success: boolean; message: string }>('/cache/stats/reset');
    return response.data;
  },
};

/**
 * 캐시 통계 인터페이스
 */
export interface CacheStats {
  hits: number;
  misses: number;
  total_requests: number;
  hit_rate: number;
  miss_rate: number;
  size: number;
  max_size: number;
  backend: string;
  last_reset: string;
  enabled: boolean;
  ttl_seconds: number;
}

/**
 * 캐시 삭제 결과
 */
export interface CacheClearResult {
  deleted_count: number;
  message: string;
}

/**
 * 캐시 무효화 결과
 */
export interface CacheInvalidateResult {
  deleted_count: number;
  pattern: string | null;
  message: string;
}

/**
 * 캐시 상태
 */
export interface CacheStatus {
  enabled: boolean;
  backend: string;
  status: string;
  message: string;
}

export default adminService;
