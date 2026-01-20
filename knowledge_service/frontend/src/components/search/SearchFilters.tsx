import { Box, FormControl, InputLabel, MenuItem, Select, TextField, Button, Collapse, IconButton } from '@mui/material';
import { useState } from 'react';
import FilterListIcon from '@mui/icons-material/FilterList';
import ClearIcon from '@mui/icons-material/Clear';

interface Filters {
  documentType?: string;
  projectName?: string;
  dateFrom?: string;
  dateTo?: string;
}

interface SearchFiltersProps {
  filters: Filters;
  onFilterChange: (filters: Filters) => void;
}

const documentTypes = [
  { value: '', label: 'All Types' },
  { value: 'technical', label: 'Technical' },
  { value: 'guide', label: 'Guide' },
  { value: 'manual', label: 'Manual' },
  { value: 'report', label: 'Report' },
];

const projects = [
  { value: '', label: 'All Projects' },
  { value: 'project-a', label: 'Project A' },
  { value: 'project-b', label: 'Project B' },
  { value: 'project-c', label: 'Project C' },
];

/**
 * SearchFilters - 검색 필터 컴포넌트
 *
 * 문서 유형, 프로젝트, 날짜 범위 필터링
 */
const SearchFilters: React.FC<SearchFiltersProps> = ({
  filters,
  onFilterChange,
}) => {
  const [expanded, setExpanded] = useState(false);

  const handleChange = (field: keyof Filters, value: string) => {
    onFilterChange({
      ...filters,
      [field]: value || undefined,
    });
  };

  const handleClear = () => {
    onFilterChange({});
  };

  const hasFilters = Object.values(filters).some(Boolean);

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
        <IconButton
          onClick={() => setExpanded(!expanded)}
          color={expanded ? 'primary' : 'default'}
        >
          <FilterListIcon />
        </IconButton>
        <Button
          variant="text"
          onClick={() => setExpanded(!expanded)}
          sx={{ textTransform: 'none' }}
        >
          Filters {hasFilters && `(${Object.values(filters).filter(Boolean).length})`}
        </Button>
        {hasFilters && (
          <IconButton onClick={handleClear} size="small" title="Clear filters">
            <ClearIcon fontSize="small" />
          </IconButton>
        )}
      </Box>

      <Collapse in={expanded}>
        <Box
          sx={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: 2,
            p: 2,
            backgroundColor: 'background.paper',
            borderRadius: 1,
          }}
        >
          <FormControl sx={{ minWidth: 150 }} size="small">
            <InputLabel>Document Type</InputLabel>
            <Select
              value={filters.documentType || ''}
              label="Document Type"
              onChange={(e) => handleChange('documentType', e.target.value)}
            >
              {documentTypes.map((type) => (
                <MenuItem key={type.value} value={type.value}>
                  {type.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl sx={{ minWidth: 150 }} size="small">
            <InputLabel>Project</InputLabel>
            <Select
              value={filters.projectName || ''}
              label="Project"
              onChange={(e) => handleChange('projectName', e.target.value)}
            >
              {projects.map((project) => (
                <MenuItem key={project.value} value={project.value}>
                  {project.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <TextField
            label="From Date"
            type="date"
            size="small"
            value={filters.dateFrom || ''}
            onChange={(e) => handleChange('dateFrom', e.target.value)}
            InputLabelProps={{ shrink: true }}
          />

          <TextField
            label="To Date"
            type="date"
            size="small"
            value={filters.dateTo || ''}
            onChange={(e) => handleChange('dateTo', e.target.value)}
            InputLabelProps={{ shrink: true }}
          />
        </Box>
      </Collapse>
    </Box>
  );
};

export default SearchFilters;
