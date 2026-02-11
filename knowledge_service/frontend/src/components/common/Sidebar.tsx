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

interface MenuSection {
  label: string;
  items: MenuItem[];
}

const menuSections: MenuSection[] = [
  {
    label: '메인',
    items: [
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
    ],
  },
  {
    label: '지식 관리',
    items: [
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
    ],
  },
  {
    label: '개인',
    items: [
      {
        text: '북마크',
        icon: <BookmarkIcon className="h-5 w-5" />,
        path: '/bookmarks',
      },
      {
        text: '프로필',
        icon: <UserIcon className="h-5 w-5" />,
        path: '/profile',
      },
    ],
  },
  {
    label: '시스템',
    items: [
      {
        text: '관리자',
        icon: <Cog6ToothIcon className="h-5 w-5" />,
        path: '/admin',
        roles: ['ADMIN'],
      },
    ],
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

  // 역할 기반 섹션 필터링
  const filteredSections = menuSections
    .map((section) => ({
      ...section,
      items: section.items.filter((item) => {
        if (!item.roles) return true;
        return item.roles.some((role) => hasRole(role));
      }),
    }))
    .filter((section) => section.items.length > 0);

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
        className={`fixed top-16 left-0 z-40 h-[calc(100vh-4rem)] bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 transition-transform duration-300 ease-in-out flex flex-col ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
        style={{ width: `${width}px` }}
        data-testid="sidebar"
      >
        {/* Mobile close button */}
        <div className="flex items-center justify-between p-4 md:hidden">
          <span className="text-lg font-semibold text-gray-900 dark:text-white" id="sidebar-title">
            메뉴
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
        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-6" aria-label="Main menu">
          {filteredSections.map((section, sectionIdx) => (
            <div key={section.label}>
              {/* Section header */}
              {sectionIdx > 0 && (
                <div className="mb-2 border-t border-gray-100 dark:border-gray-700/50" role="separator" aria-hidden="true" />
              )}
              <p className="px-3 mb-2 text-[11px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">
                {section.label}
              </p>
              <div className="space-y-0.5">
                {section.items.map((item) => {
                  const isActive =
                    location.pathname === item.path ||
                    location.pathname.startsWith(item.path + '/');
                  return (
                    <button
                      key={item.path}
                      onClick={() => handleNavigation(item.path)}
                      aria-current={isActive ? 'page' : undefined}
                      aria-label={isActive ? `${item.text} (current page)` : item.text}
                      className={`relative w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800 ${
                        isActive
                          ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300'
                          : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900 dark:text-gray-300 dark:hover:bg-gray-700/50 dark:hover:text-white'
                      }`}
                      data-testid={`nav-${item.path.replace('/', '')}`}
                    >
                      {/* Active left indicator bar */}
                      {isActive && (
                        <span className="absolute left-0 top-1.5 bottom-1.5 w-[3px] rounded-r-full bg-primary-600 dark:bg-primary-400" aria-hidden="true" />
                      )}
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
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        {/* Bottom section - Version info */}
        <div className="flex-shrink-0 p-4 border-t border-gray-100 dark:border-gray-700/50">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center flex-shrink-0">
              <svg className="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
            </div>
            <div>
              <p className="text-xs font-medium text-gray-700 dark:text-gray-300">Knowledge Portal</p>
              <p className="text-[10px] text-gray-400 dark:text-gray-500">v0.1.0 · Graph RAG</p>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;
