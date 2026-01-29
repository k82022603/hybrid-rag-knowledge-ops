/**
 * SearchFilters component tests
 *
 * Tests for the search filters component:
 * - Rendering of all filter inputs
 * - Filter change callbacks
 * - Clear all functionality
 * - Filter chips display and removal
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import SearchFilters from '../SearchFilters';

describe('SearchFilters', () => {
  const mockOnFilterChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ===== Rendering =====

  describe('rendering', () => {
    it('should render the filters container', () => {
      render(
        <SearchFilters filters={{}} onFilterChange={mockOnFilterChange} />
      );

      expect(screen.getByTestId('search-filters')).toBeInTheDocument();
    });

    it('should render filters title', () => {
      render(
        <SearchFilters filters={{}} onFilterChange={mockOnFilterChange} />
      );

      expect(screen.getByText('Filters')).toBeInTheDocument();
    });

    it('should render document type select', () => {
      render(
        <SearchFilters filters={{}} onFilterChange={mockOnFilterChange} />
      );

      expect(screen.getByLabelText('Document Type')).toBeInTheDocument();
      expect(screen.getByRole('combobox', { name: /Document Type/i })).toBeInTheDocument();
    });

    it('should render project select', () => {
      render(
        <SearchFilters filters={{}} onFilterChange={mockOnFilterChange} />
      );

      expect(screen.getByLabelText('Project')).toBeInTheDocument();
      expect(screen.getByRole('combobox', { name: /Project/i })).toBeInTheDocument();
    });

    it('should render date from input', () => {
      render(
        <SearchFilters filters={{}} onFilterChange={mockOnFilterChange} />
      );

      expect(screen.getByLabelText('From Date')).toBeInTheDocument();
    });

    it('should render date to input', () => {
      render(
        <SearchFilters filters={{}} onFilterChange={mockOnFilterChange} />
      );

      expect(screen.getByLabelText('To Date')).toBeInTheDocument();
    });

    it('should render all document type options', () => {
      render(
        <SearchFilters filters={{}} onFilterChange={mockOnFilterChange} />
      );

      const docTypeSelect = screen.getByRole('combobox', { name: /Document Type/i });
      expect(docTypeSelect).toContainHTML('All Types');
      expect(docTypeSelect).toContainHTML('Technical');
      expect(docTypeSelect).toContainHTML('Guide');
      expect(docTypeSelect).toContainHTML('Manual');
      expect(docTypeSelect).toContainHTML('Report');
      expect(docTypeSelect).toContainHTML('Policy');
      expect(docTypeSelect).toContainHTML('Meeting Notes');
    });

    it('should render all project options', () => {
      render(
        <SearchFilters filters={{}} onFilterChange={mockOnFilterChange} />
      );

      const projectSelect = screen.getByRole('combobox', { name: /Project/i });
      expect(projectSelect).toContainHTML('All Projects');
      expect(projectSelect).toContainHTML('Project A');
      expect(projectSelect).toContainHTML('Project B');
      expect(projectSelect).toContainHTML('Project C');
    });
  });

  // ===== Filter Changes =====

  describe('filter changes', () => {
    it('should call onFilterChange when document type is selected', () => {
      render(
        <SearchFilters filters={{}} onFilterChange={mockOnFilterChange} />
      );

      const docTypeSelect = screen.getByRole('combobox', { name: /Document Type/i });
      fireEvent.change(docTypeSelect, { target: { value: 'technical' } });

      expect(mockOnFilterChange).toHaveBeenCalledWith({
        documentType: 'technical',
      });
    });

    it('should call onFilterChange when project is selected', () => {
      render(
        <SearchFilters filters={{}} onFilterChange={mockOnFilterChange} />
      );

      const projectSelect = screen.getByRole('combobox', { name: /Project/i });
      fireEvent.change(projectSelect, { target: { value: 'project-a' } });

      expect(mockOnFilterChange).toHaveBeenCalledWith({
        projectName: 'project-a',
      });
    });

    it('should call onFilterChange when from date is selected', () => {
      render(
        <SearchFilters filters={{}} onFilterChange={mockOnFilterChange} />
      );

      const dateFromInput = screen.getByLabelText('From Date');
      fireEvent.change(dateFromInput, { target: { value: '2024-01-01' } });

      expect(mockOnFilterChange).toHaveBeenCalledWith({
        dateFrom: '2024-01-01',
      });
    });

    it('should call onFilterChange when to date is selected', () => {
      render(
        <SearchFilters filters={{}} onFilterChange={mockOnFilterChange} />
      );

      const dateToInput = screen.getByLabelText('To Date');
      fireEvent.change(dateToInput, { target: { value: '2024-12-31' } });

      expect(mockOnFilterChange).toHaveBeenCalledWith({
        dateTo: '2024-12-31',
      });
    });

    it('should preserve existing filters when changing one filter', () => {
      const existingFilters = {
        documentType: 'guide',
        projectName: 'project-b',
      };

      render(
        <SearchFilters
          filters={existingFilters}
          onFilterChange={mockOnFilterChange}
        />
      );

      const dateFromInput = screen.getByLabelText('From Date');
      fireEvent.change(dateFromInput, { target: { value: '2024-06-01' } });

      expect(mockOnFilterChange).toHaveBeenCalledWith({
        documentType: 'guide',
        projectName: 'project-b',
        dateFrom: '2024-06-01',
      });
    });

    it('should set filter to undefined when empty option is selected', () => {
      const existingFilters = {
        documentType: 'guide',
      };

      render(
        <SearchFilters
          filters={existingFilters}
          onFilterChange={mockOnFilterChange}
        />
      );

      const docTypeSelect = screen.getByRole('combobox', { name: /Document Type/i });
      fireEvent.change(docTypeSelect, { target: { value: '' } });

      expect(mockOnFilterChange).toHaveBeenCalledWith({
        documentType: undefined,
      });
    });
  });

  // ===== Clear All =====

  describe('clear all button', () => {
    it('should not show clear all button when no filters are active', () => {
      render(
        <SearchFilters filters={{}} onFilterChange={mockOnFilterChange} />
      );

      expect(screen.queryByText('Clear all')).not.toBeInTheDocument();
    });

    it('should show clear all button when filters are active', () => {
      render(
        <SearchFilters
          filters={{ documentType: 'guide' }}
          onFilterChange={mockOnFilterChange}
        />
      );

      expect(screen.getByText('Clear all')).toBeInTheDocument();
    });

    it('should clear all filters when clear button is clicked', () => {
      render(
        <SearchFilters
          filters={{
            documentType: 'guide',
            projectName: 'project-a',
            dateFrom: '2024-01-01',
          }}
          onFilterChange={mockOnFilterChange}
        />
      );

      const clearButton = screen.getByText('Clear all');
      fireEvent.click(clearButton);

      expect(mockOnFilterChange).toHaveBeenCalledWith({});
    });

    it('should have accessible label on clear button', () => {
      render(
        <SearchFilters
          filters={{ documentType: 'guide' }}
          onFilterChange={mockOnFilterChange}
        />
      );

      const clearButton = screen.getByRole('button', {
        name: /Clear all filters/i,
      });
      expect(clearButton).toBeInTheDocument();
    });
  });

  // ===== Filter Chips =====

  describe('filter chips', () => {
    it('should not show filter chips when no filters are active', () => {
      render(
        <SearchFilters filters={{}} onFilterChange={mockOnFilterChange} />
      );

      expect(screen.queryByText(/Type:/)).not.toBeInTheDocument();
      expect(screen.queryByText(/Project:/)).not.toBeInTheDocument();
      expect(screen.queryByText(/From:/)).not.toBeInTheDocument();
      expect(screen.queryByText(/To:/)).not.toBeInTheDocument();
    });

    it('should show document type chip when filter is active', () => {
      render(
        <SearchFilters
          filters={{ documentType: 'technical' }}
          onFilterChange={mockOnFilterChange}
        />
      );

      expect(screen.getByText('Type: technical')).toBeInTheDocument();
    });

    it('should show project chip when filter is active', () => {
      render(
        <SearchFilters
          filters={{ projectName: 'project-a' }}
          onFilterChange={mockOnFilterChange}
        />
      );

      expect(screen.getByText('Project: project-a')).toBeInTheDocument();
    });

    it('should show date from chip when filter is active', () => {
      render(
        <SearchFilters
          filters={{ dateFrom: '2024-01-15' }}
          onFilterChange={mockOnFilterChange}
        />
      );

      expect(screen.getByText('From: 2024-01-15')).toBeInTheDocument();
    });

    it('should show date to chip when filter is active', () => {
      render(
        <SearchFilters
          filters={{ dateTo: '2024-12-31' }}
          onFilterChange={mockOnFilterChange}
        />
      );

      expect(screen.getByText('To: 2024-12-31')).toBeInTheDocument();
    });

    it('should show multiple chips when multiple filters are active', () => {
      render(
        <SearchFilters
          filters={{
            documentType: 'guide',
            projectName: 'project-b',
            dateFrom: '2024-01-01',
            dateTo: '2024-06-30',
          }}
          onFilterChange={mockOnFilterChange}
        />
      );

      expect(screen.getByText('Type: guide')).toBeInTheDocument();
      expect(screen.getByText('Project: project-b')).toBeInTheDocument();
      expect(screen.getByText('From: 2024-01-01')).toBeInTheDocument();
      expect(screen.getByText('To: 2024-06-30')).toBeInTheDocument();
    });
  });

  // ===== Remove Individual Filters =====

  describe('removing individual filters', () => {
    it('should remove document type filter when chip X is clicked', () => {
      render(
        <SearchFilters
          filters={{ documentType: 'guide', projectName: 'project-a' }}
          onFilterChange={mockOnFilterChange}
        />
      );

      const removeButton = screen.getByRole('button', {
        name: /Remove document type filter/i,
      });
      fireEvent.click(removeButton);

      expect(mockOnFilterChange).toHaveBeenCalledWith({
        documentType: undefined,
        projectName: 'project-a',
      });
    });

    it('should remove project filter when chip X is clicked', () => {
      render(
        <SearchFilters
          filters={{ documentType: 'guide', projectName: 'project-a' }}
          onFilterChange={mockOnFilterChange}
        />
      );

      const removeButton = screen.getByRole('button', {
        name: /Remove project filter/i,
      });
      fireEvent.click(removeButton);

      expect(mockOnFilterChange).toHaveBeenCalledWith({
        documentType: 'guide',
        projectName: undefined,
      });
    });

    it('should remove date from filter when chip X is clicked', () => {
      render(
        <SearchFilters
          filters={{ dateFrom: '2024-01-01' }}
          onFilterChange={mockOnFilterChange}
        />
      );

      const removeButton = screen.getByRole('button', {
        name: /Remove from date filter/i,
      });
      fireEvent.click(removeButton);

      expect(mockOnFilterChange).toHaveBeenCalledWith({
        dateFrom: undefined,
      });
    });

    it('should remove date to filter when chip X is clicked', () => {
      render(
        <SearchFilters
          filters={{ dateTo: '2024-12-31' }}
          onFilterChange={mockOnFilterChange}
        />
      );

      const removeButton = screen.getByRole('button', {
        name: /Remove to date filter/i,
      });
      fireEvent.click(removeButton);

      expect(mockOnFilterChange).toHaveBeenCalledWith({
        dateTo: undefined,
      });
    });
  });

  // ===== Current Filter Values =====

  describe('current filter values', () => {
    it('should display current document type value in select', () => {
      render(
        <SearchFilters
          filters={{ documentType: 'manual' }}
          onFilterChange={mockOnFilterChange}
        />
      );

      const docTypeSelect = screen.getByRole('combobox', { name: /Document Type/i });
      expect(docTypeSelect).toHaveValue('manual');
    });

    it('should display current project value in select', () => {
      render(
        <SearchFilters
          filters={{ projectName: 'project-c' }}
          onFilterChange={mockOnFilterChange}
        />
      );

      const projectSelect = screen.getByRole('combobox', { name: /Project/i });
      expect(projectSelect).toHaveValue('project-c');
    });

    it('should display current date from value in input', () => {
      render(
        <SearchFilters
          filters={{ dateFrom: '2024-03-15' }}
          onFilterChange={mockOnFilterChange}
        />
      );

      const dateFromInput = screen.getByLabelText('From Date');
      expect(dateFromInput).toHaveValue('2024-03-15');
    });

    it('should display current date to value in input', () => {
      render(
        <SearchFilters
          filters={{ dateTo: '2024-09-30' }}
          onFilterChange={mockOnFilterChange}
        />
      );

      const dateToInput = screen.getByLabelText('To Date');
      expect(dateToInput).toHaveValue('2024-09-30');
    });

    it('should display empty values when filters are empty', () => {
      render(
        <SearchFilters filters={{}} onFilterChange={mockOnFilterChange} />
      );

      const docTypeSelect = screen.getByRole('combobox', { name: /Document Type/i });
      const projectSelect = screen.getByRole('combobox', { name: /Project/i });
      const dateFromInput = screen.getByLabelText('From Date');
      const dateToInput = screen.getByLabelText('To Date');

      expect(docTypeSelect).toHaveValue('');
      expect(projectSelect).toHaveValue('');
      expect(dateFromInput).toHaveValue('');
      expect(dateToInput).toHaveValue('');
    });
  });
});
