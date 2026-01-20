import { useState } from 'react';
import { Box, Typography, Tabs, Tab } from '@mui/material';
import ChatSearch from '@/components/search/ChatSearch';
import KeywordSearch from '@/components/search/KeywordSearch';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => (
  <div role="tabpanel" hidden={value !== index}>
    {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
  </div>
);

/**
 * SearchPage - 검색 페이지
 *
 * 채팅형 검색과 키워드 검색 두 가지 모드 제공
 */
const SearchPage: React.FC = () => {
  const [tabValue, setTabValue] = useState(0);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Search
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
        Search through knowledge base
      </Typography>

      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={tabValue} onChange={handleTabChange}>
          <Tab label="Chat Search" />
          <Tab label="Keyword Search" />
        </Tabs>
      </Box>

      <TabPanel value={tabValue} index={0}>
        <ChatSearch />
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        <KeywordSearch />
      </TabPanel>
    </Box>
  );
};

export default SearchPage;
