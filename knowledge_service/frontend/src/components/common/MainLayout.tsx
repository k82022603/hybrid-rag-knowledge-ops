/**
 * MainLayout - 전체 애플리케이션 레이아웃
 *
 * Tailwind CSS 기반
 * 상단 헤더, 좌측 사이드바, 메인 콘텐츠 영역으로 구성
 */
import React, { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';

import Header from './Header';
import Sidebar from './Sidebar';

const DRAWER_WIDTH = 256; // 16rem = 256px

const MainLayout: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(true);

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

  const handleSidebarToggle = () => {
    setSidebarOpen(!sidebarOpen);
  };

  const handleSidebarClose = () => {
    setSidebarOpen(false);
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <Header onMenuClick={handleSidebarToggle} />

      {/* Sidebar */}
      <Sidebar
        open={sidebarOpen}
        width={DRAWER_WIDTH}
        onClose={handleSidebarClose}
      />

      {/* Main content */}
      <main
        className={`min-h-screen pt-16 transition-all duration-300 ease-in-out ${
          sidebarOpen ? 'md:ml-64' : 'ml-0'
        }`}
      >
        <div className="p-4 md:p-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
};

export default MainLayout;
