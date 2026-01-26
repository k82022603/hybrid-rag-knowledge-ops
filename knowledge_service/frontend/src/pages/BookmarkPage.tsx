/**
 * BookmarkPage - 북마크 관리 페이지
 *
 * 북마크한 문서 목록 표시 (그리드/리스트 뷰)
 * 폴더별 분류 (기본, 중요, 나중에 읽기)
 * 북마크 추가/삭제, 검색 필터링
 */
import React, { useState, useCallback, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  BookmarkIcon,
  StarIcon,
  ClockIcon,
  FolderIcon,
  MagnifyingGlassIcon,
  Squares2X2Icon,
  ListBulletIcon,
  TrashIcon,
  DocumentTextIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
  FolderOpenIcon,
} from '@heroicons/react/24/outline';
import { StarIcon as StarIconSolid } from '@heroicons/react/24/solid';
import { Dialog, Transition } from '@headlessui/react';
import { Fragment } from 'react';
import { bookmarkService, type Bookmark, type BookmarkFolder } from '@/services/bookmarkService';

/**
 * 폴더 정보 매핑
 */
const FOLDER_CONFIG: Record<BookmarkFolder, { label: string; icon: React.ReactNode; color: string }> = {
  default: {
    label: 'All Bookmarks',
    icon: <BookmarkIcon className="h-5 w-5" />,
    color: 'text-primary-600 bg-primary-50 dark:text-primary-400 dark:bg-primary-900/30',
  },
  important: {
    label: 'Important',
    icon: <StarIcon className="h-5 w-5" />,
    color: 'text-warning-600 bg-warning-50 dark:text-warning-400 dark:bg-warning-900/30',
  },
  'read-later': {
    label: 'Read Later',
    icon: <ClockIcon className="h-5 w-5" />,
    color: 'text-accent-600 bg-accent-50 dark:text-accent-400 dark:bg-accent-900/30',
  },
};

/**
 * BookmarkCard 컴포넌트 - 그리드 뷰용 카드
 */
