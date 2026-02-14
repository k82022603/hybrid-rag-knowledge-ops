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
          className="fixed inset-0 z-30 bg-black/60 md:hidden backdrop-blur-sm"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        id="sidebar-navigation"
        aria-label="Main navigation sidebar"
        aria-hidden={!open}
        className={`fixed top-0 left-0 z-40 h-screen glass border-r-0 border-r border-white/5 flex flex-col transition-transform duration-300 ease-in-out ${open ? 'translate-x-0' : '-translate-x-full'
          }`}
        style={{ width: `${width}px` }}
        data-testid="sidebar"
      >
        {/* Logo Section */}
        <div className="h-20 flex items-center justify-center border-b border-white/5 shrink-0">
          <div className="flex items-center space-x-3">
            <div className="relative w-10 h-10 flex items-center justify-center">
              <div className="absolute inset-0 bg-neon-cyan/20 blur-md rounded-full animate-pulse"></div>
              <div className="relative w-8 h-8 rounded-lg bg-gradient-to-br from-neon-cyan to-neon-purple flex items-center justify-center text-white font-bold text-lg">
                N
              </div>
            </div>
            <span className="text-2xl font-bold font-display text-white tracking-wide text-glow">NEXUS</span>
          </div>
        </div>

        {/* Mobile close button */}
        <div className="flex items-center justify-between p-4 md:hidden border-b border-white/5">
          <span className="text-sm font-bold text-gray-400">MENU</span>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-white/10"
            aria-label="Close sidebar"
          >
            <XMarkIcon className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto px-3 py-6 space-y-8 scrollbar-hide">
          {filteredSections.map((section) => (
            <div key={section.label} className="space-y-2">
              <p className="px-4 text-[10px] font-bold text-gray-500 uppercase tracking-widest">
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
                      className={`group relative w-full flex items-center gap-3 px-4 py-3 rounded-r-lg text-sm font-medium transition-all duration-200 border-l-2 ${isActive
                          ? 'border-neon-cyan bg-gradient-to-r from-neon-cyan/10 to-transparent text-neon-cyan'
                          : 'border-transparent text-gray-400 hover:text-white hover:bg-white/5'
                        }`}
                    >
                      <span
                        className={`transition-colors duration-200 ${isActive ? 'text-neon-cyan drop-shadow-[0_0_5px_rgba(6,182,212,0.5)]' : 'text-gray-500 group-hover:text-gray-300'
                          }`}
                      >
                        {item.icon}
                      </span>
                      <span>{item.text}</span>

                      {/* Active Glow Effect */}
                      {isActive && (
                        <div className="absolute inset-0 bg-neon-cyan/5 blur-sm -z-10" />
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        {/* User / System Info */}
        <div className="flex-shrink-0 p-4 border-t border-white/5 bg-black/20">
          <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-white/5 transition-colors cursor-pointer group">
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-neon-purple to-neon-pink p-[1px]">
              <div className="w-full h-full bg-dark-200 rounded-full flex items-center justify-center">
                <UserIcon className="w-4 h-4 text-gray-400 group-hover:text-white transition-colors" />
              </div>
            </div>
            <div className="overflow-hidden">
              <p className="text-xs font-semibold text-gray-300 group-hover:text-white transition-colors">System Admin</p>
              <p className="text-[10px] text-neon-cyan flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-neon-cyan animate-pulse"></span>
                Online
              </p>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;
