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
 * Backend UserProfileResponse 원본 인터페이스
 */
interface BackendUserProfile {
  id: string;
  email: string;
  displayName: string;
  role: string;
  isActive: boolean;
  lastLoginAt?: string;
  createdAt: string;
  updatedAt: string;
}

/**
 * 관리자용 사용자 인터페이스
 */
export interface AdminUser extends User {
  role: string;
  status: 'active' | 'inactive';
  lastLogin?: string;
  createdAt: string;
  updatedAt: string;
}

/**
 * 사용자 역할 변경 요청
 */
export interface UpdateUserRoleRequest {
  userId: string;
  role: string;
}

/**
 * Backend 응답을 Frontend AdminUser로 매핑
 */
function mapBackendUser(raw: BackendUserProfile): AdminUser {
  return {
    id: raw.id,
    username: raw.email,
    email: raw.email,
    name: raw.displayName,
    roles: [raw.role],
    role: raw.role,
    status: raw.isActive ? 'active' : 'inactive',
    lastLogin: raw.lastLoginAt,
    createdAt: raw.createdAt,
    updatedAt: raw.updatedAt,
  };
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
 *
 * Backend: AuditLogResponse DTO (Flux<AuditLogResponse> = plain array)
 * Fields: id, userId, action, resourceType, resourceId, ipAddress,
 *         requestPath, status, errorMessage, durationMs, createdAt
 */
export interface AuditLog {
  id: string;
  userId: string | null;
  action: string;
  resourceType: string;
  resourceId?: string | null;
  ipAddress: string;
  requestPath: string;
  status: string;
  errorMessage?: string | null;
  durationMs: number | null;
  createdAt: string;
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
   *
   * Backend: GET /api/v1/admin/users?page=0&size=20&search=...&isActive=true
   * Returns: UserProfileResponse[] (plain array)
   * Pagination: 0-based page
   */
  async getUsers(
    page = 1,
    pageSize = 20,
    search?: string,
    status?: string
  ): Promise<AdminUser[]> {
    // Convert status string to isActive boolean for Backend
    let isActive: boolean | undefined;
    if (status === 'active') isActive = true;
    else if (status === 'inactive') isActive = false;

    const response = await api.get<BackendUserProfile[]>('/admin/users', {
      params: {
        page: page - 1,  // Frontend 1-based → Backend 0-based
        size: pageSize,
        search: search || undefined,
        isActive,
      },
    });

    const raw = Array.isArray(response.data) ? response.data : [];
    return raw.map(mapBackendUser);
  },

  /**
   * 사용자 역할 변경
   *
   * Backend: PUT /api/v1/admin/users/{userId}/roles
   * Body: { role: "admin" } (singular)
   */
  async updateUserRole(data: UpdateUserRoleRequest): Promise<AdminUser> {
    const response = await api.put<BackendUserProfile>(
      `/admin/users/${data.userId}/roles`,
      { role: data.role }
    );
    return mapBackendUser(response.data);
  },

  /**
   * 사용자 비활성화/활성화
   *
   * Backend: PUT /api/v1/admin/users/{userId}/status
   * Body: { isActive: true/false }
   */
  async toggleUserStatus(
    userId: string,
    active: boolean
  ): Promise<AdminUser> {
    const response = await api.put<BackendUserProfile>(
      `/admin/users/${userId}/status`,
      { isActive: active }
    );
    return mapBackendUser(response.data);
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
   *
   * Backend: GET /api/v1/admin/audit-logs?page=0&size=50
   * Returns: AuditLog[] (plain array, no wrapper)
   * Pagination: 0-based page, param name is "size" (not "pageSize")
   */
  async getAuditLogs(
    page = 0,
    size = 50
  ): Promise<AuditLog[]> {
    const response = await api.get<AuditLog[]>('/admin/audit-logs', {
      params: { page, size },
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
