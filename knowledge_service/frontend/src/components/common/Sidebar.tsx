/**
 * Sidebar - 좌측 네비게이션 사이드바
 *
 * Tailwind CSS 기반
 * 대시보드, 검색, 지식관리 메뉴 제공
 */
import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  HomeIcon,
  MagnifyingGlassIcon,
  BookOpenIcon,
  BookmarkIcon,
  ArrowUpTrayIcon,
  UserIcon,
  Cog6ToothIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import { useAuth } from '@/auth';

interface SidebarProps {
  open: boolean;
  width: number;
  onClose?: () => void;
}

interface MenuItem {
  text: string;
  icon: React.ReactNode;
  path: string;
  roles?: string[];
  dividerBefore?: boolean;
}

const menuItems: MenuItem[] = [
  {
    text: '대시보드',
    icon: <HomeIcon className="h-5 w-5" />,
    path: '/dashboard',
  },
  {
    text: '검색',
    icon: <MagnifyingGlassIcon className="h-5 w-5" />,
    path: '/search',
  },
  {
    text: '지식 관리',
    icon: <BookOpenIcon className="h-5 w-5" />,
    path: '/knowledge',
    roles: ['KNOWLEDGE_MANAGER', 'ADMIN'],
  },
  {
    text: '문서 업로드',
    icon: <ArrowUpTrayIcon className="h-5 w-5" />,
    path: '/upload',
    roles: ['KNOWLEDGE_MANAGER', 'ADMIN'],
  },
  {
    text: '북마크',
    icon: <BookmarkIcon className="h-5 w-5" />,
    path: '/bookmarks',
    dividerBefore: true,
  },
  {
    text: '프로필',
    icon: <UserIcon className="h-5 w-5" />,
    path: '/profile',
  },
  {
    text: '관리자',
    icon: <Cog6ToothIcon className="h-5 w-5" />,
    path: '/admin',
    roles: ['ADMIN'],
    dividerBefore: true,
  },
];

const Sidebar: React.FC<SidebarProps> = ({ open, width, onClose }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { hasRole } = useAuth();

  const handleNavigation = (path: string) => {
    navigate(path);
    // 모바일에서 메뉴 클릭 시 사이드바 닫기
    if (onClose && window.innerWidth < 768) {
      onClose();
    }
  };

  // 역할 기반 메뉴 필터링
  const filteredMenuItems = menuItems.filter((item) => {
    if (!item.roles) return true;
    return item.roles.some((role) => hasRole(role));
  });

  return (
    <>
      {/* Overlay for mobile */}
      {open && (
        <div
          className="fixed inset-0 z-30 bg-black/50 md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        id="sidebar-navigation"
        aria-label="Main navigation sidebar"
        aria-hidden={!open}
        className={`fixed top-16 left-0 z-40 h-[calc(100vh-4rem)] bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 transition-transform duration-300 ease-in-out ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
        style={{ width: `${width}px` }}
        data-testid="sidebar"
      >
        {/* Mobile close button */}
        <div className="flex items-center justify-between p-4 md:hidden">
          <span className="text-lg font-semibold text-gray-900 dark:text-white" id="sidebar-title">
            Menu
          </span>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800"
            aria-label="Close sidebar"
            data-testid="sidebar-close"
          >
            <XMarkIcon className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="p-4 space-y-1" aria-label="Main menu">
          {filteredMenuItems.map((item) => {
            const isActive =
              location.pathname === item.path ||
              location.pathname.startsWith(item.path + '/');
            return (
              <React.Fragment key={item.path}>
                {item.dividerBefore && (
                  <div className="my-2 border-t border-gray-200 dark:border-gray-700" role="separator" aria-hidden="true" />
                )}
                <button
                  onClick={() => handleNavigation(item.path)}
                  aria-current={isActive ? 'page' : undefined}
                  aria-label={isActive ? `${item.text} (current page)` : item.text}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800 ${
                    isActive
                      ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/50 dark:text-primary-300'
                      : 'text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700'
                  }`}
                  data-testid={`nav-${item.path.replace('/', '')}`}
                >
                  <span
                    className={
                      isActive
                        ? 'text-primary-600 dark:text-primary-400'
                        : 'text-gray-400 dark:text-gray-500'
                    }
                    aria-hidden="true"
                  >
                    {item.icon}
                  </span>
                  <span>{item.text}</span>
                  {isActive && (
                    <span className="ml-auto w-1.5 h-1.5 rounded-full bg-primary-600 dark:bg-primary-400" aria-hidden="true" />
                  )}
                </button>
              </React.Fragment>
            );
          })}
        </nav>

        {/* Bottom section - Version info */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200 dark:border-gray-700">
          <div className="text-xs text-gray-500 dark:text-gray-400">
            <p>Knowledge Portal v0.1.0</p>
            <p className="mt-1">Powered by Hybrid RAG</p>
          </div>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;