const BookmarkCard: React.FC<{
  bookmark: Bookmark;
  onDelete: (id: string) => void;
  onMove: (id: string, folder: BookmarkFolder) => void;
}> = ({ bookmark, onDelete, onMove }) => {
  return (
    <div
      className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 hover:shadow-soft transition-shadow duration-200 group"
      data-testid={`bookmark-card-${bookmark.id}`}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <DocumentTextIcon className="h-5 w-5 text-gray-400 flex-shrink-0" />
          <span className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
            {bookmark.documentType}
          </span>
        </div>
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={() => onMove(bookmark.id, bookmark.folder === 'important' ? 'default' : 'important')}
            className="p-1.5 rounded-lg hover:bg-warning-50 dark:hover:bg-warning-900/30 transition-colors"
            aria-label={bookmark.folder === 'important' ? 'Remove from important' : 'Mark as important'}
            title={bookmark.folder === 'important' ? 'Remove from important' : 'Mark as important'}
          >
            {bookmark.folder === 'important' ? (
              <StarIconSolid className="h-4 w-4 text-warning-500" />
            ) : (
              <StarIcon className="h-4 w-4 text-gray-400 hover:text-warning-500" />
            )}
          </button>
          <button
            onClick={() => onDelete(bookmark.id)}
            className="p-1.5 rounded-lg hover:bg-error-50 dark:hover:bg-error-900/30 transition-colors"
            aria-label="Delete bookmark"
            title="Delete bookmark"
          >
            <TrashIcon className="h-4 w-4 text-gray-400 hover:text-error-500" />
          </button>
        </div>
      </div>

      {/* Title */}
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2 line-clamp-2">
        {bookmark.documentTitle}
      </h3>

      {/* Note */}
      {bookmark.note && (
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-3 line-clamp-2">
          {bookmark.note}
        </p>
      )}

      {/* Tags */}
      {bookmark.tags && bookmark.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {bookmark.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center px-2 py-0.5 rounded-full text-2xs font-medium bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300"
            >
              {tag}
            </span>
          ))}
          {bookmark.tags.length > 3 && (
            <span className="text-2xs text-gray-400">+{bookmark.tags.length - 3}</span>
          )}
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between pt-3 border-t border-gray-100 dark:border-gray-700">
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-2xs font-medium ${FOLDER_CONFIG[bookmark.folder].color}`}>
          {FOLDER_CONFIG[bookmark.folder].icon}
          {FOLDER_CONFIG[bookmark.folder].label}
        </span>
        <span className="text-2xs text-gray-400">
          {new Date(bookmark.createdAt).toLocaleDateString('ko-KR')}
        </span>
      </div>
    </div>
  );
};

/**
 * BookmarkListItem 컴포넌트 - 리스트 뷰용 행
 */
const BookmarkListItem: React.FC<{
  bookmark: Bookmark;
  onDelete: (id: string) => void;
  onMove: (id: string, folder: BookmarkFolder) => void;
}> = ({ bookmark, onDelete, onMove }) => {
  return (
    <div
      className="flex items-center gap-4 px-4 py-3 bg-white dark:bg-gray-800 border-b border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors group"
      data-testid={`bookmark-list-item-${bookmark.id}`}
    >
      <DocumentTextIcon className="h-5 w-5 text-gray-400 flex-shrink-0" />

      <div className="flex-1 min-w-0">
        <h3 className="text-sm font-medium text-gray-900 dark:text-white truncate">
          {bookmark.documentTitle}
        </h3>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-xs text-gray-500 dark:text-gray-400">{bookmark.documentType}</span>
          {bookmark.note && (
            <>
              <span className="text-gray-300 dark:text-gray-600">|</span>
              <span className="text-xs text-gray-400 truncate">{bookmark.note}</span>
            </>
          )}
        </div>
      </div>

      <span className={`hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-2xs font-medium ${FOLDER_CONFIG[bookmark.folder].color}`}>
        {FOLDER_CONFIG[bookmark.folder].label}
      </span>

      <span className="hidden md:inline text-xs text-gray-400 whitespace-nowrap">
        {new Date(bookmark.createdAt).toLocaleDateString('ko-KR')}
      </span>

      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={() => onMove(bookmark.id, bookmark.folder === 'important' ? 'default' : 'important')}
          className="p-1.5 rounded-lg hover:bg-warning-50 dark:hover:bg-warning-900/30"
          aria-label={bookmark.folder === 'important' ? 'Remove from important' : 'Mark as important'}
        >
          {bookmark.folder === 'important' ? (
            <StarIconSolid className="h-4 w-4 text-warning-500" />
          ) : (
            <StarIcon className="h-4 w-4 text-gray-400" />
          )}
        </button>
        <button
          onClick={() => onDelete(bookmark.id)}
          className="p-1.5 rounded-lg hover:bg-error-50 dark:hover:bg-error-900/30"
          aria-label="Delete bookmark"
        >
          <TrashIcon className="h-4 w-4 text-gray-400 hover:text-error-500" />
        </button>
      </div>
    </div>
  );
};

/**
 * BookmarkPage 메인 컴포넌트
 */
const BookmarkPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedFolder, setSelectedFolder] = useState<BookmarkFolder | undefined>(undefined);
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const pageSize = 20;

  // Bookmark list query
  const {
    data: bookmarkData,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['bookmarks', { page, folder: selectedFolder, search: searchQuery }],
    queryFn: () => bookmarkService.getBookmarks(page, pageSize, selectedFolder, searchQuery || undefined),
  });

  // Folder counts query
  const { data: folderCounts } = useQuery({
    queryKey: ['bookmarks', 'counts'],
    queryFn: () => bookmarkService.getFolderCounts(),
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => bookmarkService.deleteBookmark(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bookmarks'] });
      setDeleteConfirmId(null);
    },
  });

  // Move mutation (update folder)
  const moveMutation = useMutation({
    mutationFn: ({ id, folder }: { id: string; folder: BookmarkFolder }) =>
      bookmarkService.updateBookmark(id, { folder }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bookmarks'] });
    },
  });

  const handleDelete = useCallback((id: string) => {
    setDeleteConfirmId(id);
  }, []);

  const confirmDelete = useCallback(() => {
    if (deleteConfirmId) {
      deleteMutation.mutate(deleteConfirmId);
    }
  }, [deleteConfirmId, deleteMutation]);

  const handleMove = useCallback(
    (id: string, folder: BookmarkFolder) => {
      moveMutation.mutate({ id, folder });
    },
    [moveMutation]
  );

  const handleSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
    setPage(1);
  }, []);

  const handleFolderChange = useCallback((folder: BookmarkFolder | undefined) => {
    setSelectedFolder(folder);
    setPage(1);
  }, []);

  const bookmarks = bookmarkData?.bookmarks ?? [];
  const totalCount = bookmarkData?.totalCount ?? 0;
  const totalPages = Math.ceil(totalCount / pageSize);

  // Folder list for sidebar
  const folders = useMemo(
    () => [
      { key: undefined as BookmarkFolder | undefined, label: 'All Bookmarks', icon: <FolderIcon className="h-5 w-5" />, count: folderCounts ? Object.values(folderCounts).reduce((a, b) => a + b, 0) : 0 },
      { key: 'default' as BookmarkFolder, label: 'Default', icon: <BookmarkIcon className="h-5 w-5" />, count: folderCounts?.default ?? 0 },
      { key: 'important' as BookmarkFolder, label: 'Important', icon: <StarIcon className="h-5 w-5" />, count: folderCounts?.important ?? 0 },
      { key: 'read-later' as BookmarkFolder, label: 'Read Later', icon: <ClockIcon className="h-5 w-5" />, count: folderCounts?.['read-later'] ?? 0 },
    ],
    [folderCounts]
  );

  return (
    <div className="space-y-6" data-testid="bookmark-page">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Bookmarks</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Save and organize your favorite documents
        </p>
      </div>

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Folder Sidebar */}
        <div className="lg:w-64 flex-shrink-0">
          <nav className="space-y-1" aria-label="Bookmark folders">
            {folders.map((folder) => {
              const isActive = selectedFolder === folder.key;
              return (
                <button
                  key={folder.label}
                  onClick={() => handleFolderChange(folder.key)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/50 dark:text-primary-300'
                      : 'text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700'
                  }`}
                  aria-current={isActive ? 'page' : undefined}
                >
                  <span className={isActive ? 'text-primary-600 dark:text-primary-400' : 'text-gray-400 dark:text-gray-500'}>
                    {folder.icon}
                  </span>
                  <span className="flex-1 text-left">{folder.label}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    isActive
                      ? 'bg-primary-100 text-primary-700 dark:bg-primary-800 dark:text-primary-200'
                      : 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400'
                  }`}>
                    {folder.count}
                  </span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* Main Content */}
        <div className="flex-1 min-w-0">
          {/* Toolbar */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 mb-4">
            {/* Search */}
            <div className="relative flex-1 w-full sm:max-w-md">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={handleSearchChange}
                placeholder="Search bookmarks..."
                className="w-full pl-9 pr-4 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                aria-label="Search bookmarks"
              />
            </div>

            {/* View toggle */}
            <div className="flex items-center gap-1 bg-gray-100 dark:bg-gray-800 rounded-lg p-0.5">
              <button
                onClick={() => setViewMode('grid')}
                className={`p-1.5 rounded-md transition-colors ${
                  viewMode === 'grid'
                    ? 'bg-white dark:bg-gray-700 text-primary-600 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
                }`}
                aria-label="Grid view"
                title="Grid view"
              >
                <Squares2X2Icon className="h-4 w-4" />
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`p-1.5 rounded-md transition-colors ${
                  viewMode === 'list'
                    ? 'bg-white dark:bg-gray-700 text-primary-600 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
                }`}
                aria-label="List view"
                title="List view"
              >
                <ListBulletIcon className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Loading State */}
          {isLoading && (
            <div className="flex items-center justify-center py-16">
              <div className="text-center">
                <ArrowPathIcon className="h-8 w-8 text-primary-500 animate-spin mx-auto mb-3" />
                <p className="text-sm text-gray-500 dark:text-gray-400">Loading bookmarks...</p>
              </div>
            </div>
          )}

          {/* Error State */}
          {isError && (
            <div className="flex items-center justify-center py-16">
              <div className="text-center max-w-sm">
                <ExclamationTriangleIcon className="h-10 w-10 text-error-500 mx-auto mb-3" />
                <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-1">
                  Failed to load bookmarks
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
                  {error instanceof Error ? error.message : 'An unexpected error occurred.'}
                </p>
                <button
                  onClick={() => refetch()}
                  className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 transition-colors"
                >
                  <ArrowPathIcon className="h-4 w-4" />
                  Retry
                </button>
              </div>
            </div>
          )}

          {/* Empty State */}
          {!isLoading && !isError && bookmarks.length === 0 && (
            <div className="flex items-center justify-center py-16">
              <div className="text-center max-w-sm">
                <FolderOpenIcon className="h-12 w-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
                <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-1">
                  No bookmarks yet
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {searchQuery
                    ? 'No bookmarks match your search. Try a different keyword.'
                    : 'Start bookmarking documents from the search results or knowledge page.'}
                </p>
              </div>
            </div>
          )}

          {/* Grid View */}
          {!isLoading && !isError && bookmarks.length > 0 && viewMode === 'grid' && (
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
              {bookmarks.map((bookmark) => (
                <BookmarkCard
                  key={bookmark.id}
                  bookmark={bookmark}
                  onDelete={handleDelete}
                  onMove={handleMove}
                />
              ))}
            </div>
          )}

          {/* List View */}
          {!isLoading && !isError && bookmarks.length > 0 && viewMode === 'list' && (
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
              {bookmarks.map((bookmark) => (
                <BookmarkListItem
                  key={bookmark.id}
                  bookmark={bookmark}
                  onDelete={handleDelete}
                  onMove={handleMove}
                />
              ))}
            </div>
          )}

          {/* Pagination */}
          {!isLoading && totalPages > 1 && (
            <div className="flex items-center justify-between mt-6">
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Showing {(page - 1) * pageSize + 1}-{Math.min(page * pageSize, totalCount)} of {totalCount} bookmarks
              </p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="px-3 py-1.5 text-sm font-medium rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Previous
                </button>
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  Page {page} of {totalPages}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="px-3 py-1.5 text-sm font-medium rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Delete Confirmation Dialog */}
      <Transition appear show={deleteConfirmId !== null} as={Fragment}>
        <Dialog
          as="div"
          className="relative z-50"
          onClose={() => setDeleteConfirmId(null)}
        >
          <Transition.Child
            as={Fragment}
            enter="ease-out duration-300"
            enterFrom="opacity-0"
            enterTo="opacity-100"
            leave="ease-in duration-200"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
          </Transition.Child>

          <div className="fixed inset-0 flex items-center justify-center p-4">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="mx-auto max-w-sm w-full rounded-xl bg-white dark:bg-gray-800 p-6 shadow-xl">
                <Dialog.Title className="text-lg font-semibold text-gray-900 dark:text-white">
                  Delete Bookmark
                </Dialog.Title>
                <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                  Are you sure you want to remove this bookmark? This action cannot be undone.
                </p>
                <div className="mt-6 flex justify-end gap-3">
                  <button
                    onClick={() => setDeleteConfirmId(null)}
                    className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={confirmDelete}
                    disabled={deleteMutation.isPending}
                    className="px-4 py-2 text-sm font-medium text-white bg-error-600 rounded-lg hover:bg-error-700 disabled:opacity-50 transition-colors"
                  >
                    {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
                  </button>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </Dialog>
      </Transition>
    </div>
  );
};

export default BookmarkPage;
