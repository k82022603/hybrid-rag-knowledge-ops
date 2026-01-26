/**
 * Dashboard Service
 *
 * 대시보드 API 서비스
 * - 검색 통계
 * - 시스템 상태
 * - 최근 활동
 * - 문서 통계
 */
import api from './api';

/**
 * 대시보드 통계 인터페이스
 */
export interface DashboardStats {
  totalDocuments: number;
  totalSearches: number;
  activeUsers: number;
  indexingRate: number;
  documentsToday: number;
  searchesToday: number;
}

/**
 * 시스템 상태 인터페이스
 */
export interface SystemHealth {
  overall: 'healthy' | 'degraded' | 'unhealthy';
  services: ServiceHealth[];
}

export interface ServiceHealth {
  name: string;
  status: 'up' | 'down' | 'degraded';
  responseTime?: number;
  lastChecked: string;
}

/**
 * 최근 활동 인터페이스
 */
export interface RecentActivity {
  id: string;
  type: 'search' | 'upload' | 'download' | 'edit' | 'delete' | 'login';
  userName: string;
  description: string;
  resourceName?: string;
  timestamp: string;
}

/**
 * 검색 트렌드 인터페이스
 */
export interface SearchTrend {
  date: string;
  count: number;
}

/**
 * 인기 검색어 인터페이스
 */
export interface PopularQuery {
  query: string;
  count: number;
}

/**
 * 문서 유형 분포 인터페이스
 */
export interface DocumentTypeDistribution {
  type: string;
  count: number;
  percentage: number;
}

/**
 * DashboardService - 대시보드 API
 */
export const dashboardService = {
  /**
   * 대시보드 통계 조회
   */
  async getStats(): Promise<DashboardStats> {
    const response = await api.get<DashboardStats>('/dashboard/stats');
    return response.data;
  },

  /**
   * 시스템 상태 조회
   */
  async getSystemHealth(): Promise<SystemHealth> {
    const response = await api.get<SystemHealth>('/dashboard/health');
    return response.data;
  },

  /**
   * 최근 활동 조회
   */
  async getRecentActivities(limit = 10): Promise<RecentActivity[]> {
    const response = await api.get<RecentActivity[]>('/dashboard/activities', {
      params: { limit },
    });
    return response.data;
  },

  /**
   * 검색 트렌드 조회 (최근 7일)
   */
  async getSearchTrends(days = 7): Promise<SearchTrend[]> {
    const response = await api.get<SearchTrend[]>('/dashboard/search-trends', {
      params: { days },
    });
    return response.data;
  },

  /**
   * 인기 검색어 조회
   */
  async getPopularQueries(limit = 10): Promise<PopularQuery[]> {
    const response = await api.get<PopularQuery[]>('/dashboard/popular-queries', {
      params: { limit },
    });
    return response.data;
  },

  /**
   * 문서 유형 분포 조회
   */
  async getDocumentTypeDistribution(): Promise<DocumentTypeDistribution[]> {
    const response = await api.get<DocumentTypeDistribution[]>(
      '/dashboard/document-types'
    );
    return response.data;
  },
};

export default dashboardService;
