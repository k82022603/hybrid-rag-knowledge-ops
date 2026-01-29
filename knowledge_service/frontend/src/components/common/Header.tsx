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
      className="fixed top-0 left-0 right-0 z-50 h-16 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 shadow-sm"
    >
      <div className="h-full px-4 flex items-center justify-between">
        {/* Left section: Menu button and Logo */}
        <div className="flex items-center">
          <button
            type="button"
            onClick={onMenuClick}
            className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800"
            aria-label={isSidebarOpen ? 'Close sidebar navigation' : 'Open sidebar navigation'}
            aria-expanded={isSidebarOpen}
            data-testid="sidebar-toggle"
          >
            <Bars3Icon className="h-6 w-6" aria-hidden="true" />
          </button>

          <div className="ml-4 flex items-center">
            <div
              className="flex-shrink-0 w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center"
              aria-hidden="true"
            >
              <svg
                className="w-5 h-5 text-white"
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
            <h1 className="ml-3 text-xl font-semibold text-gray-900 dark:text-white hidden sm:block">
              Knowledge Portal
            </h1>
            {/* Screen reader only - full app name */}
            <span className="sr-only">Knowledge Portal - Enterprise Knowledge Search System</span>
          </div>
        </div>

        {/* Right section: User menu */}
        <div className="flex items-center gap-4">
          {isAuthenticated && user && (
            <Menu as="div" className="relative">
              <MenuButton
                className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800"
                aria-label={`User menu for ${user.name || user.username}`}
                data-testid="user-menu-button"
              >
                {/* User Avatar */}
                <div
                  className="w-8 h-8 rounded-full bg-primary-600 flex items-center justify-center text-white text-sm font-medium"
                  aria-hidden="true"
                >
                  {getUserInitials()}
                </div>
                {/* User Info (hidden on mobile) */}
                <div className="hidden md:block text-left">
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {user.name || user.username}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {user.email}
                  </p>
                </div>
              </MenuButton>

              <Transition
                as={Fragment}
                enter="transition ease-out duration-100"
                enterFrom="transform opacity-0 scale-95"
                enterTo="transform opacity-100 scale-100"
                leave="transition ease-in duration-75"
                leaveFrom="transform opacity-100 scale-100"
                leaveTo="transform opacity-0 scale-95"
              >
                <MenuItems
                  className="absolute right-0 mt-2 w-56 origin-top-right rounded-lg bg-white dark:bg-gray-800 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none divide-y divide-gray-100 dark:divide-gray-700"
                  aria-label="User account options"
                >
                  {/* User Info Section */}
                  <div className="px-4 py-3">
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      {user.name || user.username}
                    </p>
                    <p className="text-sm text-gray-500 dark:text-gray-400 truncate">
                      {user.email}
                    </p>
                    {user.roles && user.roles.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {user.roles
                          .filter((role) => !role.startsWith('default-'))
                          .slice(0, 3)
                          .map((role) => (
                            <span
                              key={role}
                              className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-primary-100 text-primary-800 dark:bg-primary-900 dark:text-primary-200"
                            >
                              {role}
                            </span>
                          ))}
                      </div>
                    )}
                  </div>

                  {/* Menu Items */}
                  <div className="py-1" role="group" aria-label="Account navigation">
                    <MenuItem>
                      {({ focus }) => (
                        <button
                          onClick={() => navigate('/profile')}
                          className={`${
                            focus ? 'bg-gray-100 dark:bg-gray-700' : ''
                          } flex items-center w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-200 focus:outline-none`}
                        >
                          <UserIcon className="mr-3 h-5 w-5 text-gray-400" aria-hidden="true" />
                          <span>Profile</span>
                        </button>
                      )}
                    </MenuItem>
                    <MenuItem>
                      {({ focus }) => (
                        <button
                          onClick={() => navigate('/admin')}
                          className={`${
                            focus ? 'bg-gray-100 dark:bg-gray-700' : ''
                          } flex items-center w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-200 focus:outline-none`}
                        >
                          <Cog6ToothIcon className="mr-3 h-5 w-5 text-gray-400" aria-hidden="true" />
                          <span>Settings</span>
                        </button>
                      )}
                    </MenuItem>
                  </div>

                  {/* Logout */}
                  <div className="py-1" role="group" aria-label="Sign out">
                    <MenuItem>
                      {({ focus }) => (
                        <button
                          onClick={handleLogout}
                          className={`${
                            focus ? 'bg-gray-100 dark:bg-gray-700' : ''
                          } flex items-center w-full px-4 py-2 text-sm text-error-600 dark:text-error-400 focus:outline-none`}
                        >
                          <ArrowRightStartOnRectangleIcon className="mr-3 h-5 w-5" aria-hidden="true" />
                          <span>Sign out</span>
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
              className="btn-primary btn-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800"
              data-testid="sign-in-link"
            >
              Sign in
            </a>
          )}
        </div>
      </div>
    </header>
  );
};

export default Header;
