# STORY-041: Dashboard UI

## 메타데이터

| 항목 | 값 |
|------|-----|
| **Jira ID** | SCRUM-42 |
| **Epic** | EPIC-003 |
| **Status** | To Do |
| **Priority** | High |
| **Story Points** | 5 |
| **Assignee** | Frontend |
| **Sprint** | 3 |

---

## User Story

**As a** 지식 검색 사용자,
**I want** 직관적인 대시보드 화면,
**So that** 시스템 현황과 주요 기능에 빠르게 접근할 수 있음.

---

## Acceptance Criteria

- [ ] **Given** 로그인 완료, **When** 대시보드 접근, **Then** 사용자 환영 메시지 표시
- [ ] **Given** 대시보드 로드, **When** 통계 API 호출, **Then** 문서 수, 검색 수 등 표시
- [ ] **Given** 최근 검색 섹션, **When** 렌더링, **Then** 최근 5개 검색 기록 표시
- [ ] **Given** 빠른 검색 입력창, **When** 엔터 입력, **Then** 검색 페이지로 이동
- [ ] **Given** 사이드바 네비게이션, **When** 메뉴 클릭, **Then** 해당 페이지로 이동

---

## Tasks

- [ ] 대시보드 레이아웃 구현 (Header, Sidebar, Content)
- [ ] 통계 위젯 컴포넌트 (StatCard)
- [ ] 최근 검색 기록 컴포넌트
- [ ] 빠른 검색 입력창 컴포넌트
- [ ] API 연동 (통계, 검색 기록)
- [ ] 반응형 디자인
- [ ] 로딩/에러 상태 처리
- [ ] 단위 테스트 작성

---

## 기술 노트

### Dashboard Layout

```typescript
// frontend/src/features/dashboard/Dashboard.tsx
import { Box, Grid, Paper, Typography } from '@mui/material';
import { useAuth } from '../auth/useAuth';
import { useDashboardStats } from './hooks/useDashboardStats';
import { useRecentSearches } from './hooks/useRecentSearches';
import { StatCard } from './components/StatCard';
import { RecentSearches } from './components/RecentSearches';
import { QuickSearch } from './components/QuickSearch';
import { Sidebar } from '../../shared/components/Sidebar';
import { Header } from '../../shared/components/Header';

export const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const { stats, isLoading: statsLoading } = useDashboardStats();
  const { searches, isLoading: searchesLoading } = useRecentSearches();

  return (
    <Box sx={{ display: 'flex' }}>
      <Sidebar />
      <Box sx={{ flex: 1 }}>
        <Header />
        <Box component="main" sx={{ p: 3 }}>
          {/* 환영 메시지 */}
          <Typography variant="h4" gutterBottom>
            안녕하세요, {user?.username}님
          </Typography>

          {/* 빠른 검색 */}
          <Paper sx={{ p: 2, mb: 3 }}>
            <QuickSearch />
          </Paper>

          {/* 통계 위젯 */}
          <Grid container spacing={3} sx={{ mb: 3 }}>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                title="전체 문서"
                value={stats?.totalDocuments || 0}
                icon={<DocumentIcon />}
                loading={statsLoading}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                title="오늘 검색"
                value={stats?.todaySearches || 0}
                icon={<SearchIcon />}
                loading={statsLoading}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                title="활성 사용자"
                value={stats?.activeUsers || 0}
                icon={<UsersIcon />}
                loading={statsLoading}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <StatCard
                title="평균 응답시간"
                value={`${stats?.avgResponseTime || 0}ms`}
                icon={<TimerIcon />}
                loading={statsLoading}
              />
            </Grid>
          </Grid>

          {/* 최근 검색 */}
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              최근 검색
            </Typography>
            <RecentSearches
              searches={searches}
              loading={searchesLoading}
            />
          </Paper>
        </Box>
      </Box>
    </Box>
  );
};
```

### StatCard 컴포넌트

```typescript
// frontend/src/features/dashboard/components/StatCard.tsx
import { Card, CardContent, Typography, Skeleton, Box } from '@mui/material';

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  loading?: boolean;
  trend?: {
    value: number;
    direction: 'up' | 'down';
  };
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  icon,
  loading,
  trend
}) => {
  if (loading) {
    return (
      <Card>
        <CardContent>
          <Skeleton variant="text" width="60%" />
          <Skeleton variant="text" width="40%" height={40} />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
          <Box>
            <Typography color="textSecondary" gutterBottom>
              {title}
            </Typography>
            <Typography variant="h4">
              {value}
            </Typography>
            {trend && (
              <Typography
                variant="body2"
                color={trend.direction === 'up' ? 'success.main' : 'error.main'}
              >
                {trend.direction === 'up' ? '+' : ''}{trend.value}%
              </Typography>
            )}
          </Box>
          <Box sx={{ color: 'primary.main' }}>
            {icon}
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
};
```

### QuickSearch 컴포넌트

```typescript
// frontend/src/features/dashboard/components/QuickSearch.tsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { TextField, InputAdornment, IconButton } from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';

export const QuickSearch: React.FC = () => {
  const [query, setQuery] = useState('');
  const navigate = useNavigate();

  const handleSearch = () => {
    if (query.trim()) {
      navigate(`/search/chat?q=${encodeURIComponent(query)}`);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <TextField
      fullWidth
      placeholder="무엇이든 물어보세요..."
      value={query}
      onChange={(e) => setQuery(e.target.value)}
      onKeyPress={handleKeyPress}
      InputProps={{
        startAdornment: (
          <InputAdornment position="start">
            <SearchIcon />
          </InputAdornment>
        ),
        endAdornment: (
          <InputAdornment position="end">
            <IconButton onClick={handleSearch} disabled={!query.trim()}>
              <SendIcon />
            </IconButton>
          </InputAdornment>
        )
      }}
    />
  );
};
```

### API 훅

```typescript
// frontend/src/features/dashboard/hooks/useDashboardStats.ts
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../../shared/api/client';

interface DashboardStats {
  totalDocuments: number;
  todaySearches: number;
  activeUsers: number;
  avgResponseTime: number;
}

export const useDashboardStats = () => {
  return useQuery<DashboardStats>({
    queryKey: ['dashboard', 'stats'],
    queryFn: () => apiClient.get('/api/v1/stats/dashboard').then(res => res.data),
    staleTime: 60000, // 1분간 캐시
  });
};
```

### 영향 범위
- `frontend/src/features/dashboard/Dashboard.tsx`
- `frontend/src/features/dashboard/components/StatCard.tsx`
- `frontend/src/features/dashboard/components/QuickSearch.tsx`
- `frontend/src/features/dashboard/components/RecentSearches.tsx`
- `frontend/src/features/dashboard/hooks/useDashboardStats.ts`
- `frontend/src/shared/components/Sidebar.tsx`
- `frontend/src/shared/components/Header.tsx`

---

## 테스트 계획

- [ ] Unit Test: StatCard 렌더링
- [ ] Unit Test: QuickSearch 입력/네비게이션
- [ ] Unit Test: API 훅 (mock)
- [ ] Integration Test: Dashboard 전체 렌더링
- [ ] Accessibility Test: 키보드 네비게이션

---

## 참고 자료

- [Material UI Dashboard](https://mui.com/material-ui/getting-started/templates/dashboard/)
- [Frontend 상세 설계서](../../knowledge_service/docs/02_design/frontend_detailed_design.md)
- [UI Storyboard](../../knowledge_service/docs/02_design/ui_storyboard/)
