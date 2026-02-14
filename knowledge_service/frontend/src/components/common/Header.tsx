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
      await authService.logout();
    } catch {
      // Ignore logout API errors
    }
    dispatch(reduxLogout());
    if (authMethod === 'keycloak') {
      keycloakLogout(window.location.origin + '/login');
    } else {
      navigate('/login', { replace: true });
    }
  }, [dispatch, keycloakLogout, authMethod, navigate]);

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
      className="fixed top-0 left-0 right-0 z-50 h-20 bg-transparent"
    >
      <div className="h-full px-8 flex items-center justify-between max-w-[1920px] mx-auto">
        {/* Left section: Menu button and Logo */}
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={onMenuClick}
            className="p-2 rounded-lg text-gray-400 hover:text-neon-cyan hover:bg-white/5 transition-colors lg:hidden"
            aria-label={isSidebarOpen ? 'Close sidebar navigation' : 'Open sidebar navigation'}
            aria-expanded={isSidebarOpen}
          >
            <Bars3Icon className="h-6 w-6" aria-hidden="true" />
          </button>

          <h1 className="text-2xl font-display font-medium text-white lg:hidden">
            NEXUS
          </h1>

          {/* Breadcrumbs or Page Title could go here */}
          <div className="hidden lg:flex items-center space-x-2 text-sm text-gray-400">
            <span>Dashboard</span>
            <span className="text-gray-600">/</span>
            <span className="text-white">Overview</span>
          </div>
        </div>

        {/* Right section: User menu */}
        <div className="flex items-center gap-6">
          {/* Search Bar - Visual Only for design match */}
          <div className="relative group hidden md:block">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <svg className="h-5 w-5 text-gray-500 group-focus-within:text-neon-cyan transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
              </svg>
            </div>
            <input type="text"
              className="bg-black/20 border border-white/10 text-gray-300 text-sm rounded-lg focus:ring-1 focus:ring-neon-cyan focus:border-neon-cyan block w-64 pl-10 p-2.5 transition-all shadow-inner placeholder-gray-600"
              placeholder="Search the matrix..."
            />
          </div>

          {isAuthenticated && user && (
            <Menu as="div" className="relative">
              <MenuButton
                className="flex items-center gap-3 p-1 rounded-full hover:bg-white/5 transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-neon-cyan"
                aria-label={`User menu for ${user.name || user.username}`}
              >
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-neon-purple to-neon-pink p-[1px]">
                  <div className="w-full h-full rounded-full bg-dark-200 flex items-center justify-center">
                    <span className="text-xs font-bold text-white">{getUserInitials()}</span>
                  </div>
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
                  className="absolute right-0 mt-2 w-60 origin-top-right rounded-xl bg-dark-300/90 backdrop-blur-xl border border-white/10 shadow-[0_0_15px_rgba(0,0,0,0.5)] focus:outline-none divide-y divide-white/5 z-50"
                >
                  <div className="px-4 py-3.5">
                    <p className="text-sm font-semibold text-white">
                      {user.name || user.username}
                    </p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {user.email}
                    </p>
                  </div>

                  <div className="p-1">
                    <MenuItem>
                      {({ active }) => (
                        <button
                          onClick={() => navigate('/profile')}
                          className={`${active ? 'bg-white/5 text-neon-cyan' : 'text-gray-300'} flex items-center w-full px-3 py-2 text-sm rounded-lg transition-colors`}
                        >
                          <UserIcon className="mr-3 h-4.5 w-4.5" />
                          <span>프로필</span>
                        </button>
                      )}
                    </MenuItem>
                    <MenuItem>
                      {({ active }) => (
                        <button
                          onClick={() => navigate('/admin')}
                          className={`${active ? 'bg-white/5 text-neon-cyan' : 'text-gray-300'} flex items-center w-full px-3 py-2 text-sm rounded-lg transition-colors`}
                        >
                          <Cog6ToothIcon className="mr-3 h-4.5 w-4.5" />
                          <span>설정</span>
                        </button>
                      )}
                    </MenuItem>
                  </div>

                  <div className="p-1">
                    <MenuItem>
                      {({ active }) => (
                        <button
                          onClick={handleLogout}
                          className={`${active ? 'bg-error-900/30 text-error-400' : 'text-error-500'} flex items-center w-full px-3 py-2 text-sm rounded-lg transition-colors`}
                        >
                          <ArrowRightStartOnRectangleIcon className="mr-3 h-4.5 w-4.5" />
                          <span>로그아웃</span>
                        </button>
                      )}
                    </MenuItem>
                  </div>
                </MenuItems>
              </Transition>
            </Menu>
          )}

          {!isAuthenticated && (
            <a
              href="/login"
              className="px-4 py-2 rounded-lg bg-neon-cyan/20 text-neon-cyan border border-neon-cyan/30 hover:bg-neon-cyan/30 transition-all text-sm font-bold shadow-glow-cyan"
            >
              LOGIN
            </a>
          )}
        </div>
      </div>
    </header>
  );
};

export default Header;
