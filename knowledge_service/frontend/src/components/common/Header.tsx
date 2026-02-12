/**
 * Header - 상단 헤더 컴포넌트
 *
 * Tailwind CSS + Headless UI 기반
 * 메뉴 토글 버튼, 로고, 사용자 메뉴 포함
 */
import React, { Fragment, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Menu, MenuButton, MenuItem, MenuItems, Transition } from '@headlessui/react';
import {
  Bars3Icon,
  ArrowRightStartOnRectangleIcon,
  Cog6ToothIcon,
  UserIcon,
} from '@heroicons/react/24/outline';
import { useAuth } from '@/auth';
import { logout as reduxLogout } from '@/store/slices/authSlice';
import { useAppDispatch } from '@/store';
import { authService } from '@/services';

interface HeaderProps {
  onMenuClick: () => void;
  /** Indicates if sidebar is currently expanded */
  isSidebarOpen?: boolean;
}

const Header: React.FC<HeaderProps> = ({ onMenuClick, isSidebarOpen = true }) => {
  const { user, logout: keycloakLogout, isAuthenticated, authMethod } = useAuth();
  const dispatch = useAppDispatch();
  const navigate = useNavigate();

  const handleLogout = useCallback(async () => {
    try {
      // Call logout API
      await authService.logout();
    } catch {
      // Ignore logout API errors
    }

    // Clear Redux state
    dispatch(reduxLogout());

    // If using Keycloak, also logout from Keycloak
    if (authMethod === 'keycloak') {
      keycloakLogout(window.location.origin + '/login');
    } else {
      // Direct login - just navigate to login page
      navigate('/login', { replace: true });
    }
  }, [dispatch, keycloakLogout, authMethod, navigate]);

  // 사용자 이니셜 생성
  const getUserInitials = () => {
    if (!user?.name) return 'U';
    const names = user.name.split(' ');
    if (names.length >= 2) {
      return `${names[0][0]}${names[names.length - 1][0]}`.toUpperCase();
    }
    return user.name.substring(0, 2).toUpperCase();
  };

  return (
    <header
      role="banner"
      className="fixed top-0 left-0 right-0 z-50 h-16 glass-header transition-all duration-300"
    >
      {/* Primary accent line at top */}
      <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-primary-500 via-primary-400 to-accent-400" aria-hidden="true" />

      <div className="h-full px-4 flex items-center justify-between max-w-[1920px] mx-auto">
        {/* Left section: Menu button and Logo */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onMenuClick}
            className="p-2 rounded-lg text-gray-500 hover:bg-gray-100/80 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800/80 dark:hover:text-gray-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 transition-colors"
            aria-label={isSidebarOpen ? 'Close sidebar navigation' : 'Open sidebar navigation'}
            aria-expanded={isSidebarOpen}
            data-testid="sidebar-toggle"
          >
            <Bars3Icon className="h-6 w-6" aria-hidden="true" />
          </button>

          <div className="ml-2 flex items-center gap-3 select-none">
            <div
              className="relative flex-shrink-0 w-8 h-8 rounded-xl bg-gradient-to-br from-primary-600 to-primary-700 flex items-center justify-center shadow-md shadow-primary-500/20 group overflow-hidden"
              aria-hidden="true"
            >
              <div className="absolute inset-0 bg-white/20 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
              <svg
                className="w-5 h-5 text-white transform group-hover:scale-110 transition-transform duration-300"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
                />
              </svg>
            </div>
            <div className="hidden sm:block">
              <h1 className="text-lg font-bold text-gray-900 dark:text-white leading-none tracking-tight">
                Knowledge<span className="text-primary-600 dark:text-primary-400">Portal</span>
              </h1>
              <p className="text-[10px] font-semibold text-gray-500 dark:text-gray-400 tracking-wider uppercase mt-0.5">
                Graph RAG Platform
              </p>
            </div>
            {/* Screen reader only - full app name */}
            <span className="sr-only">Knowledge Portal - Enterprise Knowledge Search System</span>
          </div>
        </div>

        {/* Right section: User menu */}
        <div className="flex items-center gap-2 sm:gap-4">
          {isAuthenticated && user && (
            <Menu as="div" className="relative">
              <MenuButton
                className="flex items-center gap-3 p-1.5 pr-3 rounded-full hover:bg-gray-100/80 dark:hover:bg-gray-800/80 transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
                aria-label={`User menu for ${user.name || user.username}`}
                data-testid="user-menu-button"
              >
                {/* User Avatar */}
                <div
                  className="w-8 h-8 rounded-full bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-700 dark:to-gray-800 flex items-center justify-center text-gray-600 dark:text-gray-300 text-sm font-semibold shadow-inner ring-2 ring-white dark:ring-gray-700"
                  aria-hidden="true"
                >
                  {getUserInitials()}
                </div>
                {/* User Info (hidden on mobile) */}
                <div className="hidden md:block text-left mr-1">
                  <p className="text-sm font-semibold text-gray-700 dark:text-gray-200 leading-tight">
                    {user.name || user.username}
                  </p>
                </div>
              </MenuButton>

              <Transition
                as={Fragment}
                enter="transition ease-out duration-200"
                enterFrom="transform opacity-0 scale-95 translate-y-2"
                enterTo="transform opacity-100 scale-100 translate-y-0"
                leave="transition ease-in duration-150"
                leaveFrom="transform opacity-100 scale-100 translate-y-0"
                leaveTo="transform opacity-0 scale-95 translate-y-2"
              >
                <MenuItems
                  className="absolute right-0 mt-2 w-60 origin-top-right rounded-xl bg-white/90 dark:bg-gray-800/90 backdrop-blur-xl shadow-lg ring-1 ring-black/5 dark:ring-white/10 focus:outline-none divide-y divide-gray-100 dark:divide-gray-700/50 z-50 transform"
                  aria-label="User account options"
                >
                  {/* User Info Section */}
                  <div className="px-4 py-3.5 bg-gray-50/50 dark:bg-gray-800/50 rounded-t-xl">
                    <p className="text-sm font-semibold text-gray-900 dark:text-white">
                      {user.name || user.username}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 truncate mt-0.5">
                      {user.email}
                    </p>
                    {user.roles && user.roles.length > 0 && (
                      <div className="mt-2.5 flex flex-wrap gap-1">
                        {user.roles
                          .filter((role) => !role.startsWith('default-'))
                          .slice(0, 3)
                          .map((role) => (
                            <span
                              key={role}
                              className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-primary-50 text-primary-700 border border-primary-100 dark:bg-primary-900/30 dark:text-primary-300 dark:border-primary-800"
                            >
                              {role}
                            </span>
                          ))}
                      </div>
                    )}
                  </div>

                  {/* Menu Items */}
                  <div className="p-1" role="group" aria-label="Account navigation">
                    <MenuItem>
                      {({ focus }) => (
                        <button
                          onClick={() => navigate('/profile')}
                          className={`${focus ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/20 dark:text-primary-300' : 'text-gray-700 dark:text-gray-200'
                            } flex items-center w-full px-3 py-2 text-sm rounded-lg transition-colors`}
                        >
                          <UserIcon className={`mr-3 h-4.5 w-4.5 ${focus ? 'text-primary-500' : 'text-gray-400'}`} aria-hidden="true" />
                          <span>프로필</span>
                        </button>
                      )}
                    </MenuItem>
                    <MenuItem>
                      {({ focus }) => (
                        <button
                          onClick={() => navigate('/admin')}
                          className={`${focus ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/20 dark:text-primary-300' : 'text-gray-700 dark:text-gray-200'
                            } flex items-center w-full px-3 py-2 text-sm rounded-lg transition-colors`}
                        >
                          <Cog6ToothIcon className={`mr-3 h-4.5 w-4.5 ${focus ? 'text-primary-500' : 'text-gray-400'}`} aria-hidden="true" />
                          <span>설정</span>
                        </button>
                      )}
                    </MenuItem>
                  </div>

                  {/* Logout */}
                  <div className="p-1" role="group" aria-label="로그아웃">
                    <MenuItem>
                      {({ focus }) => (
                        <button
                          onClick={handleLogout}
                          className={`${focus ? 'bg-error-50 text-error-700 dark:bg-error-900/20 dark:text-error-300' : 'text-error-600 dark:text-error-400'
                            } flex items-center w-full px-3 py-2 text-sm rounded-lg transition-colors`}
                        >
                          <ArrowRightStartOnRectangleIcon className="mr-3 h-4.5 w-4.5" aria-hidden="true" />
                          <span>로그아웃</span>
                        </button>
                      )}
                    </MenuItem>
                  </div>
                </MenuItems>
              </Transition>
            </Menu>
          )}

          {/* Login button when not authenticated */}
          {!isAuthenticated && (
            <a
              href="/login"
              className="btn-primary btn-sm rounded-full px-5 shadow-lg shadow-primary-500/20 focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-gray-900"
              data-testid="sign-in-link"
            >
              로그인
            </a>
          )}
        </div>
      </div>
    </header>
  );
};

export default Header;
