import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Box, Toolbar } from '@mui/material';

import Header from './Header';
import Sidebar from './Sidebar';

const DRAWER_WIDTH = 240;

/**
 * MainLayout - 전체 애플리케이션 레이아웃
 *
 * 상단 헤더, 좌측 사이드바, 메인 콘텐츠 영역으로 구성
 */
const MainLayout: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const handleSidebarToggle = () => {
    setSidebarOpen(!sidebarOpen);
  };

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <Header onMenuClick={handleSidebarToggle} />
      <Sidebar open={sidebarOpen} width={DRAWER_WIDTH} />
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { sm: `calc(100% - ${sidebarOpen ? DRAWER_WIDTH : 0}px)` },
          ml: { sm: sidebarOpen ? `${DRAWER_WIDTH}px` : 0 },
          transition: (theme) =>
            theme.transitions.create(['margin', 'width'], {
              easing: theme.transitions.easing.sharp,
              duration: theme.transitions.duration.leavingScreen,
            }),
          backgroundColor: 'background.default',
        }}
      >
        <Toolbar /> {/* Spacer for fixed header */}
        <Outlet />
      </Box>
    </Box>
  );
};

export default MainLayout;
