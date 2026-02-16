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
        className={`fixed top-16 left-0 z-40 h-[calc(100vh-4rem)] bg-white/80 dark:bg-gray-900/80 backdrop-blur-md border-r border-gray-200/60 dark:border-gray-800/60 transition-transform duration-300 ease-in-out flex flex-col ${open ? 'translate-x-0' : '-translate-x-full'
          }`}
        style={{ width: `${width}px` }}
        data-testid="sidebar"
      >
        {/* Mobile close button */}
        <div className="flex items-center justify-between p-4 md:hidden border-b border-gray-100 dark:border-gray-800">
          <span className="text-lg font-bold text-gray-900 dark:text-white" id="sidebar-title">
            메뉴
          </span>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-primary-500"
            aria-label="Close sidebar"
            data-testid="sidebar-close"
          >
            <XMarkIcon className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto px-4 py-6 space-y-8 scrollbar-hide" aria-label="Main menu">
          {filteredSections.map((section, sectionIdx) => (
            <div key={section.label} className="space-y-3">
              <p className="px-3 text-[11px] font-bold text-gray-400 dark:text-gray-500 uppercase tracking-wider">
                {section.label}
              </p>
              <div className="space-y-1">
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
                      className={`group relative w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 outline-none focus-visible:ring-2 focus-visible:ring-primary-500 ${isActive
                          ? 'bg-primary-50 text-primary-700 shadow-sm dark:bg-primary-900/20 dark:text-primary-300'
                          : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800/50 dark:hover:text-gray-200'
                        }`}
                      data-testid={`nav-${item.path.replace('/', '')}`}
                    >
                      <span
                        className={`transition-colors duration-200 ${isActive
                            ? 'text-primary-600 dark:text-primary-400'
                            : 'text-gray-400 group-hover:text-gray-600 dark:text-gray-500 dark:group-hover:text-gray-300'
                          }`}
                        aria-hidden="true"
                      >
                        {item.icon}
                      </span>
                      <span>{item.text}</span>

                      {/* Active indicator dot */}
                      {isActive && (
                        <span className="absolute right-3 w-1.5 h-1.5 rounded-full bg-primary-500" aria-hidden="true" />
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        {/* Bottom section - Version info */}
        <div className="flex-shrink-0 p-4 border-t border-gray-100 dark:border-gray-800/60 bg-gray-50/50 dark:bg-gray-900/30">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-600 to-indigo-600 flex items-center justify-center flex-shrink-0 shadow-sm">
              <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <div>
              <p className="text-xs font-semibold text-gray-700 dark:text-gray-200">Knowledge Portal</p>
              <p className="text-[10px] text-gray-500 dark:text-gray-500">v0.1.0 · Graph RAG</p>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;
