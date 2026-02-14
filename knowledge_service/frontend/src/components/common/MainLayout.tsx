/**
 * MainLayout - 전체 애플리케이션 레이아웃
 *
 * Tailwind CSS 기반
 * 상단 헤더, 좌측 사이드바, 메인 콘텐츠 영역으로 구성
 *
 * Accessibility Features (WCAG 2.1 AA):
 * - Skip link for keyboard navigation
 * - Proper landmark roles (header, nav, main)
 * - Focus management for sidebar toggle
 * - Keyboard-accessible navigation
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Outlet, useLocation } from 'react-router-dom';

import Header from './Header';
import Sidebar from './Sidebar';
import SkipLink from './SkipLink';

const DRAWER_WIDTH = 256; // 16rem = 256px

const MainLayout: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const location = useLocation();

  // 반응형 사이드바 처리
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 768) {
        setSidebarOpen(false);
      } else {
        setSidebarOpen(true);
      }
    };

    // 초기 설정
    handleResize();

    // 리사이즈 이벤트 리스너
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Focus main content on route change for screen readers
  useEffect(() => {
    const mainContent = document.getElementById('main-content');
    if (mainContent) {
      // Use a small delay to ensure the new content is rendered
      const timeoutId = setTimeout(() => {
        mainContent.focus({ preventScroll: true });
      }, 100);
      return () => clearTimeout(timeoutId);
    }
  }, [location.pathname]);

  const handleSidebarToggle = useCallback(() => {
    setSidebarOpen((prev) => !prev);
  }, []);

  const handleSidebarClose = useCallback(() => {
    setSidebarOpen(false);
  }, []);

  // Handle Escape key to close sidebar on mobile
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && sidebarOpen && window.innerWidth < 768) {
        setSidebarOpen(false);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [sidebarOpen]);

  return (
    <div className="min-h-screen relative overflow-hidden bg-dark-200">
      {/* Background Ambient Glow */}
      <div className="absolute top-0 left-0 w-full h-full bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-neon-purple/20 via-dark-200 to-dark-300 -z-10 pointer-events-none" />
      <div className="absolute bottom-0 left-0 w-1/2 h-1/2 bg-[radial-gradient(ellipse_at_bottom_left,_var(--tw-gradient-stops))] from-neon-cyan/10 via-transparent to-transparent -z-10 pointer-events-none" />

      {/* Skip Link for keyboard navigation - WCAG 2.4.1 */}
      <SkipLink targetId="main-content" />

      {/* Header with role="banner" */}
      <Header onMenuClick={handleSidebarToggle} isSidebarOpen={sidebarOpen} />

      {/* Sidebar with navigation role */}
      <Sidebar
        open={sidebarOpen}
        width={DRAWER_WIDTH}
        onClose={handleSidebarClose}
      />

      {/* Main content area with proper landmark */}
      <main
        id="main-content"
        role="main"
        aria-label="Main content"
        tabIndex={-1}
        className={`min-h-screen pt-20 transition-all duration-300 ease-in-out focus:outline-none ${sidebarOpen ? 'md:ml-64' : 'ml-0'
          }`}
      >
        <div className="p-4 md:p-8 max-w-7xl mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
};

export default MainLayout;
