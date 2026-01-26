/**
 * Bookmark Service
 *
 * 북마크 관리 API 서비스
 * - 북마크 목록 조회
 * - 북마크 추가/삭제
 * - 폴더별 관리
 */
import api from './api';

/**
 * 북마크 폴더 타입
 */
export type BookmarkFolder = 'default' | 'important' | 'read-later';

/**
 * 북마크 인터페이스
 */
export interface Bookmark {
  id: string;
  documentId: string;
  documentTitle: string;
  documentType: string;
  folder: BookmarkFolder;
  note?: string;
  tags?: string[];
  createdAt: string;
  updatedAt: string;
}

/**
 * 북마크 생성 요청 인터페이스
 */
export interface CreateBookmarkRequest {
  documentId: string;
  folder?: BookmarkFolder;
  note?: string;
  tags?: string[];
}

/**
 * 북마크 목록 응답 인터페이스
 */
export interface BookmarkListResponse {
  bookmarks: Bookmark[];
  totalCount: number;
  page: number;
  pageSize: number;
}

/**
 * BookmarkService - 북마크 관리 API
 */
export const bookmarkService = {
  /**
   * 북마크 목록 조회
   */
  async getBookmarks(
    page = 1,
    pageSize = 20,
    folder?: BookmarkFolder,
    search?: string
  ): Promise<BookmarkListResponse> {
    const response = await api.get<BookmarkListResponse>('/bookmarks', {
      params: { page, pageSize, folder, search },
    });
    return response.data;
  },

  /**
   * 북마크 추가
   */
  async createBookmark(data: CreateBookmarkRequest): Promise<Bookmark> {
    const response = await api.post<Bookmark>('/bookmarks', data);
    return response.data;
  },

  /**
   * 북마크 삭제
   */
  async deleteBookmark(id: string): Promise<void> {
    await api.delete(`/bookmarks/${id}`);
  },

  /**
   * 북마크 수정 (폴더 이동, 메모 수정)
   */
  async updateBookmark(
    id: string,
    data: Partial<Pick<Bookmark, 'folder' | 'note' | 'tags'>>
  ): Promise<Bookmark> {
    const response = await api.put<Bookmark>(`/bookmarks/${id}`, data);
    return response.data;
  },

  /**
   * 폴더별 북마크 수 조회
   */
  async getFolderCounts(): Promise<Record<BookmarkFolder, number>> {
    const response = await api.get<Record<BookmarkFolder, number>>('/bookmarks/counts');
    return response.data;
  },
};

export default bookmarkService;
