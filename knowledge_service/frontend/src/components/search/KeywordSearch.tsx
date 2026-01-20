import { useState } from 'react';
import {
  Box,
  TextField,
  Button,
  Paper,
  Typography,
  Chip,
  Pagination,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import SearchFilters from './SearchFilters';

interface SearchResult {
  id: string;
  title: string;
  content: string;
  score: number;
  documentType: string;
  projectName: string;
}

interface Filters {
  documentType?: string;
  projectName?: string;
  dateFrom?: string;
  dateTo?: string;
}

/**
 * KeywordSearch - 키워드 검색 컴포넌트
 *
 * 필터링 및 페이지네이션 지원
 */
const KeywordSearch: React.FC = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [filters, setFilters] = useState<Filters>({});
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setIsLoading(true);
    try {
      // TODO: 실제 API 연결
      await new Promise((resolve) => setTimeout(resolve, 500));

      // Mock 결과
      const mockResults: SearchResult[] = [
        {
          id: '1',
          title: 'Sample Document 1',
          content: `This is a sample result for "${query}"...`,
          score: 0.95,
          documentType: 'Technical',
          projectName: 'Project A',
        },
        {
          id: '2',
          title: 'Sample Document 2',
          content: 'Another relevant result...',
          score: 0.87,
          documentType: 'Guide',
          projectName: 'Project B',
        },
      ];

      setResults(mockResults);
      setTotalPages(1);
    } catch (error) {
      console.error('Search error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFilterChange = (newFilters: Filters) => {
    setFilters(newFilters);
    setPage(1);
  };

  const handlePageChange = (_event: React.ChangeEvent<unknown>, value: number) => {
    setPage(value);
    // TODO: 페이지 변경 시 검색 다시 실행
  };

  return (
    <Box>
      {/* Search Input */}
      <Paper
        component="form"
        onSubmit={handleSearch}
        sx={{ p: 2, mb: 3, display: 'flex', gap: 2, alignItems: 'center' }}
      >
        <TextField
          fullWidth
          placeholder="Enter search keywords..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          variant="outlined"
        />
        <Button
          type="submit"
          variant="contained"
          startIcon={<SearchIcon />}
          disabled={isLoading || !query.trim()}
          sx={{ minWidth: 120 }}
        >
          {isLoading ? 'Searching...' : 'Search'}
        </Button>
      </Paper>

      {/* Filters */}
      <SearchFilters filters={filters} onFilterChange={handleFilterChange} />

      {/* Results */}
      <Box sx={{ mt: 3 }}>
        {results.length === 0 ? (
          <Paper sx={{ p: 4, textAlign: 'center' }}>
            <Typography color="text.secondary">
              {query ? 'No results found' : 'Enter keywords to search'}
            </Typography>
          </Paper>
        ) : (
          <>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Found {results.length} results
            </Typography>
            {results.map((result) => (
              <Paper key={result.id} sx={{ p: 3, mb: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  <Typography variant="h6">{result.title}</Typography>
                  <Chip
                    label={`${(result.score * 100).toFixed(0)}%`}
                    size="small"
                    color="primary"
                  />
                </Box>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  {result.content}
                </Typography>
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Chip
                    label={result.documentType}
                    size="small"
                    variant="outlined"
                  />
                  <Chip
                    label={result.projectName}
                    size="small"
                    variant="outlined"
                  />
                </Box>
              </Paper>
            ))}

            {totalPages > 1 && (
              <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
                <Pagination
                  count={totalPages}
                  page={page}
                  onChange={handlePageChange}
                  color="primary"
                />
              </Box>
            )}
          </>
        )}
      </Box>
    </Box>
  );
};

export default KeywordSearch;
