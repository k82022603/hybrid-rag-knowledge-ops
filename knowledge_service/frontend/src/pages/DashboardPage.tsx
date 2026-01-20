import { Box, Typography, Grid, Card, CardContent } from '@mui/material';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import SearchIcon from '@mui/icons-material/Search';
import DescriptionIcon from '@mui/icons-material/Description';
import PeopleIcon from '@mui/icons-material/People';

interface StatCardProps {
  title: string;
  value: string;
  icon: React.ReactNode;
  color: string;
}

const StatCard: React.FC<StatCardProps> = ({ title, value, icon, color }) => (
  <Card sx={{ height: '100%' }}>
    <CardContent>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        <Box
          sx={{
            backgroundColor: `${color}20`,
            borderRadius: 2,
            p: 1,
            mr: 2,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Box sx={{ color }}>{icon}</Box>
        </Box>
        <Typography variant="subtitle2" color="text.secondary">
          {title}
        </Typography>
      </Box>
      <Typography variant="h4" fontWeight="bold">
        {value}
      </Typography>
    </CardContent>
  </Card>
);

/**
 * DashboardPage - 대시보드 페이지
 *
 * 검색 통계, 시스템 상태, 사용자 활동 로그 시각화
 */
const DashboardPage: React.FC = () => {
  // TODO: React Query를 통한 실제 데이터 페칭
  const stats = [
    {
      title: 'Total Documents',
      value: '1,234',
      icon: <DescriptionIcon />,
      color: '#1976d2',
    },
    {
      title: 'Search Queries (Today)',
      value: '456',
      icon: <SearchIcon />,
      color: '#2e7d32',
    },
    {
      title: 'Active Users',
      value: '89',
      icon: <PeopleIcon />,
      color: '#ed6c02',
    },
    {
      title: 'Indexing Rate',
      value: '98.5%',
      icon: <TrendingUpIcon />,
      color: '#9c27b0',
    },
  ];

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Knowledge Portal Overview
      </Typography>

      <Grid container spacing={3}>
        {stats.map((stat, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <StatCard {...stat} />
          </Grid>
        ))}
      </Grid>

      {/* TODO: Add charts and graphs for statistics */}
      <Box sx={{ mt: 4 }}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Recent Activity
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Activity log will be displayed here...
            </Typography>
          </CardContent>
        </Card>
      </Box>
    </Box>
  );
};

export default DashboardPage;
